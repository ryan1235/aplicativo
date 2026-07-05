import sys
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QUrl
import os

app = QApplication(sys.argv)
engine = QQmlApplicationEngine()
engine.load(QUrl.fromLocalFile('qml/pages/MapPage.qml'))

def capture():
    try:
        win = engine.rootObjects()[0]
        # In PySide6, a QQuickItem grabToImage returns a QQuickItemGrabResult asynchronously, but wait, win is QQuickItem.
        # Actually grabToImage accepts a callback.
        def saved(res):
            res.saveToFile('test_render.png')
            app.quit()
        
        result = win.grabToImage()
        # QQuickItemGrabResult has a saveToFile method?
        # Let's just use grabToImage and then save.
        if result:
            result.saveToFile('test_render.png')
            print("Saved to test_render.png")
        else:
            print("grabToImage failed")
        app.quit()
    except Exception as e:
        print("Error capturing:", e)
        app.quit()

QTimer.singleShot(2000, capture)
app.exec()
