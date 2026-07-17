import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import "Vehicles.js" as VehiclesData

Item {
    id: root
    width: 320
    height: 480
    
    // Prevent clicks from passing through to map
    MouseArea { anchors.fill: parent }
    
    property string activeVehicleImage: typeof mapView !== "undefined" && mapView ? mapView.activeVehicleImage : ""
    property string activeVehicleName: typeof mapView !== "undefined" && mapView ? mapView.activeVehicleName : ""
    property int activeVehicleCount: typeof mapView !== "undefined" && mapView ? mapView.activeVehicleCount : 1
    
    signal vehicleSelected(string image, string name)
    signal vehicleCountChanged(int count)

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

    Column {
        id: vehicleSearchCol
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12
        
        property string searchText: ""
        
        Text {
            text: "Adicionar Veículo / Ícone"
            color: settingsController.textColor || "white"
            font.bold: true
            font.pixelSize: 14
        }
        
        RowLayout {
            width: parent.width
            spacing: 8
            
            Text {
                text: "Quantidade:"
                color: settingsController.textColor || "white"
                font.pixelSize: 12
            }
            
            Rectangle {
                width: 32; height: 32
                radius: 6
                color: settingsController.backgroundColor || "#121218"
                border.color: settingsController.borderColor || "#333340"
                border.width: 1
                Text { anchors.centerIn: parent; text: "-"; color: settingsController.textColor || "white"; font.bold: true }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (root.activeVehicleCount > 1) {
                            root.activeVehicleCount--
                            root.vehicleCountChanged(root.activeVehicleCount)
                        }
                    }
                    cursorShape: Qt.PointingHandCursor
                }
            }
            
            Text {
                text: root.activeVehicleCount.toString()
                color: settingsController.textColor || "white"
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
                Layout.minimumWidth: 24
                horizontalAlignment: Text.AlignHCenter
            }
            
            Rectangle {
                width: 32; height: 32
                radius: 6
                color: settingsController.backgroundColor || "#121218"
                border.color: settingsController.borderColor || "#333340"
                border.width: 1
                Text { anchors.centerIn: parent; text: "+"; color: settingsController.textColor || "white"; font.bold: true }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (root.activeVehicleCount < 50) {
                            root.activeVehicleCount++
                            root.vehicleCountChanged(root.activeVehicleCount)
                        }
                    }
                    cursorShape: Qt.PointingHandCursor
                }
            }
        }
        
        TextField {
            width: parent.width
            placeholderText: "Buscar veículo..."
            color: settingsController.textColor || "white"
            font.pixelSize: 13
            background: Rectangle { 
                color: Qt.rgba(settingsController.backgroundColor.r, settingsController.backgroundColor.g, settingsController.backgroundColor.b, 0.5)
                border.color: settingsController.borderColor || "#333340"
                border.width: 1
                radius: 6 
            }
            onTextEdited: vehicleSearchCol.searchText = text.toLowerCase()
        }
        
        ScrollView {
            width: parent.width
            height: parent.height - y
            clip: true
            
            Column {
                width: parent.width
                spacing: 16
                
                Repeater {
                    model: {
                        if (typeof VehiclesData === "undefined" || !VehiclesData.data.categories) return [];
                        return VehiclesData.data.categories;
                    }
                    
                    delegate: Column {
                        width: parent.width
                        spacing: 8
                        visible: itemsRepeater.count > 0
                        
                        Text {
                            text: modelData.name
                            color: settingsController.accentColor || "#3b82f6"
                            font.bold: true
                            font.pixelSize: 13
                        }
                        
                        Grid {
                            columns: 3
                            spacing: 12
                            
                            Repeater {
                                id: itemsRepeater
                                model: {
                                    var res = [];
                                    var items = modelData.items;
                                    for (var i = 0; i < items.length; i++) {
                                        if (vehicleSearchCol.searchText === "" || items[i].name.toLowerCase().indexOf(vehicleSearchCol.searchText) !== -1) {
                                            res.push(items[i]);
                                        }
                                    }
                                    return res;
                                }
                                delegate: Rectangle {
                                    width: 80
                                    height: 88
                                    radius: 8
                                    color: Qt.rgba(settingsController.backgroundColor.r, settingsController.backgroundColor.g, settingsController.backgroundColor.b, 0.5)
                                    border.color: root.activeVehicleImage === modelData.image ? (settingsController.accentColor || "#3b82f6") : (settingsController.borderColor || "#333340")
                                    border.width: root.activeVehicleImage === modelData.image ? 2 : 1
                                    
                                    Behavior on border.color { ColorAnimation { duration: 150 } }
                                    
                                    Rectangle {
                                        anchors.fill: parent
                                        radius: 8
                                        color: "white"
                                        opacity: mouseArea.containsMouse ? 0.05 : 0.0
                                        Behavior on opacity { NumberAnimation { duration: 150 } }
                                    }
                                    
                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        spacing: 4
                                        
                                        Item {
                                            width: parent.width
                                            height: 50
                                            Image {
                                                source: typeof mapController !== "undefined" && mapController ? mapController.baseUrl.replace(/\/map-tiles\/.*$/, "") + modelData.image : modelData.image
                                                anchors.centerIn: parent
                                                width: Math.min(parent.width, 48)
                                                height: Math.min(parent.height, 48)
                                                fillMode: Image.PreserveAspectFit
                                                asynchronous: true
                                            }
                                        }
                                        
                                        Text {
                                            text: modelData.name
                                            color: settingsController.textColor || "white"
                                            font.pixelSize: 10
                                            width: parent.width
                                            wrapMode: Text.Wrap
                                            horizontalAlignment: Text.AlignHCenter
                                            maximumLineCount: 2
                                            elide: Text.ElideRight
                                        }
                                    }
                                    
                                    MouseArea {
                                        id: mouseArea
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.activeVehicleImage = modelData.image;
                                            root.activeVehicleName = modelData.name;
                                            root.vehicleSelected(modelData.image, modelData.name);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
