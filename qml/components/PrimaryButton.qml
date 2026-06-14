import QtQuick
import QtQuick.Controls

Button {
    id: root
    property color fill: settingsController.accentColor
    property color hoverFill: settingsController.accentHoverColor
    property color textFill: "#041014"
    property string visualStyle: settingsController.buttonStyle

    implicitHeight: 38
    leftPadding: 16
    rightPadding: 16
    font.family: "Segoe UI"
    font.pixelSize: 13
    font.bold: true

    contentItem: Text {
        text: root.text
        color: root.enabled ? (root.visualStyle === "solid" ? root.textFill : "#edf6ff") : "#7f93ad"
        opacity: root.enabled ? 1 : 0.86
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: settingsController.buttonRadius
        color: {
            if (!root.enabled)
                return "#111c31"
            if (root.visualStyle === "outline")
                return root.hovered ? settingsController.accentPanelColor : "transparent"
            if (root.visualStyle === "soft")
                return root.hovered ? root.hoverFill : settingsController.accentPanelColor
            if (root.visualStyle === "glass")
                return root.hovered ? root.hoverFill : settingsController.surfaceColor
            return root.hovered ? root.hoverFill : root.fill
        }
        border.color: {
            if (!root.enabled)
                return "#1e3554"
            if (root.visualStyle === "outline" || root.visualStyle === "glass")
                return root.fill
            return "transparent"
        }
        border.width: root.visualStyle === "outline" || root.visualStyle === "glass" || !root.enabled ? 1 : 0
        opacity: root.visualStyle === "glass" && root.enabled ? 0.92 : 1
        Behavior on color { ColorAnimation { duration: 140 } }
        Behavior on border.color { ColorAnimation { duration: 140 } }
    }
}

