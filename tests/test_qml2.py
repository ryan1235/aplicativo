import sys
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QUrl

app = QApplication(sys.argv)
engine = QQmlApplicationEngine()

def handle_warnings(warnings):
    for w in warnings:
        print("QML Warning:", w.toString())

engine.warnings.connect(handle_warnings)

engine.load(QUrl.fromLocalFile('qml/pages/MapPage.qml'))

if not engine.rootObjects():
    print("Failed to load MapPage.qml")
    sys.exit(1)

def on_timeout():
    print("Timer finished")
    app.quit()

QTimer.singleShot(2000, on_timeout)
app.exec()
