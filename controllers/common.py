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


UPDATE_REPO = "ryan1235/aplicativo"
FOXHOLE_APP_ID = "505460"
FOXHOLE_PROCESS_NAMES = ("war-win64-shipping.exe", "foxhole.exe")
FOXHOLE_PATH_HINTS = ("\\steamapps\\common\\foxhole\\", "/steamapps/common/foxhole/")
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SQUADLOCK_SECONDS = 30 * 60
BASE_DIR = Path(__file__).resolve().parent.parent
CHAT_API_BASE = "https://archpixel.squareweb.app"
CHAT_WS_BASE = "wss://archpixel.squareweb.app"
CHAT_DISCORD_OAUTH_AUTH_PATH = "/chat/auth/discord/oauth"
CHAT_AUTO_LOGIN_AUTH_PATH = "/chat/auth/auto-login"
GG_LOGS_PATH = "/gg-logs"
CHAT_USERS_PATHS = ("/chat/users", "/chat/users/online")
CHAT_ONLINE_PATHS = ("/chat/presence/online", "/chat/users/online")
DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
FOXHOLE_WIKI_BASE_URL = "https://foxhole.wiki.gg"
FOXHOLE_WIKI_API_URL = f"{FOXHOLE_WIKI_BASE_URL}/api.php"
DISCORD_DEFAULT_REDIRECT_PORT = 53624
DISCORD_DEFAULT_REDIRECT_PATH = "/discord/callback"
DISCORD_DEFAULT_CLIENT_ID = "1512509453067358489"

ACTIVITY_LOG_CATEGORIES: dict[str, tuple[str, ...]] = {
    "auth": ("login", "sessao"),
    "chat": ("mensagens", "reacoes", "salas"),
    "autoclique": ("auto", "move", "pilot", "right_hold", "fixed", "artillery", "ordens", "configuracao"),
    "estoque": ("monitor", "api", "visual", "configuracao"),
    "producao": ("calculadora", "fila", "rota"),
    "macros": ("gravacao", "replay", "arquivos"),
    "notificacoes": ("squadlock", "overlay", "preferencias"),
    "configuracoes": ("app", "personalizacao", "idioma", "notificacoes"),
    "navegacao": ("paginas", "sidebar", "painel"),
}

ActivityLogger = Callable[[str, str, int, dict[str, Any] | None, str], None]

