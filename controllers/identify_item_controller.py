from __future__ import annotations
from controllers.item_search_controller import ItemSearchController
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

class IdentifyItemController(QObject):
    MONITOR_SOUND_RESET_MISS_TICKS = 4

    changed = Signal()
    scanFinished = Signal(list, str)
    monitorFinished = Signal(object, str, bool)
    selectionFinished = Signal(object, str)

    def __init__(self, item_search: ItemSearchController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.item_search = item_search
        self.results = DictListModel(["name", "score", "scoreText", "icon", "path"], self)
        self.monitorMatches = DictListModel(["matchX", "matchY", "matchW", "matchH", "matchScore", "scoreText"], self)
        self.selectionCandidates = DictListModel(["candidateIndex", "selectX", "selectY", "selectW", "selectH", "cropX", "cropY", "cropW", "cropH"], self)
        self._status = "Ready."
        self._selected_path: Path | None = None
        self._selected_image_url = ""
        self._reference_preview_revision = 0
        self._mode = "Color"
        self._threshold = 0.86
        self._scanning = False
        self._clipboard_image = None
        self._detection_template: Any | None = None
        self._last_result_rows: list[dict[str, Any]] = []
        self._monitoring = False
        self._background_mode = False
        self._page_active = False
        self._monitor_dependencies_checked = False
        self._monitor_available = True
        self._monitor_overlay_visible = False
        self._monitor_control_visible = False
        self._monitor_worker_active = False
        self._monitor_hwnd = 0
        self._monitor_match_count = 0
        self._monitor_best_score = 0.0
        self._monitor_summary = "Detection off."
        self._monitor_last_rows: list[dict[str, Any]] = []
        self._monitor_miss_count = 0
        self._monitor_sound_played = False
        self._selection_overlay_visible = False
        self._selection_busy = False
        self._selection_screenshot = None
        self._selection_candidate_rows: list[dict[str, Any]] = []
        self._selection_request_id = 0
        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._run_monitor_tick)
        self._sync_monitor_timer_interval()
        self.scanFinished.connect(self._apply_scan_result)
        self.monitorFinished.connect(self._apply_monitor_result)
        self.selectionFinished.connect(self._apply_selection_result)

    def _sync_monitor_timer_interval(self) -> None:
        interval = 1000 if self._background_mode else 200 if self._page_active else 500
        if self._monitor_timer.interval() != interval:
            self._monitor_timer.setInterval(interval)

    def setBackgroundMode(self, background: bool) -> None:
        background = bool(background)
        if self._background_mode == background:
            return
        self._background_mode = background
        self._sync_monitor_timer_interval()

    def setPageActive(self, active: bool) -> None:
        active = bool(active)
        if self._page_active == active:
            return
        self._page_active = active
        self._sync_monitor_timer_interval()

    @Slot()
    def ensureLoaded(self) -> None:
        self.changed.emit()

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def selectedImageUrl(self) -> str:
        return self._selected_image_url

    @Property(str, notify=changed)
    def selectedPath(self) -> str:
        return str(self._selected_path or "")

    @Property(str, notify=changed)
    def mode(self) -> str:
        return self._mode

    @Property(float, notify=changed)
    def threshold(self) -> float:
        return self._threshold

    @Property(bool, notify=changed)
    def scanning(self) -> bool:
        return self._scanning

    @Property(bool, notify=changed)
    def monitoring(self) -> bool:
        return self._monitoring

    @Property(bool, notify=changed)
    def monitorAvailable(self) -> bool:
        return self._monitor_available

    @Property(str, notify=changed)
    def monitorTarget(self) -> str:
        if self._detection_template is not None:
            return str(getattr(self._detection_template, "name", "") or "selected image")
        if self._selected_path:
            return self._selected_path.name
        if self._clipboard_image is not None:
            return "clipboard image"
        return ""

    @Property(bool, notify=changed)
    def monitorOverlayVisible(self) -> bool:
        return self._monitor_overlay_visible

    @Property(bool, notify=changed)
    def monitorControlVisible(self) -> bool:
        return self._monitor_control_visible

    @Property(bool, notify=changed)
    def selectionOverlayVisible(self) -> bool:
        return self._selection_overlay_visible

    @Property(bool, notify=changed)
    def selectionBusy(self) -> bool:
        return self._selection_busy

    @Property(int, notify=changed)
    def monitorMatchCount(self) -> int:
        return self._monitor_match_count

    @Property(float, notify=changed)
    def monitorBestScore(self) -> float:
        return self._monitor_best_score

    @Property(str, notify=changed)
    def monitorBestScoreText(self) -> str:
        return f"{self._monitor_best_score:.3f}" if self._monitor_best_score > 0 else "-"

    @Property(str, notify=changed)
    def monitorSummary(self) -> str:
        return self._monitor_summary

    @Property(int, notify=changed)
    def indexedCount(self) -> int:
        return 0

    @Property(QObject, constant=True)
    def resultsModel(self) -> QObject:
        return self.results

    @Property(QObject, constant=True)
    def monitorMatchesModel(self) -> QObject:
        return self.monitorMatches

    @Property(QObject, constant=True)
    def selectionCandidatesModel(self) -> QObject:
        return self.selectionCandidates

    @Property("QStringList", constant=True)
    def modes(self) -> list[str]:
        return ["Color"]

    @Slot()
    def reindex(self) -> None:
        self._status = f"Direct OpenCV detection | {identify_dependencies_status()}"
        self.changed.emit()

    @Slot(str)
    def setMode(self, mode: str) -> None:
        self._mode = "Color"
        self.changed.emit()

    @Slot(float)
    def setThreshold(self, value: float) -> None:
        self._threshold = 0.86
        self.changed.emit()

    @Slot(int)
    def selectResult(self, index: int) -> None:
        self.changed.emit()

    @Slot()
    def selectImage(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            None,
            "Select image",
            str(BASE_DIR),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not path:
            return
        self._set_selected_path(Path(path))

    @Slot(str)
    def setSelectedImage(self, value: str) -> None:
        path = Path(value)
        if path.exists():
            self._set_selected_path(path)

    def _set_selected_path(self, path: Path) -> None:
        self._selected_path = path
        self._clipboard_image = None
        self._prepare_reference_from_path(path)
        if self._detection_template is not None:
            self._set_reference_preview_url(path)
            self._reset_monitor_tracking(clear_visible_matches=True)
            self._status = f"Reference selected: {path.name}"
            if self._monitor_control_visible and not self._monitoring:
                self.startMonitor()
                return
        self.changed.emit()

    @Slot()
    def scanSelected(self) -> None:
        self.showMonitorOverlay()

    @Slot()
    def showMonitorOverlay(self) -> None:
        self._monitor_control_visible = True
        if self._monitoring:
            self._monitor_summary = f"Detection active: {self.monitorTarget or 'selected image'}"
            self._status = self._monitor_summary
        elif self._detection_template is not None:
            self.startMonitor()
            return
        else:
            self._monitor_summary = "Select an item from stockpile or paste a reference image."
            self._status = self._monitor_summary
        self.changed.emit()

    @Slot()
    def hideMonitorOverlay(self) -> None:
        if self._monitoring:
            self.stopMonitor()
        self._selection_request_id += 1
        self._monitor_control_visible = False
        self._selection_overlay_visible = False
        self._selection_busy = False
        self._selection_candidate_rows = []
        self._selection_screenshot = None
        self.selectionCandidates.set_items([])
        self.changed.emit()

    @Slot()
    def clearReference(self) -> None:
        was_monitoring = self._monitoring
        if was_monitoring:
            self.stopMonitor()
        self._selected_path = None
        self._selected_image_url = ""
        self._reference_preview_revision += 1
        self._clipboard_image = None
        self._detection_template = None
        self._last_result_rows = []
        self.results.set_items([])
        self._selection_request_id += 1
        self._selection_overlay_visible = False
        self._selection_busy = False
        self._selection_candidate_rows = []
        self._selection_screenshot = None
        self.selectionCandidates.set_items([])
        self._reset_monitor_tracking(clear_visible_matches=True)
        self._monitor_summary = "No reference selected."
        self._status = "Reference cleared."
        self.changed.emit()

    @Slot()
    def beginStockpileItemSelection(self) -> None:
        if self._selection_busy:
            return
        np_module, cv2_module, image_grab = identify_service.monitor_dependencies()
        self._monitor_available = bool(np_module is not None and cv2_module is not None and image_grab is not None)
        if not self._monitor_available:
            self._status = "Install numpy and opencv-python for stockpile item selection."
            self.changed.emit()
            return
        if not self._is_foxhole_focused():
            self._status = "Focus Foxhole with the stockpile panel open first."
            self.changed.emit()
            return
        bbox = self._window_client_rect()
        offset_x = int(bbox[0]) if bbox else 0
        offset_y = int(bbox[1]) if bbox else 0
        self._selection_busy = True
        self._selection_overlay_visible = False
        self.selectionCandidates.set_items([])
        self._status = "Scanning stockpile panel..."
        self._selection_request_id += 1
        request_id = self._selection_request_id
        self.changed.emit()

        def worker() -> None:
            try:
                _np_module, _cv2_module, grabber = identify_service.monitor_dependencies()
                if grabber is None:
                    self.selectionFinished.emit({"rows": [], "image": None, "requestId": request_id}, "Screen capture is unavailable.")
                    return
                screenshot = grabber.grab(bbox=bbox) if bbox else grabber.grab()
                regions, status = detect_stockpile_item_regions(screenshot)
                scale_x, scale_y = self._qt_screen_scale(screenshot.width, screenshot.height)
                rows: list[dict[str, Any]] = []
                for region in regions:
                    row = dict(region)
                    row["candidateIndex"] = len(rows)
                    display_x = int(row["selectX"]) + offset_x
                    display_y = int(row["selectY"]) + offset_y
                    row["selectX"] = int(round(display_x * scale_x))
                    row["selectY"] = int(round(display_y * scale_y))
                    row["selectW"] = max(8, int(round(int(row["selectW"]) * scale_x)))
                    row["selectH"] = max(8, int(round(int(row["selectH"]) * scale_y)))
                    rows.append(row)
                self.selectionFinished.emit({"rows": rows, "image": screenshot, "requestId": request_id}, status)
            except Exception as exc:
                self.selectionFinished.emit({"rows": [], "image": None, "requestId": request_id}, f"Stockpile selection error: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def cancelStockpileItemSelection(self) -> None:
        self._selection_overlay_visible = False
        self._selection_busy = False
        self._selection_request_id += 1
        self._selection_candidate_rows = []
        self._selection_screenshot = None
        self.selectionCandidates.set_items([])
        self._status = "Stockpile item selection canceled."
        self.changed.emit()

    @Slot(int)
    def selectStockpileCandidate(self, index: int) -> None:
        if index < 0 or index >= len(self._selection_candidate_rows) or self._selection_screenshot is None:
            return
        row = self._selection_candidate_rows[index]
        try:
            crop_x = int(row.get("cropX", 0))
            crop_y = int(row.get("cropY", 0))
            crop_w = int(row.get("cropW", 0))
            crop_h = int(row.get("cropH", 0))
            crop = self._selection_screenshot.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h)).convert("RGBA")
        except Exception as exc:
            self._status = f"Could not crop selected item: {exc}"
            self.changed.emit()
            return

        self._clipboard_image = crop
        self._selected_path = None
        self._prepare_reference_from_image(crop, "stockpile item")
        preview_path = identify_preview_path()
        try:
            crop.save(preview_path)
            self._set_reference_preview_url(preview_path)
        except Exception:
            self._selected_image_url = ""
        self._selection_overlay_visible = False
        self._selection_busy = False
        self._selection_candidate_rows = []
        self._selection_screenshot = None
        self.selectionCandidates.set_items([])
        if self._detection_template is not None:
            self._reset_monitor_tracking(clear_visible_matches=True)
            self._monitor_summary = "Reference selected from stockpile."
            self._status = "Reference selected from stockpile."
            if self._monitor_control_visible and not self._monitoring:
                self.startMonitor()
                return
        self.changed.emit()

    @Slot()
    def pasteClipboard(self) -> None:
        image, status = grab_clipboard_image()
        if image is None:
            self._status = status
            self.changed.emit()
            return
        self._clipboard_image = image
        self._selected_path = None
        self._prepare_reference_from_image(image, "clipboard image")
        preview_path = identify_preview_path()
        try:
            image.save(preview_path)
            self._set_reference_preview_url(preview_path)
        except Exception:
            self._selected_image_url = ""
        if self._detection_template is not None:
            self._reset_monitor_tracking(clear_visible_matches=True)
            self._status = f"{status} Reference ready."
            if self._monitor_control_visible and not self._monitoring:
                self.startMonitor()
                return
        self.changed.emit()

    def _prepare_reference_from_path(self, path: Path) -> None:
        template, status = prepare_detection_template_path(path)
        self._detection_template = template
        self._monitor_summary = status
        if template is None:
            self._status = status

    def _prepare_reference_from_image(self, image, name: str) -> None:
        template, status = prepare_detection_template(image, name=name)
        self._detection_template = template
        self._monitor_summary = status
        if template is None:
            self._status = status

    def _set_reference_preview_url(self, path: Path) -> None:
        self._reference_preview_revision += 1
        self._selected_image_url = f"{file_url(path)}?v={self._reference_preview_revision}"

    def _reset_monitor_tracking(self, *, clear_visible_matches: bool = False) -> None:
        self._monitor_last_rows = []
        self._monitor_miss_count = 0
        self._monitor_sound_played = False
        if clear_visible_matches:
            self.monitorMatches.set_items([])
            self._monitor_match_count = 0
            self._monitor_best_score = 0.0

    def _held_monitor_rows(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._monitor_last_rows if isinstance(item, dict)]

    def _register_monitor_miss(self) -> None:
        self._monitor_miss_count += 1
        self._monitor_last_rows = []
        if self._monitor_miss_count >= self.MONITOR_SOUND_RESET_MISS_TICKS:
            self._monitor_sound_played = False

    def _stabilize_monitor_scores(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self._monitor_last_rows:
            return [dict(item) for item in rows]
        stable_rows: list[dict[str, Any]] = []
        used_indexes: set[int] = set()
        previous_rows = [dict(item) for item in self._monitor_last_rows if isinstance(item, dict)]
        for row in rows:
            stable = dict(row)
            row_center_x = int(stable.get("matchX", 0)) + (int(stable.get("matchW", 0)) // 2)
            row_center_y = int(stable.get("matchY", 0)) + (int(stable.get("matchH", 0)) // 2)
            best_index = -1
            best_distance = 999999
            for index, previous in enumerate(previous_rows):
                if index in used_indexes:
                    continue
                previous_center_x = int(previous.get("matchX", 0)) + (int(previous.get("matchW", 0)) // 2)
                previous_center_y = int(previous.get("matchY", 0)) + (int(previous.get("matchH", 0)) // 2)
                distance = abs(row_center_x - previous_center_x) + abs(row_center_y - previous_center_y)
                if distance < best_distance:
                    best_distance = distance
                    best_index = index
            if best_index >= 0 and best_distance <= 6:
                previous = previous_rows[best_index]
                stable["matchScore"] = previous.get("matchScore", stable.get("matchScore", 0.0))
                stable["scoreText"] = previous.get("scoreText", stable.get("scoreText", ""))
                used_indexes.add(best_index)
            stable_rows.append(stable)
        return stable_rows

    def _begin_scan(self) -> None:
        self._scanning = True
        self._status = "Starting direct detection..."
        self.changed.emit()

    @Slot(list, str)
    def _apply_scan_result(self, matches: list[dict[str, Any]], status: str) -> None:
        self._last_result_rows = matches
        self.results.set_items(matches)
        self._status = status
        self._scanning = False
        self.changed.emit()

    @Slot(object, str)
    def _apply_selection_result(self, payload: object, status: str) -> None:
        rows: list[dict[str, Any]] = []
        image = None
        if isinstance(payload, dict):
            request_id = payload.get("requestId")
            if request_id is not None and int(request_id) != self._selection_request_id:
                return
            raw_rows = payload.get("rows", [])
            rows = list(raw_rows) if isinstance(raw_rows, list) else []
            image = payload.get("image")
        self._selection_busy = False
        self._selection_candidate_rows = rows
        self._selection_screenshot = image
        self.selectionCandidates.set_items(rows)
        self._selection_overlay_visible = bool(rows)
        self._status = status
        self.changed.emit()

    @Slot()
    def toggleMonitor(self) -> None:
        if self._monitoring:
            self.stopMonitor()
        else:
            self.startMonitor()

    @Slot()
    def startMonitor(self) -> None:
        np_module, cv2_module, image_grab = identify_service.monitor_dependencies()
        self._monitor_dependencies_checked = True
        self._monitor_available = bool(np_module is not None and cv2_module is not None and image_grab is not None)
        if not self._monitor_available:
            self._status = "Install numpy and opencv-python for on-screen monitoring."
            self.changed.emit()
            return
        if self._detection_template is None:
            self._monitor_control_visible = True
            self._monitor_summary = "Select an item from stockpile or paste a reference image first."
            self._status = self._monitor_summary
            self.changed.emit()
            return
        self._monitor_control_visible = True
        self._monitoring = True
        self._monitor_overlay_visible = True
        self._monitor_match_count = 0
        self._monitor_best_score = 0.0
        self._monitor_summary = "Detection active. Waiting for Foxhole focus."
        self._reset_monitor_tracking(clear_visible_matches=True)
        self._status = f"Detection active: {self.monitorTarget or 'selected image'}"
        self._monitor_timer.start()
        self.changed.emit()

    @Slot()
    def stopMonitor(self) -> None:
        self._monitoring = False
        self._monitor_worker_active = False
        self._monitor_overlay_visible = False
        self._monitor_timer.stop()
        self.monitorMatches.set_items([])
        self._monitor_match_count = 0
        self._monitor_best_score = 0.0
        self._monitor_summary = "Detection off."
        self._reset_monitor_tracking(clear_visible_matches=False)
        self._status = "Monitoring stopped."
        self.changed.emit()

    def _is_foxhole_focused(self) -> bool:
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                self._monitor_hwnd = 0
                return False
            title_buffer = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
            title = (title_buffer.value or "").lower()
            focused = "war" in title or "foxhole" in title
            self._monitor_hwnd = int(hwnd) if focused else 0
            return focused
        except Exception:
            self._monitor_hwnd = 0
            return False

    def _window_client_rect(self) -> tuple[int, int, int, int] | None:
        if not self._monitor_hwnd:
            return None
        try:
            user32 = ctypes.windll.user32
            rect = RECT()
            hwnd = ctypes.c_void_p(self._monitor_hwnd)
            if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
                return None
            top_left = POINT(0, 0)
            bottom_right = POINT(rect.right, rect.bottom)
            if not user32.ClientToScreen(hwnd, ctypes.byref(top_left)):
                return None
            if not user32.ClientToScreen(hwnd, ctypes.byref(bottom_right)):
                return None
            left, top, right, bottom = int(top_left.x), int(top_left.y), int(bottom_right.x), int(bottom_right.y)
            if right <= left or bottom <= top:
                return None
            return left, top, right, bottom
        except Exception:
            return None

    def _qt_screen_scale(self, image_width: int | None = None, image_height: int | None = None) -> tuple[float, float]:
        try:
            screen = QGuiApplication.primaryScreen()
            geometry = screen.geometry() if screen is not None else None
            logical_width = float(geometry.width()) if geometry is not None and geometry.width() > 0 else 0.0
            logical_height = float(geometry.height()) if geometry is not None and geometry.height() > 0 else 0.0
        except Exception:
            logical_width = 0.0
            logical_height = 0.0
        try:
            user32 = ctypes.windll.user32
            physical_width = float(user32.GetSystemMetrics(0))
            physical_height = float(user32.GetSystemMetrics(1))
        except Exception:
            physical_width = float(image_width or 0)
            physical_height = float(image_height or 0)
        if image_width and image_height and (physical_width <= 0 or physical_height <= 0):
            physical_width = float(image_width)
            physical_height = float(image_height)
        scale_x = logical_width / physical_width if logical_width > 0 and physical_width > 0 else 1.0
        scale_y = logical_height / physical_height if logical_height > 0 and physical_height > 0 else 1.0
        if not 0.25 <= scale_x <= 4.0:
            scale_x = 1.0
        if not 0.25 <= scale_y <= 4.0:
            scale_y = 1.0
        return scale_x, scale_y

    def _play_detection_alert(self) -> None:
        def worker() -> None:
            try:
                import winsound

                winsound.Beep(500, 180)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def _run_monitor_tick(self) -> None:
        if not self._monitoring or self._monitor_worker_active:
            return
        template = self._detection_template
        if template is None:
            self._status = "Select, paste, or choose a stockpile item first."
            self._monitor_summary = "No reference selected."
            self._reset_monitor_tracking(clear_visible_matches=True)
            self.changed.emit()
            return
        if not self._is_foxhole_focused():
            self._status = f"Detection active: {self.monitorTarget or 'selected image'} | waiting for Foxhole focus"
            self._monitor_summary = "Waiting for Foxhole focus."
            rows = self._held_monitor_rows()
            self._monitor_match_count = len(rows)
            self.monitorMatches.set_items(rows)
            self.changed.emit()
            return
        bbox = self._window_client_rect()
        threshold = float(self._threshold)
        self._monitor_worker_active = True

        def worker() -> None:
            try:
                np_module, cv2_module, image_grab = identify_service.monitor_dependencies()
                if np_module is None or cv2_module is None or image_grab is None:
                    self.monitorFinished.emit([], "Monitor dependencies are unavailable.", False)
                    return
                screenshot = image_grab.grab(bbox=bbox) if bbox else image_grab.grab()
                screen_np = np_module.array(screenshot.convert("RGB"), dtype=np_module.uint8)
                gray = cv2_module.cvtColor(screen_np, cv2_module.COLOR_RGB2GRAY)
                base_template = template.gray
                scale_x, scale_y = self._qt_screen_scale(screenshot.width, screenshot.height)
                if self._monitor_control_visible:
                    mask_w = min(gray.shape[1], max(1, int(round(420 / max(scale_x, 0.01)))))
                    mask_h = min(gray.shape[0], max(1, int(round(300 / max(scale_y, 0.01)))))
                    gray[:mask_h, gray.shape[1] - mask_w :] = 0
                matches: list[dict[str, Any]] = []
                best_score = -1.0
                th, tw = int(base_template.shape[0]), int(base_template.shape[1])
                if th < gray.shape[0] and tw < gray.shape[1]:
                    result = cv2_module.matchTemplate(gray, base_template, cv2_module.TM_CCOEFF_NORMED)
                    _min_val, max_val, _min_loc, max_loc = cv2_module.minMaxLoc(result)
                    best_score = max(best_score, float(max_val))
                    if max_val >= threshold:
                        mask = (result >= threshold).astype(np_module.uint8) * 255
                        contours, _hierarchy = cv2_module.findContours(mask, cv2_module.RETR_EXTERNAL, cv2_module.CHAIN_APPROX_SIMPLE)
                        ranked: list[tuple[float, int, int]] = []
                        for contour in contours:
                            rx, ry, rw, rh = cv2_module.boundingRect(contour)
                            roi = result[ry : ry + rh, rx : rx + rw]
                            if roi.size == 0:
                                continue
                            _roi_min, roi_max, _roi_min_loc, roi_max_loc = cv2_module.minMaxLoc(roi)
                            ranked.append((float(roi_max), int(rx + roi_max_loc[0]), int(ry + roi_max_loc[1])))
                        if not ranked:
                            ranked.append((float(max_val), int(max_loc[0]), int(max_loc[1])))
                        ranked.sort(reverse=True)
                        min_distance = max(12, int(max(tw, th) * 0.65))
                        for score, x, y in ranked:
                            physical_x = int(x + (bbox[0] if bbox else 0))
                            physical_y = int(y + (bbox[1] if bbox else 0))
                            display_x = int(round(physical_x * scale_x))
                            display_y = int(round(physical_y * scale_y))
                            display_w = max(8, int(round(tw * scale_x)))
                            display_h = max(8, int(round(th * scale_y)))
                            center_x = display_x + (display_w // 2)
                            center_y = display_y + (display_h // 2)
                            duplicate = False
                            for item in matches:
                                item_center_x = int(item["matchX"]) + (int(item["matchW"]) // 2)
                                item_center_y = int(item["matchY"]) + (int(item["matchH"]) // 2)
                                if abs(center_x - item_center_x) < min_distance and abs(center_y - item_center_y) < min_distance:
                                    duplicate = True
                                    break
                            if duplicate:
                                continue
                            matches.append(
                                {
                                    "matchX": display_x,
                                    "matchY": display_y,
                                    "matchW": display_w,
                                    "matchH": display_h,
                                    "matchScore": score,
                                    "scoreText": f"{score:.3f}",
                                }
                            )
                            if len(matches) >= 12:
                                break
                if matches:
                    matches.sort(key=lambda item: float(item.get("matchScore", 0.0)), reverse=True)
                    self.monitorFinished.emit(matches[:12], f"Detected: {len(matches[:12])}", True)
                else:
                    score_text = f"{best_score:.3f}" if best_score >= 0 else "-"
                    self.monitorFinished.emit([], f"Searching... best confidence {score_text}", True)
            except Exception as exc:
                self.monitorFinished.emit([], f"Monitor error: {exc}", False)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object, str, bool)
    def _apply_monitor_result(self, matches: object, status: str, visible: bool) -> None:
        self._monitor_worker_active = False
        if not self._monitoring:
            self.monitorMatches.set_items([])
            self._monitor_overlay_visible = False
            self.changed.emit()
            return
        rows = list(matches) if isinstance(matches, list) else []
        if rows:
            if not self._monitor_sound_played:
                self._play_detection_alert()
                self._monitor_sound_played = True
            rows = self._stabilize_monitor_scores([dict(item) for item in rows if isinstance(item, dict)])
            self._monitor_last_rows = [dict(item) for item in rows]
            self._monitor_miss_count = 0
        else:
            if visible:
                self._register_monitor_miss()
                rows = []
            else:
                rows = self._held_monitor_rows()
            if rows:
                status = "Detected: held"

        self.monitorMatches.set_items(rows)
        self._monitor_overlay_visible = bool((visible or rows) and self._monitoring)
        self._monitor_match_count = len(rows)
        scores = [float(item.get("matchScore", 0.0)) for item in rows if isinstance(item, dict)]
        if scores:
            self._monitor_best_score = max(scores)
        elif match := re.search(r"(?:confidence|score)\s+([0-9.]+)", status, flags=re.IGNORECASE):
            try:
                self._monitor_best_score = float(match.group(1))
            except ValueError:
                self._monitor_best_score = 0.0
        elif "confidence" not in status.lower() and "score" not in status.lower():
            self._monitor_best_score = 0.0
        self._monitor_summary = status
        self._status = status
        self.changed.emit()

    @Slot()
    def shutdown(self) -> None:
        self.stopMonitor()
        self.cancelStockpileItemSelection()
