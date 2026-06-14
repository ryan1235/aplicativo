import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property string currentKey: ""
    property bool isRecording: false
    signal keySelected(string keyName)

    width: 100
    height: 36
    radius: 8
    opacity: enabled ? 1.0 : 0.45
    color: enabled && (pickerMouse.containsMouse || isRecording) ? "#101f36" : "#0c1728"
    border.color: isRecording ? settingsController.accentColor : (enabled && pickerMouse.containsMouse ? "#2d496f" : "#1e3554")
    border.width: isRecording ? 1.5 : 1
    Behavior on color { ColorAnimation { duration: 120 } }
    Behavior on border.color { ColorAnimation { duration: 120 } }

    Text {
        anchors.centerIn: parent
        text: isRecording ? "Pressione..." : currentKey
        color: enabled ? (isRecording ? settingsController.accentColor : "#edf6ff") : "#7f93ad"
        font.family: "Segoe UI"
        font.pixelSize: 13
        font.bold: true
    }

    MouseArea {
        id: pickerMouse
        anchors.fill: parent
        enabled: root.enabled
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            root.isRecording = true
            root.forceActiveFocus()
        }
    }

    Keys.onPressed: (event) => {
        if (!isRecording) return;
        
        var keyName = "";
        
        // F1-F12
        if (event.key >= Qt.Key_F1 && event.key <= Qt.Key_F12) {
            keyName = "F" + (event.key - Qt.Key_F1 + 1);
        }
        // A-Z
        else if (event.key >= Qt.Key_A && event.key <= Qt.Key_Z) {
            keyName = String.fromCharCode(event.key);
        }
        // 0-9
        else if (event.key >= Qt.Key_0 && event.key <= Qt.Key_9) {
            keyName = String.fromCharCode(event.key);
        }
        else {
            switch(event.key) {
                case Qt.Key_Escape: keyName = "Esc"; break;
                case Qt.Key_Tab: keyName = "Tab"; break;
                case Qt.Key_Return: case Qt.Key_Enter: keyName = "Enter"; break;
                case Qt.Key_Space: keyName = "Space"; break;
                case Qt.Key_Up: keyName = "Up"; break;
                case Qt.Key_Down: keyName = "Down"; break;
                case Qt.Key_Left: keyName = "Left"; break;
                case Qt.Key_Right: keyName = "Right"; break;
                case Qt.Key_Insert: keyName = "Insert"; break;
                case Qt.Key_Delete: keyName = "Delete"; break;
                case Qt.Key_Home: keyName = "Home"; break;
                case Qt.Key_End: keyName = "End"; break;
                case Qt.Key_PageUp: keyName = "PageUp"; break;
                case Qt.Key_PageDown: keyName = "PageDown"; break;
            }
        }
        
        if (keyName !== "") {
            root.currentKey = keyName;
            root.isRecording = false;
            root.keySelected(keyName);
            event.accepted = true;
        } else {
            // Cancelar captura com teclas invÃ¡lidas (como Ctrl/Alt) para nÃ£o travar
            root.isRecording = false;
        }
    }
    
    onFocusChanged: {
        if (!activeFocus) {
            isRecording = false;
        }
    }
}


