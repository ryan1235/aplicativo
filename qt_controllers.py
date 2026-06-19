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
from typing import Any
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

from PySide6.QtNetwork import QNetworkAccessManager
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
APP_VERSION = "2.0.3"
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
FOXHOLE_WIKI_BASE_URL = "https://foxhole.wiki.gg"
FOXHOLE_WIKI_API_URL = f"{FOXHOLE_WIKI_BASE_URL}/api.php"
DISCORD_DEFAULT_REDIRECT_PORT = 53624
DISCORD_DEFAULT_REDIRECT_PATH = "/discord/callback"
DISCORD_DEFAULT_CLIENT_ID = "1512509453067358489"
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
            if key_text in {"token", "accesstoken", "access_token", "refresh_token", "authorization", "client_secret"}:
                text_value = str(item or "")
                redacted[str(key)] = f"<redacted len={len(text_value)}>"
            else:
                redacted[str(key)] = redact_login_debug(item)
        return redacted
    if isinstance(value, list):
        return [redact_login_debug(item) for item in value]
    return value


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
    for csv_path in (resource_dir() / "locations.csv", BASE_DIR / "locations.csv"):
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


def format_relative_time(value: Any) -> str:
    parsed = parse_stockpile_datetime(value)
    if parsed is None:
        return ""
    seconds = max(0, int((datetime.now().astimezone() - parsed).total_seconds()))
    if seconds < 60:
        return "Agora"
    minutes = seconds // 60
    if minutes < 60:
        return f"Há {minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"Há {hours}h"
    days = hours // 24
    if days < 30:
        return f"Há {days}d"
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
        if len(items) == len(self._items):
            self._items = items
            if items:
                self.dataChanged.emit(self.index(0, 0), self.index(len(items) - 1, 0), list(self._role_names.keys()))
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
            "identifyItem": "identify_item",
            "notifications": "notificacoes",
            "settings": "configuracoes",
            "personalization": "configuracoes",
        }
        self.navItems = DictListModel(["key", "labelKey", "icon", "section", "searchText"], self)
        self.navItems.set_items(self._nav_items())
        self._foxhole_timer = QTimer(self)
        self._foxhole_timer.timeout.connect(self.refreshFoxholeStatus)
        self._foxhole_timer.start(5000)
        self.refreshFoxholeStatus()

    @Slot(str)
    def openAdminPanel(self, token: str) -> None:
        """Verifica o acesso na API antes de abrir o painel administrativo."""
        token = str(token or "").strip()
        if not token:
            self._pending_admin_panel_token = ""
            self.showStartupDialog(
                kind="error",
                title="Acesso Negado",
                subtitle="Sem autenticação",
                body="Você precisa estar logado com o Discord para acessar o painel.",
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
                    reason = "Acesso ao painel negado."
                    if access_level in (0, 1):
                        reason = f"Seu nível de acesso ({access_level}) não permite entrar no painel."
                    elif panel_access:
                        reason = f"Nível mínimo para o painel: {panel_access.get('requiredAccessLevel', PANEL_REQUIRED_ACCESS_LEVEL)}."
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
            title="Acesso Negado",
            subtitle="Sem autenticação",
            body="Você precisa estar logado com o Discord para acessar o painel.",
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
            params = urllib.parse.urlencode({"token": token or "", "api": api_hint})
            url_str = f"http://localhost:3334/?{params}"
            success = QDesktopServices.openUrl(QUrl(url_str))
            if not success:
                import webbrowser
                webbrowser.open(url_str)
        elif status == "error":
            self.showStartupDialog(
                kind="error",
                title="Acesso Negado ao Painel",
                subtitle="Permissão insuficiente",
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
        self._current_page = page
        self.currentPageChanged.emit()

    @Slot(bool)
    def setSidebarOpen(self, open_: bool) -> None:
        open_ = bool(open_)
        if open_ == self._sidebar_open:
            return
        self._sidebar_open = open_
        self._app_settings()["sidebar_open"] = open_
        save_settings(self.settings)
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
            {"key": "itemSearch", "labelKey": "item_search.nav", "icon": "search", "section": "tools"},
            {"key": "identifyItem", "labelKey": "identify.nav", "icon": "target", "section": "tools"},
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
        self.personalization = load_personalization_settings(
            legacy_theme=self.settings.get("app", {}).get("theme"),
            legacy_colorblind=self.settings.get("app", {}).get("colorblind_mode_enabled"),
        )
        self._revision = 0
        self._status = ""

        ensure_startup_enabled_by_default(self.settings)

    def _app_settings(self) -> dict[str, Any]:
        return self.settings.setdefault("app", {})

    def _notification_settings(self) -> dict[str, Any]:
        return self.settings.setdefault("notifications", {})

    def _personalization_settings(self) -> dict[str, Any]:
        if not isinstance(self.personalization, dict):
            self.personalization = load_personalization_settings()
        self.personalization.setdefault("colorblind_mode_enabled", False)
        self.personalization.setdefault("colorblind_profile", "none")
        self.personalization.setdefault("sidebar_width", 286)
        return self.personalization

    def _theme_settings(self) -> dict[str, Any]:
        personalization = self._personalization_settings()
        theme = personalization.setdefault("theme", {})
        if not isinstance(theme, dict):
            theme = {}
            personalization["theme"] = theme
        theme.setdefault("preset", "coalition")
        custom = theme.setdefault("custom", {})
        if not isinstance(custom, dict):
            custom = {}
            theme["custom"] = custom
        for key, value in UI_THEME_CUSTOM_DEFAULT.items():
            custom.setdefault(key, value)
        return theme

    def _save(self) -> None:
        save_settings(self.settings)
        self._revision += 1
        self.changed.emit()

    def _save_personalization(self) -> None:
        save_personalization_settings(self.personalization)
        self._revision += 1
        self.changed.emit()

    def _app_bool(self, key: str, default: bool = True) -> bool:
        return bool(self._app_settings().get(key, default))

    def _ui_palette(self) -> dict[str, str]:
        preset = self.themePreset
        colorblind_profile = self.colorblindProfile
        if bool(self._personalization_settings().get("colorblind_mode_enabled", False)):
            preset = "accessible"
        if preset == "custom":
            custom = self._theme_settings().get("custom", {})
            palette = {
                key: self._sanitize_hex_color(custom.get(key), str(UI_THEME_CUSTOM_DEFAULT[key]))
                for key in UI_THEME_COLOR_KEYS
            }
            palette["gradient_enabled"] = bool(custom.get("gradient_enabled", UI_THEME_CUSTOM_DEFAULT["gradient_enabled"]))
            palette["button_style"] = self._sanitize_button_style(custom.get("button_style"))
            palette["card_radius"] = self._sanitize_card_radius(custom.get("card_radius"))
            return palette
        source = UI_THEME_PRESETS.get(preset, UI_THEME_PRESETS["coalition"])
        palette = {key: source.get(key, fallback) for key, fallback in UI_THEME_CUSTOM_DEFAULT.items()}
        if preset == "accessible":
            palette.update(COLORBLIND_THEME_OVERRIDES.get(colorblind_profile, COLORBLIND_THEME_OVERRIDES["unsure"]))
        return palette

    @staticmethod
    def _sanitize_hex_color(value: Any, fallback: str) -> str:
        text = str(value or "").strip()
        if re.fullmatch(r"#[0-9a-fA-F]{6}", text):
            return text.lower()
        if re.fullmatch(r"[0-9a-fA-F]{6}", text):
            return f"#{text.lower()}"
        return fallback

    @staticmethod
    def _sanitize_button_style(value: Any) -> str:
        text = str(value or "").strip()
        return text if text in UI_THEME_BUTTON_STYLES else "solid"

    @staticmethod
    def _sanitize_card_radius(value: Any) -> int:
        try:
            radius = int(value)
        except (TypeError, ValueError):
            return 8
        return radius if str(radius) in UI_THEME_CARD_RADIUS_OPTIONS else 8

    @staticmethod
    def _hex_to_rgb(value: Any, fallback: str = "#5eead4") -> tuple[int, int, int]:
        text = SettingsController._sanitize_hex_color(value, fallback).lstrip("#")
        return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)

    @staticmethod
    def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        return "#{:02x}{:02x}{:02x}".format(
            max(0, min(255, int(rgb[0]))),
            max(0, min(255, int(rgb[1]))),
            max(0, min(255, int(rgb[2]))),
        )

    @classmethod
    def _mix_color(cls, left: Any, right: Any, amount: float) -> str:
        amount = max(0.0, min(1.0, float(amount)))
        left_rgb = cls._hex_to_rgb(left)
        right_rgb = cls._hex_to_rgb(right)
        return cls._rgb_to_hex(tuple(round(left_rgb[i] * (1.0 - amount) + right_rgb[i] * amount) for i in range(3)))

    @classmethod
    def _shift_color(cls, value: Any, hue_shift: float = 0.0, saturation: float = 1.0, lightness: float = 1.0) -> str:
        r, g, b = cls._hex_to_rgb(value)
        hue, lum, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        hue = (hue + hue_shift) % 1.0
        lum = max(0.03, min(0.96, lum * lightness))
        sat = max(0.08, min(1.0, sat * saturation))
        nr, ng, nb = colorsys.hls_to_rgb(hue, lum, sat)
        return cls._rgb_to_hex((round(nr * 255), round(ng * 255), round(nb * 255)))

    @classmethod
    def _theme_from_accent(cls, accent: Any, support: Any | None = None, warm: Any | None = None) -> dict[str, Any]:
        accent_color = cls._sanitize_hex_color(accent, UI_THEME_CUSTOM_DEFAULT["accent"])
        support_color = cls._sanitize_hex_color(support, cls._shift_color(accent_color, 0.28, 0.9, 0.95))
        warm_color = cls._sanitize_hex_color(warm, cls._shift_color(accent_color, 0.12, 1.05, 1.08))
        background = cls._shift_color(accent_color, -0.03, 0.45, 0.18)
        surface = cls._mix_color(background, "#ffffff", 0.055)
        panel = cls._mix_color(background, accent_color, 0.24)
        return {
            "accent": accent_color,
            "accent_hover": support_color,
            "accent_panel": panel,
            "success": support_color,
            "warning": warm_color,
            "warning_text": "#fff7ed",
            "background": background,
            "surface": surface,
            "text": "#f8fafc",
            "text_inverse": "#041014",
            "secondary_text": "#c7d7ed",
            "muted_text": cls._mix_color("#94a3b8", accent_color, 0.14),
            "disabled_text": "#7f93ad",
            "border": cls._mix_color(surface, accent_color, 0.36),
            "surface_alt": cls._mix_color(background, "#ffffff", 0.04),
            "surface_raised": cls._mix_color(background, accent_color, 0.14),
            "control": cls._mix_color(background, accent_color, 0.28),
            "control_hover": cls._mix_color(background, accent_color, 0.42),
            "danger": "#fb7185",
            "danger_hover": "#e11d48",
            "danger_panel": cls._mix_color(background, "#fb7185", 0.22),
            "info": cls._shift_color(accent_color, 0.08, 0.95, 1.1),
            "scrim": "#000000",
            "gradient_start": background,
            "gradient_end": cls._mix_color(background, support_color, 0.18),
            "gradient_enabled": True,
            "button_style": secrets.choice(tuple(UI_THEME_BUTTON_STYLES.keys())),
            "card_radius": secrets.choice(tuple(int(key) for key in UI_THEME_CARD_RADIUS_OPTIONS.keys())),
        }

    def _palette_for_preview(self, preset: str) -> dict[str, str]:
        if preset == "custom":
            custom = self._theme_settings().get("custom", {})
            palette = {
                key: self._sanitize_hex_color(custom.get(key), str(UI_THEME_CUSTOM_DEFAULT[key]))
                for key in UI_THEME_COLOR_KEYS
            }
            palette["gradient_enabled"] = bool(custom.get("gradient_enabled", UI_THEME_CUSTOM_DEFAULT["gradient_enabled"]))
            palette["button_style"] = self._sanitize_button_style(custom.get("button_style"))
            palette["card_radius"] = self._sanitize_card_radius(custom.get("card_radius"))
            return palette
        palette = UI_THEME_PRESETS.get(preset, UI_THEME_PRESETS["coalition"])
        return {key: palette.get(key, fallback) for key, fallback in UI_THEME_CUSTOM_DEFAULT.items()}

    def _activate_custom_from_current_palette(self) -> tuple[dict[str, Any], bool]:
        theme = self._theme_settings()
        custom = theme.setdefault("custom", {})
        changed = theme.get("preset") != "custom" or bool(self._personalization_settings().get("colorblind_mode_enabled", False))
        if theme.get("preset") != "custom":
            current = self._ui_palette()
            custom = {
                key: current.get(key, UI_THEME_CUSTOM_DEFAULT[key])
                for key in UI_THEME_COLOR_KEYS
            }
            custom["gradient_enabled"] = bool(current.get("gradient_enabled", UI_THEME_CUSTOM_DEFAULT["gradient_enabled"]))
            custom["button_style"] = self._sanitize_button_style(current.get("button_style"))
            custom["card_radius"] = self._sanitize_card_radius(current.get("card_radius"))
            theme["custom"] = custom
        theme["preset"] = "custom"
        self._personalization_settings()["colorblind_mode_enabled"] = False
        return custom, changed

    @Property(int, notify=changed)
    def revision(self) -> int:
        return self._revision

    @Property(str, notify=changed)
    def closeAction(self) -> str:
        action = str(self._app_settings().get("close_action", "ask"))
        return action if action in VALID_CLOSE_ACTIONS else "ask"

    @Property(bool, notify=changed)
    def startWithWindows(self) -> bool:
        if os.name == "nt":
            return startup_registry_matches(self.settings)
        return False

    @Property(str, notify=changed)
    def startupCommand(self) -> str:
        return startup_command(self.settings)

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property("QVariant", notify=changed)
    def themePresets(self) -> list[dict[str, Any]]:
        current = self.themePreset
        return [
            {
                "key": key,
                "labelKey": str(UI_THEME_PRESETS[key]["labelKey"]),
                "descriptionKey": str(UI_THEME_PRESETS[key]["descriptionKey"]),
                "accent": str(self._palette_for_preview(key)["accent"]),
                "accentPanel": str(self._palette_for_preview(key)["accent_panel"]),
                "success": str(self._palette_for_preview(key)["success"]),
                "warning": str(self._palette_for_preview(key)["warning"]),
                "background": str(self._palette_for_preview(key)["background"]),
                "surface": str(self._palette_for_preview(key)["surface"]),
                "border": str(self._palette_for_preview(key)["border"]),
                "active": key == current,
            }
            for key in UI_THEME_ORDER
        ]

    @Property("QVariant", constant=True)
    def accentPaletteOptions(self) -> list[dict[str, str]]:
        return [
            {
                "key": key,
                "label": str(value["label"]),
                "accent": str(value["accent"]),
                "support": str(value["support"]),
                "warm": str(value["warm"]),
            }
            for key, value in UI_THEME_ACCENT_PALETTES.items()
        ]

    @Property("QVariant", notify=changed)
    def colorblindProfileOptions(self) -> list[dict[str, Any]]:
        current = self.colorblindProfile
        return [
            {
                "key": key,
                "labelKey": str(COLORBLIND_PROFILE_OPTIONS[key]["labelKey"]),
                "descriptionKey": str(COLORBLIND_PROFILE_OPTIONS[key]["descriptionKey"]),
                "active": key == current and (key == "none" or self.colorblindModeEnabled),
            }
            for key in COLORBLIND_PROFILE_ORDER
        ]

    @Property("QVariant", constant=True)
    def themeColorFields(self) -> list[dict[str, str]]:
        return [{"key": key, "labelKey": label_key} for key, label_key in UI_THEME_COLOR_FIELDS.items()]

    @Property("QVariant", constant=True)
    def buttonStyleOptions(self) -> list[dict[str, str]]:
        return [{"key": key, "labelKey": label_key} for key, label_key in UI_THEME_BUTTON_STYLES.items()]

    @Property("QVariant", constant=True)
    def cardRadiusOptions(self) -> list[dict[str, str]]:
        return [{"key": key, "labelKey": label_key} for key, label_key in UI_THEME_CARD_RADIUS_OPTIONS.items()]

    @Property(str, notify=changed)
    def themePreset(self) -> str:
        preset = str(self._theme_settings().get("preset") or "coalition")
        if bool(self._personalization_settings().get("colorblind_mode_enabled", False)):
            return "accessible"
        return preset if preset in UI_THEME_PRESETS else "coalition"

    @Property(str, notify=changed)
    def colorblindProfile(self) -> str:
        profile = str(self._personalization_settings().get("colorblind_profile") or "none").strip()
        return profile if profile in COLORBLIND_PROFILE_OPTIONS else "none"

    @Property(bool, notify=changed)
    def customThemeEnabled(self) -> bool:
        return self.themePreset == "custom"

    @Property(str, notify=changed)
    def accentColor(self) -> str:
        return self._ui_palette()["accent"]

    @Property(str, notify=changed)
    def accentHoverColor(self) -> str:
        return self._ui_palette()["accent_hover"]

    @Property(str, notify=changed)
    def accentPanelColor(self) -> str:
        return self._ui_palette()["accent_panel"]

    @Property(str, notify=changed)
    def successColor(self) -> str:
        return self._ui_palette()["success"]

    @Property(str, notify=changed)
    def warningColor(self) -> str:
        return self._ui_palette()["warning"]

    @Property(str, notify=changed)
    def warningTextColor(self) -> str:
        return self._ui_palette()["warning_text"]

    @Property(str, notify=changed)
    def backgroundColor(self) -> str:
        return str(self._ui_palette()["background"])

    @Property(str, notify=changed)
    def surfaceColor(self) -> str:
        return str(self._ui_palette()["surface"])

    @Property(str, notify=changed)
    def textColor(self) -> str:
        return str(self._ui_palette()["text"])

    @Property(str, notify=changed)
    def textInverseColor(self) -> str:
        return str(self._ui_palette()["text_inverse"])

    @Property(str, notify=changed)
    def secondaryTextColor(self) -> str:
        return str(self._ui_palette()["secondary_text"])

    @Property(str, notify=changed)
    def mutedTextColor(self) -> str:
        return str(self._ui_palette()["muted_text"])

    @Property(str, notify=changed)
    def disabledTextColor(self) -> str:
        return str(self._ui_palette()["disabled_text"])

    @Property(str, notify=changed)
    def borderColor(self) -> str:
        return str(self._ui_palette()["border"])

    @Property(str, notify=changed)
    def surfaceAltColor(self) -> str:
        return str(self._ui_palette()["surface_alt"])

    @Property(str, notify=changed)
    def surfaceRaisedColor(self) -> str:
        return str(self._ui_palette()["surface_raised"])

    @Property(str, notify=changed)
    def controlColor(self) -> str:
        return str(self._ui_palette()["control"])

    @Property(str, notify=changed)
    def controlHoverColor(self) -> str:
        return str(self._ui_palette()["control_hover"])

    @Property(str, notify=changed)
    def dangerColor(self) -> str:
        return str(self._ui_palette()["danger"])

    @Property(str, notify=changed)
    def dangerHoverColor(self) -> str:
        return str(self._ui_palette()["danger_hover"])

    @Property(str, notify=changed)
    def dangerPanelColor(self) -> str:
        return str(self._ui_palette()["danger_panel"])

    @Property(str, notify=changed)
    def infoColor(self) -> str:
        return str(self._ui_palette()["info"])

    @Property(str, notify=changed)
    def scrimColor(self) -> str:
        return str(self._ui_palette()["scrim"])

    @Property(str, notify=changed)
    def gradientStartColor(self) -> str:
        return str(self._ui_palette()["gradient_start"])

    @Property(str, notify=changed)
    def gradientEndColor(self) -> str:
        return str(self._ui_palette()["gradient_end"])

    @Property(bool, notify=changed)
    def gradientEnabled(self) -> bool:
        return bool(self._ui_palette()["gradient_enabled"])

    @Property(str, notify=changed)
    def buttonStyle(self) -> str:
        return self._sanitize_button_style(self._ui_palette()["button_style"])

    @Property(int, notify=changed)
    def buttonRadius(self) -> int:
        radius = self.cardRadius
        if self.buttonStyle == "outline":
            return max(4, min(10, radius))
        if self.buttonStyle == "glass":
            return max(8, radius)
        return max(4, min(16, radius))

    @Property(int, notify=changed)
    def cardRadius(self) -> int:
        return self._sanitize_card_radius(self._ui_palette()["card_radius"])

    @Property(bool, notify=changed)
    def colorblindModeEnabled(self) -> bool:
        return bool(self._personalization_settings().get("colorblind_mode_enabled", False))

    @Property(int, notify=changed)
    def sidebarWidth(self) -> int:
        try:
            width = int(self._personalization_settings().get("sidebar_width", 286))
        except (TypeError, ValueError):
            width = 286
        return max(240, min(340, width))

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
        app_settings["startup_user_changed"] = True

        try:
            set_start_with_windows(enabled, self.settings)
        except Exception as exc:
            app_settings["start_with_windows"] = False
            self._status = str(exc)
            self._save()
            return

        app_settings["start_with_windows"] = startup_registry_matches(self.settings) if enabled else False
        app_settings["startup_prompted"] = True
        app_settings["startup_default_applied"] = True
        self._status = ""
        self._save()

    @Slot(bool)
    def setColorblindModeEnabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if self.colorblindModeEnabled == enabled:
            return
        self._personalization_settings()["colorblind_mode_enabled"] = enabled
        if enabled:
            if self.colorblindProfile == "none":
                self._personalization_settings()["colorblind_profile"] = "unsure"
            self._theme_settings()["preset"] = "accessible"
        self._save_personalization()

    @Slot(str)
    def setColorblindProfile(self, profile: str) -> None:
        profile = str(profile or "").strip()
        if profile not in COLORBLIND_PROFILE_OPTIONS:
            return
        personalization = self._personalization_settings()
        enabled = profile != "none"
        if personalization.get("colorblind_profile") == profile and bool(personalization.get("colorblind_mode_enabled", False)) == enabled:
            return
        personalization["colorblind_profile"] = profile
        personalization["colorblind_mode_enabled"] = enabled
        if enabled:
            self._theme_settings()["preset"] = "accessible"
        self._save_personalization()

    @Slot(int)
    def setSidebarWidth(self, width: int) -> None:
        try:
            value = int(width)
        except (TypeError, ValueError):
            return
        value = max(240, min(340, value))
        personalization = self._personalization_settings()
        if int(personalization.get("sidebar_width", 286)) == value:
            return
        personalization["sidebar_width"] = value
        self._save_personalization()

    @Slot(str)
    def setThemePreset(self, preset: str) -> None:
        preset = str(preset or "").strip()
        if preset not in UI_THEME_PRESETS:
            return
        self._personalization_settings()["colorblind_mode_enabled"] = preset == "accessible"
        if preset == "accessible" and self.colorblindProfile == "none":
            self._personalization_settings()["colorblind_profile"] = "unsure"
        theme = self._theme_settings()
        if theme.get("preset") == preset and self.themePreset == preset:
            return
        theme["preset"] = preset
        self._save_personalization()

    @Slot(str, result=str)
    def customThemeColor(self, key: str) -> str:
        key = str(key or "").strip()
        if key not in UI_THEME_COLOR_FIELDS:
            return ""
        fallback = UI_THEME_CUSTOM_DEFAULT.get(key, "#5eead4")
        return self._sanitize_hex_color(self._theme_settings().get("custom", {}).get(key), fallback)

    @Slot(str, str)
    def setCustomThemeColor(self, key: str, value: str) -> None:
        key = str(key or "").strip()
        if key not in UI_THEME_COLOR_FIELDS:
            return
        fallback = UI_THEME_CUSTOM_DEFAULT.get(key, "#5eead4")
        color = self._sanitize_hex_color(value, fallback)
        theme = self._theme_settings()
        theme["preset"] = "custom"
        self._personalization_settings()["colorblind_mode_enabled"] = False
        custom = theme.setdefault("custom", {})
        if custom.get(key) == color and self.themePreset == "custom":
            return
        custom[key] = color
        if key == "accent":
            custom["accent_hover"] = color
        if key == "warning":
            custom["warning_text"] = "#fef3c7"
        self._save_personalization()

    @Slot(bool)
    def setThemeGradientEnabled(self, enabled: bool) -> None:
        custom, activated = self._activate_custom_from_current_palette()
        enabled = bool(enabled)
        if bool(custom.get("gradient_enabled", UI_THEME_CUSTOM_DEFAULT["gradient_enabled"])) == enabled and not activated:
            return
        custom["gradient_enabled"] = enabled
        self._save_personalization()

    @Slot(str)
    def setThemeButtonStyle(self, style: str) -> None:
        style = self._sanitize_button_style(style)
        custom, activated = self._activate_custom_from_current_palette()
        if self._sanitize_button_style(custom.get("button_style")) == style and not activated:
            return
        custom["button_style"] = style
        self._save_personalization()

    @Slot(str)
    def setThemeCardRadius(self, radius: str) -> None:
        value = self._sanitize_card_radius(radius)
        custom, activated = self._activate_custom_from_current_palette()
        if self._sanitize_card_radius(custom.get("card_radius")) == value and not activated:
            return
        custom["card_radius"] = value
        self._save_personalization()

    @Slot(str)
    def applyAccentPalette(self, key: str) -> None:
        key = str(key or "").strip()
        option = UI_THEME_ACCENT_PALETTES.get(key)
        if not option:
            return
        theme = self._theme_settings()
        theme["preset"] = "custom"
        theme["custom"] = self._theme_from_accent(option["accent"], option["support"], option["warm"])
        self._personalization_settings()["colorblind_mode_enabled"] = False
        self._save_personalization()

    @Slot(str)
    def generateThemeFromAccent(self, value: str) -> None:
        accent = self._sanitize_hex_color(value, UI_THEME_CUSTOM_DEFAULT["accent"])
        theme = self._theme_settings()
        theme["preset"] = "custom"
        theme["custom"] = self._theme_from_accent(accent)
        self._personalization_settings()["colorblind_mode_enabled"] = False
        self._save_personalization()

    @Slot()
    def randomizeCustomTheme(self) -> None:
        option = secrets.choice(tuple(UI_THEME_ACCENT_PALETTES.values()))
        hue_shift = (secrets.randbelow(41) - 20) / 360.0
        accent = self._shift_color(option["accent"], hue_shift, 1.0, 1.0)
        support = self._shift_color(option["support"], hue_shift / 2.0, 1.0, 1.0)
        warm = self._shift_color(option["warm"], -hue_shift / 3.0, 1.0, 1.0)
        custom = self._theme_from_accent(accent, support, warm)
        custom["button_style"] = secrets.choice(("solid", "soft", "outline", "glass"))
        custom["card_radius"] = secrets.choice((4, 6, 8, 12, 16))
        custom["gradient_enabled"] = secrets.choice((True, True, False))

        theme = self._theme_settings()
        theme["preset"] = "custom"
        theme["custom"] = custom
        self._personalization_settings()["colorblind_mode_enabled"] = False
        self._save_personalization()

    @Slot()
    def resetCustomTheme(self) -> None:
        theme = self._theme_settings()
        theme["custom"] = dict(UI_THEME_CUSTOM_DEFAULT)
        theme["preset"] = "custom"
        self._personalization_settings()["colorblind_mode_enabled"] = False
        self._save_personalization()

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
    def personalizationPath(self) -> str:
        from personalization_store import PERSONALIZATION_PATH

        return str(PERSONALIZATION_PATH)

    @Slot(result=str)
    def personalizationJson(self) -> str:
        return json.dumps(self.personalization, indent=2, ensure_ascii=False)

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
    DEFAULT_INTERVAL = 0.5
    MODE_KEYS = ("auto", "move", "pilot", "right_hold", "fixed", "artillery")

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
            # Propaga idioma atual do I18nController para o AutoClicker
            try:
                parent_i18n = parent.i18nController if parent is not None and hasattr(parent, "i18nController") else None
                # guarda referência para expor disponibilidade do toggle FR
                self._parent_i18n = parent_i18n
                if parent_i18n is not None:
                    # set initial language and subscribe to changes
                    self.clicker.set_language(parent_i18n.language)
                    self.changed.emit()

                    def _on_i18n_changed() -> None:
                        try:
                            self.clicker.set_language(parent_i18n.language)
                        finally:
                            self.changed.emit()

                    parent_i18n.changed.connect(_on_i18n_changed)
            except Exception:
                pass
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

    def _click_interval(self) -> float:
        data = self._clicker_settings()
        try:
            value = float(data.get("interval", self.DEFAULT_INTERVAL))
        except (TypeError, ValueError):
            value = self.DEFAULT_INTERVAL
        value = round(max(0.03, min(5.0, value)), 2)
        data["interval"] = value
        return value

    def _mode_enabled_settings(self) -> dict[str, bool]:
        data = self._clicker_settings()
        raw = data.get("modes_enabled", {})
        raw = raw if isinstance(raw, dict) else {}
        modes = {key: bool(raw.get(key, True)) for key in self.MODE_KEYS}
        data["modes_enabled"] = modes
        return modes

    def _mode_enabled(self, key: str) -> bool:
        return bool(self._mode_enabled_settings().get(key, True))

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
            self._click_interval(),
        )
        self.clicker.configure_modes_enabled(self._mode_enabled_settings())
        self.clicker.configure_action_hotkeys(
            str(data.get("move_hotkey", "F2")),
            str(data.get("fixed_hotkey", "F6")),
            str(data.get("pilot_hotkey", "F4")),
            str(data.get("artillery_hotkey", "F7")),
            str(data.get("right_hold_hotkey", "F9")),
        )
        self.clicker.shift_enabled = bool(data.get("shift_enabled", False))
        self.clicker.w_doubletap_enabled = bool(data.get("w_doubletap_enabled", False))
        self.clicker.right_doubletap_enabled = bool(data.get("right_doubletap_enabled", False))
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
        # Aplica override para manter W mesmo em FR (toggle disponível apenas para idioma FR)
        try:
            self.clicker.force_w_in_fr = bool(data.get("force_w_in_fr", False))
        except Exception:
            pass

    @Slot(str)
    def _set_status(self, text: str) -> None:
        self._status = text
        self.changed.emit()

    @Property(bool, notify=changed)
    def available(self) -> bool:
        return self._available

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=changed)
    def running(self) -> bool:
        return bool(self.clicker and self.clicker.enabled)

    def _pilot_active(self) -> bool:
        if not self.clicker:
            return False
        return bool(getattr(self.clicker, "w_hold_enabled", False))

    @Property(bool, notify=changed)
    def active(self) -> bool:
        return bool(
            self.clicker
            and (
                bool(getattr(self.clicker, "enabled", False))
                or bool(getattr(self.clicker, "fixed_click_enabled", False))
                or bool(getattr(self.clicker, "move_click_enabled", False))
                or bool(getattr(self.clicker, "artillery_enabled", False))
                or bool(getattr(self.clicker, "right_hold_enabled", False))
                or self._pilot_active()
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
        return self._pilot_active()

    @Property(bool, notify=changed)
    def artilleryRunning(self) -> bool:
        return bool(self.clicker and getattr(self.clicker, "artillery_enabled", False))

    @Property(bool, notify=changed)
    def rightHoldRunning(self) -> bool:
        return bool(self.clicker and getattr(self.clicker, "right_hold_enabled", False))

    @Property(bool, notify=changed)
    def wHoldRunning(self) -> bool:
        return self._pilot_active()

    @Property(bool, notify=changed)
    def wHoldPaused(self) -> bool:
        return bool(self.clicker and getattr(self.clicker, "pilot_w_paused", False))

    @Property(bool, notify=changed)
    def shiftPressed(self) -> bool:
        return bool(self.clicker and getattr(self.clicker, "shift_pressed", False))

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
    def rightHoldHotkey(self) -> str:
        return str(self._clicker_settings().get("right_hold_hotkey", "F9"))

    @Property(str, notify=changed)
    def mouseButton(self) -> str:
        return str(self._clicker_settings().get("mouse_button", "Esquerdo"))

    @Property(float, notify=changed)
    def interval(self) -> float:
        return self._click_interval()

    @Property(bool, notify=changed)
    def autoModeEnabled(self) -> bool:
        return self._mode_enabled("auto")

    @Property(bool, notify=changed)
    def moveModeEnabled(self) -> bool:
        return self._mode_enabled("move")

    @Property(bool, notify=changed)
    def pilotModeEnabled(self) -> bool:
        return self._mode_enabled("pilot")

    @Property(bool, notify=changed)
    def rightHoldModeEnabled(self) -> bool:
        return self._mode_enabled("right_hold")

    @Property(bool, notify=changed)
    def fixedModeEnabled(self) -> bool:
        return self._mode_enabled("fixed")

    @Property(bool, notify=changed)
    def artilleryModeEnabled(self) -> bool:
        return self._mode_enabled("artillery")

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
        if self.clicker.artillery_enabled:
            items.append(f"ART {self.artilleryHotkey}")
        if self.clicker.right_hold_enabled:
            items.append(f"RMB HOLD {self.rightHoldHotkey}")
        if self._pilot_active():
            suffix = " PAUSADO" if getattr(self.clicker, "pilot_w_paused", False) else ""
            wlabel = getattr(self.clicker, "w_hold_label", lambda: "W")()
            items.append(f"{wlabel} HOLD {self.pilotHotkey}{suffix}")
        if self.clicker.shift_enabled:
            items.append("SHIFT ON" if self.clicker.shift_pressed else "SHIFT READY")
        return " | ".join(items) if items else "-"

    @Property(str, notify=changed)
    def overlayPrimaryText(self) -> str:
        if not self.clicker:
            return "Auto Clicker indisponivel"
        if getattr(self.clicker, "w_hold_enabled", False):
            wlabel = getattr(self.clicker, "w_hold_label", lambda: "W")()
            return f"{wlabel} Hold {self.pilotHotkey}: {'pausado no S' if getattr(self.clicker, 'pilot_w_paused', False) else f'segurando {wlabel}'}"
        if getattr(self.clicker, "right_hold_enabled", False):
            return f"Right Hold {self.rightHoldHotkey}: segurando direito"
        if getattr(self.clicker, "artillery_enabled", False):
            return f"Artilharia {self.artilleryHotkey}: R + clique"
        if getattr(self.clicker, "move_click_enabled", False):
            return f"Move-click {self.moveHotkey}: segurando clique"
        if getattr(self.clicker, "fixed_click_enabled", False):
            return f"Fixo {self.fixedHotkey}: clique + slots 1-4"
        if getattr(self.clicker, "enabled", False):
            shift = " + Shift" if getattr(self.clicker, "shift_pressed", False) else ""
            return f"Auto {self.hotkey}: {self.mouseButton} | {self.interval:.1f}s{shift}"
        # Use dynamic W/Z label (respecting FR override)
        wlabel = getattr(self.clicker, "w_hold_label", lambda: "W")()
        return f"{self.hotkey} auto | {self.pilotHotkey} {wlabel} | {self.rightHoldHotkey} direito"

    @Property(str, notify=changed)
    def wHoldLabel(self) -> str:
        """Rótulo dinâmico para o W-Hold (ex.: 'W Hold:' ou 'Z Hold:')."""
        if not self.clicker:
            return "W Hold:"
        wlabel = getattr(self.clicker, "w_hold_label", lambda: "W")()
        return f"{wlabel} Hold:"

    @Property(str, notify=changed)
    def wHoldLetter(self) -> str:
        """Retorna apenas a letra usada para W-hold ('W' ou 'Z')."""
        if not self.clicker:
            return "W"
        try:
            return getattr(self.clicker, "w_hold_label", lambda: "W")()
        except Exception:
            return "W"

    @Property(bool, notify=changed)
    def frWOverrideAvailable(self) -> bool:
        """Disponibilidade do toggle: somente quando o idioma normalizado for 'fr'."""
        try:
            if getattr(self, "_parent_i18n", None) is None:
                return False
            code = normalize_language(self._parent_i18n.language)
            return code == "fr"
        except Exception:
            return False

    @Property(bool, notify=changed)
    def frWOverride(self) -> bool:
        """Estado atual do override (forcar W mesmo em FR)."""
        if not self.clicker:
            return False
        return bool(getattr(self.clicker, "force_w_in_fr", False))

    @Slot(bool)
    def setFrWOverride(self, value: bool) -> None:
        """Ativa/desativa o override e persiste a configuração; re-aplica idioma."""
        if not self.clicker:
            return
        self.clicker.force_w_in_fr = bool(value)
        # persiste a config
        try:
            self._clicker_settings()["force_w_in_fr"] = bool(value)
            save_settings(self.settings)
        except Exception:
            pass
        # re-aplica idioma atual para forçar recalculo da tecla usada
        try:
            if getattr(self, "_parent_i18n", None) is not None:
                self.clicker.set_language(self._parent_i18n.language)
        except Exception:
            pass
        self.changed.emit()

    @Property(str, notify=changed)
    def overlayHintText(self) -> str:
        if not self.clicker:
            return ""
        if getattr(self.clicker, "w_hold_enabled", False):
            return f"S pausa | Esc ou {self.pilotHotkey} para parar"
        if getattr(self.clicker, "right_hold_enabled", False):
            return f"Esc ou {self.rightHoldHotkey} para soltar"
        if getattr(self.clicker, "artillery_enabled", False):
            return f"{self.artilleryHotkey} ou clique esquerdo para parar"
        if getattr(self.clicker, "move_click_enabled", False):
            return f"Esc ou {self.moveHotkey} para soltar"
        if getattr(self.clicker, "fixed_click_enabled", False):
            return "1-4 clicam slots | mouse/asd cancela"
        if getattr(self.clicker, "enabled", False) and getattr(self.clicker, "shift_enabled", False):
            return "Shift entra somente enquanto voce segura"
        return ""

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
                f"{self.rightHoldHotkey}: right mouse hold",
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
    def setRightHoldHotkey(self, value: str) -> None:
        if value in ACTION_KEYS:
            self._clicker_settings()["right_hold_hotkey"] = value
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
        return bool(self._clicker_settings().get("w_doubletap_enabled", False))

    @Slot(bool)
    def setWDoubleTapEnabled(self, value: bool) -> None:
        self._clicker_settings()["w_doubletap_enabled"] = bool(value)
        save_settings(self.settings)
        if self.clicker:
            self.clicker.w_doubletap_enabled = bool(value)
        self.changed.emit()

    @Property(bool, notify=changed)
    def rightDoubleTapEnabled(self) -> bool:
        return bool(self._clicker_settings().get("right_doubletap_enabled", False))

    @Slot(bool)
    def setRightDoubleTapEnabled(self, value: bool) -> None:
        self._clicker_settings()["right_doubletap_enabled"] = bool(value)
        save_settings(self.settings)
        if self.clicker:
            self.clicker.right_doubletap_enabled = bool(value)
        self.changed.emit()

    @Slot(str, bool)
    def setModeEnabled(self, key: str, enabled: bool) -> None:
        key = str(key or "")
        if key not in self.MODE_KEYS:
            return
        modes = self._mode_enabled_settings()
        enabled = bool(enabled)
        if modes.get(key, True) == enabled:
            return
        modes[key] = enabled
        self._clicker_settings()["modes_enabled"] = modes
        save_settings(self.settings)
        if self.clicker:
            self.clicker.configure_modes_enabled(modes)
            self._status = self.clicker.status_text()
        self.changed.emit()

    @Slot(float)
    def setInterval(self, value: float) -> None:
        try:
            interval = float(value)
        except (TypeError, ValueError):
            interval = self.DEFAULT_INTERVAL
        self._clicker_settings()["interval"] = round(max(0.03, min(5.0, interval)), 2)
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
    visualGroupRowsChanged = Signal()

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
        self._upload_overlay_detail = ""
        self._upload_overlay_accent = "#ffd166"
        self._upload_overlay_title_key = "stockpile.overlay_processing_title"
        self._upload_overlay_progress = 100
        self._visual_items: list[dict[str, Any]] = []
        self._visual_warehouses: list[dict[str, Any]] = []
        self._visual_warehouse = ""
        self._visual_items_by_warehouse: dict[str, list[dict[str, Any]]] = {}
        self._visual_warehouse_lookup: dict[str, dict[str, Any]] = {}
        self._visual_warehouse_options: list[dict[str, Any]] = []
        self._cached_visual_groups: list[dict[str, Any]] = []
        self._watcher: StockpileWatcher | None = None
        self._api_loading = False
        self._upload_overlay_timer = QTimer(self)
        self._upload_overlay_timer.setSingleShot(True)
        self._upload_overlay_timer.timeout.connect(self.dismissUploadOverlay)
        self.logs = DictListModel(["time", "message"], self)
        self.items = DictListModel(["name", "quantity", "category", "icon"], self)
        self.warehouses = DictListModel(["name", "region", "count", "updatedAt"], self)
        self.statusFromWorker.connect(self._handle_status)
        self.refreshDebugSnapshot()

    @Property(bool, notify=changed)
    def apiLoading(self) -> bool:
        return getattr(self, "_api_loading", False)

    @Property(float, notify=changed)
    def hudScale(self) -> float:
        return float(self.settings.get("stockpile", {}).get("hud_scale", 1.0))

    @Slot(float)
    def setHudScale(self, value: float) -> None:
        self.settings.setdefault("stockpile", {})["hud_scale"] = value
        save_settings(self.settings)
        self.changed.emit()

    @Property(bool, notify=changed)
    def running(self) -> bool:
        return self._running

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

    @Property(str, notify=changed)
    def uploadOverlayDetail(self) -> str:
        return getattr(self, "_upload_overlay_detail", "")

    @Property(str, notify=changed)
    def uploadOverlayAccent(self) -> str:
        return getattr(self, "_upload_overlay_accent", "#3b82f6")

    @Property(str, notify=changed)
    def uploadOverlayTitleKey(self) -> str:
        return getattr(self, "_upload_overlay_title_key", "stockpile.overlay_processing_title")

    @Property(int, notify=changed)
    def uploadOverlayProgress(self) -> int:
        return getattr(self, "_upload_overlay_progress", 100)

    @Property("QVariantList", notify=changed)
    def warehouseRows(self) -> list[dict[str, Any]]:
        return self.warehouses.items()

    @Property("QVariantList", notify=changed)
    def itemRows(self) -> list[dict[str, Any]]:
        return self.items.items()

    @Property("QVariantList", notify=changed)
    def logRows(self) -> list[dict[str, Any]]:
        return self.logs.items()

    @Property("QVariantList", notify=changed)
    def visualWarehouseOptions(self) -> list[dict[str, Any]]:
        return list(self._visual_warehouse_options)

    @Property(str, notify=changed)
    def visualWarehouse(self) -> str:
        return self._visual_warehouse

    @Property(str, notify=changed)
    def visualWarehouseUpdatedAt(self) -> str:
        item = self._visual_warehouse_lookup.get(self._visual_warehouse)
        if item:
            return self._visual_update_label(item)
        return "-"

    @Property(bool, notify=changed)
    def visualWarehouseInactive(self) -> bool:
        item = self._visual_warehouse_lookup.get(self._visual_warehouse)
        return self._depot_state(item) == "inactive" if item else False

    @Property("QVariantList", notify=visualGroupRowsChanged)
    def visualGroupRows(self) -> list[dict[str, Any]]:
        return self._cached_visual_groups

    @Slot(str)
    def setVisualWarehouse(self, value: str) -> None:
        value = str(value or "")
        if value == self._visual_warehouse:
            return
        self._visual_warehouse = value
        self._cached_visual_groups = self._visual_groups()
        self.visualGroupRowsChanged.emit()
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

    def _apply_visual_data(
        self,
        rows: list[dict[str, Any]],
        warehouses: list[dict[str, Any]],
        stockpiles: list[str],
    ) -> None:
        raw_items_by_warehouse: dict[str, list[dict[str, Any]]] = {}
        for item in rows:
            warehouse = str(item.get("warehouse") or "")
            if warehouse:
                raw_items_by_warehouse.setdefault(warehouse, []).append(item)

        enriched_warehouses: list[dict[str, Any]] = []
        self._visual_warehouse_lookup = {}
        for warehouse in warehouses:
            name = str(warehouse.get("name") or "")
            if not name:
                continue
            enriched = dict(warehouse)
            for row in raw_items_by_warehouse.get(name, []):
                if not enriched.get("map_name") and row.get("map_name"):
                    enriched["map_name"] = row.get("map_name")
                if not enriched.get("town") and row.get("town"):
                    enriched["town"] = row.get("town")
                if enriched.get("map_name") and enriched.get("town"):
                    break
            enriched.update(self._warehouse_meta(enriched))
            if not self._is_visual_stockpile_visible(enriched):
                continue
            enriched_warehouses.append(enriched)
            self._visual_warehouse_lookup[name] = enriched

        visible_names = set(self._visual_warehouse_lookup)
        self._visual_items_by_warehouse = {
            name: raw_items_by_warehouse.get(name, [])
            for name in visible_names
        }
        self._visual_items = [
            item
            for item in rows
            if str(item.get("warehouse") or "") in visible_names
        ]
        self._visual_warehouses = enriched_warehouses
        self._visual_warehouse_options = self._build_visual_warehouse_options(enriched_warehouses)

        available = [name for name in stockpiles if name in self._visual_warehouse_lookup] or [
            str(item.get("name") or "") for item in enriched_warehouses
        ]
        available = [name for name in available if name]
        if available and self._visual_warehouse not in self._visual_warehouse_lookup:
            self._visual_warehouse = available[0]
        elif not available:
            self._visual_warehouse = ""

        self._cached_visual_groups = self._visual_groups()
        self.visualGroupRowsChanged.emit()

    @staticmethod
    def _warehouse_parts(name: str) -> tuple[str, str, str]:
        parts = [part.strip() for part in str(name or "").split("/") if part.strip()]
        if len(parts) >= 3:
            return parts[0], parts[-2], parts[-1]
        if len(parts) == 2:
            second = parts[1]
            if re.match(r"^[A-Z]{1,4}[-_]", second, re.IGNORECASE):
                return parts[0], "", second
            return parts[0], second, second
        value = parts[0] if parts else "-"
        return "", "", value

    @staticmethod
    def _depot_state(warehouse: dict[str, Any] | None) -> str:
        if not isinstance(warehouse, dict):
            return ""
        return _warehouse_text(warehouse, "depot_state", "DepotState", "depotState", "state", "State").lower()

    @staticmethod
    def _has_gg_stockpile_prefix(warehouse: dict[str, Any]) -> bool:
        name = str(warehouse.get("name") or "")
        _map_part, _town, name_code = StockpileController._warehouse_parts(name)
        candidates = [
            warehouse.get("code"),
            warehouse.get("display_name"),
            warehouse.get("warehouse_name"),
            warehouse.get("stockpile_name"),
            warehouse.get("neme"),
            name_code,
        ]
        return any(str(value or "").strip().upper().startswith("GG-") for value in candidates)

    @classmethod
    def _is_visual_stockpile_visible(cls, warehouse: dict[str, Any]) -> bool:
        return cls._has_gg_stockpile_prefix(warehouse) and cls._depot_state(warehouse) != "lost"

    @staticmethod
    def _warehouse_meta(warehouse: dict[str, Any] | str) -> dict[str, str]:
        if isinstance(warehouse, dict):
            name = str(warehouse.get("name") or "")
            explicit_title = str(
                warehouse.get("display_name")
                or warehouse.get("warehouse_name")
                or warehouse.get("stockpile_name")
                or warehouse.get("neme")
                or ""
            ).strip()
            explicit_map = _warehouse_text(warehouse, "map_name", "MapName", "mapName", "map", "Map", "region", "Region")
            explicit_town = _warehouse_text(warehouse, "town", "Town", "town_name", "TownName", "townName", "location", "Location")
        else:
            name = str(warehouse or "")
            explicit_title = ""
            explicit_map = ""
            explicit_town = ""
        map_part, town, code = StockpileController._warehouse_parts(name)
        lookup_map = explicit_map or map_part
        lookup_town = explicit_town or town
        map_key = _compact_location_key(_strip_hex_suffix(lookup_map))
        matched = _location_index().get((map_key, lookup_town.lower())) if map_key and lookup_town else None
        if not matched:
            matched = _location_from_stockpile_code(map_key, explicit_title, code, name)

        region = str((matched or {}).get("region") or _strip_hex_suffix(lookup_map) or "Outros")
        display_town = str(explicit_town or (matched or {}).get("town") or town)
        map_name = explicit_map or stockpile_map_name(str((matched or {}).get("mapName") or "") or map_part or region)
        place_path = f"{map_name} - {display_town}" if map_name and display_town else map_name or display_town or name
        title = explicit_title or (code if code and code != display_town else name)
        return {
            "region": map_name or region,
            "town": display_town,
            "code": title,
            "mapName": map_name,
            "placePath": place_path,
            "optionSubText": display_town or place_path,
            "groupLabel": map_name or region or place_path,
        }

    @staticmethod
    def _warehouse_option_sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(item.get("groupLabel") or item.get("region") or "").lower(),
            str(item.get("town") or "").lower(),
            str(item.get("code") or item.get("name") or "").lower(),
        )

    def _build_visual_warehouse_options(self, warehouses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for warehouse in sorted(warehouses, key=self._warehouse_option_sort_key):
            group_label = str(warehouse.get("groupLabel") or warehouse.get("placePath") or warehouse.get("region") or "Outros")
            grouped.setdefault(group_label, []).append(warehouse)

        options: list[dict[str, Any]] = []
        for region in sorted(grouped, key=lambda value: value.lower()):
            options.append({"text": region, "type": "header"})
            for warehouse in grouped[region]:
                updated_raw = str(warehouse.get("last_update") or warehouse.get("updatedAt") or "")
                inactive = self._depot_state(warehouse) == "inactive"
                options.append(
                    {
                        "text": str(warehouse.get("code") or warehouse.get("name") or "-"),
                        "subText": str(warehouse.get("optionSubText") or warehouse.get("placePath") or ""),
                        "sideText": "" if inactive else format_relative_time(updated_raw),
                        "sideTextKey": "stockpile.visual_depot_inactive_badge" if inactive else "",
                        "sideColor": "#ef4444" if inactive else "",
                        "id": str(warehouse.get("name") or ""),
                        "type": "item",
                    }
                )
        return options

    @staticmethod
    def _visual_update_label(item: dict[str, Any]) -> str:
        updated_raw = str(item.get("last_update") or item.get("updatedAt") or "")
        absolute = format_to_local_pc_time(updated_raw)
        relative = format_relative_time(updated_raw)
        place = str(item.get("placePath") or item.get("name") or "-")
        if absolute and absolute != "-" and relative:
            return f"{place} - {absolute} ({relative})"
        if absolute and absolute != "-":
            return f"{place} - {absolute}"
        return place

    @Slot(object)
    def _handle_status(self, message: object) -> None:
        if isinstance(message, dict):
            if message.get("kind") == "ui_error":
                self._api_loading = False
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
            self._apply_visual_data(rows, warehouses, stockpiles)
            
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
        self._api_loading = False
        self.refreshDebugSnapshot(emit_changed=False)
        self.changed.emit()

    def _append_log(self, message: str) -> None:
        self.logs.append({"time": now_label(), "message": message})
        if self.logs.count() > 200:
            self.logs.set_items(self.logs.items()[-200:])

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
        is_success = response in ("HTTP 200", "OK", "HTTP 201") or response.startswith("HTTP 2")
        count = int(message.get("report_count", self._report_count))
        
        if is_success:
            self._upload_overlay_accent = "#4ef7b2"
            self._upload_overlay_title_key = "stockpile.overlay_processing_title"
            self._upload_overlay_body = f"{count} estoques atualizados com sucesso" if count != 1 else "1 estoque atualizado com sucesso"
            names = self._stockpile_list if self._stockpile_list and self._stockpile_list != "-" else self._last_stockpile
            if names and names != "-":
                self._upload_overlay_detail = f"Atualizados: {names}"
            else:
                self._upload_overlay_detail = "Dados enviados para a nuvem."
            self._upload_overlay_progress = 100
        else:
            self._upload_overlay_accent = "#ff7a90"
            self._upload_overlay_title_key = "update.error_title"
            self._upload_overlay_body = "Falha ao atualizar estoques"
            self._upload_overlay_detail = response
            self._upload_overlay_progress = 0

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
        rows = list(self._visual_items_by_warehouse.get(warehouse, []))
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
        self._profile: dict[str, Any] = {}
        self._profile_loading = False
        self._profile_ready = False
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
        self._auto_connect_timer.setInterval(2500)
        self._auto_connect_timer.timeout.connect(self._maybe_auto_connect)


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

    def _close_ws(self) -> None:
        if self._ws is not None:
            self._ws.close()


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
    def authInFlight(self) -> bool:
        return self._auth_in_flight

    @Property(bool, notify=changed)
    def authErrorVisible(self) -> bool:
        return self._auth_error_visible

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

    def _auth_with_discord(self, payload: dict[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for path in CHAT_DISCORD_AUTH_PATHS:
            try:
                result = http_json("POST", path, payload=payload, timeout=12)
                debug_login_response(path, result)
                return result
            except Exception as exc:
                last_error = exc
        raise RuntimeError(str(last_error) if last_error else "chat auth failed")

    def _auth_with_steam(self, payload: dict[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for path in CHAT_STEAM_AUTH_PATHS:
            try:
                result = http_json("POST", path, payload=payload, timeout=12)
                debug_login_response(path, result)
                return result
            except Exception as exc:
                last_error = exc
        raise RuntimeError(str(last_error) if last_error else "chat auth failed")

    def _verify_discord_app_access(self, result: dict[str, Any]) -> dict[str, Any]:
        token = str(result.get("token") or result.get("accessToken") or "")
        user = result.get("user") if isinstance(result.get("user"), dict) else result.get("profile")
        if not isinstance(user, dict):
            raise RuntimeError("A API não retornou perfil de usuário no login.")

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
        if self._saved_discord_id():
            self._discord_configuration_checked = True
            # Keep _discord_login_required = True (or as it was) so the overlay stays up
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
                result = self._verify_discord_app_access(result)
                self.resultFromWorker.emit("auth", result)
            except Exception as exc:
                message = str(exc)
                if "access_denied" in message or "oauth_cancelled" in message:
                    message = self._t("home.chat.discord_cancelled")
                self.resultFromWorker.emit("auth-error", self._t("home.chat.auth_error", message=message))

        self._auth_in_flight = True
        self._auth_error_visible = False
        self._auth_denied = False
        self._discord_oauth_in_flight = not bool(discord_id)
        self._status = self._t("home.chat.authenticating_discord") if discord_id else self._t("home.chat.discord_opening")
        # NOTE: Do NOT set _discord_login_required = False here!
        # The overlay will only close once auth actually succeeds in _apply_result("auth").
        self.changed.emit()
        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def connectWithSteam(self) -> None:
        self.ensureStarted()
        self._auth_retry_after = 0.0
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
        self._auth_error_visible = False
        self._auth_denied = False
        self._discord_oauth_in_flight = False
        self._status = self._t("home.chat.authenticating")
        self.changed.emit()
        threading.Thread(target=worker, daemon=True).start()

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
        if self._saved_discord_id():
            self._discord_configuration_checked = True
            self._discord_login_required = True
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
        self._ensure_ws().sendTextMessage(json.dumps({
            "type": "send_message",
            "chatSlug": self._selected_room,
            "content": body.strip()
        }))

    @Slot(str, str)
    def sendMessageReply(self, body: str, replyToMessageId: str) -> None:
        if not self._token or not self._selected_room or not body.strip():
            return
        self._ensure_ws().sendTextMessage(json.dumps({
            "type": "send_message",
            "chatSlug": self._selected_room,
            "content": body.strip(),
            "replyToMessageId": replyToMessageId
        }))

    @Slot(str, str)
    def reactMessage(self, messageId: str, emoji: str) -> None:
        if not self._token or not messageId or not emoji: return
        self._ensure_ws().sendTextMessage(json.dumps({
            "type": "react_message",
            "messageId": messageId,
            "emoji": emoji
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
    def _apply_result(self, kind: str, payload: object) -> None:
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
            self._discord_login_required = not bool(self._saved_discord_id())
            self._auth_error_visible = True
            payload_text = str(payload).lower()
            denied_markers = (
                "acesso negado",
                "access denied",
                "application access denied",
                "acceso denegado",
                "acceso a la aplicacion denegado",
                "acces refuse",
                "acces a l'application refuse",
            )
            self._auth_denied = any(marker in payload_text for marker in denied_markers)
            self._auth_retry_after = time.monotonic() + 30
            self._status = str(payload)
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
        ws.open(url)

    @Slot()
    def _on_ws_connected(self) -> None:
        self._status = self._t("home.chat.connected")
        self.changed.emit()
        if self._selected_room:
            self._ensure_ws().sendTextMessage(json.dumps({"type": "join_chat", "chatSlug": self._selected_room}))

    @Slot()
    def _on_ws_disconnected(self) -> None:
        if self._started and self._token:
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
        if len(current_rows) > 200:
            current_rows = current_rows[-200:]
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
        self._close_ws()


WIKI_KEY_LABELS = {
    "class": "Classe",
    "health": "Vida",
    "resistance": "Resistencia",
    "armour": "Blindagem",
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
}

WIKI_VALUE_TRANSLATIONS = {
    "Armored Car": "Carro blindado",
    "Battle Tank": "Tanque de batalha",
    "Emplacement": "Emplacement",
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
        "Production Site": "production_site",
        "Production Cost": "production_cost_raw",
        "Package Size": "package_size",
        "Fuel Capacity": "fuel_capacity",
        "Intel Icon": "intel_icon",
    }
    return mapping.get(label, re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_"))


def wiki_field_label(key: str) -> str:
    if key in WIKI_KEY_LABELS:
        return WIKI_KEY_LABELS[key]
    return " ".join(part.capitalize() for part in str(key or "").split("_") if part)


def translate_wiki_value(value: Any) -> str:
    text = clean_wiki_text(value)
    if not text:
        return ""
    if text in WIKI_VALUE_TRANSLATIONS:
        return WIKI_VALUE_TRANSLATIONS[text]
    translated = text
    for source, target in sorted(WIKI_VALUE_TRANSLATIONS.items(), key=lambda item: -len(item[0])):
        translated = re.sub(rf"\b{re.escape(source)}\b", target, translated)
    translated = re.sub(r"\bbelow\b", "abaixo de", translated, flags=re.I)
    translated = re.sub(r"\bhealth\b", "vida", translated, flags=re.I)
    return translated


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


def extract_wiki_infobox(page_html: str) -> dict[str, str]:
    result: dict[str, str] = {}
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
    for label_match in label_pattern.finditer(infobox):
        block = infobox[label_match.end() : label_match.end() + 1800]
        value_match = re.search(
            value_pattern,
            block,
        )
        if not value_match:
            continue
        label = strip_wiki_html(label_match.group(1))
        value = strip_wiki_html(value_match.group(1))
        if label and value:
            result[normalize_wiki_key(label)] = value
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


def fetch_wiki_page_html(page_title: str) -> str:
    params = urllib.parse.urlencode(
        {
            "action": "parse",
            "page": page_title,
            "prop": "text",
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
    return page_html


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


def fetch_wiki_item_info(page_title: str) -> dict[str, Any]:
    original_title = clean_wiki_text(page_title)
    candidates = wiki_title_candidates(original_title)
    last_error: Exception | None = None
    resolved_title = candidates[0] if candidates else original_title
    page_html = ""
    for candidate in candidates:
        try:
            resolved_title = candidate
            page_html = fetch_wiki_page_html(candidate)
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
        page_html = fetch_wiki_page_html(resolved_title)

    item = extract_wiki_infobox(page_html)
    item["description"] = extract_wiki_intro(page_html)
    item["production"] = extract_wiki_production(page_html)
    item["source_url"] = f"{FOXHOLE_WIKI_BASE_URL}/wiki/{urllib.parse.quote(resolved_title.replace(' ', '_'))}"
    if item.get("image"):
        item["remote_image"] = item["image"]
        item["image"] = cache_wiki_image(str(item.get("image") or ""), resolved_title)
    return item


class ItemSearchController(QObject):
    changed = Signal()
    rowsLoaded = Signal(object, str, str)
    wikiLoaded = Signal(object, str, int)

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
            ["rowType", "region", "code", "warehouse", "place", "quantity", "updatedAt", "updatedAgo", "icon", "total"],
            self,
        )
        self.suggestions = DictListModel(["name", "alias", "detail", "source"], self)
        self.wiki_fields = DictListModel(["label", "value"], self)
        self.wiki_production_rows = DictListModel(["site", "input", "output", "time"], self)
        self._all_rows: list[dict[str, Any]] = []
        self._cached_item_names: list[str] = []
        self._name_norm_by_name: dict[str, str] = {}
        self._slang_terms = self._load_slang_terms()
        self._slang_resolved_names: dict[int, list[str]] = {}
        self._wiki_title = ""
        self._wiki_name = ""
        self._wiki_description = ""
        self._wiki_image = ""
        self._wiki_source_url = ""
        self._wiki_status_key = "item_search.wiki_empty"
        self._wiki_status_message = ""
        self._wiki_loading = False
        self._wiki_request_token = 0
        self._pending_wiki_title = ""
        self._wiki_timer = QTimer(self)
        self._wiki_timer.setSingleShot(True)
        self._wiki_timer.setInterval(500)
        self._wiki_timer.timeout.connect(self._run_pending_wiki_lookup)
        self.rowsLoaded.connect(self._apply_loaded_rows)
        self.wikiLoaded.connect(self._apply_wiki_result)

    @Slot()
    def ensureLoaded(self) -> None:
        if not self._loaded and not self._loading:
            self.refresh()

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

    @Property(QObject, constant=True)
    def wikiFields(self) -> QObject:
        return self.wiki_fields

    @Property(QObject, constant=True)
    def wikiProduction(self) -> QObject:
        return self.wiki_production_rows

    @Property("QVariantList", notify=changed)
    def resultRowItems(self) -> list[dict[str, Any]]:
        return self.items.items()

    @Property("QVariantList", notify=changed)
    def suggestionRowItems(self) -> list[dict[str, Any]]:
        return self.suggestions.items()

    @Property(bool, notify=changed)
    def wikiLoading(self) -> bool:
        return self._wiki_loading

    @Property(str, notify=changed)
    def wikiStatusKey(self) -> str:
        return self._wiki_status_key

    @Property(str, notify=changed)
    def wikiStatusMessage(self) -> str:
        return self._wiki_status_message

    @Property(str, notify=changed)
    def wikiName(self) -> str:
        return self._wiki_name

    @Property(str, notify=changed)
    def wikiDescription(self) -> str:
        return self._wiki_description

    @Property(str, notify=changed)
    def wikiImage(self) -> str:
        return self._wiki_image

    @Property(str, notify=changed)
    def wikiSourceUrl(self) -> str:
        return self._wiki_source_url

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
        raw_rows = list(rows) if isinstance(rows, list) else []
        self._all_rows = [
            item
            for item in raw_rows
            if isinstance(item, dict) and self._is_searchable_stockpile_item(item)
        ]
        self._cached_item_names = sorted(
            {str(item.get("display_name") or "-") for item in self._all_rows if item.get("display_name")},
            key=str.lower,
        )
        self._name_norm_by_name = {name: self._normalize_search_text(name) for name in self._cached_item_names}
        self._slang_resolved_names = {}
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

    @Slot(str)
    def fetchWikiInfo(self, title: str) -> None:
        self._start_wiki_lookup(str(title or "").strip())

    @Slot()
    def openWikiPage(self) -> None:
        if self._wiki_source_url:
            QDesktopServices.openUrl(QUrl(self._wiki_source_url))

    @Slot()
    def _run_pending_wiki_lookup(self) -> None:
        self._start_wiki_lookup(self._pending_wiki_title)

    def _clear_wiki_info(self) -> None:
        self._wiki_timer.stop()
        self._pending_wiki_title = ""
        self._wiki_title = ""
        self._wiki_name = ""
        self._wiki_description = ""
        self._wiki_image = ""
        self._wiki_source_url = ""
        self._wiki_status_key = "item_search.wiki_empty"
        self._wiki_status_message = ""
        self._wiki_loading = False
        self.wiki_fields.set_items([])
        self.wiki_production_rows.set_items([])

    def _schedule_wiki_lookup(self) -> None:
        if not self._query.strip():
            if self._wiki_title or self._wiki_loading or self._wiki_name:
                self._clear_wiki_info()
            return
        title = (self._best_match or self._selected_name or self._query).strip()
        if not title:
            self._clear_wiki_info()
            return
        if title == self._wiki_title and (self._wiki_loading or self._wiki_name or self._wiki_status_key != "item_search.wiki_empty"):
            return
        self._pending_wiki_title = title
        self._wiki_timer.start()

    def _start_wiki_lookup(self, title: str) -> None:
        title = str(title or "").strip()
        if not title:
            self._clear_wiki_info()
            self.changed.emit()
            return
        if title == self._wiki_title and self._wiki_loading:
            return

        self._wiki_request_token += 1
        token = self._wiki_request_token
        self._wiki_title = title
        self._wiki_name = title
        self._wiki_description = ""
        self._wiki_image = ""
        self._wiki_source_url = f"{FOXHOLE_WIKI_BASE_URL}/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
        self._wiki_status_key = "item_search.wiki_loading"
        self._wiki_status_message = ""
        self._wiki_loading = True
        self.wiki_fields.set_items([])
        self.wiki_production_rows.set_items([])
        self.changed.emit()

        def worker() -> None:
            try:
                self.wikiLoaded.emit(fetch_wiki_item_info(title), "", token)
            except Exception as exc:
                self.wikiLoaded.emit({}, str(exc), token)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object, str, int)
    def _apply_wiki_result(self, data: object, error: str, token: int) -> None:
        if token != self._wiki_request_token:
            return
        self._wiki_loading = False
        if error:
            self._wiki_status_key = "item_search.wiki_error"
            self._wiki_status_message = error
            self.wiki_fields.set_items([])
            self.wiki_production_rows.set_items([])
            self.changed.emit()
            return

        item = data if isinstance(data, dict) else {}
        production = item.get("production") if isinstance(item.get("production"), list) else []
        excluded = {"name", "image", "remote_image", "description", "production", "source_url"}
        fields = [
            {"label": wiki_field_label(str(key)), "value": translate_wiki_value(value)}
            for key, value in item.items()
            if key not in excluded and translate_wiki_value(value)
        ]
        fields.sort(key=lambda row: row["label"].lower())
        has_data = bool(item.get("name") or item.get("description") or item.get("image") or fields or production)

        self._wiki_name = clean_wiki_text(item.get("name") or self._wiki_title)
        self._wiki_description = clean_wiki_text(item.get("description") or "")
        self._wiki_image = str(item.get("image") or "")
        self._wiki_source_url = str(item.get("source_url") or self._wiki_source_url)
        self._wiki_status_key = "item_search.wiki_loaded" if has_data else "item_search.wiki_empty"
        self._wiki_status_message = ""
        self.wiki_fields.set_items(fields[:12])
        self.wiki_production_rows.set_items(
            [
                {
                    "site": clean_wiki_text(row.get("site")),
                    "input": clean_wiki_text(row.get("input")),
                    "output": clean_wiki_text(row.get("output")),
                    "time": clean_wiki_text(row.get("time")),
                }
                for row in production[:8]
                if isinstance(row, dict)
            ]
        )
        self.changed.emit()

    def _item_names(self) -> list[str]:
        return self._cached_item_names

    @staticmethod
    def _row_quantity(item: dict[str, Any]) -> int:
        try:
            return int(item.get("quantity", 0) or 0)
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _is_searchable_stockpile_item(cls, item: dict[str, Any]) -> bool:
        if cls._row_quantity(item) <= 0:
            return False
        return StockpileController._has_gg_stockpile_prefix(
            {
                "name": item.get("warehouse"),
                "warehouse_name": item.get("warehouse_name"),
                "stockpile_name": item.get("stockpile_name"),
                "neme": item.get("neme"),
            }
        )

    @staticmethod
    def _normalize_search_text(value: Any) -> str:
        text = str(value or "").casefold()
        text = "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char))
        return re.sub(r"[^a-z0-9]+", " ", text).strip()

    @staticmethod
    def _load_slang_terms() -> list[dict[str, Any]]:
        path = BASE_DIR / "slang_terms.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        raw_terms = data.get("slang_terms", []) if isinstance(data, dict) else []
        terms: list[dict[str, Any]] = []
        for index, item in enumerate(raw_terms):
            if not isinstance(item, dict):
                continue
            name = str(item.get("nome") or "").strip()
            aliases = [str(alias).strip() for alias in item.get("apelidos", []) if str(alias).strip()]
            if not name and not aliases:
                continue
            terms.append(
                {
                    "index": index,
                    "name": name,
                    "aliases": aliases,
                    "category": str(item.get("categoria") or "").strip(),
                    "kind": str(item.get("tipo") or "").strip(),
                    "faction": str(item.get("faccao") or "").strip(),
                }
            )
        return terms

    def _resolve_slang_names(self, term: dict[str, Any]) -> list[str]:
        term_index = int(term.get("index", -1))
        if term_index in self._slang_resolved_names:
            return self._slang_resolved_names[term_index]

        target_norm = self._normalize_search_text(term.get("name"))
        alias_norms = [self._normalize_search_text(alias) for alias in term.get("aliases", [])]
        target_tokens = set(target_norm.split())
        resolved: list[str] = []
        for name, norm in self._name_norm_by_name.items():
            if not norm:
                continue
            if target_norm and (norm == target_norm or target_norm in norm or norm in target_norm):
                resolved.append(name)
                continue
            if target_tokens and len(target_tokens) <= 4 and target_tokens.issubset(set(norm.split())):
                resolved.append(name)
                continue
            if any(alias_norm and (alias_norm == norm or f" {alias_norm} " in f" {norm} ") for alias_norm in alias_norms):
                resolved.append(name)

        unique = sorted(dict.fromkeys(resolved), key=str.lower)
        self._slang_resolved_names[term_index] = unique[:16]
        return self._slang_resolved_names[term_index]

    def _slang_matches_for_query(self, query_norm: str) -> list[dict[str, Any]]:
        if not query_norm:
            return []
        scored: list[tuple[int, dict[str, Any]]] = []
        for term in self._slang_terms:
            name_norm = self._normalize_search_text(term.get("name"))
            alias_norms = [self._normalize_search_text(alias) for alias in term.get("aliases", [])]
            score = 0
            if any(alias == query_norm for alias in alias_norms):
                score = 100
            elif name_norm == query_norm:
                score = 95
            elif any(alias.startswith(query_norm) for alias in alias_norms):
                score = 82
            elif name_norm.startswith(query_norm):
                score = 76
            elif any(query_norm in alias for alias in alias_norms):
                score = 62
            elif query_norm in name_norm:
                score = 55
            if score:
                scored.append((score, term))
        scored.sort(key=lambda item: (-item[0], str(item[1].get("name") or "").lower()))
        return [term for _score, term in scored[:12]]

    def _suggestions_for_query(self, query: str) -> list[dict[str, str]]:
        query_norm = self._normalize_search_text(query)
        if not query_norm:
            return []
        names = self._item_names()
        starts = [name for name in names if self._name_norm_by_name.get(name, "").startswith(query_norm)]
        contains = [name for name in names if query_norm in self._name_norm_by_name.get(name, "") and name not in starts]

        rows: list[dict[str, str]] = [
            {"name": name, "alias": "", "detail": "", "source": "item"}
            for name in (starts + contains)
        ]

        seen = {row["name"] for row in rows}
        for term in self._slang_matches_for_query(query_norm):
            alias = next(
                (
                    str(alias)
                    for alias in term.get("aliases", [])
                    if query_norm in self._normalize_search_text(alias)
                ),
                str((term.get("aliases") or [""])[0] or ""),
            )
            detail_parts = [part for part in (alias, str(term.get("name") or ""), str(term.get("kind") or "")) if part]
            for name in self._resolve_slang_names(term):
                if name in seen:
                    continue
                rows.append(
                    {
                        "name": name,
                        "alias": alias,
                        "detail": " -> ".join(detail_parts[:3]),
                        "source": "slang",
                    }
                )
                seen.add(name)
                if len(rows) >= 10:
                    return rows

        return rows[:10]

    def _rows_for_name(self, name: str) -> list[dict[str, Any]]:
        target = self._normalize_search_text(name)
        return [item for item in self._all_rows if self._normalize_search_text(item.get("display_name")) == target]

    def _matching_rows(self) -> list[dict[str, Any]]:
        query_norm = self._normalize_search_text(self._query)
        if not query_norm:
            return self._all_rows
        exact = [item for item in self._all_rows if self._normalize_search_text(item.get("display_name")) == query_norm]
        if exact:
            return exact
        suggestions = self._suggestions_for_query(self._query)
        if suggestions:
            selected = suggestions[0].get("name", "")
            selected_rows = self._rows_for_name(selected)
            if selected_rows:
                return selected_rows

        slang_rows: list[dict[str, Any]] = []
        for term in self._slang_matches_for_query(query_norm):
            for name in self._resolve_slang_names(term):
                slang_rows.extend(self._rows_for_name(name))
        if slang_rows:
            return slang_rows

        return [item for item in self._all_rows if query_norm in self._normalize_search_text(item.get("display_name"))]

    @staticmethod
    def _split_location(warehouse: str) -> tuple[str, str, str]:
        parts = [part.strip() for part in str(warehouse or "-").split("/") if part.strip()]
        if len(parts) >= 3:
            return parts[0], parts[-2], parts[-1]
        if len(parts) == 2:
            return parts[0], parts[1], parts[1]
        value = parts[0] if parts else "-"
        return value, value, value

    @staticmethod
    def _location_meta_for_row(item: dict[str, Any]) -> dict[str, str]:
        return StockpileController._warehouse_meta(
            {
                "name": item.get("warehouse"),
                "map_name": item.get("map_name"),
                "town": item.get("town"),
                "warehouse_name": item.get("warehouse_name"),
            }
        )

    def _update_search_models(self) -> None:
        suggestions = self._suggestions_for_query(self._query)
        self.suggestions.set_items(suggestions)
        self._best_match = suggestions[0].get("name", "") if suggestions else ""

        rows = self._matching_rows()
        if not self._query.strip():
            self._selected_name = ""
            self._total = sum(max(0, int(item.get("quantity", 0) or 0)) for item in rows)
            self._status_key = "item_search.loaded" if self._loaded else "item_search.loading"
            self._status_count = len(self._all_rows)
        elif rows:
            self._selected_name = str(rows[0].get("display_name") or self._query)
            self._total = sum(max(0, int(item.get("quantity", 0) or 0)) for item in rows)
            self._status_key = "item_search.best_match" if self._best_match else "item_search.loaded"
        else:
            self._selected_name = self._query
            self._total = 0
            self._status_key = "item_search.best_match_empty"

        grouped: dict[str, list[tuple[dict[str, Any], dict[str, str]]]] = {}
        for item in rows:
            meta = self._location_meta_for_row(item)
            fallback_region, _name, _code = self._split_location(str(item.get("warehouse") or "-"))
            region = str(meta.get("groupLabel") or meta.get("mapName") or meta.get("region") or fallback_region)
            grouped.setdefault(region, []).append((item, meta))

        result_rows: list[dict[str, Any]] = []
        for region in sorted(grouped):
            region_rows = sorted(
                grouped[region],
                key=lambda entry: (
                    str(entry[1].get("town") or "").lower(),
                    str(entry[1].get("code") or "").lower(),
                    str(entry[0].get("warehouse") or "").lower(),
                ),
            )
            region_total = sum(max(0, int(item.get("quantity", 0) or 0)) for item, _meta in region_rows)
            result_rows.append(
                {
                    "rowType": "region",
                    "region": region,
                    "code": "",
                    "warehouse": "",
                    "place": "",
                    "quantity": 0,
                    "updatedAt": "",
                    "updatedAgo": "",
                    "icon": "",
                    "total": region_total,
                }
            )
            for item, meta in region_rows:
                _region, _name, fallback_code = self._split_location(str(item.get("warehouse") or "-"))
                code = str(meta.get("code") or fallback_code or "-")
                place = str(meta.get("placePath") or item.get("warehouse") or "-")
                updated_raw = str(item.get("warehouse_last_update") or "-")
                icon_path = str(item.get("icon_path") or "")
                result_rows.append(
                    {
                        "rowType": "item",
                        "region": region,
                        "code": code,
                        "warehouse": str(item.get("warehouse") or "-"),
                        "place": place,
                        "quantity": max(0, int(item.get("quantity", 0) or 0)),
                        "updatedAt": format_to_local_pc_time(updated_raw),
                        "updatedAgo": format_relative_time(updated_raw),
                        "icon": file_url(icon_path) if icon_path and Path(icon_path).exists() else "",
                        "total": 0,
                    }
                )
        self.items.set_items(result_rows)
        self._schedule_wiki_lookup()


class IdentifyItemController(QObject):
    MONITOR_SOUND_RESET_MISS_TICKS = 4

    changed = Signal()
    scanFinished = Signal(list, str)
    monitorFinished = Signal(object, str, bool)
    selectionFinished = Signal(object, str)

    def __init__(self, item_search: ItemSearchController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.item_search = item_search
        self.results = DictListModel(["name", "score", "scoreText", "icon", "path"], self)
        self.monitorMatches = DictListModel(["matchX", "matchY", "matchW", "matchH", "matchScore", "scoreText"], self)
        self.selectionCandidates = DictListModel(["candidateIndex", "selectX", "selectY", "selectW", "selectH", "cropX", "cropY", "cropW", "cropH"], self)
        self._status = "Ready."
        self._selected_path: Path | None = None
        self._selected_image_url = ""
        self._reference_preview_revision = 0
        self._mode = "Color"
        self._threshold = 0.86
        self._scanning = False
        self._clipboard_image = None
        self._detection_template: Any | None = None
        self._last_result_rows: list[dict[str, Any]] = []
        self._monitoring = False
        self._monitor_dependencies_checked = False
        self._monitor_available = True
        self._monitor_overlay_visible = False
        self._monitor_control_visible = False
        self._monitor_worker_active = False
        self._monitor_hwnd = 0
        self._monitor_match_count = 0
        self._monitor_best_score = 0.0
        self._monitor_summary = "Detection off."
        self._monitor_last_rows: list[dict[str, Any]] = []
        self._monitor_miss_count = 0
        self._monitor_sound_played = False
        self._selection_overlay_visible = False
        self._selection_busy = False
        self._selection_screenshot = None
        self._selection_candidate_rows: list[dict[str, Any]] = []
        self._selection_request_id = 0
        self._monitor_timer = QTimer(self)
        self._monitor_timer.setInterval(200)
        self._monitor_timer.timeout.connect(self._run_monitor_tick)
        self.scanFinished.connect(self._apply_scan_result)
        self.monitorFinished.connect(self._apply_monitor_result)
        self.selectionFinished.connect(self._apply_selection_result)

    @Slot()
    def ensureLoaded(self) -> None:
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
        return self._monitor_available

    @Property(str, notify=changed)
    def monitorTarget(self) -> str:
        if self._detection_template is not None:
            return str(getattr(self._detection_template, "name", "") or "selected image")
        if self._selected_path:
            return self._selected_path.name
        if self._clipboard_image is not None:
            return "clipboard image"
        return ""

    @Property(bool, notify=changed)
    def monitorOverlayVisible(self) -> bool:
        return self._monitor_overlay_visible

    @Property(bool, notify=changed)
    def monitorControlVisible(self) -> bool:
        return self._monitor_control_visible

    @Property(bool, notify=changed)
    def selectionOverlayVisible(self) -> bool:
        return self._selection_overlay_visible

    @Property(bool, notify=changed)
    def selectionBusy(self) -> bool:
        return self._selection_busy

    @Property(int, notify=changed)
    def monitorMatchCount(self) -> int:
        return self._monitor_match_count

    @Property(float, notify=changed)
    def monitorBestScore(self) -> float:
        return self._monitor_best_score

    @Property(str, notify=changed)
    def monitorBestScoreText(self) -> str:
        return f"{self._monitor_best_score:.3f}" if self._monitor_best_score > 0 else "-"

    @Property(str, notify=changed)
    def monitorSummary(self) -> str:
        return self._monitor_summary

    @Property(int, notify=changed)
    def indexedCount(self) -> int:
        return 0

    @Property(QObject, constant=True)
    def resultsModel(self) -> QObject:
        return self.results

    @Property(QObject, constant=True)
    def monitorMatchesModel(self) -> QObject:
        return self.monitorMatches

    @Property(QObject, constant=True)
    def selectionCandidatesModel(self) -> QObject:
        return self.selectionCandidates

    @Property("QStringList", constant=True)
    def modes(self) -> list[str]:
        return ["Color"]

    @Slot()
    def reindex(self) -> None:
        self._status = f"Direct OpenCV detection | {identify_dependencies_status()}"
        self.changed.emit()

    @Slot(str)
    def setMode(self, mode: str) -> None:
        self._mode = "Color"
        self.changed.emit()

    @Slot(float)
    def setThreshold(self, value: float) -> None:
        self._threshold = 0.86
        self.changed.emit()

    @Slot(int)
    def selectResult(self, index: int) -> None:
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
        self._prepare_reference_from_path(path)
        if self._detection_template is not None:
            self._set_reference_preview_url(path)
            self._reset_monitor_tracking(clear_visible_matches=True)
            self._status = f"Reference selected: {path.name}"
            if self._monitor_control_visible and not self._monitoring:
                self.startMonitor()
                return
        self.changed.emit()

    @Slot()
    def scanSelected(self) -> None:
        self.showMonitorOverlay()

    @Slot()
    def showMonitorOverlay(self) -> None:
        self._monitor_control_visible = True
        if self._monitoring:
            self._monitor_summary = f"Detection active: {self.monitorTarget or 'selected image'}"
            self._status = self._monitor_summary
        elif self._detection_template is not None:
            self.startMonitor()
            return
        else:
            self._monitor_summary = "Select an item from stockpile or paste a reference image."
            self._status = self._monitor_summary
        self.changed.emit()

    @Slot()
    def hideMonitorOverlay(self) -> None:
        if self._monitoring:
            self.stopMonitor()
        self._selection_request_id += 1
        self._monitor_control_visible = False
        self._selection_overlay_visible = False
        self._selection_busy = False
        self._selection_candidate_rows = []
        self._selection_screenshot = None
        self.selectionCandidates.set_items([])
        self.changed.emit()

    @Slot()
    def clearReference(self) -> None:
        was_monitoring = self._monitoring
        if was_monitoring:
            self.stopMonitor()
        self._selected_path = None
        self._selected_image_url = ""
        self._reference_preview_revision += 1
        self._clipboard_image = None
        self._detection_template = None
        self._last_result_rows = []
        self.results.set_items([])
        self._selection_request_id += 1
        self._selection_overlay_visible = False
        self._selection_busy = False
        self._selection_candidate_rows = []
        self._selection_screenshot = None
        self.selectionCandidates.set_items([])
        self._reset_monitor_tracking(clear_visible_matches=True)
        self._monitor_summary = "No reference selected."
        self._status = "Reference cleared."
        self.changed.emit()

    @Slot()
    def beginStockpileItemSelection(self) -> None:
        if self._selection_busy:
            return
        np_module, cv2_module, image_grab = identify_service.monitor_dependencies()
        self._monitor_available = bool(np_module is not None and cv2_module is not None and image_grab is not None)
        if not self._monitor_available:
            self._status = "Install numpy and opencv-python for stockpile item selection."
            self.changed.emit()
            return
        if not self._is_foxhole_focused():
            self._status = "Focus Foxhole with the stockpile panel open first."
            self.changed.emit()
            return
        bbox = self._window_client_rect()
        offset_x = int(bbox[0]) if bbox else 0
        offset_y = int(bbox[1]) if bbox else 0
        self._selection_busy = True
        self._selection_overlay_visible = False
        self.selectionCandidates.set_items([])
        self._status = "Scanning stockpile panel..."
        self._selection_request_id += 1
        request_id = self._selection_request_id
        self.changed.emit()

        def worker() -> None:
            try:
                _np_module, _cv2_module, grabber = identify_service.monitor_dependencies()
                if grabber is None:
                    self.selectionFinished.emit({"rows": [], "image": None, "requestId": request_id}, "Screen capture is unavailable.")
                    return
                screenshot = grabber.grab(bbox=bbox) if bbox else grabber.grab()
                regions, status = detect_stockpile_item_regions(screenshot)
                scale_x, scale_y = self._qt_screen_scale(screenshot.width, screenshot.height)
                rows: list[dict[str, Any]] = []
                for region in regions:
                    row = dict(region)
                    row["candidateIndex"] = len(rows)
                    display_x = int(row["selectX"]) + offset_x
                    display_y = int(row["selectY"]) + offset_y
                    row["selectX"] = int(round(display_x * scale_x))
                    row["selectY"] = int(round(display_y * scale_y))
                    row["selectW"] = max(8, int(round(int(row["selectW"]) * scale_x)))
                    row["selectH"] = max(8, int(round(int(row["selectH"]) * scale_y)))
                    rows.append(row)
                self.selectionFinished.emit({"rows": rows, "image": screenshot, "requestId": request_id}, status)
            except Exception as exc:
                self.selectionFinished.emit({"rows": [], "image": None, "requestId": request_id}, f"Stockpile selection error: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def cancelStockpileItemSelection(self) -> None:
        self._selection_overlay_visible = False
        self._selection_busy = False
        self._selection_request_id += 1
        self._selection_candidate_rows = []
        self._selection_screenshot = None
        self.selectionCandidates.set_items([])
        self._status = "Stockpile item selection canceled."
        self.changed.emit()

    @Slot(int)
    def selectStockpileCandidate(self, index: int) -> None:
        if index < 0 or index >= len(self._selection_candidate_rows) or self._selection_screenshot is None:
            return
        row = self._selection_candidate_rows[index]
        try:
            crop_x = int(row.get("cropX", 0))
            crop_y = int(row.get("cropY", 0))
            crop_w = int(row.get("cropW", 0))
            crop_h = int(row.get("cropH", 0))
            crop = self._selection_screenshot.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h)).convert("RGBA")
        except Exception as exc:
            self._status = f"Could not crop selected item: {exc}"
            self.changed.emit()
            return

        self._clipboard_image = crop
        self._selected_path = None
        self._prepare_reference_from_image(crop, "stockpile item")
        preview_path = identify_preview_path()
        try:
            crop.save(preview_path)
            self._set_reference_preview_url(preview_path)
        except Exception:
            self._selected_image_url = ""
        self._selection_overlay_visible = False
        self._selection_busy = False
        self._selection_candidate_rows = []
        self._selection_screenshot = None
        self.selectionCandidates.set_items([])
        if self._detection_template is not None:
            self._reset_monitor_tracking(clear_visible_matches=True)
            self._monitor_summary = "Reference selected from stockpile."
            self._status = "Reference selected from stockpile."
            if self._monitor_control_visible and not self._monitoring:
                self.startMonitor()
                return
        self.changed.emit()

    @Slot()
    def pasteClipboard(self) -> None:
        image, status = grab_clipboard_image()
        if image is None:
            self._status = status
            self.changed.emit()
            return
        self._clipboard_image = image
        self._selected_path = None
        self._prepare_reference_from_image(image, "clipboard image")
        preview_path = identify_preview_path()
        try:
            image.save(preview_path)
            self._set_reference_preview_url(preview_path)
        except Exception:
            self._selected_image_url = ""
        if self._detection_template is not None:
            self._reset_monitor_tracking(clear_visible_matches=True)
            self._status = f"{status} Reference ready."
            if self._monitor_control_visible and not self._monitoring:
                self.startMonitor()
                return
        self.changed.emit()

    def _prepare_reference_from_path(self, path: Path) -> None:
        template, status = prepare_detection_template_path(path)
        self._detection_template = template
        self._monitor_summary = status
        if template is None:
            self._status = status

    def _prepare_reference_from_image(self, image, name: str) -> None:
        template, status = prepare_detection_template(image, name=name)
        self._detection_template = template
        self._monitor_summary = status
        if template is None:
            self._status = status

    def _set_reference_preview_url(self, path: Path) -> None:
        self._reference_preview_revision += 1
        self._selected_image_url = f"{file_url(path)}?v={self._reference_preview_revision}"

    def _reset_monitor_tracking(self, *, clear_visible_matches: bool = False) -> None:
        self._monitor_last_rows = []
        self._monitor_miss_count = 0
        self._monitor_sound_played = False
        if clear_visible_matches:
            self.monitorMatches.set_items([])
            self._monitor_match_count = 0
            self._monitor_best_score = 0.0

    def _held_monitor_rows(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._monitor_last_rows if isinstance(item, dict)]

    def _register_monitor_miss(self) -> None:
        self._monitor_miss_count += 1
        self._monitor_last_rows = []
        if self._monitor_miss_count >= self.MONITOR_SOUND_RESET_MISS_TICKS:
            self._monitor_sound_played = False

    def _stabilize_monitor_scores(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self._monitor_last_rows:
            return [dict(item) for item in rows]
        stable_rows: list[dict[str, Any]] = []
        used_indexes: set[int] = set()
        previous_rows = [dict(item) for item in self._monitor_last_rows if isinstance(item, dict)]
        for row in rows:
            stable = dict(row)
            row_center_x = int(stable.get("matchX", 0)) + (int(stable.get("matchW", 0)) // 2)
            row_center_y = int(stable.get("matchY", 0)) + (int(stable.get("matchH", 0)) // 2)
            best_index = -1
            best_distance = 999999
            for index, previous in enumerate(previous_rows):
                if index in used_indexes:
                    continue
                previous_center_x = int(previous.get("matchX", 0)) + (int(previous.get("matchW", 0)) // 2)
                previous_center_y = int(previous.get("matchY", 0)) + (int(previous.get("matchH", 0)) // 2)
                distance = abs(row_center_x - previous_center_x) + abs(row_center_y - previous_center_y)
                if distance < best_distance:
                    best_distance = distance
                    best_index = index
            if best_index >= 0 and best_distance <= 6:
                previous = previous_rows[best_index]
                stable["matchScore"] = previous.get("matchScore", stable.get("matchScore", 0.0))
                stable["scoreText"] = previous.get("scoreText", stable.get("scoreText", ""))
                used_indexes.add(best_index)
            stable_rows.append(stable)
        return stable_rows

    def _begin_scan(self) -> None:
        self._scanning = True
        self._status = "Starting direct detection..."
        self.changed.emit()

    @Slot(list, str)
    def _apply_scan_result(self, matches: list[dict[str, Any]], status: str) -> None:
        self._last_result_rows = matches
        self.results.set_items(matches)
        self._status = status
        self._scanning = False
        self.changed.emit()

    @Slot(object, str)
    def _apply_selection_result(self, payload: object, status: str) -> None:
        rows: list[dict[str, Any]] = []
        image = None
        if isinstance(payload, dict):
            request_id = payload.get("requestId")
            if request_id is not None and int(request_id) != self._selection_request_id:
                return
            raw_rows = payload.get("rows", [])
            rows = list(raw_rows) if isinstance(raw_rows, list) else []
            image = payload.get("image")
        self._selection_busy = False
        self._selection_candidate_rows = rows
        self._selection_screenshot = image
        self.selectionCandidates.set_items(rows)
        self._selection_overlay_visible = bool(rows)
        self._status = status
        self.changed.emit()

    @Slot()
    def toggleMonitor(self) -> None:
        if self._monitoring:
            self.stopMonitor()
        else:
            self.startMonitor()

    @Slot()
    def startMonitor(self) -> None:
        np_module, cv2_module, image_grab = identify_service.monitor_dependencies()
        self._monitor_dependencies_checked = True
        self._monitor_available = bool(np_module is not None and cv2_module is not None and image_grab is not None)
        if not self._monitor_available:
            self._status = "Install numpy and opencv-python for on-screen monitoring."
            self.changed.emit()
            return
        if self._detection_template is None:
            self._monitor_control_visible = True
            self._monitor_summary = "Select an item from stockpile or paste a reference image first."
            self._status = self._monitor_summary
            self.changed.emit()
            return
        self._monitor_control_visible = True
        self._monitoring = True
        self._monitor_overlay_visible = True
        self._monitor_match_count = 0
        self._monitor_best_score = 0.0
        self._monitor_summary = "Detection active. Waiting for Foxhole focus."
        self._reset_monitor_tracking(clear_visible_matches=True)
        self._status = f"Detection active: {self.monitorTarget or 'selected image'}"
        self._monitor_timer.start()
        self.changed.emit()

    @Slot()
    def stopMonitor(self) -> None:
        self._monitoring = False
        self._monitor_worker_active = False
        self._monitor_overlay_visible = False
        self._monitor_timer.stop()
        self.monitorMatches.set_items([])
        self._monitor_match_count = 0
        self._monitor_best_score = 0.0
        self._monitor_summary = "Detection off."
        self._reset_monitor_tracking(clear_visible_matches=False)
        self._status = "Monitoring stopped."
        self.changed.emit()

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

    def _qt_screen_scale(self, image_width: int | None = None, image_height: int | None = None) -> tuple[float, float]:
        try:
            screen = QGuiApplication.primaryScreen()
            geometry = screen.geometry() if screen is not None else None
            logical_width = float(geometry.width()) if geometry is not None and geometry.width() > 0 else 0.0
            logical_height = float(geometry.height()) if geometry is not None and geometry.height() > 0 else 0.0
        except Exception:
            logical_width = 0.0
            logical_height = 0.0
        try:
            user32 = ctypes.windll.user32
            physical_width = float(user32.GetSystemMetrics(0))
            physical_height = float(user32.GetSystemMetrics(1))
        except Exception:
            physical_width = float(image_width or 0)
            physical_height = float(image_height or 0)
        if image_width and image_height and (physical_width <= 0 or physical_height <= 0):
            physical_width = float(image_width)
            physical_height = float(image_height)
        scale_x = logical_width / physical_width if logical_width > 0 and physical_width > 0 else 1.0
        scale_y = logical_height / physical_height if logical_height > 0 and physical_height > 0 else 1.0
        if not 0.25 <= scale_x <= 4.0:
            scale_x = 1.0
        if not 0.25 <= scale_y <= 4.0:
            scale_y = 1.0
        return scale_x, scale_y

    def _play_detection_alert(self) -> None:
        def worker() -> None:
            try:
                import winsound

                winsound.Beep(500, 180)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def _run_monitor_tick(self) -> None:
        if not self._monitoring or self._monitor_worker_active:
            return
        template = self._detection_template
        if template is None:
            self._status = "Select, paste, or choose a stockpile item first."
            self._monitor_summary = "No reference selected."
            self._reset_monitor_tracking(clear_visible_matches=True)
            self.changed.emit()
            return
        if not self._is_foxhole_focused():
            self._status = f"Detection active: {self.monitorTarget or 'selected image'} | waiting for Foxhole focus"
            self._monitor_summary = "Waiting for Foxhole focus."
            rows = self._held_monitor_rows()
            self._monitor_match_count = len(rows)
            self.monitorMatches.set_items(rows)
            self.changed.emit()
            return
        bbox = self._window_client_rect()
        threshold = float(self._threshold)
        self._monitor_worker_active = True

        def worker() -> None:
            try:
                np_module, cv2_module, image_grab = identify_service.monitor_dependencies()
                if np_module is None or cv2_module is None or image_grab is None:
                    self.monitorFinished.emit([], "Monitor dependencies are unavailable.", False)
                    return
                screenshot = image_grab.grab(bbox=bbox) if bbox else image_grab.grab()
                screen_np = np_module.array(screenshot.convert("RGB"), dtype=np_module.uint8)
                gray = cv2_module.cvtColor(screen_np, cv2_module.COLOR_RGB2GRAY)
                base_template = template.gray
                scale_x, scale_y = self._qt_screen_scale(screenshot.width, screenshot.height)
                if self._monitor_control_visible:
                    mask_w = min(gray.shape[1], max(1, int(round(420 / max(scale_x, 0.01)))))
                    mask_h = min(gray.shape[0], max(1, int(round(300 / max(scale_y, 0.01)))))
                    gray[:mask_h, gray.shape[1] - mask_w :] = 0
                matches: list[dict[str, Any]] = []
                best_score = -1.0
                th, tw = int(base_template.shape[0]), int(base_template.shape[1])
                if th < gray.shape[0] and tw < gray.shape[1]:
                    result = cv2_module.matchTemplate(gray, base_template, cv2_module.TM_CCOEFF_NORMED)
                    _min_val, max_val, _min_loc, max_loc = cv2_module.minMaxLoc(result)
                    best_score = max(best_score, float(max_val))
                    if max_val >= threshold:
                        mask = (result >= threshold).astype(np_module.uint8) * 255
                        contours, _hierarchy = cv2_module.findContours(mask, cv2_module.RETR_EXTERNAL, cv2_module.CHAIN_APPROX_SIMPLE)
                        ranked: list[tuple[float, int, int]] = []
                        for contour in contours:
                            rx, ry, rw, rh = cv2_module.boundingRect(contour)
                            roi = result[ry : ry + rh, rx : rx + rw]
                            if roi.size == 0:
                                continue
                            _roi_min, roi_max, _roi_min_loc, roi_max_loc = cv2_module.minMaxLoc(roi)
                            ranked.append((float(roi_max), int(rx + roi_max_loc[0]), int(ry + roi_max_loc[1])))
                        if not ranked:
                            ranked.append((float(max_val), int(max_loc[0]), int(max_loc[1])))
                        ranked.sort(reverse=True)
                        min_distance = max(12, int(max(tw, th) * 0.65))
                        for score, x, y in ranked:
                            physical_x = int(x + (bbox[0] if bbox else 0))
                            physical_y = int(y + (bbox[1] if bbox else 0))
                            display_x = int(round(physical_x * scale_x))
                            display_y = int(round(physical_y * scale_y))
                            display_w = max(8, int(round(tw * scale_x)))
                            display_h = max(8, int(round(th * scale_y)))
                            center_x = display_x + (display_w // 2)
                            center_y = display_y + (display_h // 2)
                            duplicate = False
                            for item in matches:
                                item_center_x = int(item["matchX"]) + (int(item["matchW"]) // 2)
                                item_center_y = int(item["matchY"]) + (int(item["matchH"]) // 2)
                                if abs(center_x - item_center_x) < min_distance and abs(center_y - item_center_y) < min_distance:
                                    duplicate = True
                                    break
                            if duplicate:
                                continue
                            matches.append(
                                {
                                    "matchX": display_x,
                                    "matchY": display_y,
                                    "matchW": display_w,
                                    "matchH": display_h,
                                    "matchScore": score,
                                    "scoreText": f"{score:.3f}",
                                }
                            )
                            if len(matches) >= 12:
                                break
                if matches:
                    matches.sort(key=lambda item: float(item.get("matchScore", 0.0)), reverse=True)
                    self.monitorFinished.emit(matches[:12], f"Detected: {len(matches[:12])}", True)
                else:
                    score_text = f"{best_score:.3f}" if best_score >= 0 else "-"
                    self.monitorFinished.emit([], f"Searching... best confidence {score_text}", True)
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
        if rows:
            if not self._monitor_sound_played:
                self._play_detection_alert()
                self._monitor_sound_played = True
            rows = self._stabilize_monitor_scores([dict(item) for item in rows if isinstance(item, dict)])
            self._monitor_last_rows = [dict(item) for item in rows]
            self._monitor_miss_count = 0
        else:
            if visible:
                self._register_monitor_miss()
                rows = []
            else:
                rows = self._held_monitor_rows()
            if rows:
                status = "Detected: held"

        self.monitorMatches.set_items(rows)
        self._monitor_overlay_visible = bool((visible or rows) and self._monitoring)
        self._monitor_match_count = len(rows)
        scores = [float(item.get("matchScore", 0.0)) for item in rows if isinstance(item, dict)]
        if scores:
            self._monitor_best_score = max(scores)
        elif match := re.search(r"(?:confidence|score)\s+([0-9.]+)", status, flags=re.IGNORECASE):
            try:
                self._monitor_best_score = float(match.group(1))
            except ValueError:
                self._monitor_best_score = 0.0
        elif "confidence" not in status.lower() and "score" not in status.lower():
            self._monitor_best_score = 0.0
        self._monitor_summary = status
        self._status = status
        self.changed.emit()

    @Slot()
    def shutdown(self) -> None:
        self.stopMonitor()
        self.cancelStockpileItemSelection()


class ProductionController(QObject):
    changed = Signal()

    def __init__(self, i18n: I18nController | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.availableItems = DictListModel(
            ["key", "name", "category", "faction", "mode", "icon", "quantityPerCrate", "bmat", "emat", "rmat", "hemat", "relic"],
            self,
        )
        self.categories = DictListModel(["name", "mark", "count", "active", "icon"], self)
        self.queue = DictListModel(["key", "name", "category", "faction", "quantity", "icon", "line"], self)
        self.queueCategories = DictListModel(["name", "mark", "count", "limit", "active", "icon", "slots"], self)
        self.materials = DictListModel(["key", "label", "quantity", "crates", "icon"], self)
        self.routeTrips = DictListModel(["title", "vehicle", "materials", "orders", "inputSlots", "outputCrates", "capacity"], self)
        self._status = "Production database not loaded."
        self._loaded = False
        self._items_by_key: dict[str, ProductionItem] = {}
        self._queue: dict[str, list[ProductionItem]] = {category: [] for category in CATEGORY_ORDER}
        self._mode = "mpf"
        self._faction = "Neutral"
        self._category = ""
        self._query = ""
        self._factory_multiplier = 1
        self._route_vehicle_mode = "Dunne"
        self._summary = "-"
        self._orders = "-"
        self._material_summary = "-"
        self._material_detail = "-"
        self._route_summary = "-"
        self._warning = ""
        if self.i18n:
            self.i18n.changed.connect(self.refresh)

    @Slot()
    def ensureLoaded(self) -> None:
        if self._loaded:
            return
        all_items, self._status = load_production_items()
        self._items_by_key = {item.key: item for item in all_items}
        self._category = self._first_available_category()
        self._loaded = True
        self.refresh()

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
    def materialSummary(self) -> str:
        return self._material_summary

    @Property(str, notify=changed)
    def materialDetail(self) -> str:
        return self._material_detail

    @Property(str, notify=changed)
    def routeSummary(self) -> str:
        return self._route_summary

    categoriesChanged = Signal()
    itemsChanged = Signal()
    queueChanged = Signal()
    queueCategoriesChanged = Signal()
    materialsChanged = Signal()
    routesChanged = Signal()

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

    @Property("QVariantList", notify=itemsChanged)
    def availableItemRows(self) -> list[dict[str, Any]]:
        return getattr(self, "_cached_available_items", self.availableItems.items())

    @Property("QVariantList", notify=categoriesChanged)
    def categoryRows(self) -> list[dict[str, Any]]:
        return getattr(self, "_cached_categories", self.categories.items())

    @Property("QVariantList", notify=queueChanged)
    def queueRows(self) -> list[dict[str, Any]]:
        return getattr(self, "_cached_queue", self.queue.items())

    @Property("QVariantList", notify=queueCategoriesChanged)
    def queueCategoryRows(self) -> list[dict[str, Any]]:
        return getattr(self, "_cached_queue_categories", self.queueCategories.items())

    @Property("QVariantList", notify=materialsChanged)
    def materialRows(self) -> list[dict[str, Any]]:
        return getattr(self, "_cached_materials", self.materials.items())

    @Property("QVariantList", notify=routesChanged)
    def routeTripRows(self) -> list[dict[str, Any]]:
        return getattr(self, "_cached_routes", self.routeTrips.items())

    @Property(QObject, constant=True)
    def availableItemsModel(self) -> QObject:
        return self.availableItems

    @Property(QObject, constant=True)
    def categoriesModel(self) -> QObject:
        return self.categories

    @Property(QObject, constant=True)
    def queueModel(self) -> QObject:
        return self.queue

    @Property(QObject, constant=True)
    def queueCategoriesModel(self) -> QObject:
        return self.queueCategories

    @Property(QObject, constant=True)
    def materialsModel(self) -> QObject:
        return self.materials

    @Property(QObject, constant=True)
    def routeTripsModel(self) -> QObject:
        return self.routeTrips

    @Slot()
    def reload(self) -> None:
        self._loaded = False
        self._items_by_key = {}
        self.clear()
        self.ensureLoaded()

    @Slot(str)
    def setMode(self, mode: str) -> None:
        self.ensureLoaded()
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
        self.ensureLoaded()
        if faction not in {"Neutral", "Colonial", "Warden"}:
            return
        self._faction = faction
        self.refresh()

    @Slot(str)
    def setCategory(self, category: str) -> None:
        self.ensureLoaded()
        if category not in CATEGORY_ORDER:
            return
        self._category = category
        self.refresh()

    @Slot(str)
    def search(self, query: str) -> None:
        self.ensureLoaded()
        self._query = query
        self.refresh()

    @Slot(int)
    def setFactoryMultiplier(self, value: int) -> None:
        self.ensureLoaded()
        self._factory_multiplier = min(2, max(1, int(value)))
        self.refresh()

    @Slot(str)
    def setRouteVehicleMode(self, value: str) -> None:
        self.ensureLoaded()
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
        self.ensureLoaded()
        item = self._items_by_key.get(key)
        if not item:
            self._warning = "Item not found."
            self.changed.emit()
            return
        self._add_item(item, fill=False)

    @Slot(str)
    def fillCategoryWithItem(self, key: str) -> None:
        self.ensureLoaded()
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
        self.ensureLoaded()
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
        self.ensureLoaded()
        match = next((item for item in self._items_by_key.values() if item.name.lower() == name.strip().lower() and item.mode == self._mode), None)
        if not match:
            self._warning = f"Item not found: {name}"
            self.changed.emit()
            return
        for _ in range(max(1, int(quantity))):
            self._add_item(match, fill=False, emit=False)
        self.refresh()

    @Slot(str, int)
    def removeQueueRow(self, category: str, index: int) -> None:
        self.ensureLoaded()
        rows = self._queue.get(category, [])
        if 0 <= index < len(rows):
            rows.pop(index)
        self.refresh()

    @Slot(str, int)
    def removeQueueSlot(self, category: str, index: int) -> None:
        self.removeQueueRow(category, index)

    @Slot(str)
    def clearCategory(self, category: str) -> None:
        self.ensureLoaded()
        if category in self._queue:
            self._queue[category] = []
        self.refresh()

    @Slot()
    def clear(self) -> None:
        self._queue = {category: [] for category in CATEGORY_ORDER}
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        if not self._loaded:
            self.availableItems.set_items([])
            self.categories.set_items([])
            self.queue.set_items([])
            self.queueCategories.set_items([])
            self.materials.set_items([])
            self.routeTrips.set_items([])
            self.changed.emit()
            return
        _all_items = list(self._items_by_key.values())
        categories = available_categories(_all_items, self._mode)
        if self._category not in categories:
            self._category = categories[0] if categories else ""

        filtered = filter_items(
            _all_items,
            mode=self._mode,
            category=self._category,
            faction=self._faction,
            query=self._query,
        )
        self._cached_available_items = [self._item_to_model(item) for item in filtered]
        self.availableItems.set_items(self._cached_available_items)
        self.itemsChanged.emit()

        self._cached_categories = [
            {
                "name": category,
                "mark": str(CATEGORY_RULES.get(category, {}).get("mark") or category[:2].upper()),
                "count": len(self._queue.get(category, [])),
                "active": category == self._category,
                "icon": self._category_icon_url(category),
            }
            for category in categories
        ]
        self.categories.set_items(self._cached_categories)
        self.categoriesChanged.emit()

        totals = calculate_queue(self._queue, mode=self._mode)
        material_rows = self._material_rows(totals["totals"])

        self._cached_queue = self._queue_rows()
        self.queue.set_items(self._cached_queue)
        self.queueChanged.emit()

        self._cached_queue_categories = self._queue_category_rows(categories)
        self.queueCategories.set_items(self._cached_queue_categories)
        self.queueCategoriesChanged.emit()

        self._cached_materials = material_rows
        self.materials.set_items(self._cached_materials)
        self.materialsChanged.emit()

        self._cached_routes = self._route_rows()
        self.routeTrips.set_items(self._cached_routes)
        self.routesChanged.emit()

        material_crates = sum(int(row.get("crates", 0) or 0) for row in material_rows)
        self._summary = self._t("production.total_value", items=totals["total_items"])
        if self._mode == "mpf":
            self._orders = self._t(
                "production.total_detail_mpf",
                crates=totals["total_crates"],
                orders=totals["active_orders"],
                discount=f"{totals['discount']:.1f}",
            )
        else:
            self._orders = self._t(
                "production.total_detail_factory",
                crates=totals["total_crates"],
                factories=totals["max_factory"],
            )
        self._material_summary = self._t("production.material_total_value", crates=material_crates)
        self._material_detail = self._format_material_detail(material_rows)
        self._route_summary = f"{self.routeTrips.count()} trips | {self._route_vehicle_mode}"
        self._warning = "  ".join(totals["warnings"])
        if self._items_by_key:
            self._status = f"{len(filtered)} visible / {len(self._items_by_key)} loaded"
        self.changed.emit()

    def _first_available_category(self) -> str:
        categories = available_categories(list(self._items_by_key.values()), self._mode)
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
                    price_parts = []
                    multiplier = discount_multiplier(index + 1) if self._mode == "mpf" else 1.0
                    for key, label in MATERIALS:
                        val = getattr(item, key, 0.0)
                        if val > 0:
                            price_parts.append(f"{int(math.ceil(val * multiplier - 1e-9))} {label}")
                    price_tooltip = " | ".join(price_parts)

                    slots.append(
                        {
                            "filled": True,
                            "line": index,
                            "name": item.name,
                            "icon": file_url(item.icon_path) if item.icon_path and Path(item.icon_path).exists() else "",
                            "discount": discount,
                            "priceTooltip": price_tooltip,
                        }
                    )
                else:
                    slots.append({"filled": False, "line": index, "name": "", "icon": "", "discount": 0, "priceTooltip": ""})
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

    def _format_material_detail(self, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return self._t("production.material_empty")
        parts = [
            self._t(
                "production.material_line",
                quantity=row.get("quantity", 0),
                label=row.get("label", ""),
                crates=row.get("crates", 0),
            )
            for row in rows
        ]
        if len(parts) <= 2:
            return " | ".join(parts)
        return " | ".join(parts[:2]) + "\n" + " | ".join(parts[2:])

    def _t(self, key: str, **kwargs: Any) -> str:
        if self.i18n:
            return self.i18n.translator.t(key, **kwargs)
        if kwargs:
            try:
                return key.format(**kwargs)
            except Exception:
                return key
        return key

    def _route_order_rows(self, orders: list[tuple[str, list[ProductionItem]]]) -> list[dict[str, Any]]:
        rows = []
        for _category, chunk in orders:
            if not chunk:
                continue
            counts = {}
            icons = {}
            for item in chunk:
                counts[item.name] = counts.get(item.name, 0) + 1
                if item.name not in icons:
                    icons[item.name] = file_url(item.icon_path) if item.icon_path and Path(item.icon_path).exists() else ""
            for name, count in counts.items():
                rows.append({"name": name, "count": count, "icon": icons[name]})
        return rows

    def _route_rows(self) -> list[dict[str, Any]]:
        trips = plan_transport_routes(self._queue, mode=self._mode, vehicle=self._route_vehicle_mode)
        rows: list[dict[str, Any]] = []
        for index, trip in enumerate(trips, 1):
            vehicle = str(trip.get("vehicle") or self._route_vehicle_mode)
            title = f"Trip {index}"
            route_part = int(trip.get("route_part") or 0)
            route_parts = int(trip.get("route_parts") or 0)
            if route_part and route_parts:
                title = f"{title} ({route_part}/{route_parts})"
            rows.append(
                {
                    "title": title,
                    "vehicle": vehicle,
                    "materials": format_route_materials(trip.get("materials", {}), vehicle=vehicle),
                    "orders": format_route_orders(trip.get("orders", [])),
                    "materialsList": self._material_rows(trip.get("materials", {})),
                    "ordersList": self._route_order_rows(trip.get("orders", [])),
                    "inputSlots": int(trip.get("input_slots") or 0),
                    "outputCrates": int(trip.get("output_crates") or 0),
                    "capacity": int(trip.get("max_slots") or 15),
                    "warning": str(trip.get("warning") or ""),
                }
            )
        return rows


class TimeTaskController(QObject):
    changed = Signal()
    statusFromWorker = Signal(str)
    restoreAppRequested = Signal()

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
        self._recorder = None
        self._recorder_checked = False
        self._available = True

    @Slot()
    def ensureLoaded(self) -> None:
        self._ensure_recorder()
        self.refreshMacros()

    def _ensure_recorder(self) -> bool:
        if self._recorder is not None:
            return True
        if self._recorder_checked:
            return False
        self._recorder_checked = True
        try:
            from macro_recorder import MacroRecorder

            self._recorder = MacroRecorder(lambda message: self.statusFromWorker.emit(str(message)))
            self._available = True
        except Exception as exc:
            self._recorder = None
            self._available = False
            self._status = f"TimeTask unavailable: {exc}"
            self.changed.emit()
            return False
        self.changed.emit()
        return True

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
        return str(user_data_dir() / "macros")

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
        if not self._ensure_recorder():
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
        if not self._ensure_recorder():
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
        if not self._ensure_recorder():
            self._status = "No active recording"
        else:
            self._countdown_timer.stop()
            events = self._recorder.stop_recording()
            self._status = self._t("timetask.overlay_events", events=len(events))
            
            if events:
                import time
                name_to_save = self._macro_name
                if name_to_save == "macro" or not name_to_save.strip():
                    name_to_save = f"Macro_{time.strftime('%H%M%S')}"
                path = self._recorder.save_macro(name_to_save)
                self._selected_path = path
                self._show_replay_overlay(path.stem)
            else:
                self._show_replay_overlay()
                
            self._record_overlay_visible = False
            
        self.refreshMacros()
        self._sync_poll_timer()
        self.restoreAppRequested.emit()
        self.changed.emit()

    @Slot()
    def saveCurrent(self) -> None:
        if not self._ensure_recorder():
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
        self.restoreAppRequested.emit()
        self.changed.emit()

    @Slot()
    def pauseResume(self) -> None:
        if not self._ensure_recorder():
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
        if not self._ensure_recorder():
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
        if not self._ensure_recorder():
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
        # Also show overlay when background hold modes are active.
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


class ControllerRegistry(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        debug_memory("registry init start")
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
        self.newsController = NewsController(self.chatController, self.i18nController, self)
        self.itemSearchController = ItemSearchController(self.settings_data, self)
        self.identifyItemController = IdentifyItemController(self.itemSearchController, self)
        self.productionController = ProductionController(self.i18nController, self)
        self.timeTaskController = TimeTaskController(self.i18nController, self)
        self.notificationsController = NotificationsController(self.settings_data, self)
        self.updateController = UpdateController(self.i18nController, self)
        self.i18nController.changed.connect(self.settingsController.notifyExternalChange)
        self.settingsController.changed.connect(self.notificationsController.refresh)
        self.autoClickerController.orderRequested.connect(lambda _order: self.notificationsController.startSquadlock())
        if self.settings_data.get("stockpile", {}).get("enabled", True):
            QTimer.singleShot(0, self.stockpileController.start)
        
        QTimer.singleShot(2000, self.updateController.check)
        debug_memory("registry init ready")

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
            "newsController",
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
