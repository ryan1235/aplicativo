from __future__ import annotations

import ctypes
import math
import os
from pathlib import Path
import sys

import PySide6
from PySide6.QtCore import QUrl, Qt, qInstallMessageHandler, QtMsgType
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


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def primary_screen_size() -> tuple[int, int] | None:
    if not sys.platform.startswith("win"):
        return None
    try:
        user32 = ctypes.windll.user32
        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))
        if width > 0 and height > 0:
            return width, height
    except Exception:
        return None
    return None


def responsive_ui_scale(screen_size: tuple[int, int] | None) -> float:
    if not screen_size:
        return 1.0

    width, height = screen_size
    base_diagonal = math.hypot(1920, 1080)
    screen_diagonal = math.hypot(width, height)
    resolution_scale = screen_diagonal / base_diagonal
    moderated_scale = 1.0 + ((resolution_scale - 1.0) * 0.36)
    return round(clamp(moderated_scale, 0.90, 1.25), 2)


def configure_responsive_scaling() -> None:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")
    if "QT_SCALE_FACTOR" in os.environ or "QT_SCREEN_SCALE_FACTORS" in os.environ:
        return

    scale = responsive_ui_scale(primary_screen_size())
    os.environ["QT_SCALE_FACTOR"] = f"{scale:.2f}".rstrip("0").rstrip(".")


def configure_qt() -> None:
    os.chdir(BASE_DIR)
    configure_responsive_scaling()
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


def trim_runtime_memory(engine: QQmlApplicationEngine | None = None) -> None:
    try:
        if engine is not None:
            engine.collectGarbage()
            engine.trimComponentCache()
    except RuntimeError:
        pass
    except Exception:
        pass
    try:
        import gc

        gc.collect()
    except Exception:
        pass

def custom_message_handler(mode, context, message):
    if mode == QtMsgType.QtWarningMsg and "server replied with status code 404" in message:
        return
    print(message)

def cleanup_old_files() -> None:
    for file in BASE_DIR.rglob("*.old"):
        try:
            file.unlink()
        except OSError:
            pass


def main() -> int:
    qInstallMessageHandler(custom_message_handler)
    cleanup_old_files()
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

    def on_state_changed(state: Qt.ApplicationState) -> None:
        registry.setBackgroundMode(state != Qt.ApplicationState.ApplicationActive)
        if state == Qt.ApplicationState.ApplicationHidden:
            trim_runtime_memory(engine)
    app.applicationStateChanged.connect(on_state_changed)

    app.aboutToQuit.connect(registry.shutdown)
    try:
        return app.exec()
    finally:
        registry.shutdown()
        trim_runtime_memory(engine)
        release_single_instance_mutex(mutex)


if __name__ == "__main__":
    raise SystemExit(main())
