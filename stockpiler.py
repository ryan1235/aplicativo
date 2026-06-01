"""Extract Foxhole pinned stockpile data and send private reports to an API."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from app_paths import extracted_dir, resource_dir


BASE_DIR = resource_dir()
VENDOR_DIR = BASE_DIR / "vendor"
DB_PATH = BASE_DIR / "update64.db"
CONTENT_DIR = BASE_DIR / "Content"
TEXTURES_DIR = BASE_DIR / "Content" / "Textures"
LEGACY_TEXTURES_DIR = BASE_DIR / "Textures"


def foxhole_savegames_dir() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Foxhole" / "Saved" / "SaveGames"
    return Path.home() / "AppData" / "Local" / "Foxhole" / "Saved" / "SaveGames"


def discover_map_data_file() -> Path | None:
    savegames = foxhole_savegames_dir()
    if not savegames.exists():
        return None
    try:
        candidates = [path for path in savegames.glob("*_MapData.sav") if path.is_file()]
    except OSError:
        return None
    if not candidates:
        return None
    dated_candidates: list[tuple[float, Path]] = []
    for path in candidates:
        try:
            dated_candidates.append((path.stat().st_mtime, path))
        except OSError:
            continue
    if not dated_candidates:
        return None
    return max(dated_candidates, key=lambda item: item[0])[1]


def default_watch_file() -> Path:
    discovered = discover_map_data_file()
    if discovered:
        return discovered
    return foxhole_savegames_dir() / "SteamID_MapData.sav"


DEFAULT_WATCH_FILE = default_watch_file()
DEFAULT_API_URL = "https://felblogi.discloud.app/data"
PINNED_TOOLTIPS_KEY = "PinnedMapToolTipsW"
EXCLUDED_FIELD = "InitalMapItemDetails"
STRIPPED_PREFIXES = {
    "MapId": "EWorldConquestMapId::",
    "RenderState": "EPinnedMapWidgetRenderState::",
}
STOCKPILE_SECTIONS = (
    ("Items", False),
    ("ItemCrates", True),
    ("Vehicles", False),
    ("VehicleCrates", True),
    ("Structures", False),
    ("StructureCrates", True),
)
ICON_TABLES = (
    "items",
    "vehicles",
    "structures_shippables",
    "structures_emplacements",
    "structures_other",
    "structures_facilities",
    "structures_tripods",
    "uniforms",
    "weapons",
    "ammo",
    "aircraft",
)
UE_TICKS_AT_UNIX_EPOCH = 621_355_968_000_000_000


class ExtractError(RuntimeError):
    pass


def unreal_datetime_to_iso(ticks: int) -> str:
    unix_ticks = ticks - UE_TICKS_AT_UNIX_EPOCH
    seconds, tick_remainder = divmod(unix_ticks, 10_000_000)
    microseconds = tick_remainder // 10
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc).replace(microsecond=microseconds)
    milliseconds = dt.microsecond // 1000
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{milliseconds:03d}Z"


def simplify(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, list | tuple):
        return [simplify(item) for item in value]
    if isinstance(value, dict):
        return {key: simplify(item) for key, item in value.items()}

    class_name = value.__class__.__name__
    if class_name == "DateTimeStruct" and hasattr(value, "datetime"):
        return unreal_datetime_to_iso(value.datetime)
    if class_name.endswith("Struct") and hasattr(value, "x") and hasattr(value, "y"):
        return {"x": simplify(value.x), "y": simplify(value.y)}
    if class_name == "ArrayProperty":
        return simplify(getattr(value, "values", []))
    if class_name == "StructProperty":
        return simplify(getattr(value, "value", None))
    if hasattr(value, "value"):
        return simplify(value.value)
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(exclude_none=True)
        return simplify(
            {
                key: item
                for key, item in dumped.items()
                if key not in {"type", "field_name", "type_name", "guid", "enum_type"}
            }
        )
    raise TypeError(f"Cannot simplify {class_name}")


def extract_pinned_tooltips(path: Path, *, strip_enum_prefixes: bool = True) -> list[Any]:
    try:
        from pygvas import GVASFile
    except ModuleNotFoundError as exc:
        if VENDOR_DIR.exists() and str(VENDOR_DIR) not in sys.path:
            sys.path.insert(0, str(VENDOR_DIR))
            try:
                from pygvas import GVASFile
            except ModuleNotFoundError:
                raise ExtractError("pygvas is required to read .sav files. Install requirements-python.txt.") from exc
        else:
            raise ExtractError("pygvas is required to read .sav files. Install requirements-python.txt.") from exc

    gvas = GVASFile.deserialize_gvas_file(str(path), deserialization_hints={})
    try:
        property_value = gvas.properties[PINNED_TOOLTIPS_KEY]
    except KeyError as exc:
        raise ExtractError(f"save is missing {PINNED_TOOLTIPS_KEY!r}") from exc

    items = simplify(property_value)
    if not isinstance(items, list):
        items = [items]

    for item in items:
        if not isinstance(item, dict):
            continue
        item.pop(EXCLUDED_FIELD, None)
        if strip_enum_prefixes:
            for field, prefix in STRIPPED_PREFIXES.items():
                current = item.get(field)
                if isinstance(current, str) and current.startswith(prefix):
                    item[field] = current.removeprefix(prefix)
    return items


def _stockpile_items(stockpile_info: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(stockpile_info, dict):
        return []

    items: list[dict[str, Any]] = []
    for section, is_crated in STOCKPILE_SECTIONS:
        for item in stockpile_info.get(section) or []:
            if not isinstance(item, dict):
                continue
            code_name = item.get("CodeName")
            if not code_name:
                continue
            try:
                quantity = int(item.get("Quantity") or 0)
            except (TypeError, ValueError):
                quantity = 0
            if quantity <= 0:
                continue
            icon_name = f"{code_name}-crated" if is_crated else str(code_name)
            items.append(
                {
                    "asset_name": str(code_name),
                    "icon_name": icon_name,
                    "quantity": quantity,
                    "total_quantity": quantity,
                    "crate_quantity": quantity if is_crated else 0,
                    "is_crated": is_crated,
                }
            )
    return items


def _build_api_report(
    entry: dict[str, Any],
    *,
    stockpile_info: dict[str, Any] | None,
    inventory_name: str,
    inventory_type: str,
    source_file: Path,
    extracted_at: str,
) -> dict[str, Any] | None:
    items = _stockpile_items(stockpile_info)
    if not items:
        return None

    map_id = entry.get("MapId")
    coords = entry.get("NormalizedMapCoords") or {}
    return {
        "metadata": {
            "source": "python/stockpiler.py",
            "extracted_at": extracted_at,
            "last_updated": entry.get("LastUpdated"),
            "map_id": map_id,
            "normalized_map_coords": coords,
        },
        "header": {
            "inventory_name": inventory_name,
            "inventory_type": inventory_type,
            "map_id": map_id,
        },
        "statistics": {"inventory_name": inventory_name, "item_count": len(items)},
        "items": items,
    }


def convert_to_api_reports(entries: list[Any], source_file: Path) -> list[dict[str, Any]]:
    extracted_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    reports: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        map_id = entry.get("MapId") or "UnknownMap"
        details = entry.get("RecentMapItemDetails") or {}
        if not isinstance(details, dict):
            continue
        for reserve in details.get("ReserveStockpileInfoList") or []:
            if not isinstance(reserve, dict):
                continue
            stockpile_name = reserve.get("StockpileName")
            if not stockpile_name:
                continue
            report = _build_api_report(
                entry,
                stockpile_info=reserve.get("StockpileInfo"),
                inventory_name=f"{map_id}/{stockpile_name}",
                inventory_type="ReserveStockpile",
                source_file=source_file,
                extracted_at=extracted_at,
            )
            if report:
                reports.append(report)
    return reports


def convert_to_api_payload(entries: list[Any], source_file: Path) -> dict[str, Any]:
    reports = convert_to_api_reports(entries, source_file)
    return {
        "metadata": {
            "source": "python/stockpiler.py",
            "extracted_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "report_count": len(reports),
            "scope": "private_stockpiles",
        },
        "reports": reports,
    }


def write_json(data: Any, output: Path | None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if output is None:
        print(text, flush=True)
        return
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    except OSError as exc:
        raise ExtractError(f"Nao foi possivel criar o JSON em {output}: {exc}") from exc


def parse_api_response(status: int, response_body: str) -> dict[str, Any]:
    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError:
        parsed = None
    return {
        "status_text": f"HTTP {status}",
        "body": parsed,
        "raw_body": response_body,
    }


def texture_path_from_object_path(iconobject_path: Any) -> str:
    if not isinstance(iconobject_path, str) or not iconobject_path:
        return ""

    object_path = iconobject_path.replace("\\", "/")
    if object_path.startswith("War/Content/Textures/"):
        object_path = object_path.removeprefix("War/Content/Textures/")
    elif object_path.startswith("War/Content/"):
        object_path = object_path.removeprefix("War/Content/")
    if object_path.endswith(".0"):
        object_path = object_path[:-2]

    object_paths = [object_path]
    if object_path.startswith("Slate/Images") and not object_path.startswith("Slate/Images/"):
        object_paths.append("Slate/Images/" + object_path.removeprefix("Slate/Images"))

    for asset_dir in (CONTENT_DIR, TEXTURES_DIR, LEGACY_TEXTURES_DIR):
        for path_variant in object_paths:
            candidate = asset_dir / path_variant
            if candidate.suffix.lower() != ".png":
                candidate = candidate.with_suffix(".png")
            if candidate.exists():
                return str(candidate)

    image_name = Path(object_paths[-1]).name
    image_pattern = image_name if image_name.lower().endswith(".png") else f"{image_name}.png"
    for asset_dir in (CONTENT_DIR, TEXTURES_DIR, LEGACY_TEXTURES_DIR):
        candidate = next(asset_dir.rglob(image_pattern), None) if asset_dir.exists() else None
        if candidate and candidate.exists():
            return str(candidate)
    return ""


@lru_cache(maxsize=1)
def load_icon_index() -> dict[str, dict[str, str]]:
    if not DB_PATH.exists():
        return {}

    index: dict[str, dict[str, str]] = {}
    try:
        with sqlite3.connect(DB_PATH) as connection:
            table_rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            existing_tables = {str(row[0]) for row in table_rows}

            for table in ICON_TABLES:
                if table not in existing_tables:
                    continue
                columns = {
                    str(row[1])
                    for row in connection.execute(f'PRAGMA table_info("{table}")').fetchall()
                }
                if not {"id", "iconobject_path"}.issubset(columns):
                    continue

                name_expr = "name" if "name" in columns else "id"
                rows = connection.execute(
                    f'SELECT id, {name_expr}, iconobject_path FROM "{table}" WHERE iconobject_path IS NOT NULL'
                ).fetchall()
                for asset_id, display_name, iconobject_path in rows:
                    asset_key = str(asset_id)
                    icon_path = texture_path_from_object_path(iconobject_path)
                    if not icon_path:
                        continue
                    index.setdefault(
                        asset_key,
                        {
                            "display_name": str(display_name or asset_key),
                            "icon_path": icon_path,
                            "source_table": table,
                        },
                    )
    except sqlite3.Error as exc:
        print(f"[Stockpile] icon database unavailable: {exc}", flush=True)
    return index


def icon_info_for_asset(asset_name: str) -> dict[str, str]:
    if not asset_name or asset_name == "-":
        return {}
    index = load_icon_index()
    if asset_name in index:
        return index[asset_name]

    lower_asset = asset_name.lower()
    for key, value in index.items():
        if key.lower() == lower_asset:
            return value
    return {}


def api_last_update(api_result: dict[str, Any]) -> str:
    body = api_result.get("body")
    if not isinstance(body, dict):
        return ""
    for change in body.get("changes") or []:
        if isinstance(change, dict) and change.get("type") == "timestamp":
            return str(change.get("last_update") or "")
    return str(body.get("last_update") or "")


def warehouse_summaries(api_result: dict[str, Any]) -> list[dict[str, Any]]:
    body = api_result.get("body")
    if not isinstance(body, dict):
        return []

    warehouses: dict[str, dict[str, Any]] = {}
    for item in body.get("data") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("WarehouseName")
        if not name:
            continue
        current = warehouses.setdefault(
            str(name),
            {
                "name": str(name),
                "item_count": 0,
                "total_quantity": 0,
                "zero_count": 0,
                "change_count": 0,
                "categories": set(),
            },
        )
        quantity = item.get("Quantity") or 0
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = 0
        current["item_count"] += 1
        current["total_quantity"] += max(0, quantity)
        if quantity <= 0:
            current["zero_count"] += 1
        if item.get("CategoryName"):
            current["categories"].add(str(item["CategoryName"]))

    for change in body.get("changes") or []:
        if not isinstance(change, dict):
            continue
        name = change.get("warehouse_name")
        if not name:
            continue
        current = warehouses.setdefault(
            str(name),
            {
                "name": str(name),
                "item_count": 0,
                "total_quantity": 0,
                "zero_count": 0,
                "change_count": 0,
                "categories": set(),
            },
        )
        current["change_count"] += 1

    summaries = []
    for item in warehouses.values():
        categories = sorted(item.pop("categories"))
        item["category_count"] = len(categories)
        item["categories"] = categories[:4]
        summaries.append(item)
    return sorted(summaries, key=lambda item: (item["total_quantity"], item["item_count"]), reverse=True)


def api_item_rows(api_result: dict[str, Any]) -> list[dict[str, Any]]:
    body = api_result.get("body")
    if not isinstance(body, dict):
        return []

    rows = []
    for item in body.get("data") or []:
        if not isinstance(item, dict):
            continue
        quantity = item.get("Quantity") or 0
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = 0
        asset_name = str(item.get("asset_name") or "-")
        icon_info = icon_info_for_asset(asset_name)
        rows.append(
            {
                "warehouse": str(item.get("WarehouseName") or "-"),
                "display_name": str(item.get("DisplayName") or item.get("asset_name") or "-"),
                "asset_name": asset_name,
                "icon_name": str(item.get("icon_name") or ""),
                "icon_path": icon_info.get("icon_path", ""),
                "icon_source": icon_info.get("source_table", ""),
                "category": str(item.get("CategoryName") or "-"),
                "quantity": quantity,
                "priority": str(item.get("Priority") or "-"),
                "faction": str(item.get("Faction") or "-"),
            }
        )
    return sorted(rows, key=lambda item: (item["warehouse"], item["display_name"]))


def request_json(api_url: str, data: Any, *, purpose: str, method: str = "POST") -> dict[str, Any]:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            result = parse_api_response(response.status, response_body)
            print(f"[Stockpile API] {purpose}: {result['status_text']}", flush=True)
            return result
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        print(f"[Stockpile API] {purpose}: HTTP {exc.code}: {response_body}", flush=True)
        raise ExtractError(f"HTTP {exc.code}: {response_body}") from exc
    except urllib.error.URLError as exc:
        print(f"[Stockpile API] {purpose} failed: {exc.reason}", flush=True)
        raise ExtractError(str(exc.reason)) from exc


def request_stockpile_debug(api_url: str) -> dict[str, Any]:
    return request_json(api_url, {"mode": "debug"}, purpose="debug", method="GET")


def post_json(data: Any, api_url: str) -> dict[str, Any]:
    return request_json(api_url, data, purpose="upload")


def default_output_path(sav_path: Path, out_dir: Path) -> Path:
    return out_dir / f"{sav_path.stem}.json"


def stable_payload_for_compare(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: stable_payload_for_compare(item)
            for key, item in value.items()
            if key not in {"extracted_at"}
        }
    if isinstance(value, list):
        return [stable_payload_for_compare(item) for item in value]
    return value


def payload_changed_since_last_write(payload: dict[str, Any], output: Path) -> bool:
    if not output.exists():
        return True
    try:
        previous = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    return stable_payload_for_compare(previous) != stable_payload_for_compare(payload)


def summarize_payload(payload: dict[str, Any], api_response: dict[str, Any]) -> dict[str, Any]:
    reports = payload.get("reports") if isinstance(payload, dict) else []
    reports = reports if isinstance(reports, list) else []
    stockpiles = [
        str(report.get("header", {}).get("inventory_name", "Unknown"))
        for report in reports
        if isinstance(report, dict)
    ]
    item_count = 0
    for report in reports:
        if isinstance(report, dict):
            items = report.get("items")
            if isinstance(items, list):
                item_count += len(items)
    sent_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "kind": "api_result",
        "api_response": api_response.get("status_text", "-"),
        "api_last_update": api_last_update(api_response) or sent_at,
        "warehouse_summaries": warehouse_summaries(api_response),
        "items": api_item_rows(api_response),
        "report_count": len(reports),
        "stockpiles": stockpiles,
        "item_count": item_count,
        "sent_at": sent_at,
    }


def extract_and_post(
    path: Path,
    out_dir: Path,
    api_url: str,
    *,
    keep_enum_prefixes: bool = False,
    force_api_refresh: bool = False,
) -> dict[str, Any] | None:
    data = extract_pinned_tooltips(path, strip_enum_prefixes=not keep_enum_prefixes)
    payload = convert_to_api_payload(data, path)
    output = default_output_path(path, out_dir)
    has_changed = payload_changed_since_last_write(payload, output)
    if not has_changed and not force_api_refresh:
        print("[Stockpile] unchanged; waiting 5 min refresh", flush=True)
        return None

    if has_changed:
        write_json(payload, output)
    report_count = len(payload.get("reports", []))
    action = "wrote" if has_changed else "kept"
    print(f"[Stockpile] {action} {report_count} private API reports", flush=True)
    api_message = post_json(payload, api_url)
    summary = summarize_payload(payload, api_message)
    summary["payload_changed"] = has_changed
    summary["upload_reason"] = "file_changed" if has_changed else "sync_refresh"
    return summary


class StockpileWatcher:
    def __init__(
        self,
        file_path: Path,
        out_dir: Path,
        api_url: str,
        *,
        extract_initial: bool = True,
        debounce: float = 3.0,
        interval: float = 0.5,
        sync_interval: float = 300.0,
        status_callback: Callable[[str | dict[str, Any]], None] | None = None,
    ) -> None:
        self.file_path = file_path
        self.out_dir = out_dir
        self.api_url = api_url
        self.extract_initial = extract_initial
        self.debounce = debounce
        self.interval = interval
        self.sync_interval = sync_interval
        self.status_callback = status_callback
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.send_count = 0

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _status(self, message: str | dict[str, Any]) -> None:
        if isinstance(message, dict):
            print(
                f"[Stockpile] {message.get('api_response', '-')} | "
                f"{message.get('report_count', 0)} stockpiles | "
                f"{len(message.get('items') or [])} API items",
                flush=True,
            )
        else:
            print(f"[Stockpile] {message}", flush=True)
        if self.status_callback:
            self.status_callback(message)

    def _run(self) -> None:
        path = self.file_path.resolve()
        self._status("running")
        last_mtime = path.stat().st_mtime if path.exists() else 0.0
        pending_at = time.monotonic() if self.extract_initial else None
        pending_force_api_refresh = False
        next_sync_at = time.monotonic() + self.sync_interval
        if not path.exists():
            self._status(f"waiting for Foxhole save file: {path}")

        while not self.stop_event.is_set():
            try:
                mtime = path.stat().st_mtime
            except FileNotFoundError:
                discovered = discover_map_data_file()
                if discovered and discovered.resolve() != path:
                    path = discovered.resolve()
                    self.file_path = path
                    last_mtime = path.stat().st_mtime
                    pending_at = time.monotonic()
                    self._status(f"found Foxhole save file: {path}")
                    time.sleep(self.interval)
                    continue
                time.sleep(self.interval)
                continue
            except OSError as exc:
                self._status(f"cannot read Foxhole save file: {path}: {exc}")
                time.sleep(self.interval)
                continue

            now = time.monotonic()
            if mtime != last_mtime:
                last_mtime = mtime
                pending_at = now
                pending_force_api_refresh = False

            if now >= next_sync_at:
                pending_at = now
                pending_force_api_refresh = True
                next_sync_at = now + self.sync_interval

            if pending_at is not None and now - pending_at >= self.debounce:
                pending_at = None
                try:
                    result = extract_and_post(
                        path,
                        self.out_dir,
                        self.api_url,
                        force_api_refresh=pending_force_api_refresh,
                    )
                    pending_force_api_refresh = False
                    if result is None:
                        self._status("stockpile unchanged")
                    else:
                        self.send_count += 1
                        result["send_count"] = self.send_count
                        self._status(result)
                except Exception as exc:
                    pending_force_api_refresh = False
                    self._status(str(exc))

            time.sleep(self.interval)


def stockpile_settings_from_env() -> dict[str, Any]:
    return {
        "watch_file": os.getenv("STOCKPILER_WATCH_FILE", str(DEFAULT_WATCH_FILE)),
        "api_url": os.getenv("STOCKPILER_API_URL", DEFAULT_API_URL),
        "out_dir": os.getenv("STOCKPILER_OUT_DIR", str(extracted_dir())),
        "enabled": True,
        "extract_initial": True,
    }
