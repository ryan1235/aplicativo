import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import "../components"

Item {
    id: root

    // Background Image
    Rectangle {
        anchors.fill: parent
        color: "#0a0f18" // Slightly lighter than pure black
        z: -2
    }
    
    Image {
        id: bgImage
        anchors.fill: parent
        source: typeof appController !== "undefined" ? appController.assetUrl("img/mapwarpepe.png") : ""
        fillMode: Image.PreserveAspectCrop
        visible: false // Hidden because MultiEffect handles it
    }
    
    MultiEffect {
        anchors.fill: bgImage
        source: bgImage
        blurEnabled: true
        blurMax: 32
        blur: 0.4 // Subtle blur
        opacity: 0.45 // Increased opacity to make it lighter/brighter
        z: -1
    }

    MapView {
        id: mapView
        anchors.fill: parent
        // No margins for true fullscreen
    }

    // Loading Screen Overlay
    Rectangle {
        id: loadingScreen
        anchors.fill: parent
        color: "#1c2025"
        z: 99
        
        property bool isReady: typeof mapController !== "undefined" && mapController && mapController.mapTextItemsModel && mapController.mapTextItemsModel.length > 0
        opacity: isReady ? 0.0 : 1.0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 800; easing.type: Easing.InOutQuad } }

        Column {
            anchors.centerIn: parent
            spacing: 24
            
            BusyIndicator {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 64
                height: 64
                running: parent.visible
                
                contentItem: Item {
                    implicitWidth: 64
                    implicitHeight: 64
                    
                    Item {
                        id: item
                        x: parent.width / 2 - 32
                        y: parent.height / 2 - 32
                        width: 64
                        height: 64
                        opacity: loadingScreen.visible ? 1 : 0
                        
                        RotationAnimator {
                            target: item
                            running: loadingScreen.visible
                            from: 0
                            to: 360
                            loops: Animation.Infinite
                            duration: 1250
                        }
                        
                        Repeater {
                            id: repeater
                            model: 6
                            
                            Rectangle {
                                x: item.width / 2 - width / 2
                                y: item.height / 2 - height / 2
                                implicitWidth: 8
                                implicitHeight: 8
                                radius: 4
                                color: "#3b82f6"
                                transform: [
                                    Translate {
                                        y: -Math.min(item.width, item.height) * 0.5 + 4
                                    },
                                    Rotation {
                                        angle: index / repeater.count * 360
                                        origin.x: 4
                                        origin.y: Math.min(item.width, item.height) * 0.5
                                    }
                                ]
                            }
                        }
                    }
                }
            }
            
            Text {
                text: "Conectando aos Satélites..."
                color: "#e0e0e0"
                font.pixelSize: 18
                font.family: "Segoe UI"
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }
    }
    
    // Download Overlay
    property bool isMapDownloading: false
    property int downloadCurrent: 0
    property int downloadTotal: 100
    
    Rectangle {
        id: downloadOverlay
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.8)
        visible: isMapDownloading
        z: 999
        
        // Block mouse events
        MouseArea { anchors.fill: parent }
        
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 20
            
            BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                running: isMapDownloading
            }
            
            Text {
                text: "Configurando mapa offline pela primeira vez...\nIsso pode levar alguns segundos."
                color: "white"
                font.pixelSize: 16
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                Layout.alignment: Qt.AlignHCenter
            }
            
            ProgressBar {
                id: downloadProgress
                Layout.fillWidth: true
                Layout.preferredWidth: 300
                from: 0
                to: downloadTotal
                value: downloadCurrent
            }
            
            Text {
                text: downloadCurrent + " / " + downloadTotal + " blocos verificados"
                color: "#AAAAAA"
                font.pixelSize: 12
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
    
    Connections {
        target: typeof mapController !== "undefined" ? mapController : null
        
        function onMapDownloadProgress(current, total) {
            isMapDownloading = true;
            downloadCurrent = current;
            downloadTotal = total;
        }
        
        function onMapDownloadFinished() {
            isMapDownloading = false;
        }
    }
    
    Timer {
        id: startupTimer
        interval: 400
        repeat: false
        onTriggered: {
            if (typeof mapController !== "undefined" && mapController) {
                mapController.checkAndDownloadInitialMap();
                mapController.fetchOfficialMapLabels();
                mapController.fetchMapItems();
                mapController.fetchStockData();
            }
        }
    }
    
    Component.onCompleted: {
        startupTimer.start();
    }
    
    onVisibleChanged: {
        if (visible) {
            startupTimer.start();
        }
    }
}
