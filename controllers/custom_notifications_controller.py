from __future__ import annotations
from controllers.notifications_controller import NotificationsController
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

class CustomNotificationsController(QObject):
    changed = Signal()

    def __init__(self, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._items = []
        self._list_model = DictListModel(["id", "name", "duration", "active", "sound", "showOverlay", "remaining", "progress"], self)
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._tick)
        self.load()

    @Property(QObject, constant=True)
    def model(self) -> DictListModel:
        return self._list_model

    @Property(bool, notify=changed)
    def hasOverlayItems(self) -> bool:
        return any(item.get("showOverlay", False) for item in self._items)

    @Property('QVariantList', notify=changed)
    def availableImages(self) -> list[str]:
        img_dir = Path("img")
        if img_dir.exists():
            return [p.name for p in img_dir.glob("*.png")] + [p.name for p in img_dir.glob("*.jpg")]
        return []

    def load(self) -> None:
        notifications_settings = self.settings.get("notifications", {})
        self._items = notifications_settings.get("custom", [])
        for item in self._items:
            item.setdefault("remaining", item.get("duration", 0))
            if item.get("active") and item.get("remaining", 0) > 0:
                self._tick_timer.start()
        self._update_model()

    def save(self) -> None:
        notifications_settings = self.settings.setdefault("notifications", {})
        notifications_settings["custom"] = self._items
        save_settings(self.settings)

    def _update_model(self) -> None:
        model_items = []
        for item in self._items:
            dur = item.get("duration", 1)
            rem = item.get("remaining", 0)
            progress = 1.0 - (rem / dur) if dur > 0 else 0.0
            model_items.append({
                "id": item.get("id"),
                "name": item.get("name", "Timer"),
                "duration": item.get("duration"),
                "active": item.get("active"),
                "sound": item.get("sound"),
                "showOverlay": item.get("showOverlay", False),
                "remaining": rem,
                "progress": progress
            })
        self._list_model.set_items(model_items)
        self.changed.emit()

    @Slot(str, int, bool, bool, bool)
    def createNotification(self, name: str, duration: int, active: bool, sound: bool, show_overlay: bool) -> None:
        import uuid
        new_item = {
            "id": str(uuid.uuid4()),
            "name": name,
            "duration": duration,
            "active": active,
            "sound": sound,
            "showOverlay": show_overlay,
            "remaining": duration
        }
        self._items.append(new_item)
        if active and duration > 0:
            self._tick_timer.start()
        self.save()
        self._update_model()

    @Slot(str, bool)
    def toggleActive(self, item_id: str, active: bool) -> None:
        for item in self._items:
            if item.get("id") == item_id:
                item["active"] = active
                if active and item.get("remaining", 0) <= 0:
                    item["remaining"] = item.get("duration", 0)
                break
        self.save()
        self._update_model()
        if any(i.get("active") and i.get("remaining", 0) > 0 for i in self._items):
            self._tick_timer.start()

    @Slot(str)
    def resetNotification(self, item_id: str) -> None:
        for item in self._items:
            if item.get("id") == item_id:
                item["remaining"] = item.get("duration", 0)
                item["active"] = True
                break
        self.save()
        self._update_model()
        if any(i.get("active") and i.get("remaining", 0) > 0 for i in self._items):
            self._tick_timer.start()

    @Slot(str)
    def finishNotification(self, item_id: str) -> None:
        for item in self._items:
            if item.get("id") == item_id:
                item["remaining"] = 0
                item["active"] = False
                break
        self.save()
        self._update_model()

    @Slot(str)
    def deleteNotification(self, item_id: str) -> None:
        self._items = [i for i in self._items if i.get("id") != item_id]
        self.save()
        self._update_model()

    def _tick(self) -> None:
        any_active = False
        for item in self._items:
            if item.get("active") and item.get("remaining", 0) > 0:
                item["remaining"] -= 1
                any_active = True
                if item["remaining"] <= 0:
                    item["active"] = False
                    if item.get("sound", False):
                        play_sound("squad")
        if not any_active:
            self._tick_timer.stop()
        self._update_model()

    @Slot()
    def shutdown(self) -> None:
        self._tick_timer.stop()
        self.save()

    def setActivityLogger(self, logger) -> None:
        pass
