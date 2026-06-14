import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string title: ""
    property string value: ""
    property string detail: ""
    property color accent: settingsController.accentColor
    property int contentMargins: 14
    property int contentSpacing: 5
    property int titlePixelSize: 11
    property int valuePixelSize: 22
    property int detailPixelSize: 12
    property int valueMaximumLineCount: 1
    property int detailMaximumLineCount: 1

    radius: 8
    color: "#111c31"
    border.color: "#24486d"
    border.width: 1
    implicitHeight: 104

    Behavior on color {
        ColorAnimation { duration: 150; easing.type: Easing.OutCubic }
    }

    Behavior on border.color {
        ColorAnimation { duration: 150; easing.type: Easing.OutCubic }
    }

    Behavior on opacity {
        NumberAnimation { duration: 150; easing.type: Easing.OutCubic }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.contentMargins
        spacing: root.contentSpacing

        Text {
            text: root.title
            color: "#99abc4"
            font.family: "Segoe UI"
            font.pixelSize: root.titlePixelSize
            font.bold: true
            elide: Text.ElideRight
            Layout.fillWidth: true
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
        }

        Text {
            text: root.detail
            color: "#edf6ff"
            opacity: 0.82
            font.family: "Segoe UI"
            font.pixelSize: root.detailPixelSize
            elide: Text.ElideRight
            maximumLineCount: root.detailMaximumLineCount
            wrapMode: Text.NoWrap
            Layout.fillWidth: true
        }
    }
}


