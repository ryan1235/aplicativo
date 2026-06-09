from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import filecmp
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
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

    def __init__(self) -> None:
        super().__init__()
        self.window = QWidget()
        self.window.setWindowTitle(_t("update.runner_window_title"))
        self.window.setFixedSize(540, 280)
        self.window.setWindowFlags(self.window.windowFlags() | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.window.setAttribute(Qt.WA_TranslucentBackground)
        self._accent = COLORS["accent"]

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
        self.window.setStyleSheet(
            f"""
            QWidget {{ font-family: "Segoe UI", sans-serif; }}
            #panel {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #111c31, stop:1 #070b16); border: 1px solid {self._accent}; border-radius: 14px; }}
            QLabel#heading {{ font-size: 24px; font-weight: bold; color: #edf6ff; }}
            QLabel#status {{ font-size: 14px; color: #a4b9d6; }}
            QLabel#phase {{ font-size: 12px; font-weight: bold; color: {self._accent}; background: rgba(255, 255, 255, 0.08); padding: 5px 12px; border-radius: 6px; }}
            QLabel#percent {{ font-size: 32px; font-weight: bold; color: {self._accent}; margin-top: -10px; }}
            QLabel#detail {{ font-size: 12px; color: #7f93ad; }}
            QProgressBar {{ border: 1px solid #1e3554; border-radius: 8px; background: #070b16; height: 16px; }}
            QProgressBar::chunk {{ background: {self._accent}; border-radius: 7px; }}
            """
        )

    def set_progress(self, value: int, status: str, detail: str = "", accent: str | None = None) -> None:
        self.progress_requested.emit(value, status, detail, accent or COLORS["accent"])

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
        QTimer.singleShot(650, self.window.close)


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
