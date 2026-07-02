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
    property int contentMargins: 20
    property int contentSpacing: 8
    property int titlePixelSize: 12
    property int valuePixelSize: 24
    property int detailPixelSize: 12
    property int valueMaximumLineCount: 1
    property int detailMaximumLineCount: 1

    radius: 20
    color: settingsController.surfaceColor
    border.color: hoverArea.containsMouse ? root.accent : Qt.rgba(1, 1, 1, 0.05)
    border.width: 1
    implicitHeight: 120
    clip: true

    Behavior on border.color {
        ColorAnimation { duration: 250; easing.type: Easing.OutCubic }
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.accent
        opacity: hoverArea.containsMouse ? 0.12 : 0.03
        
        Behavior on opacity {
            NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.contentMargins
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
            opacity: 0.7
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
        cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.NoButton
    }
}
