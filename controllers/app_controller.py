from __future__ import annotations
from controllers.i18n_controller import I18nController
from controllers.settings_controller import SettingsController
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

class AppController(QObject):
    currentPageChanged = Signal()
    foxholeStatusChanged = Signal()
    closeRequested = Signal()
    startupDialogChanged = Signal()
    tutorialDialogChanged = Signal()
    panelAccessResult = Signal(str, str)
    sidebarChanged = Signal()
    sidebarSectionsChanged = Signal()

    def __init__(self, i18n: I18nController, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.settings = settings
        self.panelAccessResult.connect(self._on_panel_access_result)
        self._current_page = "home"
        self._foxhole_status = "Checking Foxhole..."
        self._startup_dialog_visible = False
        self._startup_dialog_kind = ""
        self._startup_dialog_title = ""
        self._startup_dialog_subtitle = ""
        self._startup_dialog_body = ""
        self._startup_dialog_image_url = ""
        self._tutorial_dialog_visible = False
        self._tutorial_dialog_title = ""
        self._tutorial_dialog_body = ""
        self._pending_admin_panel_token = ""
        self._panel_access_check_running = False
        self._activity_logger: ActivityLogger | None = None
        self._background_mode = False
        app_settings = self._app_settings()
        self._sidebar_open = bool(app_settings.get("sidebar_open", True))
        self._sidebar_sections_revision = 0
        self._sidebar_sections = self._normalized_sidebar_sections(app_settings.get("sidebar_sections"))
        save_settings(self.settings)
        self._tutorial_key_by_page = {
            "home": "inicio",
            "chat": "chat",
            "autoClicker": "ferramentas",
            "timeTask": "time_task",
            "stockpile": "stockpile",
            "production": "production_calculator",
            "itemSearch": "item_search",
            "wiki": "wiki",
            "identifyItem": "identify_item",
            "notifications": "notificacoes",
            "settings": "configuracoes",
            "personalization": "configuracoes",
        }
        self.navItems = DictListModel(["key", "labelKey", "icon", "section", "searchText"], self)
        self.navItems.set_items(self._nav_items())
        self._foxhole_timer = QTimer(self)
        self._foxhole_timer.timeout.connect(self.refreshFoxholeStatus)
        self._sync_foxhole_timer()
        self.refreshFoxholeStatus()

    def _sync_foxhole_timer(self) -> None:
        interval = 30000 if self._background_mode else 5000
        if self._foxhole_timer.interval() != interval:
            self._foxhole_timer.setInterval(interval)
        if not self._foxhole_timer.isActive():
            self._foxhole_timer.start()

    def setBackgroundMode(self, background: bool) -> None:
        background = bool(background)
        if self._background_mode == background:
            return
        self._background_mode = background
        self._sync_foxhole_timer()


    def setActivityLogger(self, logger: ActivityLogger | None) -> None:
        self._activity_logger = logger

    def _log_activity(self, action: str, *, subcategory: str, metadata: dict[str, Any] | None = None) -> None:
        if callable(self._activity_logger):
            self._activity_logger("navegacao", action, 1, metadata or {}, subcategory)

    @Slot(str)
    def openAdminPanel(self, token: str) -> None:
        """Verifica o acesso na API antes de abrir o painel administrativo."""
        token = str(token or "").strip()
        if not token:
            self._pending_admin_panel_token = ""
            self.showStartupDialog(
                kind="error",
                title=self._t("error.auth.denied.title"),
                subtitle=self._t("error.auth.reauth.title"),
                body=self._t("error.auth.reauth.body"),
                image_url="",
            )
            return

        # Guarda o token para o botão "Tentar novamente" refazer a mesma checagem na API.
        self._pending_admin_panel_token = token
        if self._panel_access_check_running:
            self.panelAccessResult.emit("checking", "")
            return

        def _check_and_open() -> None:
            try:
                profile_res = http_json("GET", "/chat/profile", token=token)
                profile = profile_res.get("profile") or profile_res
                if not isinstance(profile, dict):
                    raise RuntimeError("Perfil inválido retornado pela API.")

                profile = merge_panel_profile(profile, profile_res.get("panelAccess") or profile.get("panelAccess"))
                discord_id = str(profile.get("discordId") or profile.get("discord_id") or "").strip()
                panel_access = profile.get("panelAccess") if isinstance(profile.get("panelAccess"), dict) else {}

                if discord_id and not bool(panel_access.get("verified")):
                    access_res = http_json("POST", "/chat/panel/access", token=token, payload={"discordId": discord_id})
                    profile = merge_panel_profile(
                        access_res.get("user") if isinstance(access_res.get("user"), dict) else profile,
                        access_res,
                    )
                    panel_access = profile.get("panelAccess") if isinstance(profile.get("panelAccess"), dict) else {}

                access_level = int_or_none(panel_access.get("accessLevel"))
                if bool(panel_access.get("canLoginPanel")) and access_level is not None and access_level >= PANEL_REQUIRED_ACCESS_LEVEL:
                    self.panelAccessResult.emit("ok", token)
                else:
                    reason = self._t("error.auth.denied.title")
                    if access_level in (0, 1):
                        reason = self._t("error.auth.denied.level_info").replace("{current}", str(access_level)).replace("{required}", str(PANEL_REQUIRED_ACCESS_LEVEL))
                    elif panel_access:
                        reason = self._t("error.auth.denied.level_info").replace("{current}", str(access_level)).replace("{required}", str(panel_access.get("requiredAccessLevel", PANEL_REQUIRED_ACCESS_LEVEL)))
                    self.panelAccessResult.emit("error", reason)
            except Exception as exc:
                self.panelAccessResult.emit("error", f"Erro ao verificar acesso: {exc}")
            finally:
                self._panel_access_check_running = False

        self._panel_access_check_running = True
        self.panelAccessResult.emit("checking", "")
        threading.Thread(target=_check_and_open, daemon=True).start()

    @Slot()
    def retryAdminPanelAccess(self) -> None:
        """Refaz a checagem do painel quando o usuário clica em Tentar novamente."""
        token = str(getattr(self, "_pending_admin_panel_token", "") or "").strip()
        self._startup_dialog_visible = False
        self.startupDialogChanged.emit()
        if token:
            self.openAdminPanel(token)
            return
        self.showStartupDialog(
            kind="error",
            title=self._t("error.auth.denied.title"),
            subtitle=self._t("error.auth.reauth.title"),
            body=self._t("error.auth.reauth.body"),
            image_url="",
        )

    @Slot(str, str)
    def _on_panel_access_result(self, status: str, payload: str) -> None:
        if status == "ok":
            token = payload
            self._pending_admin_panel_token = ""
            try:
                import admin_server
                admin_server.start_admin_server()
            except Exception as e:
                print(f"Failed to start admin server: {e}")
            import urllib.parse
            api_hint = base64.urlsafe_b64encode(CHAT_API_BASE.encode("utf-8")).decode("ascii")
            theme_hint = ""
            try:
                personalization = load_personalization_settings(
                    legacy_theme=self.settings.get("app", {}).get("theme"),
                    legacy_colorblind=self.settings.get("app", {}).get("colorblind_mode_enabled"),
                )
                theme_settings = personalization.get("theme") if isinstance(personalization, dict) else {}
                theme_settings = theme_settings if isinstance(theme_settings, dict) else {}
                preset = str(theme_settings.get("preset") or "coalition")
                if bool(personalization.get("colorblind_mode_enabled", False)):
                    preset = "accessible"
                if preset == "custom":
                    custom = theme_settings.get("custom") if isinstance(theme_settings.get("custom"), dict) else {}
                    palette = {
                        key: SettingsController._sanitize_hex_color(custom.get(key), str(UI_THEME_CUSTOM_DEFAULT[key]))
                        for key in UI_THEME_COLOR_KEYS
                    }
                    palette["gradient_enabled"] = bool(custom.get("gradient_enabled", UI_THEME_CUSTOM_DEFAULT["gradient_enabled"]))
                    palette["card_radius"] = SettingsController._sanitize_card_radius(custom.get("card_radius"))
                else:
                    source = UI_THEME_PRESETS.get(preset, UI_THEME_PRESETS["coalition"])
                    palette = {key: source.get(key, fallback) for key, fallback in UI_THEME_CUSTOM_DEFAULT.items()}
                    if preset == "accessible":
                        profile = str(personalization.get("colorblind_profile") or "unsure")
                        palette.update(COLORBLIND_THEME_OVERRIDES.get(profile, COLORBLIND_THEME_OVERRIDES["unsure"]))
                theme_hint = base64.urlsafe_b64encode(
                    json.dumps(palette, separators=(",", ":")).encode("utf-8")
                ).decode("ascii").rstrip("=")
            except Exception as exc:
                print(f"Failed to prepare admin panel theme: {exc}")
            params = urllib.parse.urlencode(
                {
                    "token": token or "",
                    "api": api_hint,
                    "lang": normalize_language(getattr(self.i18n, "language", selected_language(self.settings))),
                    "theme": theme_hint,
                }
            )
            url_str = f"http://localhost:3334/?{params}"
            success = QDesktopServices.openUrl(QUrl(url_str))
            if not success:
                import webbrowser
                webbrowser.open(url_str)
        elif status == "error":
            self.showStartupDialog(
                kind="error",
                title=self._t("error.auth.denied.title"),
                subtitle=self._t("error.auth.permission.title"),
                body=payload,
                image_url="",
            )
        # "checking" = noop (just waiting)

    @Property(str, constant=True)
    def appTitle(self) -> str:
        return APP_TITLE

    @Property(str, constant=True)
    def version(self) -> str:
        return APP_VERSION

    @Property(str, notify=currentPageChanged)
    def currentPage(self) -> str:
        return self._current_page

    @Property(str, notify=foxholeStatusChanged)
    def foxholeStatus(self) -> str:
        return self._foxhole_status

    @Property(bool, notify=startupDialogChanged)
    def startupDialogVisible(self) -> bool:
        return self._startup_dialog_visible

    @Property(str, notify=startupDialogChanged)
    def startupDialogKind(self) -> str:
        return self._startup_dialog_kind

    @Property(str, notify=startupDialogChanged)
    def startupDialogTitle(self) -> str:
        return self._startup_dialog_title

    @Property(str, notify=startupDialogChanged)
    def startupDialogSubtitle(self) -> str:
        return self._startup_dialog_subtitle

    @Property(str, notify=startupDialogChanged)
    def startupDialogBody(self) -> str:
        return self._startup_dialog_body

    @Property(str, notify=startupDialogChanged)
    def startupDialogImageUrl(self) -> str:
        return self._startup_dialog_image_url

    @Property(bool, notify=currentPageChanged)
    def hasTutorial(self) -> bool:
        return self._tutorial_key_for_page(self._current_page) is not None

    @Property(bool, notify=sidebarChanged)
    def sidebarOpen(self) -> bool:
        return self._sidebar_open

    @Property(int, notify=sidebarSectionsChanged)
    def sidebarSectionsRevision(self) -> int:
        return self._sidebar_sections_revision

    @Property(bool, notify=tutorialDialogChanged)
    def tutorialDialogVisible(self) -> bool:
        return self._tutorial_dialog_visible

    @Property(str, notify=tutorialDialogChanged)
    def tutorialDialogTitle(self) -> str:
        return self._tutorial_dialog_title

    @Property(str, notify=tutorialDialogChanged)
    def tutorialDialogBody(self) -> str:
        return self._tutorial_dialog_body

    @Slot(str)
    def setCurrentPage(self, page: str) -> None:
        if page == self._current_page:
            return
        previous = self._current_page
        self._current_page = page
        self._log_activity("abrir_pagina", subcategory="paginas", metadata={"page": page, "previousPage": previous})
        self.currentPageChanged.emit()

    @Slot(bool)
    def setSidebarOpen(self, open_: bool) -> None:
        open_ = bool(open_)
        if open_ == self._sidebar_open:
            return
        self._sidebar_open = open_
        self._app_settings()["sidebar_open"] = open_
        save_settings(self.settings)
        self._log_activity("alternar_sidebar", subcategory="sidebar", metadata={"open": open_})
        self.sidebarChanged.emit()

    @Slot(str, result=bool)
    def sidebarSectionExpanded(self, section: str) -> bool:
        return bool(self._sidebar_sections.get(str(section or ""), True))

    @Slot(str, bool)
    def setSidebarSectionExpanded(self, section: str, expanded: bool) -> None:
        section = str(section or "").strip()
        if section not in self._sidebar_sections:
            return
        expanded = bool(expanded)
        if self._sidebar_sections.get(section) == expanded:
            return
        if not expanded and sum(1 for value in self._sidebar_sections.values() if value) <= 1:
            return
        self._sidebar_sections[section] = expanded
        self._app_settings()["sidebar_sections"] = dict(self._sidebar_sections)
        save_settings(self.settings)
        self._sidebar_sections_revision += 1
        self.sidebarSectionsChanged.emit()

    @Slot(str, result=str)
    def assetUrl(self, relative: str) -> str:
        return file_url(resource_dir() / relative)

    @Slot()
    def openFoxhole(self) -> None:
        QDesktopServices.openUrl(QUrl(f"steam://run/{FOXHOLE_APP_ID}"))

    @Slot()
    def refreshFoxholeStatus(self) -> None:
        running = any(process_running(name) for name in FOXHOLE_PROCESS_NAMES)
        self._foxhole_status = "Foxhole is running" if running else "Foxhole is not running"
        self.foxholeStatusChanged.emit()

    @Slot()
    def requestClose(self) -> None:
        self.closeRequested.emit()

    def _t(self, key: str, **kwargs: Any) -> str:
        return self.i18n.translator.t(key, **kwargs)

    def _app_settings(self) -> dict[str, Any]:
        return self.settings.setdefault("app", {})

    def _nav_items(self) -> list[dict[str, str]]:
        items = [
            {"key": "home", "labelKey": "nav.home", "icon": "home", "section": "core"},
            {"key": "chat", "labelKey": "home.chat.title", "icon": "chat", "section": "core"},
            {"key": "autoClicker", "labelKey": "nav.auto_clicker", "icon": "bolt", "section": "automation"},
            {"key": "timeTask", "labelKey": "timetask.nav", "icon": "timer", "section": "automation"},
            {"key": "stockpile", "labelKey": "stockpile.nav", "icon": "database", "section": "logistics"},
            {"key": "production", "labelKey": "production.nav", "icon": "factory", "section": "logistics"},
            {"key": "msuppCalculator", "labelKey": "M-Supp Calc", "icon": "target", "section": "logistics"},
            {"key": "itemSearch", "labelKey": "item_search.nav", "icon": "search", "section": "tools"},
            {"key": "wiki", "labelKey": "wiki.nav", "icon": "wiki.png", "section": "tools"},
            {"key": "identifyItem", "labelKey": "identify.nav", "icon": "target", "section": "tools"},
            {"key": "map", "labelKey": "Mapa", "icon": "map", "section": "tools"},
            {"key": "notifications", "labelKey": "notifications.nav", "icon": "bell", "section": "tools"},
            {"key": "settings", "labelKey": "nav.settings", "icon": "settings", "section": "config"},
            {"key": "personalization", "labelKey": "nav.personalization", "icon": "palette", "section": "config"},
        ]
        catalogs = {language: Translator._load_catalog(language) for language in SUPPORTED_LANGUAGES}
        fallback = Translator._load_catalog("pt")
        for item in items:
            terms = [item["key"], item["labelKey"], item["section"]]
            for catalog in catalogs.values():
                terms.append(catalog.get(item["labelKey"], fallback.get(item["labelKey"], "")))
            item["searchText"] = self._nav_search_text(terms)
        return items

    @staticmethod
    def _nav_search_text(values: list[str]) -> str:
        terms = []
        for value in values:
            text = str(value or "").strip().lower()
            if not text:
                continue
            normalized = "".join(
                char for char in unicodedata.normalize("NFKD", text)
                if not unicodedata.combining(char)
            )
            terms.append(text)
            terms.append(normalized)
        return " ".join(dict.fromkeys(terms))

    def _normalized_sidebar_sections(self, value: Any) -> dict[str, bool]:
        defaults = {
            "core": True,
            "automation": True,
            "logistics": True,
            "tools": True,
            "config": True,
        }
        if isinstance(value, dict):
            for key in defaults:
                defaults[key] = bool(value.get(key, defaults[key]))
        if not any(defaults.values()):
            defaults = {key: True for key in defaults}
        self._app_settings()["sidebar_sections"] = dict(defaults)
        return defaults

    def _tutorial_key_for_page(self, page: str) -> str | None:
        key = self._tutorial_key_by_page.get(page)
        if not key:
            return None
        title_key = f"tutorial.{key}.title"
        content_key = f"tutorial.{key}.content"
        title = self._t(title_key)
        content = self._t(content_key)
        if title == title_key or content == content_key:
            return None
        return key

    @Slot()
    def showTutorial(self) -> None:
        key = self._tutorial_key_for_page(self._current_page)
        if not key:
            return
        self._tutorial_dialog_title = self._t(f"tutorial.{key}.title")
        self._tutorial_dialog_body = self._t(f"tutorial.{key}.content")
        self._tutorial_dialog_visible = True
        self.tutorialDialogChanged.emit()

    @Slot()
    def dismissTutorial(self) -> None:
        self._tutorial_dialog_visible = False
        self.tutorialDialogChanged.emit()

    def _set_startup_dialog(
        self,
        *,
        kind: str,
        title: str,
        subtitle: str,
        body: str,
        image_url: str = "",
    ) -> None:
        self._startup_dialog_kind = kind
        self._startup_dialog_title = title
        self._startup_dialog_subtitle = subtitle
        self._startup_dialog_body = body
        self._startup_dialog_image_url = image_url
        self._startup_dialog_visible = True
        self.startupDialogChanged.emit()

    @Slot()
    def runStartupPrompts(self) -> None:
        if self._startup_dialog_visible:
            return
        self.showReleaseNotesIfNeeded()

    @Slot()
    def showReleaseNotesIfNeeded(self) -> None:
        app_settings = self._app_settings()
        if app_settings.get("last_release_notes_version") != APP_VERSION:
            app_settings["last_release_notes_version"] = APP_VERSION
            save_settings(self.settings)
        self._startup_dialog_visible = False
        self._startup_dialog_kind = ""
        self.startupDialogChanged.emit()

    @Slot()
    def acceptStartupDialog(self) -> None:
        app_settings = self._app_settings()
        kind = self._startup_dialog_kind
        if kind == "tips":
            app_settings["last_tips_version"] = APP_VERSION
            save_settings(self.settings)
            self._startup_dialog_visible = False
            self.startupDialogChanged.emit()
            self.showReleaseNotesIfNeeded()
            return
        if kind == "release":
            app_settings["last_release_notes_version"] = APP_VERSION
            save_settings(self.settings)
        if kind == "error" and getattr(self, "_pending_admin_panel_token", ""):
            self.retryAdminPanelAccess()
            return
        self._startup_dialog_visible = False
        self._startup_dialog_kind = ""
        self.startupDialogChanged.emit()

    @Slot()
    def quit(self) -> None:
        QGuiApplication.quit()
