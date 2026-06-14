import QtQuick
import QtQuick.Controls

Button {
    id: root
    property color fill: settingsController.accentColor
    property color hoverFill: settingsController.accentHoverColor
    property color textFill: "#041014"

    implicitHeight: 38
    leftPadding: 16
    rightPadding: 16
    font.family: "Segoe UI"
    font.pixelSize: 13
    font.bold: true

    contentItem: Text {
        text: root.text
        color: root.enabled ? root.textFill : "#7f93ad"
        opacity: root.enabled ? 1 : 0.86
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 8
        color: !root.enabled ? "#111c31" : (root.hovered ? root.hoverFill : root.fill)
        border.color: !root.enabled ? "#1e3554" : "transparent"
        border.width: !root.enabled ? 1 : 0
        Behavior on color { ColorAnimation { duration: 140 } }
        Behavior on border.color { ColorAnimation { duration: 140 } }
    }
}

