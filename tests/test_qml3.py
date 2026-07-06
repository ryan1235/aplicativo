import sys
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QUrl, qInstallMessageHandler

def qt_message_handler(mode, context, message):
    print(message)

qInstallMessageHandler(qt_message_handler)

app = QApplication(sys.argv)
engine = QQmlApplicationEngine()
engine.load(QUrl.fromLocalFile('qml/pages/MapPage.qml'))

def on_timeout():
    app.quit()

QTimer.singleShot(2000, on_timeout)
app.exec()
