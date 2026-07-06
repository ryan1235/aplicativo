from __future__ import annotations
from controllers.i18n_controller import I18nController
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

class UpdateController(QObject):
    changed = Signal()
    checkResultFromWorker = Signal(object, str)
    progressFromWorker = Signal(int, str)
    installFailedFromWorker = Signal(str)
    quitFromWorker = Signal()

    def __init__(self, i18n: I18nController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self._status = self._t("update.status_idle")
        self._checking = False
        self._installing = False
        self._offer_visible = False
        self._progress_visible = False
        self._error_visible = False
        self._error_text = ""
        self._update: UpdateInfo | None = None
        self._progress_value = 0
        self._progress_text = ""
        self.checkResultFromWorker.connect(self._handle_check_result)
        self.progressFromWorker.connect(self._handle_progress)
        self.installFailedFromWorker.connect(self._handle_install_failed)
        self.quitFromWorker.connect(QGuiApplication.quit)

    def _t(self, key: str, **kwargs: Any) -> str:
        return self.i18n.translator.t(key, **kwargs)

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=changed)
    def checking(self) -> bool:
        return self._checking

    @Property(bool, notify=changed)
    def installing(self) -> bool:
        return self._installing

    @Property(bool, notify=changed)
    def offerVisible(self) -> bool:
        return self._offer_visible

    @Property(bool, notify=changed)
    def progressVisible(self) -> bool:
        return self._progress_visible

    @Property(bool, notify=changed)
    def errorVisible(self) -> bool:
        return self._error_visible

    @Property(str, notify=changed)
    def errorText(self) -> str:
        return self._error_text

    @Property(str, notify=changed)
    def updateVersion(self) -> str:
        return self._update.version if self._update else ""

    @Property(str, notify=changed)
    def updateName(self) -> str:
        return self._update.name if self._update else ""

    @Property(str, notify=changed)
    def updateBody(self) -> str:
        if not self._update:
            return ""
        return self._update.body.strip() or self._update.name or self._update.version

    @Property(str, notify=changed)
    def updateAvailableBody(self) -> str:
        if not self._update:
            return ""
        return self._t("update.available_body", version=self._update.version)

    @Property(str, notify=changed)
    def updateAssetName(self) -> str:
        return self._update.asset_name if self._update else ""

    @Property(int, notify=changed)
    def progressValue(self) -> int:
        return self._progress_value

    @Property(str, notify=changed)
    def progressText(self) -> str:
        return self._progress_text

    @Property(bool, notify=changed)
    def sourceMode(self) -> bool:
        return not is_built_app()

    @Slot()
    def check(self) -> None:
        if self._checking or self._installing:
            return
        debug_log("update", "check start", {"repo": UPDATE_REPO, "currentVersion": APP_VERSION})
        self._checking = True
        self._error_visible = False
        self._offer_visible = False
        self._status = self._t("update.checking")
        self.changed.emit()

        def worker() -> None:
            try:
                update = check_latest_release(UPDATE_REPO, APP_VERSION)
            except Exception as exc:
                self.checkResultFromWorker.emit(None, str(exc))
                return
            self.checkResultFromWorker.emit(update, "")

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def dismissOffer(self) -> None:
        self._offer_visible = False
        self.changed.emit()

    @Slot()
    def dismissError(self) -> None:
        self._error_visible = False
        self.changed.emit()

    @Slot()
    def installAvailableUpdate(self) -> None:
        if self._installing or not self._update:
            return
        debug_log("update", "install requested", {"version": self._update.version, "asset": self._update.asset_name})

        update = self._update
        self._offer_visible = False
        self._progress_visible = True
        self._installing = True
        self._progress_value = 0
        self._progress_text = self._t("update.download_prepare", version=update.version)
        self._status = self._progress_text
        self.changed.emit()

        def worker() -> None:
            try:
                def on_download_progress(downloaded: int, total: int) -> None:
                    if total > 0:
                        percent = max(0, min(100, int((downloaded / total) * 100)))
                        mb_done = downloaded / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        text = f"{self._t('update.downloading')} {percent}% ({mb_done:.1f}/{mb_total:.1f} MB)"
                    else:
                        percent = 0
                        mb_done = downloaded / (1024 * 1024)
                        text = f"{self._t('update.downloading')} {mb_done:.1f} MB"
                    self.progressFromWorker.emit(percent, text)

                zip_path = download_update(update, progress_callback=on_download_progress, translator=self.i18n.translator)
                self.progressFromWorker.emit(100, self._t("update.launching"))
                launch_updater(
                    zip_path,
                    runtime_dir(),
                    launch_target(),
                    language=self.i18n.language,
                    translator=self.i18n.translator,
                )
                self.quitFromWorker.emit()
            except Exception as exc:
                self.installFailedFromWorker.emit(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object, str)
    def _handle_check_result(self, update: object, error: str) -> None:
        self._checking = False
        if error:
            debug_log("update", "check failed", {"error": error})
            self._status = self._t("update.check_failed", message=error)
            self._error_text = self._status
            self._error_visible = True
            self.changed.emit()
            return
        self._update = update if isinstance(update, UpdateInfo) else None
        if self._update:
            debug_log("update", "available", {"version": self._update.version, "asset": self._update.asset_name})
            self._status = self._t("update.available_status", version=self._update.version)
            self._offer_visible = True
        else:
            debug_log("update", "no update", {})
            self._status = self._t("update.no_update")
            self._offer_visible = False
        self.changed.emit()

    @Slot(int, str)
    def _handle_progress(self, value: int, text: str) -> None:
        self._progress_value = max(0, min(100, int(value)))
        self._progress_text = text
        self._status = text
        debug_log("update", "progress", {"value": self._progress_value, "text": text})
        self.changed.emit()

    @Slot(str)
    def _handle_install_failed(self, message: str) -> None:
        self._installing = False
        self._progress_visible = False
        self._error_text = message
        self._error_visible = True
        self._status = message
        debug_log("update", "install failed", {"message": message})
        self.changed.emit()
