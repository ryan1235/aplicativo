import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string title: ""
    property string value: ""
    property string detail: ""
    property string emoji: ""
    property int textRightMargin: 0
    property color accent: settingsController.accentColor
    property int contentMargins: 18
    property int contentSpacing: 6
    property int titlePixelSize: 11
    property int valuePixelSize: 22
    property int detailPixelSize: 12
    property int valueMaximumLineCount: 1
    property int detailMaximumLineCount: 1

    radius: settingsController.cardRadius
    color: hoverArea.containsMouse ? settingsController.accentPanelColor : settingsController.surfaceColor
    border.color: hoverArea.containsMouse ? root.accent : settingsController.borderColor
    border.width: 1
    implicitHeight: 110
    clip: true

    Behavior on color {
        ColorAnimation { duration: 200; easing.type: Easing.OutCubic }
    }

    Behavior on border.color {
        ColorAnimation { duration: 200; easing.type: Easing.OutCubic }
    }

    Rectangle {
        id: accentBar
        width: 4
        height: parent.height
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        color: root.accent
        opacity: hoverArea.containsMouse ? 1.0 : 0.6
        
        Behavior on opacity {
            NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
        }
    }

    Rectangle {
        anchors.fill: parent
        anchors.leftMargin: accentBar.width
        radius: root.radius
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: root.accent }
            GradientStop { position: 0.6; color: "transparent" }
        }
        opacity: hoverArea.containsMouse ? 0.12 : 0.03
        
        Behavior on opacity {
            NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.contentMargins
        anchors.leftMargin: root.contentMargins + accentBar.width
        spacing: root.contentSpacing

        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            Text {
                text: root.emoji
                font.pixelSize: root.titlePixelSize + 2
                visible: root.emoji !== ""
            }
            Text {
                text: root.title.toUpperCase()
                color: settingsController.mutedTextColor
                font.family: "Segoe UI"
                font.pixelSize: root.titlePixelSize
                font.bold: true
                font.letterSpacing: 1.0
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }

        Text {
            text: root.value
            color: root.accent
            font.family: "Segoe UI"
            font.pixelSize: root.valuePixelSize
            font.bold: true
            elide: Text.ElideRight
            maximumLineCount: root.valueMaximumLineCount
            wrapMode: Text.NoWrap
            Layout.fillWidth: true
            Layout.rightMargin: root.textRightMargin
        }

        Text {
            text: root.detail
            color: settingsController.textColor
            opacity: 0.8
            font.family: "Segoe UI"
            font.pixelSize: root.detailPixelSize
            elide: Text.ElideRight
            maximumLineCount: root.detailMaximumLineCount
            wrapMode: Text.NoWrap
            Layout.fillWidth: true
            Layout.rightMargin: root.textRightMargin
        }
    }

    MouseArea {
        id: hoverArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }
}
