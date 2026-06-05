import QtQuick
import QtQuick.Controls

Switch {
    id: control
    implicitWidth: 44
    implicitHeight: 24

    indicator: Rectangle {
        implicitWidth: control.implicitWidth
        implicitHeight: control.implicitHeight
        x: control.leftPadding
        y: parent.height / 2 - height / 2
        radius: height / 2
        color: control.checked ? "#173c35" : "#0e1a2d"
        border.color: control.checked ? "#5eead4" : "#2d496f"
        opacity: control.enabled ? 1.0 : 0.55
        Behavior on color { ColorAnimation { duration: 130 } }
        Behavior on border.color { ColorAnimation { duration: 130 } }

        Rectangle {
            width: 16
            height: 16
            radius: 8
            x: control.checked ? parent.width - width - 4 : 4
            y: 4
            color: control.checked ? "#5eead4" : "#7f93ad"
            Behavior on x { NumberAnimation { duration: 130; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: 130 } }
        }
    }

    contentItem: Item {}
}
