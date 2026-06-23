from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.request
import zipfile

import PySide6
from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QIcon, QMovie
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "GG Coalition"
APP_EXE_NAME = "GG Coalition.exe"
REPO = "ryan1235/aplicativo"
GITHUB_LATEST_RELEASE = f"https://api.github.com/repos/{REPO}/releases/latest"
MIN_ZIP_SIZE = 1024 * 1024
INSTALL_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "Programs" / APP_NAME
ICON_PATH = Path(__file__).resolve().parent / "img" / "app_icon.ico"
GIF_PATH = Path(__file__).resolve().parent / "img" / "ggimege.gif"
USER_AGENT = "GG-Coalition-Web-Setup/1.0"


TEXT = {
    "pt": {
        "language": "Idioma",
        "title": "Instalar GG Coalition",
        "subtitle": "Baixa a versão mais recente do GitHub e instala automaticamente.",
        "welcome_title": "Instalar GG Coalition",
        "welcome_body": "Este assistente baixa a versão mais recente e prepara tudo em poucos passos.",
        "mode_title": "Escolha como instalar",
        "mode_body": "Confira o destino da instalação e clique em instalar.",
        "existing_short": "Já existe uma instalação. Marque instalação limpa se quiser remover os arquivos antigos.",
        "install_path": "Destino",
        "clean_choice": "Fazer instalação limpa",
        "update_choice": "Atualizar mantendo arquivos existentes",
        "next": "Próximo",
        "back": "Voltar",
        "finish": "Concluir",
        "start": "Instalar última versão",
        "clean": "Instalação limpa",
        "open": "Abrir GG Coalition",
        "close": "Fechar",
        "ready": "Pronto para instalar",
        "checking": "Procurando a última versão...",
        "found": "Versão encontrada: {version}",
        "downloading": "Baixando pacote...",
        "extracting": "Extraindo arquivos...",
        "closing": "Fechando versão instalada...",
        "installing": "Instalando arquivos...",
        "shortcuts": "Criando atalhos...",
        "launching": "Abrindo aplicativo...",
        "done": "Instalação concluída.",
        "failed": "Falha na instalação.",
        "existing_title": "Versão já instalada",
        "existing_body": "Encontrei uma instalação em:\n{path}\n\nDeseja fazer uma instalação limpa? Isso remove os arquivos antigos antes de instalar a versão mais recente. Suas configurações em %LOCALAPPDATA%\\GG Coalition são mantidas.",
        "yes_clean": "Sim, instalação limpa",
        "no_keep": "Não, atualizar por cima",
        "cancel": "Cancelar",
        "cleaning": "Removendo instalação antiga...",
        "download_failed": "Download falhou: HTTP {status}",
        "zip_invalid": "O pacote baixado não é um ZIP válido.",
        "zip_incomplete": "O pacote está incompleto. Faltando: {missing}",
        "no_asset": "Não encontrei um ZIP GG-Coalition na última release.",
        "error_log": "Detalhes salvos em: {path}",
    },
    "en": {
        "language": "Language",
        "title": "Install GG Coalition",
        "subtitle": "Downloads the latest GitHub release and installs it automatically.",
        "welcome_title": "Install GG Coalition",
        "welcome_body": "This setup wizard downloads the latest version and gets everything ready in a few steps.",
        "mode_title": "Choose install mode",
        "mode_body": "Confirm the install destination and click install.",
        "existing_short": "An installation already exists. Select clean install to remove the old program files.",
        "install_path": "Destination",
        "clean_choice": "Clean install",
        "update_choice": "Update existing files",
        "next": "Next",
        "back": "Back",
        "finish": "Finish",
        "start": "Install latest version",
        "clean": "Clean install",
        "open": "Open GG Coalition",
        "close": "Close",
        "ready": "Ready to install",
        "checking": "Looking for the latest version...",
        "found": "Version found: {version}",
        "downloading": "Downloading package...",
        "extracting": "Extracting files...",
        "closing": "Closing installed version...",
        "installing": "Installing files...",
        "shortcuts": "Creating shortcuts...",
        "launching": "Opening application...",
        "done": "Installation complete.",
        "failed": "Installation failed.",
        "existing_title": "Version already installed",
        "existing_body": "I found an installation at:\n{path}\n\nDo you want a clean install? This removes old program files before installing the latest version. Your settings in %LOCALAPPDATA%\\GG Coalition are kept.",
        "yes_clean": "Yes, clean install",
        "no_keep": "No, update in place",
        "cancel": "Cancel",
        "cleaning": "Removing old installation...",
        "download_failed": "Download failed: HTTP {status}",
        "zip_invalid": "The downloaded package is not a valid ZIP.",
        "zip_incomplete": "The package is incomplete. Missing: {missing}",
        "no_asset": "No GG-Coalition ZIP asset was found in the latest release.",
        "error_log": "Details saved to: {path}",
    },
    "es": {
        "language": "Idioma",
        "title": "Instalar GG Coalition",
        "subtitle": "Descarga la última versión de GitHub y la instala automáticamente.",
        "welcome_title": "Instalar GG Coalition",
        "welcome_body": "Este asistente descarga la versión más reciente y prepara todo en pocos pasos.",
        "mode_title": "Elige cómo instalar",
        "mode_body": "Confirma el destino de instalación y haz clic en instalar.",
        "existing_short": "Ya existe una instalación. Marca instalación limpia para quitar los archivos antiguos.",
        "install_path": "Destino",
        "clean_choice": "Instalación limpia",
        "update_choice": "Actualizar archivos existentes",
        "next": "Siguiente",
        "back": "Atrás",
        "finish": "Finalizar",
        "start": "Instalar última versión",
        "clean": "Instalación limpia",
        "open": "Abrir GG Coalition",
        "close": "Cerrar",
        "ready": "Listo para instalar",
        "checking": "Buscando la última versión...",
        "found": "Versión encontrada: {version}",
        "downloading": "Descargando paquete...",
        "extracting": "Extrayendo archivos...",
        "closing": "Cerrando versión instalada...",
        "installing": "Instalando archivos...",
        "shortcuts": "Creando accesos directos...",
        "launching": "Abriendo aplicación...",
        "done": "Instalación completada.",
        "failed": "Error en la instalación.",
        "existing_title": "Ya hay una versión instalada",
        "existing_body": "Encontré una instalación en:\n{path}\n\n¿Quieres hacer una instalación limpia? Esto elimina los archivos antiguos antes de instalar la versión más reciente. Tus configuraciones en %LOCALAPPDATA%\\GG Coalition se mantienen.",
        "yes_clean": "Sí, instalación limpia",
        "no_keep": "No, actualizar encima",
        "cancel": "Cancelar",
        "cleaning": "Eliminando instalación antigua...",
        "download_failed": "La descarga falló: HTTP {status}",
        "zip_invalid": "El paquete descargado no es un ZIP válido.",
        "zip_incomplete": "El paquete está incompleto. Falta: {missing}",
        "no_asset": "No encontré un ZIP GG-Coalition en la última release.",
        "error_log": "Detalles guardados en: {path}",
    },
    "fr": {
        "language": "Langue",
        "title": "Installer GG Coalition",
        "subtitle": "Télécharge la dernière version GitHub et l'installe automatiquement.",
        "welcome_title": "Installer GG Coalition",
        "welcome_body": "Cet assistant télécharge la dernière version et prépare tout en quelques étapes.",
        "mode_title": "Choisissez le mode d'installation",
        "mode_body": "Vérifiez la destination puis lancez l'installation.",
        "existing_short": "Une installation existe déjà. Cochez installation propre pour supprimer les anciens fichiers.",
        "install_path": "Destination",
        "clean_choice": "Installation propre",
        "update_choice": "Mettre à jour les fichiers existants",
        "next": "Suivant",
        "back": "Retour",
        "finish": "Terminer",
        "start": "Installer la dernière version",
        "clean": "Installation propre",
        "open": "Ouvrir GG Coalition",
        "close": "Fermer",
        "ready": "Prêt à installer",
        "checking": "Recherche de la dernière version...",
        "found": "Version trouvée : {version}",
        "downloading": "Téléchargement du paquet...",
        "extracting": "Extraction des fichiers...",
        "closing": "Fermeture de la version installée...",
        "installing": "Installation des fichiers...",
        "shortcuts": "Création des raccourcis...",
        "launching": "Ouverture de l'application...",
        "done": "Installation terminée.",
        "failed": "Échec de l'installation.",
        "existing_title": "Version déjà installée",
        "existing_body": "J'ai trouvé une installation dans :\n{path}\n\nVoulez-vous faire une installation propre ? Cela supprime les anciens fichiers avant d'installer la dernière version. Vos paramètres dans %LOCALAPPDATA%\\GG Coalition sont conservés.",
        "yes_clean": "Oui, installation propre",
        "no_keep": "Non, mettre à jour",
        "cancel": "Annuler",
        "cleaning": "Suppression de l'ancienne installation...",
        "download_failed": "Téléchargement échoué : HTTP {status}",
        "zip_invalid": "Le paquet téléchargé n'est pas un ZIP valide.",
        "zip_incomplete": "Le paquet est incomplet. Manquant : {missing}",
        "no_asset": "Aucun ZIP GG-Coalition n'a été trouvé dans la dernière release.",
        "error_log": "Détails enregistrés dans : {path}",
    },
}


