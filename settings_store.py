import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from i18n import detect_user_language
from stockpiler import DEFAULT_API_URL, DEFAULT_WATCH_FILE


SETTINGS_PATH = Path(__file__).with_name("felb_settings.json")


DEFAULT_SETTINGS: dict[str, Any] = {
    "language": "auto",
    "auto_clicker": {
        "hotkey": "F3",
        "mouse_button": "Esquerdo",
        "interval": 0.05,
        "mode": "Foxhole",
        "overlay_enabled": True,
        "overlay_hotkey": "F8",
        "overlay_color": "Azul",
        "overlay_show_profile": True,
        "overlay_show_clicker": True,
        "overlay_show_target": True,
    },
    "stockpile": {
        "enabled": True,
        "watch_file": str(DEFAULT_WATCH_FILE),
        "api_url": DEFAULT_API_URL,
        "out_dir": "extracted",
        "extract_initial": True,
    },
    "app": {
        "close_action": "ask",
    },
}


def load_settings() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return deepcopy(DEFAULT_SETTINGS)

    try:
        loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return deepcopy(DEFAULT_SETTINGS)

    settings = deepcopy(DEFAULT_SETTINGS)
    settings["language"] = loaded.get("language", DEFAULT_SETTINGS["language"])
    settings["auto_clicker"] = {
        **DEFAULT_SETTINGS["auto_clicker"],
        **loaded.get("auto_clicker", {}),
    }
    settings["stockpile"] = {
        **DEFAULT_SETTINGS["stockpile"],
        **loaded.get("stockpile", {}),
    }
    settings["app"] = {
        **DEFAULT_SETTINGS["app"],
        **loaded.get("app", {}),
    }
    return settings


def selected_language(settings: dict[str, Any]) -> str:
    language = settings.get("language", "auto")
    return detect_user_language() if language == "auto" else str(language)


def save_settings(settings: dict[str, Any]) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
