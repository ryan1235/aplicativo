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
from .map_coordinates import api_to_map_pixels, map_pixels_to_api, zoom_scale_x, zoom_scale_y


def build_local_tile_url_cache(local_tiles_dir: str) -> dict[tuple[int, int, int], str]:
    """Build a local tile URL cache from the available tile index files in img/tiles."""
    cache: dict[tuple[int, int, int], str] = {}
    if not local_tiles_dir or not os.path.isdir(local_tiles_dir):
        return cache

    def add_tile(z: int, x: int, y: int, relative_path: str | None = None) -> None:
        if z < 0 or x < 0 or y < 0:
            return
        if relative_path:
            relative_path = relative_path.replace("\\", "/")
            if relative_path.startswith("./"):
                relative_path = relative_path[2:]
            path = os.path.join(local_tiles_dir, *relative_path.split("/"))
        else:
            path = os.path.join(local_tiles_dir, str(z), f"{x}_{y}.webp")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            cache[(z, x, y)] = f"file:///{path.replace(chr(92), '/')}"

    tiles_json_path = os.path.join(local_tiles_dir, "tiles.json")
    if os.path.exists(tiles_json_path):
        with open(tiles_json_path, "r", encoding="utf-8") as handle:
            tiles_index = json.load(handle)
        if isinstance(tiles_index, dict):
            for z_str, tiles in tiles_index.items():
                try:
                    z = int(z_str)
                except (TypeError, ValueError):
                    continue
                if isinstance(tiles, list):
                    for tile in tiles:
                        if not isinstance(tile, dict):
                            continue
                        x = int(tile.get("x", -1))
                        y = int(tile.get("y", -1))
                        add_tile(z, x, y, tile.get("file") or tile.get("path"))

    tile_index_path = os.path.join(local_tiles_dir, "tile_index.json")
    if os.path.exists(tile_index_path):
        with open(tile_index_path, "r", encoding="utf-8") as handle:
            tile_index = json.load(handle)
        if isinstance(tile_index, dict):
            for z_str, tiles in tile_index.items():
                try:
                    z = int(z_str)
                except (TypeError, ValueError):
                    continue
                if isinstance(tiles, dict):
                    for tile_key, tile_info in tiles.items():
                        if not isinstance(tile_info, dict):
                            continue
                        x = int(tile_info.get("x", -1))
                        y = int(tile_info.get("y", -1))
                        if x < 0 or y < 0:
                            if isinstance(tile_key, str):
                                parts = tile_key.split("_")
                                if len(parts) == 2:
                                    try:
                                        x = int(parts[0])
                                        y = int(parts[1])
                                    except ValueError:
                                        x = -1
                                        y = -1
                        add_tile(z, x, y, tile_info.get("path") or tile_info.get("file"))

    return cache


