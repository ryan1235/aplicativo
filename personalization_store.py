import json
from copy import deepcopy
from typing import Any

from app_paths import personalization_settings_path


PERSONALIZATION_PATH = personalization_settings_path()

DEFAULT_THEME_CUSTOM: dict[str, Any] = {
    "accent": "#5eead4",
    "accent_hover": "#34d399",
    "accent_panel": "#123b34",
    "success": "#62d7a4",
    "warning": "#f59e0b",
    "warning_text": "#ffedd5",
    "background": "#070b16",
    "surface": "#111c31",
    "text": "#edf6ff",
    "text_inverse": "#041014",
    "secondary_text": "#c7d7ed",
    "muted_text": "#9fb3c8",
    "disabled_text": "#7f93ad",
    "border": "#2b4b68",
    "surface_alt": "#0e1a2d",
    "surface_raised": "#172943",
    "control": "#1d3353",
    "control_hover": "#2d496f",
    "danger": "#ff7a90",
    "danger_hover": "#b94a5d",
    "danger_panel": "#4b1d31",
    "info": "#8ab4ff",
    "scrim": "#000000",
    "gradient_start": "#070b16",
    "gradient_end": "#12243a",
    "gradient_enabled": False,
    "button_style": "solid",
    "card_radius": 8,
}

DEFAULT_PERSONALIZATION_SETTINGS: dict[str, Any] = {
    "schema_version": 1,
    "colorblind_mode_enabled": False,
    "colorblind_profile": "none",
    "sidebar_width": 286,
    "theme": {
        "preset": "coalition",
        "custom": deepcopy(DEFAULT_THEME_CUSTOM),
    },
}


def _coerce_settings(loaded: Any, legacy_theme: Any = None, legacy_colorblind: Any = None) -> dict[str, Any]:
    source = loaded if isinstance(loaded, dict) else {}
    settings = deepcopy(DEFAULT_PERSONALIZATION_SETTINGS)

    theme_source = source.get("theme")
    if not isinstance(theme_source, dict) and isinstance(legacy_theme, dict):
        theme_source = legacy_theme
    if isinstance(theme_source, dict):
        settings["theme"] = {
            **settings["theme"],
            **theme_source,
        }
        custom_source = theme_source.get("custom")
        if isinstance(custom_source, dict):
            settings["theme"]["custom"] = {
                **settings["theme"]["custom"],
                **custom_source,
            }

    if "colorblind_mode_enabled" in source:
        settings["colorblind_mode_enabled"] = bool(source.get("colorblind_mode_enabled"))
    elif legacy_colorblind is not None:
        settings["colorblind_mode_enabled"] = bool(legacy_colorblind)
    settings["colorblind_profile"] = str(source.get("colorblind_profile") or settings["colorblind_profile"])
    try:
        settings["sidebar_width"] = int(source.get("sidebar_width", settings["sidebar_width"]))
    except (TypeError, ValueError):
        settings["sidebar_width"] = int(DEFAULT_PERSONALIZATION_SETTINGS["sidebar_width"])

    return settings


def load_personalization_settings(legacy_theme: Any = None, legacy_colorblind: Any = None) -> dict[str, Any]:
    try:
        loaded = json.loads(PERSONALIZATION_PATH.read_text(encoding="utf-8")) if PERSONALIZATION_PATH.exists() else {}
    except (OSError, json.JSONDecodeError):
        loaded = {}

    settings = _coerce_settings(loaded, legacy_theme, legacy_colorblind)
    save_personalization_settings(settings)
    return settings


def save_personalization_settings(settings: dict[str, Any]) -> None:
    PERSONALIZATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    PERSONALIZATION_PATH.write_text(json.dumps(_coerce_settings(settings), indent=2), encoding="utf-8")
