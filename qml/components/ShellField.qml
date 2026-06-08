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
        placeholderText: root.placeholder
        color: "#edf6ff"
        selectedTextColor: "#041014"
        selectionColor: "#5eead4"
        font.family: "Segoe UI"
        font.pixelSize: 13
        Layout.fillWidth: true
        onAccepted: root.accepted(text)
        background: Rectangle {
            radius: 7
            color: "#0e1a2d"
            border.color: input.activeFocus ? "#5eead4" : "#2d496f"
            border.width: 1
            Behavior on border.color { ColorAnimation { duration: 120 } }
        }
    }
}
