from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import filecmp
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
import traceback

import PySide6
from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget, QGraphicsDropShadowEffect

try:
    from i18n import Translator, normalize_language
except Exception:  # pragma: no cover - updater can still show Portuguese fallback text.
    Translator = None

    def normalize_language(language: str | None) -> str:
        return "pt"


SKIP_NAMES = {"felb_settings.json", "__pycache__", "extracted"}
APP_EXE_NAME = "GG Coalition.exe"
UPDATER_EXE_NAME = "GG Updater.exe"
COLORS = {
    "bg": "#070b16",
    "card": "#111c31",
    "text": "#edf6ff",
    "muted": "#99abc4",
    "accent": "#5eead4",
    "warning": "#ffd166",
    "error": "#ff6b6b",
    "line": "#2d496f",
}
THEME_DEFAULT = {
    "accent": "#5eead4",
    "success": "#62d7a4",
    "warning": "#f59e0b",
    "danger": "#ff7a90",
    "background": "#070b16",
    "surface": "#111c31",
    "surface_alt": "#0e1a2d",
    "surface_raised": "#172943",
    "control": "#1d3353",
    "text": "#edf6ff",
    "muted_text": "#9fb3c8",
    "disabled_text": "#7f93ad",
    "border": "#2b4b68",
    "gradient_start": "#070b16",
    "gradient_end": "#12243a",
    "gradient_enabled": False,
    "card_radius": 8,
}
THEME_PRESETS = {
    "coalition": {},
    "warden": {
        "accent": "#93c5fd",
        "success": "#7dd3fc",
        "warning": "#facc15",
        "background": "#07111d",
        "surface": "#101827",
        "text": "#edf6ff",
        "muted_text": "#b6c7d9",
        "border": "#2e4b68",
        "gradient_start": "#07111d",
        "gradient_end": "#1b2a3e",
        "gradient_enabled": True,
    },
    "ember": {
        "accent": "#fb7185",
        "success": "#34d399",
        "warning": "#f59e0b",
        "background": "#170b12",
        "surface": "#26151f",
        "text": "#fff1f2",
        "muted_text": "#e7b5c2",
        "border": "#713247",
        "gradient_start": "#170b12",
        "gradient_end": "#3a1827",
        "gradient_enabled": True,
        "card_radius": 10,
    },
    "light": {
        "accent": "#2563eb",
        "success": "#059669",
        "warning": "#d97706",
        "background": "#eef4fb",
        "surface": "#ffffff",
        "text": "#0f172a",
        "muted_text": "#475569",
        "disabled_text": "#64748b",
        "border": "#b9c8dc",
        "control": "#dbeafe",
        "gradient_start": "#f8fbff",
        "gradient_end": "#dceafe",
        "gradient_enabled": True,
    },
    "midnight": {
        "accent": "#38bdf8",
        "success": "#22c55e",
        "warning": "#eab308",
        "background": "#020617",
        "surface": "#0b1224",
        "text": "#f8fafc",
        "muted_text": "#94a3b8",
        "border": "#1e3a5f",
        "gradient_start": "#020617",
        "gradient_end": "#111827",
        "gradient_enabled": True,
        "card_radius": 6,
    },
    "verdant": {
        "accent": "#84cc16",
        "success": "#22c55e",
        "warning": "#fbbf24",
        "background": "#07120b",
        "surface": "#101d15",
        "text": "#f2ffe8",
        "muted_text": "#b4c9aa",
        "border": "#355430",
        "gradient_start": "#07120b",
        "gradient_end": "#172812",
        "gradient_enabled": True,
    },
    "signal": {
        "accent": "#f97316",
        "success": "#10b981",
        "warning": "#facc15",
        "background": "#11100b",
        "surface": "#1d1a14",
        "text": "#fff7ed",
        "muted_text": "#d7c6a8",
        "border": "#60412b",
        "gradient_start": "#11100b",
        "gradient_end": "#2a1a12",
        "gradient_enabled": True,
        "card_radius": 6,
    },
    "aurora": {
        "accent": "#a78bfa",
        "success": "#5eead4",
        "warning": "#f0abfc",
        "background": "#0f1020",
        "surface": "#181827",
        "text": "#f8f7ff",
        "muted_text": "#c8bddc",
        "border": "#4b3d71",
        "gradient_start": "#0f1020",
        "gradient_end": "#17233b",
        "gradient_enabled": True,
        "card_radius": 12,
    },
    "accessible": {
        "accent": "#8ab4ff",
        "success": "#8ab4ff",
        "warning": "#f0abfc",
        "background": "#050b16",
        "surface": "#101b2f",
        "text": "#f8fafc",
        "muted_text": "#bfdbfe",
        "border": "#3b82f6",
        "gradient_start": "#050b16",
        "gradient_end": "#1b2240",
    },
}
COLORBLIND_THEME_OVERRIDES = {
    "unsure": {"accent": "#3b82f6", "success": "#38bdf8", "warning": "#f97316", "danger": "#ec4899", "border": "#3b82f6", "control": "#1d3353"},
    "deuteranopia": {"accent": "#2563eb", "success": "#06b6d4", "warning": "#f59e0b", "danger": "#db2777", "border": "#3b82f6", "control": "#1d3353"},
    "protanopia": {"accent": "#1d4ed8", "success": "#0891b2", "warning": "#fbbf24", "danger": "#c026d3", "border": "#3b82f6", "control": "#1d3353"},
    "tritanopia": {"accent": "#ec4899", "success": "#14b8a6", "warning": "#f97316", "danger": "#f43f5e", "border": "#ec4899", "control": "#3a2145"},
    "achromatopsia": {"accent": "#f8fafc", "success": "#f8fafc", "warning": "#e2e8f0", "danger": "#ffffff", "border": "#f8fafc", "control": "#334155"},
}

