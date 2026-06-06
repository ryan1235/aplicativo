from __future__ import annotations

import base64
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
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from PySide6.QtNetwork import QNetworkAccessManager
from PySide6.QtWebSockets import QWebSocket
from PySide6.QtCore import (
    QAbstractListModel,
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

from app_paths import extracted_dir, resolve_writable_path, resource_dir, settings_path
from app_update import UpdateInfo, check_latest_release, download_update, launch_updater
from auto_clicker import ACTION_KEYS, HOTKEYS, MOUSE_BUTTONS, POINT, RECT, AutoClicker
from identify_service import (
    ImageGrab as identify_image_grab,
    cv2 as identify_cv2,
    dependencies_status as identify_dependencies_status,
    grab_clipboard_image,
    grab_screen_image,
    index_icon_templates,
    np as identify_np,
    prepare_image,
    prepare_image_path,
    scan_image,
    scan_image_path,
)
from i18n import SUPPORTED_LANGUAGES, Translator, normalize_language
from macro_recorder import MACRO_DIR, MacroRecorder
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
from settings_store import load_settings, save_settings, selected_language
from steam_profile import SteamProfile, get_local_steam_profile
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


APP_TITLE = "GG Coalition"
APP_VERSION = "1.8.6"
UPDATE_REPO = "ryan1235/aplicativo"
FOXHOLE_APP_ID = "505460"
FOXHOLE_PROCESS_NAMES = ("war-win64-shipping.exe", "foxhole.exe")
FOXHOLE_PATH_HINTS = ("\\steamapps\\common\\foxhole\\", "/steamapps/common/foxhole/")
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SQUADLOCK_SECONDS = 30 * 60
BASE_DIR = Path(__file__).resolve().parent
CHAT_API_BASE = "https://archpixel.squareweb.app"
CHAT_WS_BASE = "wss://archpixel.squareweb.app"
CHAT_DISCORD_AUTH_PATHS = ("/chat/auth/discord", "/chat/auth/login")
CHAT_STEAM_AUTH_PATHS = ("/chat/auth/steam", "/chat/auth/local")
CHAT_USERS_PATHS = ("/chat/users", "/chat/users/online")
CHAT_ONLINE_PATHS = ("/chat/presence/online", "/chat/users/online")
DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = f"{DISCORD_API_BASE}/oauth2/token"
DISCORD_USER_URL = f"{DISCORD_API_BASE}/users/@me"
DISCORD_DEFAULT_REDIRECT_PORT = 53624
DISCORD_DEFAULT_REDIRECT_PATH = "/discord/callback"
IMAGE_URL_RE = re.compile(r"https?://[^\s<>\"]+\.(?:png|jpe?g|webp|gif)(?:\?[^\s<>\"]*)?", re.IGNORECASE)
MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_.-]{1,32})")
QUICK_EMOJIS = ("👍", "❤️", "😂", "🔥", "✅", "🫡", "👀", "🚚", "⚠️", "🎯")
SOUND_DIRS = (BASE_DIR / "efeitos sonoros", BASE_DIR / "audio")
SOUND_EXTENSIONS = (".wav", ".mp3", ".wma")
VALID_CLOSE_ACTIONS = ("ask", "tray", "exit")
STARTUP_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
OVERLAY_PALETTES = {
    "Azul": {"bg": "#071426", "panel": "#12233d", "accent": "#8ab4ff"},
    "Verde": {"bg": "#071a18", "panel": "#10342e", "accent": "#5eead4"},
    "Roxo": {"bg": "#141125", "panel": "#2a214b", "accent": "#c4b5fd"},
    "Vermelho": {"bg": "#211016", "panel": "#431926", "accent": "#ff8aa0"},
}
OVERLAY_COLOR_LABEL_KEYS = {
    "Azul": "overlay.color_blue",
    "Verde": "overlay.color_green",
    "Roxo": "overlay.color_purple",
    "Vermelho": "overlay.color_red",
}


def file_url(path: str | Path) -> str:
    return QUrl.fromLocalFile(str(Path(path).resolve())).toString()

def obfuscate_string(text: str) -> str:
    if not text:
        return text
    return base64.b64encode(text.encode("utf-8")[::-1]).decode("utf-8")

def deobfuscate_string(text: str) -> str:
    if not text:
        return text
    try:
        return base64.b64decode(text.encode("utf-8"))[::-1].decode("utf-8")
    except Exception:
        return text

def now_milliseconds() -> int:
    return int(time.time() * 1000)


def now_label() -> str:
    return datetime.now().strftime("%H:%M:%S")


def format_duration(seconds: int) -> str:
    minutes, remainder = divmod(max(0, int(seconds)), 60)
    return f"{minutes:02d}:{remainder:02d}"


def sound_path(name: str) -> Path | None:
    for directory in SOUND_DIRS:
        for extension in SOUND_EXTENSIONS:
            path = directory / f"{name}{extension}"
            if path.exists():
                return path
    return None


