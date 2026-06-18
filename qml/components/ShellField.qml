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
        color: settingsController.mutedTextColor
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
        placeholderTextColor: settingsController.disabledTextColor
        color: settingsController.textColor
        selectedTextColor: settingsController.backgroundColor
        selectionColor: settingsController.accentColor
        font.family: "Segoe UI"
        font.pixelSize: 13
        leftPadding: 12
        rightPadding: 12
        verticalAlignment: TextInput.AlignVCenter
        onAccepted: root.accepted(text)
        background: Rectangle {
            radius: settingsController.cardRadius
            color: input.hovered || input.activeFocus ? settingsController.accentPanelColor : settingsController.backgroundColor
            border.color: input.activeFocus ? settingsController.accentColor : settingsController.borderColor
            border.width: input.activeFocus ? 1.5 : 1
            Behavior on color { ColorAnimation { duration: 120 } }
            Behavior on border.color { ColorAnimation { duration: 120 } }
        }
    }
}

