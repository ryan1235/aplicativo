import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Item {
    id: root
    width: 280
    height: baseSettings.height + 60
    
    // Prevent clicks from passing through to map
    MouseArea { anchors.fill: parent }

    property string activeColor: "#ef4444"
    property int activeThickness: 3
    property real activeOpacity: 1.0
    property string activeToolId: "polygon"
    
    signal colorChanged(string color)
    signal thicknessChanged(int thickness)
    signal opacityChanged(real opacity)
    signal finishDrawing()
    
    onActiveColorChanged: root.colorChanged(activeColor)
    onActiveThicknessChanged: root.thicknessChanged(activeThickness)
    onActiveOpacityChanged: root.opacityChanged(activeOpacity)

    MapToolSettings {
        id: baseSettings
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        
        activeToolId: root.activeToolId
        activeColor: root.activeColor
        activeThickness: root.activeThickness
        activeOpacity: root.activeOpacity
        
        onActiveColorChanged: root.activeColor = activeColor
        onActiveThicknessChanged: root.activeThickness = activeThickness
        onActiveOpacityChanged: root.activeOpacity = activeOpacity
    }
    
    Rectangle {
        id: finishBtn
        anchors.top: baseSettings.bottom
        anchors.topMargin: 4
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width - 24
        height: 40
        radius: 8
        color: mouseArea.containsMouse ? (settingsController.accentColor || "#3b82f6") : Qt.rgba((settingsController.accentColor || "#3b82f6").r, (settingsController.accentColor || "#3b82f6").g, (settingsController.accentColor || "#3b82f6").b, 0.8)
        border.color: settingsController.accentColor || "#3b82f6"
        border.width: 1
        
        Behavior on color { ColorAnimation { duration: 150 } }
        
        Text {
            anchors.centerIn: parent
            text: "✅ Finalizar Área"
            color: "white"
            font.bold: true
            font.pixelSize: 13
        }
        
        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.finishDrawing()
        }
    }
}
