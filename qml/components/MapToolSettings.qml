import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import Qt.labs.platform 1.1 as Platform
import "MapToolsData.js" as ToolsData

Item {
    id: root
    width: 280
    height: contentCol.implicitHeight + 24
    
    property string activeToolId: "pan"
    property var activeTool: null
    
    onActiveToolIdChanged: {
        root.activeTool = ToolsData.getToolById(root.activeToolId);
        console.log("[DEBUG] MapToolSettings activeToolId changed to:", root.activeToolId, "activeTool:", root.activeTool ? root.activeTool.id : "null", "implicitHeight:", contentCol.implicitHeight);
    }
    Component.onCompleted: {
        root.activeTool = ToolsData.getToolById(root.activeToolId);
        console.log("[DEBUG] MapToolSettings completed for:", root.activeToolId);
    }
    
    property string activeColor: "#ef4444"
    property int activeThickness: 3
    property real activeOpacity: 1.0

    // Prevent clicks from passing through to map
    MouseArea { anchors.fill: parent }

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: 18
        color: Qt.rgba(settingsController.surfaceColor.r, settingsController.surfaceColor.g, settingsController.surfaceColor.b, 0.85)
        border.color: Qt.rgba(settingsController.borderColor.r, settingsController.borderColor.g, settingsController.borderColor.b, 0.5)
        border.width: 1
    }

    MultiEffect {
        source: bg
        anchors.fill: bg
        shadowEnabled: true
        shadowOpacity: 0.5
        shadowBlur: 1.5
        shadowVerticalOffset: 4
        shadowColor: "black"
        blurEnabled: true
        blur: 0.8
    }

    Column {
        id: contentCol
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 16
        spacing: 16

        Text {
            text: {
                if (!root.activeTool) return "Configurações"
                var lang = typeof settingsController !== "undefined" ? (settingsController.language || "pt") : "pt";
                var toolName = root.activeTool.names ? (root.activeTool.names[lang] || root.activeTool.names["en"]) : "Configurações";
                return toolName + " - Configurações"
            }
            color: settingsController.textColor || "white"
            font.bold: true
            font.pixelSize: 14
        }

        // Color Picker
        Column {
            width: parent.width
            spacing: 10
            visible: root.activeTool ? !!root.activeTool.supportsColor : false

            Text { text: "Cor"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 11; font.bold: true }

            Flow {
                width: parent.width
                spacing: 8
                
                Repeater {
                    model: [
                        "#ef4444", "#f97316", "#eab308", "#22c55e", 
                        "#06b6d4", "#3b82f6", "#a855f7", "#ec4899", 
                        "#78350f", "#ffffff", "#000000"
                    ]
                    delegate: Rectangle {
                        width: 28
                        height: 28
                        radius: 14
                        color: modelData
                        border.color: root.activeColor === modelData ? (settingsController.accentColor || "#3b82f6") : Qt.rgba(1,1,1,0.2)
                        border.width: root.activeColor === modelData ? 2 : 1
                        
                        scale: mouseArea.containsMouse ? 1.10 : (root.activeColor === modelData ? 1.05 : 1.0)
                        Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutQuad } }
                        
                        MouseArea {
                            id: mouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: root.activeColor = modelData
                            cursorShape: Qt.PointingHandCursor
                        }
                        
                        MultiEffect {
                            source: parent
                            anchors.fill: parent
                            shadowEnabled: root.activeColor === modelData
                            shadowColor: settingsController.accentColor || "#3b82f6"
                            shadowOpacity: 0.6
                            shadowBlur: 0.8
                            visible: root.activeColor === modelData
                        }
                    }
                }
                
                Rectangle {
                    width: 28
                    height: 28
                    radius: 14
                    color: "transparent"
                    border.color: settingsController.borderColor || "#888"
                    border.width: 1
                    
                    scale: customColorMouseArea.containsMouse ? 1.10 : 1.0
                    Behavior on scale { NumberAnimation { duration: 150 } }
                    
                    Text { anchors.centerIn: parent; text: "+"; color: settingsController.textColor || "white"; font.bold: true; font.pixelSize: 16 }
                    
                    MouseArea {
                        id: customColorMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: colorDialog.open()
                        cursorShape: Qt.PointingHandCursor
                    }
                }
            }
        }

        // Thickness Slider
        Column {
            width: parent.width
            spacing: 10
            visible: root.activeTool ? !!root.activeTool.supportsThickness : false

            Text { text: "Espessura"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 11; font.bold: true }

            RowLayout {
                width: parent.width
                spacing: 12
                
                Rectangle {
                    width: 40
                    height: 24
                    color: "transparent"
                    Layout.alignment: Qt.AlignVCenter
                    
                    Rectangle {
                        anchors.centerIn: parent
                        width: 40
                        height: root.activeThickness
                        radius: root.activeThickness / 2
                        color: root.activeColor
                        border.color: root.activeColor === "#000000" ? "#ffffff" : "transparent"
                        border.width: root.activeColor === "#000000" ? 1 : 0
                        
                        Behavior on height { NumberAnimation { duration: 100 } }
                        Behavior on radius { NumberAnimation { duration: 100 } }
                    }
                }
                
                Slider {
                    Layout.fillWidth: true
                    from: 1
                    to: 20
                    value: root.activeThickness
                    stepSize: 1
                    onValueChanged: root.activeThickness = value
                }
                
                Text {
                    text: root.activeThickness + " px"
                    color: settingsController.textColor || "white"
                    font.pixelSize: 12
                    font.bold: true
                    Layout.alignment: Qt.AlignVCenter
                    Layout.minimumWidth: 40
                    horizontalAlignment: Text.AlignRight
                }
            }
        }
        
        // Opacity Slider
        Column {
            width: parent.width
            spacing: 10
            visible: root.activeTool ? !!root.activeTool.supportsOpacity : false

            Text { text: "Opacidade"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 11; font.bold: true }

            RowLayout {
                width: parent.width
                spacing: 12
                
                Rectangle {
                    width: 24
                    height: 24
                    radius: 12
                    color: root.activeColor
                    opacity: root.activeOpacity
                    border.color: root.activeColor === "#000000" ? "#ffffff" : "transparent"
                    border.width: root.activeColor === "#000000" ? 1 : 0
                    Layout.alignment: Qt.AlignVCenter
                }
                
                Slider {
                    Layout.fillWidth: true
                    from: 0.1
                    to: 1.0
                    value: root.activeOpacity
                    stepSize: 0.05
                    onValueChanged: root.activeOpacity = value
                }
                
                Text {
                    text: Math.round(root.activeOpacity * 100) + "%"
                    color: settingsController.textColor || "white"
                    font.pixelSize: 12
                    font.bold: true
                    Layout.alignment: Qt.AlignVCenter
                    Layout.minimumWidth: 40
                    horizontalAlignment: Text.AlignRight
                }
            }
        }
    }

    Platform.ColorDialog {
        id: colorDialog
        title: "Escolha uma cor customizada"
        currentColor: root.activeColor
        onAccepted: root.activeColor = color
    }
}