UPDATER_FALLBACK_PT = {
    "update.runner_window_title": "GG Coalition Launcher",
    "update.runner_heading": "Atualizando GG Coalition",
    "update.runner_prepare": "Preparando atualizacao...",
    "update.runner_wait_app": "Aguardando o aplicativo fechar...",
    "update.runner_closing_app": "Fechando GG Coalition aberto...",
    "update.runner_close_failed": "Nao consegui fechar o GG Coalition para atualizar. Feche pelo Gerenciador de Tarefas e tente novamente: {detail}",
    "update.runner_installing_files": "Instalando arquivos...",
    "update.runner_wait_file": "Aguardando arquivo liberar...",
    "update.runner_wait_file_detail": "{file} tentativa {attempt}/{attempts}. Feche o GG Coalition se ele ainda estiver aberto.",
    "update.runner_locked_saved": "Arquivo em uso salvo para proxima abertura.",
    "update.runner_using_extracted": "Usando pacote extraido...",
    "update.runner_extracting": "Extraindo pacote...",
    "update.runner_zip_not_found": "ZIP nao encontrado: {path}",
    "update.runner_zip_invalid": "Arquivo de update invalido: {path}",
    "update.runner_zip_incomplete": "ZIP de update incompleto. Faltando: {missing}. Use o release\\GG-Coalition.zip gerado pelo build.",
    "update.runner_app_missing": "Aplicativo atualizado nao encontrado. Procurei por {app} em {target}.",
    "update.runner_opening_app": "Abrindo GG Coalition...",
    "update.runner_install_target": "Destino da instalacao...",
    "update.runner_target_invalid": "Destino de atualizacao invalido: {target}",
    "update.runner_completed": "Atualizacao concluida.",
    "update.runner_done": "Pronto",
    "update.runner_failed": "Erro ao atualizar.",
    "update.runner_log": "{message}\nLog: {log}",
}


