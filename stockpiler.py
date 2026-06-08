"""Extract Foxhole pinned stockpile data and send private reports to an API."""

from __future__ import annotations

import gc
import hashlib
import heapq
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
    files = discover_map_data_files()
    return files[0] if files else None


def discover_map_data_files() -> list[Path]:
    savegames = foxhole_savegames_dir()
    if not savegames.exists():
        return []
    try:
        candidates = [path for path in savegames.glob("*_MapData.sav") if path.is_file()]
    except OSError:
        return []
    if not candidates:
        return []
    dated_candidates: list[tuple[float, Path]] = []
    for path in candidates:
        try:
            dated_candidates.append((path.stat().st_mtime, path))
        except OSError:
            continue
    if not dated_candidates:
        return []
    return [path for _mtime, path in sorted(dated_candidates, key=lambda item: item[0], reverse=True)]


def default_watch_file() -> Path:
    discovered = discover_map_data_file()
    if discovered:
        return discovered
    return foxhole_savegames_dir() / "SteamID_MapData.sav"


DEFAULT_WATCH_FILE = default_watch_file()


def _hidden_text(values: tuple[int, ...], *, mask: int = 71) -> str:
    return "".join(chr(value ^ mask) for value in values)


DEFAULT_API_URL = os.getenv(
    "STOCKPILER_API_URL",
    _hidden_text((47, 51, 51, 55, 52, 125, 104, 104, 33, 34, 43, 37, 43, 40, 32, 46, 105, 35, 46, 52, 36, 43, 40, 50, 35, 105, 38, 55, 55, 104, 35, 38, 51, 38)),
)
DEFAULT_API_KEY = os.getenv(
    "FELB_API_KEY",
    _hidden_text((6, 14, 61, 38, 112, 42, 116, 106, 46, 4, 15, 20, 43, 19, 37, 11, 3, 38, 49, 29, 44, 6, 10, 106, 113, 0, 49, 119, 61, 21, 4, 43, 11, 116, 119, 31, 37, 21, 20)),
)
STOCKPILE_DEBUG_LOG = extracted_dir() / "stockpile_debug.log"
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
MAX_LOG_MESSAGE_CHARS = 4000
VERBOSE_STOCKPILE_DEBUG = os.environ.get("FELB_STOCKPILE_VERBOSE_DEBUG", "").lower() in {"1", "true", "yes", "on"}
PRETTY_STOCKPILE_JSON = os.environ.get("FELB_STOCKPILE_PRETTY_JSON", "").lower() in {"1", "true", "yes", "on"}


class ExtractError(RuntimeError):
    pass


def _compact_log_message(message: object) -> str:
    text = str(message)
    if len(text) <= MAX_LOG_MESSAGE_CHARS:
        return text
    omitted = len(text) - MAX_LOG_MESSAGE_CHARS
    return f"{text[:MAX_LOG_MESSAGE_CHARS]}... <truncated {omitted} chars>"


def _debug_log(message: str) -> None:
    message = _compact_log_message(message)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)
    try:
        STOCKPILE_DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        with STOCKPILE_DEBUG_LOG.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def _runtime_log(message: str) -> None:
    message = _compact_log_message(message)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


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


def _stable_hash_update(hasher: "hashlib._Hash", value: Any) -> None:
    if isinstance(value, dict):
        hasher.update(b"{")
        first = True
        for key in sorted((item for item in value.keys() if str(item) != "extracted_at"), key=str):
            if not first:
                hasher.update(b",")
            first = False
            hasher.update(json.dumps(str(key), ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            hasher.update(b":")
            _stable_hash_update(hasher, value[key])
        hasher.update(b"}")
        return
    if isinstance(value, list):
        hasher.update(b"[")
        for index, item in enumerate(value):
            if index:
                hasher.update(b",")
            _stable_hash_update(hasher, item)
        hasher.update(b"]")
        return
    hasher.update(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def stable_payload_hash(value: Any) -> str:
    hasher = hashlib.sha256()
    _stable_hash_update(hasher, value)
    return hasher.hexdigest()


def payload_hash_path(output: Path) -> Path:
    return output.with_suffix(output.suffix + ".sha256")


def write_payload_hash(payload: Any, output: Path, payload_hash: str | None = None) -> None:
    digest = payload_hash or stable_payload_hash(payload)
    try:
        payload_hash_path(output).write_text(digest + "\n", encoding="utf-8")
    except OSError:
        pass


def write_json(data: Any, output: Path | None, payload_hash: str | None = None) -> None:
    if output is None:
        print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)
        return
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as handle:
            if PRETTY_STOCKPILE_JSON:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            else:
                json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
        write_payload_hash(data, output, payload_hash)
        _runtime_log(f"[Stockpile] JSON written to {output}")
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
        "raw_body": "" if parsed is not None else response_body,
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


def format_to_local_pc_time(value: str) -> str:
    text = str(value or "").strip()
    if not text or text == "-":
        return "-"
    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return text
    try:
        if parsed.tzinfo is None:
            # API usually sends UTC-like timestamps without offset.
            parsed = parsed.replace(tzinfo=timezone.utc)
        local_dt = parsed.astimezone()
        return local_dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return text


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
                "last_update": "",
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
        warehouse_last_update = str(item.get("WarehouseLastUpdate") or "")
        if warehouse_last_update:
            current["last_update"] = warehouse_last_update

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
                "last_update": "",
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
                "warehouse_last_update": str(item.get("WarehouseLastUpdate") or "-"),
            }
        )
    rows.sort(key=lambda item: (item["warehouse"], item["display_name"]))
    return rows


