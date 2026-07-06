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
        self._activity_logger: ActivityLogger | None = None

        ensure_startup_enabled_by_default(self.settings)

    def setActivityLogger(self, logger: ActivityLogger | None) -> None:
        self._activity_logger = logger

    def _log_activity(self, action: str, *, subcategory: str, metadata: dict[str, Any] | None = None) -> None:
        if callable(self._activity_logger):
            self._activity_logger("configuracoes", action, 1, metadata or {}, subcategory)

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
        self._log_activity("alterar_configuracao", subcategory=str(section or "app"), metadata={"section": section, "key": key})

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
