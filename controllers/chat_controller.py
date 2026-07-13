from __future__ import annotations
from controllers.i18n_controller import I18nController
from controllers.steam_controller import SteamController
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

class ChatController(QObject):
    changed = Signal()
    resultFromWorker = Signal(str, object)

    def __init__(
        self,
        steam: SteamController,
        settings: dict[str, Any],
        i18n: I18nController,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.steam = steam
        self.settings = settings
        self.i18n = i18n
        self._token = ""
        self._status = "Disconnected"
        self._selected_room = ""
        self._selected_room_label = ""
        self._next_message_cursor = ""
        self._loading_older_messages = False
        self._auth_in_flight = False
        self._rooms_in_flight = False
        self._messages_in_flight = False
        self._auth_retry_after = 0.0
        self._current_user_id = ""
        self._current_user_name = ""
        self._current_user_avatar = ""
        self._current_user_provider = ""
        self._current_user_discord_id = ""
        self._current_user_steam_id = ""
        self._profile: dict[str, Any] = {}
        self._profile_loading = False
        self._profile_ready = False
        self._activity_summary: dict[str, Any] = {}
        self._activity_categories: list[dict[str, Any]] = []
        self._activity_actions: list[dict[str, Any]] = []
        self._activity_timeseries: list[dict[str, Any]] = []
        self._activity_users: list[dict[str, Any]] = []
        self._activity_logs: list[dict[str, Any]] = []
        self._activity_user_stats: dict[str, Any] = {}
        self._user_metrics: dict[str, Any] = {}
        self._activity_error = ""
        self._auth_error_category = ""
        self._auth_error_message = ""
        self._auth_error_blocked_reason = ""
        self._auth_error_blocked_at = ""
        self._auth_error_current_level = 0
        self._auth_error_required_level = 0
        self._auth_error_visible = False
        self._auth_denied = False
        self._discord_oauth_in_flight = False
        self._discord_configuration_checked = False
        self._discord_login_required = False
        self._mention_overlay_visible = False
        self._mention_overlay_title = ""
        self._mention_overlay_body = ""
        # Hover card state for per-mention mouseover
        self._mention_hover_visible = False
        self._mention_hover_name = ""
        self._mention_hover_regiment = ""
        self._mention_hover_x = 0.0
        self._mention_hover_y = 0.0
        self._mention_hover_avatar = ""
        self._mention_hover_online = False
        self._started = False
        self._background_mode = False
        self._chat_page_active = False
        self._ws = None
        app_settings = self.settings.setdefault("app", {})
        self._discord_user_settings = self.settings.setdefault("discord", {})
        self._discord_settings = app_settings.setdefault("chat_discord", {})
        seen_message_mentions = app_settings.get("chat_seen_message_mentions", [])
        self._known_message_ids: set[str] = set()
        self._notified_message_ids: set[str] = {str(item) for item in seen_message_mentions if str(item)}
        self._seeded_message_rooms: set[str] = set()
        seen_mentions = app_settings.get("chat_seen_mentions", [])
        self._known_mentions: set[str] = {str(item) for item in seen_mentions if str(item)}
        seen_whispers = app_settings.get("chat_seen_whispers", [])
        self._known_whispers: set[str] = {str(item) for item in seen_whispers if str(item)}
        self._notifications_seeded = False
        self._all_user_rows: list[dict[str, Any]] = []
        self._online_rows: list[dict[str, Any]] = []
        self.rooms = DictListModel(["slug", "label", "unread"], self)
        self.messages = DictListModel(
            ["id", "author", "body", "meta", "rawTime", "sortKey", "mine", "avatar", "mediaUrl", "isGif", "mentioned", "reactions", "replyToMessageId", "replyToAuthor", "replyToBody", "authorDiscordId", "regiment", "role"],
            self,
        )
        self.onlineUsers = DictListModel(["name", "detail", "avatar", "mention", "discordId", "connectedAt", "regiment", "role"], self)
        self.mentionSuggestions = DictListModel(["name", "detail", "avatar", "mention", "discordId"], self)
        self.i18n.changed.connect(self._refresh_room_labels)
        self.resultFromWorker.connect(self._apply_result)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(15000)
        self._refresh_timer.timeout.connect(self.refreshCurrent)
        self._notification_timer = QTimer(self)
        self._notification_timer.setInterval(22000)
        self._notification_timer.timeout.connect(self.refreshNotifications)
        self._presence_timer = QTimer(self)
        self._presence_timer.setInterval(30000)
        self._presence_timer.timeout.connect(self.refreshPresence)
        self._auto_connect_timer = QTimer(self)
        self._auto_connect_timer.timeout.connect(self._maybe_auto_connect)
        self._sync_timer_intervals()

    def _sync_timer_intervals(self) -> None:
        if self._background_mode:
            refresh_interval = 120000
            notification_interval = 90000
            presence_interval = 180000
            auto_connect_interval = 45000
        elif self._chat_page_active:
            refresh_interval = 15000
            notification_interval = 22000
            presence_interval = 30000
            auto_connect_interval = 2500
        else:
            refresh_interval = 60000
            notification_interval = 45000
            presence_interval = 90000
            auto_connect_interval = 15000

        for timer, interval in (
            (self._refresh_timer, refresh_interval),
            (self._notification_timer, notification_interval),
            (self._presence_timer, presence_interval),
            (self._auto_connect_timer, auto_connect_interval),
        ):
            if timer.interval() != interval:
                timer.setInterval(interval)

    def setBackgroundMode(self, background: bool) -> None:
        background = bool(background)
        if self._background_mode == background:
            return
        self._background_mode = background
        self._sync_timer_intervals()

    def setPageActive(self, active: bool) -> None:
        active = bool(active)
        if self._chat_page_active == active:
            return
        self._chat_page_active = active
        self._sync_timer_intervals()


    @Slot()
    def ensureStarted(self) -> None:
        if self._started:
            return
        self._started = True
        try:
            self.steam.changed.connect(self._maybe_auto_connect)
        except RuntimeError:
            pass
        self._auto_connect_timer.start()
        QTimer.singleShot(0, self._maybe_auto_connect)
        self.changed.emit()

    def _ensure_ws(self):
        if self._ws is None:
            from PySide6.QtWebSockets import QWebSocket

            self._ws = QWebSocket()
            self._ws.connected.connect(self._on_ws_connected)
            self._ws.disconnected.connect(self._on_ws_disconnected)
            self._ws.textMessageReceived.connect(self._on_ws_text_received)
        return self._ws

    def _send_ws(self, payload: dict[str, Any]) -> None:
        debug_log("websocket", "send", payload)
        self._ensure_ws().sendTextMessage(json.dumps(payload, ensure_ascii=False))

    def _close_ws(self) -> None:
        if self._ws is not None:
            self._ws.close()



    def logActivity(
        self,
        category: str,
        action: str,
        quantity: int = 1,
        metadata: dict[str, Any] | None = None,
        subcategory: str = "",
    ) -> None:
        token = str(self._token or "").strip()
        category = str(category or "").strip()
        action = str(action or "").strip()
        if not token or not category or not action:
            debug_log("activity", "skip", {"category": category, "action": action, "tokenPresent": bool(token)})
            return
        try:
            quantity_value = int(quantity)
        except (TypeError, ValueError):
            quantity_value = 1
        quantity_value = max(1, min(1_000_000, quantity_value))
        details = dict(metadata or {})
        if subcategory and not details.get("subcategory"):
            details["subcategory"] = str(subcategory)
        details.setdefault("appVersion", APP_VERSION)
        
        try:
            from PySide6.QtGui import QCursor
            pos = QCursor.pos()
            details.setdefault("mouseX", pos.x())
            details.setdefault("mouseY", pos.y())
        except Exception:
            pass
            
        payload = {
            "category": category,
            "action": action,
            "quantity": quantity_value,
            "metadata": details,
            "occurredAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        }

        def worker() -> None:
            try:
                http_json_url("POST", f"{CHAT_API_BASE.rstrip('/')}/{GG_LOGS_PATH.lstrip('/')}", token=token, payload=payload, timeout=8)
                debug_log("activity", "sent", {"category": category, "action": action, "quantity": quantity_value})
            except Exception as exc:
                debug_log("activity", "send failed", {"category": category, "action": action, "error": repr(exc)})

        threading.Thread(target=worker, daemon=True).start()

    @Property(str, notify=changed)
    def apiToken(self) -> str:
        return getattr(self, "_token", "")

    @Property("QVariantMap", notify=changed)
    def userProfile(self) -> dict:
        return getattr(self, "_profile", {})

    @Property(bool, notify=changed)
    def profileLoading(self) -> bool:
        return self._profile_loading

    @Property(bool, notify=changed)
    def profileReady(self) -> bool:
        return self._profile_ready

    @Property(bool, notify=changed)
    def profileGateVisible(self) -> bool:
        if self._token and self._profile_ready and not self._profile_loading:
            return False
        return True

    @Property("QVariantMap", notify=changed)
    def activitySummary(self) -> dict[str, Any]:
        return self._activity_summary

    @Property("QVariantList", notify=changed)
    def activityCategories(self) -> list[dict[str, Any]]:
        return self._activity_categories

    @Property("QVariantList", notify=changed)
    def activityActions(self) -> list[dict[str, Any]]:
        return self._activity_actions

    @Property("QVariantList", notify=changed)
    def activityTimeseries(self) -> list[dict[str, Any]]:
        return self._activity_timeseries

    @Property("QVariantList", notify=changed)
    def activityUsers(self) -> list[dict[str, Any]]:
        return self._activity_users

    @Property("QVariantList", notify=changed)
    def activityLogs(self) -> list[dict[str, Any]]:
        return self._activity_logs

    @Property("QVariantMap", notify=changed)
    def activityUserStats(self) -> dict[str, Any]:
        return self._activity_user_stats

    @Property("QVariantMap", notify=changed)
    def userMetrics(self) -> dict[str, Any]:
        return self._user_metrics

    @Property(str, notify=changed)
    def activityError(self) -> str:
        return self._activity_error

    def _activity_path(self, path_value: str, params: dict[str, Any] | None = None) -> str:
        query = urllib.parse.urlencode(
            [(key, value) for key, value in (params or {}).items() if value not in ("", None)]
        )
        return f"{path_value}?{query}" if query else path_value

    def _request_activity(self, kind: str, path_value: str, timeout: int = 12) -> None:
        if not self._token:
            return

        def run() -> None:
            try:
                result = http_json("GET", path_value, token=self._token, timeout=timeout)
                self.resultFromWorker.emit(kind, result)
            except Exception as exc:
                self.resultFromWorker.emit(f"{kind}-error", str(exc))

        threading.Thread(target=run, daemon=True).start()

    @Slot()
    def loadActivityDashboard(self) -> None:
        if not self._token:
            return
        self._request_activity("activity-summary", "/gg-logs/stats/summary")
        self._request_activity("activity-categories", "/gg-logs/stats/categories")
        self._request_activity("activity-actions", "/gg-logs/stats/actions")
        self._request_activity("activity-timeseries", self._activity_path("/gg-logs/stats/timeseries", {"period": "day", "splitBy": "category"}))
        self._request_activity("activity-users", self._activity_path("/gg-logs/stats/users", {"limit": 10}))

    @Slot(str, str)
    def loadActivityActionsByCategory(self, category: str, splitBy: str = "") -> None:
        params: dict[str, Any] = {}
        if category:
            params["category"] = category
        if splitBy:
            params["splitBy"] = splitBy
        self._request_activity("activity-actions", self._activity_path("/gg-logs/stats/actions", params))

    @Slot(str, str, str)
    def loadActivityTimeseries(self, period: str = "day", splitBy: str = "category", category: str = "") -> None:
        params: dict[str, Any] = {"period": period or "day"}
        if splitBy:
            params["splitBy"] = splitBy
        if category:
            params["category"] = category
        self._request_activity("activity-timeseries", self._activity_path("/gg-logs/stats/timeseries", params))

    @Slot(str, str, str)
    def loadActivityUserStats(self, userId: str = "", fromDate: str = "", toDate: str = "") -> None:
        user_id = str(userId or "").strip() or str(self._profile.get("id") or self._profile.get("discordId") or self._current_user_id or "").strip()
        if not user_id:
            return
        params: dict[str, Any] = {}
        if fromDate:
            params["from"] = fromDate
        if toDate:
            params["to"] = toDate
        self._request_activity("activity-user-stats", self._activity_path(f"/gg-logs/users/{urllib.parse.quote(user_id)}/stats", params))

    @Slot(int, str, str, str, str, str, str)
    def loadActivityLogs(
        self,
        take: int = 50,
        cursor: str = "",
        category: str = "",
        action: str = "",
        userId: str = "",
        fromDate: str = "",
        toDate: str = "",
    ) -> None:
        params: dict[str, Any] = {"take": max(1, min(100, int_or_none(take) or 50))}
        if cursor:
            params["cursor"] = cursor
        if category:
            params["category"] = category
        if action:
            params["action"] = action
        if userId:
            params["userId"] = userId
        if fromDate:
            params["from"] = fromDate
        if toDate:
            params["to"] = toDate
        self._request_activity("activity-logs", self._activity_path("/gg-logs", params))

    @Slot()
    def refreshCurrentUserActivity(self) -> None:
        self.fetchCurrentUserMetrics("month")
        self.loadActivityDashboard()
        self.loadActivityUserStats()
        self.loadActivityLogs(8)

    @Slot(str)
    def fetchCurrentUserMetrics(self, rangeValue: str = "month") -> None:
        range_value = str(rangeValue or "month").strip().lower()
        if range_value not in {"today", "week", "month", "year", "total"}:
            range_value = "month"
        self._request_activity("activity-user-metrics", self._activity_path("/gg-logs/me/metrics", {"range": range_value}))

    @Slot()
    def fetchProfile(self) -> None:
        if not self._token:
            return
        if self._profile_loading:
            return
        self._profile_loading = True
        self.changed.emit()

        def run():
            try:
                res = http_json("GET", "/chat/profile", token=self._token)
                profile = res.get("profile") if isinstance(res.get("profile"), dict) else {}
                if isinstance(profile, dict) and isinstance(res.get("panelAccess"), dict):
                    profile = dict(profile)
                    profile["panelAccess"] = res.get("panelAccess")
                self.resultFromWorker.emit("profile-fetched", profile)
            except Exception as e:
                self.resultFromWorker.emit("profile-error", str(e))
        threading.Thread(target=run, daemon=True).start()

    @Slot(str)
    def updateRegiment(self, regiment: str) -> None:
        if not self._token:
            return
        regiment = normalize_regiment(regiment)
        def run():
            try:
                res = http_json("PATCH", "/chat/profile", token=self._token, payload={"regiment": regiment})
                profile = res.get("profile") if isinstance(res.get("profile"), dict) else {}
                if isinstance(profile, dict) and isinstance(res.get("panelAccess"), dict):
                    profile = dict(profile)
                    profile["panelAccess"] = res.get("panelAccess")
                self.resultFromWorker.emit("profile-updated", profile)
            except Exception as e:
                self.resultFromWorker.emit("profile-error", str(e))
        threading.Thread(target=run, daemon=True).start()

    @Slot(str)
    def postStockpileHelp(self, note: str) -> None:
        if not self._token:
            return
        def run():
            try:
                http_json("POST", "/chat/profile/stock-help", token=self._token, payload={"note": note})
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    @Slot()
    def logout(self) -> None:
        self._token = ""
        self._clear_secure_login_credentials()
        self._discord_user_settings.clear()
        save_settings(self.settings)
        ws = getattr(self, "_ws", None)
        if ws is not None:
            ws.close()
        self._discord_login_required = True
        self._current_user_id = ""
        self._profile = {}
        self._profile_loading = False
        self._profile_ready = False
        self._activity_summary = {}
        self._activity_categories = []
        self._activity_actions = []
        self._activity_timeseries = []
        self._activity_users = []
        self._activity_logs = []
        self._activity_user_stats = {}
        self._user_metrics = {}
        self._activity_error = ""
        self._auth_error_visible = False
        self._auth_denied = False
        self._discord_oauth_in_flight = False
        self._status = "Disconnected"
        self.changed.emit()



    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def selectedRoom(self) -> str:
        return self._selected_room

    @Property(str, notify=changed)
    def selectedRoomLabel(self) -> str:
        return self._selected_room_label

    @Property(bool, notify=changed)
    def hasOlderMessages(self) -> bool:
        return bool(self._next_message_cursor)

    @Property(bool, notify=changed)
    def loadingOlderMessages(self) -> bool:
        return self._loading_older_messages

    @Property(str, notify=changed)
    def currentUserName(self) -> str:
        return self._current_user_name or self._saved_discord_name() or self.steam.personaName

    @Property(str, notify=changed)
    def currentUserAvatar(self) -> str:
        return self._current_user_avatar or self._saved_discord_avatar() or self.steam.avatarUrl

    @Property(str, notify=changed)
    def currentProvider(self) -> str:
        return self._current_user_provider or ("discord" if self._saved_discord_id() else "steam")

    @Property(str, notify=changed)
    def discordId(self) -> str:
        return self._current_user_discord_id or self._saved_discord_id()

    @Property(str, notify=changed)
    def currentUserId(self) -> str:
        return self._current_user_id or self.discordId or self.steam.steamId or ""

    @Property("QVariantList", notify=changed)
    def roomsRows(self) -> list[dict[str, Any]]:
        return self.rooms.items()

    @Property("QVariantList", notify=changed)
    def messagesRows(self) -> list[dict[str, Any]]:
        return self.messages.items()

    @Property("QVariantList", notify=changed)
    def onlineRows(self) -> list[dict[str, Any]]:
        return self.onlineUsers.items()

    @Property("QVariantList", notify=changed)
    def mentionSuggestionRows(self) -> list[dict[str, Any]]:
        return self.mentionSuggestions.items()

    @Property(QObject, constant=True)
    def roomsModel(self) -> QObject:
        return self.rooms

    @Property(QObject, constant=True)
    def messagesModel(self) -> QObject:
        return self.messages

    @Property(QObject, constant=True)
    def onlineUsersModel(self) -> QObject:
        return self.onlineUsers

    @Property(QObject, constant=True)
    def mentionSuggestionsModel(self) -> QObject:
        return self.mentionSuggestions

    @Property(bool, notify=changed)
    def connected(self) -> bool:
        return bool(self._token and (self._current_user_discord_id or self._saved_discord_id()))

    @Property(bool, notify=changed)
    def discordOAuthConfigured(self) -> bool:
        return bool(self._discord_client_id())

    @Property(str, notify=changed)
    def discordRedirectUri(self) -> str:
        return discord_redirect_uri(self._discord_redirect_port())

    @Property(bool, notify=changed)
    def discordConfigurationChecked(self) -> bool:
        return self._discord_configuration_checked

    @Property(bool, notify=changed)
    def discordLoginRequired(self) -> bool:
        return self._discord_login_required

    @Property(bool, notify=changed)
    def secureReloginRequired(self) -> bool:
        return bool((self._has_secure_auto_login_key() or self._saved_discord_id()) and not self._token)

    @Property(bool, notify=changed)
    def authInFlight(self) -> bool:
        return self._auth_in_flight

    @Property(bool, notify=changed)
    def authErrorVisible(self) -> bool:
        return self._auth_error_visible

    @Property(str, notify=changed)
    def authErrorCategory(self) -> str:
        return self._auth_error_category

    @Property(str, notify=changed)
    def authErrorMessage(self) -> str:
        return self._auth_error_message

    @Property(str, notify=changed)
    def authErrorBlockedReason(self) -> str:
        return self._auth_error_blocked_reason

    @Property(str, notify=changed)
    def authErrorBlockedAt(self) -> str:
        return self._auth_error_blocked_at

    @Property(int, notify=changed)
    def authErrorCurrentLevel(self) -> int:
        return self._auth_error_current_level

    @Property(int, notify=changed)
    def authErrorRequiredLevel(self) -> int:
        return self._auth_error_required_level

    @Property(bool, notify=changed)
    def authDenied(self) -> bool:
        return self._auth_denied

    @Property(bool, notify=changed)
    def discordOAuthInFlight(self) -> bool:
        return self._discord_oauth_in_flight

    @Property(bool, notify=changed)
    def canOpenAdminPanel(self) -> bool:
        profile = getattr(self, "_profile", {})
        if not isinstance(profile, dict):
            return False
        access = normalize_panel_access(profile.get("panelAccess"), profile)
        return bool(access.get("canLoginPanel"))

    @Property(bool, notify=changed)
    def mentionOverlayVisible(self) -> bool:
        return self._mention_overlay_visible

    @Property(str, notify=changed)
    def mentionOverlayTitle(self) -> str:
        return self._mention_overlay_title

    @Property(str, notify=changed)
    def mentionOverlayBody(self) -> str:
        return self._mention_overlay_body

    @Property(bool, notify=changed)
    def mentionHoverVisible(self) -> bool:
        return getattr(self, "_mention_hover_visible", False)

    @Property(str, notify=changed)
    def mentionHoverName(self) -> str:
        return getattr(self, "_mention_hover_name", "")

    @Property(str, notify=changed)
    def mentionHoverRegiment(self) -> str:
        return getattr(self, "_mention_hover_regiment", "")

    @Property(str, notify=changed)
    def mentionHoverAvatar(self) -> str:
        return getattr(self, "_mention_hover_avatar", "")

    @Property(bool, notify=changed)
    def mentionHoverOnline(self) -> bool:
        return bool(getattr(self, "_mention_hover_online", False))

    @Property(float, notify=changed)
    def mentionHoverX(self) -> float:
        return float(getattr(self, "_mention_hover_x", 0.0))

    @Property(float, notify=changed)
    def mentionHoverY(self) -> float:
        return float(getattr(self, "_mention_hover_y", 0.0))

    @Property("QStringList", constant=True)
    def quickEmojis(self) -> list[str]:
        return list(QUICK_EMOJIS)

    def _t(self, key: str, **kwargs: Any) -> str:
        return self.i18n.translator.t(key, **kwargs)

    def _saved_discord_id(self) -> str:
        return deobfuscate_string(str(self._discord_user_settings.get("id") or "").strip())

    def _saved_discord_name(self) -> str:
        return deobfuscate_string(str(self._discord_user_settings.get("displayName") or self._discord_user_settings.get("username") or "").strip())

    def _saved_discord_avatar(self) -> str:
        return deobfuscate_string(str(self._discord_user_settings.get("avatar") or "").strip())

    def _discord_client_id(self) -> str:
        return str(os.environ.get("DISCORD_CLIENT_ID") or self._discord_settings.get("clientId") or DISCORD_DEFAULT_CLIENT_ID).strip()

    def _discord_redirect_port(self) -> int:
        try:
            port = int(os.environ.get("DISCORD_REDIRECT_PORT") or self._discord_settings.get("redirectPort") or DISCORD_DEFAULT_REDIRECT_PORT)
        except (TypeError, ValueError):
            return DISCORD_DEFAULT_REDIRECT_PORT
        return port if 1024 <= port <= 65535 else DISCORD_DEFAULT_REDIRECT_PORT

    def _save_discord_profile(self, user: dict[str, Any]) -> None:
        discord_id = str(user.get("discordId") or self._current_user_discord_id or self._saved_discord_id()).strip()
        if not discord_id:
            return
        self._discord_user_settings["id"] = obfuscate_string(discord_id)
        name = str(
            user.get("displayName")
            or user.get("globalName")
            or user.get("username")
            or user.get("name")
            or user.get("personaname")
            or self._current_user_name
            or self.steam.personaName
        ).strip()
        if name:
            self._discord_user_settings["displayName"] = obfuscate_string(name)
        username = str(user.get("username") or "").strip()
        if username:
            self._discord_user_settings["username"] = obfuscate_string(username)
        avatar = user_avatar_url(user).strip()
        if avatar:
            self._discord_user_settings["avatar"] = obfuscate_string(avatar)
        save_settings(self.settings)

    def _auth_with_discord_oauth(self) -> dict[str, Any]:
        client_id = self._discord_client_id()
        if not client_id:
            raise RuntimeError(self._t("home.chat.discord_config_missing", uri=self.discordRedirectUri))
        port = self._discord_redirect_port()
        redirect_uri = discord_redirect_uri(port)
        state = secrets.token_urlsafe(24)
        verifier = secrets.token_urlsafe(64)
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "identify",
            "state": state,
            "code_challenge": pkce_challenge(verifier),
            "code_challenge_method": "S256",
            "prompt": "consent",
        }
        auth_url = f"{DISCORD_AUTHORIZE_URL}?{urllib.parse.urlencode(query)}"
        code = wait_for_discord_oauth_code(state, port, auth_url=auth_url, language=self.i18n.translator.language)
        payload = {
            "code": code,
            "codeVerifier": verifier,
            "redirectUri": redirect_uri,
            "appVersion": APP_VERSION,
            "app_version": APP_VERSION,
        }
        result = http_json_url(
            "POST",
            f"{CHAT_API_BASE.rstrip('/')}/{CHAT_DISCORD_OAUTH_AUTH_PATH.lstrip('/')}",
            payload=payload,
            timeout=20,
        )
        debug_login_response(CHAT_DISCORD_OAUTH_AUTH_PATH, result)
        return result

    def _discord_auth_payload(self, discord_id: str) -> dict[str, str]:
        payload: dict[str, str] = {"discordId": discord_id}
        steam_id = self.steam.steamId
        if steam_id:
            payload["steamId"] = steam_id
        display_name = self._saved_discord_name() or self.steam.personaName
        if display_name:
            payload["displayName"] = display_name
            payload["personaname"] = display_name
        username = str(self._discord_settings.get("username") or "").strip()
        if username:
            payload["username"] = username
        avatar = self._saved_discord_avatar()
        if avatar:
            payload["avatar"] = avatar
            payload["avatarmedium"] = avatar
            payload["avatarfull"] = avatar
        return payload

    def _discord_auth_payload_from_profile(self, user: dict[str, Any]) -> dict[str, str]:
        discord_id = str(user.get("discordId") or user.get("id") or "").strip()
        payload = self._discord_auth_payload(discord_id)
        field_map = {
            "username": "username",
            "globalName": "globalName",
            "displayName": "displayName",
            "discriminator": "discriminator",
            "avatar": "avatar",
            "avatarfull": "avatarfull",
            "avatarmedium": "avatarmedium",
            "discordAvatar": "discordAvatar",
        }
        for target, source in field_map.items():
            value = str(user.get(source) or "").strip()
            if value:
                payload[target] = value
        return payload

    def _apply_current_user_profile(self, user: dict[str, Any]) -> None:
        user = merge_panel_profile(user, user.get("panelAccess"))
        self._current_user_id = str(user.get("id") or self._current_user_id or "")
        self._current_user_provider = str(
            user.get("provider")
            or self._current_user_provider
            or ("discord" if user.get("discordId") or self._saved_discord_id() else "steam")
        )
        self._current_user_discord_id = str(user.get("discordId") or self._current_user_discord_id or self._saved_discord_id())
        self._current_user_steam_id = str(user.get("steamId") or self._current_user_steam_id or self.steam.steamId)
        self._current_user_name = str(
            user.get("displayName")
            or user.get("globalName")
            or user.get("name")
            or user.get("personaName")
            or user.get("personaname")
            or user.get("nickname")
            or user.get("username")
            or self._current_user_name
            or self._saved_discord_name()
            or self.steam.personaName
        )
        self._current_user_avatar = user_avatar_url(user) or self._current_user_avatar or self._saved_discord_avatar() or self.steam.avatarUrl
        if self._current_user_discord_id:
            self._save_discord_profile(user)

    def _secure_login_credentials(self) -> tuple[str, str]:
        credentials = secure_load_credentials()
        if not credentials:
            return '', ''
        auto_login_key, access_password = credentials
        return str(auto_login_key or access_password or '').strip(), str(access_password or auto_login_key or '').strip()

    def _has_secure_auto_login_key(self) -> bool:
        auto_login_key, _access_password = self._secure_login_credentials()
        return bool(auto_login_key)

    def _clear_secure_login_credentials(self) -> None:
        secure_clear_credentials()

    def _save_secure_login_credentials_from_auth_result(self, result: dict[str, Any]) -> None:
        auto_login_key = str(
            result.get("autoLoginKey")
            or result.get("auto_login_key")
            or result.get("accessPassword")
            or result.get("access_password")
            or ""
        ).strip()
        access_password = str(
            result.get("accessPassword")
            or result.get("access_password")
            or auto_login_key
        ).strip()
        if not auto_login_key:
            return
        try:
            secure_save_credentials(auto_login_key, access_password or auto_login_key)
        except Exception as exc:
            debug_log("auth", "secure credential save failed", {"error": repr(exc)})

    def _auth_with_auto_login(self) -> dict[str, Any]:
        auto_login_key, access_password = self._secure_login_credentials()
        if not auto_login_key:
            raise RuntimeError('autoLoginKey e obrigatorio')
        payload = {
            'autoLoginKey': auto_login_key,
            'accessPassword': access_password or auto_login_key,
            'appVersion': APP_VERSION,
            'app_version': APP_VERSION,
        }
        result = http_json('POST', CHAT_AUTO_LOGIN_AUTH_PATH, payload=payload, timeout=12)
        debug_login_response(CHAT_AUTO_LOGIN_AUTH_PATH, result)
        return result

    def _verify_discord_app_access(self, result: dict[str, Any]) -> dict[str, Any]:
        token = str(result.get("token") or result.get("accessToken") or "")
        user = result.get("user") if isinstance(result.get("user"), dict) else result.get("profile")
        if not isinstance(user, dict):
            raise RuntimeError("A API não retornou perfil de usuário no login.")
        discord_id = str(user.get("discordId") or user.get("discord_id") or "").strip()
        if not discord_id:
            raise RuntimeError("A API não retornou o Discord ID validado no login.")
        user = dict(user)
        user["discordId"] = discord_id

        access = result.get("panelAccess") or user.get("panelAccess")
        profile = merge_panel_profile(user, access)

        if not panel_access_allows_app_login(profile):
            discord_id = str(profile.get("discordId") or profile.get("discord_id") or "").strip()
            if discord_id:
                access_result = http_json("POST", "/chat/panel/access", token=token or None, payload={"discordId": discord_id}, timeout=12)
                debug_login_response("/chat/panel/access", access_result)
                profile = merge_panel_profile(
                    access_result.get("user") if isinstance(access_result.get("user"), dict) else profile,
                    access_result,
                )

        if not panel_access_allows_app_login(profile):
            access = profile.get("panelAccess") if isinstance(profile.get("panelAccess"), dict) else {}
            level = int_or_none(access.get("accessLevel") or profile.get("panelAccessLevel") or profile.get("accessLevel"))
            reason = str(access.get("message") or access.get("reason") or f"nível {level if level is not None else 0}")
            raise RuntimeError(f"Acesso negado: {reason}")

        result = dict(result)
        result["user"] = profile
        result["panelAccess"] = profile.get("panelAccess")
        return result

    def _request_users(self) -> dict[str, Any]:
        last_error: Exception | None = None
        for path in CHAT_USERS_PATHS:
            try:
                return http_json("GET", path, token=self._token)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(str(last_error) if last_error else "chat users failed")

    def _request_online_users(self) -> dict[str, Any]:
        discord_id = self._current_user_discord_id or self._saved_discord_id()
        if discord_id:
            try:
                return http_json("POST", "/chat/presence/ping", token=self._token, payload={"discordId": discord_id}, timeout=10)
            except Exception:
                pass
        if self._current_user_id:
            try:
                return http_json("POST", "/chat/presence/ping", token=self._token, payload={"userId": self._current_user_id}, timeout=10)
            except Exception:
                pass
        steam_id = self._current_user_steam_id or self.steam.steamId
        if steam_id:
            try:
                return http_json("POST", "/chat/presence/ping", token=self._token, payload={"steamId": steam_id}, timeout=10)
            except Exception:
                pass
        last_error: Exception | None = None
        for path in CHAT_ONLINE_PATHS:
            try:
                return http_json("GET", path, token=self._token, timeout=10)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(str(last_error) if last_error else "chat online users failed")

    def _request_messages(self, slug: str, cursor: str = "") -> dict[str, Any]:
        path = f"/chat/chats/{urllib.parse.quote(slug)}/messages?take=50"
        if cursor:
            path = f"{path}&cursor={urllib.parse.quote(cursor)}"
        return http_json("GET", path, token=self._token)

    @Slot()
    def connectWithDiscord(self) -> None:
        self.ensureStarted()
        self._auth_retry_after = 0.0
        self._connect_with_discord(allow_oauth=True)

    @Slot()
    def autoConnectWithSavedDiscord(self) -> None:
        self.ensureStarted()
        if self._has_secure_auto_login_key():
            self._discord_configuration_checked = True
            self._discord_login_required = False
            self.changed.emit()
            self._connect_with_discord(allow_oauth=False)
            return
        self._discord_configuration_checked = True
        self._discord_login_required = True
        self._status = self._t("home.chat.no_discord")
        self.changed.emit()

    def _connect_with_discord(self, *, allow_oauth: bool = False) -> None:
        self.ensureStarted()
        if self._auth_in_flight:
            return
        if self._token:
            if not self._profile_ready and not self._profile_loading:
                self.fetchProfile()
            self.refreshRooms()
            self.refreshPresence()
            self.refreshNotifications()
            return
        now = time.monotonic()
        if now < self._auth_retry_after:
            retry_seconds = int(max(1, self._auth_retry_after - now))
            self._status = self._t("home.chat.auth_needed") + f" ({retry_seconds}s)"
            self.changed.emit()
            return
        has_auto_login_key = self._has_secure_auto_login_key()
        if not has_auto_login_key and not allow_oauth:
            self._discord_configuration_checked = True
            self._discord_login_required = True
            self._status = self._t("home.chat.no_discord")
            self.changed.emit()
            return
        if allow_oauth and not self._discord_client_id():
            self._status = self._t("home.chat.discord_config_missing", uri=self.discordRedirectUri)
            self.changed.emit()
            return

        def worker() -> None:
            try:
                if not allow_oauth and has_auto_login_key:
                    result = self._auth_with_auto_login()
                else:
                    result = self._auth_with_discord_oauth()
                result = self._verify_discord_app_access(result)
                self.resultFromWorker.emit("auth", result)
            except Exception as exc:
                message = str(exc)
                lowered = message.lower()
                if not allow_oauth and any(marker in lowered for marker in ("reauthrequired", "reauth required", "auto-login invalida", "auto-login inválida", "chave de auto-login invalida", "chave de auto-login inválida", "permissao foi revogado", "permissão foi revogado")):
                    self._clear_secure_login_credentials()
                if "access_denied" in message or "oauth_cancelled" in message:
                    message = self._t("home.chat.discord_cancelled")
                self.resultFromWorker.emit("auth-error", self._t("home.chat.auth_error", message=message))

        self._auth_in_flight = True
        self._auth_error_visible = False
        self._auth_denied = False
        self._discord_oauth_in_flight = allow_oauth
        if has_auto_login_key and not allow_oauth:
            self._discord_login_required = False
            self._status = self._t("home.chat.authenticating_discord")
        else:
            self._status = self._t("home.chat.discord_opening")
        self.changed.emit()
        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def connectWithSteam(self) -> None:
        self.connectWithDiscord()

    @Slot()
    def _maybe_auto_connect(self) -> None:
        if not self._started:
            return
        if self._token:
            if self._auto_connect_timer.isActive():
                self._auto_connect_timer.stop()
            return
        if self._auth_in_flight:
            return
        if self._has_secure_auto_login_key():
            self._discord_configuration_checked = True
            self._discord_login_required = False
            self.changed.emit()
            self._connect_with_discord(allow_oauth=False)
            return
        self._discord_configuration_checked = True
        self._discord_login_required = True
        self._status = self._t("home.chat.no_discord")
        self.changed.emit()

    @Slot()
    def refreshRooms(self) -> None:
        self.ensureStarted()
        if not self._token:
            self.connectWithDiscord()
            return
        if self._rooms_in_flight:
            return
        self._rooms_in_flight = True

        def worker() -> None:
            try:
                self.resultFromWorker.emit("rooms", http_json("GET", "/chat/chats", token=self._token))
            except Exception as exc:
                self.resultFromWorker.emit("error", self._t("home.chat.chat_error", message=str(exc)))
                return
            try:
                self.resultFromWorker.emit("users", self._request_users())
            except Exception as exc:
                self.resultFromWorker.emit("users-error", str(exc))
            try:
                self.resultFromWorker.emit("online", self._request_online_users())
            except Exception as exc:
                self.resultFromWorker.emit("online-error", str(exc))
            finally:
                self.resultFromWorker.emit("rooms-finished", {})

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def refreshPresence(self) -> None:
        if not self._token:
            return

        def worker() -> None:
            try:
                self.resultFromWorker.emit("online", self._request_online_users())
            except Exception as exc:
                self.resultFromWorker.emit("online-error", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def refreshCurrent(self) -> None:
        if not self._token:
            return
        if self._selected_room:
            self.selectRoom(self._selected_room)
        else:
            self.refreshRooms()

    @Slot()
    def refreshNotifications(self) -> None:
        if not self._token:
            return

        def worker() -> None:
            try:
                result = http_json("GET", "/chat/notifications?unreadOnly=true&take=50", token=self._token, timeout=10)
                self.resultFromWorker.emit("notifications", result)
            except Exception:
                try:
                    result = http_json("GET", "/chat/mentions/notifications?unreadOnly=true&take=50", token=self._token, timeout=10)
                    self.resultFromWorker.emit("notifications", {"mentions": result.get("mentions") or []})
                except Exception as exc:
                    self.resultFromWorker.emit("notification-error", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str)
    def selectRoom(self, slug: str) -> None:
        room_changed = slug != self._selected_room
        self._selected_room = slug
        self._selected_room_label = self._room_label(slug)
        debug_log("chat", "select room", {"slug": slug, "label": self._selected_room_label, "changed": room_changed})
        if room_changed:
            self._next_message_cursor = ""
            self._loading_older_messages = False
            self.messages.set_items([])
        self.changed.emit()
        if not self._token or not slug:
            return
        if self._messages_in_flight:
            return
        self._messages_in_flight = True

        def worker() -> None:
            try:
                self.resultFromWorker.emit(
                    "messages",
                    {
                        "slug": slug,
                        "appendOlder": False,
                        "result": self._request_messages(slug),
                    },
                )
            except Exception as exc:
                self.resultFromWorker.emit("error", self._t("home.chat.message_error", message=str(exc)))
            finally:
                self.resultFromWorker.emit("messages-finished", {})

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def loadOlderMessages(self) -> None:
        if not self._token or not self._selected_room or not self._next_message_cursor or self._loading_older_messages:
            return
        if self._messages_in_flight:
            return
        slug = self._selected_room
        cursor = self._next_message_cursor
        self._loading_older_messages = True
        self._messages_in_flight = True
        self._status = self._t("home.chat.loading_older")
        self.changed.emit()

        def worker() -> None:
            try:
                self.resultFromWorker.emit(
                    "messages",
                    {
                        "slug": slug,
                        "appendOlder": True,
                        "result": self._request_messages(slug, cursor),
                    },
                )
            except Exception as exc:
                self.resultFromWorker.emit("message-error", self._t("home.chat.message_error", message=str(exc)))
            finally:
                self.resultFromWorker.emit("messages-finished", {})

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str)
    def sendMessage(self, body: str) -> None:
        if not self._token or not self._selected_room or not body.strip():
            return
        content = body.strip()
        self._send_ws({
            "type": "send_message",
            "chatSlug": self._selected_room,
            "content": content
        })
        self.logActivity(
            "chat",
            "enviar_mensagem",
            metadata={
                "subcategory": "mensagens",
                "chatSlug": self._selected_room,
                "length": len(content),
                "mentions": len(MENTION_RE.findall(content)),
            },
        )

    @Slot(str, str)
    def sendMessageReply(self, body: str, replyToMessageId: str) -> None:
        if not self._token or not self._selected_room or not body.strip():
            return
        content = body.strip()
        self._send_ws({
            "type": "send_message",
            "chatSlug": self._selected_room,
            "content": content,
            "replyToMessageId": replyToMessageId
        })
        self.logActivity(
            "chat",
            "responder_mensagem",
            metadata={
                "subcategory": "mensagens",
                "chatSlug": self._selected_room,
                "replyToMessageId": str(replyToMessageId or ""),
                "length": len(content),
                "mentions": len(MENTION_RE.findall(content)),
            },
        )

    @Slot(str, str)
    def reactMessage(self, messageId: str, emoji: str) -> None:
        if not self._token or not messageId or not emoji:
            return
        self._send_ws({
            "type": "react_message",
            "messageId": messageId,
            "emoji": emoji
        })
        self.logActivity(
            "chat",
            "reagir_mensagem",
            metadata={
                "subcategory": "reacoes",
                "messageId": str(messageId or ""),
                "emoji": str(emoji or ""),
            },
        )


    @Slot(str)
    def sendGif(self, url: str) -> None:
        if not self._token or not self._selected_room or not str(url or "").strip():
            return
        media_url = str(url or "").strip()
        self._send_ws({
            "type": "send_message",
            "chatSlug": self._selected_room,
            "content": media_url
        })
        self.logActivity(
            "chat",
            "enviar_gif",
            metadata={
                "subcategory": "mensagens",
                "chatSlug": self._selected_room,
                "urlHost": urllib.parse.urlparse(media_url).netloc,
            },
        )

    @Slot(str)
    def updateMentionSuggestions(self, text: str) -> None:
        token = self._mention_token(text)
        if token is None:
            self.mentionSuggestions.set_items([])
            self.changed.emit()
            return
        token_lower = token.casefold()
        rows = [
            row
            for row in self._online_rows
            if token_lower in str(row.get("name", "")).casefold() or token_lower in str(row.get("mention", "")).casefold()
        ][:8]
        self.mentionSuggestions.set_items(rows)
        self.changed.emit()

    @Slot(str, str, result=str)
    def applyMention(self, text: str, mention: str) -> str:
        match = None
        for candidate in MENTION_RE.finditer(text):
            match = candidate
        if match and match.end() == len(text):
            prefix = text[: match.start()]
            suffix = text[match.end() :]
            return f"{prefix}@{mention} {suffix}"
        spacer = "" if not text or text.endswith(" ") else " "
        return f"{text}{spacer}@{mention} "

    @Slot(str, result="QVariantList")
    def parseMessageSegments(self, text: str) -> list[dict]:
        """Split a message into segments: plain text and mention segments.

        Uses the combined user list (online + all users) and prioritizes longer
        user names first to avoid partial matches (e.g. 'Ryan Luca' before 'Ryan').
        Returns a list of dicts: {"text": str, "mention": str, "user": dict}
        """
        if not text:
            return []
        source = str(text)
        lower = source.casefold()
        debug_mentions = bool(os.environ.get("FELB_DEBUG_MENTIONS"))

        # build candidate map: mention/name -> user row
        user_rows = self._merge_user_rows(self._online_rows, self._all_user_rows)
        candidate_map: dict[str, dict] = {}
        for row in user_rows:
            raw = str(row.get("mention") or row.get("name") or "").strip()
            if not raw:
                continue
            key = raw.lstrip("@").strip()
            if not key:
                continue
            candidate_map[key.casefold()] = row

        # sort candidates by length desc to prefer longest match
        candidates = sorted(candidate_map.keys(), key=lambda s: len(s), reverse=True)

        occupied = [False] * len(source)
        matches: list[tuple[int, int, str]] = []

        for cand in candidates:
            token = "@" + cand
            start = lower.find(token)
            while start != -1:
                end = start + len(token)
                # boundary check before '@'
                if start == 0 or not lower[start - 1].isalnum():
                    # avoid overlaps
                    if not any(occupied[i] for i in range(start, end)):
                        matches.append((start, end, cand))
                        for i in range(start, end):
                            occupied[i] = True
                start = lower.find(token, start + 1)

        if not matches:
            if debug_mentions:
                print(f"[mentions] no matches for: {source}", flush=True)
            return [{"text": source, "mention": "", "user": {}}]

        matches.sort()
        segments: list[dict] = []
        pos = 0
        for start, end, cand in matches:
            if pos < start:
                segments.append({"text": source[pos:start], "mention": "", "user": {}})
            # use original-cased text for display
            mention_text = source[start + 1 : end]
            user = candidate_map.get(cand)
            segments.append({"text": source[start:end], "mention": mention_text, "user": user or {}})
            pos = end
        if pos < len(source):
            segments.append({"text": source[pos:], "mention": "", "user": {}})
        if debug_mentions:
            try:
                found = [source[s:e] for s, e, _ in matches]
            except Exception:
                found = matches
            print(f"[mentions] parsed segments for: {source} -> mentions={found}", flush=True)
        return segments

    @Slot(str, str, str, bool, float, float)
    def showMentionHover(self, name: str, regiment: str, avatar: str, online: bool, x: float, y: float) -> None:
        self._mention_hover_name = str(name or "")
        self._mention_hover_regiment = str(regiment or "")
        self._mention_hover_avatar = str(avatar or "")
        self._mention_hover_online = bool(online)
        try:
            self._mention_hover_x = float(x)
            self._mention_hover_y = float(y)
        except Exception:
            self._mention_hover_x = 0.0
            self._mention_hover_y = 0.0
        self._mention_hover_visible = True
        if os.environ.get("FELB_DEBUG_MENTIONS"):
            print(
                f"[mentions] showMentionHover name={self._mention_hover_name!r} regiment={self._mention_hover_regiment!r} avatar={self._mention_hover_avatar!r} online={self._mention_hover_online} x={self._mention_hover_x} y={self._mention_hover_y}",
                flush=True,
            )
        self.changed.emit()

    @Slot()
    def dismissMentionHover(self) -> None:
        self._mention_hover_visible = False
        if os.environ.get("FELB_DEBUG_MENTIONS"):
            print("[mentions] dismissMentionHover", flush=True)
        self.changed.emit()

    @Slot()
    def dismissMentionOverlay(self) -> None:
        self._mention_overlay_visible = False
        self.changed.emit()

    @Slot(str, object)
    def _classify_auth_error(self, payload: object) -> dict[str, Any]:
        result: dict[str, Any] = {
            "category": "UNKNOWN",
            "message": "Erro desconhecido",
            "blockedReason": "",
            "blockedAt": "",
            "currentAccessLevel": 0,
            "requiredAccessLevel": 0,
        }
        
        if isinstance(payload, dict):
            msg = str(payload.get("message") or payload.get("error") or payload.get("detail") or "Erro desconhecido")
            result["message"] = msg
            
            status = int_or_none(payload.get("status"))
            
            if msg.lower().startswith("conta gg bloqueada"):
                result["category"] = "BLOCKED"
                result["blockedReason"] = str(payload.get("blockedReason") or "Violação dos Termos de Serviço")
                result["blockedAt"] = str(payload.get("blockedAt") or "")
                return result
                
            denied_markers = (
                "acesso negado", "access denied", "application access denied",
                "acceso denegado", "acceso a la aplicacion denegado",
                "acces refuse", "acces a l'application refuse",
                "permissao insuficiente", "permissões", "permission", "revogado", "revoked"
            )
            
            if status == 403:
                if any(m in msg.lower() for m in denied_markers):
                    if "permiss" in msg.lower() or "permission" in msg.lower():
                        result["category"] = "PERMISSION"
                    else:
                        result["category"] = "ACCESS_DENIED"
                        result["currentAccessLevel"] = int_or_none(payload.get("accessLevel")) or 0
                        result["requiredAccessLevel"] = int_or_none(payload.get("requiredAccessLevel")) or PANEL_REQUIRED_ACCESS_LEVEL
                elif "desativada" in msg.lower() or "deactivated" in msg.lower():
                    result["category"] = "NOT_FOUND"
                else:
                    result["category"] = "ACCESS_DENIED"
                return result
                
            if status == 401:
                result["category"] = "REAUTH"
                return result
                
            if status == 404:
                result["category"] = "NOT_FOUND"
                return result
                
            lower_msg = msg.lower()
            if "bloqueada" in lower_msg or "blocked" in lower_msg:
                result["category"] = "BLOCKED"
            elif any(m in lower_msg for m in denied_markers):
                if "permiss" in lower_msg:
                    result["category"] = "PERMISSION"
                else:
                    result["category"] = "ACCESS_DENIED"
            elif "sessão" in lower_msg or "session" in lower_msg or "token" in lower_msg or "auto-login" in lower_msg or "invalida" in lower_msg or "invalid" in lower_msg:
                result["category"] = "REAUTH"
            elif "encontrado" in lower_msg or "not found" in lower_msg:
                result["category"] = "NOT_FOUND"
                
        else:
            msg = str(payload)
            result["message"] = msg
            lower_msg = msg.lower()
            if "bloqueada" in lower_msg or "blocked" in lower_msg:
                result["category"] = "BLOCKED"
            elif any(m in lower_msg for m in ("acesso negado", "access denied")):
                result["category"] = "ACCESS_DENIED"
            elif "permiss" in lower_msg:
                result["category"] = "PERMISSION"
            elif "sessão" in lower_msg or "session" in lower_msg or "token" in lower_msg or "auto-login" in lower_msg or "invalida" in lower_msg or "invalid" in lower_msg:
                result["category"] = "REAUTH"
            elif "encontrado" in lower_msg or "not found" in lower_msg:
                result["category"] = "NOT_FOUND"
                
        return result

    def _apply_result(self, kind: str, payload: object) -> None:
        if kind.startswith("activity-") and kind.endswith("-error"):
            self._activity_error = str(payload or "")
            self.changed.emit()
            return
        if kind == "activity-summary" and isinstance(payload, dict):
            self._activity_error = ""
            self._activity_summary = payload
            self.changed.emit()
            return
        if kind == "activity-categories" and isinstance(payload, dict):
            self._activity_error = ""
            self._activity_categories = list(payload.get("categories") or [])
            self.changed.emit()
            return
        if kind == "activity-actions" and isinstance(payload, dict):
            self._activity_error = ""
            self._activity_actions = list(payload.get("actions") or [])
            self.changed.emit()
            return
        if kind == "activity-timeseries" and isinstance(payload, dict):
            self._activity_error = ""
            self._activity_timeseries = list(payload.get("points") or [])
            self.changed.emit()
            return
        if kind == "activity-users" and isinstance(payload, dict):
            self._activity_error = ""
            self._activity_users = list(payload.get("users") or [])
            self.changed.emit()
            return
        if kind == "activity-logs" and isinstance(payload, dict):
            self._activity_error = ""
            self._activity_logs = list(payload.get("logs") or [])
            self.changed.emit()
            return
        if kind == "activity-user-stats" and isinstance(payload, dict):
            self._activity_error = ""
            self._activity_user_stats = payload
            self.changed.emit()
            return
        if kind == "activity-user-metrics" and isinstance(payload, dict):
            self._activity_error = ""
            self._user_metrics = payload
            account = payload.get("account")
            if isinstance(account, dict):
                self._profile = merge_panel_profile(account, account.get("panelAccess"))
                self._apply_current_user_profile(self._profile)
                self._profile_ready = True
            recent_logs = payload.get("recentLogs")
            if isinstance(recent_logs, list):
                self._activity_logs = recent_logs
            actions = payload.get("actions")
            if isinstance(actions, dict):
                self._activity_user_stats = actions
                self._activity_categories = list(actions.get("categories") or [])
                self._activity_actions = list(actions.get("actions") or [])
            self.changed.emit()
            return
        if kind == "auth" and isinstance(payload, dict):
            self._auth_in_flight = False
            self._auth_error_visible = False
            self._auth_denied = False
            self._discord_oauth_in_flight = False
            self._auth_retry_after = 0.0
            self._discord_configuration_checked = True
            self._discord_login_required = False
            self._profile_ready = False
            self._token = str(payload.get("token") or payload.get("accessToken") or "")
            self._save_secure_login_credentials_from_auth_result(payload)
            auth_flow = str(payload.get("authFlow") or "")
            auth_action = "login_auto" if "auto" in auth_flow else "login_oauth" if "oauth" in auth_flow else "login"
            self.logActivity(
                "auth",
                auth_action,
                metadata={
                    "subcategory": "login",
                    "authFlow": auth_flow,
                    "provider": str((payload.get("user") or {}).get("provider") or "discord") if isinstance(payload.get("user"), dict) else "discord",
                },
            )
            user = payload.get("user") or payload.get("profile") or {}
            if isinstance(user, dict):
                user = merge_panel_profile(user, payload.get("panelAccess") or user.get("panelAccess"))
                self._apply_current_user_profile(user)
            else:
                self._current_user_id = ""
                self._current_user_provider = "discord" if self._saved_discord_id() else "steam"
                self._current_user_discord_id = self._saved_discord_id()
                self._current_user_name = self._saved_discord_name() or self.steam.personaName
                self._current_user_avatar = self._saved_discord_avatar() or self.steam.avatarUrl
                self._current_user_steam_id = self.steam.steamId
            self._status = self._t("home.chat.connected") if self._token else "Connected without token"
            if self._token:
                # Set initial profile from the auth response
                if isinstance(user, dict) and user:
                    self._profile = user

                # Fetch fresh profile async
                self.fetchProfile()
                self.loadActivityDashboard()
                self.loadActivityUserStats()
                self.loadActivityLogs(8)

                self._connect_ws()

                if self._auto_connect_timer.isActive():
                    self._auto_connect_timer.stop()
                self._notifications_seeded = False
                self._seeded_message_rooms.clear()
                self._refresh_timer.start()
                self._notification_timer.start()
                self._presence_timer.start()
                self.refreshNotifications()
            self.refreshRooms()
        elif kind == "auth-error":
            self._auth_in_flight = False
            self._discord_oauth_in_flight = False
            self._profile_loading = False
            self._profile_ready = False
            self._discord_configuration_checked = True
            self._discord_login_required = True
            error_data = self._classify_auth_error(payload)
            self._auth_error_visible = True
            self._auth_error_category = error_data["category"]
            self._auth_error_message = error_data["message"]
            self._auth_error_blocked_reason = error_data.get("blockedReason", "")
            self._auth_error_blocked_at = error_data.get("blockedAt", "")
            self._auth_error_current_level = error_data.get("currentAccessLevel", 0)
            self._auth_error_required_level = error_data.get("requiredAccessLevel", 0)
            self._auth_denied = error_data["category"] == "ACCESS_DENIED"
            import time
            self._auth_retry_after = time.monotonic() + 30
            self._status = error_data["message"]
            if error_data["category"] in ("REAUTH", "NOT_FOUND"):
                self._clear_secure_login_credentials()
        elif kind == "rooms" and isinstance(payload, dict):
            rooms = payload.get("chats") or payload.get("rooms") or []
            self.rooms.set_items([self._room_to_row(room) for room in rooms])
            self._status = f"{len(rooms)} chat rooms loaded"
            if self._selected_room:
                self._selected_room_label = self._room_label(self._selected_room)
            if not self._selected_room and rooms:
                first = self._room_to_row(rooms[0])
                self.selectRoom(str(first["slug"]))
        elif kind == "rooms-finished":
            self._rooms_in_flight = False
        elif kind == "users" and isinstance(payload, dict):
            users = payload.get("users") or []
            rows = [self._user_to_row(user) for user in users]
            self._all_user_rows = rows
        elif kind == "online" and isinstance(payload, dict):
            users = payload.get("onlineUsers") or payload.get("users") or []
            import time
            from datetime import datetime
            
            if not hasattr(self, '_user_online_since'):
                self._user_online_since = {}
            current_time = time.time()
            
            online_rows = []
            for u in users:
                row = self._user_to_row(u)
                
                iso_time = u.get("lastLoginAt")
                if iso_time and isinstance(iso_time, str):
                    try:
                        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
                        row["connectedAt"] = float(dt.timestamp())
                    except Exception:
                        row["connectedAt"] = current_time
                else:
                    uid = str(row.get("discordId") or row.get("mention") or row.get("name") or "")
                    if uid and uid not in self._user_online_since:
                        self._user_online_since[uid] = current_time
                    row["connectedAt"] = float(self._user_online_since.get(uid, current_time))
                
                online_rows.append(row)
            
            online_rows.sort(key=lambda r: float(r.get("connectedAt", 0.0)), reverse=True)
            self._online_rows = online_rows
            self.onlineUsers.set_items(online_rows)
        elif kind == "messages" and isinstance(payload, dict):
            slug = str(payload.get("slug") or self._selected_room)
            if slug != self._selected_room:
                return
            result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
            append_older = bool(payload.get("appendOlder"))
            messages = (result.get("messages") or []) if isinstance(result, dict) else []
            rows = normalize_messages(
                messages,
                self._current_user_name or self._saved_discord_name() or self.steam.personaName,
                self._current_user_steam_id or self.steam.steamId,
                self._current_user_discord_id or self._saved_discord_id(),
            )
            current_rows = [self.messages.get(index) for index in range(self.messages.count())]
            if append_older or current_rows:
                rows = merge_message_rows(rows, current_rows)
            seed_mentions = append_older or slug not in self._seeded_message_rooms
            self._notify_mentions(rows, slug=slug, seed=seed_mentions)
            self._seeded_message_rooms.add(slug)
            if len(rows) > 200:
                rows = rows[-200:]
            if not same_message_rows(rows, current_rows):
                self.messages.set_items(rows)
            self._next_message_cursor = str(result.get("nextCursor") or "") if isinstance(result, dict) else ""
            self._loading_older_messages = False
            self._status = self._t("home.chat.ready")
        elif kind == "messages-finished":
            self._messages_in_flight = False
        elif kind == "sent":
            self._status = self._t("home.chat.sent")
            self.selectRoom(self._selected_room)
        elif kind == "profile-fetched" or kind == "profile-updated":
            self._profile_loading = False
            if isinstance(payload, dict):
                # If it's my own profile (no ID passed, or ID matches me), save to self._profile
                if not payload.get("id") or payload.get("id") == self._current_user_id or kind == "profile-updated":
                    self._profile = payload
                    self._apply_current_user_profile(payload)
                    self._profile_ready = True
                    self._discord_login_required = False
                    self._status = self._t("home.chat.connected")
                    self.loadActivityDashboard()
                    self.loadActivityUserStats()
                    self.loadActivityLogs(8)
                    self.changed.emit()
                else:
                    # Notify UI about someone else's profile
                    self.resultFromWorker.emit("other-profile-ready", payload)
        elif kind == "profile-error":
            self._profile_loading = False
            self._profile_ready = False
            self._status = self._t("home.chat.auth_error", message=str(payload))
        elif kind == "notifications" and isinstance(payload, dict):
            self._apply_notifications(payload)
        elif kind == "notification-error":
            pass
        elif kind == "users-error":
            pass
        elif kind == "online-error":
            pass
        elif kind == "message-error":
            self._messages_in_flight = False
            self._loading_older_messages = False
            self._status = str(payload)
        elif kind == "error":
            self._messages_in_flight = False
            self._loading_older_messages = False
            self._status = str(payload)
        self.changed.emit()

    def _room_to_row(self, room: dict[str, Any]) -> dict[str, Any]:
        slug = str(room.get("slug") or room.get("id") or "")
        raw_label = str(room.get("name") or room.get("label") or slug or "Room")
        return {
            "slug": slug,
            "label": self._translated_room_label(slug, raw_label),
            "rawLabel": raw_label,
            "unread": int(room.get("unreadCount") or room.get("unread") or 0),
        }

    def _room_label(self, slug: str) -> str:
        for index in range(self.rooms.count()):
            row = self.rooms.get(index)
            if row.get("slug") == slug:
                return str(row.get("label") or slug)
        return slug

    def _room_translation_key(self, slug: str, label: str = "") -> str:
        value = f"{slug} {label}".strip().casefold()
        normalized = unicodedata.normalize("NFKD", value)
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
        tokens = set(normalized.split())
        if "global" in tokens:
            return "home.chat.room_global"
        if tokens & {"discussion", "discusion", "discussao", "discussaoo", "discussione", "debate"}:
            return "home.chat.room_discussion"
        if tokens & {"logi", "logistica", "logistics", "logistique", "logisticaa"}:
            return "home.chat.room_logi"
        if tokens & {"faci", "facility", "facilities", "instalacoes", "instalaciones", "installations"}:
            return "home.chat.room_faci"
        if tokens & {"front", "frente", "linha", "frontline"}:
            return "home.chat.room_front"
        return ""

    def _translated_room_label(self, slug: str, label: str = "") -> str:
        key = self._room_translation_key(slug, label)
        return self._t(key) if key else (label or slug or "Room")

    @Slot()
    def _refresh_room_labels(self) -> None:
        rows = []
        for row in self.rooms.items():
            raw_label = str(row.get("rawLabel") or row.get("label") or row.get("slug") or "")
            rows.append(
                {
                    **row,
                    "label": self._translated_room_label(str(row.get("slug") or ""), raw_label),
                    "rawLabel": raw_label,
                }
            )
        if rows:
            self.rooms.set_items(rows)
        if self._selected_room:
            self._selected_room_label = self._room_label(self._selected_room)
        self.changed.emit()

    @staticmethod
    def _merge_user_rows(primary: list[dict[str, Any]], secondary: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in [*primary, *secondary]:
            key = str(row.get("mention") or row.get("name") or row.get("detail") or "").casefold()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(row)
        return merged

    @staticmethod
    def _user_to_row(user: dict[str, Any]) -> dict[str, Any]:
        name = user_display_name(user)
        mention = str(user.get("mention") or user.get("username") or user.get("globalName") or name).strip().lstrip("@")
        detail = str(user.get("status") or "").strip()
        if not detail and user.get("provider") == "discord":
            detail = f"@{mention}" if mention else str(user.get("discordId") or "")
        if not detail:
            detail = str(user.get("steamId") or user.get("discordId") or "")
        
        access = user.get("panelAccess") if isinstance(user.get("panelAccess"), dict) else {}
        access_level = int_or_none(access.get("accessLevel") or user.get("panelAccessLevel") or user.get("accessLevel"))
        role = normalize_panel_role(user.get("role"), access_level)
        
        return {
            "name": name,
            "detail": detail,
            "avatar": str(user.get("avatarUrl") or user.get("avatar") or user.get("avatarfull") or user.get("avatarmedium") or ""),
            "mention": mention,
            "discordId": str(user.get("discordId") or ""),
            "connectedAt": float(user.get("_connectedAt") or 0.0),
            "regiment": normalize_regiment(user.get("regiment")),
            "role": role,
        }

    @Slot(str, result=bool)
    def userIsOnline(self, mentionOrId: str) -> bool:
        if not mentionOrId:
            return False
        key = str(mentionOrId).strip().lstrip("@").casefold()
        for row in self._online_rows:
            if not isinstance(row, dict):
                continue
            m = str(row.get("mention") or "").strip().lstrip("@").casefold()
            if m and m == key:
                return True
            # check by discordId / name
            if str(row.get("discordId") or "").strip() == mentionOrId:
                return True
            if str(row.get("name") or "").strip().casefold() == key:
                return True
        return False

    @staticmethod
    def _mention_token(text: str) -> str | None:
        match = None
        for candidate in MENTION_RE.finditer(text):
            match = candidate
        if not match or match.end() != len(text):
            return None
        return match.group(1)

    def _notify_mentions(self, rows: list[dict[str, Any]], *, slug: str = "", seed: bool = False) -> None:
        seen_changed = False
        for row in rows:
            identity = str(row.get("id") or "")
            if not identity:
                continue
            new_message = identity not in self._known_message_ids
            if new_message:
                self._known_message_ids.add(identity)
            if row.get("mine") or not row.get("mentioned"):
                continue
            if seed or identity in self._notified_message_ids:
                if identity not in self._notified_message_ids:
                    self._notified_message_ids.add(identity)
                    seen_changed = True
                continue
            if not new_message:
                continue
            self._notified_message_ids.add(identity)
            seen_changed = True
            self._show_mention(
                self._t("home.chat.mention_title"),
                self._t("home.chat.mention_body", user=row.get("author") or "User", room=self._room_label(slug) or self._selected_room_label or self._selected_room or "-"),
            )
        if seen_changed:
            self._persist_seen_message_mentions()

    def _apply_notifications(self, payload: dict[str, Any]) -> None:
        mentions = payload.get("mentions") or []
        whispers = payload.get("whispers") or []
        if not self._notifications_seeded:
            mentions_changed = False
            whispers_changed = False
            for mention in mentions:
                mention_id = self._notification_identity(mention)
                if not mention_id:
                    continue
                if mention_id not in self._known_mentions:
                    self._known_mentions.add(mention_id)
                    mentions_changed = True
                threading.Thread(target=lambda mid=mention_id: self._mark_mention_read(mid), daemon=True).start()
            for whisper in whispers:
                whisper_id = self._notification_identity(whisper)
                if whisper_id and whisper_id not in self._known_whispers:
                    self._known_whispers.add(whisper_id)
                    whispers_changed = True
            self._notifications_seeded = True
            if mentions_changed:
                self._persist_seen_mentions()
            if whispers_changed:
                self._persist_seen_whispers()
            return

        self._notifications_seeded = True
        seen_changed = False
        for mention in mentions:
            mention_id = self._notification_identity(mention)
            if mention_id and mention_id in self._known_mentions:
                continue
            if mention_id:
                self._known_mentions.add(mention_id)
                seen_changed = True
            user = mention.get("mentionedBy") or mention.get("fromUser") or mention.get("user") or {}
            chat = mention.get("chat") or {}
            user_name = self._user_to_row(user if isinstance(user, dict) else {})["name"]
            room = str(chat.get("name") or chat.get("slug") or self._selected_room_label or "-") if isinstance(chat, dict) else self._selected_room_label
            self._show_mention(self._t("home.chat.mention_title"), self._t("home.chat.mention_body", user=user_name, room=room))
            if mention_id:
                threading.Thread(target=lambda mid=mention_id: self._mark_mention_read(mid), daemon=True).start()
        if seen_changed:
            self._persist_seen_mentions()
        whispers_changed = False
        for whisper in whispers:
            whisper_id = self._notification_identity(whisper)
            if whisper_id and whisper_id in self._known_whispers:
                continue
            if whisper_id:
                self._known_whispers.add(whisper_id)
                whispers_changed = True
            sender = whisper.get("fromUser") or whisper.get("sender") or whisper.get("user") or {}
            user_name = self._user_to_row(sender if isinstance(sender, dict) else {})["name"]
            self._show_mention(self._t("home.chat.whisper_title"), self._t("home.chat.whisper_body", user=user_name))
            break
        if whispers_changed:
            self._persist_seen_whispers()

    @staticmethod
    def _notification_identity(notification: dict[str, Any]) -> str:
        return str(notification.get("id") or notification.get("_id") or notification.get("messageId") or notification.get("notificationId") or "")

    def _mark_mention_read(self, mention_id: str) -> None:
        try:
            http_json("PATCH", f"/chat/mentions/{urllib.parse.quote(mention_id)}/read", token=self._token, timeout=8)
        except Exception:
            pass

    def _persist_seen_mentions(self) -> None:
        app_settings = self.settings.setdefault("app", {})
        app_settings["chat_seen_mentions"] = list(self._known_mentions)[-250:]
        save_settings(self.settings)

    def _persist_seen_whispers(self) -> None:
        app_settings = self.settings.setdefault("app", {})
        app_settings["chat_seen_whispers"] = list(self._known_whispers)[-250:]
        save_settings(self.settings)

    def _persist_seen_message_mentions(self) -> None:
        app_settings = self.settings.setdefault("app", {})
        app_settings["chat_seen_message_mentions"] = list(self._notified_message_ids)[-500:]
        save_settings(self.settings)

    def _show_mention(self, title: str, body: str) -> None:
        app_settings = self.settings.get("app", {})
        if app_settings.get("chat_mention_sound_enabled", True):
            self._play_mention_sound()
        if not app_settings.get("chat_mention_overlay_enabled", True):
            return
        self._mention_overlay_title = title
        self._mention_overlay_body = body
        self._mention_overlay_visible = True
        QTimer.singleShot(6500, self.dismissMentionOverlay)

    @staticmethod
    def _play_mention_sound() -> None:
        try:
            if os.name == "nt":
                import winsound

                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass


    def _connect_ws(self) -> None:
        if not self._token: return
        ws = self._ensure_ws()
        ws.close()
        url = QUrl(f"{CHAT_WS_BASE}/ws/chat?token={self._token}")
        debug_log("websocket", "connect", {"url": f"{CHAT_WS_BASE}/ws/chat", "tokenPresent": bool(self._token)})
        ws.open(url)

    @Slot()
    def _on_ws_connected(self) -> None:
        debug_log("websocket", "connected", {"selectedRoom": self._selected_room})
        self._status = self._t("home.chat.connected")
        self.changed.emit()
        if self._selected_room:
            self._send_ws({"type": "join_chat", "chatSlug": self._selected_room})

    @Slot()
    def _on_ws_disconnected(self) -> None:
        debug_log("websocket", "disconnected", {"started": self._started, "tokenPresent": bool(self._token)})
        if self._started and self._token:
            QTimer.singleShot(5000, self._connect_ws)

    @Slot(str)
    def _on_ws_text_received(self, text: str) -> None:
        try:
            data = json.loads(text)
        except Exception:
            debug_log("websocket", "receive invalid json", {"text": text})
            return
        dtype = data.get("type")
        debug_log("websocket", "receive", {"type": dtype, "payload": data})
        if dtype == "message_created":
            msg = data.get("message")
            if msg:
                self._handle_ws_message(msg)
        elif dtype == "message_updated" or dtype == "message_reaction_updated":
            msg = data.get("message")
            if msg:
                self._handle_ws_message_update(msg)
        elif dtype == "message_deleted":
            msg_id = data.get("messageId") or (data.get("message") or {}).get("id")
            if msg_id:
                self._handle_ws_message_delete(msg_id)

    def _handle_ws_message(self, msg: dict) -> None:
        debug_log("chat", "message created", {"id": msg.get("id") or msg.get("_id"), "chatSlug": msg.get("chatSlug")})
        rows = normalize_messages([msg], self.currentUserName, self._current_user_steam_id, self.discordId)
        if not rows: return
        row = rows[0]
        current_rows = [self.messages.get(i) for i in range(self.messages.count())]
        current_rows.append(row)
        if len(current_rows) > 200:
            current_rows = current_rows[-200:]
        self.messages.set_items(current_rows)
        self.changed.emit()

    def _handle_ws_message_update(self, msg: dict) -> None:
        debug_log("chat", "message updated", {"id": msg.get("id") or msg.get("_id")})
        rows = normalize_messages([msg], self.currentUserName, self._current_user_steam_id, self.discordId)
        if not rows: return
        row = rows[0]
        current_rows = [self.messages.get(i) for i in range(self.messages.count())]
        for i, r in enumerate(current_rows):
            if str(r.get("id")) == str(row["id"]):
                current_rows[i] = row
                break
        self.messages.set_items(current_rows)
        self.changed.emit()

    def _handle_ws_message_delete(self, msg_id: str) -> None:
        debug_log("chat", "message deleted", {"id": msg_id})
        current_rows = [self.messages.get(i) for i in range(self.messages.count())]
        current_rows = [r for r in current_rows if str(r.get("id")) != str(msg_id)]
        self.messages.set_items(current_rows)
        self.changed.emit()


    @Slot()
    def shutdown(self) -> None:
        self._refresh_timer.stop()
        self._notification_timer.stop()
        self._presence_timer.stop()
        self._auto_connect_timer.stop()
        self._close_ws()
