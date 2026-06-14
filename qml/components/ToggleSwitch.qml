import QtQuick
import QtQuick.Controls

Switch {
    id: control
    implicitWidth: 48
    implicitHeight: 26

    indicator: Rectangle {
        implicitWidth: control.implicitWidth
        implicitHeight: control.implicitHeight
        x: control.leftPadding
        y: parent.height / 2 - height / 2
        radius: height / 2
        color: control.checked ? settingsController.accentPanelColor : (control.hovered ? settingsController.surfaceColor : settingsController.backgroundColor)
        border.color: control.checked ? settingsController.accentColor : settingsController.borderColor
        border.width: control.activeFocus ? 1.5 : 1
        opacity: control.enabled ? 1.0 : 0.55
        Behavior on color { ColorAnimation { duration: 130 } }
        Behavior on border.color { ColorAnimation { duration: 130 } }

        Rectangle {
            width: 18
            height: 18
            radius: 9
            x: control.checked ? parent.width - width - 4 : 4
            y: 4
            color: control.checked ? settingsController.accentColor : settingsController.mutedTextColor
            border.color: settingsController.textColor
            border.width: 1
            Behavior on x { NumberAnimation { duration: 130; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: 130 } }
        }
    }

    contentItem: Item {}
}

