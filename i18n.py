import json
import locale
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
TRANSLATIONS_DIR = BASE_DIR / "translations"
SUPPORTED_LANGUAGES = {
    "pt": {"name": "Português", "flag": "br", "emoji": "🇧🇷"},
    "en": {"name": "English", "flag": "us", "emoji": "🇺🇸"},
    "es": {"name": "Español", "flag": "es", "emoji": "🇪🇸"},
    "fr": {"name": "Français", "flag": "fr", "emoji": "🇫🇷"},
}
DEFAULT_LANGUAGE = "pt"


def detect_user_language() -> str:
    candidates = []
    try:
        default_locale = locale.getlocale()[0]
        if default_locale:
            candidates.append(default_locale)
    except Exception:
        pass

    try:
        candidates.append(locale.getdefaultlocale()[0] or "")
    except Exception:
        pass

    for candidate in candidates:
        code = candidate.split("_", 1)[0].split("-", 1)[0].lower()
        if code in SUPPORTED_LANGUAGES:
            return code
    return DEFAULT_LANGUAGE


class Translator:
    def __init__(self, language: str | None = None) -> None:
        self.language = normalize_language(language or detect_user_language())
        self._catalog = self._load_catalog(self.language)
        self._fallback = self._load_catalog(DEFAULT_LANGUAGE)

    def set_language(self, language: str) -> None:
        self.language = normalize_language(language)
        self._catalog = self._load_catalog(self.language)

    def t(self, key: str, **kwargs: Any) -> str:
        value = self._catalog.get(key, self._fallback.get(key, key))
        if kwargs:
            try:
                return value.format(**kwargs)
            except Exception:
                return value
        return value

    @staticmethod
    def flag_url(language: str) -> str:
        flag_code = SUPPORTED_LANGUAGES[normalize_language(language)]["flag"]
        return f"https://flagcdn.com/w80/{flag_code}.png"

    @staticmethod
    def _load_catalog(language: str) -> dict[str, str]:
        path = TRANSLATIONS_DIR / normalize_language(language) / "translation.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return {str(key): str(value) for key, value in data.items()}


def normalize_language(language: str | None) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    code = language.split("_", 1)[0].split("-", 1)[0].lower()
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
