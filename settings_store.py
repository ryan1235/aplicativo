import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from app_paths import extracted_dir, settings_path
from i18n import detect_user_language
from stockpiler import DEFAULT_WATCH_FILE, discover_map_data_file


SETTINGS_PATH = settings_path()


DEFAULT_SETTINGS: dict[str, Any] = {
    "language": "auto",
    "auto_clicker": {
        "hotkey": "F3",
        "move_hotkey": "F2",
        "fixed_hotkey": "F6",
        "pilot_hotkey": "F4",
        "right_hold_hotkey": "F9",
        "mouse_button": "Esquerdo",
        "interval": 0.2,
        "mode": "Foxhole",
        "modes_enabled": {
            "auto": True,
            "move": True,
            "pilot": True,
            "right_hold": True,
            "fixed": True,
            "artillery": True,
        },
        "slot_1_x": 40,
        "slot_1_y": 80,
        "slot_2_x": 95,
        "slot_2_y": 80,
        "slot_3_x": 150,
        "slot_3_y": 80,
        "slot_4_x": 205,
        "slot_4_y": 80,
        "f5_orders": [
            "Diesel",
            "Cmats",
            "Bmats",
            "Emats",
        ],
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
        "right_doubletap_enabled": False,
    },
    "stockpile": {
        "enabled": True,
        "watch_file": str(DEFAULT_WATCH_FILE),
        "out_dir": str(extracted_dir()),
        "extract_initial": True,
    },
    "notifications": {
        "squadlock_overlay_enabled": True,
        "squadlock_x": None,
        "squadlock_y": None,
    },
    "discord": {
        "id": "",
        "username": "",
        "displayName": "",
        "avatar": "",
    },
    "app": {
        "close_action": "ask",
        "startup_prompted": False,
        "start_with_windows": False,
        "last_release_notes_version": "",
        "last_tips_version": "",
        "theme": {
            "preset": "coalition",
            "custom": {
                "accent": "#5eead4",
                "accent_hover": "#8ab4ff",
                "accent_panel": "#10342e",
                "success": "#62d7a4",
                "warning": "#ffd166",
                "warning_text": "#fef3c7",
                "background": "#070b16",
                "surface": "#111c31",
                "text": "#edf6ff",
                "muted_text": "#99abc4",
                "border": "#24486d",
                "gradient_start": "#070b16",
                "gradient_end": "#0d1729",
                "gradient_enabled": False,
                "button_style": "solid",
                "card_radius": 8,
            },
        },
        "chat_discord": {
            "clientId": "",
            "clientSecret": "",
            "redirectPort": 53624,
        },
        "stockpile_sound_enabled": True,
        "squadlock_sound_enabled": True,
        "chat_mention_overlay_enabled": True,
        "chat_mention_sound_enabled": True,
        "chat_show_translated_messages": True,
        "colorblind_mode_enabled": False,
        "sidebar_open": True,
        "sidebar_sections": {
            "core": True,
            "automation": True,
            "logistics": True,
            "tools": True,
            "config": True,
        },
    },
    "time_task": {
        "overlay_record_x": None,
        "overlay_record_y": None,
        "overlay_replay_x": None,
        "overlay_replay_y": None,
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
    settings["stockpile"].pop("api_url", None)
    settings["notifications"] = {
        **DEFAULT_SETTINGS["notifications"],
        **loaded.get("notifications", {}),
    }
    settings["discord"] = {
        **DEFAULT_SETTINGS["discord"],
        **loaded.get("discord", {}),
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
    settings["app"]["theme"] = {
        **DEFAULT_SETTINGS["app"]["theme"],
        **loaded.get("app", {}).get("theme", {}),
    }
    settings["app"]["theme"]["custom"] = {
        **DEFAULT_SETTINGS["app"]["theme"]["custom"],
        **loaded.get("app", {}).get("theme", {}).get("custom", {}),
    }
    settings["app"]["chat_discord"] = {
        **DEFAULT_SETTINGS["app"]["chat_discord"],
        **loaded.get("app", {}).get("chat_discord", {}),
    }
    legacy_discord = loaded.get("app", {}).get("chat_discord", {})
    if not settings["discord"].get("id") and legacy_discord.get("discordId"):
        settings["discord"]["id"] = str(legacy_discord.get("discordId") or "")
    for new_key, old_key in (("username", "username"), ("displayName", "displayName"), ("avatar", "avatar")):
        if not settings["discord"].get(new_key) and legacy_discord.get(old_key):
            settings["discord"][new_key] = str(legacy_discord.get(old_key) or "")
    for old_key in ("discordId", "username", "displayName", "avatar"):
        settings["app"]["chat_discord"].pop(old_key, None)
    settings["time_task"] = {
        **DEFAULT_SETTINGS["time_task"],
        **loaded.get("time_task", {}),
    }
    save_settings(settings)
    return settings


def selected_language(settings: dict[str, Any]) -> str:
    language = settings.get("language", "auto")
    return detect_user_language() if language == "auto" else str(language)


def save_settings(settings: dict[str, Any]) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
