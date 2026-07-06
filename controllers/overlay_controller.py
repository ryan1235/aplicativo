from __future__ import annotations
from controllers.auto_clicker_controller import AutoClickerController
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

class OverlayController(QObject):
    changed = Signal()

    def __init__(
        self,
        settings: dict[str, Any],
        auto_clicker: AutoClickerController,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.auto_clicker = auto_clicker
        self._visible = False
        self._preview_until = 0.0
        self._hotkey_was_down = False
        self._background_mode = False
        self._last_find_attempt = 0.0
        self.auto_clicker.changed.connect(self._refresh_visibility)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._sync_timer_interval()
        self._timer.start()
        self._refresh_visibility()

    def _sync_timer_interval(self) -> None:
        interval = 500 if self._background_mode else 250
        if self._timer.interval() != interval:
            self._timer.setInterval(interval)

    def setBackgroundMode(self, background: bool) -> None:
        background = bool(background)
        if self._background_mode == background:
            return
        self._background_mode = background
        self._sync_timer_interval()

    @Slot()
    def shutdown(self) -> None:
        self._timer.stop()
        self._set_overlay_visible(False)

    def _clicker_settings(self) -> dict[str, Any]:
        return self.settings.setdefault("auto_clicker", {})

    def _int_or_default(self, value: object, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _palette(self) -> dict[str, str]:
        return OVERLAY_PALETTES.get(self.colorName, OVERLAY_PALETTES["Azul"])

    @Property(bool, notify=changed)
    def visible(self) -> bool:
        return self._visible

    @Property(bool, notify=changed)
    def enabled(self) -> bool:
        return bool(self._clicker_settings().get("overlay_enabled", True))

    @Property(str, notify=changed)
    def hotkey(self) -> str:
        return str(self._clicker_settings().get("overlay_hotkey", "F8"))

    @Property(str, notify=changed)
    def colorName(self) -> str:
        name = str(self._clicker_settings().get("overlay_color", "Azul"))
        return name if name in OVERLAY_PALETTES else "Azul"

    @Property(str, notify=changed)
    def backgroundColor(self) -> str:
        return self._palette()["bg"]

    @Property(str, notify=changed)
    def panelColor(self) -> str:
        return self._palette()["panel"]

    @Property(str, notify=changed)
    def accentColor(self) -> str:
        return self._palette()["accent"]

    @Property(bool, notify=changed)
    def showProfile(self) -> bool:
        return bool(self._clicker_settings().get("overlay_show_profile", True))

    @Property(bool, notify=changed)
    def showClicker(self) -> bool:
        return bool(self._clicker_settings().get("overlay_show_clicker", True))

    @Property(bool, notify=changed)
    def showTarget(self) -> bool:
        return bool(self._clicker_settings().get("overlay_show_target", True))

    @Property(bool, notify=changed)
    def notificationEnabled(self) -> bool:
        return bool(self._clicker_settings().get("overlay_notification_enabled", True))

    @Property(int, notify=changed)
    def panelX(self) -> int:
        return self._int_or_default(self._clicker_settings().get("overlay_panel_x"), -1)

    @Property(int, notify=changed)
    def panelY(self) -> int:
        return self._int_or_default(self._clicker_settings().get("overlay_panel_y"), -1)

    @Property("QStringList", constant=True)
    def hotkeys(self) -> list[str]:
        return list(HOTKEYS.keys())

    @Property("QStringList", constant=True)
    def colors(self) -> list[str]:
        return list(OVERLAY_PALETTES.keys())

    @Slot(str, result=str)
    def colorLabelKey(self, name: str) -> str:
        return OVERLAY_COLOR_LABEL_KEYS.get(name, "overlay.color_blue")

    @Slot(bool)
    def setEnabled(self, enabled: bool) -> None:
        if not enabled:
            self._preview_until = 0.0
        self._clicker_settings()["overlay_enabled"] = bool(enabled)
        self._save_settings()

    @Slot()
    def toggle(self) -> None:
        self.setEnabled(not self.enabled)

    @Slot()
    def preview(self) -> None:
        self._preview_until = time.monotonic() + 8.0
        self._refresh_visibility()

    @Slot(str)
    def setHotkey(self, value: str) -> None:
        if value in HOTKEYS:
            self._clicker_settings()["overlay_hotkey"] = value
            self._save_settings()

    @Slot(str)
    def setColorName(self, value: str) -> None:
        if value in OVERLAY_PALETTES:
            self._clicker_settings()["overlay_color"] = value
            self._save_settings()

    @Slot(bool)
    def setShowProfile(self, enabled: bool) -> None:
        self._clicker_settings()["overlay_show_profile"] = bool(enabled)
        self._save_settings()

    @Slot(bool)
    def setShowClicker(self, enabled: bool) -> None:
        self._clicker_settings()["overlay_show_clicker"] = bool(enabled)
        self._save_settings()

    @Slot(bool)
    def setShowTarget(self, enabled: bool) -> None:
        self._clicker_settings()["overlay_show_target"] = bool(enabled)
        self._save_settings()

    @Slot(bool)
    def setNotificationEnabled(self, enabled: bool) -> None:
        self._clicker_settings()["overlay_notification_enabled"] = bool(enabled)
        self._save_settings()

    @Slot(int, int)
    def savePanelPosition(self, x: int, y: int) -> None:
        data = self._clicker_settings()
        data["overlay_panel_x"] = max(0, int(x))
        data["overlay_panel_y"] = max(0, int(y))
        self._save_settings()

    def _save_settings(self) -> None:
        save_settings(self.settings)
        self._refresh_visibility()
        self.changed.emit()

    @Slot()
    def _poll(self) -> None:
        hotkey = self.hotkey
        vk = HOTKEYS.get(hotkey, HOTKEYS["F8"])
        clicker = self.auto_clicker.clicker
        try:
            is_down = bool(clicker and clicker.user32.GetAsyncKeyState(vk) & 0x8000)
        except Exception:
            is_down = False
        if is_down and not self._hotkey_was_down:
            self.toggle()
        self._hotkey_was_down = is_down
        self._refresh_visibility()

    def _refresh_visibility(self) -> None:
        if not self.enabled and time.monotonic() > self._preview_until:
            self._set_visible(False)
            return
        if time.monotonic() <= self._preview_until:
            self._set_visible(True)
            return
        # Also show overlay when hold modes are active.
        clicker = self.auto_clicker.clicker
        if clicker and (
            getattr(clicker, "move_click_enabled", False)
            or getattr(clicker, "w_hold_enabled", False)
            or getattr(clicker, "right_hold_enabled", False)
        ):
            self._set_visible(True)
            return
        self._set_visible(self._is_foxhole_overlay_context())


    def _is_foxhole_overlay_context(self) -> bool:
        clicker = self.auto_clicker.clicker
        if not clicker:
            return False
        try:
            if not clicker.target_hwnd or not clicker.user32.IsWindow(clicker.target_hwnd):
                now = time.monotonic()
                if now - self._last_find_attempt >= 5:
                    self._last_find_attempt = now
                    clicker.use_foxhole_window(quiet=True)
            if not clicker.target_hwnd or not clicker.user32.IsWindow(clicker.target_hwnd):
                return False
            foreground = clicker.user32.GetForegroundWindow()
            if foreground and (
                foreground == clicker.target_hwnd
                or clicker.is_same_process_window(foreground, clicker.target_hwnd)
                or clicker.is_foxhole_window(foreground)
            ):
                return True
            point = POINT()
            if clicker.user32.GetCursorPos(ctypes.byref(point)):
                cursor_hwnd = clicker.user32.WindowFromPoint(point)
                if cursor_hwnd and (
                    cursor_hwnd == clicker.target_hwnd
                    or clicker.is_same_process_window(cursor_hwnd, clicker.target_hwnd)
                    or clicker.is_foxhole_window(cursor_hwnd)
                ):
                    return True
        except Exception:
            return False
        return False

    def _set_visible(self, visible: bool) -> None:
        if self._visible == visible:
            return
        self._visible = visible
        self.changed.emit()
