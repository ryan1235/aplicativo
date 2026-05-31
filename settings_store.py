import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from app_paths import extracted_dir, settings_path
from i18n import detect_user_language
from stockpiler import DEFAULT_API_URL, DEFAULT_WATCH_FILE, discover_map_data_file


SETTINGS_PATH = settings_path()


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
        "overlay_notification_enabled": True,
        "overlay_panel_x": None,
        "overlay_panel_y": None,
        "overlay_notification_x": None,
        "overlay_notification_y": None,
    },
    "stockpile": {
        "enabled": True,
        "watch_file": str(DEFAULT_WATCH_FILE),
        "api_url": DEFAULT_API_URL,
        "out_dir": str(extracted_dir()),
        "extract_initial": True,
    },
    "notifications": {
        "squadlock_overlay_enabled": True,
        "squadlock_x": None,
        "squadlock_y": None,
    },
    "app": {
        "close_action": "ask",
        "startup_prompted": False,
        "start_with_windows": False,
        "last_release_notes_version": "",
        "stockpile_sound_enabled": True,
        "squadlock_sound_enabled": True,
    },
}


def load_settings() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        settings = deepcopy(DEFAULT_SETTINGS)
        save_settings(settings)
        return settings

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
    settings["notifications"] = {
        **DEFAULT_SETTINGS["notifications"],
        **loaded.get("notifications", {}),
    }
    watch_file = Path(str(settings["stockpile"].get("watch_file", "")))
    discovered_watch_file = discover_map_data_file()
    if discovered_watch_file and not watch_file.exists():
        settings["stockpile"]["watch_file"] = str(discovered_watch_file)
    out_dir = Path(str(settings["stockpile"].get("out_dir", "")))
    if not out_dir.is_absolute():
        settings["stockpile"]["out_dir"] = str(extracted_dir())
    settings["app"] = {
        **DEFAULT_SETTINGS["app"],
        **loaded.get("app", {}),
    }
    save_settings(settings)
    return settings


def selected_language(settings: dict[str, Any]) -> str:
    language = settings.get("language", "auto")
    return detect_user_language() if language == "auto" else str(language)


def save_settings(settings: dict[str, Any]) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
