import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import "../components"

Item {
    id: root

    // Opaque background to save resources and avoid loading large wallpapers
    Rectangle {
        anchors.fill: parent
        color: "#0a0f18"
        z: -1
    }

    MapView {
        id: mapView
        anchors.fill: parent
        // No margins for true fullscreen
    }

    // Loading Screen Overlay (dados da API)
    Rectangle {
        id: loadingScreen
        anchors.fill: parent
        color: "#1c2025"
        z: 99
        
        property bool apiReady: typeof mapController !== "undefined" && mapController && mapController.mapTextItemsModel && mapController.mapTextItemsModel.length > 0
        property bool isReady: apiReady
            && (typeof mapController === "undefined" || !mapController || !mapController.isBlockingBake)
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
                running: parent.parent.visible
                
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
                id: loadingStatusText
                text: {
                    if (!loadingScreen.apiReady) return "Conectando aos Satélites...";
                    return "Preparando região central do mapa...";
                }
                color: "#e0e0e0"
                font.pixelSize: 18
                font.family: "Segoe UI"
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.AlignHCenter
            }

            ProgressBar {
                anchors.horizontalCenter: parent.horizontalCenter
                visible: typeof mapController !== "undefined" && mapController && mapController.isBlockingBake && root.bakeProgressTotal > 0
                from: 0
                to: root.bakeProgressTotal
                value: root.bakeProgressCurrent
                width: 320
            }

            Text {
                visible: typeof mapController !== "undefined" && mapController && mapController.isBlockingBake && root.bakeProgressTotal > 0
                text: root.bakeProgressCurrent + " / " + root.bakeProgressTotal
                color: "#9ca3af"
                font.pixelSize: 12
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }
    }
    
    // Download Overlay (tiles crus legados)
    property bool isMapDownloading: false
    property int downloadCurrent: 0
    property int downloadTotal: 100

    property bool isMapBaking: false
    property bool isBackgroundBaking: false
    property string bakeStage: ""
    property int bakeProgressCurrent: 0
    property int bakeProgressTotal: 0
    property string bakeStatusMessage: ""
    
    // Indicador discreto enquanto o restante das camadas gera em segundo plano
    Rectangle {
        id: backgroundBakePill
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 16
        width: bgBakeColumn.implicitWidth + 20
        height: bgBakeColumn.implicitHeight + 12
        radius: 8
        color: Qt.rgba(0, 0, 0, 0.75)
        border.color: "#374151"
        visible: isBackgroundBaking
        z: 50

        Column {
            id: bgBakeColumn
            anchors.centerIn: parent
            spacing: 4

            Text {
                text: bakeStatusMessage || "Otimizando mapa..."
                color: "#e5e7eb"
                font.pixelSize: 11
                anchors.horizontalCenter: parent.horizontalCenter
            }

            ProgressBar {
                width: 180
                from: 0
                to: bakeProgressTotal > 0 ? bakeProgressTotal : 1
                value: bakeProgressCurrent
            }
        }
    }
    
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

        function onMapBakeProgress(stage, current, total) {
            bakeStage = stage;
            bakeProgressCurrent = current;
            bakeProgressTotal = total;
            isMapBaking = typeof mapController !== "undefined" && mapController && mapController.isBlockingBake;
            isBackgroundBaking = typeof mapController !== "undefined" && mapController && mapController.isBackgroundBake;

            if (stage === "icons_viewport") {
                bakeStatusMessage = "Camada 1: ícones da região visível...";
            } else if (stage === "icons_background") {
                bakeStatusMessage = "Segundo plano: ícones restantes...";
            } else if (stage === "labels_viewport") {
                bakeStatusMessage = "Camada 2: nomes da região visível...";
            } else if (stage === "labels_background") {
                bakeStatusMessage = "Segundo plano: nomes restantes...";
            } else if (stage === "icons_fetch" || stage === "labels_fetch") {
                bakeStatusMessage = "Consultando dados do mapa...";
            }
        }

        function onMapBakeFinished() {
            isMapBaking = false;
            isBackgroundBaking = false;
            bakeProgressCurrent = 0;
            bakeProgressTotal = 0;
            bakeStatusMessage = "";
        }

        function onMapViewportReady() {
            isMapBaking = false;
        }
    }
    
    Timer {
        id: startupTimer
        interval: 400
        repeat: false
        onTriggered: {
            if (typeof mapController !== "undefined" && mapController) {
                mapController.checkAndGenerateBakedTiles();
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