def play_sound(name: str) -> None:
    path = sound_path(name)
    if not path:
        return
    if path.suffix.lower() == ".wav":
        try:
            import winsound

            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception:
            pass
    try:
        alias = f"gg_{name}_{int(time.time() * 1000)}"
        winmm = ctypes.windll.winmm
        winmm.mciSendStringW(f"close {alias}", None, 0, None)
        winmm.mciSendStringW(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
        winmm.mciSendStringW(f"play {alias}", None, 0, None)
        close_timer = threading.Timer(10.0, lambda: winmm.mciSendStringW(f"close {alias}", None, 0, None))
        close_timer.daemon = True
        close_timer.start()
    except Exception:
        pass


def startup_target_and_args(settings: dict[str, Any]) -> tuple[Path, str]:
    app_settings = settings.get("app", {})
    background_arg = " --background" if app_settings.get("start_in_background", False) else ""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve(), background_arg.strip()

    python_exe = Path(sys.executable).resolve()
    pythonw = python_exe.with_name("pythonw.exe")
    if pythonw.exists():
        python_exe = pythonw
    return python_exe, f'"{(BASE_DIR / "felb_app.py").resolve()}"{background_arg}'


def startup_command(settings: dict[str, Any]) -> str:
    target, arguments = startup_target_and_args(settings)
    return f'"{target}" {arguments}'.strip() if arguments else f'"{target}"'


def launch_target() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return BASE_DIR / "felb_app.py"


def runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return launch_target().parent
    return BASE_DIR


def startup_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def startup_shortcut_path() -> Path:
    return startup_dir() / f"{APP_TITLE}.lnk"


def startup_task_name() -> str:
    return f"{APP_TITLE} Startup"


def schtasks_executable() -> str:
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidate = windir / "System32" / "schtasks.exe"
    return str(candidate) if candidate.exists() else "schtasks"


def remove_startup_task() -> None:
    subprocess.run(
        [
            schtasks_executable(),
            "/Delete",
            "/TN",
            startup_task_name(),
            "/F",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def remove_startup_shortcuts() -> None:
    for path in (startup_shortcut_path(), startup_dir() / f"{APP_TITLE}.cmd", startup_dir() / f"{APP_TITLE}.bat"):
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


def set_start_with_windows(enabled: bool, settings: dict[str, Any]) -> None:
    if os.name != "nt":
        raise RuntimeError("Windows startup is only available on Windows.")

    import winreg

    remove_startup_task()
    remove_startup_shortcuts()
    if enabled:
        command = startup_command(settings)
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, STARTUP_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_TITLE, 0, winreg.REG_SZ, command)
        return

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_TITLE)
    except FileNotFoundError:
        pass


class DictListModel(QAbstractListModel):
    def __init__(self, roles: list[str], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._role_names = {Qt.UserRole + index + 1: role.encode("utf-8") for index, role in enumerate(roles)}
        self._roles = {name: role for role, name in self._role_names.items()}
        self._items: list[dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802 - Qt API
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:  # noqa: N802 - Qt API
        if not index.isValid() or index.row() < 0 or index.row() >= len(self._items):
            return None
        role_name = self._role_names.get(role)
        if not role_name:
            return None
        return self._items[index.row()].get(role_name.decode("utf-8"))

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802 - Qt API
        return self._role_names

    def set_items(self, items: list[dict[str, Any]]) -> None:
        if items == self._items:
            return
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def append(self, item: dict[str, Any]) -> None:
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        self.endInsertRows()

    @Slot(result=int)
    def count(self) -> int:
        return len(self._items)

    @Slot(int, result="QVariant")
    def get(self, row: int) -> dict[str, Any]:
        if row < 0 or row >= len(self._items):
            return {}
        return dict(self._items[row])

    def items(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._items]


class I18nController(QObject):
    changed = Signal()

    def __init__(self, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.translator = Translator(selected_language(settings))
        self.languages = DictListModel(["code", "name", "flag", "active"], self)
        self._revision = 0
        self._refresh_languages()

    def _refresh_languages(self) -> None:
        current = self.language
        self.languages.set_items(
            [
                {
                    "code": code,
                    "name": data["name"],
                    "flag": file_url(BASE_DIR / "img" / "flags" / f"{data['flag']}.png"),
                    "active": code == current,
                }
                for code, data in SUPPORTED_LANGUAGES.items()
            ]
        )

    @Property(str, notify=changed)
    def language(self) -> str:
        return self.translator.language

    @Property(int, notify=changed)
    def revision(self) -> int:
        return self._revision

    @Slot(str, result=str)
    def t(self, key: str) -> str:
        return self.translator.t(key)

    @Slot(str)
    def setLanguage(self, language: str) -> None:
        language = normalize_language(language)
        self.settings["language"] = language
        save_settings(self.settings)
        self.translator.set_language(language)
        self._revision += 1
        self._refresh_languages()
        self.changed.emit()


class AppController(QObject):
    currentPageChanged = Signal()
    foxholeStatusChanged = Signal()
    closeRequested = Signal()
    startupDialogChanged = Signal()
    tutorialDialogChanged = Signal()

    def __init__(self, i18n: I18nController, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.settings = settings
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
        self._tutorial_key_by_page = {
            "home": "inicio",
            "chat": "chat",
            "autoClicker": "ferramentas",
            "timeTask": "time_task",
            "stockpile": "stockpile",
            "production": "production_calculator",
            "itemSearch": "item_search",
            "identifyItem": "identify_item",
            "notifications": "notificacoes",
            "settings": "configuracoes",
        }
        self.navItems = DictListModel(["key", "labelKey", "icon", "section"], self)
        self.navItems.set_items(
            [
                {"key": "home", "labelKey": "nav.home", "icon": "home", "section": "core"},

                {"key": "chat", "labelKey": "home.chat.title", "icon": "chat", "section": "core"},
                {"key": "autoClicker", "labelKey": "nav.auto_clicker", "icon": "bolt", "section": "automation"},
                {"key": "timeTask", "labelKey": "timetask.nav", "icon": "timer", "section": "automation"},
                {"key": "stockpile", "labelKey": "stockpile.nav", "icon": "database", "section": "logistics"},
                {"key": "production", "labelKey": "production.nav", "icon": "factory", "section": "logistics"},
                {"key": "itemSearch", "labelKey": "item_search.nav", "icon": "search", "section": "tools"},
                {"key": "identifyItem", "labelKey": "identify.nav", "icon": "target", "section": "tools"},
                {"key": "notifications", "labelKey": "notifications.nav", "icon": "bell", "section": "tools"},
                {"key": "settings", "labelKey": "nav.settings", "icon": "settings", "section": "config"},
            ]
        )
        self._foxhole_timer = QTimer(self)
        self._foxhole_timer.timeout.connect(self.refreshFoxholeStatus)
        self._foxhole_timer.start(5000)
        self.refreshFoxholeStatus()

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
        self._current_page = page
        self.currentPageChanged.emit()

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
        app_settings = self._app_settings()
        if app_settings.get("last_tips_version") != APP_VERSION:
            tips_image = BASE_DIR / "img" / "dicas.png"
            self._set_startup_dialog(
                kind="tips",
                title=self._t("startup.tips.title"),
                subtitle="",
                body=self._t("startup.tips.content"),
                image_url=file_url(tips_image) if tips_image.exists() else "",
            )
            return
        self.showReleaseNotesIfNeeded()

    @Slot()
    def showReleaseNotesIfNeeded(self) -> None:
        app_settings = self._app_settings()
        if app_settings.get("last_release_notes_version") == APP_VERSION:
            self._startup_dialog_visible = False
            self.startupDialogChanged.emit()
            return
        self._set_startup_dialog(
            kind="release",
            title=self._t("release.heading", version=APP_VERSION),
            subtitle=self._t("release.subtitle"),
            body=self._t("release.body"),
        )

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
        self._startup_dialog_visible = False
        self._startup_dialog_kind = ""
        self.startupDialogChanged.emit()

    @Slot()
    def quit(self) -> None:
        QGuiApplication.quit()


class SteamController(QObject):
    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._profile = SteamProfile()
        self._status = "Searching Steam profile..."
        self.refresh()

    @Property(str, notify=changed)
    def personaName(self) -> str:
        return self._profile.persona_name or self._profile.account_name or "Unknown Steam user"

    @Property(str, notify=changed)
    def steamId(self) -> str:
        return self._profile.steam_id or ""

    @Property(str, notify=changed)
    def avatarUrl(self) -> str:
        return file_url(self._profile.avatar_path) if self._profile.avatar_path else ""


    @Property("QVariantMap", notify=changed)
    def userProfile(self) -> dict:
        return getattr(self, "_profile", {})

    @Slot()
    def logout(self) -> None:
        self._token = ""
        self._discord_user_settings.clear()
        save_settings(self.settings)
        self._ws.close()
        self._discord_login_required = True
        self._current_user_id = ""
        self._profile = {}
        self._status = "Disconnected"
        self.changed.emit()



    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Slot()
    def refresh(self) -> None:
        def worker() -> None:
            profile = get_local_steam_profile()
            self._profile = profile
            self._status = "Steam profile loaded" if profile.steam_id else "Steam profile not found"
            self.changed.emit()

        threading.Thread(target=worker, daemon=True).start()


class SettingsController(QObject):
    changed = Signal()

    def __init__(self, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._revision = 0
        self._status = ""

    def _app_settings(self) -> dict[str, Any]:
        return self.settings.setdefault("app", {})

    def _notification_settings(self) -> dict[str, Any]:
        return self.settings.setdefault("notifications", {})

    def _save(self) -> None:
        save_settings(self.settings)
        self._revision += 1
        self.changed.emit()

    def _app_bool(self, key: str, default: bool = True) -> bool:
        return bool(self._app_settings().get(key, default))

    @Property(int, notify=changed)
    def revision(self) -> int:
        return self._revision

    @Property(str, notify=changed)
    def closeAction(self) -> str:
        action = str(self._app_settings().get("close_action", "ask"))
        return action if action in VALID_CLOSE_ACTIONS else "ask"

    @Property(bool, notify=changed)
    def startWithWindows(self) -> bool:
        return bool(self._app_settings().get("start_with_windows", False))

    @Property(str, notify=changed)
    def startupCommand(self) -> str:
        return startup_command(self.settings)


    @Property("QVariantMap", notify=changed)
    def userProfile(self) -> dict:
        return getattr(self, "_profile", {})

    @Slot()
    def logout(self) -> None:
        self._token = ""
        self._discord_user_settings.clear()
        save_settings(self.settings)
        self._ws.close()
        self._discord_login_required = True
        self._current_user_id = ""
        self._profile = {}
        self._status = "Disconnected"
        self.changed.emit()



    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=changed)
    def stockpileSoundEnabled(self) -> bool:
        return self._app_bool("stockpile_sound_enabled")

    @Property(bool, notify=changed)
    def squadlockSoundEnabled(self) -> bool:
        return self._app_bool("squadlock_sound_enabled")

    @Property(bool, notify=changed)
    def chatMentionOverlayEnabled(self) -> bool:
        return self._app_bool("chat_mention_overlay_enabled")

    @Property(bool, notify=changed)
    def chatMentionSoundEnabled(self) -> bool:
        return self._app_bool("chat_mention_sound_enabled")

    @Property(bool, notify=changed)
    def squadlockOverlayEnabled(self) -> bool:
        return bool(self._notification_settings().get("squadlock_overlay_enabled", True))

    @Slot(str, str, result="QVariant")
    def value(self, section: str, key: str) -> Any:
        return self.settings.get(section, {}).get(key)

    @Slot(str, str, "QVariant")
    def setValue(self, section: str, key: str, value: Any) -> None:
        target = self.settings.setdefault(section, {})
        target[key] = value
        self._save()

    @Slot()
    def notifyExternalChange(self) -> None:
        self._revision += 1
        self.changed.emit()

    @Slot(str)
    def setCloseAction(self, action: str) -> None:
        action = str(action)
        if action not in VALID_CLOSE_ACTIONS:
            action = "ask"
        if self.closeAction == action:
            return
        self._app_settings()["close_action"] = action
        self._save()

    @Slot(bool)
    def setStartWithWindows(self, enabled: bool) -> None:
        enabled = bool(enabled)
        app_settings = self._app_settings()
        try:
            set_start_with_windows(enabled, self.settings)
        except Exception as exc:
            if enabled:
                app_settings["start_with_windows"] = False
            self._status = str(exc)
            self._save()
            return

        app_settings["start_with_windows"] = enabled
        app_settings["startup_prompted"] = True
        self._status = ""
        self._save()

    @Slot(str, bool)
    def setNotificationEnabled(self, key: str, enabled: bool) -> None:
        enabled = bool(enabled)
        if key == "squadlock_overlay_enabled":
            self._notification_settings()[key] = enabled
        elif key in {
            "stockpile_sound_enabled",
            "squadlock_sound_enabled",
            "chat_mention_overlay_enabled",
            "chat_mention_sound_enabled",
        }:
            self._app_settings()[key] = enabled
        else:
            return
        self._save()

    @Slot(result=str)
    def settingsPath(self) -> str:
        return str(settings_path())

    @Slot(result=str)
    def settingsJson(self) -> str:
        return json.dumps(self.settings, indent=2, ensure_ascii=False)


class TrayController(QObject):
    restoreRequested = Signal()
    quitRequested = Signal()

    def __init__(self, app: QApplication, i18n: I18nController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.app = app
        self.i18n = i18n
        self.icon = QSystemTrayIcon(self)
        icon_path = BASE_DIR / "img" / "app_icon.ico"
        if icon_path.exists():
            self.icon.setIcon(QIcon(str(icon_path)))
        self.icon.setToolTip(APP_TITLE)
        self.menu = QMenu()
        self.open_action = self.menu.addAction("")
        self.open_action.triggered.connect(self.restoreRequested.emit)
        self.exit_action = self.menu.addAction("")
        self.exit_action.triggered.connect(self.quitRequested.emit)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._activated)
        self.i18n.changed.connect(self._refresh_text)
        self._refresh_text()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.icon.show()

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.restoreRequested.emit()

    @Slot()
    def _refresh_text(self) -> None:
        self.open_action.setText(self.i18n.t("tray.open"))
        self.exit_action.setText(self.i18n.t("tray.exit"))

    @Slot(str, str)
    def showMessage(self, title: str, message: str) -> None:
        if self.icon.isVisible():
            self.icon.showMessage(title, message, QSystemTrayIcon.Information, 3500)


class AutoClickerController(QObject):
    changed = Signal()
    statusFromWorker = Signal(str)
    menuRequested = Signal()
    orderRequested = Signal(str)

    def __init__(self, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._status = "Auto Clicker initializing..."
        self._available = True
        self.slots = DictListModel(["slotNumber", "slotX", "slotY"], self)
        self.orders = DictListModel(["name"], self)
        self.statusFromWorker.connect(self._set_status)
        self.menuRequested.connect(self._start_default_order)
        try:
            self.clicker = AutoClicker(lambda text: self.statusFromWorker.emit(str(text)))
            self.clicker.set_menu_callback(lambda: self.menuRequested.emit())
            self._apply_settings()
        except Exception as exc:
            self.clicker = None
            self._available = False
            self._status = f"Auto Clicker unavailable: {exc}"
        self._refresh_models()
        self.changed.emit()

    def _clicker_settings(self) -> dict[str, Any]:
        return self.settings.setdefault("auto_clicker", {})

    def _orders_from_settings(self) -> list[str]:
        orders = [str(item).strip() for item in self._clicker_settings().get("f5_orders", []) if str(item).strip()]
        return orders or ["Diesel", "Cmats", "Bmats", "Emats"]

    def _refresh_models(self) -> None:
        data = self._clicker_settings()
        self.slots.set_items(
            [
                {
                    "slotNumber": slot,
                    "slotX": int(data.get(f"slot_{slot}_x", 0) or 0),
                    "slotY": int(data.get(f"slot_{slot}_y", 0) or 0),
                }
                for slot in (1, 2, 3, 4)
            ]
        )
        self.orders.set_items([{"name": name} for name in self._orders_from_settings()])

    def _apply_settings(self) -> None:
        if not self.clicker:
            return
        data = self._clicker_settings()
        self.clicker.configure(
            str(data.get("hotkey", "F3")),
            str(data.get("mouse_button", "Esquerdo")),
            0.3,
        )
        self.clicker.configure_action_hotkeys(
            str(data.get("move_hotkey", "F2")),
            str(data.get("fixed_hotkey", "F6")),
            str(data.get("pilot_hotkey", "F4")),
            str(data.get("artillery_hotkey", "F7")),
        )
        self.clicker.set_slot_positions(
            {
                slot: (
                    int(data.get(f"slot_{slot}_x", 0)),
                    int(data.get(f"slot_{slot}_y", 0)),
                )
                for slot in (1, 2, 3, 4)
            }
        )
        self._status = self.clicker.status_text()

    @Slot(str)
    def _set_status(self, text: str) -> None:
        self._status = text
        self.changed.emit()

    @Property(bool, notify=changed)
    def available(self) -> bool:
        return self._available


    @Property("QVariantMap", notify=changed)
    def userProfile(self) -> dict:
        return getattr(self, "_profile", {})

    @Slot()
    def logout(self) -> None:
        self._token = ""
        self._discord_user_settings.clear()
        save_settings(self.settings)
        self._ws.close()
        self._discord_login_required = True
        self._current_user_id = ""
        self._profile = {}
        self._status = "Disconnected"
        self.changed.emit()



    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=changed)
    def running(self) -> bool:
        return bool(self.clicker and self.clicker.enabled)

    @Property(bool, notify=changed)
    def active(self) -> bool:
        return bool(
            self.clicker
            and (
                self.clicker.enabled
                or self.clicker.fixed_click_enabled
                or self.clicker.move_click_enabled
                or time.monotonic() < self.clicker.last_pilot_until
            )
        )

    @Property(bool, notify=changed)
    def fixedRunning(self) -> bool:
        return bool(self.clicker and self.clicker.fixed_click_enabled)

    @Property(bool, notify=changed)
    def moveRunning(self) -> bool:
        return bool(self.clicker and self.clicker.move_click_enabled)

    @Property(bool, notify=changed)
    def pilotRunning(self) -> bool:
        return bool(self.clicker and time.monotonic() < self.clicker.last_pilot_until)

    @Property(str, notify=changed)
    def hotkey(self) -> str:
        return str(self._clicker_settings().get("hotkey", "F3"))

    @Property(str, notify=changed)
    def moveHotkey(self) -> str:
        return str(self._clicker_settings().get("move_hotkey", "F2"))

    @Property(str, notify=changed)
    def fixedHotkey(self) -> str:
        return str(self._clicker_settings().get("fixed_hotkey", "F6"))

    @Property(str, notify=changed)
    def pilotHotkey(self) -> str:
        return str(self._clicker_settings().get("pilot_hotkey", "F4"))

    @Property(str, notify=changed)
    def artilleryHotkey(self) -> str:
        return str(self._clicker_settings().get("artillery_hotkey", "F7"))

    @Property(str, notify=changed)
    def mouseButton(self) -> str:
        return str(self._clicker_settings().get("mouse_button", "Esquerdo"))

    @Property(float, notify=changed)
    def interval(self) -> float:
        return 0.3

    @Property(str, notify=changed)
    def targetTitle(self) -> str:
        return str(self.clicker.target_title if self.clicker and self.clicker.target_title else "Foxhole")

    @Property(int, notify=changed)
    def clickCount(self) -> int:
        return int(self.clicker.click_count if self.clicker else 0)

    @Property(str, notify=changed)
    def modeSummary(self) -> str:
        if not self.clicker:
            return "-"
        items: list[str] = []
        if self.clicker.enabled:
            items.append(f"AUTO {self.hotkey} ({self.interval:.2f}s)")
        if self.clicker.move_click_enabled:
            items.append(f"MOVE {self.moveHotkey}")
        if self.clicker.fixed_click_enabled:
            items.append(f"FIXED {self.fixedHotkey}")
            items.append("SLOTS 1-4")
        if time.monotonic() < self.clicker.last_pilot_until:
            items.append(f"PILOT {self.pilotHotkey}")
        return " | ".join(items) if items else "-"

    @Property(QObject, constant=True)
    def slotModel(self) -> QObject:
        return self.slots

    @Property(QObject, constant=True)
    def orderModel(self) -> QObject:
        return self.orders

    @Property("QStringList", constant=True)
    def hotkeys(self) -> list[str]:
        return list(ACTION_KEYS.keys())

    @Property("QStringList", constant=True)
    def mouseButtons(self) -> list[str]:
        return list(MOUSE_BUTTONS.keys())

    @Slot(str, result=str)
    def mouseButtonLabel(self, value: str) -> str:
        return {
            "Esquerdo": "clicker.mouse_left",
            "Direito": "clicker.mouse_right",
            "Meio": "clicker.mouse_middle",
        }.get(value, "clicker.mouse_left")

    @Slot(result=str)
    def shortcutsText(self) -> str:
        return "\n".join(
            [
                f"{self.hotkey}: default Auto Clicker toggle",
                f"{self.moveHotkey}: Move-Click hold",
                f"{self.fixedHotkey}: fixed double-click and slots 1-4",
                f"{self.pilotHotkey}: pilot sequence",
                f"{self.artilleryHotkey}: artillery sequence",
                "F5: orders and stock menu",
            ]
        )

    @Slot()
    def toggle(self) -> None:
        if self.clicker:
            self.clicker.toggle()
            self._status = self.clicker.status_text()
            self.changed.emit()

    @Slot()
    def captureFoxhole(self) -> None:
        if self.clicker:
            self._status = self.clicker.use_foxhole_window()
            self.changed.emit()

    @Slot(str)
    def setHotkey(self, value: str) -> None:
        if value in ACTION_KEYS:
            self._clicker_settings()["hotkey"] = value
            self._save_and_apply()

    @Slot(str)
    def setMoveHotkey(self, value: str) -> None:
        if value in ACTION_KEYS:
            self._clicker_settings()["move_hotkey"] = value
            self._save_and_apply()

    @Slot(str)
    def setFixedHotkey(self, value: str) -> None:
        if value in ACTION_KEYS:
            self._clicker_settings()["fixed_hotkey"] = value
            self._save_and_apply()

    @Slot(str)
    def setPilotHotkey(self, value: str) -> None:
        if value in ACTION_KEYS:
            self._clicker_settings()["pilot_hotkey"] = value
            self._save_and_apply()

    @Slot(str)
    def setArtilleryHotkey(self, value: str) -> None:
        if value in ACTION_KEYS:
            self._clicker_settings()["artillery_hotkey"] = value
            self._save_and_apply()

    @Slot(str)
    def setMouseButton(self, value: str) -> None:
        if value in MOUSE_BUTTONS:
            self._clicker_settings()["mouse_button"] = value
            self._save_and_apply()

    @Property(bool, notify=changed)
    def shiftEnabled(self) -> bool:
        return bool(self._clicker_settings().get("shift_enabled", False))

    @Slot(bool)
    def setShiftEnabled(self, value: bool) -> None:
        self._clicker_settings()["shift_enabled"] = bool(value)
        save_settings(self.settings)
        if self.clicker:
            self.clicker.shift_enabled = bool(value)
        self.changed.emit()

    @Property(bool, notify=changed)
    def wDoubleTapEnabled(self) -> bool:
        return bool(self._clicker_settings().get("w_doubletap_enabled", True))

    @Slot(bool)
    def setWDoubleTapEnabled(self, value: bool) -> None:
        self._clicker_settings()["w_doubletap_enabled"] = bool(value)
        save_settings(self.settings)
        if self.clicker:
            self.clicker.w_doubletap_enabled = bool(value)
        self.changed.emit()

    @Slot(float)
    def setInterval(self, value: float) -> None:
        pass
        self._save_and_apply()

    @Slot(int, int, int)
    def setSlotPosition(self, slot: int, x: int, y: int) -> None:
        if slot not in (1, 2, 3, 4):
            return
        data = self._clicker_settings()
        data[f"slot_{slot}_x"] = max(0, int(x))
        data[f"slot_{slot}_y"] = max(0, int(y))
        self._save_and_apply()

    @Slot(int, str)
    def setOrderName(self, index: int, name: str) -> None:
        orders = self._orders_from_settings()
        if index < 0 or index >= len(orders):
            return
        clean = str(name).strip()
        if not clean:
            return
        orders[index] = clean
        self._clicker_settings()["f5_orders"] = orders
        self._save_and_apply()

    @Slot()
    def addOrder(self) -> None:
        orders = self._orders_from_settings()
        orders.append(f"Order {len(orders) + 1}")
        self._clicker_settings()["f5_orders"] = orders
        self._save_and_apply()

    @Slot(int)
    def removeOrder(self, index: int) -> None:
        orders = self._orders_from_settings()
        if index < 0 or index >= len(orders):
            return
        del orders[index]
        self._clicker_settings()["f5_orders"] = orders or ["Diesel"]
        self._save_and_apply()

    @Slot(int)
    def startOrder(self, index: int) -> None:
        orders = self._orders_from_settings()
        if not orders:
            return
        order_name = orders[index] if 0 <= index < len(orders) else orders[0]
        self._status = f"Order started: {order_name}"
        self.orderRequested.emit(order_name)
        self.changed.emit()

    @Slot()
    def _start_default_order(self) -> None:
        self.startOrder(0)

    def _save_and_apply(self) -> None:
        save_settings(self.settings)
        self._apply_settings()
        self._refresh_models()
        self.changed.emit()

    @Slot()
    def shutdown(self) -> None:
        if self.clicker:
            self.clicker.stop()


class StockpileController(QObject):
    changed = Signal()
    statusFromWorker = Signal(object)

    def __init__(self, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._running = False
        self._status = "Idle"
        self._last_response = "-"
        self._last_update = "-"
        self._sent_count = 0
        self._report_count = 0
        self._item_count = 0
        self._last_stockpile = "-"
        self._stockpile_list = "-"
        self._debug_visible = False
        self._debug_text = ""
        self._upload_overlay_visible = False
        self._upload_overlay_body = ""
        self._visual_items: list[dict[str, Any]] = []
        self._visual_warehouses: list[dict[str, Any]] = []
        self._visual_warehouse = ""
        self._watcher: StockpileWatcher | None = None
        self._api_loading = False
        self._upload_overlay_timer = QTimer(self)
        self._upload_overlay_timer.setSingleShot(True)
        self._upload_overlay_timer.timeout.connect(self.dismissUploadOverlay)
        self._api_refresh_timer = QTimer(self)
        self._api_refresh_timer.setInterval(30_000)
        self._api_refresh_timer.timeout.connect(self.refreshApiSnapshot)
        self.logs = DictListModel(["time", "message"], self)
        self.items = DictListModel(["name", "quantity", "category", "icon"], self)
        self.warehouses = DictListModel(["name", "region", "count", "updatedAt"], self)
        self.statusFromWorker.connect(self._handle_status)
        self.refreshDebugSnapshot()
        self._api_refresh_timer.start()
        QTimer.singleShot(0, self.refreshApiSnapshot)

    @Property(bool, notify=changed)
    def running(self) -> bool:
        return self._running


    @Property("QVariantMap", notify=changed)
    def userProfile(self) -> dict:
        return getattr(self, "_profile", {})

    @Slot()
    def logout(self) -> None:
        self._token = ""
        self._discord_user_settings.clear()
        save_settings(self.settings)
        self._ws.close()
        self._discord_login_required = True
        self._current_user_id = ""
        self._profile = {}
        self._status = "Disconnected"
        self.changed.emit()



    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def lastResponse(self) -> str:
        return self._last_response

    @Property(str, notify=changed)
    def lastUpdate(self) -> str:
        return self._last_update

    @Property(str, notify=changed)
    def watchFile(self) -> str:
        return str(self.settings.get("stockpile", {}).get("watch_file", ""))

    @Property(str, notify=changed)
    def apiUrl(self) -> str:
        return str(self.settings.get("stockpile", {}).get("api_url", DEFAULT_API_URL))

    @Property(str, notify=changed)
    def outDir(self) -> str:
        return str(self.settings.get("stockpile", {}).get("out_dir", str(extracted_dir())))

    @Property(int, notify=changed)
    def sentCount(self) -> int:
        return self._sent_count

    @Property(int, notify=changed)
    def reportCount(self) -> int:
        return self._report_count

    @Property(int, notify=changed)
    def itemCount(self) -> int:
        return self._item_count

    @Property(str, notify=changed)
    def lastStockpile(self) -> str:
        return self._last_stockpile

    @Property(str, notify=changed)
    def stockpileList(self) -> str:
        return self._stockpile_list

    @Property(bool, notify=changed)
    def debugVisible(self) -> bool:
        return self._debug_visible

    @Property(str, notify=changed)
    def debugText(self) -> str:
        return self._debug_text

    @Property(bool, notify=changed)
    def uploadOverlayVisible(self) -> bool:
        return self._upload_overlay_visible

    @Property(str, notify=changed)
    def uploadOverlayBody(self) -> str:
        return self._upload_overlay_body

    @Property("QVariantList", notify=changed)
    def warehouseRows(self) -> list[dict[str, Any]]:
        return self.warehouses.items()

    @Property("QVariantList", notify=changed)
    def itemRows(self) -> list[dict[str, Any]]:
        return self.items.items()

    @Property("QVariantList", notify=changed)
    def logRows(self) -> list[dict[str, Any]]:
        return self.logs.items()

    @Property("QStringList", notify=changed)
    def visualWarehouseOptions(self) -> list[str]:
        return [str(item.get("name") or "-") for item in self._visual_warehouses if item.get("name")]

    @Property(str, notify=changed)
    def visualWarehouse(self) -> str:
        return self._visual_warehouse

    @Property(str, notify=changed)
    def visualWarehouseUpdatedAt(self) -> str:
        for item in self._visual_warehouses:
            if str(item.get("name") or "") == self._visual_warehouse:
                return format_to_local_pc_time(str(item.get("last_update") or item.get("updatedAt") or "-"))
        return "-"

    @Property("QVariantList", notify=changed)
    def visualGroupRows(self) -> list[dict[str, Any]]:
        return self._visual_groups()

    @Slot(str)
    def setVisualWarehouse(self, value: str) -> None:
        value = str(value or "")
        if value == self._visual_warehouse:
            return
        self._visual_warehouse = value
        self.changed.emit()

    @Slot(str)
    def setWatchFile(self, value: str) -> None:
        self.settings.setdefault("stockpile", {})["watch_file"] = value
        save_settings(self.settings)
        self.refreshDebugSnapshot()
        self.changed.emit()

    @Slot(str)
    def setApiUrl(self, value: str) -> None:
        self.settings.setdefault("stockpile", {})["api_url"] = value
        save_settings(self.settings)
        self.changed.emit()

    @Slot(str)
    def setOutDir(self, value: str) -> None:
        self.settings.setdefault("stockpile", {})["out_dir"] = value
        save_settings(self.settings)
        self.refreshDebugSnapshot()
        self.changed.emit()

    @Slot()
    def chooseWatchFile(self) -> None:
        current = Path(self.watchFile)
        start_dir = current.parent if current.parent.exists() else foxhole_savegames_dir()
        path, _selected_filter = QFileDialog.getOpenFileName(
            None,
            APP_TITLE,
            str(start_dir),
            "Foxhole map data (*.sav);;All files (*)",
        )
        if path:
            self.setWatchFile(path)

    @Slot()
    def chooseOutDir(self) -> None:
        current = Path(self.outDir)
        start_dir = current if current.exists() else extracted_dir()
        path = QFileDialog.getExistingDirectory(None, APP_TITLE, str(start_dir))
        if path:
            self.setOutDir(path)

    @Slot()
    def discoverWatchFile(self) -> None:
        discovered = discover_map_data_file()
        if discovered:
            self.setWatchFile(str(discovered))
            self._append_log(f"Discovered save file: {discovered}")
        else:
            self._append_log("No Foxhole map save file found yet.")

    @Slot()
    def start(self) -> None:
        if self._running:
            return
        self._ensure_latest_watch_file()
        self._watcher = StockpileWatcher(
            Path(self.watchFile),
            Path(self.outDir),
            self.apiUrl,
            extract_initial=True,
            status_callback=lambda message: self.statusFromWorker.emit(message),
        )
        self._watcher.start()
        self._running = True
        self.settings.setdefault("stockpile", {})["enabled"] = True
        save_settings(self.settings)
        self._status = "Watcher running"
        self._append_log("Watcher started")
        self.refreshDebugSnapshot(emit_changed=False)
        self.changed.emit()

    @Slot()
    def stop(self) -> None:
        self._stop(persist_enabled=True)

    def _stop(self, persist_enabled: bool) -> None:
        if self._watcher:
            self._watcher.stop()
        self._watcher = None
        self._running = False
        if persist_enabled:
            self.settings.setdefault("stockpile", {})["enabled"] = False
            save_settings(self.settings)
        self._status = "Stopped"
        self._append_log("Watcher stopped")
        self.refreshDebugSnapshot(emit_changed=False)
        self.changed.emit()

    @Slot()
    def refreshApiDebug(self) -> None:
        self.refreshApiSnapshot()

    @Slot()
    def refreshApiSnapshot(self) -> None:
        if self._api_loading:
            return
        self._api_loading = True
        self._status = "Fetching stockpiles from API..."
        self._append_log(self._status)
        self.changed.emit()

        def worker() -> None:
            try:
                api_response = request_stockpile_debug(self.apiUrl)
                summaries = warehouse_summaries(api_response)
                result = {
                    "kind": "api_snapshot",
                    "api_response": api_response.get("status_text", "-"),
                    "api_last_update": format_to_local_pc_time(api_last_update(api_response)),
                    "warehouse_summaries": summaries,
                    "items": api_item_rows(api_response),
                    "report_count": len(summaries),
                    "stockpiles": [str(item.get("name", "-")) for item in summaries],
                    "send_count": self._sent_count,
                }
                self.statusFromWorker.emit(result)
            except Exception as exc:
                self.statusFromWorker.emit({"kind": "ui_error", "text": f"Stockpile API error: {exc}"})
            finally:
                self._api_loading = False

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def extractOnce(self) -> None:
        self._ensure_latest_watch_file()
        watch_file = Path(self.watchFile)
        out_dir = Path(self.outDir)
        api_url = self.apiUrl
        if not watch_file.exists():
            self.statusFromWorker.emit("manual extract error: no *_MapData.sav file found")
            return

        def worker() -> None:
            try:
                result = extract_and_post(
                    watch_file,
                    out_dir,
                    api_url,
                    force_api_refresh=True,
                    upload_reason="manual",
                )
                if result is None:
                    self.statusFromWorker.emit(f"stockpile unchanged: {watch_file.name}")
                else:
                    self.statusFromWorker.emit(result)
            except Exception as exc:
                self.statusFromWorker.emit(f"manual extract error for {watch_file.name}: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object)
    def _handle_status(self, message: object) -> None:
        if isinstance(message, dict):
            if message.get("kind") == "ui_error":
                self._status = str(message.get("text") or "-")
                self._append_log(self._status)
                self.refreshDebugSnapshot(emit_changed=False)
                self.changed.emit()
                return
            self._sent_count = int(message.get("send_count", self._sent_count) or self._sent_count)
            rows = list(message.get("items") or []) if "items" in message else api_item_rows(message)
            warehouses = (
                list(message.get("warehouse_summaries") or [])
                if "warehouse_summaries" in message
                else warehouse_summaries(message)
            )
            if message.get("kind") == "api_snapshot" and not rows and self._visual_items:
                self._status = "Fetching stockpiles from API..."
                self.refreshDebugSnapshot(emit_changed=False)
                self.changed.emit()
                return
            stockpiles = [str(item.get("name", "-")) for item in warehouses if item.get("name")]
            self._report_count = int(message.get("report_count", len(warehouses)) or len(warehouses))
            self._item_count = len(rows)
            self._last_stockpile = stockpiles[-1] if stockpiles else "-"
            self._stockpile_list = ", ".join(stockpiles[:6]) if stockpiles else "-"
            if len(stockpiles) > 6:
                self._stockpile_list = f"{self._stockpile_list} +{len(stockpiles) - 6}"
            self._visual_items = rows
            self._visual_warehouses = warehouses
            if stockpiles and self._visual_warehouse not in stockpiles:
                self._visual_warehouse = stockpiles[0]
            elif not stockpiles:
                self._visual_warehouse = ""
            self._last_response = str(message.get("api_response") or message.get("message") or "OK")
            self._last_update = str(message.get("api_last_update") or api_last_update(message) or now_label())
            if message.get("kind") == "api_snapshot":
                self._status = "API data loaded."
            else:
                self._status = f"{self._report_count} reports, {self._item_count} items"
                if message.get("payload_changed") and self.parent():
                    # Attempt to invoke postStockpileHelp on the chat controller
                    try:
                        app = QApplication.instance()
                        for obj in app.children():
                            if type(obj).__name__ == "ControllerRegistry":
                                obj.chatController.postStockpileHelp("Estoque atualizado")
                                break
                    except Exception:
                        pass
            self._append_log(self._last_response)
            try:
                self.items.set_items(normalize_item_rows(rows))
                self.warehouses.set_items(normalize_warehouses(warehouses))
            except Exception:
                pass
            if "upload_reason" in message:
                self._show_upload_notification(message)
        else:
            text = str(message)
            self._maybe_update_watch_file_from_status(text)
            self._status = text
            self._append_log(text)
        self.refreshDebugSnapshot(emit_changed=False)
        self.changed.emit()

    def _append_log(self, message: str) -> None:
        self.logs.append({"time": now_label(), "message": message})

    @Slot()
    def dismissUploadOverlay(self) -> None:
        if not self._upload_overlay_visible:
            return
        self._upload_overlay_timer.stop()
        self._upload_overlay_visible = False
        self.changed.emit()

    def _show_upload_notification(self, message: dict[str, Any]) -> None:
        app_settings = self.settings.get("app", {})
        clicker_settings = self.settings.get("auto_clicker", {})
        if bool(app_settings.get("stockpile_sound_enabled", True)):
            play_sound("estoque")
        if not bool(clicker_settings.get("overlay_notification_enabled", True)):
            return
        response = str(message.get("api_response") or message.get("message") or "OK")
        names = self._stockpile_list if self._stockpile_list and self._stockpile_list != "-" else self._last_stockpile
        if names and names != "-":
            self._upload_overlay_body = f"{names} | {response}"
        else:
            self._upload_overlay_body = response
        self._upload_overlay_visible = True
        self._upload_overlay_timer.start(4500)

    def _ensure_latest_watch_file(self) -> bool:
        latest = self._newer_discovered_watch_file()
        if latest is None:
            return False
        self.settings.setdefault("stockpile", {})["watch_file"] = str(latest)
        save_settings(self.settings)
        self._append_log(f"Using latest Foxhole save file: {latest}")
        self.refreshDebugSnapshot(emit_changed=False)
        self.changed.emit()
        return True

    def _newer_discovered_watch_file(self) -> Path | None:
        discovered = discover_map_data_file()
        if not discovered:
            return None
        current = Path(self.watchFile)
        try:
            if current.exists() and current.resolve() == discovered.resolve():
                return None
        except OSError:
            return discovered
        return discovered

    def _maybe_update_watch_file_from_status(self, message: str) -> None:
        prefixes = ("found newer Foxhole save file: ", "found Foxhole save file: ")
        for prefix in prefixes:
            if not message.startswith(prefix):
                continue
            path = Path(message.removeprefix(prefix).strip())
            if not path.exists():
                return
            self.settings.setdefault("stockpile", {})["watch_file"] = str(path)
            save_settings(self.settings)
            return

    @staticmethod
    def _clean_visual_item_name(item: dict[str, Any]) -> str:
        display_name = str(item.get("display_name") or item.get("asset_name") or item.get("name") or "-").strip()
        suffix = " Crated"
        if display_name.endswith(suffix):
            display_name = display_name[: -len(suffix)].strip()
        return display_name or "-"

    @staticmethod
    def _visual_group_key(item: dict[str, Any]) -> str:
        asset = str(item.get("asset_name") or "").lower()
        display = str(item.get("display_name") or item.get("name") or "").lower()
        icon_name = str(item.get("icon_name") or "").lower()
        category = str(item.get("category") or "").lower()
        icon_source = str(item.get("icon_source") or "").lower()
        priority = str(item.get("priority") or "").lower()
        is_crated = "crated" in display or icon_name.endswith("-crated")
        is_shippable = category in {"shippables", "shippable", "structures"} or icon_source == "structures_shippables"

        if priority and priority not in {"-", "medium", "normal"}:
            return "priority"
        if asset in {"basicmaterials", "bmat", "bmats"} or "basic materials" in display or display in {"bmat", "bmats"}:
            return "starter"
        if asset in {"cloth", "soldiersupplies", "shirts"} or "soldier supplies" in display or "shirts" in display:
            return "starter"
        if asset in {"maintenancesupplies", "msup", "msups"} or "maintenance supplies" in display or "msup" in display:
            return "starter"
        if (
            asset in {"cloth", "soldiersupplies", "maintenancesupplies"}
            or "basic materials" in display
            or "soldier supplies" in display
            or "maintenance supplies" in display
        ):
            return "supplies"
        if category == "vehicle":
            return "vehicle_crates" if is_crated else "vehicles"
        if is_shippable:
            return "shippable_crates" if is_crated else "shippables"
        if category == "utility":
            return "common_logi"
        return "supplies"

    @staticmethod
    def _visual_sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
        display = str(item.get("display_name") or item.get("name") or "").lower()
        asset = str(item.get("asset_name") or "").lower()
        starter_order = 99
        if asset in {"basicmaterials", "bmat", "bmats"} or "basic materials" in display:
            starter_order = 0
        elif asset in {"cloth", "soldiersupplies", "shirts"} or "soldier supplies" in display or "shirts" in display:
            starter_order = 1
        elif asset in {"maintenancesupplies", "msup", "msups"} or "maintenance supplies" in display or "msup" in display:
            starter_order = 2
        return (
            starter_order,
            -int(item.get("quantity", 0) or 0),
            str(item.get("display_name") or item.get("name") or ""),
        )

    def _visual_groups(self) -> list[dict[str, Any]]:
        warehouse = self._visual_warehouse
        rows = [item for item in self._visual_items if str(item.get("warehouse") or "") == warehouse]
        positive_rows = [item for item in rows if int(item.get("quantity", 0) or 0) > 0]
        rows = positive_rows or rows
        ordered_keys = [
            "starter",
            "priority",
            "supplies",
            "common_logi",
            "vehicles",
            "vehicle_crates",
            "shippables",
            "shippable_crates",
        ]
        groups: dict[str, list[dict[str, Any]]] = {key: [] for key in ordered_keys}
        for item in rows:
            groups.setdefault(self._visual_group_key(item), []).append(item)

        result: list[dict[str, Any]] = []
        for key in ordered_keys:
            items = sorted(groups.get(key) or [], key=self._visual_sort_key)
            if not items:
                continue
            result.append(
                {
                    "key": key,
                    "titleKey": f"stockpile.group_{key}",
                    "accent": "#8ab4ff" if key in {"starter", "common_logi"} else "#aeb7c2",
                    "items": [self._visual_item_row(item) for item in items],
                }
            )
        return result

    def _visual_item_row(self, item: dict[str, Any]) -> dict[str, Any]:
        icon_path = str(item.get("icon_path") or item.get("icon") or "")
        return {
            "name": self._clean_visual_item_name(item),
            "quantity": int(item.get("quantity", 0) or 0),
            "category": str(item.get("category") or "-"),
            "priority": str(item.get("priority") or "-"),
            "icon": file_url(icon_path) if icon_path and Path(icon_path).exists() else "",
        }

    @Slot()
    def toggleDebug(self) -> None:
        self._debug_visible = not self._debug_visible
        if self._debug_visible:
            self.refreshDebugSnapshot(emit_changed=False)
        self.changed.emit()

    @Slot()
    def refreshDebugSnapshot(self, emit_changed: bool = True) -> None:
        self._debug_text = self._build_debug_snapshot()
        if emit_changed:
            self.changed.emit()

    def _build_debug_snapshot(self) -> str:
        lines = ["[Stockpile diagnostics]"]
        lines.append(f"watcher_alive={self._watcher_alive()} running={self._running}")
        lines.append(f"status={self._status}")
        watch_path = Path(self.watchFile)
        out_dir = resolve_writable_path(self.outDir)
        lines.append(self._file_stat_line("watch_file", watch_path))
        lines.append(f"out_dir={out_dir}")
        lines.append(self._file_stat_line("captured_json", default_output_path(watch_path, out_dir)))
        lines.append(self._file_stat_line("last_sent_json", last_sent_output_path(watch_path, out_dir)))
        discovered = discover_map_data_file()
        lines.append(f"discover_map_data_file={discovered or '-'}")
        save_dir = foxhole_savegames_dir()
        lines.append(f"savegames_dir={save_dir}")
        try:
            candidates = sorted(
                [path for path in save_dir.glob("*_MapData.sav") if path.is_file()],
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
        except OSError as exc:
            lines.append(f"candidates_error={exc}")
            candidates = []
        if not candidates:
            lines.append("candidates=none")
        for index, candidate in enumerate(candidates[:5], 1):
            try:
                marker = " <= watched" if candidate.resolve() == watch_path.resolve() else ""
            except OSError:
                marker = ""
            lines.append(self._file_stat_line(f"candidate_{index}{marker}", candidate))
        lines.append("")
        lines.append("[Recent app log]")
        for row in self.logs._items[-8:]:
            lines.append(f"{row.get('time')} {row.get('message')}")
        lines.append("")
        lines.append("[stockpile_debug.log tail]")
        lines.extend(self._debug_log_tail())
        return "\n".join(lines)

    def _watcher_alive(self) -> bool:
        thread = getattr(self._watcher, "thread", None)
        return bool(self._watcher and thread and thread.is_alive())

    @staticmethod
    def _file_stat_line(label: str, path: Path) -> str:
        try:
            stat = path.stat()
        except OSError as exc:
            return f"{label}: {path} | missing/unreadable ({exc})"
        changed = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return f"{label}: {path} | size={stat.st_size} mtime={changed} mtime_ns={stat.st_mtime_ns}"

    @staticmethod
    def _debug_log_tail(max_lines: int = 24) -> list[str]:
        try:
            lines = STOCKPILE_DEBUG_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return [f"{STOCKPILE_DEBUG_LOG}: missing"]
        return lines[-max_lines:] or ["empty"]

    @Slot()
    def shutdown(self) -> None:
        self._api_refresh_timer.stop()
        self._stop(persist_enabled=False)


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
        self._discord_configuration_checked = False
        self._discord_login_required = False
        self._mention_overlay_visible = False
        self._mention_overlay_title = ""
        self._mention_overlay_body = ""
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
            ["id", "author", "body", "meta", "rawTime", "sortKey", "mine", "avatar", "mediaUrl", "isGif", "mentioned", "reactions", "replyToMessageId", "replyToAuthor", "replyToBody"],
            self,
        )
        self.onlineUsers = DictListModel(["name", "detail", "avatar", "mention", "discordId"], self)
        self.mentionSuggestions = DictListModel(["name", "detail", "avatar", "mention", "discordId"], self)
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
        self._auto_connect_timer.setInterval(2500)
        self._auto_connect_timer.timeout.connect(self._maybe_auto_connect)
        self.steam.changed.connect(self._maybe_auto_connect)
        self._auto_connect_timer.start()
        QTimer.singleShot(0, self._maybe_auto_connect)
        self._ws = QWebSocket()
        self._ws.connected.connect(self._on_ws_connected)
        self._ws.disconnected.connect(self._on_ws_disconnected)
        self._ws.textMessageReceived.connect(self._on_ws_text_received)



    @Property("QVariantMap", notify=changed)
    def userProfile(self) -> dict:
        return getattr(self, "_profile", {})




    @Slot(str)
    def fetchProfile(self, user_id: str = "") -> None:
        if not self._token:
            return
        def run():
            try:
                if user_id:
                    res = http_json("GET", f"/chat/users/{user_id}/profile", token=self._token)
                else:
                    res = http_json("GET", "/chat/profile", token=self._token)
                self.resultFromWorker.emit("profile-fetched", res.get("profile", {}))
            except Exception as e:
                self.resultFromWorker.emit("profile-error", str(e))
        threading.Thread(target=run, daemon=True).start()

    @Slot(str)
    def updateRegiment(self, regiment: str) -> None:
        if not self._token:
            return
        def run():
            try:
                res = http_json("PATCH", "/chat/profile", token=self._token, payload={"regiment": regiment})
                self.resultFromWorker.emit("profile-updated", res.get("profile", {}))
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
        self._discord_user_settings.clear()
        save_settings(self.settings)
        self._ws.close()
        self._discord_login_required = True
        self._current_user_id = ""
        self._profile = {}
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
    def authInFlight(self) -> bool:
        return self._auth_in_flight

    @Property(bool, notify=changed)
    def mentionOverlayVisible(self) -> bool:
        return self._mention_overlay_visible

    @Property(str, notify=changed)
    def mentionOverlayTitle(self) -> str:
        return self._mention_overlay_title

    @Property(str, notify=changed)
    def mentionOverlayBody(self) -> str:
        return self._mention_overlay_body

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
        return str(os.environ.get("DISCORD_CLIENT_ID") or self._discord_settings.get("clientId") or "").strip()

    def _discord_client_secret(self) -> str:
        return str(os.environ.get("DISCORD_CLIENT_SECRET") or self._discord_settings.get("clientSecret") or "").strip()

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

    def _discord_oauth_profile(self) -> dict[str, Any]:
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
        form = {
            "client_id": client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        }
        client_secret = self._discord_client_secret()
        if client_secret:
            form["client_secret"] = client_secret
        token_result = http_json_url("POST", DISCORD_TOKEN_URL, form=form, timeout=20)
        access_token = str(token_result.get("access_token") or "")
        if not access_token:
            raise RuntimeError("Discord OAuth did not return an access token.")
        user = http_json_url("GET", DISCORD_USER_URL, token=access_token, timeout=20)
        if not user.get("id"):
            raise RuntimeError("Discord OAuth did not return a user profile.")
        avatar_url = discord_avatar_url(user)
        if avatar_url:
            user["avatarUrl"] = avatar_url
            user["avatarfull"] = avatar_url
            user["avatarmedium"] = avatar_url
        user["discordId"] = str(user.get("id") or "")
        user["displayName"] = str(user.get("global_name") or user.get("username") or "")
        user["globalName"] = str(user.get("global_name") or "")
        user["discriminator"] = str(user.get("discriminator") or "")
        user["discordAvatar"] = str(user.get("avatar") or "")
        return user

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

    def _auth_with_discord(self, payload: dict[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for path in CHAT_DISCORD_AUTH_PATHS:
            try:
                return http_json("POST", path, payload=payload, timeout=12)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(str(last_error) if last_error else "chat auth failed")

    def _auth_with_steam(self, payload: dict[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for path in CHAT_STEAM_AUTH_PATHS:
            try:
                return http_json("POST", path, payload=payload, timeout=12)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(str(last_error) if last_error else "chat auth failed")

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
        self._connect_with_discord(allow_oauth=True)

    @Slot()
    def autoConnectWithSavedDiscord(self) -> None:
        if self._saved_discord_id():
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
        if self._auth_in_flight:
            return
        if self._token:
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
        discord_id = self._saved_discord_id()
        if not discord_id:
            self._discord_configuration_checked = True
            self._discord_login_required = True
            if not allow_oauth:
                self._status = self._t("home.chat.no_discord")
                self.changed.emit()
                return
            if not self._discord_client_id():
                self._status = self._t("home.chat.discord_config_missing", uri=self.discordRedirectUri)
                self.changed.emit()
                return

        def worker() -> None:
            try:
                if discord_id:
                    result = self._auth_with_discord(self._discord_auth_payload(discord_id))
                else:
                    profile = self._discord_oauth_profile()
                    self._save_discord_profile(profile)
                    result = self._auth_with_discord(self._discord_auth_payload_from_profile(profile))
                self.resultFromWorker.emit("auth", result)
            except Exception as exc:
                message = str(exc)
                if "access_denied" in message or "oauth_cancelled" in message:
                    message = self._t("home.chat.discord_cancelled")
                self.resultFromWorker.emit("auth-error", self._t("home.chat.auth_error", message=message))

        self._auth_in_flight = True
        self._discord_login_required = False
        self._status = self._t("home.chat.authenticating_discord") if discord_id else self._t("home.chat.discord_opening")
        self.changed.emit()
        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def connectWithSteam(self) -> None:
        if self._auth_in_flight:
            return
        if self._token:
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
        profile_name = self.steam.personaName
        steam_id = self.steam.steamId
        if not steam_id:
            self._status = self._t("home.chat.no_steam")
            self.changed.emit()
            return

        def worker() -> None:
            try:
                payload = {"steamId": steam_id, "name": profile_name}
                result = self._auth_with_steam(payload)
                self.resultFromWorker.emit("auth", result)
            except Exception as exc:
                self.resultFromWorker.emit("auth-error", self._t("home.chat.auth_error", message=str(exc)))

        self._auth_in_flight = True
        self._status = self._t("home.chat.authenticating")
        self.changed.emit()
        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def _maybe_auto_connect(self) -> None:
        if self._token:
            if self._auto_connect_timer.isActive():
                self._auto_connect_timer.stop()
            return
        if self._auth_in_flight:
            return
        if self._saved_discord_id():
            self._connect_with_discord(allow_oauth=False)
            return
        self._discord_configuration_checked = True
        self._discord_login_required = True
        self._status = self._t("home.chat.no_discord")
        self.changed.emit()

    @Slot()
    def refreshRooms(self) -> None:
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
        self._ws.sendTextMessage(json.dumps({
            "type": "send_message",
            "chatSlug": self._selected_room,
            "content": body.strip()
        }))

    @Slot(str, str)
    def sendMessageReply(self, body: str, replyToMessageId: str) -> None:
        if not self._token or not self._selected_room or not body.strip():
            return
        self._ws.sendTextMessage(json.dumps({
            "type": "send_message",
            "chatSlug": self._selected_room,
            "content": body.strip(),
            "replyToMessageId": replyToMessageId
        }))

    @Slot(str, str)
    def reactMessage(self, messageId: str, emoji: str) -> None:
        if not self._token or not messageId or not emoji: return
        self._ws.sendTextMessage(json.dumps({
            "type": "react_message",
            "messageId": messageId,
            "emoji": emoji
        }))

    @Slot(str, str)
    def sendWhisperToUser(self, targetDiscordId: str, body: str) -> None:
        if not self._token or not targetDiscordId or not body.strip(): return
        self._ws.sendTextMessage(json.dumps({
            "type": "send_whisper",
            "targetDiscordId": targetDiscordId,
            "content": body.strip()
        }))
    @Slot(str)
    def sendGif(self, url: str) -> None:
        self.sendMessage(url)

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

    @Slot()
    def dismissMentionOverlay(self) -> None:
        self._mention_overlay_visible = False
        self.changed.emit()

    @Slot(str, object)
    def _apply_result(self, kind: str, payload: object) -> None:
        if kind == "auth" and isinstance(payload, dict):
            self._auth_in_flight = False
            self._auth_retry_after = 0.0
            self._discord_configuration_checked = True
            self._discord_login_required = False
            self._token = str(payload.get("token") or payload.get("accessToken") or "")
            user = payload.get("user") or payload.get("profile") or {}
            if isinstance(user, dict):
                self._current_user_id = str(user.get("id") or "")
                self._current_user_provider = str(user.get("provider") or ("discord" if user.get("discordId") else "steam"))
                self._current_user_discord_id = str(user.get("discordId") or self._saved_discord_id())
                self._current_user_steam_id = str(user.get("steamId") or self.steam.steamId)
                self._current_user_name = str(
                    user.get("displayName")
                    or user.get("globalName")
                    or user.get("name")
                    or user.get("personaName")
                    or user.get("personaname")
                    or user.get("nickname")
                    or user.get("username")
                    or self._saved_discord_name()
                    or self.steam.personaName
                )
                self._current_user_avatar = user_avatar_url(user)
                if self._current_user_discord_id:
                    self._save_discord_profile(user)
            else:
                self._current_user_id = ""
                self._current_user_provider = "discord" if self._saved_discord_id() else "steam"
                self._current_user_discord_id = self._saved_discord_id()
                self._current_user_name = self._saved_discord_name() or self.steam.personaName
                self._current_user_avatar = self._saved_discord_avatar() or self.steam.avatarUrl
                self._current_user_steam_id = self.steam.steamId
            self._status = self._t("home.chat.connected") if self._token else "Connected without token"
            if self._token:
                try:
                    profile_res = http_json("GET", "/chat/profile", token=self._token)
                    self._profile = profile_res.get("profile", {})
                    self.changed.emit()
                except Exception:
                    pass
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
            self._discord_configuration_checked = True
            self._discord_login_required = not bool(self._saved_discord_id())
            self._auth_retry_after = time.monotonic() + 30
            self._status = str(payload)
        elif kind == "rooms" and isinstance(payload, dict):
            rooms = payload.get("chats") or payload.get("rooms") or []
            self.rooms.set_items([self._room_to_row(room) for room in rooms])
            self._status = f"{len(rooms)} chat rooms loaded"
            if not self._selected_room and rooms:
                first = self._room_to_row(rooms[0])
                self.selectRoom(str(first["slug"]))
        elif kind == "rooms-finished":
            self._rooms_in_flight = False
        elif kind == "users" and isinstance(payload, dict):
            users = payload.get("users") or []
            rows = [self._user_to_row(user) for user in users]
            self._all_user_rows = rows
            self._online_rows = self._merge_user_rows(self._online_rows, rows)
        elif kind == "online" and isinstance(payload, dict):
            users = payload.get("onlineUsers") or payload.get("users") or []
            online_rows = [self._user_to_row(user) for user in users]
            self._online_rows = self._merge_user_rows(online_rows, self._all_user_rows)
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
            if isinstance(payload, dict):
                # If it's my own profile (no ID passed, or ID matches me), save to self._profile
                if not payload.get("id") or payload.get("id") == self._current_user_id or kind == "profile-updated":
                    self._profile = payload
                    self.changed.emit()
                else:
                    # Notify UI about someone else's profile
                    self.resultFromWorker.emit("other-profile-ready", payload)
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
        return {
            "slug": slug,
            "label": str(room.get("name") or room.get("label") or slug or "Room"),
            "unread": int(room.get("unreadCount") or room.get("unread") or 0),
        }

    def _room_label(self, slug: str) -> str:
        for index in range(self.rooms.count()):
            row = self.rooms.get(index)
            if row.get("slug") == slug:
                return str(row.get("label") or slug)
        return slug

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
        return {
            "name": name,
            "detail": detail,
            "avatar": str(user.get("avatarUrl") or user.get("avatar") or user.get("avatarfull") or user.get("avatarmedium") or ""),
            "mention": mention,
            "discordId": str(user.get("discordId") or ""),
        }

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
        self._ws.close()
        url = QUrl(f"{CHAT_WS_BASE}/ws/chat?token={self._token}")
        self._ws.open(url)

    @Slot()
    def _on_ws_connected(self) -> None:
        self._status = self._t("home.chat.connected")
        self.changed.emit()
        if self._selected_room:
            self._ws.sendTextMessage(json.dumps({"type": "join_chat", "chatSlug": self._selected_room}))

    @Slot()
    def _on_ws_disconnected(self) -> None:
        if self._token:
            QTimer.singleShot(5000, self._connect_ws)

    @Slot(str)
    def _on_ws_text_received(self, text: str) -> None:
        try:
            data = json.loads(text)
        except Exception:
            return
        dtype = data.get("type")
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
        rows = normalize_messages([msg], self.currentUserName, self._current_user_steam_id, self.discordId)
        if not rows: return
        row = rows[0]
        current_rows = [self.messages.get(i) for i in range(self.messages.count())]
        current_rows.append(row)
        self.messages.set_items(current_rows)
        self.changed.emit()

    def _handle_ws_message_update(self, msg: dict) -> None:
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


class ItemSearchController(QObject):
    changed = Signal()
    rowsLoaded = Signal(object, str, str)

    def __init__(self, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._query = ""
        self._status_key = "item_search.loading"
        self._status_count = 0
        self._status_message = ""
        self._loading = False
        self._loaded = False
        self._best_match = ""
        self._selected_name = ""
        self._total = 0
        self._last_update = "-"
        self.items = DictListModel(
            ["rowType", "region", "code", "warehouse", "quantity", "updatedAt", "icon", "total"],
            self,
        )
        self.suggestions = DictListModel(["name"], self)
        self._all_rows: list[dict[str, Any]] = []
        self.rowsLoaded.connect(self._apply_loaded_rows)
        QTimer.singleShot(0, self.refresh)


    @Property("QVariantMap", notify=changed)
    def userProfile(self) -> dict:
        return getattr(self, "_profile", {})

    @Slot()
    def logout(self) -> None:
        self._token = ""
        self._discord_user_settings.clear()
        save_settings(self.settings)
        self._ws.close()
        self._discord_login_required = True
        self._current_user_id = ""
        self._profile = {}
        self._status = "Disconnected"
        self.changed.emit()



    @Property(str, notify=changed)
    def status(self) -> str:
        if self._status_key == "item_search.loaded":
            return f"{self._status_count} items loaded."
        if self._status_key == "item_search.error":
            return f"Error loading items: {self._status_message}"
        if self._status_key == "item_search.best_match":
            return f"Suggestion: {self._best_match}"
        return self._status_message or "Loading items from the API..."

    @Property(str, notify=changed)
    def statusKey(self) -> str:
        return self._status_key

    @Property(int, notify=changed)
    def statusCount(self) -> int:
        return self._status_count

    @Property(str, notify=changed)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(str, notify=changed)
    def query(self) -> str:
        return self._query

    @Property(bool, notify=changed)
    def loading(self) -> bool:
        return self._loading

    @Property(bool, notify=changed)
    def loaded(self) -> bool:
        return self._loaded

    @Property(str, notify=changed)
    def bestMatch(self) -> str:
        return self._best_match

    @Property(str, notify=changed)
    def selectedName(self) -> str:
        return self._selected_name

    @Property(int, notify=changed)
    def total(self) -> int:
        return self._total

    @Property(str, notify=changed)
    def lastUpdate(self) -> str:
        return self._last_update

    @Property(QObject, constant=True)
    def resultRows(self) -> QObject:
        return self.items

    @Property(QObject, constant=True)
    def suggestionRows(self) -> QObject:
        return self.suggestions

    @Property("QVariantList", notify=changed)
    def resultRowItems(self) -> list[dict[str, Any]]:
        return self.items.items()

    @Property("QVariantList", notify=changed)
    def suggestionRowItems(self) -> list[dict[str, Any]]:
        return self.suggestions.items()

    @Slot()
    def refresh(self) -> None:
        if self._loading:
            return
        self._loading = True
        self._status_key = "item_search.loading"
        self._status_message = ""
        self.changed.emit()

        def worker() -> None:
            try:
                stockpile = self.settings.get("stockpile", {})
                api_response = request_stockpile_debug(str(stockpile.get("api_url", DEFAULT_API_URL)))
                rows = api_item_rows(api_response)
                last_update = format_to_local_pc_time(api_last_update(api_response))
                self.rowsLoaded.emit(rows, last_update, "")
            except Exception as exc:
                self.rowsLoaded.emit([], "-", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object, str, str)
    def _apply_loaded_rows(self, rows: object, last_update: str, error: str) -> None:
        self._loading = False
        if error:
            self._status_key = "item_search.error"
            self._status_message = error
            self.changed.emit()
            return
        self._all_rows = list(rows) if isinstance(rows, list) else []
        self._last_update = last_update or "-"
        self._loaded = True
        self._status_key = "item_search.loaded"
        self._status_count = len(self._all_rows)
        self._update_search_models()
        self.changed.emit()

    @Slot(str)
    def search(self, query: str) -> None:
        self._query = query
        self._update_search_models()
        self.changed.emit()

    @Slot(str)
    def chooseSuggestion(self, name: str) -> None:
        self._query = str(name)
        self._update_search_models()
        self.changed.emit()

    def _item_names(self) -> list[str]:
        names = {str(item.get("display_name") or "-") for item in self._all_rows if item.get("display_name")}
        return sorted(names, key=str.lower)

    def _suggestions_for_query(self, query: str) -> list[str]:
        lower = query.strip().lower()
        if not lower:
            return []
        names = self._item_names()
        starts = [name for name in names if name.lower().startswith(lower)]
        contains = [name for name in names if lower in name.lower() and name not in starts]
        return (starts + contains)[:8]

    def _matching_rows(self) -> list[dict[str, Any]]:
        query = self._query.strip().lower()
        if not query:
            return []
        exact = [item for item in self._all_rows if str(item.get("display_name") or "").lower() == query]
        if exact:
            return exact
        suggestions = self._suggestions_for_query(self._query)
        if suggestions:
            selected = suggestions[0].lower()
            return [item for item in self._all_rows if str(item.get("display_name") or "").lower() == selected]
        return [item for item in self._all_rows if query in str(item.get("display_name") or "").lower()]

    @staticmethod
    def _split_location(warehouse: str) -> tuple[str, str, str]:
        parts = [part.strip() for part in str(warehouse or "-").split("/") if part.strip()]
        if len(parts) >= 3:
            return parts[0], parts[-2], parts[-1]
        if len(parts) == 2:
            return parts[0], parts[1], parts[1]
        value = parts[0] if parts else "-"
        return value, value, value

    def _update_search_models(self) -> None:
        suggestions = self._suggestions_for_query(self._query)
        self.suggestions.set_items([{"name": name} for name in suggestions])
        self._best_match = suggestions[0] if suggestions else ""

        rows = self._matching_rows()
        if not self._query.strip():
            self.items.set_items([])
            self._selected_name = ""
            self._total = 0
            self._status_key = "item_search.loaded" if self._loaded else "item_search.loading"
            self._status_count = len(self._all_rows)
            return

        if rows:
            self._selected_name = str(rows[0].get("display_name") or self._query)
            self._total = sum(max(0, int(item.get("quantity", 0) or 0)) for item in rows)
            self._status_key = "item_search.best_match" if self._best_match else "item_search.loaded"
        else:
            self._selected_name = self._query
            self._total = 0
            self._status_key = "item_search.best_match_empty"

        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in rows:
            region, _name, _code = self._split_location(str(item.get("warehouse") or "-"))
            grouped.setdefault(region, []).append(item)

        result_rows: list[dict[str, Any]] = []
        for region in sorted(grouped):
            region_rows = sorted(grouped[region], key=lambda item: str(item.get("warehouse") or ""))
            region_total = sum(max(0, int(item.get("quantity", 0) or 0)) for item in region_rows)
            result_rows.append(
                {
                    "rowType": "region",
                    "region": region,
                    "code": "",
                    "warehouse": "",
                    "quantity": 0,
                    "updatedAt": "",
                    "icon": "",
                    "total": region_total,
                }
            )
            for item in region_rows:
                _region, _name, code = self._split_location(str(item.get("warehouse") or "-"))
                icon_path = str(item.get("icon_path") or "")
                result_rows.append(
                    {
                        "rowType": "item",
                        "region": region,
                        "code": code,
                        "warehouse": str(item.get("warehouse") or "-"),
                        "quantity": max(0, int(item.get("quantity", 0) or 0)),
                        "updatedAt": format_to_local_pc_time(str(item.get("warehouse_last_update") or "-")),
                        "icon": file_url(icon_path) if icon_path and Path(icon_path).exists() else "",
                        "total": 0,
                    }
                )
        self.items.set_items(result_rows)


class IdentifyItemController(QObject):
    changed = Signal()
    scanFinished = Signal(list, str)
    monitorFinished = Signal(object, str, bool)

    def __init__(self, item_search: ItemSearchController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.item_search = item_search
        self.results = DictListModel(["name", "score", "scoreText", "icon", "path"], self)
        self.monitorMatches = DictListModel(["matchX", "matchY", "matchW", "matchH"], self)
        self._templates, self._status = index_icon_templates()
        self._status = f"{self._status} | {identify_dependencies_status()}"
        self._selected_path: Path | None = None
        self._selected_image_url = ""
        self._mode = "Hybrid"
        self._threshold = 0.85
        self._scanning = False
        self._clipboard_image = None
        self._last_result_rows: list[dict[str, Any]] = []
        self._monitoring = False
        self._monitor_target_name = ""
        self._monitor_overlay_visible = False
        self._monitor_worker_active = False
        self._monitor_hwnd = 0
        self._monitor_tick = 0
        self._monitor_timer = QTimer(self)
        self._monitor_timer.setInterval(280)
        self._monitor_timer.timeout.connect(self._run_monitor_tick)
        self.scanFinished.connect(self._apply_scan_result)
        self.monitorFinished.connect(self._apply_monitor_result)


    @Property("QVariantMap", notify=changed)
    def userProfile(self) -> dict:
        return getattr(self, "_profile", {})

    @Slot()
    def logout(self) -> None:
        self._token = ""
        self._discord_user_settings.clear()
        save_settings(self.settings)
        self._ws.close()
        self._discord_login_required = True
        self._current_user_id = ""
        self._profile = {}
        self._status = "Disconnected"
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
        return bool(identify_cv2 is not None and identify_np is not None and identify_image_grab is not None)

    @Property(str, notify=changed)
    def monitorTarget(self) -> str:
        return self._monitor_target_name

    @Property(bool, notify=changed)
    def monitorOverlayVisible(self) -> bool:
        return self._monitor_overlay_visible

    @Property(int, notify=changed)
    def indexedCount(self) -> int:
        return len(self._templates)

    @Property(QObject, constant=True)
    def resultsModel(self) -> QObject:
        return self.results

    @Property(QObject, constant=True)
    def monitorMatchesModel(self) -> QObject:
        return self.monitorMatches

    @Property("QStringList", constant=True)
    def modes(self) -> list[str]:
        return ["Gray", "Color", "Hybrid"]

    @Slot()
    def reindex(self) -> None:
        self._templates, self._status = index_icon_templates()
        self._status = f"{self._status} | {identify_dependencies_status()}"
        self.changed.emit()

    @Slot(str)
    def setMode(self, mode: str) -> None:
        if mode not in {"Gray", "Color", "Hybrid"}:
            return
        self._mode = mode
        self.changed.emit()

    @Slot(float)
    def setThreshold(self, value: float) -> None:
        self._threshold = max(0.5, min(0.99, float(value)))
        self.changed.emit()

    @Slot(int)
    def selectResult(self, index: int) -> None:
        if index < 0 or index >= len(self._last_result_rows):
            return
        self._monitor_target_name = str(self._last_result_rows[index].get("name") or "")
        if self._monitoring and self._monitor_target_name:
            self._status = f"Monitoring: {self._monitor_target_name}"
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
        self._selected_image_url = file_url(path)
        self._status = f"Selected: {path.name}"
        self.changed.emit()

    @Slot()
    def scanSelected(self) -> None:
        if self._scanning:
            return
        if not self._selected_path and self._clipboard_image is None:
            self._status = "Select, paste, or capture an image first."
            self.changed.emit()
            return
        self._begin_scan()

        def worker() -> None:
            if self._clipboard_image is not None:
                matches, status = scan_image(self._clipboard_image, self._templates, mode=self._mode)
            else:
                matches, status = scan_image_path(Path(self._selected_path), self._templates, mode=self._mode)
            self.scanFinished.emit([match_to_dict(match) for match in matches], status)

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def pasteClipboard(self) -> None:
        image, status = grab_clipboard_image()
        if image is None:
            self._status = status
            self.changed.emit()
            return
        self._clipboard_image = image
        self._selected_path = None
        preview_path = identify_preview_path()
        try:
            image.save(preview_path)
            self._selected_image_url = file_url(preview_path)
        except Exception:
            self._selected_image_url = ""
        self._status = status
        self.changed.emit()
        self.scanSelected()

    @Slot()
    def captureScreen(self) -> None:
        image, status = grab_screen_image()
        if image is None:
            self._status = status
            self.changed.emit()
            return
        self._clipboard_image = image
        self._selected_path = None
        preview_path = identify_preview_path()
        try:
            image.save(preview_path)
            self._selected_image_url = file_url(preview_path)
        except Exception:
            self._selected_image_url = ""
        self._status = status
        self.changed.emit()
        self.scanSelected()

    def _begin_scan(self) -> None:
        self._scanning = True
        self._status = f"Scanning {len(self._templates)} templates with {self._mode.lower()} mode..."
        self.changed.emit()

    @Slot(list, str)
    def _apply_scan_result(self, matches: list[dict[str, Any]], status: str) -> None:
        visible = [match for match in matches if float(match.get("score", 0.0)) >= self._threshold]
        rows = visible or matches
        self._last_result_rows = rows
        self.results.set_items(rows)
        if rows and not self._monitor_target_name:
            self._monitor_target_name = str(rows[0].get("name") or "")
        self._status = f"{status}; showing {len(rows)} result(s)"
        self._scanning = False
        self.changed.emit()

    @Slot()
    def toggleMonitor(self) -> None:
        if self._monitoring:
            self.stopMonitor()
        else:
            self.startMonitor()

    @Slot()
    def startMonitor(self) -> None:
        if not self.monitorAvailable:
            self._status = "Install numpy and opencv-python for on-screen monitoring."
            self.changed.emit()
            return
        if not self._monitor_target_name and self._last_result_rows:
            self._monitor_target_name = str(self._last_result_rows[0].get("name") or "")
        if not self._monitor_target_name and self._current_target_gray() is None:
            self._status = "Run an identification first."
            self.changed.emit()
            return
        self._monitoring = True
        self._monitor_tick = 0
        self._status = f"Monitoring: {self._monitor_target_name or 'selected image'}"
        self._monitor_timer.start()
        self.changed.emit()

    @Slot()
    def stopMonitor(self) -> None:
        self._monitoring = False
        self._monitor_worker_active = False
        self._monitor_overlay_visible = False
        self._monitor_timer.stop()
        self.monitorMatches.set_items([])
        self._status = "Monitoring stopped."
        self.changed.emit()

    def _current_target_gray(self):
        if self._selected_path and self._selected_path.exists():
            gray, _color = prepare_image_path(self._selected_path)
            return gray
        if self._clipboard_image is not None:
            gray, _color = prepare_image(self._clipboard_image)
            return gray
        return None

    def _monitor_templates(self) -> list[Any]:
        templates: list[Any] = []
        current_gray = self._current_target_gray()
        if current_gray is not None:
            templates.append(current_gray)
        if self._monitor_target_name:
            templates.extend(template.gray for template in self._templates if template.name == self._monitor_target_name)
        deduped: list[Any] = []
        seen: set[int] = set()
        for template in templates:
            identity = id(template)
            if identity in seen:
                continue
            seen.add(identity)
            deduped.append(template)
        return deduped

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

    @Slot()
    def _run_monitor_tick(self) -> None:
        if not self._monitoring or self._monitor_worker_active:
            return
        self._monitor_tick += 1
        templates = self._monitor_templates()
        if not templates:
            self._status = "Run an identification first."
            self._monitor_overlay_visible = False
            self.monitorMatches.set_items([])
            self.changed.emit()
            return
        if not self._is_foxhole_focused():
            self._status = f"Monitoring: {self._monitor_target_name or 'selected image'} | waiting for Foxhole focus"
            self._monitor_overlay_visible = False
            self.monitorMatches.set_items([])
            self.changed.emit()
            return
        bbox = self._window_client_rect()
        threshold = float(self._threshold)
        self._monitor_worker_active = True

        def worker() -> None:
            try:
                screenshot = identify_image_grab.grab(bbox=bbox) if bbox else identify_image_grab.grab()
                screen_np = identify_np.array(screenshot)
                gray = identify_cv2.cvtColor(screen_np, identify_cv2.COLOR_RGB2GRAY)
                matches: list[dict[str, int]] = []
                best_score = -1.0
                for template in templates:
                    for scale in (0.85, 1.0, 1.15):
                        th = max(12, int(template.shape[0] * scale))
                        tw = max(12, int(template.shape[1] * scale))
                        if th >= gray.shape[0] or tw >= gray.shape[1]:
                            continue
                        interpolation = identify_cv2.INTER_AREA if scale < 1 else identify_cv2.INTER_CUBIC
                        resized = identify_cv2.resize(template, (tw, th), interpolation=interpolation)
                        result = identify_cv2.matchTemplate(gray, resized, identify_cv2.TM_CCOEFF_NORMED)
                        _min_val, max_val, _min_loc, _max_loc = identify_cv2.minMaxLoc(result)
                        best_score = max(best_score, float(max_val))
                        ys, xs = identify_np.where(result >= threshold)
                        for x, y in zip(xs.tolist(), ys.tolist()):
                            gx = int(x + (bbox[0] if bbox else 0))
                            gy = int(y + (bbox[1] if bbox else 0))
                            if all(abs(gx - item["matchX"]) > 20 or abs(gy - item["matchY"]) > 20 for item in matches):
                                matches.append({"matchX": gx, "matchY": gy, "matchW": tw, "matchH": th})
                            if len(matches) >= 10:
                                break
                        if len(matches) >= 10:
                            break
                    if len(matches) >= 10:
                        break
                if matches:
                    self.monitorFinished.emit(matches, f"Found: {len(matches)}", True)
                else:
                    self.monitorFinished.emit([], f"Searching... score {best_score:.3f}", False)
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
        self.monitorMatches.set_items(rows)
        self._monitor_overlay_visible = bool(visible and rows and self._monitoring)
        self._status = status
        self.changed.emit()

    @Slot()
    def shutdown(self) -> None:
        self.stopMonitor()


class ProductionController(QObject):
    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.availableItems = DictListModel(
            ["key", "name", "category", "faction", "mode", "icon", "quantityPerCrate", "bmat", "emat", "rmat", "hemat", "relic"],
            self,
        )
        self.categories = DictListModel(["name", "mark", "count", "active", "icon"], self)
        self.queue = DictListModel(["key", "name", "category", "faction", "quantity", "icon", "line"], self)
        self.queueCategories = DictListModel(["name", "mark", "count", "limit", "active", "icon", "slots"], self)
        self.materials = DictListModel(["key", "label", "quantity", "crates", "icon"], self)
        self.routeTrips = DictListModel(["title", "vehicle", "materials", "orders", "inputSlots", "outputCrates", "capacity"], self)
        self._all_items, self._status = load_production_items()
        self._items_by_key = {item.key: item for item in self._all_items}
        self._queue: dict[str, list[ProductionItem]] = {category: [] for category in CATEGORY_ORDER}
        self._mode = "mpf"
        self._faction = "Neutral"
        self._category = self._first_available_category()
        self._query = ""
        self._factory_multiplier = 1
        self._route_vehicle_mode = "Dunne"
        self._summary = "-"
        self._orders = "-"
        self._route_summary = "-"
        self._warning = ""
        self.refresh()


    @Property("QVariantMap", notify=changed)
    def userProfile(self) -> dict:
        return getattr(self, "_profile", {})

    @Slot()
    def logout(self) -> None:
        self._token = ""
        self._discord_user_settings.clear()
        save_settings(self.settings)
        self._ws.close()
        self._discord_login_required = True
        self._current_user_id = ""
        self._profile = {}
        self._status = "Disconnected"
        self.changed.emit()



    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def mode(self) -> str:
        return self._mode

    @Property(str, notify=changed)
    def faction(self) -> str:
        return self._faction

    @Property(str, notify=changed)
    def category(self) -> str:
        return self._category

    @Property(str, notify=changed)
    def query(self) -> str:
        return self._query

    @Property(int, notify=changed)
    def factoryMultiplier(self) -> int:
        return self._factory_multiplier

    @Property(str, notify=changed)
    def routeVehicleMode(self) -> str:
        return self._route_vehicle_mode

    @Property(str, notify=changed)
    def summary(self) -> str:
        return self._summary

    @Property(str, notify=changed)
    def orders(self) -> str:
        return self._orders

    @Property(str, notify=changed)
    def routeSummary(self) -> str:
        return self._route_summary

    @Property(str, notify=changed)
    def warning(self) -> str:
        return self._warning

    @Property("QStringList", constant=True)
    def modes(self) -> list[str]:
        return ["mpf", "factory"]

    @Property("QStringList", constant=True)
    def factions(self) -> list[str]:
        return ["Neutral", "Colonial", "Warden"]

    @Property("QStringList", notify=changed)
    def routeVehicleOptions(self) -> list[str]:
        return ["Dunne", "Flatbed"] if self._mode == "mpf" else ["Dunne"]

    @Property("QVariantList", notify=changed)
    def availableItemRows(self) -> list[dict[str, Any]]:
        return self.availableItems.items()

    @Property("QVariantList", notify=changed)
    def categoryRows(self) -> list[dict[str, Any]]:
        return self.categories.items()

    @Property("QVariantList", notify=changed)
    def queueRows(self) -> list[dict[str, Any]]:
        return self.queue.items()

    @Property("QVariantList", notify=changed)
    def queueCategoryRows(self) -> list[dict[str, Any]]:
        return self.queueCategories.items()

    @Property("QVariantList", notify=changed)
    def materialRows(self) -> list[dict[str, Any]]:
        return self.materials.items()

    @Property("QVariantList", notify=changed)
    def routeTripRows(self) -> list[dict[str, Any]]:
        return self.routeTrips.items()

    @Slot()
    def reload(self) -> None:
        self._all_items, self._status = load_production_items()
        self._items_by_key = {item.key: item for item in self._all_items}
        self._category = self._first_available_category()
        self.clear()

    @Slot(str)
    def setMode(self, mode: str) -> None:
        if mode not in {"mpf", "factory"} or mode == self._mode:
            return
        self._mode = mode
        if self._mode != "mpf":
            self._route_vehicle_mode = "Dunne"
        self._queue = {category: [] for category in CATEGORY_ORDER}
        self._category = self._first_available_category()
        self.refresh()

    @Slot(str)
    def setFaction(self, faction: str) -> None:
        if faction not in {"Neutral", "Colonial", "Warden"}:
            return
        self._faction = faction
        self.refresh()

    @Slot(str)
    def setCategory(self, category: str) -> None:
        if category not in CATEGORY_ORDER:
            return
        self._category = category
        self.refresh()

    @Slot(str)
    def search(self, query: str) -> None:
        self._query = query
        self.refresh()

    @Slot(int)
    def setFactoryMultiplier(self, value: int) -> None:
        self._factory_multiplier = min(2, max(1, int(value)))
        self.refresh()

    @Slot(str)
    def setRouteVehicleMode(self, value: str) -> None:
        if value not in {"Dunne", "Flatbed"}:
            return
        if self._mode != "mpf":
            value = "Dunne"
        if value == self._route_vehicle_mode:
            return
        self._route_vehicle_mode = value
        self.refresh()

    @Slot(str)
    def addItemByKey(self, key: str) -> None:
        item = self._items_by_key.get(key)
        if not item:
            self._warning = "Item not found."
            self.changed.emit()
            return
        self._add_item(item, fill=False)

    @Slot(str)
    def fillCategoryWithItem(self, key: str) -> None:
        item = self._items_by_key.get(key)
        if item:
            category_queue = self._queue.setdefault(item.category, [])
            limit = category_limit(item.category, self._mode, self._factory_multiplier)
            if category_queue and category_queue[0].item_id == item.item_id and len(category_queue) >= limit:
                category_queue.clear()
                self.refresh()
            else:
                self._add_item(item, fill=True)

    @Slot(str)
    def removeItemByKey(self, key: str) -> None:
        item = self._items_by_key.get(key)
        if not item:
            return
        rows = self._queue.get(item.category, [])
        for index, queued in enumerate(rows):
            if queued.item_id == item.item_id:
                rows.pop(index)
                self.refresh()
                return

    @Slot(str, int)
    def addItem(self, name: str, quantity: int) -> None:
        match = next((item for item in self._all_items if item.name.lower() == name.strip().lower() and item.mode == self._mode), None)
        if not match:
            self._warning = f"Item not found: {name}"
            self.changed.emit()
            return
        for _ in range(max(1, int(quantity))):
            self._add_item(match, fill=False, emit=False)
        self.refresh()

    @Slot(str, int)
    def removeQueueRow(self, category: str, index: int) -> None:
        rows = self._queue.get(category, [])
        if 0 <= index < len(rows):
            rows.pop(index)
        self.refresh()

    @Slot(str, int)
    def removeQueueSlot(self, category: str, index: int) -> None:
        self.removeQueueRow(category, index)

    @Slot()
    def clear(self) -> None:
        self._queue = {category: [] for category in CATEGORY_ORDER}
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        categories = available_categories(self._all_items, self._mode)
        if self._category not in categories:
            self._category = categories[0] if categories else ""

        filtered = filter_items(
            self._all_items,
            mode=self._mode,
            category=self._category,
            faction=self._faction,
            query=self._query,
        )
        self.availableItems.set_items([self._item_to_model(item) for item in filtered])
        self.categories.set_items(
            [
                {
                    "name": category,
                    "mark": str(CATEGORY_RULES.get(category, {}).get("mark") or category[:2].upper()),
                    "count": len(self._queue.get(category, [])),
                    "active": category == self._category,
                    "icon": self._category_icon_url(category),
                }
                for category in categories
            ]
        )
        self.queue.set_items(self._queue_rows())
        self.queueCategories.set_items(self._queue_category_rows(categories))
        totals = calculate_queue(self._queue, mode=self._mode)
        self.materials.set_items(self._material_rows(totals["totals"]))
        self.routeTrips.set_items(self._route_rows())
        self._summary = f"{totals['total_crates']} crates | {totals['total_items']} produced items"
        if self._mode == "mpf":
            self._orders = f"{totals['active_orders']} orders | {totals['discount']:.1f}% material discount"
        else:
            self._orders = f"{totals['total_crates']} crates | {totals['max_factory']} factories needed"
        self._route_summary = f"{self.routeTrips.count()} trips | {self._route_vehicle_mode}"
        self._warning = "  ".join(totals["warnings"])
        if self._all_items:
            self._status = f"{len(filtered)} visible / {len(self._all_items)} loaded"
        self.changed.emit()

    def _first_available_category(self) -> str:
        categories = available_categories(self._all_items, self._mode)
        return categories[0] if categories else ""

    def _add_item(self, item: ProductionItem, *, fill: bool, emit: bool = True) -> None:
        category_queue = self._queue.setdefault(item.category, [])
        if category_queue and category_queue[0].item_id != item.item_id:
            category_queue.clear()
        limit = category_limit(item.category, self._mode, self._factory_multiplier)
        if fill:
            while len(category_queue) < limit:
                category_queue.append(item)
        elif len(category_queue) < limit:
            category_queue.append(item)
        else:
            self._warning = f"{item.category} is already at its {limit} crate limit."
        if emit:
            self.refresh()

    def _item_to_model(self, item: ProductionItem) -> dict[str, Any]:
        return {
            "key": item.key,
            "name": item.name,
            "category": item.category,
            "faction": item.faction,
            "mode": item.mode,
            "icon": file_url(item.icon_path) if item.icon_path and Path(item.icon_path).exists() else "",
            "quantityPerCrate": item.quantity_per_crate,
            "bmat": int(item.bmat),
            "emat": int(item.emat),
            "rmat": int(item.rmat),
            "hemat": int(item.hemat),
            "relic": int(item.relic),
        }

    def _queue_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for category in CATEGORY_ORDER:
            for index, item in enumerate(self._queue.get(category, [])):
                rows.append(
                    {
                        "key": item.key,
                        "name": item.name,
                        "category": category,
                        "faction": item.faction,
                        "quantity": item.quantity_per_crate,
                        "icon": file_url(item.icon_path) if item.icon_path and Path(item.icon_path).exists() else "",
                        "line": index,
                    }
                )
        return rows

    def _category_icon_url(self, category: str) -> str:
        mark = str(CATEGORY_RULES.get(category, {}).get("mark") or category[:2].upper()).lower()
        path = CALCULATOR_MENU_DIR / f"{mark}.png"
        return file_url(path) if path.exists() else ""

    def _queue_category_rows(self, categories: list[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for category in categories:
            queued = self._queue.get(category, [])
            limit = category_limit(category, self._mode, self._factory_multiplier)
            slots: list[dict[str, Any]] = []
            for index in range(limit):
                if index < len(queued):
                    item = queued[index]
                    discount = int((1 - discount_multiplier(index + 1)) * 100) if self._mode == "mpf" else 0
                    slots.append(
                        {
                            "filled": True,
                            "line": index,
                            "name": item.name,
                            "icon": file_url(item.icon_path) if item.icon_path and Path(item.icon_path).exists() else "",
                            "discount": discount,
                        }
                    )
                else:
                    slots.append({"filled": False, "line": index, "name": "", "icon": "", "discount": 0})
            rows.append(
                {
                    "name": category,
                    "mark": str(CATEGORY_RULES.get(category, {}).get("mark") or category[:2].upper()),
                    "count": len(queued),
                    "limit": limit,
                    "active": category == self._category,
                    "icon": self._category_icon_url(category),
                    "slots": slots,
                }
            )
        return rows

    def _material_rows(self, totals: dict[str, float]) -> list[dict[str, Any]]:
        rows = []
        for key, label in MATERIALS:
            quantity = int(math.ceil(max(0, totals.get(key, 0.0)) - 1e-9))
            if quantity <= 0:
                continue
            crate_size = MATERIAL_CRATE_SIZES.get(key, 1)
            rows.append(
                {
                    "key": key,
                    "label": label,
                    "quantity": quantity,
                    "crates": int(math.ceil(quantity / crate_size)),
                    "icon": file_url(MATERIAL_ICON_PATHS[key]) if key in MATERIAL_ICON_PATHS and MATERIAL_ICON_PATHS[key].exists() else "",
                }
            )
        return rows

    def _route_rows(self) -> list[dict[str, Any]]:
        trips = plan_transport_routes(self._queue, mode=self._mode, vehicle=self._route_vehicle_mode)
        rows: list[dict[str, Any]] = []
        for index, trip in enumerate(trips, 1):
            vehicle = str(trip.get("vehicle") or self._route_vehicle_mode)
            rows.append(
                {
                    "title": f"Trip {index}",
                    "vehicle": vehicle,
                    "materials": format_route_materials(trip.get("materials", {}), vehicle=vehicle),
                    "orders": format_route_orders(trip.get("orders", [])),
                    "inputSlots": int(trip.get("input_slots") or 0),
                    "outputCrates": int(trip.get("output_crates") or 0),
                    "capacity": int(trip.get("max_slots") or 15),
                }
            )
        return rows


class TimeTaskController(QObject):
    changed = Signal()
    statusFromWorker = Signal(str)

    def __init__(self, i18n: I18nController | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self._status = self._t("timetask.status_idle")
        self._metric = self._t("timetask.metric_empty")
        self._macro_name = "macro"
        self._speed = "1.0"
        self._repeat = "1"
        self._delay = "0s"
        self._stock_macro_name = self._t("timetask.none")
        self._stock_interval = "1"
        self._selected_path: Path | None = None
        self._summaries = []
        self._record_overlay_visible = False
        self._replay_overlay_visible = False
        self._record_overlay_title = self._t("timetask.overlay_ready")
        self._record_overlay_detail = self._t("timetask.overlay_record_options")
        self._record_overlay_hint = self._t("timetask.overlay_focus_hint")
        self._record_overlay_accent = "#5eead4"
        self._replay_overlay_title = self._t("timetask.replay_overlay_title")
        self._replay_overlay_detail = self._t("timetask.replay_empty")
        self._replay_overlay_accent = "#62d7a4"
        self._countdown_value = 0
        self._settings = load_settings()
        time_task_settings = self._settings.get("time_task", {})
        self._record_overlay_x = self._int_or_default(time_task_settings.get("overlay_record_x"), -1)
        self._record_overlay_y = self._int_or_default(time_task_settings.get("overlay_record_y"), -1)
        self._replay_overlay_x = self._int_or_default(time_task_settings.get("overlay_replay_x"), -1)
        self._replay_overlay_y = self._int_or_default(time_task_settings.get("overlay_replay_y"), -1)
        self._macros = DictListModel(["name", "duration", "events", "createdAt", "path", "selected"], self)
        self.statusFromWorker.connect(self._set_status_from_worker)
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._run_countdown_tick)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(300)
        self._poll_timer.timeout.connect(self._poll_state)
        try:
            self._recorder = MacroRecorder(lambda message: self.statusFromWorker.emit(str(message)))
            self._available = True
        except Exception as exc:
            self._recorder = None
            self._available = False
            self._status = f"TimeTask unavailable: {exc}"
        self.refreshMacros()

    @staticmethod
    def _int_or_default(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _t(self, key: str, **kwargs: Any) -> str:
        translator = self.i18n.translator if self.i18n is not None else Translator()
        return translator.t(key, **kwargs)

    @Property(QObject, constant=True)
    def macros(self) -> DictListModel:
        return self._macros


    @Property("QVariantMap", notify=changed)
    def userProfile(self) -> dict:
        return getattr(self, "_profile", {})

    @Slot()
    def logout(self) -> None:
        self._token = ""
        self._discord_user_settings.clear()
        save_settings(self.settings)
        self._ws.close()
        self._discord_login_required = True
        self._current_user_id = ""
        self._profile = {}
        self._status = "Disconnected"
        self.changed.emit()



    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def metric(self) -> str:
        return self._metric

    @Property(bool, notify=changed)
    def available(self) -> bool:
        return self._available

    @Property(bool, notify=changed)
    def recording(self) -> bool:
        return bool(self._recorder and self._recorder.recording)

    @Property(bool, notify=changed)
    def paused(self) -> bool:
        return bool(self._recorder and (self._recorder.paused or self._recorder.replay_paused))

    @Property(bool, notify=changed)
    def replaying(self) -> bool:
        return bool(self._recorder and self._recorder.replaying)

    @Property(str, notify=changed)
    def macroName(self) -> str:
        return self._macro_name

    @Property(str, notify=changed)
    def speed(self) -> str:
        return self._speed

    @Property(str, notify=changed)
    def repeat(self) -> str:
        return self._repeat

    @Property(str, notify=changed)
    def delay(self) -> str:
        return self._delay

    @Property(str, notify=changed)
    def stockMacroName(self) -> str:
        return self._stock_macro_name

    @Property(str, notify=changed)
    def stockInterval(self) -> str:
        return self._stock_interval

    @Property(str, notify=changed)
    def selectedMacroName(self) -> str:
        return self._selected_path.stem if self._selected_path else ""

    @Property(bool, notify=changed)
    def recordOverlayVisible(self) -> bool:
        return self._record_overlay_visible

    @Property(str, notify=changed)
    def recordOverlayTitle(self) -> str:
        return self._record_overlay_title

    @Property(str, notify=changed)
    def recordOverlayDetail(self) -> str:
        return self._record_overlay_detail

    @Property(str, notify=changed)
    def recordOverlayHint(self) -> str:
        return self._record_overlay_hint

    @Property(str, notify=changed)
    def recordOverlayAccent(self) -> str:
        return self._record_overlay_accent

    @Property(int, notify=changed)
    def recordOverlayX(self) -> int:
        return self._record_overlay_x

    @Property(int, notify=changed)
    def recordOverlayY(self) -> int:
        return self._record_overlay_y

    @Property(bool, notify=changed)
    def replayOverlayVisible(self) -> bool:
        return self._replay_overlay_visible

    @Property(str, notify=changed)
    def replayOverlayTitle(self) -> str:
        return self._replay_overlay_title

    @Property(str, notify=changed)
    def replayOverlayDetail(self) -> str:
        return self._replay_overlay_detail

    @Property(str, notify=changed)
    def replayOverlayAccent(self) -> str:
        return self._replay_overlay_accent

    @Property(int, notify=changed)
    def replayOverlayX(self) -> int:
        return self._replay_overlay_x

    @Property(int, notify=changed)
    def replayOverlayY(self) -> int:
        return self._replay_overlay_y

    @Property("QStringList", constant=True)
    def speedOptions(self) -> list[str]:
        return ["0.5", "1.0", "1.5", "2.0"]

    @Property("QStringList", constant=True)
    def delayOptions(self) -> list[str]:
        return ["0s", "0.5s", "1s", "2s", "5s", "10s", "1 min", "2 min", "5 min"]

    @Property("QStringList", notify=changed)
    def stockMacroOptions(self) -> list[str]:
        return [self._t("timetask.none")] + [summary.name for summary in self._summaries]

    @Property(str, constant=True)
    def macroFolder(self) -> str:
        return str(MACRO_DIR)

    @Slot(str)
    def setMacroName(self, value: str) -> None:
        self._macro_name = str(value or "macro")
        self.changed.emit()

    @Slot(str)
    def setSpeed(self, value: str) -> None:
        self._speed = str(value or "1.0")
        self.changed.emit()

    @Slot(str)
    def setRepeat(self, value: str) -> None:
        self._repeat = str(value or "1")
        self.changed.emit()

    @Slot(str)
    def setDelay(self, value: str) -> None:
        self._delay = str(value or "0s")
        self.changed.emit()

    @Slot(str)
    def setStockMacroName(self, value: str) -> None:
        self._stock_macro_name = str(value or self._t("timetask.none"))
        self.changed.emit()

    @Slot(str)
    def setStockInterval(self, value: str) -> None:
        self._stock_interval = str(value or "1")
        self.changed.emit()

    @Slot(int)
    def selectMacro(self, row: int) -> None:
        if row < 0 or row >= len(self._summaries):
            return
        self._selected_path = self._summaries[row].path
        self._show_replay_overlay(self._selected_path.stem)
        self.refreshMacros()

    @Slot()
    def showRecordOverlay(self) -> None:
        self._countdown_timer.stop()
        self._replay_overlay_visible = False
        self._record_overlay_visible = True
        self._record_overlay_title = self._t("timetask.overlay_ready")
        self._record_overlay_detail = self._t("timetask.overlay_record_options")
        self._record_overlay_hint = self._t("timetask.overlay_focus_hint")
        self._record_overlay_accent = "#5eead4"
        self.changed.emit()

    @Slot()
    def hideRecordOverlay(self) -> None:
        if self.recording:
            return
        self._record_overlay_visible = False
        self.changed.emit()

    @Slot()
    def hideReplayOverlay(self) -> None:
        if self.replaying:
            return
        self._replay_overlay_visible = False
        self.changed.emit()

    @Slot()
    def startRecording(self) -> None:
        if not self._recorder:
            self._status = "TimeTask unavailable"
            self.changed.emit()
            return
        if self._recorder.start_recording():
            self._record_overlay_visible = True
            self._record_overlay_title = self._t("timetask.overlay_recording")
            self._record_overlay_detail = self._t("timetask.overlay_armed")
            self._record_overlay_hint = self._t("timetask.overlay_focus_hint")
            self._record_overlay_accent = "#ffd166"
        else:
            self._status = "Could not start recording"
        self._sync_poll_timer()
        self.changed.emit()

    @Slot()
    def beginCountdownRecording(self) -> None:
        if not self._recorder:
            self._status = "TimeTask unavailable"
            self.changed.emit()
            return
        if self._recorder.recording:
            self._recorder.resume_recording()
            return
        self._replay_overlay_visible = False
        self._record_overlay_visible = True
        self._countdown_value = 3
        self._run_countdown_tick()

    def _run_countdown_tick(self) -> None:
        if self._countdown_value <= 0:
            self._countdown_timer.stop()
            self.startRecording()
            return
        self._record_overlay_title = self._t("timetask.overlay_countdown_title")
        self._record_overlay_detail = str(self._countdown_value)
        self._record_overlay_hint = self._t("timetask.overlay_countdown_hint")
        self._record_overlay_accent = "#ffd166"
        self._record_overlay_visible = True
        self._countdown_value -= 1
        self._countdown_timer.start()
        self.changed.emit()

    @Slot()
    def stopRecording(self) -> None:
        if not self._recorder:
            self._status = "No active recording"
        else:
            self._countdown_timer.stop()
            events = self._recorder.stop_recording()
            self._status = self._t("timetask.overlay_events", events=len(events))
            self._record_overlay_visible = False
            self._show_replay_overlay()
        self.refreshMacros()
        self._sync_poll_timer()
        self.changed.emit()

    @Slot()
    def saveCurrent(self) -> None:
        if not self._recorder:
            self._status = "TimeTask unavailable"
            self.changed.emit()
            return
        self._countdown_timer.stop()
        if self._recorder.recording:
            self._recorder.stop_recording()
        events = self._recorder.snapshot_events()
        if not events:
            self._status = self._t("timetask.no_events")
            self.changed.emit()
            return
        path = self._recorder.save_macro(self._macro_name)
        self._status = self._t("timetask.saved", path=str(path))
        self._selected_path = path
        self._record_overlay_visible = False
        self.refreshMacros()
        self._show_replay_overlay(path.stem)
        self.changed.emit()

    @Slot()
    def pauseResume(self) -> None:
        if not self._recorder:
            return
        if self._recorder.recording:
            if self._recorder.paused:
                self._recorder.resume_recording()
            else:
                self._recorder.pause_recording()
        elif self._recorder.replaying:
            if self._recorder.replay_paused:
                self._recorder.resume_replay()
            else:
                self._recorder.pause_replay()
        self.changed.emit()

    @Slot()
    def playSelected(self) -> None:
        if not self._recorder:
            self._status = "TimeTask unavailable"
            self.changed.emit()
            return
        if not self._selected_path:
            self.refreshMacros()
            if self._summaries:
                self._selected_path = self._summaries[0].path
            else:
                self._status = self._t("timetask.pick_macro")
                self._show_replay_overlay(self._status)
                return
        speed = self._parse_float(self._speed, 1.0)
        repeat = self._parse_int(self._repeat, 1)
        delay = self._delay_seconds(self._delay)
        stock_path = self._stock_macro_path()
        stock_interval = self._parse_int(self._stock_interval, 1)
        self._record_overlay_visible = False
        self._show_replay_overlay(self._selected_path.stem, visible=True)
        started = self._recorder.replay_macro(
            self._selected_path,
            speed=speed,
            repeat=repeat,
            delay_between=delay,
            stock_path=stock_path,
            stock_interval=stock_interval,
        )
        if started:
            self._status = self._t("timetask.overlay_playing")
        else:
            self._status = self._t("timetask.replay_need_foxhole")
            self._show_replay_overlay(self._status)
        self._sync_poll_timer()
        self.changed.emit()

    @Slot()
    def stopReplay(self) -> None:
        if self._recorder:
            self._recorder.stop_replay()
        self._replay_overlay_visible = False
        self._status = self._t("timetask.stopped")
        self._sync_poll_timer()
        self.changed.emit()

    @Slot()
    def deleteSelectedMacro(self) -> None:
        if not self._selected_path:
            self._status = self._t("timetask.pick_macro")
            self.changed.emit()
            return
        parent = QApplication.activeWindow()
        answer = QMessageBox.question(parent, self._t("timetask.delete"), self._t("timetask.delete_confirm", name=self._selected_path.stem))
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._selected_path.unlink()
        except OSError as exc:
            self._status = str(exc)
        else:
            self._status = self._t("timetask.deleted")
            self._selected_path = None
            self._replay_overlay_visible = False
        self.refreshMacros()
        self.changed.emit()

    @Slot(int, int)
    def setRecordOverlayPosition(self, x: int, y: int) -> None:
        self._record_overlay_x = max(0, int(x))
        self._record_overlay_y = max(0, int(y))
        self._settings.setdefault("time_task", {})["overlay_record_x"] = self._record_overlay_x
        self._settings.setdefault("time_task", {})["overlay_record_y"] = self._record_overlay_y
        save_settings(self._settings)
        self.changed.emit()

    @Slot(int, int)
    def setReplayOverlayPosition(self, x: int, y: int) -> None:
        self._replay_overlay_x = max(0, int(x))
        self._replay_overlay_y = max(0, int(y))
        self._settings.setdefault("time_task", {})["overlay_replay_x"] = self._replay_overlay_x
        self._settings.setdefault("time_task", {})["overlay_replay_y"] = self._replay_overlay_y
        save_settings(self._settings)
        self.changed.emit()

    @Slot()
    def refreshMacros(self) -> None:
        if not self._recorder:
            self._summaries = []
        else:
            try:
                self._summaries = self._recorder.list_macros()
            except Exception as exc:
                self._status = f"Macro list unavailable: {exc}"
                self._summaries = []
        if self._selected_path is None and self._summaries:
            self._selected_path = self._summaries[0].path
        if self._selected_path and not any(summary.path == self._selected_path for summary in self._summaries):
            self._selected_path = self._summaries[0].path if self._summaries else None
        if self._stock_macro_name not in self.stockMacroOptions:
            self._stock_macro_name = self._t("timetask.none")
        self._macros.set_items(
            [
                {
                    "name": summary.name,
                    "duration": f"{summary.duration:.1f}s",
                    "events": summary.events,
                    "createdAt": summary.created_at,
                    "path": str(summary.path),
                    "selected": self._selected_path == summary.path,
                }
                for summary in self._summaries
            ]
        )
        self.changed.emit()

    def _set_status_from_worker(self, message: str) -> None:
        self._status = message
        if any(token in message.lower() for token in ("finalizada", "cancelada", "parada", "finished", "cancelled", "stopped")):
            self.refreshMacros()
            if not self.replaying:
                self._show_replay_overlay()
        self._sync_poll_timer()
        self.changed.emit()

    def _poll_state(self) -> None:
        if not self._recorder:
            self._sync_poll_timer()
            return
        if not (self._recorder.recording or self._recorder.replaying):
            self._sync_poll_timer()
            return
        events = self._recorder.snapshot_events()
        duration = events[-1]["t"] if events else 0.0
        self._metric = self._t("timetask.metric", events=len(events), duration=f"{duration:.1f}s")
        if self._recorder.recording:
            self._record_overlay_visible = True
            self._record_overlay_title = self._t("timetask.overlay_recording")
            self._record_overlay_detail = (
                self._t("timetask.overlay_paused")
                if self._recorder.paused
                else self._t("timetask.overlay_events_live", events=len(events), live=self._recorder.live_status())
            )
            self._record_overlay_hint = self._t("timetask.overlay_focus_hint")
            self._record_overlay_accent = "#ffd166"
        if self._recorder.replaying:
            self._replay_overlay_visible = True
            self._replay_overlay_title = self._t("timetask.overlay_playing")
            self._replay_overlay_detail = (
                self._t("timetask.overlay_paused")
                if self._recorder.replay_paused
                else self._t("timetask.overlay_replay_live", live=self._recorder.replay_status())
            )
            self._replay_overlay_accent = "#62d7a4"
        self.changed.emit()

    def _sync_poll_timer(self) -> None:
        active = bool(self._recorder and (self._recorder.recording or self._recorder.replaying))
        if active and not self._poll_timer.isActive():
            self._poll_timer.start()
        elif not active and self._poll_timer.isActive():
            self._poll_timer.stop()

    def _show_replay_overlay(self, detail: str | None = None, *, visible: bool = True) -> None:
        if detail is None:
            if self._selected_path:
                detail = self._selected_path.stem
            elif self._summaries:
                detail = self._summaries[0].name
            else:
                detail = self._t("timetask.replay_empty")
        self._replay_overlay_title = self._t("timetask.replay_overlay_title")
        self._replay_overlay_detail = detail
        self._replay_overlay_accent = "#62d7a4"
        self._replay_overlay_visible = visible
        self.changed.emit()

    @staticmethod
    def _parse_float(value: str, fallback: float) -> float:
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _parse_int(value: str, fallback: int) -> int:
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return fallback

    def _delay_seconds(self, value: str) -> float:
        text = str(value or "0s").strip().lower()
        try:
            if "min" in text:
                return float(text.replace("min", "").replace("s", "").strip()) * 60
            return float(text.replace("s", "").strip() or 0)
        except ValueError:
            return 0.0

    def _stock_macro_path(self) -> Path | None:
        none_label = self._t("timetask.none")
        if self._stock_macro_name == none_label:
            return None
        for summary in self._summaries:
            if summary.name == self._stock_macro_name:
                return summary.path
        return None

    @Slot()
    def shutdown(self) -> None:
        self._countdown_timer.stop()
        self._poll_timer.stop()
        if self._recorder:
            self._recorder.stop()


class NotificationsController(QObject):
    changed = Signal()

    def __init__(self, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._remaining_seconds = SQUADLOCK_SECONDS
        self._running = False
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
        self._focus_timer.setInterval(500)
        self._focus_timer.timeout.connect(self._refresh_overlay_visibility)
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

    @Slot()
    def startSquadlock(self) -> None:
        self._remaining_seconds = SQUADLOCK_SECONDS
        self._running = True
        self._finished = False
        self._tick_timer.start()
        self._refresh_overlay_visibility()
        self._sync_focus_timer()
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


    @Property("QVariantMap", notify=changed)
    def userProfile(self) -> dict:
        return getattr(self, "_profile", {})

    @Slot()
    def logout(self) -> None:
        self._token = ""
        self._discord_user_settings.clear()
        save_settings(self.settings)
        self._ws.close()
        self._discord_login_required = True
        self._current_user_id = ""
        self._profile = {}
        self._status = "Disconnected"
        self.changed.emit()



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
        return not bool(getattr(sys, "frozen", False))

    @Slot()
    def check(self) -> None:
        if self._checking or self._installing:
            return
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
        if self.sourceMode:
            self._error_text = self._t("update.source_mode_unavailable")
            self._error_visible = True
            self._status = self._error_text
            self.changed.emit()
            return

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
            self._status = self._t("update.check_failed", message=error)
            self._error_text = self._status
            self._error_visible = True
            self.changed.emit()
            return
        self._update = update if isinstance(update, UpdateInfo) else None
        if self._update:
            self._status = self._t("update.available_status", version=self._update.version)
            self._offer_visible = True
        else:
            self._status = self._t("update.no_update")
            self._offer_visible = False
        self.changed.emit()

    @Slot(int, str)
    def _handle_progress(self, value: int, text: str) -> None:
        self._progress_value = max(0, min(100, int(value)))
        self._progress_text = text
        self._status = text
        self.changed.emit()

    @Slot(str)
    def _handle_install_failed(self, message: str) -> None:
        self._installing = False
        self._progress_visible = False
        self._error_text = message
        self._error_visible = True
        self._status = message
        self.changed.emit()


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
        self._last_find_attempt = 0.0
        self.auto_clicker.changed.connect(self._refresh_visibility)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(250)
        self._refresh_visibility()

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
        # Also show overlay when pilot (w_hold) is active
        clicker = self.auto_clicker.clicker
        if clicker and getattr(clicker, "w_hold_enabled", False):
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


def process_running(process_name: str) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=2,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return process_name.lower() in result.stdout.lower()
    except Exception:
        return False


def normalize_item_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        icon = row.get("icon") or row.get("icon_path") or row.get("texture") or ""
        normalized.append(
            {
                "name": str(row.get("name") or row.get("item") or "-"),
                "quantity": int(row.get("quantity") or row.get("count") or 0),
                "category": str(row.get("category") or row.get("type") or ""),
                "icon": file_url(icon) if icon and Path(str(icon)).exists() else "",
            }
        )
    return normalized


def normalize_warehouses(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        normalized.append(
            {
                "name": str(row.get("name") or row.get("stockpile") or "-"),
                "region": str(row.get("region") or row.get("map") or ""),
                "count": int(row.get("count") or row.get("item_count") or 0),
                "updatedAt": str(row.get("updatedAt") or row.get("last_update") or ""),
            }
        )
    return normalized


def identify_preview_path() -> Path:
    path = extracted_dir() / "identify-preview.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def match_to_dict(match) -> dict[str, Any]:
    return {
        "name": str(match.name),
        "score": float(match.score),
        "scoreText": f"{float(match.score):.3f}",
        "icon": file_url(match.path) if match.path and Path(match.path).exists() else "",
        "path": str(match.path),
    }


def load_item_index() -> list[dict[str, str]]:
    roots = [
        BASE_DIR / "Content" / "Textures" / "UI" / "ItemIcons",
        BASE_DIR / "Content" / "Textures" / "UI" / "VehicleIcons",
        BASE_DIR / "img" / "calculator",
    ]
    items: list[dict[str, str]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                continue
            name = path.stem.replace("ItemIcon", "").replace("Icon", "")
            category = root.name
            items.append({"name": name, "path": str(path), "category": category, "icon": file_url(path)})
    items.sort(key=lambda item: item["name"].lower())
    return items


def message_identity(message: dict[str, Any], index: int) -> str:
    return str(message.get("id") or message.get("_id") or message.get("messageId") or f"row-{index}")


def parse_message_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if number > 10_000_000_000:
            number /= 1000.0
        try:
            return datetime.fromtimestamp(number, tz=timezone.utc).astimezone()
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return parse_message_datetime(int(text))
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone()


def format_chat_time(value: Any) -> str:
    parsed = parse_message_datetime(value)
    if parsed is None:
        return str(value or "")
    now = datetime.now().astimezone()
    if parsed.date() == now.date():
        return f"Hoje {parsed:%H:%M}"
    if (now.date() - parsed.date()).days == 1:
        return f"Ontem {parsed:%H:%M}"
    if parsed.year == now.year:
        return parsed.strftime("%d/%m %H:%M")
    return parsed.strftime("%d/%m/%Y %H:%M")


def message_sort_value(value: Any, index: int) -> float:
    parsed = parse_message_datetime(value)
    if parsed is None:
        return float(index)
    return parsed.timestamp()


def message_user(message: dict[str, Any]) -> dict[str, Any]:
    for key in ("user", "author", "sender", "fromUser", "createdBy"):
        value = message.get(key)
        if isinstance(value, dict):
            return value
    return {}


def user_display_name(user: dict[str, Any]) -> str:
    return str(
        user.get("displayName")
        or user.get("globalName")
        or user.get("name")
        or user.get("personaName")
        or user.get("personaname")
        or user.get("nickname")
        or user.get("username")
        or "User"
    )


def user_avatar_url(user: dict[str, Any]) -> str:
    return str(user.get("avatarUrl") or user.get("avatarfull") or user.get("avatarmedium") or user.get("avatar") or "")


def first_media_url(content: str) -> str:
    match = IMAGE_URL_RE.search(content or "")
    return match.group(0).rstrip(").,;]") if match else ""


def normalize_messages(
    messages: list[dict[str, Any]],
    current_name: str = "",
    current_steam_id: str = "",
    current_discord_id: str = "",
) -> list[dict[str, Any]]:
    result = []
    local_name = str(current_name or "").strip().casefold()
    local_steam = str(current_steam_id or "").strip()
    local_discord = str(current_discord_id or "").strip()
    for index, message in enumerate(messages):
        author = message_user(message)
        author_name = user_display_name(author) if author else str(message.get("authorName") or message.get("username") or "User")
        avatar = user_avatar_url(author)
        author_steam = str(author.get("steamId") or author.get("steam_id") or "")
        author_discord = str(author.get("discordId") or author.get("discord_id") or "")
        created = message.get("createdAt") or message.get("created_at") or message.get("timestamp") or message.get("sentAt") or ""
        body = str(message.get("content") or message.get("body") or message.get("text") or message.get("message") or "")
        media_url = first_media_url(body)
        is_mine = bool(message.get("mine") or False)
        if not is_mine:
            remote_name = author_name.strip().casefold()
            is_mine = bool(
                (local_discord and author_discord == local_discord)
                or (local_steam and author_steam == local_steam)
                or (local_name and remote_name == local_name)
            )
        mentioned = bool(local_name and f"@{local_name}" in body.casefold())
        for mention in message.get("mentions") or []:
            mentioned_user = mention.get("mentionedUser") or mention.get("user") or mention if isinstance(mention, dict) else {}
            if not isinstance(mentioned_user, dict):
                continue
            mention_steam = str(mentioned_user.get("steamId") or mentioned_user.get("steam_id") or "")
            mention_discord = str(mentioned_user.get("discordId") or mentioned_user.get("discord_id") or "")
            mention_name = user_display_name(mentioned_user).strip().casefold()
            if (
                (local_discord and mention_discord == local_discord)
                or (local_steam and mention_steam == local_steam)
                or (local_name and mention_name == local_name)
            ):
                mentioned = True
                break
        result.append(
            {
                "id": message_identity(message, index),
                "author": author_name,
                "body": body,
                "meta": format_chat_time(created),
                "rawTime": str(created or ""),
                "sortKey": message_sort_value(created, index),
                "mine": is_mine,
                "avatar": avatar,
                "mediaUrl": media_url,
                "isGif": media_url.lower().split("?", 1)[0].endswith(".gif"),
                "mentioned": mentioned,
                "reactions": message.get("reactions") or [],
                "replyToMessageId": str(message.get("replyToMessageId") or ""),
                "replyToAuthor": str((message.get("replyToMessage") or {}).get("authorName") or ""),
                "replyToBody": str((message.get("replyToMessage") or {}).get("content") or ""),
                "authorDiscordId": author_discord,
            }
        )
    return sorted(
        result,
        key=lambda row: (
            float(row.get("sortKey") or 0.0),
            str(row.get("id") or ""),
        ),
    )


def merge_message_rows(incoming: list[dict[str, Any]], current: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_by_id: dict[str, dict[str, Any]] = {}
    for row in [*incoming, *current]:
        identity = str(row.get("id") or "")
        if not identity:
            continue
        if identity not in merged_by_id:
            merged_by_id[identity] = row
            continue
        previous = merged_by_id[identity]
        if not previous.get("rawTime") and row.get("rawTime"):
            merged_by_id[identity] = row
    return sorted(
        merged_by_id.values(),
        key=lambda row: (
            float(row.get("sortKey") or 0.0),
            str(row.get("id") or ""),
        ),
    )


def same_message_rows(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> bool:
    if len(left) != len(right):
        return False
    keys = ("id", "body", "meta", "rawTime", "author", "mine", "mentioned", "mediaUrl")
    for left_row, right_row in zip(left, right):
        for key in keys:
            if left_row.get(key) != right_row.get(key):
                return False
    return True


def http_json(
    method: str,
    path: str,
    *,
    token: str | None = None,
    payload: Any | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json", "User-Agent": "GG Coalition/1.0"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{CHAT_API_BASE.rstrip('/')}/{path.lstrip('/')}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {body or 'empty response'}") from exc


def http_json_url(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: Any | None = None,
    form: dict[str, str] | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json", "User-Agent": "GG Coalition/1.0"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {body or 'empty response'}") from exc


def discord_avatar_url(user: dict[str, Any]) -> str:
    user_id = str(user.get("id") or "")
    avatar = str(user.get("avatar") or "")
    if not user_id or not avatar:
        return ""
    ext = "gif" if avatar.startswith("a_") else "png"
    return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.{ext}?size=256"


def discord_redirect_uri(port: int = DISCORD_DEFAULT_REDIRECT_PORT) -> str:
    return f"http://127.0.0.1:{port}{DISCORD_DEFAULT_REDIRECT_PATH}"


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def gg_logo_data_uri() -> str:
    logo_path = BASE_DIR / "img" / "ggimege.gif"
    try:
        data = logo_path.read_bytes()
    except OSError:
        return ""
    return "data:image/gif;base64," + base64.b64encode(data).decode("ascii")


def discord_oauth_callback_html(*, success: bool, language: str) -> bytes:
    copy = {
        "pt": {
            "ok_title": "Login recebido",
            "ok_body": "Voce ja pode voltar para o GG Coalition.",
            "cancel_title": "Login cancelado",
            "cancel_body": "A autorizacao do Discord foi cancelada. Volte ao aplicativo para tentar de novo.",
            "small": "Esta aba pode ser fechada.",
        },
        "en": {
            "ok_title": "Login received",
            "ok_body": "You can return to GG Coalition.",
            "cancel_title": "Login cancelled",
            "cancel_body": "Discord authorization was cancelled. Return to the app to try again.",
            "small": "This tab can be closed.",
        },
        "es": {
            "ok_title": "Login recibido",
            "ok_body": "Ya puedes volver a GG Coalition.",
            "cancel_title": "Login cancelado",
            "cancel_body": "La autorizacion de Discord fue cancelada. Vuelve a la aplicacion para intentarlo otra vez.",
            "small": "Esta pestana se puede cerrar.",
        },
        "fr": {
            "ok_title": "Login recu",
            "ok_body": "Vous pouvez retourner dans GG Coalition.",
            "cancel_title": "Login annule",
            "cancel_body": "L'autorisation Discord a ete annulee. Retournez dans l'application pour reessayer.",
            "small": "Cet onglet peut etre ferme.",
        },
    }.get(normalize_language(language), {})
    title = copy["ok_title"] if success else copy["cancel_title"]
    body_text = copy["ok_body"] if success else copy["cancel_body"]
    mark = "✓" if success else "!"
    color = "#5eead4" if success else "#ffd166"
    logo_uri = gg_logo_data_uri()
    logo_html = (
        f'<img class="logo-img" src="{html.escape(logo_uri)}" alt="GG Coalition">'
        if logo_uri
        else f'<div class="mark">{html.escape(mark)}</div>'
    )
    return f"""
<!doctype html>
<html lang="{html.escape(normalize_language(language))}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GG Coalition</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: "Segoe UI", Arial, sans-serif;
      color: #edf6ff;
      background:
        radial-gradient(circle at 50% 30%, rgba(94,234,212,.12), transparent 28rem),
        linear-gradient(145deg, #070b16, #0d1729 58%, #08111f);
    }}
    .card {{
      width: min(420px, calc(100vw - 32px));
      padding: 34px 30px;
      border: 1px solid #24486d;
      border-radius: 10px;
      background: rgba(17,28,49,.88);
      box-shadow: 0 24px 70px rgba(0,0,0,.34);
      text-align: center;
      animation: in .28s ease-out both;
    }}
    .logo {{
      width: 78px;
      height: 78px;
      margin: 0 auto 18px;
      border-radius: 12px;
      display: grid;
      place-items: center;
      background: #0e1a2d;
      border: 1px solid #2d496f;
      overflow: hidden;
      position: relative;
    }}
    .logo::after {{
      content: "{html.escape(mark)}";
      position: absolute;
      right: -4px;
      bottom: -4px;
      width: 30px;
      height: 30px;
      display: grid;
      place-items: center;
      border-radius: 10px;
      color: #06111c;
      background: {color};
      font-size: 18px;
      font-weight: 900;
      border: 3px solid #0e1a2d;
    }}
    .logo-img {{
      width: 70px;
      height: 70px;
      object-fit: contain;
    }}
    .mark {{
      width: 58px;
      height: 58px;
      margin: 0 auto 18px;
      border-radius: 12px;
      display: grid;
      place-items: center;
      background: #0e1a2d;
      border: 1px solid #2d496f;
      color: {color};
      font-size: 28px;
      font-weight: 800;
    }}
    h1 {{ margin: 0; font-size: 24px; line-height: 1.2; }}
    p {{ margin: 10px 0 0; color: #c7d7ed; font-size: 14px; line-height: 1.5; }}
    .small {{ color: #7f93ad; font-size: 12px; margin-top: 18px; }}
    @keyframes in {{
      from {{ opacity: 0; transform: translateY(8px) scale(.98); }}
      to {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
  </style>
  <script>setTimeout(function () {{ window.close(); }}, 1200);</script>
</head>
<body>
  <main class="card">
    <div class="logo">{logo_html}</div>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(body_text)}</p>
    <p class="small">{html.escape(copy["small"])}</p>
  </main>
</body>
</html>
    """.encode("utf-8")


def wait_for_discord_oauth_code(expected_state: str, port: int, timeout: int = 180, auth_url: str = "", language: str = "pt") -> str:
    result: dict[str, str] = {}
    finished = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if parsed.path != DISCORD_DEFAULT_REDIRECT_PATH:
                self.send_response(404)
                self.end_headers()
                return
            state = (params.get("state") or [""])[0]
            if state != expected_state:
                result["error"] = "invalid_oauth_state"
            elif params.get("error"):
                result["error"] = (params.get("error_description") or params.get("error") or ["oauth_cancelled"])[0]
            else:
                result["code"] = (params.get("code") or [""])[0]
            body = discord_oauth_callback_html(success=bool(result.get("code")) and not result.get("error"), language=language)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            finished.set()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 0.5
    try:
        if auth_url and not QDesktopServices.openUrl(QUrl(auth_url)):
            raise RuntimeError("discord_browser_error")
        while not finished.wait(0):
            server.handle_request()
            if timeout <= 0:
                break
            timeout -= 0.5
    finally:
        server.server_close()
    if result.get("error"):
        raise RuntimeError(result["error"])
    code = result.get("code", "")
    if not code:
        raise RuntimeError("discord_oauth_timeout")
    return code


class ControllerRegistry(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.settings_data = load_settings()
        self.i18nController = I18nController(self.settings_data, self)
        self.appController = AppController(self.i18nController, self.settings_data, self)
        self.settingsController = SettingsController(self.settings_data, self)
        self.steamController = SteamController(self)
        self.trayController = TrayController(app, self.i18nController, self)
        self.autoClickerController = AutoClickerController(self.settings_data, self)
        self.overlayController = OverlayController(self.settings_data, self.autoClickerController, self)
        self.stockpileController = StockpileController(self.settings_data, self)
        self.chatController = ChatController(self.steamController, self.settings_data, self.i18nController, self)
        self.itemSearchController = ItemSearchController(self.settings_data, self)
        self.identifyItemController = IdentifyItemController(self.itemSearchController, self)
        self.productionController = ProductionController(self)
        self.timeTaskController = TimeTaskController(self.i18nController, self)
        self.notificationsController = NotificationsController(self.settings_data, self)
        self.updateController = UpdateController(self.i18nController, self)
        self.i18nController.changed.connect(self.settingsController.notifyExternalChange)
        self.settingsController.changed.connect(self.notificationsController.refresh)
        self.autoClickerController.orderRequested.connect(lambda _order: self.notificationsController.startSquadlock())
        if self.settings_data.get("stockpile", {}).get("enabled", True):
            QTimer.singleShot(0, self.stockpileController.start)

    def expose(self, engine) -> None:
        context = engine.rootContext()
        for name in (
            "appController",
            "i18nController",
            "settingsController",
            "steamController",
            "trayController",
            "autoClickerController",
            "overlayController",
            "stockpileController",
            "chatController",
            "itemSearchController",
            "identifyItemController",
            "productionController",
            "timeTaskController",
            "notificationsController",
            "updateController",
        ):
            context.setContextProperty(name, getattr(self, name))
        context.setContextProperty("navItems", self.appController.navItems)
        context.setContextProperty("languagesModel", self.i18nController.languages)

    @Slot()
    def shutdown(self) -> None:
        self.autoClickerController.shutdown()
        self.stockpileController.shutdown()
        self.chatController.shutdown()
        self.identifyItemController.shutdown()
        self.timeTaskController.shutdown()
        self.notificationsController.shutdown()
