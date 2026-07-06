from __future__ import annotations
from controllers.i18n_controller import I18nController
from controllers.chat_controller import ChatController
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

class NewsController(QObject):
    changed = Signal()
    fetchResultFromWorker = Signal(object, str)
    LOCALE_BY_LANGUAGE = {"pt": "pt-BR", "en": "en-US", "es": "es-ES", "fr": "fr-FR"}

    def __init__(self, chat: ChatController, i18n: I18nController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.chat = chat
        self.i18n = i18n
        self._loading = False
        self._error = ""
        self._news: list[dict[str, Any]] = []
        self.fetchResultFromWorker.connect(self._handle_fetch_result)
        self.i18n.changed.connect(self._handle_language_changed)

    @Property(bool, notify=changed)
    def loading(self) -> bool:
        return self._loading

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Property("QVariantList", notify=changed)
    def newsModel(self) -> list[dict[str, Any]]:
        return self._news

    @Slot()
    def fetchNews(self) -> None:
        if self._loading:
            return
        token = str(getattr(self.chat, "_token", "") or "")
        if not token:
            self._news = []
            self._error = ""
            self.changed.emit()
            return
        self._loading = True
        self._error = ""
        self.changed.emit()
        threading.Thread(target=self._fetch_worker, args=(token,), daemon=True).start()

    def _fetch_worker(self, token: str) -> None:
        try:
            locale = self.LOCALE_BY_LANGUAGE.get(normalize_language(self.i18n.language), "pt-BR")
            query = urllib.parse.urlencode({"locale": locale})
            result = http_json("GET", f"/news?{query}", token=token, timeout=12)
            raw_news = result.get("news", []) if isinstance(result, dict) else result
            if not isinstance(raw_news, list):
                raw_news = []
            self.fetchResultFromWorker.emit(self._normalize_news_items(raw_news), "")
        except Exception as exc:
            self.fetchResultFromWorker.emit([], str(exc))

    def _normalize_news_items(self, news: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for item in news:
            if not isinstance(item, dict):
                continue
            body = str(item.get("bodyMarkdown") or item.get("body") or item.get("content") or "").strip()
            title = str(item.get("title") or "").strip()
            type_value = str(item.get("type") or item.get("category") or "general").strip() or "general"
            date_value = item.get("publishedAt") or item.get("startsAt") or item.get("createdAt") or ""
            author = item.get("author") if isinstance(item.get("author"), dict) else {}
            body_html = str(item.get("bodyHtml") or item.get("html") or "").strip() or markdown_to_html(body)
            content_blocks = item.get("contentBlocks") if isinstance(item.get("contentBlocks"), list) else []
            if not content_blocks:
                content_blocks = markdown_to_news_blocks(body)
            plain_body = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", body)
            plain_body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", plain_body)
            plain_body = re.sub(r"^[#>*\-\s]+", "", plain_body, flags=re.MULTILINE).strip()
            image_url = news_image_url(item)
            items.append(
                {
                    **item,
                    "title": title,
                    "body": plain_body,
                    "bodyMarkdown": body,
                    "bodyMarkdownNoImages": plain_body,
                    "bodyHtml": body_html,
                    "contentBlocks": content_blocks,
                    "excerpt": " ".join(plain_body.split())[:220],
                    "image": image_url,
                    "thumbnail": str(item.get("thumbnailUrl") or item.get("thumbnail") or image_url),
                    "category": type_value.replace("-", " ").replace("_", " ").title(),
                    "date": str(date_value or ""),
                    "viewCount": int_or_none(item.get("viewCount")) or 0,
                    "locale": str(item.get("locale") or ""),
                    "authorName": str(author.get("name") or author.get("email") or "GG Coalition"),
                }
            )
        return items

    @Slot(object, str)
    def _handle_fetch_result(self, news: list[dict[str, Any]], error: str) -> None:
        self._loading = False
        self._error = error
        self._news = news
        self.changed.emit()

    @Slot()
    def _handle_language_changed(self) -> None:
        if getattr(self.chat, "_token", ""):
            self.fetchNews()

    @Slot(str)
    def registerView(self, news_id: str) -> None:
        token = str(getattr(self.chat, "_token", "") or "")
        if not token or not news_id:
            return
        threading.Thread(
            target=lambda: self._register_view_worker(token, news_id),
            daemon=True,
        ).start()

    def _register_view_worker(self, token: str, news_id: str) -> None:
        try:
            http_json("POST", f"/news/{urllib.parse.quote(news_id)}/view", token=token, timeout=8)
        except Exception:
            pass