class MapController(QObject):
    baseUrlChanged = Signal()
    mapItemsChanged = Signal()
    mapTextItemsChanged = Signal()
    calibrationChanged = Signal()
    visibleItemsChanged = Signal()
    visibleTextItemsChanged = Signal()
    visibleTestItemsChanged = Signal()
    _internalFetchCompleted = Signal(list)
    _internalTestFetchCompleted = Signal(list)
    _internalTextItemsCompleted = Signal(list)
    _internalStockDataCompleted = Signal(dict)
    
    mapDownloadProgress = Signal(int, int, arguments=["current", "total"])
    mapDownloadFinished = Signal()
    mapBakeProgress = Signal(str, int, int, arguments=["stage", "current", "total"])
    mapBakeFinished = Signal()
    mapViewportReady = Signal()
    mapTilesReadyChanged = Signal()
    localTilesAvailableChanged = Signal()
    localTileManifestChanged = Signal()
    _internalBakeProgress = Signal(str, int, int)
    _internalBakeFinished = Signal()
    _internalUnlockAfterLayer = Signal(int)

    def __init__(self, settings_data: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        # Use AppData for map cache so it's not bundled in the build
        import os
        from PySide6.QtCore import QStandardPaths
        
        app_data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        self._map_tiles_root = os.path.join(app_data_dir, "map-tiles")
        self._base_cache_dir = os.path.join(self._map_tiles_root, "patch-64")
        self._cache_dir = self._base_cache_dir
        os.makedirs(self._cache_dir, exist_ok=True)
        
        self._icons_tiles_ready = False
        self._labels_tiles_ready = False
        self._blocking_bake_running = False
        self._background_bake_running = False
        self._map_bake_stage = ""
        self._viewport_gate: threading.Event | None = None
        self._settings = settings_data

        self._local_tiles_dir = os.path.join(str(BASE_DIR), "img", "tiles")
        self._local_tile_manifest: dict[str, Any] | None = None
        self._local_tile_tiles: dict[str, set[tuple[int, int]]] = {}
        self._local_tile_url_cache: dict[tuple[int, int, int], str] = {}
        
        # Initialize map items BEFORE loading local tile manifest (which calls _auto_calibrate_local_map)
        self._map_items = []
        self._test_items = []
        self._map_text_items = []
        self._visible_map_items = []
        self._visible_text_items = []
        self._visible_test_items = []
        self._viewport_center_x = 0.0
        self._viewport_center_y = 0.0
        self._viewport_width = 1920.0
        self._viewport_height = 1080.0
        self._viewport_zoom = 2
        self._map_scale = 1.0
        self._map_offset_x = 0.0
        self._map_offset_y = 0.0
        
        self._load_local_tile_manifest()
        
        self._refresh_tile_urls()
        self._fallback_url = "https://foxlogi.com/map-tiles/patch-64/{z}/{x}/{y}.webp"

        self._internalFetchCompleted.connect(self._updateMapItems)
        self._internalTestFetchCompleted.connect(self._updateTestItems)
        self._internalTextItemsCompleted.connect(self._updateTextItems)
        self._internalStockDataCompleted.connect(self._on_stock_data_completed)
        self._internalBakeProgress.connect(self._on_bake_progress)
        self._internalBakeFinished.connect(self._on_bake_finished)
        self._internalUnlockAfterLayer.connect(self._on_unlock_after_layer)
        
        # Start fetching with optimized sequencing to reduce memory spike
        # Prioritize map items first, then labels, then stock data
        QTimer.singleShot(100, self.fetchMapItems)

    def _read_api_cache(self, filename: str, max_age_hours: float):
        import os, json, time
        cache_path = os.path.join(os.path.dirname(self._cache_dir), 'api_cache', filename)
        if os.path.exists(cache_path):
            if (time.time() - os.path.getmtime(cache_path)) < (max_age_hours * 3600):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    pass
        return None

    def _write_api_cache(self, filename: str, data: list):
        import os, json
        cache_dir = os.path.join(os.path.dirname(self._cache_dir), 'api_cache')
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, filename)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass

    @Property(str, notify=baseUrlChanged)
    def baseUrl(self) -> str:
        return self._base_url

    @baseUrl.setter
    def baseUrl(self, value: str) -> None:
        if self._base_url != value:
            self._base_url = value
            self._settings.setdefault("map", {})["base_url"] = value
            save_settings(self._settings)
            self.baseUrlChanged.emit()
            
    @Property(str, constant=True)
    def fallbackUrl(self) -> str:
        return self._fallback_url

    @Property(bool, notify=localTilesAvailableChanged)
    def localTilesAvailable(self) -> bool:
        return self._local_tile_manifest is not None

    @Property(int, notify=localTileManifestChanged)
    def localTileSize(self) -> int:
        if self._local_tile_manifest is None:
            return 256
        return int(self._local_tile_manifest.get("tileSize", 256))

    @Property(int, notify=localTileManifestChanged)
    def localMaxZoom(self) -> int:
        if self._local_tile_manifest is None:
            return 6
        levels = self._local_tile_manifest.get("levels", {})
        if not levels:
            return 6
        return max(int(z) for z in levels.keys())

    @Property(str, notify=mapTilesReadyChanged)
    def labelsBaseUrl(self) -> str:
        local_path = self._cache_dir.replace("\\", "/")
        return f"file:///{local_path}/{{z}}/{{x}}/{{y}}.webp"

    @Property(bool, notify=mapTilesReadyChanged)
    def iconsTilesReady(self) -> bool:
        return self._icons_tiles_ready

    @Property(bool, notify=mapTilesReadyChanged)
    def labelsTilesReady(self) -> bool:
        return self._labels_tiles_ready

    @Property(bool, notify=mapBakeProgress)
    def isBlockingBake(self) -> bool:
        return self._blocking_bake_running

    @Property(bool, notify=mapBakeProgress)
    def isBackgroundBake(self) -> bool:
        return self._background_bake_running

    @Property(bool, notify=mapBakeProgress)
    def isMapBaking(self) -> bool:
        return self._blocking_bake_running

    @Property(str, notify=mapBakeProgress)
    def mapBakeStage(self) -> str:
        return self._map_bake_stage

    def _load_local_tile_manifest(self) -> None:
        import json
        import os
        try:
            self._local_tile_tiles = {}
            self._local_tile_url_cache = {}
            manifest_path = os.path.join(self._local_tiles_dir, "manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, "r", encoding="utf-8") as f:
                    self._local_tile_manifest = json.load(f)
            else:
                self._local_tile_manifest = None

            if self._local_tile_manifest is not None:
                self._local_tile_url_cache = build_local_tile_url_cache(self._local_tiles_dir)
                self._local_tile_tiles = {}
                for (z, x, y) in self._local_tile_url_cache.keys():
                    z_str = str(z)
                    self._local_tile_tiles.setdefault(z_str, set()).add((x, y))
        except Exception as e:
            print(f"[MapController] Failed to load local tile manifest: {e}")
            self._local_tile_manifest = None
            self._local_tile_tiles = {}
            self._local_tile_url_cache = {}
        self.localTilesAvailableChanged.emit()
        self.localTileManifestChanged.emit()
        self._apply_local_map_calibration()

    def _get_zoom_scale_x(self, z: int) -> float:
        return zoom_scale_x(z, self._local_tile_manifest, self.getLocalTileLevelWidth)

    def _get_zoom_scale_y(self, z: int) -> float:
        return zoom_scale_y(z, self._local_tile_manifest, self.getLocalTileLevelHeight)

    @Slot(int, result=float)
    def getMapZoomScaleX(self, z: int) -> float:
        return self._get_zoom_scale_x(z)

    @Slot(int, result=float)
    def getMapZoomScaleY(self, z: int) -> float:
        return self._get_zoom_scale_y(z)

    @Slot(float, float, int, result=float)
    def apiToMapPixelX(self, api_x: float, api_y: float, zoom: int) -> float:
        sx = self._get_zoom_scale_x(zoom)
        sy = self._get_zoom_scale_y(zoom)
        px, _ = api_to_map_pixels(
            api_x, api_y, zoom, self._map_scale, self._map_offset_x, self._map_offset_y, sx, sy
        )
        return px

    @Slot(float, float, int, result=float)
    def apiToMapPixelY(self, api_x: float, api_y: float, zoom: int) -> float:
        sx = self._get_zoom_scale_x(zoom)
        sy = self._get_zoom_scale_y(zoom)
        _, py = api_to_map_pixels(
            api_x, api_y, zoom, self._map_scale, self._map_offset_x, self._map_offset_y, sx, sy
        )
        return py

    @Slot(float, float, int, result=float)
    def mapPixelToApiX(self, px: float, py: float, zoom: int) -> float:
        sx = self._get_zoom_scale_x(zoom)
        sy = self._get_zoom_scale_y(zoom)
        api_x, _ = map_pixels_to_api(
            px, py, zoom, self._map_scale, self._map_offset_x, self._map_offset_y, sx, sy
        )
        return api_x

    @Slot(float, float, int, result=float)
    def mapPixelToApiY(self, px: float, py: float, zoom: int) -> float:
        sx = self._get_zoom_scale_x(zoom)
        sy = self._get_zoom_scale_y(zoom)
        _, api_y = map_pixels_to_api(
            px, py, zoom, self._map_scale, self._map_offset_x, self._map_offset_y, sx, sy
        )
        return api_y

    def _apply_local_map_calibration(self) -> None:
        """Calibração manual via painel de debug — sem auto-ajuste."""
        pass

    def _refresh_tile_urls(self) -> None:
        from map_tile_baker import MapTileBaker

        baker = MapTileBaker(self._map_tiles_root, BASE_DIR)
        self._icons_tiles_ready = baker.icons_ready()
        self._labels_tiles_ready = baker.labels_ready()
        local_path = self._cache_dir.replace("\\", "/")
        self._base_url = f"file:///{local_path}/{{z}}/{{x}}/{{y}}.webp"
        self.baseUrlChanged.emit()
        self.mapTilesReadyChanged.emit()

    def _auto_calibrate_local_map(self) -> None:
        self._apply_local_map_calibration()

    @Slot(str, int, int)
    def _on_bake_progress(self, stage: str, current: int, total: int) -> None:
        self._map_bake_stage = stage
        if stage.endswith("_background"):
            self._background_bake_running = True
        self.mapBakeProgress.emit(stage, current, total)

    @Slot()
    def _on_bake_finished(self) -> None:
        self._blocking_bake_running = False
        self._background_bake_running = False
        self._map_bake_stage = ""
        self._refresh_tile_urls()
        self.mapBakeFinished.emit()

    @Slot(int)
    def _on_unlock_after_layer(self, layer: int) -> None:
        """Libera o mapa após cada camada prioritária (viewport)."""
        self._blocking_bake_running = False
        self._refresh_tile_urls_quiet()
        if layer == 1:
            self.mapViewportReady.emit()
        if self._viewport_gate is not None:
            self._viewport_gate.set()

    def _wait_for_viewport_unlock(self) -> None:
        if self._viewport_gate is None:
            return
        self._viewport_gate.clear()
        self._internalUnlockAfterLayer.emit(self._pending_unlock_layer)
        self._viewport_gate.wait(timeout=120)

    @Slot()
    def checkAndGenerateBakedTiles(self) -> None:
        # We no longer bake tiles as both Icons and Text are rendered dynamically via C++ engine (MapIconsRenderer & MapTextRenderer).
        self.mapBakeProgress.emit("prepare", 1, 1)
        self._map_bake_stage = ""
        self._refresh_tile_urls()
        self.mapViewportReady.emit()
        self._internalBakeFinished.emit()

    def _run_staged_labels_only(self) -> None:
        """Gera só a camada de nomes quando ícones já existem."""
        QMetaObject.invokeMethod(self, "_on_bake_finished", Qt.ConnectionType.QueuedConnection)

    def _run_background_labels_bake(self) -> None:
        self._run_staged_labels_only()

    def _run_incremental_icon_update(self) -> None:
        QMetaObject.invokeMethod(self, "_refresh_tile_urls_quiet", Qt.ConnectionType.QueuedConnection)

    @Slot()
    def _refresh_tile_urls_quiet(self) -> None:
        from map_tile_baker import MapTileBaker

        baker = MapTileBaker(self._map_tiles_root, BASE_DIR)
        self._icons_tiles_ready = baker.icons_ready()
        self._labels_tiles_ready = baker.labels_ready()
        self.mapTilesReadyChanged.emit()

    @Slot(int, int, int, result=str)
    def getLabelsTileUrl(self, z: int, x: int, y: int) -> str:
        import os
        if not self._labels_tiles_ready:
            return ""
        tile_dir = os.path.join(self._cache_dir, str(z), str(x))
        file_path = os.path.join(tile_dir, f"{y}.webp")
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return f"file:///{file_path.replace(chr(92), '/')}"
        return ""

    @Slot(int, result=int)
    def getLocalTileCols(self, z: int) -> int:
        if self._local_tile_manifest is None:
            return 0
        level = self._local_tile_manifest.get("levels", {}).get(str(z))
        if not level:
            return 0
        return int(level.get("cols", 0))

    @Slot(int, result=int)
    def getLocalTileRows(self, z: int) -> int:
        if self._local_tile_manifest is None:
            return 0
        level = self._local_tile_manifest.get("levels", {}).get(str(z))
        if not level:
            return 0
        return int(level.get("rows", 0))

    @Slot(int, result=int)
    def getLocalTileLevelWidth(self, z: int) -> int:
        if self._local_tile_manifest is None:
            return 0
        level = self._local_tile_manifest.get("levels", {}).get(str(z))
        if not level:
            return 0
        return int(level.get("width", 0))

    @Slot(int, result=int)
    def getLocalTileLevelHeight(self, z: int) -> int:
        if self._local_tile_manifest is None:
            return 0
        level = self._local_tile_manifest.get("levels", {}).get(str(z))
        if not level:
            return 0
        return int(level.get("height", 0))

    @Slot(int, int, int, result=str)
    def getLocalTileUrl(self, z: int, x: int, y: int) -> str:
        return self._local_tile_url_cache.get((z, x, y), "")

    @Property(list, notify=mapItemsChanged)
    def mapItemsModel(self) -> list:
        return self._map_items

    @Property(list, notify=mapTextItemsChanged)
    def mapTextItemsModel(self) -> list:
        return self._map_text_items

    @Property(list, notify=mapItemsChanged)
    def testItemsModel(self) -> list:
        return self._test_items

    # --- Viewport-filtered models (only items visible on screen) ---
    @Property(list, notify=visibleItemsChanged)
    def visibleMapItemsModel(self) -> list:
        return self._visible_map_items

    @Property(list, notify=visibleTextItemsChanged)
    def visibleMapTextItemsModel(self) -> list:
        return self._visible_text_items

    @Property(list, notify=visibleTestItemsChanged)
    def visibleTestItemsModel(self) -> list:
        return self._visible_test_items

    @Slot(float, float, float, float, int)
    def updateViewport(self, centerX: float, centerY: float, viewW: float, viewH: float, zoom: int) -> None:
        """Called from QML when the viewport changes. Recalculates visible models."""
        self._viewport_center_x = centerX
        self._viewport_center_y = centerY
        self._viewport_width = viewW
        self._viewport_height = viewH
        self._viewport_zoom = zoom
        self._recalculate_visible_items()

    def _recalculate_visible_items(self) -> None:
        """Filter all item lists to only include items within the current viewport + margin."""
        zoom = self._viewport_zoom
        sx = self._get_zoom_scale_x(zoom)
        sy = self._get_zoom_scale_y(zoom)
        cx = self._viewport_center_x
        cy = self._viewport_center_y
        half_w = self._viewport_width / 2.0
        half_h = self._viewport_height / 2.0
        margin = 300.0

        vp_left = cx - half_w - margin
        vp_right = cx + half_w + margin
        vp_top = cy - half_h - margin
        vp_bottom = cy + half_h + margin

        scale = self._map_scale
        off_x = self._map_offset_x
        off_y = self._map_offset_y

        new_visible = []
        for item in self._map_items:
            ix = item.get('x', 0.0)
            iy = item.get('y', 0.0)
            wpx, wpy = api_to_map_pixels(ix, iy, zoom, scale, off_x, off_y, sx, sy)
            if vp_left <= wpx <= vp_right and vp_top <= wpy <= vp_bottom:
                new_visible.append(item)
            elif item.get('stock') is not None:
                new_visible.append(item)
        if new_visible != self._visible_map_items:
            self._visible_map_items = new_visible
            self.visibleItemsChanged.emit()

        # Filter text items (labels)
        new_text = []
        for item in self._map_text_items:
            ix = item.get('x', 0.0)
            iy = item.get('y', 0.0)
            wpx, wpy = api_to_map_pixels(ix, iy, zoom, scale, off_x, off_y, sx, sy)
            if vp_left <= wpx <= vp_right and vp_top <= wpy <= vp_bottom:
                new_text.append(item)
        if new_text != self._visible_text_items:
            self._visible_text_items = new_text
            self.visibleTextItemsChanged.emit()

        new_test = []
        for item in self._test_items:
            ix = item.get('x', 0.0)
            iy = item.get('y', 0.0)
            wpx, wpy = api_to_map_pixels(ix, iy, zoom, scale, off_x, off_y, sx, sy)
            if vp_left <= wpx <= vp_right and vp_top <= wpy <= vp_bottom:
                new_test.append(item)
        if new_test != self._visible_test_items:
            self._visible_test_items = new_test
            self.visibleTestItemsChanged.emit()
        
    @Slot()
    def fetchStockData(self) -> None:
        import urllib.request
        import json
        import threading

        def _fetch():
            try:
                url = "https://felblogi.discloud.app/data"
                headers = {
                    "X-API-Key": "AIza7m3-iCHSlTbLDavZkAM-6Gv0zRClL30XbRS",
                    "Content-Type": "application/json"
                }
                data = json.dumps({"mode": "debug"}).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers, method='GET')
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                
                stock_list = res_data.get('data', [])
                
                # Group by map_name and town, then by warehouse
                grouped = {}
                for item in stock_list:
                    w = item.get('warehouse', {})
                    map_name = w.get('map_name')
                    town = w.get('town')
                    
                    if not map_name or not town:
                        continue
                        
                    key = f"{map_name}|{town}"
                    if key not in grouped:
                        grouped[key] = {}
                        
                    warehouse_name = item.get("WarehouseName", "Unknown")
                    last_update = item.get("WarehouseLastUpdate", "")
                    if warehouse_name not in grouped[key]:
                        grouped[key][warehouse_name] = {
                            "warehouse_name": warehouse_name,
                            "last_update": last_update,
                            "items": []
                        }
                    
                    icon_name_raw = str(item.get('icon_name', ''))
                    icon_name = icon_name_raw.replace("-crated", "")
                    
                    if not hasattr(self, '_db_icon_map'):
                        import sqlite3
                        try:
                            with sqlite3.connect(BASE_DIR / "update64.db") as db:
                                tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%iconobject_path%'").fetchall()
                                self._db_icon_map = {}
                                for (t,) in tables:
                                    for row in db.execute(f"SELECT id, iconobject_path FROM {t} WHERE iconobject_path IS NOT NULL").fetchall():
                                        self._db_icon_map[row[0].lower()] = row[1]
                        except Exception as e:
                            print(f"[MapController] Failed to load update64.db icon map: {e}")
                            self._db_icon_map = {}

                    final_icon_url = ""
                    db_path = self._db_icon_map.get(icon_name.lower())
                    if db_path:
                        # e.g. "War/Content/Textures/UI/VehicleIcons/AAAmmoIcon.0"
                        local_path = db_path.replace("War/Content/", "Content/").replace(".0", ".png")
                        abs_path = BASE_DIR / local_path
                        if abs_path.exists():
                            final_icon_url = file_url(abs_path)
                    
                    grouped[key][warehouse_name]["items"].append({
                        "name": item.get("DisplayName", "-"),
                        "quantity": item.get("Quantity", 0),
                        "icon": final_icon_url,
                        "category": item.get("CategoryName", "-")
                    })
                
                final_grouped = {}
                for key, wh_dict in grouped.items():
                    final_grouped[key] = list(wh_dict.values())
                
                print(f"[MapController] fetchStockData parsed {len(final_grouped)} stockpiles")
                # Run on main thread safely
                self._internalStockDataCompleted.emit(final_grouped)
            except Exception as e:
                print(f"[MapController] Error fetching stock data: {e}")

        threading.Thread(target=_fetch, daemon=True).start()

    @Slot(str)
    def copyTextToClipboard(self, text: str) -> None:
        from PySide6.QtGui import QGuiApplication
        cb = QGuiApplication.clipboard()
        if cb:
            cb.setText(text)

    @Property(float, notify=calibrationChanged)
    def mapScale(self) -> float:
        return self._map_scale

    @mapScale.setter
    def mapScale(self, value: float) -> None:
        if self._map_scale != value:
            self._map_scale = value
            self.calibrationChanged.emit()



    @Property(float, notify=calibrationChanged)
    def mapOffsetX(self) -> float:
        return self._map_offset_x

    @mapOffsetX.setter
    def mapOffsetX(self, value: float) -> None:
        if self._map_offset_x != value:
            self._map_offset_x = value
            self.calibrationChanged.emit()

    @Property(float, notify=calibrationChanged)
    def mapOffsetY(self) -> float:
        return self._map_offset_y

    @mapOffsetY.setter
    def mapOffsetY(self, value: float) -> None:
        if self._map_offset_y != value:
            self._map_offset_y = value
            self.calibrationChanged.emit()

    @Slot()
    def fetchOfficialMapLabels(self) -> None:
        import urllib.request
        import json
        import threading
        import concurrent.futures
        import os

        def _fetch():
            cached = self._read_api_cache('official_labels.json', max_age_hours=24.0)
            if cached:
                import time
                time.sleep(0.2)
                self._internalTextItemsCompleted.emit(cached)
                return
                
            try:
                # 1. Load exact Hex Origins mapping
                origins_file = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'origins.json'))
                with open(origins_file, 'r', encoding='utf-8') as f:
                    HEX_ORIGINS = json.load(f)
                    
                # 2. Fetch official maps
                maps_req = urllib.request.Request("https://war-service-live.foxholeservices.com/api/worldconquest/maps", headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(maps_req) as response:
                    maps = json.loads(response.read().decode())

                SCALE_X = 25.553590845600255
                SCALE_Y = -22.32744119202343
                
                final_text_items = []
                
                def process_hex(m):
                    try:
                        req = urllib.request.Request(f'https://war-service-live.foxholeservices.com/api/worldconquest/maps/{m}/static', headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req) as response:
                            data = json.loads(response.read().decode())
                            
                            # Use exact pre-calculated median origin
                            origin = HEX_ORIGINS.get(m)
                            if not origin:
                                return []
                            origin_x, origin_y = origin[0], origin[1]
                            
                            items = []
                            
                            # Add the Hex Name itself at the center (0.5, 0.5)
                            import re
                            hex_display_name = re.sub(r'(?<!^)(?=[A-Z])', ' ', m.replace("Hex", ""))
                            items.append({
                                "text": hex_display_name,
                                "x": origin_x + (0.5 * SCALE_X),
                                "y": origin_y + (0.5 * SCALE_Y),
                                "mapMarkerType": "Hex"
                            })
                            
                            for text_item in data.get('mapTextItems', []):
                                lx, ly = text_item.get('x', 0), text_item.get('y', 0)
                                gx = origin_x + (lx * SCALE_X)
                                gy = origin_y + (ly * SCALE_Y)
                                
                                items.append({
                                    "text": text_item.get("text", ""),
                                    "x": gx,
                                    "y": gy,
                                    "mapMarkerType": text_item.get("mapMarkerType", "Minor")
                                })
                            return items
                    except Exception:
                        pass
                    return []

                # Fetch all hexes concurrently (reduced workers to avoid rate limits)
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    results = executor.map(process_hex, maps)
                    for r in results:
                        final_text_items.extend(r)
                        
                self._write_api_cache('official_labels.json', final_text_items)
                self._internalTextItemsCompleted.emit(final_text_items)

            except Exception as e:
                print(f"Error fetching official map labels: {e}")
                
        threading.Thread(target=_fetch, daemon=True).start()

    @Slot()
    def fetchMapItems(self) -> None:
        import urllib.request
        import json
        import threading
        
        def _fetch():
            cached = self._read_api_cache('map_items.json', max_age_hours=24.0)
            if cached:
                import time
                time.sleep(0.2)
                self._internalFetchCompleted.emit(cached)
                return
                
            try:
                req = urllib.request.Request("https://foxlogi.com/api/map-items/", headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                    
                    unique_data = []
                    seen_names = set()
                    
                    for item in data:
                        unique_data.append(item)
                        
                    self._write_api_cache('map_items.json', unique_data)
                    self._internalFetchCompleted.emit(unique_data)
            except Exception as e:
                print(f"Error fetching map items: {e}")
                
        threading.Thread(target=_fetch, daemon=True).start()

    @Slot()
    def fetchTestData(self) -> None:
        import urllib.request
        import json
        import threading
        import csv
        import os
        
        def _fetch():
            cached = self._read_api_cache('test_data.json', max_age_hours=1.0)
            if cached:
                import time
                time.sleep(0.2)
                self._internalTestFetchCompleted.emit(cached)
                return
                
            try:
                # Build lookup from Foxlogi map items
                loc_map = {}
                # Force fetch if empty so the user doesn't have to click the other button first
                items_to_check = self._map_items
                if not items_to_check:
                    try:
                        map_req = urllib.request.Request("https://foxlogi.com/api/map-items/", headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(map_req) as map_res:
                            items_to_check = json.loads(map_res.read().decode())
                    except Exception:
                        pass
                        
                for m_item in items_to_check:
                    name = m_item.get("name")
                    if name:
                        if name not in loc_map:
                            loc_map[name] = {}
                        loc_map[name][m_item.get("type")] = (m_item.get("x", 0), m_item.get("y", 0))
                
                req = urllib.request.Request(
                    "https://felblogi.discloud.app/data",
                    data=b'{"mode": "debug"}',
                    headers={'Content-Type': 'application/json', 'X-API-Key': 'AIza7m3-iCHSlTbLDavZkAM-6Gv0zRClL30XbRS'},
                    method='GET'
                )
                with urllib.request.urlopen(req) as response:
                    raw_data = json.loads(response.read().decode())
                    
                    warehouses = {}
                    for item in raw_data.get("data", []):
                        wh = item.get("warehouse", {})
                        wh_name = item.get("WarehouseName", "Unknown")
                        town_name = wh.get("town", "").strip()
                        
                        # Find the best coordinate for the warehouse type
                        real_coords = None
                        if town_name in loc_map:
                            town_types = loc_map[town_name]
                            # Try Seaport (52), Storage Depot (33, 51), or fallback to whatever exists
                            if 52 in town_types:
                                real_coords = town_types[52]
                            elif 33 in town_types:
                                real_coords = town_types[33]
                            elif 51 in town_types:
                                real_coords = town_types[51]
                            else:
                                # Just pick the first available if exact depot isn't found
                                real_coords = next(iter(town_types.values()))
                        
                        if wh_name not in warehouses:
                            if real_coords:
                                final_x, final_y = real_coords
                            else:
                                # Fallback
                                final_x = wh.get("x", 0) * 150
                                final_y = -wh.get("y", 0) * 150
                                
                            warehouses[wh_name] = {
                                "name": wh_name,
                                "x": final_x,
                                "y": final_y,
                                "items": []
                            }
                        
                        qty = item.get("Quantity", 0)
                        if qty > 0:
                            warehouses[wh_name]["items"].append(f"{qty}x {item.get('DisplayName', 'Unknown')}")
                    
                    result_list = list(warehouses.values())
                    self._write_api_cache('test_data.json', result_list)
                    self._internalTestFetchCompleted.emit(result_list)
            except Exception as e:
                print(f"Error fetching test items: {e}")
                
        threading.Thread(target=_fetch, daemon=True).start()

    @Slot(list)
    def _updateMapItems(self, data: list) -> None:
        if getattr(self, '_raw_map_items', None) == data:
            return  # No changes in API, skip expensive rebuild
        self._raw_map_items = list(data)
        
        self._map_items = data
        self._auto_calibrate_local_map()
        self._merge_stock_data()
        self.mapItemsChanged.emit()
        self._recalculate_visible_items()
        # Chain next fetches after map items loaded to reduce memory spike
        QTimer.singleShot(500, self.fetchOfficialMapLabels)
        QTimer.singleShot(700, self.fetchStockData)

    @Slot(list)
    def _updateTestItems(self, data: list) -> None:
        self._test_items = []
        self.mapItemsChanged.emit()
        self._test_items = data
        self.mapItemsChanged.emit()
        self._recalculate_visible_items()

    @Slot(dict)
    def _on_stock_data_completed(self, stock_dict: dict) -> None:
        print(f"[MapController] _on_stock_data_completed called with {len(stock_dict)} groups")
        self._last_stock_dict = stock_dict
        self._merge_stock_data()
        
    def _merge_stock_data(self):
        if not hasattr(self, '_last_stock_dict') or not self._last_stock_dict:
            print("[MapController] _merge_stock_data skipped: no stock dict")
            return
        if not getattr(self, '_map_items', None) or not getattr(self, '_map_text_items', None):
            print(f"[MapController] _merge_stock_data skipped: _map_items={len(getattr(self, '_map_items', []))}, text={len(getattr(self, '_map_text_items', []))}")
            return
            
        updated_items = list(self._map_items)
        for item in updated_items:
            item.pop('stock', None)
            
        matched_count = 0
        
        for api_key, stock_data in self._last_stock_dict.items():
            api_town = api_key.split('|')[-1].strip().lower()
            
            town_tx, town_ty = None, None
            for text_item in self._map_text_items:
                if text_item.get('mapMarkerType') in ('Major', 'Minor'):
                    if text_item.get('text', '').strip().lower() == api_town:
                        town_tx = text_item.get('x', 0.0)
                        town_ty = text_item.get('y', 0.0)
                        break
                        
            if town_tx is None or town_ty is None:
                continue
                
            best_p1 = None
            best_p1_dist = float('inf')
            
            best_p2 = None
            best_p2_dist = float('inf')
            
            for item in updated_items:
                ix = item.get('x', 0.0)
                iy = item.get('y', 0.0)
                dx = ix - town_tx
                dy = iy - town_ty
                dist = dx*dx + dy*dy
                
                # Limit radius so we don't match cross-map structures
                if dist > 350000:
                    continue
                    
                iconType = str(item.get('type', ''))
                if iconType in ('33', '52', '88'):
                    if dist < best_p1_dist:
                        best_p1_dist = dist
                        best_p1 = item
                elif iconType in ('53', '54', '56', '57', '58', '29', '45', '46', '47', '27', '35', '50', '55'):
                    if dist < best_p2_dist:
                        best_p2_dist = dist
                        best_p2 = item
                        
            if best_p1 is not None:
                best_p1['stock'] = stock_data
                matched_count += 1
            elif best_p2 is not None:
                best_p2['stock'] = stock_data
                matched_count += 1

        print(f"[MapController] _merge_stock_data finished: matched {matched_count} depots")
        self._map_items = updated_items
        self.mapItemsChanged.emit()
        self._recalculate_visible_items()

    @Slot('QVariant', 'QVariant', 'QVariant', 'QVariant', 'QVariant', 'QVariant', result="QVariant")
    def calculateArtillery(self, startX, startY, endX, endY, windDir=0.0, windTier=0.0) -> dict:
        try:
            from foxmap.geo.artillery import ArtilleryCalculator
            calc = ArtilleryCalculator()
            sx = float(startX) if startX is not None else 0.0
            sy = float(startY) if startY is not None else 0.0
            ex = float(endX) if endX is not None else 0.0
            ey = float(endY) if endY is not None else 0.0
            wd = float(windDir) if windDir is not None else 0.0
            wt = int(float(windTier)) if windTier is not None else 0
            solution = calc.calculate((sx, sy), (ex, ey), wd, wt)
            return {
                "distance_meters": solution.distance_meters,
                "distance_hexes": solution.distance_hexes,
                "bearing": solution.bearing,
                "aim_x": solution.aim_x,
                "aim_y": solution.aim_y
            }
        except Exception as e:
            print(f"[MapController] Error in calculateArtillery: {e}")
            return {}

    @Slot(list)
    def _updateTextItems(self, data: list) -> None:
        self._map_text_items = []
        self.mapTextItemsChanged.emit()
        self._map_text_items = data
        self._merge_stock_data()
        self.mapTextItemsChanged.emit()
        self._recalculate_visible_items()

    @Slot(int, int, int, result=str)
    def getTileUrl(self, z: int, x: int, y: int) -> str:
        local_url = self.getLocalTileUrl(z, x, y)
        if local_url:
            return local_url

        import os
        from map_tile_baker import ICON_BAKE_ZOOMS

        if self._icons_tiles_ready and z in ICON_BAKE_ZOOMS:
            tile_dir = os.path.join(self._cache_dir, str(z), str(x))
            file_path = os.path.join(tile_dir, f"{y}.webp")
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return f"file:///{file_path.replace(chr(92), '/')}"

        legacy_dir = os.path.join(self._map_tiles_root, "patch-64", str(z), str(x))
        legacy_path = os.path.join(legacy_dir, f"{y}.webp")
        if os.path.exists(legacy_path) and os.path.getsize(legacy_path) > 0:
            return f"file:///{legacy_path.replace(chr(92), '/')}"

        return self._fallback_url.format(z=z, x=x, y=y)

    @Slot(int, int, int)
    def cacheTile(self, z: int, x: int, y: int) -> None:
        import os
        import urllib.request
        import threading
        
        def _download_and_save():
            tile_dir = os.path.join(self._cache_dir, str(z), str(x))
            os.makedirs(tile_dir, exist_ok=True)
            file_path = os.path.join(tile_dir, f"{y}.webp")
            
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return
                
            try:
                url = self._fallback_url.format(z=z, x=x, y=y)
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = response.read()
                    if data:
                        with open(file_path, 'wb') as f:
                            f.write(data)
            except Exception as e:
                if getattr(e, 'code', None) == 404:
                    with open(file_path, 'wb') as f:
                        f.write(b'')
                
        threading.Thread(target=_download_and_save, daemon=True).start()

    @Slot()
    def checkAndDownloadInitialMap(self) -> None:
        import os
        import urllib.request
        import threading
        import time
        
        def _check_and_download():
            FAST_ZOOM = 3
            fast_total = sum((2 ** z) * (2 ** z) for z in range(FAST_ZOOM + 1))
            SILENT_ZOOM = 5
            
            missing_fast = []
            for z in range(FAST_ZOOM + 1):
                max_coord = 2 ** z
                for x in range(max_coord):
                    for y in range(max_coord):
                        tile_dir = os.path.join(self._cache_dir, str(z), str(x))
                        file_path = os.path.join(tile_dir, f"{y}.webp")
                        if not os.path.exists(file_path):
                            missing_fast.append((z, x, y, file_path, tile_dir))
            
            if missing_fast:
                downloaded_count = fast_total - len(missing_fast)
                self.mapDownloadProgress.emit(downloaded_count, fast_total)
                
                for z, x, y, file_path, tile_dir in missing_fast:
                    os.makedirs(tile_dir, exist_ok=True)
                    try:
                        url = self._fallback_url.format(z=z, x=x, y=y)
                        print(f"[MAP_DEBUG] Baixando (FAST) tile {z}/{x}/{y} de {url}")
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=5) as response:
                            data = response.read()
                            if data:
                                with open(file_path, 'wb') as f:
                                    f.write(data)
                                print(f"[MAP_DEBUG] Sucesso (FAST) tile {z}/{x}/{y}")
                            else:
                                print(f"[MAP_DEBUG] Arquivo vazio recebido (FAST) tile {z}/{x}/{y}")
                    except Exception as e:
                        print(f"[MAP_DEBUG] ERRO (FAST) tile {z}/{x}/{y}: {e}")
                        if getattr(e, 'code', None) == 404:
                            with open(file_path, 'wb') as f:
                                f.write(b'')
                    
                    downloaded_count += 1
                    if downloaded_count % 5 == 0 or downloaded_count == fast_total:
                        self.mapDownloadProgress.emit(downloaded_count, fast_total)
                        
            self.mapDownloadFinished.emit()
            
            missing_silent = []
            for z in range(FAST_ZOOM + 1, SILENT_ZOOM + 1):
                max_coord = 2 ** z
                for x in range(max_coord):
                    for y in range(max_coord):
                        tile_dir = os.path.join(self._cache_dir, str(z), str(x))
                        file_path = os.path.join(tile_dir, f"{y}.webp")
                        if not os.path.exists(file_path):
                            missing_silent.append((z, x, y, file_path, tile_dir))
                            
            for z, x, y, file_path, tile_dir in missing_silent:
                os.makedirs(tile_dir, exist_ok=True)
                try:
                    url = self._fallback_url.format(z=z, x=x, y=y)
                    print(f"[MAP_DEBUG] Baixando (SILENT) tile {z}/{x}/{y} de {url}")
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        data = response.read()
                        if data:
                            with open(file_path, 'wb') as f:
                                f.write(data)
                            print(f"[MAP_DEBUG] Sucesso (SILENT) tile {z}/{x}/{y}")
                    time.sleep(0.05)
                except Exception as e:
                    print(f"[MAP_DEBUG] ERRO (SILENT) tile {z}/{x}/{y}: {e}")
                    if getattr(e, 'code', None) == 404:
                        with open(file_path, 'wb') as f:
                            f.write(b'')
                                
        threading.Thread(target=_check_and_download, daemon=True).start()
