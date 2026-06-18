from __future__ import annotations

import os
from pathlib import Path
import sys


APP_DIR_NAME = "GG Coalition"


def resource_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


def user_data_dir() -> Path:
    candidates: list[Path] = []
    base = os.getenv("LOCALAPPDATA")
    if base:
        candidates.append(Path(base) / APP_DIR_NAME)
    candidates.append(Path.home() / APP_DIR_NAME)
    candidates.append(resource_dir() / "user_data")

    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError:
            continue
    raise RuntimeError("Nao foi possivel criar uma pasta gravavel para os dados do app.")


def extracted_dir() -> Path:
    path = user_data_dir() / "extracted"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return user_data_dir() / "felb_settings.json"


def personalization_settings_path() -> Path:
    return user_data_dir() / "felb_personalization.json"


def resolve_writable_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return user_data_dir() / path
