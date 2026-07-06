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

class NotificationsController(QObject):
    changed = Signal()

    def __init__(self, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._remaining_seconds = SQUADLOCK_SECONDS
        self._running = False
        self._activity_logger: ActivityLogger | None = None
        self._background_mode = False
        self._finished = False
        self._overlay_visible = False
        self._overlay_hold_until = 0.0
        notification_settings = self.settings.get("notifications", {})
        self._overlay_enabled = bool(notification_settings.get("squadlock_overlay_enabled", True))
        self._overlay_x = self._int_or_default(notification_settings.get("squadlock_x"), -1)
        self._overlay_y = self._int_or_default(notification_settings.get("squadlock_y"), -1)
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._tick)
        self._focus_timer = QTimer(self)
        self._focus_timer.timeout.connect(self._refresh_overlay_visibility)
        self._sync_focus_timer_interval()
        self._notifications = DictListModel(["key", "labelKey", "active", "detailKey"], self)
        self.refresh()

    @staticmethod
    def _int_or_default(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @Property(QObject, constant=True)
    def notifications(self) -> DictListModel:
        return self._notifications

    @Property(int, notify=changed)
    def remainingSeconds(self) -> int:
        return self._remaining_seconds

    @Property(str, notify=changed)
    def timeText(self) -> str:
        return format_duration(self._remaining_seconds)

    @Property(str, notify=changed)
    def statusKey(self) -> str:
        if self._finished:
            return "notifications.finished"
        if self._running:
            return "notifications.active"
        return "notifications.waiting"

    @Property(float, notify=changed)
    def progress(self) -> float:
        return 1.0 - (max(0, self._remaining_seconds) / SQUADLOCK_SECONDS)

    @Property(bool, notify=changed)
    def squadlockRunning(self) -> bool:
        return self._running

    @Property(bool, notify=changed)
    def squadlockFinished(self) -> bool:
        return self._finished

    @Property(bool, notify=changed)
    def overlayEnabled(self) -> bool:
        return self._overlay_enabled

    @Property(bool, notify=changed)
    def overlayVisible(self) -> bool:
        return self._overlay_visible

    @Property(int, notify=changed)
    def overlayX(self) -> int:
        return self._overlay_x

    @Property(int, notify=changed)
    def overlayY(self) -> int:
        return self._overlay_y

    @Property(bool, notify=changed)
    def squadlockSoundEnabled(self) -> bool:
        return bool(self.settings.get("app", {}).get("squadlock_sound_enabled", True))

    @Slot()
    def refresh(self) -> None:
        app_settings = self.settings.get("app", {})
        notification_settings = self.settings.get("notifications", {})
        self._overlay_enabled = bool(notification_settings.get("squadlock_overlay_enabled", True))
        self._notifications.set_items(
            [
                {
                    "key": "stockpile_sound_enabled",
                    "labelKey": "settings.sound_stockpile",
                    "active": bool(app_settings.get("stockpile_sound_enabled", True)),
                    "detailKey": "notifications.stockpile_sound_detail",
                },
                {
                    "key": "squadlock_overlay_enabled",
                    "labelKey": "notifications.show_overlay",
                    "active": self._overlay_enabled,
                    "detailKey": "notifications.squadlock_overlay_detail",
                },
                {
                    "key": "squadlock_sound_enabled",
                    "labelKey": "settings.sound_squadlock",
                    "active": bool(app_settings.get("squadlock_sound_enabled", True)),
                    "detailKey": "notifications.squadlock_sound_detail",
                },
                {
                    "key": "chat_mention_overlay_enabled",
                    "labelKey": "settings.chat_mention_overlay",
                    "active": bool(app_settings.get("chat_mention_overlay_enabled", True)),
                    "detailKey": "notifications.chat_mention_overlay_detail",
                },
                {
                    "key": "chat_mention_sound_enabled",
                    "labelKey": "settings.chat_mention_sound",
                    "active": bool(app_settings.get("chat_mention_sound_enabled", True)),
                    "detailKey": "notifications.chat_mention_sound_detail",
                },
            ]
        )
        self._refresh_overlay_visibility()
        self._sync_focus_timer()
        self.changed.emit()

    def _sync_focus_timer_interval(self) -> None:
        interval = 1500 if self._background_mode else 500
        if self._focus_timer.interval() != interval:
            self._focus_timer.setInterval(interval)

    def setBackgroundMode(self, background: bool) -> None:
        background = bool(background)
        if self._background_mode == background:
            return
        self._background_mode = background
        self._sync_focus_timer_interval()

    def setActivityLogger(self, logger: ActivityLogger | None) -> None:
        self._activity_logger = logger

    def _log_activity(self, action: str, *, subcategory: str, metadata: dict[str, Any] | None = None) -> None:
        if callable(self._activity_logger):
            self._activity_logger("notificacoes", action, 1, metadata or {}, subcategory)

    @Slot()
    def startSquadlock(self) -> None:
        self._remaining_seconds = SQUADLOCK_SECONDS
        self._running = True
        self._finished = False
        self._tick_timer.start()
        self._refresh_overlay_visibility()
        self._sync_focus_timer()
        self._log_activity("iniciar_squadlock", subcategory="squadlock", metadata={"seconds": SQUADLOCK_SECONDS})
        self.changed.emit()

    @Slot()
    def resetSquadlock(self) -> None:
        self.startSquadlock()

    @Slot()
    def finishSquadlock(self) -> None:
        self._tick_timer.stop()
        self._running = False
        self._finished = False
        self._remaining_seconds = SQUADLOCK_SECONDS
        self._set_overlay_visible(False)
        self._sync_focus_timer()
        self._log_activity("finalizar_squadlock", subcategory="squadlock")
        self.changed.emit()

    @Slot(bool)
    def setOverlayEnabled(self, enabled: bool) -> None:
        self._overlay_enabled = bool(enabled)
        notifications = self.settings.setdefault("notifications", {})
        notifications["squadlock_overlay_enabled"] = self._overlay_enabled
        save_settings(self.settings)
        self.refresh()
        self._refresh_overlay_visibility()

    @Slot(str, bool)
    def setNotificationEnabled(self, key: str, enabled: bool) -> None:
        if key == "squadlock_overlay_enabled":
            self.setOverlayEnabled(enabled)
            return
        if key in {
            "stockpile_sound_enabled",
            "squadlock_sound_enabled",
            "chat_mention_overlay_enabled",
            "chat_mention_sound_enabled",
        }:
            self.settings.setdefault("app", {})[key] = bool(enabled)
            save_settings(self.settings)
            self.refresh()

    @Slot(int, int)
    def setOverlayPosition(self, x: int, y: int) -> None:
        self._overlay_x = max(0, int(x))
        self._overlay_y = max(0, int(y))
        notifications = self.settings.setdefault("notifications", {})
        notifications["squadlock_x"] = self._overlay_x
        notifications["squadlock_y"] = self._overlay_y
        save_settings(self.settings)
        self.changed.emit()

    @Slot(int)
    def holdOverlayVisible(self, milliseconds: int = 1500) -> None:
        self._overlay_hold_until = time.monotonic() + max(0, int(milliseconds)) / 1000
        self._refresh_overlay_visibility()
        self._sync_focus_timer()

    def _tick(self) -> None:
        if not self._running:
            return
        self._remaining_seconds = max(0, self._remaining_seconds - 1)
        if self._remaining_seconds <= 0:
            self._tick_timer.stop()
            self._running = False
            self._finished = True
            if self.squadlockSoundEnabled:
                play_sound("squad")
        self._refresh_overlay_visibility()
        self._sync_focus_timer()
        self.changed.emit()

    def _refresh_overlay_visibility(self) -> None:
        if not self._overlay_enabled or not (self._running or self._finished):
            self._set_overlay_visible(False)
            return
        held = time.monotonic() <= self._overlay_hold_until
        self._set_overlay_visible(held or self.is_foxhole_foreground())

    def _set_overlay_visible(self, visible: bool) -> None:
        visible = bool(visible)
        if self._overlay_visible == visible:
            return
        self._overlay_visible = visible
        self.changed.emit()

    def _sync_focus_timer(self) -> None:
        active = bool(self._overlay_enabled and (self._running or self._finished))
        if active and not self._focus_timer.isActive():
            self._focus_timer.start()
        elif not active and self._focus_timer.isActive():
            self._focus_timer.stop()

    def is_foxhole_foreground(self) -> bool:
        try:
            user32 = ctypes.windll.user32
            foreground = user32.GetForegroundWindow()
            if not foreground:
                return False
            return self.is_foxhole_window(int(foreground))
        except Exception:
            return False

    def is_foxhole_window(self, hwnd: int) -> bool:
        process_path = self.get_window_process_path(hwnd).lower()
        process_name = Path(process_path).name.lower() if process_path else ""
        return process_name in FOXHOLE_PROCESS_NAMES or any(hint in process_path for hint in FOXHOLE_PATH_HINTS)

    def get_window_process_path(self, hwnd: int) -> str:
        try:
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value:
                return ""
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if not handle:
                return ""
            try:
                path_buffer = ctypes.create_unicode_buffer(1024)
                size = ctypes.c_ulong(len(path_buffer))
                if ctypes.windll.kernel32.QueryFullProcessImageNameW(handle, 0, path_buffer, ctypes.byref(size)):
                    return path_buffer.value
                return ""
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            return ""

    @Slot()
    def shutdown(self) -> None:
        self._tick_timer.stop()
        self._focus_timer.stop()
        self._set_overlay_visible(False)