IMAGE_URL_RE = re.compile(r"https?://[^\s<>\"]+\.(?:png|jpe?g|webp|gif)(?:\?[^\s<>\"]*)?", re.IGNORECASE)
MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_.-]{1,32})")
QUICK_EMOJIS = ("👍", "❤️", "😂", "🔥", "✅", "🫡", "👀", "🚚", "⚠️", "🎯")
SOUND_DIRS = (BASE_DIR / "efeitos sonoros", BASE_DIR / "audio")
SOUND_EXTENSIONS = (".wav", ".mp3", ".wma")
VALID_CLOSE_ACTIONS = ("ask", "tray", "exit")
UI_THEME_CUSTOM_DEFAULT = DEFAULT_THEME_CUSTOM
UI_THEME_COLOR_KEYS = (
    "accent",
    "accent_hover",
    "accent_panel",
    "success",
    "warning",
    "warning_text",
    "background",
    "surface",
    "text",
    "text_inverse",
    "secondary_text",
    "muted_text",
    "disabled_text",
    "border",
    "surface_alt",
    "surface_raised",
    "control",
    "control_hover",
    "danger",
    "danger_hover",
    "danger_panel",
    "info",
    "scrim",
    "gradient_start",
    "gradient_end",
)
UI_THEME_PRESETS = {
    "coalition": {
        "labelKey": "settings.theme_coalition",
        "descriptionKey": "settings.theme_coalition_detail",
        "accent": "#5eead4",
        "accent_hover": "#34d399",
        "accent_panel": "#123b34",
        "success": "#62d7a4",
        "warning": "#f59e0b",
        "warning_text": "#ffedd5",
        "background": "#070b16",
        "surface": "#111c31",
        "text": "#edf6ff",
        "muted_text": "#9fb3c8",
        "border": "#2b4b68",
        "gradient_start": "#070b16",
        "gradient_end": "#12243a",
        "gradient_enabled": False,
        "button_style": "solid",
        "card_radius": 8,
    },
    "warden": {
        "labelKey": "settings.theme_warden",
        "descriptionKey": "settings.theme_warden_detail",
        "accent": "#93c5fd",
        "accent_hover": "#facc15",
        "accent_panel": "#172554",
        "success": "#7dd3fc",
        "warning": "#facc15",
        "warning_text": "#422006",
        "background": "#07111d",
        "surface": "#101827",
        "text": "#edf6ff",
        "muted_text": "#b6c7d9",
        "border": "#2e4b68",
        "gradient_start": "#07111d",
        "gradient_end": "#1b2a3e",
        "gradient_enabled": True,
        "button_style": "soft",
        "card_radius": 8,
    },
    "ember": {
        "labelKey": "settings.theme_ember",
        "descriptionKey": "settings.theme_ember_detail",
        "accent": "#fb7185",
        "accent_hover": "#f97316",
        "accent_panel": "#3a1827",
        "success": "#34d399",
        "warning": "#f59e0b",
        "warning_text": "#ffedd5",
        "background": "#170b12",
        "surface": "#26151f",
        "text": "#fff1f2",
        "muted_text": "#e7b5c2",
        "border": "#713247",
        "gradient_start": "#170b12",
        "gradient_end": "#3a1827",
        "gradient_enabled": True,
        "button_style": "glass",
        "card_radius": 10,
    },
    "light": {
        "labelKey": "settings.theme_light",
        "descriptionKey": "settings.theme_light_detail",
        "accent": "#2563eb",
        "accent_hover": "#1d4ed8",
        "accent_panel": "#dbeafe",
        "success": "#059669",
        "warning": "#d97706",
        "warning_text": "#7c2d12",
        "background": "#eef4fb",
        "surface": "#ffffff",
        "text": "#0f172a",
        "muted_text": "#475569",
        "border": "#b9c8dc",
        "gradient_start": "#f8fbff",
        "gradient_end": "#dceafe",
        "gradient_enabled": True,
        "button_style": "solid",
        "card_radius": 8,
    },
    "midnight": {
        "labelKey": "settings.theme_midnight",
        "descriptionKey": "settings.theme_midnight_detail",
        "accent": "#38bdf8",
        "accent_hover": "#22d3ee",
        "accent_panel": "#0f2d3f",
        "success": "#22c55e",
        "warning": "#eab308",
        "warning_text": "#fef9c3",
        "background": "#020617",
        "surface": "#0b1224",
        "text": "#f8fafc",
        "muted_text": "#94a3b8",
        "border": "#1e3a5f",
        "gradient_start": "#020617",
        "gradient_end": "#111827",
        "gradient_enabled": True,
        "button_style": "outline",
        "card_radius": 6,
    },
    "verdant": {
        "labelKey": "settings.theme_verdant",
        "descriptionKey": "settings.theme_verdant_detail",
        "accent": "#84cc16",
        "accent_hover": "#bef264",
        "accent_panel": "#1f3515",
        "success": "#22c55e",
        "warning": "#fbbf24",
        "warning_text": "#422006",
        "background": "#07120b",
        "surface": "#101d15",
        "text": "#f2ffe8",
        "muted_text": "#b4c9aa",
        "border": "#355430",
        "gradient_start": "#07120b",
        "gradient_end": "#172812",
        "gradient_enabled": True,
        "button_style": "soft",
        "card_radius": 8,
    },
    "signal": {
        "labelKey": "settings.theme_signal",
        "descriptionKey": "settings.theme_signal_detail",
        "accent": "#f97316",
        "accent_hover": "#38bdf8",
        "accent_panel": "#3b2212",
        "success": "#10b981",
        "warning": "#facc15",
        "warning_text": "#422006",
        "background": "#11100b",
        "surface": "#1d1a14",
        "text": "#fff7ed",
        "muted_text": "#d7c6a8",
        "border": "#60412b",
        "gradient_start": "#11100b",
        "gradient_end": "#2a1a12",
        "gradient_enabled": True,
        "button_style": "solid",
        "card_radius": 6,
    },
    "aurora": {
        "labelKey": "settings.theme_aurora",
        "descriptionKey": "settings.theme_aurora_detail",
        "accent": "#a78bfa",
        "accent_hover": "#5eead4",
        "accent_panel": "#281f45",
        "success": "#5eead4",
        "warning": "#f0abfc",
        "warning_text": "#fae8ff",
        "background": "#0f1020",
        "surface": "#181827",
        "text": "#f8f7ff",
        "muted_text": "#c8bddc",
        "border": "#4b3d71",
        "gradient_start": "#0f1020",
        "gradient_end": "#17233b",
        "gradient_enabled": True,
        "button_style": "glass",
        "card_radius": 12,
    },
    "accessible": {
        "labelKey": "settings.theme_accessible",
        "descriptionKey": "settings.theme_accessible_detail",
        "accent": "#8ab4ff",
        "accent_hover": "#f0abfc",
        "accent_panel": "#13243d",
        "success": "#8ab4ff",
        "warning": "#f0abfc",
        "warning_text": "#fce7f3",
        "background": "#050b16",
        "surface": "#101b2f",
        "text": "#f8fafc",
        "muted_text": "#bfdbfe",
        "border": "#3b82f6",
        "gradient_start": "#050b16",
        "gradient_end": "#1b2240",
        "gradient_enabled": False,
        "button_style": "outline",
        "card_radius": 8,
    },
    "custom": {
        "labelKey": "settings.theme_custom",
        "descriptionKey": "settings.theme_custom_detail",
        **UI_THEME_CUSTOM_DEFAULT,
    },
}
UI_THEME_ORDER = ("coalition", "warden", "ember", "verdant", "signal", "aurora", "light", "midnight", "accessible", "custom")
UI_THEME_COLOR_FIELDS = {
    "accent": "settings.theme_color_accent",
    "accent_panel": "settings.theme_color_panel",
    "background": "settings.theme_color_background",
    "surface": "settings.theme_color_surface",
    "text": "settings.theme_color_text",
    "text_inverse": "settings.theme_color_text_inverse",
    "secondary_text": "settings.theme_color_secondary_text",
    "muted_text": "settings.theme_color_muted_text",
    "disabled_text": "settings.theme_color_disabled_text",
    "border": "settings.theme_color_border",
    "surface_alt": "settings.theme_color_surface_alt",
    "surface_raised": "settings.theme_color_surface_raised",
    "control": "settings.theme_color_control",
    "control_hover": "settings.theme_color_control_hover",
    "danger": "settings.theme_color_danger",
    "danger_panel": "settings.theme_color_danger_panel",
    "info": "settings.theme_color_info",
    "scrim": "settings.theme_color_scrim",
    "gradient_start": "settings.theme_color_gradient_start",
    "gradient_end": "settings.theme_color_gradient_end",
    "success": "settings.theme_color_success",
    "warning": "settings.theme_color_warning",
}
UI_THEME_BUTTON_STYLES = {
    "solid": "settings.button_style_solid",
    "soft": "settings.button_style_soft",
    "outline": "settings.button_style_outline",
    "glass": "settings.button_style_glass",
}
UI_THEME_CARD_RADIUS_OPTIONS = {
    "4": "settings.card_radius_sharp",
    "6": "settings.card_radius_compact",
    "8": "settings.card_radius_standard",
    "12": "settings.card_radius_round",
    "16": "settings.card_radius_pill",
}
UI_THEME_ACCENT_PALETTES = {
    "teal": {"label": "Teal", "accent": "#5eead4", "support": "#34d399", "warm": "#f59e0b"},
    "sky": {"label": "Sky", "accent": "#38bdf8", "support": "#818cf8", "warm": "#facc15"},
    "lime": {"label": "Lime", "accent": "#84cc16", "support": "#22c55e", "warm": "#fbbf24"},
    "amber": {"label": "Amber", "accent": "#f59e0b", "support": "#ef4444", "warm": "#fde047"},
    "rose": {"label": "Rose", "accent": "#fb7185", "support": "#f97316", "warm": "#facc15"},
    "violet": {"label": "Violet", "accent": "#a78bfa", "support": "#5eead4", "warm": "#f0abfc"},
    "steel": {"label": "Steel", "accent": "#93c5fd", "support": "#64748b", "warm": "#facc15"},
    "white": {"label": "White", "accent": "#e5e7eb", "support": "#38bdf8", "warm": "#fbbf24"},
}
COLORBLIND_PROFILE_ORDER = ("none", "unsure", "deuteranopia", "protanopia", "tritanopia", "achromatopsia")
COLORBLIND_PROFILE_OPTIONS = {
    "none": {
        "labelKey": "settings.colorblind_profile_none",
        "descriptionKey": "settings.colorblind_profile_none_detail",
    },
    "unsure": {
        "labelKey": "settings.colorblind_profile_unsure",
        "descriptionKey": "settings.colorblind_profile_unsure_detail",
    },
    "deuteranopia": {
        "labelKey": "settings.colorblind_profile_deuteranopia",
        "descriptionKey": "settings.colorblind_profile_deuteranopia_detail",
    },
    "protanopia": {
        "labelKey": "settings.colorblind_profile_protanopia",
        "descriptionKey": "settings.colorblind_profile_protanopia_detail",
    },
    "tritanopia": {
        "labelKey": "settings.colorblind_profile_tritanopia",
        "descriptionKey": "settings.colorblind_profile_tritanopia_detail",
    },
    "achromatopsia": {
        "labelKey": "settings.colorblind_profile_achromatopsia",
        "descriptionKey": "settings.colorblind_profile_achromatopsia_detail",
    },
}
COLORBLIND_THEME_OVERRIDES = {
    "unsure": {
        "accent": "#3b82f6",
        "accent_hover": "#ec4899",
        "accent_panel": "#162a4a",
        "success": "#38bdf8",
        "warning": "#f97316",
        "warning_text": "#fff7ed",
        "danger": "#ec4899",
        "danger_hover": "#be185d",
        "danger_panel": "#3b1730",
        "info": "#a78bfa",
        "border": "#3b82f6",
        "control": "#1d3353",
        "control_hover": "#375f8f",
    },
    "deuteranopia": {
        "accent": "#2563eb",
        "accent_hover": "#f97316",
        "accent_panel": "#132a4f",
        "success": "#06b6d4",
        "warning": "#f59e0b",
        "warning_text": "#fff7ed",
        "danger": "#db2777",
        "danger_hover": "#be185d",
        "danger_panel": "#38162b",
        "info": "#7c3aed",
        "border": "#3b82f6",
        "control": "#1d3353",
        "control_hover": "#365d8d",
    },
    "protanopia": {
        "accent": "#1d4ed8",
        "accent_hover": "#f59e0b",
        "accent_panel": "#13264a",
        "success": "#0891b2",
        "warning": "#fbbf24",
        "warning_text": "#422006",
        "danger": "#c026d3",
        "danger_hover": "#a21caf",
        "danger_panel": "#321636",
        "info": "#9333ea",
        "border": "#3b82f6",
        "control": "#1d3353",
        "control_hover": "#365d8d",
    },
    "tritanopia": {
        "accent": "#ec4899",
        "accent_hover": "#14b8a6",
        "accent_panel": "#3a1730",
        "success": "#14b8a6",
        "warning": "#f97316",
        "warning_text": "#fff7ed",
        "danger": "#f43f5e",
        "danger_hover": "#e11d48",
        "danger_panel": "#3b1624",
        "info": "#a855f7",
        "border": "#ec4899",
        "control": "#3a2145",
        "control_hover": "#58356e",
    },
    "achromatopsia": {
        "accent": "#f8fafc",
        "accent_hover": "#cbd5e1",
        "accent_panel": "#263241",
        "success": "#f8fafc",
        "warning": "#e2e8f0",
        "warning_text": "#020617",
        "danger": "#ffffff",
        "danger_hover": "#cbd5e1",
        "danger_panel": "#334155",
        "info": "#e2e8f0",
        "border": "#f8fafc",
        "control": "#334155",
        "control_hover": "#475569",
        "text_inverse": "#020617",
        "scrim": "#000000",
    },
}
STARTUP_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
OVERLAY_PALETTES = {
    "Azul": {"bg": "#071426", "panel": "#12233d", "accent": "#8ab4ff"},
    "Verde": {"bg": "#071a18", "panel": "#10342e", "accent": "#5eead4"},
    "Roxo": {"bg": "#141125", "panel": "#2a214b", "accent": "#c4b5fd"},
    "Vermelho": {"bg": "#211016", "panel": "#431926", "accent": "#ff8aa0"},
    "Acessivel": {"bg": "#050b16", "panel": "#162a4a", "accent": "#f97316"},
}
OVERLAY_COLOR_LABEL_KEYS = {
    "Azul": "overlay.color_blue",
    "Verde": "overlay.color_green",
    "Roxo": "overlay.color_purple",
    "Vermelho": "overlay.color_red",
    "Acessivel": "overlay.color_accessible",
}

PANEL_REQUIRED_ACCESS_LEVEL = 2

PANEL_ACCESS_ROLE_BY_LEVEL = {
    2: "MEMBER",
    3: "MEMBER",
    4: "ADMIN",
    5: "WINNER",
}

REGIMENT_CANONICAL = {
    "STORM": "STORM",
    "WRG": "WRG",
    "LIDA": "LIDA",
    "7CMD": "7CMD",
    "FELB": "FELB",
    "GDO": "GDO",
    "DOGZ": "DOGZ",
    "DOG'Z": "DOGZ",
    "DOG Z": "DOGZ",
    "REQ": "REQ",
}




