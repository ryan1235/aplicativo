from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import threading
from typing import Any

from app_metadata import APP_TITLE, APP_VERSION
from app_paths import user_data_dir


SENSITIVE_KEYS = {
    "authorization",
    "access_token",
    "refresh_token",
    "token",
    "code",
    "codeverifier",
    "code_verifier",
    "clientsecret",
    "client_secret",
    "password",
    "secret",
}
MAX_TEXT_LENGTH = 4000


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _log_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def redact_sensitive(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "<max-depth>"
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).replace("-", "_").replace(" ", "_").lower()
            if normalized in SENSITIVE_KEYS or any(token in normalized for token in ("authorization", "token", "secret", "password")):
                result[str(key)] = "<redacted>"
            else:
                result[str(key)] = redact_sensitive(item, depth=depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [redact_sensitive(item, depth=depth + 1) for item in value[:80]]
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    if isinstance(value, str):
        if len(value) > MAX_TEXT_LENGTH:
            return value[:MAX_TEXT_LENGTH] + f"... <truncated {len(value) - MAX_TEXT_LENGTH} chars>"
        return value
    return value


class DebugLogger:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._enabled = False
        self._path: Path | None = None

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    @property
    def path(self) -> str:
        with self._lock:
            return str(self._path or "")

    def set_enabled(self, enabled: bool, *, reason: str = "") -> str:
        with self._lock:
            if enabled and self._path is None:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                self._path = _log_dir() / f"debug-{stamp}.log"
            self._enabled = bool(enabled)
            path = str(self._path or "")
        if enabled:
            self.log(
                "debug",
                "enabled",
                {
                    "reason": reason,
                    "app": APP_TITLE,
                    "version": APP_VERSION,
                    "pid": os.getpid(),
                    "python": platform.python_version(),
                    "platform": platform.platform(),
                },
                force=True,
            )
        else:
            self.log("debug", "disabled", {"reason": reason}, force=True)
        return path

    def log(self, category: str, message: str, data: Any | None = None, *, force: bool = False) -> None:
        with self._lock:
            if not self._enabled and not force:
                return
            if self._path is None:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                self._path = _log_dir() / f"debug-{stamp}.log"
            path = self._path

        entry = {
            "ts": _utc_now(),
            "category": category,
            "message": message,
            "data": redact_sensitive(data or {}),
        }
        try:
            line = json.dumps(entry, ensure_ascii=False, default=str)
        except TypeError:
            entry["data"] = str(entry["data"])
            line = json.dumps(entry, ensure_ascii=False, default=str)

        with self._lock:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
            except OSError:
                pass


debug_logger = DebugLogger()


def debug_log(category: str, message: str, data: Any | None = None, *, force: bool = False) -> None:
    debug_logger.log(category, message, data, force=force)
