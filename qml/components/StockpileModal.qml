import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: stockpileModal
    property var modelData
    property bool hasStock: modelData && modelData.stock !== undefined
    property bool isHoveredMapItem: false
    z: 50
    // Keep visible if either the map icon is hovered or the panel itself is hovered/pinned
    property bool isPinned: false
    visible: hasStock && (isHoveredMapItem || panelHoverHandler.hovered || isPinned)
    opacity: visible ? 1 : 0
    
    // Position directly next to the icon without a gap, so hover is continuous
    
    
    
    // Default sizes (smaller when pinned to look cleaner on map)
    width: isPinned ? 420 : 600
    height: stockHoverContent.implicitHeight + 20
    radius: 8
    color: settingsController.surfaceColor 
    border.color: settingsController.borderColor
    border.width: 1
    
    Behavior on opacity { NumberAnimation { duration: 150 } }
    
    HoverHandler {
        id: panelHoverHandler
    }
    
    TapHandler {
        onTapped: {
            stockpileModal.isPinned = !stockpileModal.isPinned;
            if (stockpileModal.isPinned) {
                stockpileModal.parent.scale = 1.0;
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: settingsController.backgroundColor
        opacity: 0.2
    }

    // Keep track of which warehouse is selected
    property int selectedWarehouseIndex: 0
    property var currentWarehouse: (modelData && modelData.stock && modelData.stock.length > selectedWarehouseIndex) ? modelData.stock[selectedWarehouseIndex] : null

    // Helper to group items by category
    function getItemsByCategory(catKey) {
        if (!currentWarehouse || !currentWarehouse.items) return [];
        var res = [];
        for (var i = 0; i < currentWarehouse.items.length; i++) {
            var item = currentWarehouse.items[i];
            // Match categories (or map multiple API categories to the UI category)
            if (catKey === "Priority" && item.category === "Priority") {
                res.push(item);
            } else if (catKey === "Supplies" && (item.category === "Supplies" || item.category === "Medical" || item.category === "Utility")) {
                res.push(item);
            } else if (catKey === "CommonLogi" && (item.category === "Small Arms" || item.category === "Heavy Arms" || item.category === "Heavy Ammo")) {
                res.push(item);
            } else if (catKey === "Vehicles" && item.category === "Vehicles") {
                res.push(item);
            } else if (catKey === "Others" && item.category !== "Priority" && item.category !== "Supplies" && item.category !== "Medical" && item.category !== "Utility" && item.category !== "Small Arms" && item.category !== "Heavy Arms" && item.category !== "Heavy Ammo" && item.category !== "Vehicles") {
                res.push(item);
            }
        }
        return res;
    }

    ColumnLayout {
        id: stockHoverContent
        anchors.fill: parent
        anchors.margins: 10
        spacing: 12

        // Header row
        RowLayout {
            Layout.fillWidth: true
            
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    text: root.tr("map.stock.title", "Visual do estoque")
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 16
                    font.bold: true
                }
                Text {
                    text: root.tr("map.stock.updated", "Atualizado") + ": " + (modelData ? modelData.name : "") + " - " + (stockpileModal.currentWarehouse ? stockpileModal.currentWarehouse.last_update : "")
                    color: settingsController.mutedTextColor
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                }
            }
            
            // Warehouse Selector
            ComboBox {
                id: warehouseCombo
                Layout.preferredWidth: 150
                visible: modelData && modelData.stock !== undefined && modelData.stock !== null && modelData.stock.length > 1
                model: {
                    var arr = [];
                    if (modelData && modelData.stock) {
                        for (var i = 0; i < modelData.stock.length; i++) {
                            arr.push(modelData.stock[i].warehouse_name);
                        }
                    }
                    return arr;
                }
                currentIndex: stockpileModal.selectedWarehouseIndex
                onCurrentIndexChanged: {
                    if (currentIndex >= 0) {
                        stockpileModal.selectedWarehouseIndex = currentIndex;
                    }
                }
                
                background: Rectangle {
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor
                    radius: 4
                }
                contentItem: Text {
                    text: warehouseCombo.currentText
                    color: "white"
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 12
                    leftPadding: 10
                }
            }
            
            // Optional pin indicator
            Text {
                text: stockpileModal.isPinned ? "­ƒôî" : ""
                color: "#FFD700"
                font.pixelSize: 14
                visible: stockpileModal.isPinned
            }
        }
        
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: settingsController.borderColor
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: settingsController.borderColor
        }
        
        // Dynamic categories
        Repeater {
            model: [
                { key: "Priority", label: root.tr("map.stock.priority", "PRIORIDADE") },
                { key: "Supplies", label: root.tr("map.stock.supplies", "SUPRIMENTOS") },
                { key: "CommonLogi", label: root.tr("map.stock.common_logi", "LOGI COMUM") },
                { key: "Vehicles", label: root.tr("map.stock.vehicles", "VE├ìCULOS") },
                { key: "Others", label: root.tr("map.stock.others", "OUTROS") }
            ]
            delegate: ColumnLayout {
                property var catItems: stockpileModal.getItemsByCategory(modelData.key)
                visible: catItems.length > 0
                spacing: 4
                Layout.fillWidth: true

                Text {
                    text: modelData.label
                    color: settingsController.mutedTextColor
                    font.family: "Segoe UI"
                    font.pixelSize: 10
                    font.bold: true
                }
                
                Flow {
                    Layout.fillWidth: true
                    spacing: 4
                    Repeater {
                        model: catItems
                        delegate: Rectangle {
                            width: 60
                            height: 28
                            color: settingsController.backgroundColor
                            border.color: settingsController.borderColor
                            border.width: 1
                            radius: 3
                            
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 4
                                spacing: 4
                                Image {
                                    source: modelData.icon || ""
                                    sourceSize.width: 20
                                    sourceSize.height: 20
                                    Layout.preferredWidth: 20
                                    Layout.preferredHeight: 20
                                    fillMode: Image.PreserveAspectFit
                                }
                                Text {
                                    text: modelData.quantity || "0"
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignRight
}
                            }
                        }
                    }
                }
            }
        }
    }
}