def request_json(api_url: str, data: Any, *, purpose: str, method: str = "POST") -> dict[str, Any]:
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    log_upload = purpose == "upload" and method.upper() == "POST"
    log = _debug_log if log_upload else _runtime_log
    log(f"[Stockpile API] request start purpose={purpose} method={method} endpoint=stockpile")
    if log_upload:
        _debug_log(f"[Stockpile API] request payload bytes={len(body)}")
        if VERBOSE_STOCKPILE_DEBUG:
            _debug_log(f"[Stockpile API] request payload body={body.decode('utf-8', errors='replace')}")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-Key": DEFAULT_API_KEY,
    }
    request = urllib.request.Request(
        api_url,
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            result = parse_api_response(response.status, response_body)
            log(f"[Stockpile API] response status={response.status}")
            if log_upload and VERBOSE_STOCKPILE_DEBUG:
                _debug_log(f"[Stockpile API] response body={response_body}")
            log(f"[Stockpile API] {purpose}: {result['status_text']}")
            return result
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        log(f"[Stockpile API] HTTPError status={exc.code} body={response_body}")
        raise ExtractError(f"HTTP {exc.code}: {response_body}") from exc
    except urllib.error.URLError as exc:
        log(f"[Stockpile API] URLError reason={exc.reason}")
        raise ExtractError(str(exc.reason)) from exc


def request_stockpile_debug(api_url: str) -> dict[str, Any]:
    return request_json(api_url, {"mode": "debug"}, purpose="debug", method="GET")


def post_json(data: Any, api_url: str) -> dict[str, Any]:
    return request_json(api_url, data, purpose="upload")


def default_output_path(sav_path: Path, out_dir: Path) -> Path:
    return out_dir / f"{sav_path.stem}.json"


def last_sent_output_path(sav_path: Path, out_dir: Path) -> Path:
    return out_dir / f"{sav_path.stem}_last_sent.json"


def payload_changed_since_json(payload: dict[str, Any], output: Path, payload_hash: str | None = None) -> bool:
    current_hash = payload_hash or stable_payload_hash(payload)
    hash_path = payload_hash_path(output)
    try:
        previous_hash = hash_path.read_text(encoding="utf-8").strip()
    except OSError:
        previous_hash = ""
    if previous_hash:
        return previous_hash != current_hash
    if not output.exists():
        return True
    try:
        with output.open("r", encoding="utf-8") as handle:
            previous = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return True
    previous_hash = stable_payload_hash(previous)
    del previous
    changed = previous_hash != current_hash
    if not changed:
        write_payload_hash(payload, output, current_hash)
    return changed


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


def log_stockpile_debug_details(
    payload: dict[str, Any],
    *,
    source_file: Path,
    output: Path,
    sent_output: Path,
    upload_reason: str,
    capture_changed: bool,
    api_payload_changed: bool,
    extracted_entries: int,
    action: str,
) -> None:
    reports = payload.get("reports") if isinstance(payload, dict) else []
    reports = reports if isinstance(reports, list) else []
    total_items = 0
    total_crated = 0
    for report in reports:
        if not isinstance(report, dict):
            continue
        items = report.get("items")
        if not isinstance(items, list):
            continue
        total_items += len(items)
        total_crated += sum(1 for item in items if isinstance(item, dict) and item.get("is_crated"))

    _debug_log("[Stockpile Reload] ----------")
    _debug_log(f"[Stockpile Reload] reason={upload_reason} action={action}")
    _debug_log(f"[Stockpile Reload] source_file={source_file}")
    _debug_log(f"[Stockpile Reload] extracted_entries={extracted_entries}")
    _debug_log(f"[Stockpile Reload] captured_json={output}")
    _debug_log(f"[Stockpile Reload] last_sent_json={sent_output}")
    _debug_log("[Stockpile Reload] comparison=stable payload JSON, ignoring extracted_at timestamps")
    _debug_log(
        "[Stockpile Reload] "
        f"captured_json_changed={capture_changed} "
        f"last_sent_json_equal={not api_payload_changed} "
        f"api_payload_changed={api_payload_changed}"
    )
    _debug_log(f"[Stockpile Reload] detected_stockpiles={len(reports)} detected_items={total_items} crated_items={total_crated}")

    for index, report in enumerate(reports, 1):
        if not isinstance(report, dict):
            continue
        header = report.get("header") if isinstance(report.get("header"), dict) else {}
        metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        items = report.get("items") if isinstance(report.get("items"), list) else []
        name = header.get("inventory_name", "Unknown")
        inventory_type = header.get("inventory_type", "-")
        map_id = header.get("map_id") or metadata.get("map_id") or "-"
        _debug_log(f"[Stockpile Reload] #{index} {name} type={inventory_type} map={map_id} items={len(items)}")
        valid_count = sum(1 for item in items if isinstance(item, dict))
        sample_items = heapq.nsmallest(
            20,
            (item for item in items if isinstance(item, dict)),
            key=lambda item: (str(item.get("display_name") or item.get("asset_name") or ""), int(item.get("quantity") or 0)),
        )
        for item in sample_items:
            display = item.get("display_name") or item.get("asset_name") or "-"
            asset = item.get("asset_name") or "-"
            quantity = item.get("quantity") or 0
            crate_quantity = item.get("crate_quantity") or 0
            crate_text = f", crates={crate_quantity}" if crate_quantity else ""
            _debug_log(f"[Stockpile Reload]    - {display} ({asset}) qty={quantity}{crate_text}")
        if valid_count > 20:
            _debug_log(f"[Stockpile Reload]    ... +{valid_count - 20} itens")


def extract_and_post(
    path: Path,
    out_dir: Path,
    api_url: str,
    *,
    keep_enum_prefixes: bool = False,
    force_api_refresh: bool = False,
    upload_reason: str = "file_changed",
) -> dict[str, Any] | None:
    _runtime_log(f"[Stockpile] extract_and_post start file={path} out_dir={out_dir} endpoint=stockpile")
    data = extract_pinned_tooltips(path, strip_enum_prefixes=not keep_enum_prefixes)
    extracted_entries = len(data) if isinstance(data, list) else 0
    _runtime_log(f"[Stockpile] extracted entries={extracted_entries}")
    payload = convert_to_api_payload(data, path)
    del data
    current_hash = stable_payload_hash(payload)
    output = default_output_path(path, out_dir)
    sent_output = last_sent_output_path(path, out_dir)
    capture_changed = payload_changed_since_json(payload, output, current_hash)
    api_payload_changed = payload_changed_since_json(payload, sent_output, current_hash)
    _runtime_log(
        "[Stockpile] "
        f"capture_changed={capture_changed} api_payload_changed={api_payload_changed} "
        f"force_api_refresh={force_api_refresh} output={output} last_sent={sent_output}"
    )
    if capture_changed:
        write_json(payload, output, current_hash)
    else:
        _runtime_log("[Stockpile] captured JSON unchanged")

    if not api_payload_changed and not force_api_refresh:
        log_stockpile_debug_details(
            payload,
            source_file=path,
            output=output,
            sent_output=sent_output,
            upload_reason=upload_reason,
            capture_changed=capture_changed,
            api_payload_changed=api_payload_changed,
            extracted_entries=extracted_entries,
            action="skip: same as last sent JSON",
        )
        _runtime_log("[Stockpile] unchanged; API skipped")
        del payload
        gc.collect()
        return None

    report_count = len(payload.get("reports", []))
    log_stockpile_debug_details(
        payload,
        source_file=path,
        output=output,
        sent_output=sent_output,
        upload_reason=upload_reason,
        capture_changed=capture_changed,
        api_payload_changed=api_payload_changed,
        extracted_entries=extracted_entries,
        action="POST to API" if api_payload_changed else "POST to API (forced refresh)",
    )
    _debug_log(f"[Stockpile] posting {report_count} private API reports")
    api_message = post_json(payload, api_url)
    _debug_log(f"[Stockpile] API parsed status={api_message.get('status_text', '-')}")
    write_json(payload, sent_output, current_hash)
    summary = summarize_payload(payload, api_message)
    del api_message
    summary["payload_changed"] = api_payload_changed
    summary["upload_reason"] = upload_reason
    del payload
    gc.collect()
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
        sync_interval: float | None = None,
        discovery_interval: float = 5.0,
        status_callback: Callable[[str | dict[str, Any]], None] | None = None,
    ) -> None:
        self.file_path = file_path
        self.out_dir = out_dir
        self.api_url = api_url
        self.extract_initial = extract_initial
        self.debounce = debounce
        self.interval = interval
        self.sync_interval = sync_interval
        self.discovery_interval = max(interval, discovery_interval)
        self.status_callback = status_callback
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.send_count = 0
        self._cached_candidate_file: Path | None = None
        self._last_discovery_at = 0.0

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
            _runtime_log(
                f"[Stockpile] {message.get('api_response', '-')} | "
                f"{message.get('report_count', 0)} stockpiles | "
                f"{len(message.get('items') or [])} API items"
            )
        else:
            _runtime_log(f"[Stockpile] {message}")
        if self.status_callback:
            self.status_callback(message)

    def _run(self) -> None:
        configured_path = self.file_path.resolve()
        self._status("running")
        watched_path: Path | None = None
        watched_stat: tuple[int, int] | None = None
        pending_path: Path | None = None
        pending_at: float | None = None
        pending_upload_reason = ""
        _debug_log(
            "[Stockpile Watcher] started "
            f"configured_file={configured_path} extract_initial={self.extract_initial}"
        )
        initial_scan_done = False
        if not self._candidate_file():
            _debug_log(f"[Stockpile Watcher] waiting for Foxhole save files in {foxhole_savegames_dir()}")
            self._status(f"waiting for Foxhole save files in: {foxhole_savegames_dir()}")

        while not self.stop_event.is_set():
            now = time.monotonic()
            candidate = self._candidate_file()
            if candidate is None:
                initial_scan_done = True
                if self.stop_event.wait(self.interval):
                    break
                continue

            try:
                resolved = candidate.resolve()
                stat = resolved.stat()
            except FileNotFoundError:
                initial_scan_done = True
                if self.stop_event.wait(self.interval):
                    break
                continue
            except OSError as exc:
                _debug_log(f"[Stockpile Watcher] cannot read file={candidate} error={exc}")
                self._status(f"cannot read Foxhole save file: {candidate}: {exc}")
                initial_scan_done = True
                if self.stop_event.wait(self.interval):
                    break
                continue

            current_stat = (stat.st_mtime_ns, stat.st_size)
            is_new_active_file = watched_path is None or resolved != watched_path
            if is_new_active_file:
                watched_path = resolved
                watched_stat = current_stat
                self.file_path = resolved
                if self.extract_initial or initial_scan_done:
                    pending_path = resolved
                    pending_at = now
                    pending_upload_reason = "startup" if not initial_scan_done else "file_changed"
                _debug_log(
                    "[Stockpile Watcher] tracking latest save "
                    f"file={resolved} size={stat.st_size} mtime_ns={stat.st_mtime_ns}"
                )
                status_prefix = "found newer Foxhole save file" if initial_scan_done else "found Foxhole save file"
                self._status(f"{status_prefix}: {resolved}")
            elif current_stat != watched_stat:
                watched_stat = current_stat
                pending_path = resolved
                pending_at = now
                pending_upload_reason = "file_changed"
                _debug_log(
                    "[Stockpile Watcher] reload detected "
                    f"file={resolved} size={stat.st_size} mtime_ns={stat.st_mtime_ns}"
                )
                self._status(f"reload detected: {resolved.name}")
            initial_scan_done = True

            if pending_path is not None and pending_at is not None and now - pending_at >= self.debounce:
                path = pending_path
                upload_reason = pending_upload_reason
                pending_path = None
                pending_at = None
                pending_upload_reason = ""
                try:
                    _debug_log(f"[Stockpile Watcher] processing reload reason={upload_reason} file={path}")
                    self._status(f"processing reload: {path.name}")
                    result = extract_and_post(
                        path,
                        self.out_dir,
                        self.api_url,
                        upload_reason=upload_reason,
                    )
                    if result is None:
                        self._status(f"stockpile unchanged: {path.name}")
                    else:
                        self.send_count += 1
                        result["send_count"] = self.send_count
                        self._status(result)
                except Exception as exc:
                    self._status(f"error processing {path.name}: {exc}")

            if self.stop_event.wait(self.interval):
                break

    def _candidate_file(self) -> Path | None:
        now = time.monotonic()
        if self._cached_candidate_file is not None and now - self._last_discovery_at < self.discovery_interval:
            return self._cached_candidate_file
        discovered = discover_map_data_file()
        if discovered:
            self._cached_candidate_file = discovered
            self._last_discovery_at = now
            return discovered
        if self.file_path.exists():
            self._cached_candidate_file = self.file_path
            self._last_discovery_at = now
            return self.file_path
        self._cached_candidate_file = None
        self._last_discovery_at = now
        return None


def stockpile_settings_from_env() -> dict[str, Any]:
    return {
        "watch_file": os.getenv("STOCKPILER_WATCH_FILE", str(DEFAULT_WATCH_FILE)),
        "api_url": DEFAULT_API_URL,
        "out_dir": os.getenv("STOCKPILER_OUT_DIR", str(extracted_dir())),
        "enabled": True,
        "extract_initial": True,
    }
