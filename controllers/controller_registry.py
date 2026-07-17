from __future__ import annotations
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
from .i18n_controller import I18nController
from .app_controller import AppController
from .steam_controller import SteamController
from .settings_controller import SettingsController
from .tray_controller import TrayController
from .auto_clicker_controller import AutoClickerController
from .stockpile_controller import StockpileController
from .chat_controller import ChatController
from .item_search_controller import ItemSearchController
from .identify_item_controller import IdentifyItemController
from .production_controller import ProductionController
from .time_task_controller import TimeTaskController
from .notifications_controller import NotificationsController
from .update_controller import UpdateController
from .overlay_controller import OverlayController
from .news_controller import NewsController
from .debug_controller import DebugController
from .custom_notifications_controller import CustomNotificationsController
from .map_controller import MapController
from .map_session_controller import MapSessionController
from .routing_controller import RoutingController

class ControllerRegistry(QObject):
    def __init__(self, app: QApplication) -> None:
        from foxmap.geo.artillery_controller import ArtilleryController
        super().__init__()
        self._shutdown_done = False
        self._background_mode = False
        debug_memory("registry init start")
        self.settings_data = load_settings()
        self.debugController = DebugController(self.settings_data, self)
        debug_log("app", "registry init start", {"version": APP_VERSION})
        self.i18nController = I18nController(self.settings_data, self)
        self.appController = AppController(self.i18nController, self.settings_data, self)
        self.settingsController = SettingsController(self.settings_data, self)
        self.steamController = SteamController(self)
        self.trayController = TrayController(app, self.i18nController, self)
        self.autoClickerController = AutoClickerController(self.settings_data, self)
        self.overlayController = OverlayController(self.settings_data, self.autoClickerController, self)
        self.stockpileController = StockpileController(self.settings_data, self)
        self.chatController = ChatController(self.steamController, self.settings_data, self.i18nController, self)
        self.newsController = NewsController(self.chatController, self.i18nController, self)
        self.itemSearchController = ItemSearchController(self.settings_data, self)
        self.identifyItemController = IdentifyItemController(self.itemSearchController, self)
        self.productionController = ProductionController(self.i18nController, self)
        self.timeTaskController = TimeTaskController(self.i18nController, self)
        self.notificationsController = NotificationsController(self.settings_data, self)
        self.customNotificationsController = CustomNotificationsController(self.settings_data, self)
        self.msuppController = MSuppController(self)
        self.mapController = MapController(self.settings_data, self)
        self.mapSessionController = MapSessionController(self.chatController, self)
        self.artilleryController = ArtilleryController(self)
        self.routingController = RoutingController(str(BASE_DIR), self)
        for controller in (
            self.appController,
            self.settingsController,
            self.autoClickerController,
            self.stockpileController,
            self.productionController,
            self.timeTaskController,
            self.notificationsController,
            self.customNotificationsController,
        ):
            controller.setActivityLogger(self.chatController.logActivity)
        self.updateController = UpdateController(self.i18nController, self)
        self.i18nController.changed.connect(self.settingsController.notifyExternalChange)
        self.appController.currentPageChanged.connect(self._sync_runtime_throttles)
        self.i18nController.changed.connect(self.stockpileController.refreshLocalizedTimes)
        self.i18nController.changed.connect(self.itemSearchController.refreshLocalizedTimes)
        self.settingsController.changed.connect(self.notificationsController.refresh)
        self.autoClickerController.orderRequested.connect(lambda _order: self.notificationsController.startSquadlock())
        if self.settings_data.get("stockpile", {}).get("enabled", True):
            QTimer.singleShot(0, self.stockpileController.start)
        
        QTimer.singleShot(2000, self.updateController.check)
        self._sync_runtime_throttles()
        debug_memory("registry init ready")
        debug_log("app", "registry init ready", {"controllers": "ready"})

    def _sync_runtime_throttles(self) -> None:
        current_page = self.appController.currentPage
        self.chatController.setPageActive(current_page == "chat")
        self.identifyItemController.setPageActive(current_page == "identifyItem")

    def setBackgroundMode(self, background: bool) -> None:
        background = bool(background)
        if self._background_mode == background:
            return
        self._background_mode = background
        for controller in (
            self.appController,
            self.chatController,
            self.identifyItemController,
            self.overlayController,
            self.notificationsController,
        ):
            try:
                controller.setBackgroundMode(background)
            except Exception as exc:
                debug_log("app", "background mode failed", {"controller": type(controller).__name__, "error": str(exc), "background": background})
        self._sync_runtime_throttles()

    def expose(self, engine) -> None:
        context = engine.rootContext()
        for name in (
            "appController",
            "i18nController",
            "settingsController",
            "debugController",
            "steamController",
            "trayController",
            "autoClickerController",
            "overlayController",
            "stockpileController",
            "chatController",
            "newsController",
            "itemSearchController",
            "identifyItemController",
            "productionController",
            "timeTaskController",
            "notificationsController",
            "customNotificationsController",
            "updateController",
            "msuppController",
            "mapController",
            "mapSessionController",
            "artilleryController",
            "routingController",
        ):
            context.setContextProperty(name, getattr(self, name))
        context.setContextProperty("navItems", self.appController.navItems)
        context.setContextProperty("languagesModel", self.i18nController.languages)

    @Slot()
    def shutdown(self) -> None:
        if self._shutdown_done:
            return
        self._shutdown_done = True
        for controller in (
            self.debugController,
            self.overlayController,
            self.autoClickerController,
            self.stockpileController,
            self.chatController,
            self.identifyItemController,
            self.timeTaskController,
            self.notificationsController,
        ):
            try:
                controller.shutdown()
            except Exception as exc:
                debug_log("app", "controller shutdown failed", {"controller": type(controller).__name__, "error": str(exc)})
