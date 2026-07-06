from __future__ import annotations
from .dict_list_model import DictListModel
from .api_http_error import ApiHttpError
from .auth_ui_error import AuthUiError
import base64
import colorsys
import csv
import ctypes
from datetime import datetime, timezone
import hashlib
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from typing import Any, Callable
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from debug_logging import debug_log, debug_logger
from PySide6.QtNetwork import QNetworkAccessManager
from PySide6.QtCore import (
    QAbstractListModel,
    QMetaObject,
    QModelIndex,
    QObject,
    Property,
    QTimer,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox, QSystemTrayIcon
from app_metadata import APP_TITLE, APP_USER_AGENT, APP_VERSION
from app_paths import extracted_dir, resolve_writable_path, resource_dir, settings_path, user_data_dir
from app_update import UpdateInfo, check_latest_release, download_update, launch_updater
from auto_clicker import ACTION_KEYS, HOTKEYS, MOUSE_BUTTONS, POINT, RECT, AutoClicker
import identify_service
from identify_service import (
    dependencies_status as identify_dependencies_status,
    detect_stockpile_item_regions,
    prepare_detection_template,
    prepare_detection_template_path,
    grab_clipboard_image,
)
from i18n import SUPPORTED_LANGUAGES, Translator, normalize_language
from production_service import (
    CALCULATOR_MENU_DIR,
    CATEGORY_ORDER,
    CATEGORY_RULES,
    MATERIAL_CRATE_SIZES,
    MATERIAL_ICON_PATHS,
    MATERIALS,
    ProductionItem,
    available_categories,
    calculate_queue,
    category_limit,
    discount_multiplier,
    filter_items,
    format_route_materials,
    format_route_orders,
    load_production_items,
    plan_transport_routes,
)
from personalization_store import DEFAULT_THEME_CUSTOM, load_personalization_settings, save_personalization_settings
from settings_store import load_settings, save_settings, selected_language
from secure_store import secure_clear_credentials, secure_load_credentials, secure_save_credentials
from steam_profile import SteamProfile, get_local_steam_profile
from msupp_controller import MSuppController
from stockpiler import (
    DEFAULT_API_URL,
    STOCKPILE_DEBUG_LOG,
    StockpileWatcher,
    api_item_rows,
    api_last_update,
    default_output_path,
    discover_map_data_file,
    extract_and_post,
    format_to_local_pc_time,
    foxhole_savegames_dir,
    last_sent_output_path,
    request_stockpile_debug,
    warehouse_summaries,
)

from .common import *
from .common import _compact_location_key, _location_index, _warehouse_nested, _stockpile_town_code, _first_mapping_text, _location_from_stockpile_code, _location_code_index, _town_code_candidates, _warehouse_text, _strip_hex_suffix

class StockpileController(QObject):
    changed = Signal()
    statusFromWorker = Signal(object)
    visualGroupRowsChanged = Signal()

    def __init__(self, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._running = False
        self._activity_logger: ActivityLogger | None = None
        self._status = "Idle"
        self._last_response = "-"
        self._last_update = "-"
        self._sent_count = 0
        self._report_count = 0
        self._item_count = 0
        self._last_stockpile = "-"
        self._stockpile_list = "-"
        self._debug_visible = False
        self._debug_text = ""
        self._upload_overlay_visible = False
        self._upload_overlay_body = ""
        self._upload_overlay_detail = ""
        self._upload_overlay_accent = "#ffd166"
        self._upload_overlay_title_key = "stockpile.overlay_processing_title"
        self._upload_overlay_progress = 100
        self._visual_items: list[dict[str, Any]] = []
        self._visual_warehouses: list[dict[str, Any]] = []
        self._visual_warehouse = ""
        self._visual_items_by_warehouse: dict[str, list[dict[str, Any]]] = {}
        self._visual_warehouse_lookup: dict[str, dict[str, Any]] = {}
        self._visual_warehouse_options: list[dict[str, Any]] = []
        self._cached_visual_groups: list[dict[str, Any]] = []
        self._watcher: StockpileWatcher | None = None
        self._api_loading = False
        self._upload_overlay_timer = QTimer(self)
        self._upload_overlay_timer.setSingleShot(True)
        self._upload_overlay_timer.timeout.connect(self.dismissUploadOverlay)
        self.logs = DictListModel(["time", "message"], self)
        self.items = DictListModel(["name", "quantity", "category", "icon"], self)
        self.warehouses = DictListModel(["name", "region", "count", "updatedAt"], self)
        self.statusFromWorker.connect(self._handle_status)
        self.refreshDebugSnapshot()


    def setActivityLogger(self, logger: ActivityLogger | None) -> None:
        self._activity_logger = logger

    def _log_activity(
        self,
        action: str,
        *,
        subcategory: str,
        quantity: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not callable(self._activity_logger):
            return
        self._activity_logger("estoque", action, quantity, metadata or {}, subcategory)

    @Property(bool, notify=changed)
    def apiLoading(self) -> bool:
        return getattr(self, "_api_loading", False)

    @Property(float, notify=changed)
    def hudScale(self) -> float:
        return float(self.settings.get("stockpile", {}).get("hud_scale", 1.0))

    @Slot(float)
    def setHudScale(self, value: float) -> None:
        self.settings.setdefault("stockpile", {})["hud_scale"] = value
        save_settings(self.settings)
        self._log_activity("ajustar_hud", subcategory="visual", metadata={"hudScale": float(value)})
        self.changed.emit()

    @Property(bool, notify=changed)
    def running(self) -> bool:
        return self._running

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def lastResponse(self) -> str:
        return self._last_response

    @Property(str, notify=changed)
    def lastUpdate(self) -> str:
        return self._last_update

    @Property(str, notify=changed)
    def watchFile(self) -> str:
        return str(self.settings.get("stockpile", {}).get("watch_file", ""))

    @Property(str, notify=changed)
    def apiUrl(self) -> str:
        return str(self.settings.get("stockpile", {}).get("api_url", DEFAULT_API_URL))

    @Property(str, notify=changed)
    def outDir(self) -> str:
        return str(self.settings.get("stockpile", {}).get("out_dir", str(extracted_dir())))

    @Property(int, notify=changed)
    def sentCount(self) -> int:
        return self._sent_count

    @Property(int, notify=changed)
    def reportCount(self) -> int:
        return self._report_count

    @Property(int, notify=changed)
    def itemCount(self) -> int:
        return self._item_count

    @Property(str, notify=changed)
    def lastStockpile(self) -> str:
        return self._last_stockpile

    @Property(str, notify=changed)
    def stockpileList(self) -> str:
        return self._stockpile_list

    @Property(bool, notify=changed)
    def debugVisible(self) -> bool:
        return self._debug_visible

    @Property(str, notify=changed)
    def debugText(self) -> str:
        return self._debug_text

    @Property(bool, notify=changed)
    def uploadOverlayVisible(self) -> bool:
        return self._upload_overlay_visible

    @Property(str, notify=changed)
    def uploadOverlayBody(self) -> str:
        return self._upload_overlay_body

    @Property(str, notify=changed)
    def uploadOverlayDetail(self) -> str:
        return getattr(self, "_upload_overlay_detail", "")

    @Property(str, notify=changed)
    def uploadOverlayAccent(self) -> str:
        return getattr(self, "_upload_overlay_accent", "#3b82f6")

    @Property(str, notify=changed)
    def uploadOverlayTitleKey(self) -> str:
        return getattr(self, "_upload_overlay_title_key", "stockpile.overlay_processing_title")

    @Property(int, notify=changed)
    def uploadOverlayProgress(self) -> int:
        return getattr(self, "_upload_overlay_progress", 100)

    @Property("QVariantList", notify=changed)
    def warehouseRows(self) -> list[dict[str, Any]]:
        return self.warehouses.items()

    @Property("QVariantList", notify=changed)
    def itemRows(self) -> list[dict[str, Any]]:
        return self.items.items()

    @Property("QVariantList", notify=changed)
    def logRows(self) -> list[dict[str, Any]]:
        return self.logs.items()

    @Property("QVariantList", notify=changed)
    def visualWarehouseOptions(self) -> list[dict[str, Any]]:
        return list(self._visual_warehouse_options)

    @Property(str, notify=changed)
    def visualWarehouse(self) -> str:
        return self._visual_warehouse

    @Property(str, notify=changed)
    def visualWarehouseUpdatedAt(self) -> str:
        if self._visual_warehouse == "__ALL__":
            return "Todos os estoques combinados"
        if self._visual_warehouse.startswith("__REGION__"):
            region = self._visual_warehouse[len("__REGION__"):]
            return f"{region} (Todos os estoques combinados)"
        item = self._visual_warehouse_lookup.get(self._visual_warehouse)
        if item:
            return self._visual_update_label(item)
        return "-"

    @Property(bool, notify=changed)
    def visualWarehouseInactive(self) -> bool:
        item = self._visual_warehouse_lookup.get(self._visual_warehouse)
        return self._depot_state(item) == "inactive" if item else False

    @Property("QVariantList", notify=visualGroupRowsChanged)
    def visualGroupRows(self) -> list[dict[str, Any]]:
        return self._cached_visual_groups

    @Slot()
    def refreshLocalizedTimes(self) -> None:
        if self._visual_warehouses:
            self._visual_warehouse_options = self._build_visual_warehouse_options(self._visual_warehouses)
        self.changed.emit()

    @Slot(str)
    def setVisualWarehouse(self, value: str) -> None:
        value = str(value or "")
        if value == self._visual_warehouse:
            return
        self._visual_warehouse = value
        self._cached_visual_groups = self._visual_groups()
        self._log_activity("selecionar_deposito", subcategory="visual", metadata={"warehouse": value})
        self.visualGroupRowsChanged.emit()
        self.changed.emit()

    @Slot(str)
    def setWatchFile(self, value: str) -> None:
        self.settings.setdefault("stockpile", {})["watch_file"] = value
        save_settings(self.settings)
        self._log_activity("configurar_monitor", subcategory="configuracao", metadata={"field": "watch_file", "fileName": Path(value).name})
        self.refreshDebugSnapshot()
        self.changed.emit()

    @Slot(str)
    def setApiUrl(self, value: str) -> None:
        self.settings.setdefault("stockpile", {})["api_url"] = value
        save_settings(self.settings)
        self._log_activity("configurar_monitor", subcategory="configuracao", metadata={"field": "api_url"})
        self.changed.emit()

    @Slot(str)
    def setOutDir(self, value: str) -> None:
        self.settings.setdefault("stockpile", {})["out_dir"] = value
        save_settings(self.settings)
        self._log_activity("configurar_monitor", subcategory="configuracao", metadata={"field": "out_dir", "folderName": Path(value).name})
        self.refreshDebugSnapshot()
        self.changed.emit()

    @Slot()
    def chooseWatchFile(self) -> None:
        current = Path(self.watchFile)
        start_dir = current.parent if current.parent.exists() else foxhole_savegames_dir()
        path, _selected_filter = QFileDialog.getOpenFileName(
            None,
            APP_TITLE,
            str(start_dir),
            "Foxhole map data (*.sav);;All files (*)",
        )
        if path:
            self.setWatchFile(path)

    @Slot()
    def chooseOutDir(self) -> None:
        current = Path(self.outDir)
        start_dir = current if current.exists() else extracted_dir()
        path = QFileDialog.getExistingDirectory(None, APP_TITLE, str(start_dir))
        if path:
            self.setOutDir(path)

    @Slot()
    def discoverWatchFile(self) -> None:
        discovered = discover_map_data_file()
        if discovered:
            self.setWatchFile(str(discovered))
            self._append_log(f"Discovered save file: {discovered}")
        else:
            self._append_log("No Foxhole map save file found yet.")

    @Slot()
    def start(self) -> None:
        if self._running:
            return
        self._ensure_latest_watch_file()
        self._watcher = StockpileWatcher(
            Path(self.watchFile),
            Path(self.outDir),
            self.apiUrl,
            extract_initial=True,
            status_callback=lambda message: self.statusFromWorker.emit(message),
        )
        self._watcher.start()
        self._running = True
        self.settings.setdefault("stockpile", {})["enabled"] = True
        save_settings(self.settings)
        self._status = "Watcher running"
        self._append_log("Watcher started")
        self._log_activity("iniciar_monitor", subcategory="monitor", metadata={"watchFile": Path(self.watchFile).name, "outDir": Path(self.outDir).name})
        self.refreshDebugSnapshot(emit_changed=False)
        self.changed.emit()

    @Slot()
    def stop(self) -> None:
        self._stop(persist_enabled=True)

    def _stop(self, persist_enabled: bool) -> None:
        if self._watcher:
            self._watcher.stop()
        self._watcher = None
        self._running = False
        if persist_enabled:
            self.settings.setdefault("stockpile", {})["enabled"] = False
            save_settings(self.settings)
        self._status = "Stopped"
        self._append_log("Watcher stopped")
        self._log_activity("parar_monitor", subcategory="monitor", metadata={"persistEnabled": bool(persist_enabled)})
        self.refreshDebugSnapshot(emit_changed=False)
        self.changed.emit()

    @Slot()
    def refreshApiDebug(self) -> None:
        self.refreshApiSnapshot()

    @Slot()
    def refreshApiSnapshot(self) -> None:
        if self._api_loading:
            return
        self._api_loading = True
        self._status = "Fetching stockpiles from API..."
        self._append_log(self._status)
        self._log_activity("atualizar_snapshot", subcategory="api", metadata={"apiUrlConfigured": bool(self.apiUrl)})
        self.changed.emit()

        def worker() -> None:
            try:
                api_response = request_stockpile_debug(self.apiUrl)
                summaries = warehouse_summaries(api_response)
                result = {
                    "kind": "api_snapshot",
                    "api_response": api_response.get("status_text", "-"),
                    "api_last_update": format_to_local_pc_time(api_last_update(api_response)),
                    "warehouse_summaries": summaries,
                    "items": api_item_rows(api_response),
                    "report_count": len(summaries),
                    "stockpiles": [str(item.get("name", "-")) for item in summaries],
                    "send_count": self._sent_count,
                }
                self.statusFromWorker.emit(result)
            except Exception as exc:
                self.statusFromWorker.emit({"kind": "ui_error", "text": f"Stockpile API error: {exc}"})

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def extractOnce(self) -> None:
        self._ensure_latest_watch_file()
        watch_file = Path(self.watchFile)
        out_dir = Path(self.outDir)
        api_url = self.apiUrl
        if not watch_file.exists():
            self.statusFromWorker.emit("manual extract error: no *_MapData.sav file found")
            return
        self._log_activity("extrair_manual", subcategory="monitor", metadata={"watchFile": watch_file.name, "outDir": out_dir.name})

        def worker() -> None:
            try:
                result = extract_and_post(
                    watch_file,
                    out_dir,
                    api_url,
                    force_api_refresh=True,
                    upload_reason="manual",
                )
                if result is None:
                    self.statusFromWorker.emit(f"stockpile unchanged: {watch_file.name}")
                else:
                    self.statusFromWorker.emit(result)
            except Exception as exc:
                self.statusFromWorker.emit(f"manual extract error for {watch_file.name}: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _apply_visual_data(
        self,
        rows: list[dict[str, Any]],
        warehouses: list[dict[str, Any]],
        stockpiles: list[str],
    ) -> None:
        raw_items_by_warehouse: dict[str, list[dict[str, Any]]] = {}
        for item in rows:
            warehouse = str(item.get("warehouse") or "")
            if warehouse:
                raw_items_by_warehouse.setdefault(warehouse, []).append(item)

        enriched_warehouses: list[dict[str, Any]] = []
        self._visual_warehouse_lookup = {}
        for warehouse in warehouses:
            name = str(warehouse.get("name") or "")
            if not name:
                continue
            enriched = dict(warehouse)
            for row in raw_items_by_warehouse.get(name, []):
                if not enriched.get("map_name") and row.get("map_name"):
                    enriched["map_name"] = row.get("map_name")
                if not enriched.get("town") and row.get("town"):
                    enriched["town"] = row.get("town")
                if enriched.get("map_name") and enriched.get("town"):
                    break
            enriched.update(self._warehouse_meta(enriched))
            if not self._is_visual_stockpile_visible(enriched):
                continue
            enriched_warehouses.append(enriched)
            self._visual_warehouse_lookup[name] = enriched

        visible_names = set(self._visual_warehouse_lookup)
        self._visual_items_by_warehouse = {
            name: raw_items_by_warehouse.get(name, [])
            for name in visible_names
        }
        self._visual_items = [
            item
            for item in rows
            if str(item.get("warehouse") or "") in visible_names
        ]
        self._visual_warehouses = enriched_warehouses
        self._visual_warehouse_options = self._build_visual_warehouse_options(enriched_warehouses)

        available = [name for name in stockpiles if name in self._visual_warehouse_lookup] or [
            str(item.get("name") or "") for item in enriched_warehouses
        ]
        available = [name for name in available if name]
        if available and self._visual_warehouse not in self._visual_warehouse_lookup and self._visual_warehouse not in ["__ALL__"] and not self._visual_warehouse.startswith("__REGION__"):
            self._visual_warehouse = available[0]
        elif not available and self._visual_warehouse not in ["__ALL__"] and not self._visual_warehouse.startswith("__REGION__"):
            self._visual_warehouse = ""

        self._cached_visual_groups = self._visual_groups()
        self.visualGroupRowsChanged.emit()

    @staticmethod
    def _warehouse_parts(name: str) -> tuple[str, str, str]:
        parts = [part.strip() for part in str(name or "").split("/") if part.strip()]
        if len(parts) >= 3:
            return parts[0], parts[-2], parts[-1]
        if len(parts) == 2:
            second = parts[1]
            if re.match(r"^[A-Z]{1,4}[-_]", second, re.IGNORECASE):
                return parts[0], "", second
            return parts[0], second, second
        value = parts[0] if parts else "-"
        return "", "", value

    @staticmethod
    def _depot_state(warehouse: dict[str, Any] | None) -> str:
        if not isinstance(warehouse, dict):
            return ""
        return _warehouse_text(warehouse, "depot_state", "DepotState", "depotState", "state", "State").lower()

    @staticmethod
    def _has_gg_stockpile_prefix(warehouse: dict[str, Any]) -> bool:
        name = str(warehouse.get("name") or "")
        _map_part, _town, name_code = StockpileController._warehouse_parts(name)
        candidates = [
            warehouse.get("code"),
            warehouse.get("display_name"),
            warehouse.get("warehouse_name"),
            warehouse.get("stockpile_name"),
            warehouse.get("neme"),
            name_code,
        ]
        return any(str(value or "").strip().upper().startswith("GG-") for value in candidates)

    @classmethod
    def _is_visual_stockpile_visible(cls, warehouse: dict[str, Any]) -> bool:
        return cls._has_gg_stockpile_prefix(warehouse) and cls._depot_state(warehouse) != "lost"

    @staticmethod
    def _warehouse_meta(warehouse: dict[str, Any] | str) -> dict[str, str]:
        if isinstance(warehouse, dict):
            name = str(warehouse.get("name") or "")
            explicit_title = str(
                warehouse.get("display_name")
                or warehouse.get("warehouse_name")
                or warehouse.get("stockpile_name")
                or warehouse.get("neme")
                or ""
            ).strip()
            explicit_map = _warehouse_text(warehouse, "map_name", "MapName", "mapName", "map", "Map", "region", "Region")
            explicit_town = _warehouse_text(warehouse, "town", "Town", "town_name", "TownName", "townName", "location", "Location")
        else:
            name = str(warehouse or "")
            explicit_title = ""
            explicit_map = ""
            explicit_town = ""
        map_part, town, code = StockpileController._warehouse_parts(name)
        lookup_map = explicit_map or map_part
        lookup_town = explicit_town or town
        map_key = _compact_location_key(_strip_hex_suffix(lookup_map))
        matched = _location_index().get((map_key, lookup_town.lower())) if map_key and lookup_town else None
        if not matched:
            matched = _location_from_stockpile_code(map_key, explicit_title, code, name)

        region = str((matched or {}).get("region") or _strip_hex_suffix(lookup_map) or "Outros")
        display_town = str(explicit_town or (matched or {}).get("town") or town)
        map_name = explicit_map or stockpile_map_name(str((matched or {}).get("mapName") or "") or map_part or region)
        place_path = f"{map_name} - {display_town}" if map_name and display_town else map_name or display_town or name
        title = explicit_title or (code if code and code != display_town else name)
        return {
            "region": map_name or region,
            "town": display_town,
            "code": title,
            "mapName": map_name,
            "placePath": place_path,
            "optionSubText": display_town or place_path,
            "groupLabel": map_name or region or place_path,
        }

    @staticmethod
    def _warehouse_option_sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(item.get("groupLabel") or item.get("region") or "").lower(),
            str(item.get("town") or "").lower(),
            str(item.get("code") or item.get("name") or "").lower(),
        )

    def _build_visual_warehouse_options(self, warehouses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for warehouse in sorted(warehouses, key=self._warehouse_option_sort_key):
            group_label = str(warehouse.get("groupLabel") or warehouse.get("placePath") or warehouse.get("region") or "Outros")
            grouped.setdefault(group_label, []).append(warehouse)

        options: list[dict[str, Any]] = []
        translator = Translator(selected_language(self.settings))
        
        options.append({
            "text": "Todos os Estoques",
            "id": "__ALL__",
            "type": "region_header"
        })

        for region in sorted(grouped, key=lambda value: value.lower()):
            options.append({"text": region, "type": "region_header", "id": f"__REGION__{region}"})
            for warehouse in grouped[region]:
                updated_raw = str(warehouse.get("last_update") or warehouse.get("updatedAt") or "")
                inactive = self._depot_state(warehouse) == "inactive"
                options.append(
                    {
                        "text": str(warehouse.get("code") or warehouse.get("name") or "-"),
                        "subText": str(warehouse.get("optionSubText") or warehouse.get("placePath") or ""),
                        "sideText": "" if inactive else format_relative_time(updated_raw, translator),
                        "sideTextKey": "stockpile.visual_depot_inactive_badge" if inactive else "",
                        "sideColor": "#ef4444" if inactive else "",
                        "id": str(warehouse.get("name") or ""),
                        "type": "item",
                    }
                )
        return options

    def _visual_update_label(self, item: dict[str, Any]) -> str:
        updated_raw = str(item.get("last_update") or item.get("updatedAt") or "")
        absolute = format_to_local_pc_time(updated_raw)
        relative = format_relative_time(updated_raw, Translator(selected_language(self.settings)))
        place = str(item.get("placePath") or item.get("name") or "-")
        if absolute and absolute != "-" and relative:
            return f"{place} - {absolute} ({relative})"
        if absolute and absolute != "-":
            return f"{place} - {absolute}"
        return place

    @Slot(object)
    def _handle_status(self, message: object) -> None:
        if isinstance(message, dict):
            if message.get("kind") == "ui_error":
                self._api_loading = False
                self._status = str(message.get("text") or "-")
                self._append_log(self._status)
                self.refreshDebugSnapshot(emit_changed=False)
                self.changed.emit()
                return
            self._sent_count = int(message.get("send_count", self._sent_count) or self._sent_count)
            rows = list(message.get("items") or []) if "items" in message else api_item_rows(message)
            warehouses = (
                list(message.get("warehouse_summaries") or [])
                if "warehouse_summaries" in message
                else warehouse_summaries(message)
            )
            if message.get("kind") == "api_snapshot" and not rows and self._visual_items:
                self._status = "Fetching stockpiles from API..."
                self.refreshDebugSnapshot(emit_changed=False)
                self.changed.emit()
                return
            stockpiles = [str(item.get("name", "-")) for item in warehouses if item.get("name")]
            self._report_count = int(message.get("report_count", len(warehouses)) or len(warehouses))
            self._item_count = len(rows)
            self._last_stockpile = stockpiles[-1] if stockpiles else "-"
            self._stockpile_list = ", ".join(stockpiles[:6]) if stockpiles else "-"
            if len(stockpiles) > 6:
                self._stockpile_list = f"{self._stockpile_list} +{len(stockpiles) - 6}"
            self._apply_visual_data(rows, warehouses, stockpiles)
            
            self._last_response = str(message.get("api_response") or message.get("message") or "OK")
            self._last_update = str(message.get("api_last_update") or api_last_update(message) or now_label())
            if message.get("kind") == "api_snapshot":
                self._status = "API data loaded."
            else:
                self._status = f"{self._report_count} reports, {self._item_count} items"
                if message.get("payload_changed") and self.parent():
                    # Attempt to invoke postStockpileHelp on the chat controller
                    try:
                        app = QApplication.instance()
                        for obj in app.children():
                            if type(obj).__name__ == "ControllerRegistry":
                                obj.chatController.postStockpileHelp("Estoque atualizado")
                                break
                    except Exception:
                        pass
            self._append_log(self._last_response)
            try:
                self.items.set_items(normalize_item_rows(rows))
                self.warehouses.set_items(normalize_warehouses(warehouses))
            except Exception:
                pass
            if "upload_reason" in message:
                quantity = int(message.get("report_count", self._report_count) or 1)
                self._log_activity(
                    "sincronizar_estoque",
                    subcategory="monitor",
                    quantity=max(1, quantity),
                    metadata={
                        "uploadReason": str(message.get("upload_reason") or ""),
                        "reportCount": self._report_count,
                        "itemCount": self._item_count,
                        "stockpileList": self._stockpile_list,
                        "payloadChanged": bool(message.get("payload_changed")),
                    },
                )
                self._show_upload_notification(message)
        else:
            text = str(message)
            self._maybe_update_watch_file_from_status(text)
            self._status = text
            self._append_log(text)
        self._api_loading = False
        self.refreshDebugSnapshot(emit_changed=False)
        self.changed.emit()

    def _append_log(self, message: str) -> None:
        debug_log("stockpile", "log", {"message": message})
        self.logs.append({"time": now_label(), "message": message})
        if self.logs.count() > 200:
            self.logs.set_items(self.logs.items()[-200:])

    @Slot()
    def dismissUploadOverlay(self) -> None:
        if not self._upload_overlay_visible:
            return
        self._upload_overlay_timer.stop()
        self._upload_overlay_visible = False
        self.changed.emit()

    def _show_upload_notification(self, message: dict[str, Any]) -> None:
        app_settings = self.settings.get("app", {})
        clicker_settings = self.settings.get("auto_clicker", {})
        if bool(app_settings.get("stockpile_sound_enabled", True)):
            play_sound("estoque")
        if not bool(clicker_settings.get("overlay_notification_enabled", True)):
            return
            
        response = str(message.get("api_response") or message.get("message") or "OK")
        is_success = response in ("HTTP 200", "OK", "HTTP 201") or response.startswith("HTTP 2")
        count = int(message.get("report_count", self._report_count))
        
        if is_success:
            self._upload_overlay_accent = "#4ef7b2"
            self._upload_overlay_title_key = "stockpile.overlay_processing_title"
            self._upload_overlay_body = f"{count} estoques atualizados com sucesso" if count != 1 else "1 estoque atualizado com sucesso"
            names = self._stockpile_list if self._stockpile_list and self._stockpile_list != "-" else self._last_stockpile
            if names and names != "-":
                self._upload_overlay_detail = f"Atualizados: {names}"
            else:
                self._upload_overlay_detail = "Dados enviados para a nuvem."
            self._upload_overlay_progress = 100
        else:
            self._upload_overlay_accent = "#ff7a90"
            self._upload_overlay_title_key = "update.error_title"
            self._upload_overlay_body = "Falha ao atualizar estoques"
            self._upload_overlay_detail = response
            self._upload_overlay_progress = 0

        self._upload_overlay_visible = True
        self._upload_overlay_timer.start(4500)

    def _ensure_latest_watch_file(self) -> bool:
        latest = self._newer_discovered_watch_file()
        if latest is None:
            return False
        self.settings.setdefault("stockpile", {})["watch_file"] = str(latest)
        save_settings(self.settings)
        self._append_log(f"Using latest Foxhole save file: {latest}")
        self.refreshDebugSnapshot(emit_changed=False)
        self.changed.emit()
        return True

    def _newer_discovered_watch_file(self) -> Path | None:
        discovered = discover_map_data_file()
        if not discovered:
            return None
        current = Path(self.watchFile)
        try:
            if current.exists() and current.resolve() == discovered.resolve():
                return None
        except OSError:
            return discovered
        return discovered

    def _maybe_update_watch_file_from_status(self, message: str) -> None:
        prefixes = ("found newer Foxhole save file: ", "found Foxhole save file: ")
        for prefix in prefixes:
            if not message.startswith(prefix):
                continue
            path = Path(message.removeprefix(prefix).strip())
            if not path.exists():
                return
            self.settings.setdefault("stockpile", {})["watch_file"] = str(path)
            save_settings(self.settings)
            return

    @staticmethod
    def _clean_visual_item_name(item: dict[str, Any]) -> str:
        display_name = str(item.get("display_name") or item.get("asset_name") or item.get("name") or "-").strip()
        suffix = " Crated"
        if display_name.endswith(suffix):
            display_name = display_name[: -len(suffix)].strip()
        return display_name or "-"

    @staticmethod
    def _visual_group_key(item: dict[str, Any]) -> str:
        asset = str(item.get("asset_name") or "").lower()
        display = str(item.get("display_name") or item.get("name") or "").lower()
        icon_name = str(item.get("icon_name") or "").lower()
        category = str(item.get("category") or "").lower()
        icon_source = str(item.get("icon_source") or "").lower()
        priority = str(item.get("priority") or "").lower()
        is_crated = "crated" in display or icon_name.endswith("-crated")
        is_shippable = category in {"shippables", "shippable", "structures"} or icon_source == "structures_shippables"

        if priority and priority not in {"-", "medium", "normal"}:
            return "priority"
        if asset in {"basicmaterials", "bmat", "bmats"} or "basic materials" in display or display in {"bmat", "bmats"}:
            return "starter"
        if asset in {"cloth", "soldiersupplies", "shirts"} or "soldier supplies" in display or "shirts" in display:
            return "starter"
        if asset in {"maintenancesupplies", "msup", "msups"} or "maintenance supplies" in display or "msup" in display:
            return "starter"
        if (
            asset in {"cloth", "soldiersupplies", "maintenancesupplies"}
            or "basic materials" in display
            or "soldier supplies" in display
            or "maintenance supplies" in display
        ):
            return "supplies"
        if category == "vehicle":
            return "vehicle_crates" if is_crated else "vehicles"
        if is_shippable:
            return "shippable_crates" if is_crated else "shippables"
        if category == "utility":
            return "common_logi"
        return "supplies"

    @staticmethod
    def _visual_sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
        display = str(item.get("display_name") or item.get("name") or "").lower()
        asset = str(item.get("asset_name") or "").lower()
        starter_order = 99
        if asset in {"basicmaterials", "bmat", "bmats"} or "basic materials" in display:
            starter_order = 0
        elif asset in {"cloth", "soldiersupplies", "shirts"} or "soldier supplies" in display or "shirts" in display:
            starter_order = 1
        elif asset in {"maintenancesupplies", "msup", "msups"} or "maintenance supplies" in display or "msup" in display:
            starter_order = 2
        return (
            starter_order,
            -int(item.get("quantity", 0) or 0),
            str(item.get("display_name") or item.get("name") or ""),
        )

    def _visual_groups(self) -> list[dict[str, Any]]:
        warehouse = self._visual_warehouse
        
        if warehouse == "__ALL__":
            rows = []
            for item_list in self._visual_items_by_warehouse.values():
                rows.extend(item_list)
        elif warehouse.startswith("__REGION__"):
            region = warehouse[len("__REGION__"):]
            rows = []
            for wh_name, item_list in self._visual_items_by_warehouse.items():
                wh_data = self._visual_warehouse_lookup.get(wh_name, {})
                group_label = str(wh_data.get("groupLabel") or wh_data.get("placePath") or wh_data.get("region") or "Outros")
                if group_label == region:
                    rows.extend(item_list)
        else:
            rows = list(self._visual_items_by_warehouse.get(warehouse, []))

        if warehouse == "__ALL__" or warehouse.startswith("__REGION__"):
            merged_items = {}
            for row in rows:
                key = self._clean_visual_item_name(row)
                if key not in merged_items:
                    merged_items[key] = dict(row)
                else:
                    merged_items[key]["quantity"] = int(merged_items[key].get("quantity") or 0) + int(row.get("quantity") or 0)
            rows = list(merged_items.values())

        positive_rows = [item for item in rows if int(item.get("quantity", 0) or 0) > 0]
        rows = positive_rows or rows
        ordered_keys = [
            "starter",
            "priority",
            "supplies",
            "common_logi",
            "vehicles",
            "vehicle_crates",
            "shippables",
            "shippable_crates",
        ]
        groups: dict[str, list[dict[str, Any]]] = {key: [] for key in ordered_keys}
        for item in rows:
            groups.setdefault(self._visual_group_key(item), []).append(item)

        result: list[dict[str, Any]] = []
        for key in ordered_keys:
            items = sorted(groups.get(key) or [], key=self._visual_sort_key)
            if not items:
                continue
            result.append(
                {
                    "key": key,
                    "titleKey": f"stockpile.group_{key}",
                    "accent": "#8ab4ff" if key in {"starter", "common_logi"} else "#aeb7c2",
                    "items": [self._visual_item_row(item) for item in items],
                }
            )
        return result

    def _visual_item_row(self, item: dict[str, Any]) -> dict[str, Any]:
        icon_path = str(item.get("icon_path") or item.get("icon") or "")
        return {
            "name": self._clean_visual_item_name(item),
            "quantity": int(item.get("quantity", 0) or 0),
            "category": str(item.get("category") or "-"),
            "priority": str(item.get("priority") or "-"),
            "icon": file_url(icon_path) if icon_path and Path(icon_path).exists() else "",
        }

    @Slot()
    def toggleDebug(self) -> None:
        self._debug_visible = not self._debug_visible
        if self._debug_visible:
            self.refreshDebugSnapshot(emit_changed=False)
        self.changed.emit()

    @Slot()
    def refreshDebugSnapshot(self, emit_changed: bool = True) -> None:
        self._debug_text = self._build_debug_snapshot()
        if emit_changed:
            self.changed.emit()

    def _build_debug_snapshot(self) -> str:
        lines = ["[Stockpile diagnostics]"]
        lines.append(f"watcher_alive={self._watcher_alive()} running={self._running}")
        lines.append(f"status={self._status}")
        watch_path = Path(self.watchFile)
        out_dir = resolve_writable_path(self.outDir)
        lines.append(self._file_stat_line("watch_file", watch_path))
        lines.append(f"out_dir={out_dir}")
        lines.append(self._file_stat_line("captured_json", default_output_path(watch_path, out_dir)))
        lines.append(self._file_stat_line("last_sent_json", last_sent_output_path(watch_path, out_dir)))
        discovered = discover_map_data_file()
        lines.append(f"discover_map_data_file={discovered or '-'}")
        save_dir = foxhole_savegames_dir()
        lines.append(f"savegames_dir={save_dir}")
        try:
            candidates = sorted(
                [path for path in save_dir.glob("*_MapData.sav") if path.is_file()],
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
        except OSError as exc:
            lines.append(f"candidates_error={exc}")
            candidates = []
        if not candidates:
            lines.append("candidates=none")
        for index, candidate in enumerate(candidates[:5], 1):
            try:
                marker = " <= watched" if candidate.resolve() == watch_path.resolve() else ""
            except OSError:
                marker = ""
            lines.append(self._file_stat_line(f"candidate_{index}{marker}", candidate))
        lines.append("")
        lines.append("[Recent app log]")
        for row in self.logs._items[-8:]:
            lines.append(f"{row.get('time')} {row.get('message')}")
        lines.append("")
        lines.append("[stockpile_debug.log tail]")
        lines.extend(self._debug_log_tail())
        return "\n".join(lines)

    def _watcher_alive(self) -> bool:
        thread = getattr(self._watcher, "thread", None)
        return bool(self._watcher and thread and thread.is_alive())

    @staticmethod
    def _file_stat_line(label: str, path: Path) -> str:
        try:
            stat = path.stat()
        except OSError as exc:
            return f"{label}: {path} | missing/unreadable ({exc})"
        changed = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return f"{label}: {path} | size={stat.st_size} mtime={changed} mtime_ns={stat.st_mtime_ns}"

    @staticmethod
    def _debug_log_tail(max_lines: int = 24) -> list[str]:
        try:
            lines = STOCKPILE_DEBUG_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return [f"{STOCKPILE_DEBUG_LOG}: missing"]
        return lines[-max_lines:] or ["empty"]

    @Slot()
    def shutdown(self) -> None:
        self._stop(persist_enabled=False)