def load_updater_language() -> str | None:
    env_language = os.getenv("GG_COALITION_LANGUAGE")
    if env_language:
        return normalize_language(env_language)
    base = os.getenv("LOCALAPPDATA")
    candidates = []
    if base:
        candidates.append(Path(base) / "GG Coalition" / "felb_settings.json")
    candidates.append(Path.home() / "GG Coalition" / "felb_settings.json")
    candidates.append(Path(__file__).resolve().parent / "user_data" / "felb_settings.json")
    for path in candidates:
        try:
            language = json.loads(path.read_text(encoding="utf-8")).get("language")
        except (OSError, json.JSONDecodeError, AttributeError):
            continue
        if language and language != "auto":
            return normalize_language(str(language))
    return None


def updater_data_candidates(filename: str) -> list[Path]:
    candidates: list[Path] = []
    base = os.getenv("LOCALAPPDATA")
    if base:
        candidates.append(Path(base) / "GG Coalition" / filename)
    candidates.append(Path.home() / "GG Coalition" / filename)
    candidates.append(Path(__file__).resolve().parent / "user_data" / filename)
    return candidates


def read_first_json(filename: str) -> dict:
    for path in updater_data_candidates(filename):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def sanitize_hex_color(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        return text.lower()
    if re.fullmatch(r"[0-9a-fA-F]{6}", text):
        return f"#{text.lower()}"
    return fallback


def sanitize_card_radius(value: object) -> int:
    try:
        radius = int(value)
    except (TypeError, ValueError):
        return int(THEME_DEFAULT["card_radius"])
    return max(4, min(12, radius))


def load_updater_theme() -> dict[str, object]:
    settings = read_first_json("felb_personalization.json")
    legacy_settings = read_first_json("felb_settings.json")
    theme_settings = settings.get("theme") if isinstance(settings.get("theme"), dict) else {}
    if not theme_settings and isinstance(legacy_settings.get("app"), dict):
        legacy_theme = legacy_settings["app"].get("theme")
        theme_settings = legacy_theme if isinstance(legacy_theme, dict) else {}
    preset = str(theme_settings.get("preset") or "coalition")
    if bool(settings.get("colorblind_mode_enabled", False)):
        preset = "accessible"

    palette = dict(THEME_DEFAULT)
    if preset == "custom":
        custom = theme_settings.get("custom") if isinstance(theme_settings.get("custom"), dict) else {}
        for key, fallback in THEME_DEFAULT.items():
            if key in {"gradient_enabled", "card_radius"}:
                continue
            palette[key] = sanitize_hex_color(custom.get(key), str(fallback))
        palette["gradient_enabled"] = bool(custom.get("gradient_enabled", THEME_DEFAULT["gradient_enabled"]))
        palette["card_radius"] = sanitize_card_radius(custom.get("card_radius"))
    else:
        palette.update(THEME_PRESETS.get(preset, THEME_PRESETS["coalition"]))
        if preset == "accessible":
            profile = str(settings.get("colorblind_profile") or "unsure")
            palette.update(COLORBLIND_THEME_OVERRIDES.get(profile, COLORBLIND_THEME_OVERRIDES["unsure"]))

    for key, fallback in THEME_DEFAULT.items():
        if key in {"gradient_enabled", "card_radius"}:
            continue
        palette[key] = sanitize_hex_color(palette.get(key), str(fallback))
    palette["card_radius"] = sanitize_card_radius(palette.get("card_radius"))
    palette["gradient_enabled"] = bool(palette.get("gradient_enabled"))
    return palette


class FallbackTranslator:
    def t(self, key: str, **kwargs) -> str:
        value = UPDATER_FALLBACK_PT.get(key, key)
        if kwargs:
            try:
                return value.format(**kwargs)
            except Exception:
                return value
        return value


TR = Translator(load_updater_language()) if Translator is not None else FallbackTranslator()


def _t(key: str, **kwargs) -> str:
    return TR.t(key, **kwargs)


def configure_qt_runtime() -> None:
    pyside_dir = Path(PySide6.__file__).resolve().parent
    try:
        os.add_dll_directory(str(pyside_dir))
    except (AttributeError, OSError):
        pass
    os.environ["PATH"] = str(pyside_dir) + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("QT_PLUGIN_PATH", str(pyside_dir / "plugins"))


class UpdateWindow(QObject):
    progress_requested = Signal(int, str, str, str)
    close_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.window = QWidget()
        self.window.setWindowTitle(_t("update.runner_window_title"))
        self.window.setFixedSize(540, 280)
        self.window.setWindowFlags(self.window.windowFlags() | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.window.setAttribute(Qt.WA_TranslucentBackground)
        self._theme = load_updater_theme()
        self._accent = self.color("accent")

        outer = QVBoxLayout(self.window)
        outer.setContentsMargins(20, 20, 20, 20)
        panel = QWidget()
        panel.setObjectName("panel")
        
        shadow = QGraphicsDropShadowEffect(self.window)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 0)
        panel.setGraphicsEffect(shadow)
        
        outer.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        heading = QLabel(_t("update.runner_heading"))
        heading.setObjectName("heading")
        layout.addWidget(heading)

        self.status_label = QLabel(_t("update.runner_prepare"))
        self.status_label.setObjectName("status")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        progress_row = QHBoxLayout()
        self.phase_label = QLabel(_t("update.runner_prepare"))
        self.phase_label.setObjectName("phase")
        progress_row.addWidget(self.phase_label)
        progress_row.addStretch(1)
        self.percent_label = QLabel("0%")
        self.percent_label.setObjectName("percent")
        self.percent_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        progress_row.addWidget(self.percent_label)
        layout.addLayout(progress_row)

        self.detail_label = QLabel("")
        self.detail_label.setObjectName("detail")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label, stretch=1)

        self._apply_style()

        self.progress_requested.connect(self._set_progress)
        self.close_requested.connect(self._close_with_quit)
        self.center()
        self.window.show()

    def center(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        rect = screen.availableGeometry()
        frame = self.window.frameGeometry()
        frame.moveCenter(rect.center())
        self.window.move(frame.topLeft())

    def _apply_style(self) -> None:
        gradient_start = self.color("gradient_start") if self._theme.get("gradient_enabled") else self.color("surface")
        gradient_end = self.color("gradient_end") if self._theme.get("gradient_enabled") else self.color("background")
        radius = int(self._theme.get("card_radius", 8)) + 6
        self.window.setStyleSheet(
            f"""
            QWidget {{ font-family: "Segoe UI", sans-serif; }}
            #panel {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {gradient_start}, stop:1 {gradient_end}); border: 1px solid {self.color("border")}; border-radius: {radius}px; }}
            QLabel#heading {{ font-size: 24px; font-weight: bold; color: {self.color("text")}; }}
            QLabel#status {{ font-size: 14px; color: {self.color("muted_text")}; }}
            QLabel#phase {{ font-size: 12px; font-weight: bold; color: {self._accent}; background: {self.color("control")}; padding: 5px 12px; border-radius: 6px; }}
            QLabel#percent {{ font-size: 32px; font-weight: bold; color: {self._accent}; margin-top: -10px; }}
            QLabel#detail {{ font-size: 12px; color: {self.color("disabled_text")}; }}
            QProgressBar {{ border: 1px solid {self.color("border")}; border-radius: 8px; background: {self.color("background")}; height: 16px; }}
            QProgressBar::chunk {{ background: {self._accent}; border-radius: 7px; }}
            """
        )

    def color(self, key: str) -> str:
        fallback = {
            "background": COLORS["bg"],
            "surface": COLORS["card"],
            "text": COLORS["text"],
            "muted_text": COLORS["muted"],
            "disabled_text": COLORS["muted"],
            "border": COLORS["line"],
            "accent": COLORS["accent"],
            "warning": COLORS["warning"],
            "danger": COLORS["error"],
        }.get(key, COLORS["accent"])
        return sanitize_hex_color(self._theme.get(key), fallback)

    def _resolve_accent(self, accent: str | None) -> str:
        if not accent or accent == COLORS["accent"]:
            return self.color("accent")
        if accent == COLORS["warning"]:
            return self.color("warning")
        if accent == COLORS["error"]:
            return self.color("danger")
        return sanitize_hex_color(accent, self.color("accent"))

    def set_progress(self, value: int, status: str, detail: str = "", accent: str | None = None) -> None:
        self.progress_requested.emit(value, status, detail, self._resolve_accent(accent))

    @Slot(int, str, str, str)
    def _set_progress(self, value: int, status: str, detail: str = "", accent: str = "") -> None:
        safe_value = max(0, min(100, int(value)))
        if accent and accent != self._accent:
            self._accent = accent
            self._apply_style()
        self.progress.setValue(safe_value)
        self.percent_label.setText(f"{safe_value}%")
        self.phase_label.setText(status)
        self.status_label.setText(status)
        self.detail_label.setText(detail)

    def close(self) -> None:
        self.close_requested.emit()

    @Slot()
    def _close_with_quit(self) -> None:
        QTimer.singleShot(650, self._finish)

    def _finish(self) -> None:
        self.window.close()
        app = QApplication.instance()
        if app:
            app.quit()


def wait_for_process(pid: int, window: UpdateWindow, timeout: float = 25.0) -> None:
    if pid <= 0:
        return
    if os.name == "nt":
        wait_for_process_windows(pid, window, timeout)
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        window.set_progress(15, _t("update.runner_wait_app"), f"PID {pid}", COLORS["warning"])
        time.sleep(0.25)


def wait_for_process_windows(pid: int, window: UpdateWindow, timeout: float) -> None:
    synchronize = 0x00100000
    wait_timeout = 0x00000102
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(synchronize, False, pid)
    if not handle:
        return
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            window.set_progress(15, _t("update.runner_wait_app"), f"PID {pid}", COLORS["warning"])
            result = kernel32.WaitForSingleObject(handle, 250)
            if result != wait_timeout:
                return
    finally:
        kernel32.CloseHandle(handle)


def close_installed_app_processes(target: Path, window: UpdateWindow, timeout: float = 12.0) -> None:
    if os.name != "nt":
        return
    target = target.resolve()
    current_pid = os.getpid()
    matches = matching_processes_in_dir(target, {APP_EXE_NAME.lower(), UPDATER_EXE_NAME.lower()}, exclude_pid=current_pid)
    if not matches:
        return
    names = ", ".join(f"{name} (PID {pid})" for pid, name in matches)
    window.set_progress(18, _t("update.runner_closing_app"), names, COLORS["warning"])
    for pid, _name in matches:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remaining = matching_processes_in_dir(target, {APP_EXE_NAME.lower(), UPDATER_EXE_NAME.lower()}, exclude_pid=current_pid)
        if not remaining:
            return
        detail = ", ".join(f"{name} (PID {pid})" for pid, name in remaining)
        window.set_progress(20, _t("update.runner_wait_app"), detail, COLORS["warning"])
        time.sleep(0.5)
    remaining = matching_processes_in_dir(target, {APP_EXE_NAME.lower(), UPDATER_EXE_NAME.lower()}, exclude_pid=current_pid)
    if remaining:
        detail = ", ".join(f"{name} (PID {pid})" for pid, name in remaining)
        raise RuntimeError(
            _t("update.runner_close_failed", detail=detail)
        )


def matching_processes_in_dir(target: Path, names: set[str], exclude_pid: int) -> list[tuple[int, str]]:
    kernel32 = ctypes.windll.kernel32
    matches: dict[int, str] = {}
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        return []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        has_entry = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while has_entry:
            pid = int(entry.th32ProcessID)
            if pid and pid != exclude_pid and pid not in matches:
                process_path = process_path_for_pid(kernel32, pid)
                if process_path:
                    path = Path(process_path)
                    if path.name.lower() in names and is_relative_to(path.parent, target):
                        matches[pid] = path.name
            has_entry = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return sorted(matches.items())


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def process_path_for_pid(kernel32, pid: int) -> str:
    process_query_limited_information = 0x1000
    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        return ""
    try:
        path_buffer = ctypes.create_unicode_buffer(32768)
        size = ctypes.c_ulong(len(path_buffer))
        if kernel32.QueryFullProcessImageNameW(handle, 0, path_buffer, ctypes.byref(size)):
            return path_buffer.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def copy_tree(source: Path, target: Path, window: UpdateWindow) -> None:
    target.mkdir(parents=True, exist_ok=True)
    files = [file for file in source.rglob("*") if file.is_file() and not any(part in SKIP_NAMES for part in file.parts)]
    total = max(1, len(files))
    for index, file in enumerate(files, start=1):
        relative = file.relative_to(source)
        if relative.name in SKIP_NAMES:
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        window.set_progress(45 + int((index / total) * 40), _t("update.runner_installing_files"), str(relative))
        if same_file(file, destination) or same_content(file, destination):
            continue
        try:
            copy_with_retry(file, destination, window)
        except OSError as exc:
            if can_stage_locked_file(destination, exc):
                save_locked_file_copy(file, destination, window)
            else:
                raise


def same_file(source: Path, destination: Path) -> bool:
    try:
        return source.resolve() == destination.resolve()
    except OSError:
        return False


def same_content(source: Path, destination: Path) -> bool:
    try:
        if not destination.exists() or not destination.is_file():
            return False
        source_stat = source.stat()
        destination_stat = destination.stat()
        if source_stat.st_size != destination_stat.st_size:
            return False
        return filecmp.cmp(source, destination, shallow=False)
    except OSError:
        return False


def copy_with_retry(source: Path, destination: Path, window: UpdateWindow, attempts: int = 45) -> None:
    last_error: OSError | None = None
    for attempt in range(1, attempts + 1):
        try:
            shutil.copy2(source, destination)
            return
        except OSError as exc:
            if not is_locked_file_error(exc):
                raise
            last_error = exc
            if can_stage_locked_file(destination, exc):
                raise
            close_installed_app_processes(destination.parent, window, timeout=3.0)
            window.set_progress(
                80,
                _t("update.runner_wait_file"),
                _t("update.runner_wait_file_detail", file=destination.name, attempt=attempt, attempts=attempts),
                COLORS["warning"],
            )
            time.sleep(1)
    if last_error:
        raise last_error


def is_locked_file_error(exc: OSError) -> bool:
    return isinstance(exc, PermissionError) or getattr(exc, "winerror", None) == 32


def can_stage_locked_file(destination: Path, exc: OSError) -> bool:
    if not is_locked_file_error(exc):
        return False
    return destination.name.lower() != APP_EXE_NAME.lower()


def save_locked_file_copy(source: Path, destination: Path, window: UpdateWindow) -> None:
    old_file = destination.with_name(f"{destination.name}.old")
    if old_file.exists():
        try:
            old_file.unlink()
        except OSError:
            pass
    try:
        destination.rename(old_file)
    except OSError:
        pass
    shutil.copy2(source, destination)
    window.set_progress(85, _t("update.runner_locked_saved"), destination.name)


def extract_zip(zip_path: Path, window: UpdateWindow) -> Path:
    packaged_source = Path(sys.executable).resolve().parent
    if (packaged_source / APP_EXE_NAME).exists() and (packaged_source / UPDATER_EXE_NAME).exists():
        window.set_progress(25, _t("update.runner_using_extracted"), str(packaged_source))
        return packaged_source
    validate_update_zip(zip_path)
    temp_dir = Path(tempfile.mkdtemp(prefix="gg_coalition_update_"))
    window.set_progress(25, _t("update.runner_extracting"), zip_path.name)
    with zipfile.ZipFile(zip_path, "r") as archive:
        safe_extractall(archive, temp_dir)

    entries = [item for item in temp_dir.iterdir()]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return temp_dir


def validate_update_zip(zip_path: Path) -> None:
    if not zip_path.exists():
        raise RuntimeError(_t("update.runner_zip_not_found", path=zip_path))
    if not zipfile.is_zipfile(zip_path):
        raise RuntimeError(_t("update.runner_zip_invalid", path=zip_path))
    with zipfile.ZipFile(zip_path, "r") as archive:
        validate_zip_member_paths(archive)
        names = {Path(name).name.lower() for name in archive.namelist()}
    missing = [name for name in (APP_EXE_NAME,) if name.lower() not in names]
    if missing:
        raise RuntimeError(
            _t("update.runner_zip_incomplete", missing=", ".join(missing))
        )


def validate_zip_member_paths(archive: zipfile.ZipFile) -> None:
    for member in archive.infolist():
        normalized = member.filename.replace("\\", "/")
        path = PurePosixPath(normalized)
        if not normalized or path.is_absolute() or ".." in path.parts:
            raise RuntimeError(_t("update.runner_zip_invalid", path=member.filename))


def safe_extractall(archive: zipfile.ZipFile, target: Path) -> None:
    validate_zip_member_paths(archive)
    target.mkdir(parents=True, exist_ok=True)
    target_root = target.resolve()
    for member in archive.infolist():
        destination = (target / member.filename).resolve()
        try:
            destination.relative_to(target_root)
        except ValueError as exc:
            raise RuntimeError(_t("update.runner_zip_invalid", path=member.filename)) from exc
        archive.extract(member, target)


def resolve_launch_target(launch: Path, target: Path) -> Path:
    candidates = [
        launch,
        target / APP_EXE_NAME,
        target / "GG Coalition Launcher.exe",
    ]
    candidates.extend(
        sorted(
            [
                item
                for item in target.glob("*.exe")
                if item.name.lower() != UPDATER_EXE_NAME.lower()
            ],
            key=lambda item: item.stat().st_size if item.exists() else 0,
            reverse=True,
        )
    )
    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate.resolve()
        except OSError:
            continue
    raise RuntimeError(
        _t("update.runner_app_missing", app=APP_EXE_NAME, target=target)
    )


def launch_app(launch: Path, target: Path, window: UpdateWindow) -> None:
    launch = resolve_launch_target(launch, target)
    window.set_progress(95, _t("update.runner_opening_app"), str(launch))
    cwd = launch.parent if launch.parent.exists() else target
    try:
        if launch.suffix.lower() == ".py":
            subprocess.Popen([sys.executable, str(launch)], cwd=str(cwd), close_fds=True)
        else:
            subprocess.Popen([str(launch)], cwd=str(cwd), close_fds=True)
    except OSError:
        if os.name == "nt" and launch.exists():
            os.startfile(str(launch))
        else:
            raise


def write_error_log(target: Path, exc: Exception) -> Path:
    log_path = target / "GG Updater Error.log"
    try:
        log_path.write_text(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            encoding="utf-8",
        )
    except OSError:
        log_path = Path(tempfile.gettempdir()) / "GG Updater Error.log"
        log_path.write_text(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            encoding="utf-8",
        )
    return log_path


def run_update(args, window: UpdateWindow) -> None:
    try:
        zip_path = Path(args.zip)
        target = Path(args.target).resolve()
        launch = Path(args.launch)
        window.set_progress(5, _t("update.runner_prepare"), zip_path.name)
        window.set_progress(8, _t("update.runner_install_target"), str(target))
        wait_for_process(args.pid, window)
        close_installed_app_processes(target, window)
        source = extract_zip(zip_path, window)
        if same_file(source / APP_EXE_NAME, target / APP_EXE_NAME):
            raise RuntimeError(_t("update.runner_target_invalid", target=target))
        copy_tree(source, target, window)
        launch_app(launch, target, window)
        window.set_progress(100, _t("update.runner_completed"), _t("update.runner_done"), COLORS["accent"])
    except Exception as exc:
        target = Path(getattr(args, "target", tempfile.gettempdir()))
        log_path = write_error_log(target, exc)
        window.set_progress(100, _t("update.runner_failed"), _t("update.runner_log", message=exc, log=log_path), COLORS["error"])
        time.sleep(10)
    finally:
        window.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--launch", required=True)
    parser.add_argument("--pid", type=int, default=0)
    args = parser.parse_args()

    configure_qt_runtime()
    app = QApplication(sys.argv)
    window = UpdateWindow()
    threading.Thread(target=run_update, args=(args, window), daemon=True).start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
