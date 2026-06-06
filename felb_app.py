from __future__ import annotations

import ctypes
import os
from pathlib import Path
import sys

import PySide6
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMessageBox

from qt_controllers import APP_TITLE, ControllerRegistry


BASE_DIR = Path(__file__).resolve().parent
QML_ENTRY = BASE_DIR / "qml" / "Main.qml"
ICON_ICO_PATH = BASE_DIR / "img" / "app_icon.ico"
SINGLE_INSTANCE_MUTEX_NAME = "Local\\GGCoalition.SingleInstance"
ERROR_ALREADY_EXISTS = 183
BACKGROUND_ARGS = {"--background", "-background", "/background"}
ALLOW_MULTIPLE_ENV = "FELB_ALLOW_MULTIPLE"
TRUE_ENV_VALUES = {"1", "true", "yes", "on"}


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def allow_multiple_instances() -> bool:
    return os.environ.get(ALLOW_MULTIPLE_ENV, "").strip().lower() in TRUE_ENV_VALUES


def acquire_single_instance_mutex(name: str = SINGLE_INSTANCE_MUTEX_NAME):
    try:
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
        if not handle:
            return None
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            ctypes.windll.kernel32.CloseHandle(handle)
            return None
        return handle
    except Exception:
        return object()


def release_single_instance_mutex(handle) -> None:
    if not handle:
        return
    try:
        if isinstance(handle, int):
            ctypes.windll.kernel32.CloseHandle(handle)
        elif hasattr(handle, "value"):
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        pass


def configure_qt() -> None:
    os.chdir(BASE_DIR)
    pyside_dir = Path(PySide6.__file__).resolve().parent
    try:
        os.add_dll_directory(str(pyside_dir))
    except (AttributeError, OSError):
        pass
    os.environ["PATH"] = str(pyside_dir) + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("QT_PLUGIN_PATH", str(pyside_dir / "plugins"))
    os.environ.setdefault("QML_IMPORT_PATH", str(pyside_dir / "qml"))
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")
    QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)


def main() -> int:
    load_env_file(BASE_DIR / ".env")
    configure_qt()
    background = any(arg.lower() in BACKGROUND_ARGS for arg in sys.argv[1:])
    allow_multiple = allow_multiple_instances()
    mutex = None if allow_multiple else acquire_single_instance_mutex()
    if not allow_multiple and mutex is None:
        if background:
            return 0
        app = QApplication(sys.argv)
        QMessageBox.information(None, APP_TITLE, "GG Coalition is already running.")
        return 0

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("GG Coalition")
    if ICON_ICO_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_ICO_PATH)))

    registry = ControllerRegistry(app)
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(BASE_DIR / "qml"))
    registry.expose(engine)
    engine.load(QUrl.fromLocalFile(str(QML_ENTRY)))

    if not engine.rootObjects():
        registry.shutdown()
        release_single_instance_mutex(mutex)
        return 1
    if background:
        engine.rootObjects()[0].setProperty("visible", False)

    app.aboutToQuit.connect(registry.shutdown)
    try:
        return app.exec()
    finally:
        registry.shutdown()
        release_single_instance_mutex(mutex)


if __name__ == "__main__":
    raise SystemExit(main())
