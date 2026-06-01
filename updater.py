from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import filecmp
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk
import zipfile
import traceback


SKIP_NAMES = {"felb_settings.json", "__pycache__", "extracted"}
APP_EXE_NAME = "GG Coalition.exe"
UPDATER_EXE_NAME = "GG Updater.exe"
COLORS = {
    "bg": "#070b16",
    "card": "#111c31",
    "text": "#edf6ff",
    "muted": "#99abc4",
    "accent": "#5eead4",
    "line": "#2d496f",
}


class UpdateWindow:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("GG Coalition Launcher")
        self.root.geometry("460x240")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS["bg"])
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor=COLORS["bg"], background=COLORS["accent"], bordercolor=COLORS["line"])

        panel = tk.Frame(self.root, bg=COLORS["card"], highlightthickness=1, highlightbackground=COLORS["line"])
        panel.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(panel, text="Atualizando GG Coalition", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).pack(
            anchor="w", padx=22, pady=(22, 4)
        )
        self.status_var = tk.StringVar(value="Preparando atualizacao...")
        tk.Label(panel, textvariable=self.status_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(
            anchor="w", padx=22, pady=(0, 18)
        )
        self.progress = ttk.Progressbar(panel, mode="determinate", maximum=100, value=0)
        self.progress.pack(fill="x", padx=22, pady=(0, 14))
        self.detail_var = tk.StringVar(value="")
        tk.Label(panel, textvariable=self.detail_var, bg=COLORS["card"], fg=COLORS["accent"], font=("Segoe UI", 9, "bold"), wraplength=390, justify="left").pack(
            anchor="w", padx=22
        )
        self.center()

    def center(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def set_progress(self, value: int, status: str, detail: str = "") -> None:
        self.root.after(0, self._set_progress, value, status, detail)

    def _set_progress(self, value: int, status: str, detail: str = "") -> None:
        self.progress.configure(value=value)
        self.status_var.set(status)
        self.detail_var.set(detail)

    def close(self) -> None:
        self.root.after(650, self.root.destroy)


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
        window.set_progress(15, "Aguardando o aplicativo fechar...", f"PID {pid}")
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
            window.set_progress(15, "Aguardando o aplicativo fechar...", f"PID {pid}")
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
    window.set_progress(18, "Fechando GG Coalition aberto...", names)
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
        window.set_progress(20, "Aguardando o aplicativo fechar...", detail)
        time.sleep(0.5)
    remaining = matching_processes_in_dir(target, {APP_EXE_NAME.lower(), UPDATER_EXE_NAME.lower()}, exclude_pid=current_pid)
    if remaining:
        detail = ", ".join(f"{name} (PID {pid})" for pid, name in remaining)
        raise RuntimeError(
            "Nao consegui fechar o GG Coalition para atualizar. "
            f"Feche pelo Gerenciador de Tarefas e tente novamente: {detail}"
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
        window.set_progress(45 + int((index / total) * 40), "Instalando arquivos...", str(relative))
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
                "Aguardando arquivo liberar...",
                f"{destination.name} tentativa {attempt}/{attempts}. Feche o GG Coalition se ele ainda estiver aberto.",
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
    pending = destination.with_name(f"{destination.name}.new")
    shutil.copy2(source, pending)
    window.set_progress(85, "Arquivo em uso salvo para proxima abertura.", pending.name)


def extract_zip(zip_path: Path, window: UpdateWindow) -> Path:
    packaged_source = Path(sys.executable).resolve().parent
    if (packaged_source / APP_EXE_NAME).exists() and (packaged_source / UPDATER_EXE_NAME).exists():
        window.set_progress(25, "Usando pacote extraido...", str(packaged_source))
        return packaged_source
    validate_update_zip(zip_path)
    temp_dir = Path(tempfile.mkdtemp(prefix="gg_coalition_update_"))
    window.set_progress(25, "Extraindo pacote...", zip_path.name)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(temp_dir)

    entries = [item for item in temp_dir.iterdir()]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return temp_dir


def validate_update_zip(zip_path: Path) -> None:
    if not zip_path.exists():
        raise RuntimeError(f"ZIP nao encontrado: {zip_path}")
    if not zipfile.is_zipfile(zip_path):
        raise RuntimeError(f"Arquivo de update invalido: {zip_path}")
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = {Path(name).name.lower() for name in archive.namelist()}
    missing = [name for name in (APP_EXE_NAME,) if name.lower() not in names]
    if missing:
        raise RuntimeError(
            "ZIP de update incompleto. Faltando: "
            + ", ".join(missing)
            + ". Use o release\\GG-Coalition.zip gerado pelo build."
        )


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
        "Aplicativo atualizado nao encontrado. Procurei por "
        f"{APP_EXE_NAME} em {target}."
    )


def launch_app(launch: Path, target: Path, window: UpdateWindow) -> None:
    launch = resolve_launch_target(launch, target)
    window.set_progress(95, "Abrindo GG Coalition...", str(launch))
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
        window.set_progress(5, "Preparando atualizacao...", zip_path.name)
        window.set_progress(8, "Destino da instalacao...", str(target))
        wait_for_process(args.pid, window)
        close_installed_app_processes(target, window)
        source = extract_zip(zip_path, window)
        if same_file(source / APP_EXE_NAME, target / APP_EXE_NAME):
            raise RuntimeError(f"Destino de atualizacao invalido: {target}")
        copy_tree(source, target, window)
        launch_app(launch, target, window)
        window.set_progress(100, "Atualizacao concluida.", "Pronto")
    except Exception as exc:
        target = Path(getattr(args, "target", tempfile.gettempdir()))
        log_path = write_error_log(target, exc)
        window.set_progress(100, "Erro ao atualizar.", f"{exc}\nLog: {log_path}")
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

    window = UpdateWindow()
    threading.Thread(target=run_update, args=(args, window), daemon=True).start()
    window.root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
