import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Item {
    id: root
    width: 240
    height: 80
    
    // Prevent clicks from passing through to map
    MouseArea { anchors.fill: parent }
    
    signal clearAllRequested()

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: 12
        color: Qt.rgba(settingsController.surfaceColor.r, settingsController.surfaceColor.g, settingsController.surfaceColor.b, 0.95)
        border.color: settingsController.borderColor || "#333340"
        border.width: 1
    }

    MultiEffect {
        source: bg
        anchors.fill: bg
        shadowEnabled: true
        shadowOpacity: 0.3
        shadowBlur: 0.8
        shadowVerticalOffset: 2
        shadowColor: "black"
    }
    
    Rectangle {
        id: clearBtn
        anchors.centerIn: parent
        width: parent.width - 24
        height: 44
        radius: 8
        color: mouseArea.containsMouse ? "#dc2626" : "#ef4444"
        
        Behavior on color { ColorAnimation { duration: 150 } }
        
        Text {
            anchors.centerIn: parent
            text: "🗑️ Limpar Todos os Desenhos"
            color: "white"
            font.bold: true
            font.pixelSize: 13
        }
        
        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.clearAllRequested()
        }
    }
}
