import QtQuick
import QtQuick.Controls

Button {
    id: root
    property color fill: "#5eead4"
    property color hoverFill: "#8ab4ff"
    property color textFill: "#041014"

    implicitHeight: 38
    leftPadding: 16
    rightPadding: 16
    font.family: "Segoe UI"
    font.pixelSize: 13
    font.bold: true

    contentItem: Text {
        text: root.text
        color: root.textFill
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 8
        color: root.hovered ? root.hoverFill : root.fill
        Behavior on color { ColorAnimation { duration: 140 } }
    }
}