def int_or_none(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_panel_role(current_role: object, access_level: int | None) -> str:
    role = str(current_role or "").strip().upper()
    if role == "DEV":
        return "DEV"
    if access_level is None:
        return role
    return PANEL_ACCESS_ROLE_BY_LEVEL.get(access_level, role or "MEMBER")


def normalize_regiment(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    key = re.sub(r"[^A-Z0-9]+", " ", raw.upper()).strip()
    compact = key.replace(" ", "")
    for candidate in (raw.upper(), key, compact):
        if candidate in REGIMENT_CANONICAL:
            return REGIMENT_CANONICAL[candidate]
    return raw


def normalize_panel_access(access: object, user: dict[str, Any] | None = None) -> dict[str, Any]:
    user = user or {}
    access_data = access if isinstance(access, dict) else {}
    access_level = int_or_none(
        access_data.get("accessLevel")
        or access_data.get("panelAccessLevel")
        or user.get("panelAccessLevel")
        or user.get("accessLevel")
    )
    api_allows_panel = bool(access_data.get("canLoginPanel")) if "canLoginPanel" in access_data else True
    can_login_panel = bool(api_allows_panel and access_level is not None and access_level >= PANEL_REQUIRED_ACCESS_LEVEL)
    return {
        "accessLevel": access_level if access_level is not None else 0,
        "canLoginPanel": can_login_panel,
        "verified": access_level is not None,
        "requiredAccessLevel": int_or_none(access_data.get("requiredAccessLevel")) or PANEL_REQUIRED_ACCESS_LEVEL,
        "requiredRolesForAdminControls": access_data.get("requiredRolesForAdminControls") or ["WINNER", "DEV"],
        "canLoginChat": access_data.get("canLoginChat", True),
        "message": access_data.get("message") or access_data.get("reason") or "",
    }


def merge_panel_profile(user: dict[str, Any], access: object | None = None) -> dict[str, Any]:
    merged = dict(user)
    panel_access = normalize_panel_access(access or merged.get("panelAccess"), merged)
    access_level = int_or_none(panel_access.get("accessLevel"))
    role = normalize_panel_role(merged.get("role"), access_level)
    if role:
        merged["role"] = role
    regiment = normalize_regiment(merged.get("regiment"))
    if regiment:
        merged["regiment"] = regiment
    merged["panelAccess"] = panel_access
    merged["panelAccessLevel"] = access_level if access_level is not None else 0
    if access and isinstance(access, dict) and access.get("panelAccessSyncedAt"):
        merged["panelAccessSyncedAt"] = access.get("panelAccessSyncedAt")
    return merged


def panel_access_allows_app_login(profile: dict[str, Any]) -> bool:
    access = profile.get("panelAccess") if isinstance(profile.get("panelAccess"), dict) else {}
    access_level = int_or_none(access.get("accessLevel") or profile.get("panelAccessLevel") or profile.get("accessLevel"))
    if access_level is None:
        return False
    if access_level in (0, 1):
        return False
    if access.get("canLoginChat") is False:
        return False
    if "canLoginPanel" in access and access.get("canLoginPanel") is False:
        return False
    return access_level >= PANEL_REQUIRED_ACCESS_LEVEL


def redact_login_debug(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in {"token", "accesstoken", "access_token", "refresh_token", "authorization", "client_secret", "code", "codeverifier", "code_verifier", "autologinkey", "auto_login_key", "accesspassword", "access_password"}:
                text_value = str(item or "")
                redacted[str(key)] = f"<redacted len={len(text_value)}>"
            else:
                redacted[str(key)] = redact_login_debug(item)
        return redacted
    if isinstance(value, list):
        return [redact_login_debug(item) for item in value]
    return value


def redact_http_error_body(body: str) -> str:
    if not body:
        return body
    try:
        parsed = json.loads(body)
    except Exception:
        sanitized = body
        sensitive_patterns = (
            r'("code"\s*:\s*")[^"]+(")',
            r'("codeVerifier"\s*:\s*")[^"]+(")',
            r'("code_verifier"\s*:\s*")[^"]+(")',
            r'("client_secret"\s*:\s*")[^"]+(")',
            r'("autoLoginKey"\s*:\s*")[^"]+(")',
            r'("auto_login_key"\s*:\s*")[^"]+(")',
            r'("accessPassword"\s*:\s*")[^"]+(")',
            r'("access_password"\s*:\s*")[^"]+(")',
        )
        for pattern in sensitive_patterns:
            sanitized = re.sub(pattern, r'\1<redacted>\2', sanitized, flags=re.IGNORECASE)
        return sanitized
    return json.dumps(redact_login_debug(parsed), ensure_ascii=False)

def debug_login_response(label: str, result: dict[str, Any]) -> None:
    try:
        body = json.dumps(redact_login_debug(result), ensure_ascii=False, indent=2)
    except Exception:
        body = str(result)
    print(f"[GG Coalition login] {label} retornou:\n{body}", flush=True)


def file_url(path: str | Path) -> str:
    return QUrl.fromLocalFile(str(Path(path).resolve())).toString()


def markdown_inline_html(value: object) -> str:
    text = html.escape(str(value or ""))
    text = re.sub(
        r"@\[video\]\((https?://[^)\s]+)\)",
        r'<a href="\1">video</a>',
        text,
    )
    text = re.sub(
        r"!\[([^\]]*)\]\((https?://[^)\s]+)\)",
        r'<img src="\2" alt="\1" />',
        text,
    )
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def markdown_table_html(rows: list[str]) -> str:
    parsed: list[list[str]] = []
    for index, row in enumerate(rows):
        if index == 1:
            continue
        cells = [markdown_inline_html(cell.strip()) for cell in row.strip().strip("|").split("|")]
        parsed.append(cells)
    if not parsed:
        return ""
    headers = "".join(f"<th>{cell}</th>" for cell in parsed[0])
    body_rows = "".join(
        f"<tr>{''.join(f'<td>{cell}</td>' for cell in row)}</tr>"
        for row in parsed[1:]
    )
    return f"<table><thead><tr>{headers}</tr></thead><tbody>{body_rows}</tbody></table>"


def markdown_is_table_start(lines: list[str], index: int) -> bool:
    current = lines[index] if index < len(lines) else ""
    next_line = lines[index + 1] if index + 1 < len(lines) else ""
    return bool(
        re.match(r"^\s*\|.+\|\s*$", current)
        and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", next_line)
    )


def markdown_to_html(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lines = text.splitlines()
    output: list[str] = []
    list_tag = ""

    def close_list() -> None:
        nonlocal list_tag
        if list_tag:
            output.append(f"</{list_tag}>")
            list_tag = ""

    index = 0
    while index < len(lines):
        raw = lines[index]
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            close_list()
            index += 1
            continue
        if re.match(r"^(-{3,}|\*{3,})$", stripped):
            close_list()
            output.append("<hr />")
            index += 1
            continue
        if markdown_is_table_start(lines, index):
            close_list()
            table_rows: list[str] = []
            while index < len(lines) and re.match(r"^\s*\|.+\|\s*$", lines[index]):
                table_rows.append(lines[index])
                index += 1
            output.append(markdown_table_html(table_rows))
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{markdown_inline_html(heading.group(2))}</h{level}>")
            index += 1
            continue
        unordered = re.match(r"^[-*]\s+(.+)$", line)
        ordered = re.match(r"^\d+\.\s+(.+)$", line)
        if unordered or ordered:
            tag = "ul" if unordered else "ol"
            if list_tag != tag:
                close_list()
                list_tag = tag
                output.append(f"<{tag}>")
            output.append(f"<li>{markdown_inline_html((unordered or ordered).group(1))}</li>")
            index += 1
            continue
        if line.startswith("> "):
            close_list()
            output.append(f"<blockquote>{markdown_inline_html(line[2:])}</blockquote>")
            index += 1
            continue
        close_list()
        output.append(f"<p>{markdown_inline_html(line)}</p>")
        index += 1

    close_list()
    return "".join(output)


def markdown_to_news_blocks(value: object) -> list[dict[str, Any]]:
    html_value = markdown_to_html(value)
    return [{"type": "rich", "html": html_value}] if html_value else []


def news_image_url(item: dict[str, Any]) -> str:
    for key in (
        "thumbnailUrl",
        "thumbnail",
        "coverImageUrl",
        "coverImage",
        "imageUrl",
        "image",
        "bannerUrl",
        "banner",
    ):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    media = item.get("media") if isinstance(item.get("media"), dict) else {}
    for key in ("thumbnailUrl", "url", "imageUrl", "src"):
        value = str(media.get(key) or "").strip()
        if value:
            return value
    return ""


_LOCATION_INDEX: dict[tuple[str, str], dict[str, str]] | None = None
_LOCATION_CODE_INDEX: dict[tuple[str, str], dict[str, str]] | None = None


def _compact_location_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _strip_hex_suffix(value: str) -> str:
    text = str(value or "").strip()
    return text[:-3] if text.lower().endswith("hex") else text


def stockpile_map_name(value: str) -> str:
    text = _strip_hex_suffix(value).strip()
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _first_mapping_text(mapping: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _warehouse_nested(warehouse: dict[str, Any]) -> dict[str, Any]:
    nested = warehouse.get("warehouse")
    return nested if isinstance(nested, dict) else {}


def _warehouse_text(warehouse: dict[str, Any], *keys: str) -> str:
    return _first_mapping_text(warehouse, *keys) or _first_mapping_text(_warehouse_nested(warehouse), *keys)


def _town_code_candidates(town: str, code: str = "") -> list[str]:
    candidates: list[str] = []
    code_text = re.sub(r"[^A-Z0-9]", "", str(code or "").upper())
    if len(code_text) >= 2:
        candidates.append(code_text[-2:])

    normalized = re.sub(r"['’]", "", str(town or ""))
    words = re.findall(r"[A-Za-z0-9]+", normalized)
    if words:
        candidates.append("".join(word[0].upper() for word in words))
        main_words = [word for word in words if word.lower() not in {"a", "an", "of", "the"}]
        if main_words:
            candidates.append("".join(word[0].upper() for word in main_words))

    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique


def _stockpile_town_code(value: str) -> str:
    parts = [part.strip() for part in str(value or "").upper().split("-") if part.strip()]
    if len(parts) >= 2 and parts[0] == "GG":
        return re.sub(r"[^A-Z0-9]", "", parts[1])
    return ""


def _location_index() -> dict[tuple[str, str], dict[str, str]]:
    global _LOCATION_INDEX
    if _LOCATION_INDEX is not None:
        return _LOCATION_INDEX

    index: dict[tuple[str, str], dict[str, str]] = {}
    for csv_path in (resource_dir() / "data" / "locations.csv", BASE_DIR / "data" / "locations.csv"):
        if not csv_path.exists():
            continue
        try:
            with csv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
                for row in csv.DictReader(handle):
                    region = str(row.get("Hex") or "").strip()
                    town = str(row.get("Loc") or "").strip()
                    if not region or not town:
                        continue
                    index[(_compact_location_key(region), town.lower())] = {
                        "region": region,
                        "town": town,
                        "mapName": stockpile_map_name(region),
                        "code": str(row.get("Code") or "").strip(),
                    }
        except OSError:
            continue
        if index:
            break
    _LOCATION_INDEX = index
    return index


def _location_code_index() -> dict[tuple[str, str], dict[str, str]]:
    global _LOCATION_CODE_INDEX
    if _LOCATION_CODE_INDEX is not None:
        return _LOCATION_CODE_INDEX

    index: dict[tuple[str, str], dict[str, str]] = {}
    for location in _location_index().values():
        map_key = _compact_location_key(location.get("region", ""))
        if not map_key:
            continue
        for code in _town_code_candidates(location.get("town", ""), location.get("code", "")):
            index.setdefault((map_key, code), location)
    _LOCATION_CODE_INDEX = index
    return index


def _location_from_stockpile_code(map_key: str, *values: str) -> dict[str, str] | None:
    if not map_key:
        return None
    locations = _location_code_index()
    for value in values:
        town_code = _stockpile_town_code(value)
        if not town_code:
            continue
        matched = locations.get((map_key, town_code))
        if matched:
            return matched
    return None


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


def parse_stockpile_datetime(value: Any) -> datetime | None:
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
    if not text or text == "-":
        return None
    if text.isdigit():
        return parse_stockpile_datetime(int(text))
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


def format_relative_time(value: Any, translator: Translator | None = None) -> str:
    parsed = parse_stockpile_datetime(value)
    if parsed is None:
        return ""
    seconds = max(0, int((datetime.now().astimezone() - parsed).total_seconds()))

    def relative_text(key: str, **kwargs: Any) -> str:
        if translator is not None:
            return translator.t(key, **kwargs)
        return Translator("pt").t(key, **kwargs)

    if seconds < 60:
        return relative_text("time.now")
    minutes = seconds // 60
    if minutes == 1:
        return relative_text("time.minute_ago")
    if minutes < 60:
        return relative_text("time.minutes_ago", count=minutes)
    hours = minutes // 60
    if hours == 1:
        return relative_text("time.hour_ago")
    if hours < 24:
        return relative_text("time.hours_ago", count=hours)
    days = hours // 24
    if days == 1:
        return relative_text("time.day_ago")
    if days < 30:
        return relative_text("time.days_ago", count=days)
    return parsed.strftime("%d/%m/%Y")


def debug_memory(label: str) -> None:
    if not os.environ.get("FELB_DEBUG_MEMORY"):
        return
    try:
        import psutil

        rss_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        return
    print(f"[memory] {label}: {rss_mb:.1f} MB", flush=True)


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


def is_python_launcher(path: Path) -> bool:
    return path.name.lower() in {"python.exe", "pythonw.exe", "py.exe"}


def current_windows_module_exe() -> Path | None:
    if os.name != "nt":
        return None

    import ctypes
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = ctypes.windll.kernel32.GetModuleFileNameW(None, buffer, len(buffer))
        if size:
            path = Path(buffer.value).resolve()
            if path.exists():
                return path
    except Exception:
        pass

    return None


def built_executable_path() -> Path | None:
    candidates: list[Path] = []

    module_exe = current_windows_module_exe()
    if module_exe:
        candidates.append(module_exe)

    try:
        if sys.argv and sys.argv[0]:
            candidates.append(Path(sys.argv[0]).resolve())
    except Exception:
        pass

    try:
        current_exe = Path(sys.executable).resolve()
        candidates.append(current_exe)
        candidates.append(current_exe.parent / f"{APP_TITLE}.exe")
    except Exception:
        pass

    candidates.append(BASE_DIR / f"{APP_TITLE}.exe")

    for candidate in candidates:
        try:
            candidate = candidate.resolve()
            if (
                candidate.exists()
                and candidate.suffix.lower() == ".exe"
                and not is_python_launcher(candidate)
            ):
                return candidate
        except Exception:
            pass

    return None


def is_built_app() -> bool:
    return bool(
        getattr(sys, "frozen", False)
        or "__compiled__" in globals()
        or hasattr(sys, "_MEIPASS")
    )


def startup_target_and_args(settings: dict[str, Any]) -> tuple[Path, list[str]]:
    app_settings = settings.get("app", {})
    args: list[str] = []

    if app_settings.get("start_in_background", False):
        args.append("--background")

    if is_built_app():
        exe = built_executable_path()
        if exe:
            return exe, args
        raise RuntimeError("Executável do aplicativo buildado não encontrado.")

    python_exe = Path(sys.executable).resolve()
    pythonw = python_exe.with_name("pythonw.exe")
    if pythonw.exists():
        python_exe = pythonw

    script_path = (BASE_DIR / "felb_app.py").resolve()
    return python_exe, [str(script_path), *args]


def startup_command(settings: dict[str, Any]) -> str:
    target, args = startup_target_and_args(settings)
    return subprocess.list2cmdline([str(target), *args])


def launch_target() -> Path:
    exe = built_executable_path()
    if exe:
        return exe
    return BASE_DIR / "felb_app.py"


def runtime_dir() -> Path:
    exe = built_executable_path()
    if exe:
        return exe.parent
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


def read_startup_command() -> str:
    if os.name != "nt":
        return ""

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _kind = winreg.QueryValueEx(key, APP_TITLE)
            return str(value or "")
    except FileNotFoundError:
        return ""
    except OSError:
        return ""


def startup_registry_matches(settings: dict[str, Any]) -> bool:
    try:
        expected = startup_command(settings).strip()
    except Exception:
        return False

    current = read_startup_command().strip()
    return current.lower() == expected.lower()


def set_start_with_windows(enabled: bool, settings: dict[str, Any]) -> None:
    if os.name != "nt":
        raise RuntimeError("Windows startup is only available on Windows.")

    import winreg

    remove_startup_task()
    remove_startup_shortcuts()

    if enabled:
        command = startup_command(settings)

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            STARTUP_RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, APP_TITLE, 0, winreg.REG_SZ, command)

        if not startup_registry_matches(settings):
            raise RuntimeError("Falha ao confirmar o comando de inicialização no Registro do Windows.")

        return

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_TITLE)
    except FileNotFoundError:
        pass


def ensure_startup_enabled_by_default(settings: dict[str, Any]) -> None:
    app_settings = settings.setdefault("app", {})

    if os.name != "nt" or not is_built_app():
        return

    # Se o usuário/app já queria iniciar com Windows, mas o caminho mudou após update,
    # corrige o Registro para o EXE atual.
    if app_settings.get("start_with_windows", False) and not startup_registry_matches(settings):
        try:
            set_start_with_windows(True, settings)
            app_settings["start_with_windows"] = startup_registry_matches(settings)
            app_settings.pop("startup_default_error", None)
            save_settings(settings)
        except Exception as exc:
            app_settings["startup_default_error"] = str(exc)
            save_settings(settings)
        return

    if app_settings.get("startup_default_applied", False):
        return

    try:
        set_start_with_windows(True, settings)
        app_settings["start_with_windows"] = startup_registry_matches(settings)
        app_settings["startup_prompted"] = True
        app_settings["startup_default_applied"] = True
        app_settings.pop("startup_default_error", None)
    except Exception as exc:
        app_settings["start_with_windows"] = False
        app_settings["startup_default_applied"] = True
        app_settings["startup_default_error"] = str(exc)

    save_settings(settings)




















WIKI_KEY_LABELS_BY_LANGUAGE = {
    "pt": {
        "class": "Classe",
        "health": "Vida",
        "resistance": "Resistencia",
        "armour": "Blindagem",
        "armor": "Blindagem",
        "speed": "Velocidade",
        "velocity": "Velocidade",
        "caliber": "Calibre",
        "reload": "Recarga",
        "cooldown": "Tempo de recarga",
        "splash_radius": "Raio de explosao",
        "damage_per_shot": "Dano por tiro",
        "fuel_usage": "Consumo de combustivel",
        "disable_threshold": "Limite de desativacao",
        "repair_cost": "Custo de reparo",
        "crew": "Tripulacao",
        "inventory_slots": "Espacos no inventario",
        "armament": "Armamento",
        "ammo": "Municao",
        "production_site": "Local de producao",
        "production_cost_raw": "Custo de producao",
        "package_size": "Tamanho do pacote",
        "fuel_capacity": "Capacidade de combustivel",
        "intel_icon": "Icone de inteligencia",
        "super_class": "Superclasse",
        "category": "Categoria",
        "encumbrance": "Peso",
        "amount_per_crate": "Quantidade por caixa",
        "main_production_site": "Local principal de producao",
        "main_production_cost": "Custo principal de producao",
        "faction": "Faccao",
        "damage": "Dano",
        "damage_type": "Tipo de dano",
        "range": "Alcance",
        "rate_of_fire": "Cadencia",
        "magazine_size": "Tamanho do carregador",
        "reload_time": "Tempo de recarga",
        "weight": "Peso",
        "equipment_slot": "Espaco de equipamento",
        "ammunition": "Municao",
        "fire_rate": "Cadencia de tiro",
        "firing_mode": "Modo de disparo",
        "hitpoints": "Pontos de vida",
        "hp": "HP",
        "explosive_damage": "Dano explosivo",
        "ap_damage": "Dano AP",
        "penetration_modifier": "Modificador de penetracao",
        "inner_radius": "Raio interno",
        "outer_radius": "Raio externo",
        "storage_capacity": "Capacidade de armazenamento",
    },
    "en": {
        "class": "Class",
        "health": "Health",
        "resistance": "Resistance",
        "armour": "Armour",
        "armor": "Armour",
        "speed": "Speed",
        "velocity": "Velocity",
        "caliber": "Caliber",
        "reload": "Reload",
        "cooldown": "Cooldown",
        "splash_radius": "Splash radius",
        "damage_per_shot": "Damage per shot",
        "fuel_usage": "Fuel usage",
        "disable_threshold": "Disable threshold",
        "repair_cost": "Repair cost",
        "crew": "Crew",
        "inventory_slots": "Inventory slots",
        "armament": "Armament",
        "ammo": "Ammo",
        "production_site": "Production site",
        "production_cost_raw": "Production cost",
        "package_size": "Package size",
        "fuel_capacity": "Fuel capacity",
        "intel_icon": "Intel icon",
        "super_class": "Super class",
        "category": "Category",
        "encumbrance": "Encumbrance",
        "amount_per_crate": "Amount per crate",
        "main_production_site": "Main production site",
        "main_production_cost": "Main production cost",
        "faction": "Faction",
        "damage": "Damage",
        "damage_type": "Damage type",
        "range": "Range",
        "rate_of_fire": "Rate of fire",
        "magazine_size": "Magazine size",
        "reload_time": "Reload time",
        "weight": "Weight",
        "equipment_slot": "Equipment slot",
        "ammunition": "Ammunition",
        "fire_rate": "Fire rate",
        "firing_mode": "Firing mode",
        "hitpoints": "Hit points",
        "hp": "HP",
        "explosive_damage": "Explosive damage",
        "ap_damage": "AP damage",
        "penetration_modifier": "Penetration modifier",
        "inner_radius": "Inner radius",
        "outer_radius": "Outer radius",
        "storage_capacity": "Storage capacity",
    },
    "es": {
        "class": "Clase",
        "health": "Vida",
        "resistance": "Resistencia",
        "armour": "Blindaje",
        "armor": "Blindaje",
        "speed": "Velocidad",
        "velocity": "Velocidad",
        "caliber": "Calibre",
        "reload": "Recarga",
        "cooldown": "Tiempo de recarga",
        "splash_radius": "Radio de explosion",
        "damage_per_shot": "Dano por disparo",
        "fuel_usage": "Consumo de combustible",
        "disable_threshold": "Umbral de desactivacion",
        "repair_cost": "Costo de reparacion",
        "crew": "Tripulacion",
        "inventory_slots": "Espacios de inventario",
        "armament": "Armamento",
        "ammo": "Municion",
        "production_site": "Lugar de produccion",
        "production_cost_raw": "Costo de produccion",
        "package_size": "Tamano del paquete",
        "fuel_capacity": "Capacidad de combustible",
        "intel_icon": "Icono de inteligencia",
        "super_class": "Superclase",
        "category": "Categoria",
        "encumbrance": "Peso",
        "amount_per_crate": "Cantidad por caja",
        "main_production_site": "Lugar principal de produccion",
        "main_production_cost": "Costo principal de produccion",
        "faction": "Faccion",
        "damage": "Dano",
        "damage_type": "Tipo de dano",
        "range": "Alcance",
        "rate_of_fire": "Cadencia",
        "magazine_size": "Tamano del cargador",
        "reload_time": "Tiempo de recarga",
        "weight": "Peso",
        "equipment_slot": "Espacio de equipo",
        "ammunition": "Municion",
        "fire_rate": "Cadencia de disparo",
        "firing_mode": "Modo de disparo",
        "hitpoints": "Pontos de vida",
        "hp": "HP",
        "explosive_damage": "Dano explosivo",
        "ap_damage": "Dano AP",
        "penetration_modifier": "Modificador de penetracao",
        "inner_radius": "Raio interno",
        "outer_radius": "Raio externo",
        "storage_capacity": "Capacidade de armazenamento",
    },
    "fr": {
        "class": "Classe",
        "health": "Sante",
        "resistance": "Resistance",
        "armour": "Blindage",
        "armor": "Blindage",
        "speed": "Vitesse",
        "velocity": "Vitesse",
        "caliber": "Calibre",
        "reload": "Rechargement",
        "cooldown": "Temps de recharge",
        "splash_radius": "Rayon d explosion",
        "damage_per_shot": "Degats par tir",
        "fuel_usage": "Consommation de carburant",
        "disable_threshold": "Seuil de desactivation",
        "repair_cost": "Cout de reparation",
        "crew": "Equipage",
        "inventory_slots": "Emplacements d'inventaire",
        "armament": "Armement",
        "ammo": "Munitions",
        "production_site": "Site de production",
        "production_cost_raw": "Cout de production",
        "package_size": "Taille du paquet",
        "fuel_capacity": "Capacite de carburant",
        "intel_icon": "Icone de renseignement",
        "super_class": "Super classe",
        "category": "Categorie",
        "encumbrance": "Poids",
        "amount_per_crate": "Quantite par caisse",
        "main_production_site": "Site principal de production",
        "main_production_cost": "Cout principal de production",
        "faction": "Faction",
        "damage": "Degats",
        "damage_type": "Type de degats",
        "range": "Portee",
        "rate_of_fire": "Cadence",
        "magazine_size": "Taille du chargeur",
        "reload_time": "Temps de rechargement",
        "weight": "Poids",
        "equipment_slot": "Emplacement d'equipement",
        "ammunition": "Munitions",
        "fire_rate": "Cadence de tir",
        "firing_mode": "Mode de tir",
        "hitpoints": "Points de vie",
        "hp": "PV",
        "explosive_damage": "Degats explosifs",
        "ap_damage": "Degats AP",
        "penetration_modifier": "Modificateur de penetration",
        "inner_radius": "Rayon interieur",
        "outer_radius": "Rayon exterieur",
        "storage_capacity": "Capacite de stockage",
    },
}

WIKI_VALUE_TRANSLATIONS_BY_LANGUAGE = {
    "pt": {
        "Armored Car": "Carro blindado",
        "Battle Tank": "Tanque de batalha",
        "Emplacement": "Posicao fixa",
        "Field Weapon": "Arma de campo",
        "Flatbed Truck": "Caminhao prancha",
        "Heavy Artillery": "Artilharia pesada",
        "Infantry Weapon": "Arma de infantaria",
        "Large Item": "Item grande",
        "Logistics Structure": "Estrutura logistica",
        "Material": "Material",
        "Refined Material": "Material refinado",
        "Resource": "Recurso",
        "Small Arms": "Armas leves",
        "Small Item": "Item pequeno",
        "Structure": "Estrutura",
        "Vehicle": "Veiculo",
        "Warden": "Warden",
        "Colonial": "Colonial",
        "Both": "Ambos",
        "Factory": "Fabrica",
        "Garage": "Garagem",
        "Mass Production Factory": "Fabrica de producao em massa",
        "Construction Yard": "Patio de construcao",
        "Unpackageable": "Nao empacotavel",
        "None": "Nenhum",
        "Submachine Gun Ammo": "Municao de submetralhadora",
        "Magazine": "Carregador",
        "Ammunition": "Municao",
        "Firearms": "Armas de fogo",
        "Small Arms Facility Items": "Itens de instalacao de armas leves",
        "Basic Materials": "Materiais basicos",
        "Crate": "Caixa",
        "Magazines": "Carregadores",
        "Rifles": "Rifles",
        "Weapon Classes": "Classes de armas",
        "Light Kinetic Damage": "Dano cinetico leve",
        "Kinetic Damage": "Dano cinetico",
        "Submachine Guns": "Submetralhadoras",
        "Weapons": "Armas",
        "Tools": "Ferramentas",
        "Uniforms": "Uniformes",
        "Vehicles": "Veiculos",
        "Structures": "Estruturas",
        "Armored Vehicles": "Veiculos blindados",
        "Inventory": "Inventario",
        "Player": "Jogador",
        "Players": "Jogadores",
        "Faction": "Faccao",
        "Stack": "Acumulo",
        "Stacks": "Acumulos",
        "Per slot": "Por espaco",
        "Soldier Uniform": "Uniforme de soldado",
        "Snow Uniform": "Uniforme de neve",
        "Rain Uniform": "Uniforme de chuva",
        "Structure damage": "Dano a estruturas",
        "Armored vehicle": "veiculo blindado",
        "Armored vehicles": "veiculos blindados",
        "Small Arms Magazine": "Carregador de armas leves",
        "small arms Magazine": "carregador de armas leves",
        "is a type of": "e um tipo de",
        "used in": "usado em",
        "By default": "Por padrao",
        "its bullets": "seus projeteis",
        "deal": "causam",
        "damage": "dano",
        "It does not deal any damage to": "Nao causa dano a",
        "and very little to": "e muito pouco a",
        "It does not stack in the player's inventory": "Nao acumula no inventario do jogador",
        "except when wearing": "exceto ao usar",
        "can be fired by": "pode ser disparado por",
        "Description": "Descricao",
        "Usage": "Uso",
        "Production": "Producao",
        "Storage": "Armazenamento",
        "Tactics": "Taticas",
        "Trivia": "Curiosidades",
        "Update History": "Historico de atualizacoes",
    },
    "en": {
        "Armored Car": "Armored Car",
        "Battle Tank": "Battle Tank",
        "Emplacement": "Emplacement",
        "Field Weapon": "Field Weapon",
        "Flatbed Truck": "Flatbed Truck",
        "Heavy Artillery": "Heavy Artillery",
        "Infantry Weapon": "Infantry Weapon",
        "Large Item": "Large Item",
        "Logistics Structure": "Logistics Structure",
        "Material": "Material",
        "Refined Material": "Refined Material",
        "Resource": "Resource",
        "Small Arms": "Small Arms",
        "Small Item": "Small Item",
        "Structure": "Structure",
        "Vehicle": "Vehicle",
        "Warden": "Warden",
        "Colonial": "Colonial",
        "Both": "Both",
        "Factory": "Factory",
        "Garage": "Garage",
        "Mass Production Factory": "Mass Production Factory",
        "Construction Yard": "Construction Yard",
        "Unpackageable": "Unpackageable",
        "None": "None",
        "Submachine Gun Ammo": "Submachine Gun Ammo",
        "Magazine": "Magazine",
        "Ammunition": "Ammunition",
        "Firearms": "Firearms",
        "Small Arms Facility Items": "Small Arms Facility Items",
        "Basic Materials": "Basic Materials",
        "Crate": "Crate",
        "Magazines": "Magazines",
        "Rifles": "Rifles",
        "Weapon Classes": "Weapon Classes",
        "Light Kinetic Damage": "Light Kinetic Damage",
        "Description": "Description",
        "Usage": "Usage",
        "Production": "Production",
        "Storage": "Storage",
        "Tactics": "Tactics",
        "Trivia": "Trivia",
        "Update History": "Update History",
    },
    "es": {
        "Armored Car": "Auto blindado",
        "Battle Tank": "Tanque de batalla",
        "Emplacement": "Emplazamiento",
        "Field Weapon": "Arma de campo",
        "Flatbed Truck": "Camion plataforma",
        "Heavy Artillery": "Artilleria pesada",
        "Infantry Weapon": "Arma de infanteria",
        "Large Item": "Item grande",
        "Logistics Structure": "Estructura logistica",
        "Material": "Material",
        "Refined Material": "Material refinado",
        "Resource": "Recurso",
        "Small Arms": "Armas ligeras",
        "Small Item": "Item pequeno",
        "Structure": "Estructura",
        "Vehicle": "Vehiculo",
        "Warden": "Warden",
        "Colonial": "Colonial",
        "Both": "Ambos",
        "Factory": "Fabrica",
        "Garage": "Garaje",
        "Mass Production Factory": "Fabrica de produccion en masa",
        "Construction Yard": "Patio de construccion",
        "Unpackageable": "No empaquetable",
        "None": "Ninguno",
        "Submachine Gun Ammo": "Municion de subfusil",
        "Magazine": "Cargador",
        "Ammunition": "Municion",
        "Firearms": "Armas de fuego",
        "Small Arms Facility Items": "Items de instalacion de armas ligeras",
        "Basic Materials": "Materiales basicos",
        "Crate": "Caja",
        "Magazines": "Cargadores",
        "Rifles": "Rifles",
        "Weapon Classes": "Clases de armas",
        "Light Kinetic Damage": "Dano cinetico ligero",
        "Kinetic Damage": "Dano cinetico",
        "Submachine Guns": "Subfusiles",
        "Weapons": "Armas",
        "Tools": "Herramientas",
        "Uniforms": "Uniformes",
        "Vehicles": "Vehiculos",
        "Structures": "Estructuras",
        "Armored Vehicles": "Vehiculos blindados",
        "Inventory": "Inventario",
        "Player": "Jugador",
        "Players": "Jugadores",
        "Faction": "Faccion",
        "Stack": "Acumulacion",
        "Stacks": "Acumulaciones",
        "Per slot": "Por espacio",
        "Soldier Uniform": "Uniforme de soldado",
        "Snow Uniform": "Uniforme de nieve",
        "Rain Uniform": "Uniforme de lluvia",
        "Structure damage": "Dano a estructuras",
        "Armored vehicle": "vehiculo blindado",
        "Armored vehicles": "vehiculos blindados",
        "Small Arms Magazine": "Cargador de armas ligeras",
        "small arms Magazine": "cargador de armas ligeras",
        "is a type of": "es un tipo de",
        "used in": "usado en",
        "By default": "Por defecto",
        "its bullets": "sus proyectiles",
        "deal": "causan",
        "damage": "dano",
        "It does not deal any damage to": "No causa dano a",
        "and very little to": "y muy poco a",
        "It does not stack in the player's inventory": "No se acumula en el inventario del jugador",
        "except when wearing": "excepto al usar",
        "can be fired by": "puede ser disparado por",
        "Description": "Descripcion",
        "Usage": "Uso",
        "Production": "Produccion",
        "Storage": "Almacenamiento",
        "Tactics": "Tacticas",
        "Trivia": "Curiosidades",
        "Update History": "Historial de actualizaciones",
    },
    "fr": {
        "Armored Car": "Voiture blindee",
        "Battle Tank": "Char de bataille",
        "Emplacement": "Emplacement",
        "Field Weapon": "Arme de campagne",
        "Flatbed Truck": "Camion plateau",
        "Heavy Artillery": "Artillerie lourde",
        "Infantry Weapon": "Arme d'infanterie",
        "Large Item": "Objet lourd",
        "Logistics Structure": "Structure logistique",
        "Material": "Materiau",
        "Refined Material": "Materiau raffine",
        "Resource": "Ressource",
        "Small Arms": "Armes legeres",
        "Small Item": "Petit objet",
        "Structure": "Structure",
        "Vehicle": "Vehicule",
        "Warden": "Warden",
        "Colonial": "Colonial",
        "Both": "Les deux",
        "Factory": "Usine",
        "Garage": "Garage",
        "Mass Production Factory": "Usine de production de masse",
        "Construction Yard": "Chantier de construction",
        "Unpackageable": "Non empaquetable",
        "None": "Aucun",
        "Submachine Gun Ammo": "Munitions de pistolet-mitrailleur",
        "Magazine": "Chargeur",
        "Ammunition": "Munitions",
        "Firearms": "Armes a feu",
        "Small Arms Facility Items": "Objets d'installation d'armes legeres",
        "Basic Materials": "Materiaux basiques",
        "Crate": "Caisse",
        "Magazines": "Chargeurs",
        "Rifles": "Fusils",
        "Weapon Classes": "Classes d'armes",
        "Light Kinetic Damage": "Degats cinetiques legers",
        "Kinetic Damage": "Degats cinetiques",
        "Submachine Guns": "Pistolets-mitrailleurs",
        "Weapons": "Armes",
        "Tools": "Outils",
        "Uniforms": "Uniformes",
        "Vehicles": "Vehicules",
        "Structures": "Structures",
        "Armored Vehicles": "Vehicules blindes",
        "Inventory": "Inventaire",
        "Player": "Joueur",
        "Players": "Joueurs",
        "Faction": "Faction",
        "Stack": "Pile",
        "Stacks": "Piles",
        "Per slot": "Par emplacement",
        "Soldier Uniform": "Uniforme de soldat",
        "Snow Uniform": "Uniforme de neige",
        "Rain Uniform": "Uniforme de pluie",
        "Structure damage": "Degats aux structures",
        "Armored vehicle": "vehicule blinde",
        "Armored vehicles": "vehicules blindes",
        "Small Arms Magazine": "Chargeur d'armes legeres",
        "small arms Magazine": "chargeur d'armes legeres",
        "is a type of": "est un type de",
        "used in": "utilise dans",
        "By default": "Par defaut",
        "its bullets": "ses projectiles",
        "deal": "infligent",
        "damage": "degats",
        "It does not deal any damage to": "N'inflige aucun degat a",
        "and very little to": "et tres peu a",
        "It does not stack in the player's inventory": "Ne s'empile pas dans l'inventaire du joueur",
        "except when wearing": "sauf en portant",
        "can be fired by": "peut etre tire par",
        "Description": "Description",
        "Usage": "Utilisation",
        "Production": "Production",
        "Storage": "Stockage",
        "Tactics": "Tactiques",
        "Trivia": "Anecdotes",
        "Update History": "Historique des mises a jour",
    },
}

WIKI_FALLBACK_WORDS = {
    "pt": {"below": "abaixo de", "health": "vida"},
    "en": {"below": "below", "health": "health"},
    "es": {"below": "por debajo de", "health": "vida"},
    "fr": {"below": "sous", "health": "sante"},
}


def clean_wiki_text(text: Any) -> str:
    value = html.unescape(str(text or "").replace("\xa0", " "))
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def strip_wiki_html(value: str) -> str:
    value = re.sub(r"<!--.*?-->", " ", value, flags=re.S)
    value = re.sub(r"<(script|style)\b.*?</\1>", " ", value, flags=re.S | re.I)
    value = re.sub(r"<sup\b.*?</sup>", " ", value, flags=re.S | re.I)
    value = re.sub(r"<br\s*/?>", " / ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return clean_wiki_text(value)


def strip_wiki_block(value: str) -> str:
    value = re.sub(r"<!--.*?-->", " ", value, flags=re.S)
    value = re.sub(r"<(script|style|aside|table)\b.*?</\1>", " ", value, flags=re.S | re.I)
    value = re.sub(r"<span\b[^>]*class=(?:\"[^\"]*\bmw-editsection\b[^\"]*\"|'[^']*\bmw-editsection\b[^']*')[^>]*>.*?</span>", " ", value, flags=re.S | re.I)
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</p\s*>", "\n", value, flags=re.I)
    value = re.sub(r"<li\b[^>]*>", "\n- ", value, flags=re.I)
    value = re.sub(r"</h[1-6]\s*>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value.replace("\xa0", " "))
    lines = [re.sub(r"\s+", " ", line).strip(" -") for line in value.splitlines()]
    lines = [line for line in lines if line and line.lower() not in {"edit", "edit source"}]
    return "\n".join(dict.fromkeys(lines))


def normalize_wiki_key(label: str) -> str:
    mapping = {
        "Class": "class",
        "Health": "health",
        "Resistance": "resistance",
        "Armour": "armour",
        "Disable Threshold": "disable_threshold",
        "Repair Cost": "repair_cost",
        "Crew": "crew",
        "Inventory Slots": "inventory_slots",
        "Armament": "armament",
        "Ammo": "ammo",
        "Super Class": "super_class",
        "Category": "category",
        "Encumbrance": "encumbrance",
        "Amount per crate": "amount_per_crate",
        "Main Production Site": "main_production_site",
        "Main Production Cost": "main_production_cost",
        "Faction": "faction",
        "Damage": "damage",
        "Damage Type": "damage_type",
        "Range": "range",
        "Rate of Fire": "rate_of_fire",
        "Magazine Size": "magazine_size",
        "Reload Time": "reload_time",
        "Weight": "weight",
        "Equipment Slot": "equipment_slot",
        "Ammunition": "ammunition",
        "Fire Rate": "fire_rate",
        "Firing Mode": "firing_mode",
        "Hit Points": "hitpoints",
        "Hitpoints": "hitpoints",
        "HP": "hp",
        "Explosive Damage": "explosive_damage",
        "AP Damage": "ap_damage",
        "Penetration Modifier": "penetration_modifier",
        "Inner Radius": "inner_radius",
        "Outer Radius": "outer_radius",
        "Storage Capacity": "storage_capacity",
        "Production Site": "production_site",
        "Production Cost": "production_cost_raw",
        "Package Size": "package_size",
        "Fuel Capacity": "fuel_capacity",
        "Intel Icon": "intel_icon",
    }
    return mapping.get(label, re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_"))


def wiki_field_label(key: str, language: str | None = None) -> str:
    labels = WIKI_KEY_LABELS_BY_LANGUAGE.get(normalize_language(language), WIKI_KEY_LABELS_BY_LANGUAGE["pt"])
    if key in labels:
        return labels[key]
    return " ".join(part.capitalize() for part in str(key or "").split("_") if part)


def translate_wiki_value(value: Any, language: str | None = None) -> str:
    text = clean_wiki_text(value)
    if not text:
        return ""
    code = normalize_language(language)
    translations = WIKI_VALUE_TRANSLATIONS_BY_LANGUAGE.get(code, WIKI_VALUE_TRANSLATIONS_BY_LANGUAGE["pt"])
    if text in translations:
        return translations[text]
    translated = text
    for source, target in sorted(translations.items(), key=lambda item: -len(item[0])):
        translated = re.sub(rf"\b{re.escape(source)}\b", target, translated)
    fallback_words = WIKI_FALLBACK_WORDS.get(code, WIKI_FALLBACK_WORDS["pt"])
    translated = re.sub(r"\bbelow\b", fallback_words["below"], translated, flags=re.I)
    translated = re.sub(r"\bhealth\b", fallback_words["health"], translated, flags=re.I)
    return translated


def wiki_section_label(value: Any, language: str | None = None) -> str:
    text = clean_wiki_text(value)
    return translate_wiki_value(text, language) or text


def wiki_title_candidates(page_title: str) -> list[str]:
    raw = clean_wiki_text(page_title)
    candidates = [raw]
    cleaned = raw
    patterns = (
        r"\s+stock$",
        r"\s+stockpile$",
        r"\s+crated\s+stock$",
        r"\s+crate\s+stock$",
        r"\s+crated$",
        r"\s+crate$",
        r"\s+crates$",
        r"\s+packed$",
        r"\s+packaged$",
    )
    changed = True
    while changed:
        changed = False
        for pattern in patterns:
            next_value = re.sub(pattern, "", cleaned, flags=re.I).strip()
            if next_value != cleaned:
                cleaned = next_value
                changed = True
    if cleaned and cleaned != raw:
        candidates.append(cleaned)
    no_parentheses = re.sub(r"\s*\([^)]*\)\s*", " ", cleaned).strip()
    if no_parentheses and no_parentheses not in candidates:
        candidates.append(no_parentheses)
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def cache_wiki_image(image_url: str, page_title: str) -> str:
    url = clean_wiki_text(image_url)
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        suffix = Path(parsed.path).suffix.lower()
        if suffix not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            suffix = ".png"
        cache_dir = user_data_dir() / "wiki_images"
        cache_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(f"{page_title}|{url}".encode("utf-8", errors="ignore")).hexdigest()[:16]
        target = cache_dir / f"{digest}{suffix}"
        if not target.exists() or target.stat().st_size <= 0:
            request = urllib.request.Request(url, headers={"User-Agent": "FELBApp/1.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                target.write_bytes(response.read())
        return file_url(target)
    except Exception:
        return url


def extract_wiki_infobox(page_html: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    aside_match = re.search(
        r"<aside\b(?=[^>]*\bportable-infobox\b)[^>]*>(.*?)</aside>",
        page_html,
        flags=re.S | re.I,
    )
    if not aside_match:
        return result
    infobox = aside_match.group(1)

    title_match = re.search(
        r"<[^>]*class=(?:\"[^\"]*\bpi-title\b[^\"]*\"|'[^']*\bpi-title\b[^']*'|[^\s>]*\bpi-title\b[^\s>]*)[^>]*>(.*?)</[^>]+>",
        infobox,
        flags=re.S | re.I,
    )
    if title_match:
        result["name"] = strip_wiki_html(title_match.group(1))

    image_match = re.search(
        r"<img\b[^>]*\b(?:data-src|src)=(?:\"([^\"]+)\"|'([^']+)'|([^\s>]+))",
        infobox,
        flags=re.S | re.I,
    )
    if image_match:
        src = next((group for group in image_match.groups() if group), "")
        result["image"] = urllib.parse.urljoin(FOXHOLE_WIKI_BASE_URL, html.unescape(src))
    else:
        srcset_match = re.search(r"<img\b[^>]*\bsrcset=(?:\"([^\"]+)\"|'([^']+)')", infobox, flags=re.S | re.I)
        if srcset_match:
            srcset = next((group for group in srcset_match.groups() if group), "")
            src = clean_wiki_text(srcset.split(",", 1)[0].split(" ", 1)[0])
            result["image"] = urllib.parse.urljoin(FOXHOLE_WIKI_BASE_URL, html.unescape(src))

    label_pattern = re.compile(
        r"<[^>]*class=(?:\"[^\"]*\bpi-data-label\b[^\"]*\"|'[^']*\bpi-data-label\b[^']*'|[^\s>]*\bpi-data-label\b[^\s>]*)[^>]*>(.*?)</[^>]+>",
        flags=re.S | re.I,
    )
    value_pattern = re.compile(
        r"<[^>]*class=(?:\"[^\"]*\bpi-data-value\b[^\"]*\"|'[^']*\bpi-data-value\b[^']*'|[^\s>]*\bpi-data-value\b[^\s>]*)[^>]*>(.*?)</[^>]+>",
        flags=re.S | re.I,
    )
    fields: list[dict[str, str]] = []
    for label_match in label_pattern.finditer(infobox):
        next_label = label_pattern.search(infobox, label_match.end())
        block_end = next_label.start() if next_label else len(infobox)
        block = infobox[label_match.start() : block_end]
        value_match = re.search(value_pattern, block)
        if not value_match:
            continue
        label = strip_wiki_html(label_match.group(1))
        value = strip_wiki_html(value_match.group(1))
        if label and value:
            key = normalize_wiki_key(label)
            header_matches = list(
                re.finditer(
                    r"<[^>]*class=(?:\"[^\"]*\bpi-header\b[^\"]*\"|'[^']*\bpi-header\b[^']*'|[^\s>]*\bpi-header\b[^\s>]*)[^>]*>(.*?)</[^>]+>",
                    infobox[: label_match.start()],
                    flags=re.S | re.I,
                )
            )
            group = strip_wiki_html(header_matches[-1].group(1)) if header_matches else ""
            fields.append({"key": key, "label": label, "value": value, "group": group})
            if key not in result:
                result[key] = value
    result["fields"] = fields
    return result


def extract_wiki_intro(page_html: str) -> str:
    cleaned = re.sub(r"<aside\b.*?</aside>", " ", page_html, flags=re.S | re.I)
    cleaned = re.sub(r"<table\b.*?</table>", " ", cleaned, flags=re.S | re.I)
    cleaned = re.sub(r"<div\b[^>]*(?:id=\"toc\"|class=\"[^\"]*toc[^\"]*\")[^>]*>.*?</div>", " ", cleaned, flags=re.S | re.I)
    cleaned = re.sub(r"<span\b[^>]*class=\"[^\"]*\bmw-editsection\b[^\"]*\"[^>]*>.*?</span>", " ", cleaned, flags=re.S | re.I)
    for paragraph in re.findall(r"<p\b[^>]*>(.*?)</p>", cleaned, flags=re.S | re.I):
        text = strip_wiki_html(paragraph)
        if len(text) > 24:
            return text
    return ""


def extract_wiki_sections(page_html: str, sections: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    allowed = {
        "Description",
        "Usage",
        "Production",
        "Storage",
        "Tactics",
        "Notes",
        "Variants",
        "Trivia",
        "Update History",
    }
    heading_pattern = re.compile(
        r"<h([23])\b[^>]*>\s*<span\b[^>]*class=(?:\"[^\"]*\bmw-headline\b[^\"]*\"|'[^']*\bmw-headline\b[^']*')[^>]*\bid=(?:\"([^\"]+)\"|'([^']+)')[^>]*>(.*?)</span>.*?</h\1>",
        flags=re.S | re.I,
    )
    matches = list(heading_pattern.finditer(page_html))
    rows: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        title = strip_wiki_html(match.group(4))
        if title not in allowed:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(page_html)
        body = strip_wiki_block(page_html[match.end() : end])
        if len(body) > 1200:
            body = body[:1200].rsplit("\n", 1)[0].strip() or body[:1200].strip()
        if body:
            rows.append({"title": title, "body": body})
    return rows[:8]


def normalize_wiki_categories(categories: Any) -> list[str]:
    rows = categories if isinstance(categories, list) else []
    values: list[str] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        category = clean_wiki_text(item.get("category") or item.get("*") or "")
        category = category.replace("_", " ")
        if category and not category.startswith("Pages "):
            values.append(category)
    return list(dict.fromkeys(values))[:8]


def extract_wiki_production(page_html: str) -> list[dict[str, str]]:
    production_pos = page_html.find('id="Production"')
    if production_pos < 0:
        production_pos = page_html.find("id='Production'")
    if production_pos < 0:
        production_pos = page_html.find("id=Production")
    if production_pos < 0:
        return []

    table_match = re.search(
        r"<table\b(?=[^>]*\bwikitable\b)[^>]*>(.*?)</table>",
        page_html[production_pos:],
        flags=re.S | re.I,
    )
    if not table_match:
        return []

    rows: list[dict[str, str]] = []
    for row_match in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", table_match.group(1), flags=re.S | re.I):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row_match.group(1), flags=re.S | re.I)
        if len(cells) < 4:
            continue
        site = strip_wiki_html(cells[0])
        input_text = strip_wiki_html(cells[1])
        output = strip_wiki_html(cells[2])
        time_text = strip_wiki_html(cells[-1])
        if site or input_text or output or time_text:
            rows.append({"site": site, "input": input_text, "output": output, "time": time_text})
    return rows[:8]


def fetch_wiki_page_payload(page_title: str) -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {
            "action": "parse",
            "page": page_title,
            "prop": "text|categories|sections|displaytitle",
            "format": "json",
            "formatversion": "2",
            "origin": "*",
        }
    )
    request = urllib.request.Request(
        f"{FOXHOLE_WIKI_API_URL}?{params}",
        headers={"User-Agent": "FELBApp/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))

    if isinstance(payload, dict) and payload.get("error"):
        info = payload.get("error") or {}
        raise RuntimeError(str(info.get("info") or info.get("code") or "Wiki page not found."))

    page = payload.get("parse") if isinstance(payload, dict) else {}
    page_html = str((page or {}).get("text") or "")
    if not page_html:
        raise RuntimeError("Wiki page returned no content.")
    return page if isinstance(page, dict) else {"text": page_html}


def fetch_wiki_page_html(page_title: str) -> str:
    return str(fetch_wiki_page_payload(page_title).get("text") or "")


def search_wiki_page_title(query: str) -> str:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": "1",
            "format": "json",
            "formatversion": "2",
            "origin": "*",
        }
    )
    request = urllib.request.Request(
        f"{FOXHOLE_WIKI_API_URL}?{params}",
        headers={"User-Agent": "FELBApp/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    rows = ((payload.get("query") or {}).get("search") or []) if isinstance(payload, dict) else []
    if rows and isinstance(rows[0], dict):
        return clean_wiki_text(rows[0].get("title"))
    return ""


def search_wiki_page_titles(query: str, limit: int = 6) -> list[str]:
    raw = clean_wiki_text(query)
    if len(raw) < 3:
        return []
    params = urllib.parse.urlencode(
        {
            "action": "opensearch",
            "search": raw,
            "limit": str(max(1, min(10, limit))),
            "namespace": "0",
            "format": "json",
            "origin": "*",
        }
    )
    request = urllib.request.Request(f"{FOXHOLE_WIKI_API_URL}?{params}", headers={"User-Agent": APP_USER_AGENT})
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    titles = payload[1] if isinstance(payload, list) and len(payload) > 1 and isinstance(payload[1], list) else []
    return [clean_wiki_text(title) for title in titles if clean_wiki_text(title)]


def fetch_wiki_item_info(page_title: str) -> dict[str, Any]:
    original_title = clean_wiki_text(page_title)
    candidates = wiki_title_candidates(original_title)
    last_error: Exception | None = None
    resolved_title = candidates[0] if candidates else original_title
    page_html = ""
    page_payload: dict[str, Any] = {}
    for candidate in candidates:
        try:
            resolved_title = candidate
            page_payload = fetch_wiki_page_payload(candidate)
            page_html = str(page_payload.get("text") or "")
            break
        except Exception as exc:
            last_error = exc
    if not page_html:
        search_query = candidates[-1] if candidates else original_title
        fallback_title = search_wiki_page_title(search_query)
        if not fallback_title:
            if last_error:
                raise last_error
            raise RuntimeError("Wiki page not found.")
        resolved_title = fallback_title
        page_payload = fetch_wiki_page_payload(resolved_title)
        page_html = str(page_payload.get("text") or "")

    item = extract_wiki_infobox(page_html)
    item["name"] = clean_wiki_text(item.get("name") or page_payload.get("title") or resolved_title)
    item["display_title"] = strip_wiki_html(page_payload.get("displaytitle") or "")
    item["description"] = extract_wiki_intro(page_html)
    item["production"] = extract_wiki_production(page_html)
    item["sections"] = extract_wiki_sections(page_html, page_payload.get("sections") if isinstance(page_payload.get("sections"), list) else [])
    item["categories"] = normalize_wiki_categories(page_payload.get("categories"))
    item["source_url"] = f"{FOXHOLE_WIKI_BASE_URL}/wiki/{urllib.parse.quote(resolved_title.replace(' ', '_'))}"
    if item.get("image"):
        item["remote_image"] = item["image"]
        item["image"] = cache_wiki_image(str(item.get("image") or ""), resolved_title)
    return item
















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
                "regiment": str(author.get("regiment") or message.get("regiment") or ""),
                "role": normalize_panel_role(
                    author.get("role") or message.get("role"),
                    int_or_none(
                        (author.get("panelAccess") or {}).get("accessLevel")
                        if isinstance(author.get("panelAccess"), dict)
                        else author.get("panelAccessLevel") or author.get("accessLevel")
                    )
                ),
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
    started = time.monotonic()
    data = None
    headers = {"Accept": "application/json", "User-Agent": APP_USER_AGENT, "X-App-Version": APP_VERSION}
    if payload is not None:
        if isinstance(payload, dict):
            payload = {**payload, "app": APP_TITLE, "appVersion": APP_VERSION, "app_version": APP_VERSION}
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
    debug_log("http", "request", {
        "method": method,
        "url": request.full_url,
        "headers": headers,
        "payload": payload,
        "timeout": timeout,
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(body) if body else {}
            debug_log("http", "response", {
                "method": method,
                "url": request.full_url,
                "status": getattr(response, "status", None),
                "durationMs": round((time.monotonic() - started) * 1000, 1),
                "body": parsed,
            })
            return parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        safe_body = redact_http_error_body(body)
        debug_log("http", "error", {
            "method": method,
            "url": request.full_url,
            "status": exc.code,
            "reason": exc.reason,
            "durationMs": round((time.monotonic() - started) * 1000, 1),
            "body": safe_body,
        })
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {safe_body or 'empty response'}") from exc
    except Exception as exc:
        debug_log("http", "exception", {
            "method": method,
            "url": request.full_url,
            "durationMs": round((time.monotonic() - started) * 1000, 1),
            "error": repr(exc),
        })
        raise


def http_json_url(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: Any | None = None,
    form: dict[str, str] | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    started = time.monotonic()
    data = None
    headers = {"Accept": "application/json", "User-Agent": APP_USER_AGENT, "X-App-Version": APP_VERSION}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    debug_log("http", "request", {
        "method": method,
        "url": url,
        "headers": headers,
        "payload": payload,
        "form": form,
        "timeout": timeout,
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(body) if body else {}
            debug_log("http", "response", {
                "method": method,
                "url": url,
                "status": getattr(response, "status", None),
                "durationMs": round((time.monotonic() - started) * 1000, 1),
                "body": parsed,
            })
            return parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        safe_body = redact_http_error_body(body)
        debug_log("http", "error", {
            "method": method,
            "url": url,
            "status": exc.code,
            "reason": exc.reason,
            "durationMs": round((time.monotonic() - started) * 1000, 1),
            "body": safe_body,
        })
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {safe_body or 'empty response'}") from exc
    except Exception as exc:
        debug_log("http", "exception", {
            "method": method,
            "url": url,
            "durationMs": round((time.monotonic() - started) * 1000, 1),
            "error": repr(exc),
        })
        raise


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
        if auth_url:
            try:
                import webbrowser

                opened = webbrowser.open(auth_url, new=2)
            except Exception:
                opened = False
            if not opened and not QDesktopServices.openUrl(QUrl(auth_url)):
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









