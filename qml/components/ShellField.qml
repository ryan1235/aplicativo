import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    property alias text: input.text
    property string label: ""
    property string placeholder: ""
    signal accepted(string value)

    spacing: 6

    Text {
        text: root.label
        color: "#99abc4"
        font.family: "Segoe UI"
        font.pixelSize: 11
        font.bold: true
        Layout.fillWidth: true
        elide: Text.ElideRight
    }

    TextField {
        id: input
        Layout.fillWidth: true
        Layout.preferredHeight: 40
        placeholderText: root.placeholder
        placeholderTextColor: "#60728c"
        color: "#edf6ff"
        selectedTextColor: "#041014"
        selectionColor: settingsController.accentColor
        font.family: "Segoe UI"
        font.pixelSize: 13
        leftPadding: 12
        rightPadding: 12
        verticalAlignment: TextInput.AlignVCenter
        onAccepted: root.accepted(text)
        background: Rectangle {
            radius: 8
            color: input.hovered || input.activeFocus ? "#101f36" : "#0c1728"
            border.color: input.activeFocus ? settingsController.accentColor : (input.hovered ? "#2d496f" : "#1e3554")
            border.width: input.activeFocus ? 1.5 : 1
            Behavior on color { ColorAnimation { duration: 120 } }
            Behavior on border.color { ColorAnimation { duration: 120 } }
        }
    }
}