@dataclass
class ReleaseAsset:
    version: str
    name: str
    url: str
    size: int


def configure_qt_runtime() -> None:
    pyside_dir = Path(PySide6.__file__).resolve().parent
    try:
        os.add_dll_directory(str(pyside_dir))
    except (AttributeError, OSError):
        pass
    os.environ["PATH"] = str(pyside_dir) + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("QT_PLUGIN_PATH", str(pyside_dir / "plugins"))


def tr(language: str, key: str, **kwargs) -> str:
    value = TEXT.get(language, TEXT["pt"]).get(key, TEXT["pt"].get(key, key))
    if kwargs:
        try:
            return value.format(**kwargs)
        except Exception:
            return value
    return value


def fetch_latest_asset() -> ReleaseAsset:
    request = urllib.request.Request(
        GITHUB_LATEST_RELEASE,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        release = json.loads(response.read().decode("utf-8", errors="replace"))
    version = str(release.get("tag_name") or release.get("name") or "latest")
    assets = release.get("assets") or []
    candidates = [
        item for item in assets
        if str(item.get("name") or "").lower().endswith(".zip")
        and "gg-coalition" in str(item.get("name") or "").lower()
        and item.get("browser_download_url")
    ]
    if not candidates:
        raise RuntimeError("no_asset")
    asset = max(candidates, key=lambda item: int(item.get("size") or 0))
    return ReleaseAsset(
        version=version,
        name=str(asset.get("name") or "GG-Coalition.zip"),
        url=str(asset.get("browser_download_url")),
        size=int(asset.get("size") or 0),
    )


def download_asset(asset: ReleaseAsset, target: Path, progress) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(asset.url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        status = getattr(response, "status", 200)
        if status >= 400:
            raise RuntimeError(("download_failed", status))
        total = int(response.headers.get("Content-Length") or asset.size or 0)
        downloaded = 0
        with target.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                progress(downloaded, total)
    validate_zip(target)
    return target


def validate_zip(path: Path) -> None:
    if path.stat().st_size < MIN_ZIP_SIZE or not zipfile.is_zipfile(path):
        raise RuntimeError("zip_invalid")
    with zipfile.ZipFile(path, "r") as archive:
        validate_zip_paths(archive)
        names = {Path(item.filename).name.lower() for item in archive.infolist()}
    missing = [APP_EXE_NAME] if APP_EXE_NAME.lower() not in names else []
    if missing:
        raise RuntimeError(("zip_incomplete", ", ".join(missing)))


def validate_zip_paths(archive: zipfile.ZipFile) -> None:
    for member in archive.infolist():
        normalized = member.filename.replace("\\", "/")
        path = PurePosixPath(normalized)
        if not normalized or path.is_absolute() or ".." in path.parts:
            raise RuntimeError("zip_invalid")


def extract_zip(zip_path: Path, target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as archive:
        validate_zip_paths(archive)
        root = target.resolve()
        for member in archive.infolist():
            destination = (target / member.filename).resolve()
            try:
                destination.relative_to(root)
            except ValueError as exc:
                raise RuntimeError("zip_invalid") from exc
            archive.extract(member, target)
    entries = [item for item in target.iterdir()]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return target


def close_installed_processes(target: Path) -> None:
    if os.name != "nt" or not target.exists():
        return
    current_pid = os.getpid()
    for pid, name in matching_processes_in_dir(target, {APP_EXE_NAME.lower(), "gg updater.exe"}, current_pid):
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if not matching_processes_in_dir(target, {APP_EXE_NAME.lower(), "gg updater.exe"}, current_pid):
            return
        time.sleep(0.35)


def matching_processes_in_dir(target: Path, names: set[str], exclude_pid: int) -> list[tuple[int, str]]:
    if os.name != "nt":
        return []
    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        return []
    matches: dict[int, str] = {}
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
    handle = kernel32.OpenProcess(0x1000, False, pid)
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


def safe_clean_install_dir(path: Path) -> None:
    target = path.resolve()
    local = Path(os.getenv("LOCALAPPDATA", "")).resolve()
    expected = (local / "Programs" / APP_NAME).resolve()
    if target != expected:
        raise RuntimeError(f"unsafe clean target: {target}")
    if target.exists():
        shutil.rmtree(target)


def copy_tree(source: Path, target: Path, progress) -> None:
    files = [item for item in source.rglob("*") if item.is_file()]
    total = max(1, len(files))
    target.mkdir(parents=True, exist_ok=True)
    for index, file in enumerate(files, start=1):
        relative = file.relative_to(source)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, destination)
        progress(index, total, relative)


def create_shortcuts(install_dir: Path) -> None:
    if os.name != "nt":
        return
    exe = install_dir / APP_EXE_NAME
    if not exe.exists():
        return
    start_menu = Path(os.getenv("APPDATA", str(Path.home()))) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME
    desktop = Path.home() / "Desktop"
    start_menu.mkdir(parents=True, exist_ok=True)
    create_shortcut(start_menu / f"{APP_NAME}.lnk", exe, install_dir)
    create_shortcut(desktop / f"{APP_NAME}.lnk", exe, install_dir)


def create_shortcut(shortcut: Path, target: Path, working_dir: Path) -> None:
    shortcut_text = ps_single_quote(shortcut)
    target_text = ps_single_quote(target)
    working_dir_text = ps_single_quote(working_dir)
    ps = (
        "$shell=New-Object -ComObject WScript.Shell; "
        f"$s=$shell.CreateShortcut('{shortcut_text}'); "
        f"$s.TargetPath='{target_text}'; "
        f"$s.WorkingDirectory='{working_dir_text}'; "
        "$s.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def ps_single_quote(value: Path | str) -> str:
    return str(value).replace("'", "''")


def launch_app(install_dir: Path) -> None:
    exe = install_dir / APP_EXE_NAME
    if exe.exists():
        subprocess.Popen([str(exe)], cwd=str(install_dir), close_fds=True)


def write_error(exc: BaseException) -> Path:
    target = Path(os.getenv("TEMP", str(Path.home()))) / "GG-Coalition-Web-Setup.log"
    target.write_text("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)), encoding="utf-8")
    return target


class InstallerSignals(QObject):
    progress = Signal(int, str, str, str)
    finished = Signal(bool, str, str)


class InstallerWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.language = "pt"
        self.signals = InstallerSignals()
        self.signals.progress.connect(self.set_progress)
        self.signals.finished.connect(self.finish)
        self.install_complete = False
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(720, 460)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.build_ui()
        self.apply_text()
        self.center()

    def build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        self.card = QFrame()
        self.card.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)
        root.addWidget(self.card)

        shell = QVBoxLayout(self.card)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        top = QHBoxLayout()
        top.setContentsMargins(24, 18, 24, 8)
        self.window_title = QLabel(APP_NAME)
        self.window_title.setObjectName("windowTitle")
        top.addWidget(self.window_title)
        top.addStretch(1)
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("language")
        self.language_combo.addItem("Português", "pt")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Español", "es")
        self.language_combo.addItem("Français", "fr")
        self.language_combo.currentIndexChanged.connect(self.change_language)
        top.addWidget(self.language_combo)
        self.close_button = QPushButton("X")
        self.close_button.setObjectName("close")
        self.close_button.clicked.connect(self.close)
        top.addWidget(self.close_button)
        shell.addLayout(top)

        body = QHBoxLayout()
        body.setContentsMargins(24, 8, 24, 18)
        body.setSpacing(22)

        media_panel = QFrame()
        media_panel.setObjectName("mediaPanel")
        media_layout = QVBoxLayout(media_panel)
        media_layout.setContentsMargins(18, 18, 18, 18)
        media_layout.setSpacing(14)
        self.badge = QLabel("GG")
        self.badge.setObjectName("badge")
        self.badge.setAlignment(Qt.AlignCenter)
        media_layout.addWidget(self.badge, alignment=Qt.AlignLeft)
        self.gif_label = QLabel()
        self.gif_label.setObjectName("gif")
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setFixedSize(196, 156)
        if GIF_PATH.exists():
            self.gif_movie = QMovie(str(GIF_PATH))
            self.gif_movie.setCacheMode(QMovie.CacheAll)
            self.gif_movie.setSpeed(105)
            self.gif_movie.setScaledSize(self.gif_label.size())
            self.gif_label.setMovie(self.gif_movie)
            self.gif_movie.start()
        else:
            self.gif_label.setText("GG")
        media_layout.addWidget(self.gif_label, alignment=Qt.AlignCenter)
        self.media_caption = QLabel("Latest release")
        self.media_caption.setObjectName("mediaCaption")
        self.media_caption.setAlignment(Qt.AlignCenter)
        self.media_caption.setWordWrap(True)
        media_layout.addWidget(self.media_caption)
        body.addWidget(media_panel)

        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")
        self.welcome_title = QLabel()
        self.welcome_title.setObjectName("pageTitle")
        self.welcome_body = QLabel()
        self.welcome_body.setObjectName("pageBody")
        self.welcome_body.setWordWrap(True)
        self.mode_title = QLabel()
        self.mode_title.setObjectName("pageTitle")
        self.mode_body = QLabel()
        self.mode_body.setObjectName("pageBody")
        self.mode_body.setWordWrap(True)
        self.install_path_label = QLabel()
        self.install_path_label.setObjectName("installPath")
        self.install_path_label.setWordWrap(True)
        self.clean_checkbox = QCheckBox()
        self.clean_checkbox.setObjectName("check")
        self.progress_title = QLabel()
        self.progress_title.setObjectName("pageTitle")
        self.status = QLabel()
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.detail = QLabel("")
        self.detail.setObjectName("detail")
        self.detail.setWordWrap(True)
        self.percent = QLabel("0%")
        self.percent.setObjectName("percent")
        self.done_title = QLabel()
        self.done_title.setObjectName("pageTitle")
        self.done_body = QLabel()
        self.done_body.setObjectName("pageBody")
        self.done_body.setWordWrap(True)

        self.pages.addWidget(self.make_welcome_page())
        self.pages.addWidget(self.make_mode_page())
        self.pages.addWidget(self.make_progress_page())
        self.pages.addWidget(self.make_done_page())
        body.addWidget(self.pages, stretch=1)
        shell.addLayout(body, stretch=1)

        actions = QHBoxLayout()
        actions.setContentsMargins(24, 0, 24, 24)
        self.step_hint = QLabel("")
        self.step_hint.setObjectName("stepHint")
        actions.addWidget(self.step_hint, stretch=1)
        actions.addStretch(1)
        self.back_button = QPushButton()
        self.back_button.setObjectName("secondary")
        self.back_button.clicked.connect(self.back_page)
        actions.addWidget(self.back_button)
        self.start_button = QPushButton()
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.next_page)
        actions.addWidget(self.start_button)
        self.open_button = QPushButton()
        self.open_button.setObjectName("secondary")
        self.open_button.hide()
        self.open_button.clicked.connect(lambda: launch_app(INSTALL_DIR))
        actions.addWidget(self.open_button)
        shell.addLayout(actions)

        self.card.setStyleSheet(
            """
            QFrame#card { background: #f8fbff; border: 1px solid #d7e2ee; border-radius: 16px; }
            QFrame#mediaPanel { background: #edf7ff; border: 1px solid #c9ddec; border-radius: 14px; min-width: 236px; max-width: 236px; }
            QLabel { font-family: "Segoe UI"; color: #132238; }
            QLabel#windowTitle { color: #607187; font-size: 12px; font-weight: 800; }
            QLabel#badge { min-width: 48px; max-width: 48px; min-height: 34px; max-height: 34px; background: #ffffff; color: #0f766e; border: 1px solid #2dd4bf; border-radius: 11px; font-weight: 900; }
            QLabel#gif { background: #ffffff; border: 1px solid #d6e6f2; border-radius: 12px; }
            QLabel#mediaCaption, QLabel#stepHint, QLabel#detail, QLabel#installPath { color: #607187; font-size: 11px; }
            QLabel#pageTitle { color: #132238; font-size: 28px; font-weight: 900; }
            QLabel#pageBody { color: #536579; font-size: 13px; line-height: 150%; }
            QLabel#status { color: #132238; font-size: 15px; font-weight: 800; }
            QLabel#percent { color: #0f766e; font-size: 38px; font-weight: 900; }
            QStackedWidget#pages { background: transparent; }
            QCheckBox#check { color: #132238; font-family: "Segoe UI"; font-size: 13px; spacing: 10px; }
            QCheckBox#check::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid #28b8a8; background: #ffffff; }
            QCheckBox#check::indicator:checked { background: #2dd4bf; }
            QPushButton { font-family: "Segoe UI"; border-radius: 8px; padding: 11px 18px; font-weight: 800; min-width: 92px; }
            QPushButton#primary { background: #14b8a6; color: #ffffff; border: 0; }
            QPushButton#primary:hover { background: #0f9f92; }
            QPushButton#primary:disabled { background: #a7c7c2; color: #ffffff; }
            QPushButton#secondary { background: #ffffff; color: #1f334b; border: 1px solid #c8d6e4; }
            QPushButton#secondary:hover { background: #edf7ff; }
            QPushButton#close { background: transparent; color: #607187; padding: 6px 10px; border-radius: 6px; min-width: 0; }
            QPushButton#close:hover { background: #ffe8ee; color: #c2415a; }
            QComboBox#language { background: #ffffff; color: #1f334b; border: 1px solid #c8d6e4; border-radius: 8px; padding: 8px 12px; min-width: 120px; font-weight: 700; }
            QProgressBar { height: 14px; background: #e6eef7; border: 1px solid #d2dfec; border-radius: 7px; }
            QProgressBar::chunk { background: #14b8a6; border-radius: 6px; }
            """
        )
        self.page_index = 0
        self.sync_page()

    def make_page(self, widgets: list[QWidget]) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(16)
        for widget in widgets:
            layout.addWidget(widget)
        layout.addStretch(1)
        return page

    def make_welcome_page(self) -> QWidget:
        return self.make_page([self.welcome_title, self.welcome_body])

    def make_mode_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self.mode_title)
        layout.addWidget(self.mode_body)
        destination_card = QFrame()
        destination_card.setObjectName("destinationCard")
        destination_layout = QVBoxLayout(destination_card)
        destination_layout.setContentsMargins(14, 12, 14, 12)
        destination_layout.setSpacing(6)
        self.destination_label = QLabel(tr(self.language, "install_path"))
        self.destination_label.setObjectName("detail")
        destination_layout.addWidget(self.destination_label)
        destination_layout.addWidget(self.install_path_label)
        layout.addWidget(destination_card)
        layout.addWidget(self.clean_checkbox)
        layout.addStretch(1)
        destination_card.setStyleSheet("QFrame#destinationCard { background: #ffffff; border: 1px solid #d7e2ee; border-radius: 10px; }")
        return page

    def make_progress_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self.progress_title)
        progress_row = QHBoxLayout()
        progress_text = QVBoxLayout()
        progress_text.setSpacing(8)
        progress_text.addWidget(self.status)
        progress_text.addWidget(self.detail)
        progress_row.addLayout(progress_text, stretch=1)
        progress_row.addWidget(self.percent)
        layout.addLayout(progress_row)
        layout.addWidget(self.progress)
        layout.addStretch(1)
        return page

    def make_done_page(self) -> QWidget:
        return self.make_page([self.done_title, self.done_body])

    def center(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())

    def change_language(self) -> None:
        self.language = str(self.language_combo.currentData() or "pt")
        self.apply_text()

    def apply_text(self) -> None:
        self.window_title.setText(f"{APP_NAME} Setup")
        self.media_caption.setText("GG Coalition\nOnline Setup")
        self.welcome_title.setText(tr(self.language, "welcome_title"))
        self.welcome_body.setText(tr(self.language, "welcome_body"))
        self.mode_title.setText(tr(self.language, "mode_title"))
        self.mode_body.setText(tr(self.language, "mode_body"))
        self.destination_label.setText(tr(self.language, "install_path"))
        self.install_path_label.setText(str(INSTALL_DIR))
        self.clean_checkbox.setText(tr(self.language, "clean_choice"))
        self.progress_title.setText(tr(self.language, "start"))
        self.done_title.setText(tr(self.language, "done"))
        self.done_body.setText(str(INSTALL_DIR))
        self.open_button.setText(tr(self.language, "open"))
        if not self.install_complete:
            self.status.setText(tr(self.language, "ready"))
        self.sync_page()

    def has_existing_install(self) -> bool:
        return INSTALL_DIR.exists() and (
            (INSTALL_DIR / APP_EXE_NAME).exists() or any(INSTALL_DIR.glob("*"))
        )

    def sync_page(self) -> None:
        self.pages.setCurrentIndex(self.page_index)
        self.back_button.setVisible(self.page_index == 1)
        self.open_button.setVisible(self.install_complete)
        self.start_button.setVisible(not self.install_complete)
        self.language_combo.setEnabled(self.page_index == 0)
        if self.page_index == 0:
            self.start_button.setText(tr(self.language, "next"))
            self.step_hint.setText("1 / 4")
        elif self.page_index == 1:
            self.start_button.setText(tr(self.language, "start"))
            self.step_hint.setText("2 / 4")
            existing = self.has_existing_install()
            self.clean_checkbox.setVisible(existing)
            self.clean_checkbox.setChecked(False)
            if existing:
                self.mode_body.setText(tr(self.language, "existing_short"))
            else:
                self.mode_body.setText(tr(self.language, "mode_body"))
        elif self.page_index == 2:
            self.start_button.setText(tr(self.language, "start"))
            self.step_hint.setText("3 / 4")
        else:
            self.start_button.setText(tr(self.language, "finish"))
            self.step_hint.setText("4 / 4")

    def next_page(self) -> None:
        if self.page_index == 0:
            self.page_index = 1
            self.sync_page()
            return
        if self.page_index == 1:
            self.start_install()
            return
        if self.page_index == 3:
            self.close()

    def back_page(self) -> None:
        if self.page_index > 0 and not self.install_complete:
            self.page_index -= 1
            self.sync_page()

    def start_install(self) -> None:
        clean = self.has_existing_install() and self.clean_checkbox.isChecked()
        self.page_index = 2
        self.sync_page()
        self.start_button.setEnabled(False)
        self.back_button.setEnabled(False)
        self.language_combo.setEnabled(False)
        threading.Thread(target=self.install_worker, args=(clean,), daemon=True).start()

    def install_worker(self, clean: bool) -> None:
        try:
            self.emit_progress(4, "checking", "")
            asset = fetch_latest_asset()
            self.emit_progress(10, "found", asset.name, version=asset.version)
            temp_dir = Path(tempfile.mkdtemp(prefix="gg_coalition_setup_"))
            zip_path = temp_dir / asset.name

            def download_progress(downloaded: int, total: int) -> None:
                percent = 12 + int((downloaded / max(1, total or asset.size or downloaded)) * 36)
                mb_done = downloaded / (1024 * 1024)
                mb_total = (total or asset.size or downloaded) / (1024 * 1024)
                self.emit_progress(percent, "downloading", f"{mb_done:.1f}/{mb_total:.1f} MB")

            download_asset(asset, zip_path, download_progress)
            self.emit_progress(52, "extracting", zip_path.name)
            source = extract_zip(zip_path, temp_dir / "extract")
            self.emit_progress(60, "closing", str(INSTALL_DIR))
            close_installed_processes(INSTALL_DIR)
            if clean:
                self.emit_progress(64, "cleaning", str(INSTALL_DIR))
                safe_clean_install_dir(INSTALL_DIR)

            def copy_progress(index: int, total: int, relative: Path) -> None:
                self.emit_progress(66 + int((index / total) * 24), "installing", str(relative))

            copy_tree(source, INSTALL_DIR, copy_progress)
            self.emit_progress(94, "shortcuts", str(INSTALL_DIR))
            create_shortcuts(INSTALL_DIR)
            self.emit_progress(98, "launching", str(INSTALL_DIR / APP_EXE_NAME))
            launch_app(INSTALL_DIR)
            self.emit_progress(100, "done", str(INSTALL_DIR))
            self.signals.finished.emit(True, tr(self.language, "done"), "")
        except Exception as exc:
            log_path = write_error(exc)
            message = self.error_message(exc)
            detail = tr(self.language, "error_log", path=log_path)
            self.signals.finished.emit(False, message, detail)

    def error_message(self, exc: BaseException) -> str:
        if isinstance(exc, RuntimeError) and exc.args:
            key = exc.args[0]
            if key == "no_asset":
                return tr(self.language, "no_asset")
            if key == "zip_invalid":
                return tr(self.language, "zip_invalid")
            if isinstance(key, tuple) and key[0] == "download_failed":
                return tr(self.language, "download_failed", status=key[1])
            if isinstance(key, tuple) and key[0] == "zip_incomplete":
                return tr(self.language, "zip_incomplete", missing=key[1])
        return str(exc)

    def emit_progress(self, value: int, key: str, detail: str, **kwargs) -> None:
        self.signals.progress.emit(value, tr(self.language, key, **kwargs), detail, "#5eead4")

    @Slot(int, str, str, str)
    def set_progress(self, value: int, status: str, detail: str, _accent: str) -> None:
        safe_value = max(0, min(100, int(value)))
        self.progress.setValue(safe_value)
        self.percent.setText(f"{safe_value}%")
        self.status.setText(status)
        self.detail.setText(detail)

    @Slot(bool, str, str)
    def finish(self, success: bool, message: str, detail: str) -> None:
        self.install_complete = success
        self.done_title.setText(message)
        self.done_body.setText(detail or str(INSTALL_DIR))
        self.page_index = 3
        self.pages.setCurrentIndex(3)
        self.back_button.hide()
        self.start_button.setEnabled(True)
        self.start_button.show()
        self.start_button.setText(tr(self.language, "finish"))
        self.language_combo.setEnabled(True)
        self.step_hint.setText("4 / 4")
        if success:
            self.open_button.show()
            self.close_button.setText(tr(self.language, "close"))
        else:
            self.progress.setValue(100)
            self.percent.setText("100%")
            self.open_button.hide()


def main() -> int:
    configure_qt_runtime()
    app = QApplication(sys.argv)
    window = InstallerWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
