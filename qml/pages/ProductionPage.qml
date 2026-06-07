import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: root
    color: "transparent"

    Component.onCompleted: productionController.ensureLoaded()

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: tr("production.title")
                color: "#edf6ff"
                font.family: "Segoe UI"
                font.pixelSize: 26
                font.bold: true
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            PrimaryButton {
                text: tr("production.reload_db")
                fill: "#1d3353"
                hoverFill: "#2d496f"
                textFill: "#edf6ff"
                onClicked: productionController.reload()
            }
            PrimaryButton {
                text: tr("production.clear")
                fill: "#1d3353"
                hoverFill: "#2d496f"
                textFill: "#edf6ff"
                onClicked: productionController.clear()
            }
        }

        Text {
            text: productionController.status
            color: productionController.status.indexOf("missing") >= 0 || productionController.status.indexOf("error") >= 0 ? "#ff7a90" : "#99abc4"
            font.family: "Segoe UI"
            font.pixelSize: 12
            Layout.fillWidth: true
            elide: Text.ElideRight
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 16

            // Mode Selection
            RowLayout {
                spacing: 8
                RadioButton {
                    text: "Fábrica comum"
                    checked: productionController.mode === "factory"
                    onClicked: productionController.setMode("factory")
                    contentItem: Text { text: parent.text; color: parent.checked ? "#edf6ff" : "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 13; leftPadding: parent.indicator.width + parent.spacing; verticalAlignment: Text.AlignVCenter }
                }
                RowLayout {
                    visible: productionController.mode === "factory"
                    spacing: 4
                    PrimaryButton {
                        text: "-"
                        leftPadding: 0; rightPadding: 0
                        implicitWidth: 24; implicitHeight: 24; font.pixelSize: 12
                        onClicked: productionController.setFactoryMultiplier(Math.max(1, productionController.factoryMultiplier - 1))
                    }
                    Text {
                        text: productionController.factoryMultiplier
                        color: "#edf6ff"; font.family: "Segoe UI"; font.pixelSize: 14; font.bold: true
                    }
                    PrimaryButton {
                        text: "+"
                        leftPadding: 0; rightPadding: 0
                        implicitWidth: 24; implicitHeight: 24; font.pixelSize: 12
                        onClicked: productionController.setFactoryMultiplier(productionController.factoryMultiplier + 1)
                    }
                }
                RadioButton {
                    text: "MPF"
                    checked: productionController.mode === "mpf"
                    onClicked: productionController.setMode("mpf")
                    contentItem: Text { text: parent.text; color: parent.checked ? "#edf6ff" : "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 13; leftPadding: parent.indicator.width + parent.spacing; verticalAlignment: Text.AlignVCenter }
                }
            }

            Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 20; color: "#24486d" }

            // Faction Selection
            RowLayout {
                spacing: 8
                RadioButton {
                    text: "Neutro"
                    checked: productionController.faction === "Neutral"
                    onClicked: productionController.setFaction("Neutral")
                    contentItem: Text { text: parent.text; color: parent.checked ? "#edf6ff" : "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 13; leftPadding: parent.indicator.width + parent.spacing; verticalAlignment: Text.AlignVCenter }
                }
                RadioButton {
                    text: "Colonial"
                    checked: productionController.faction === "Colonial"
                    onClicked: productionController.setFaction("Colonial")
                    contentItem: Text { text: parent.text; color: parent.checked ? "#edf6ff" : "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 13; leftPadding: parent.indicator.width + parent.spacing; verticalAlignment: Text.AlignVCenter }
                }
                RadioButton {
                    text: "Warden"
                    checked: productionController.faction === "Warden"
                    onClicked: productionController.setFaction("Warden")
                    contentItem: Text { text: parent.text; color: parent.checked ? "#edf6ff" : "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 13; leftPadding: parent.indicator.width + parent.spacing; verticalAlignment: Text.AlignVCenter }
                }
            }

            Item { Layout.fillWidth: true } // Spacer

            ColumnLayout {
                spacing: 2
                Text { text: "SHIFT-CLIQUE PREENCHE A CATEGORIA"; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 9; font.bold: true; Layout.alignment: Qt.AlignRight }
                TextField {
                    Layout.preferredWidth: 260
                    placeholderText: tr("production.search_placeholder") || "Buscar item..."
                    color: "#edf6ff"
                    onTextChanged: productionController.search(text)
                    background: Rectangle { radius: 7; color: "#0e1a2d"; border.color: "#2d496f" }
                }
            }
        }

        ScrollView {
            id: categories
            Layout.fillWidth: true
            Layout.preferredHeight: 54
            clip: true
            ScrollBar.vertical.policy: ScrollBar.AlwaysOff
            background: Rectangle { color: "transparent" }

            Row {
                spacing: 8
                Repeater {
                    model: productionController.categoriesModel
                    delegate: Button {
                        width: 76
                        height: 76
                        onClicked: productionController.setCategory(String(model.name || ""))
                        background: Rectangle {
                            radius: 4
                            color: model.active ? "#5eead4" : "#111c31"
                            border.color: model.active ? "#5eead4" : "#24486d"
                            Behavior on color { ColorAnimation { duration: 120 } }
                        }
                        contentItem: ColumnLayout {
                            spacing: 4
                            Image {
                                Layout.alignment: Qt.AlignHCenter
                                source: model.icon || ""
                                Layout.preferredWidth: 32
                                Layout.preferredHeight: 32
                                fillMode: Image.PreserveAspectFit
                                asynchronous: true
                                cache: false
                            }
                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: (model.mark || "") + " " + String(model.count || 0)
                                color: model.active ? "#041014" : "#edf6ff"
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 8
                color: "#111c31"
                border.color: "#24486d"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: tr("production.items")
                        color: "#edf6ff"
                        font.family: "Segoe UI"
                        font.pixelSize: 17
                        font.bold: true
                    }

                    GridView {
                        id: productGrid
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        reuseItems: true
                        cellWidth: 116
                        cellHeight: 92
                        model: productionController.availableItemsModel
                        ScrollBar.vertical: ScrollBar { active: productGrid.moving }

                        delegate: Rectangle {
                            width: 108
                            height: 84
                            radius: 8
                            color: mouse.containsMouse ? "#172943" : "#0e1a2d"
                            border.color: "#2d496f"
                            Behavior on color { ColorAnimation { duration: 120 } }

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 2
                                Image {
                                    source: model.icon || ""
                                    Layout.alignment: Qt.AlignHCenter
                                    Layout.preferredWidth: 30
                                    Layout.preferredHeight: 30
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                    cache: false
                                    sourceSize.width: 40
                                    sourceSize.height: 40
                                }
                                Text {
                                    text: model.name || "-"
                                    color: "#edf6ff"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 9
                                    font.bold: true
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignHCenter
                                }
                                Text {
                                    text: (model.faction || "-") + " | " + String(model.quantityPerCrate || 0) + "/crate"
                                    color: "#99abc4"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 8
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: mouse
                                anchors.fill: parent
                                hoverEnabled: true
                                acceptedButtons: Qt.LeftButton | Qt.RightButton
                                onClicked: function(event) {
                                    if (event.button === Qt.RightButton)
                                        productionController.removeItemByKey(String(model.key || ""))
                                    else if ((event.modifiers & Qt.ShiftModifier) || (event.modifiers & Qt.ControlModifier))
                                        productionController.fillCategoryWithItem(String(model.key || ""))
                                    else
                                        productionController.addItemByKey(String(model.key || ""))
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.preferredWidth: 390
                Layout.fillHeight: true
                radius: 8
                color: "#111c31"
                border.color: "#24486d"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 7

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: summaryCol.implicitHeight + 20
                            radius: 8
                            color: "#0e1a2d"
                            border.color: "#1e3554"
                            
                            RowLayout {
                                id: summaryCol
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 10
                                spacing: 12
                                
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Text { text: "Resultado"; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 11; font.bold: true }
                                    Text { text: productionController.summary; color: "#edf6ff"; font.family: "Segoe UI"; font.pixelSize: 16; font.bold: true }
                                    Text { text: productionController.orders; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                                }
                                
                                Rectangle {
                                    Layout.preferredWidth: 1
                                    Layout.fillHeight: true
                                    color: "#1e3554"
                                }
                                
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Text { text: "Materiais"; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 11; font.bold: true }
                                    Text { text: productionController.materialDetail; color: "#edf6ff"; font.family: "Segoe UI"; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true; wrapMode: Text.WordWrap; maximumLineCount: 2 }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            
                            Repeater {
                                model: productionController.materialsModel
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 56
                                    radius: 6
                                    color: "#07111f"
                                    border.color: "#1e3554"
                                    
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 4
                                        spacing: 4
                                        Image {
                                            source: model.icon || ""
                                            Layout.preferredWidth: 24
                                            Layout.preferredHeight: 24
                                            fillMode: Image.PreserveAspectFit
                                            asynchronous: true
                                            cache: false
                                        }
                                        ColumnLayout {
                                            spacing: 0
                                            Layout.fillWidth: true
                                            Text { text: model.label || ""; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 10; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                                            RowLayout {
                                                spacing: 4
                                                Text { text: String(model.quantity || 0); color: "#8ab4ff"; font.family: "Segoe UI"; font.pixelSize: 13; font.bold: true }
                                                Text { text: String(model.crates || 0) + "cx"; color: "#edf6ff"; font.family: "Segoe UI"; font.pixelSize: 9; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        visible: String(productionController.warning || "") !== ""
                        Layout.preferredHeight: visible ? warningText.implicitHeight + 12 : 0
                        radius: 7
                        color: "#201b12"
                        border.color: "#ffd166"
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 7
                            Text {
                                text: "!"
                                color: "#ffd166"
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                font.bold: true
                                Layout.preferredWidth: 12
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Text {
                                id: warningText
                                text: productionController.warning
                                color: "#ffd166"
                                font.family: "Segoe UI"
                                font.pixelSize: 10
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }
                    }

                    ScrollView {
                        id: planningScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        background: Rectangle { color: "transparent" }

                        Column {
                            id: planningContent
                            width: planningScroll.availableWidth
                            spacing: 8

                            Text {
                                width: planningContent.width
                                text: tr("production.queue")
                                color: "#edf6ff"
                                font.family: "Segoe UI"
                                font.pixelSize: 15
                                font.bold: true
                            }

                            Column {
                                id: queueColumn
                                width: planningContent.width
                                spacing: 5
                                Repeater {
                                    model: productionController.queueCategoryRows
                                    delegate: Rectangle {
                                        property var row: modelData
                                        width: queueColumn.width
                                        height: 35
                                        radius: 7
                                        color: row.active ? "#132b43" : "#0e1a2d"
                                        border.color: row.active ? "#5eead4" : "#1e3554"
                                        Behavior on color { ColorAnimation { duration: 120 } }
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 5
                                            spacing: 7
                                            Image {
                                                source: row.icon || ""
                                                Layout.preferredWidth: 24
                                                Layout.preferredHeight: 24
                                                fillMode: Image.PreserveAspectFit
                                            }
                                            ColumnLayout {
                                                Layout.preferredWidth: 42
                                                spacing: 0
                                                Text { text: row.mark || ""; color: row.active ? "#5eead4" : "#edf6ff"; font.family: "Segoe UI"; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                                Text { text: String(row.count || 0) + "/" + String(row.limit || 0); color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 9; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                            }

                                            Flow {
                                                Layout.fillWidth: true
                                                spacing: 4
                                                Repeater {
                                                    model: row.slots || []
                                                    delegate: Rectangle {
                                                        property var slot: modelData
                                                        width: 26
                                                        height: 26
                                                        radius: 5
                                                        color: slot.filled ? "#172943" : "#07111f"
                                                        border.color: slot.filled ? "#2d6a91" : "#1e3554"
                                                        opacity: slot.filled ? 1.0 : 0.72

                                                        Image {
                                                            anchors.centerIn: parent
                                                            source: slot.icon || ""
                                                            width: 22
                                                            height: 22
                                                            fillMode: Image.PreserveAspectFit
                                                            visible: slot.filled && String(slot.icon || "") !== ""
                                                        }
                                                        Text {
                                                            anchors.centerIn: parent
                                                            text: slot.filled ? String(slot.name || "").slice(0, 2).toUpperCase() : ""
                                                            color: "#edf6ff"
                                                            font.family: "Segoe UI"
                                                            font.pixelSize: 8
                                                            font.bold: true
                                                            visible: slot.filled && String(slot.icon || "") === ""
                                                        }
                                                        Rectangle {
                                                            visible: slot.filled && (slot.discount || 0) > 0
                                                            anchors.right: parent.right
                                                            anchors.top: parent.top
                                                            anchors.margins: 1
                                                            width: 13
                                                            height: 10
                                                            radius: 3
                                                            color: "#07111f"
                                                            border.color: "#5eead4"
                                                            Text {
                                                                anchors.centerIn: parent
                                                                text: String(slot.discount || 0)
                                                                color: "#5eead4"
                                                                font.family: "Segoe UI"
                                                                font.pixelSize: 7
                                                                font.bold: true
                                                            }
                                                        }
                                                        MouseArea {
                                                            id: slotMouse
                                                            anchors.fill: parent
                                                            enabled: slot.filled
                                                            hoverEnabled: true
                                                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                                            onClicked: productionController.removeQueueSlot(row.name || "", slot.line || 0)
                                                        }
                                                        ToolTip.visible: slotMouse.containsMouse && slot.filled
                                                        ToolTip.text: slot.name || ""
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Text {
                                width: planningContent.width
                                text: tr("production.routes")
                                color: "#edf6ff"
                                font.family: "Segoe UI"
                                font.pixelSize: 15
                                font.bold: true
                            }

                            Rectangle {
                                width: planningContent.width
                                height: Math.max(170, routesContent.implicitHeight + 16)
                                radius: 8
                                color: "#0e1a2d"
                                border.color: "#24486d"

                                ColumnLayout {
                                    id: routesContent
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 6

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text {
                                            text: productionController.routeSummary
                                            color: "#edf6ff"
                                            font.family: "Segoe UI"
                                            font.pixelSize: 12
                                            font.bold: true
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                        PrimaryComboBox {
                                            Layout.preferredWidth: 116
                                            model: productionController.routeVehicleOptions
                                            currentIndex: Math.max(0, productionController.routeVehicleOptions.indexOf(productionController.routeVehicleMode))
                                            onActivated: productionController.setRouteVehicleMode(currentText)
                                        }
                                    }

                                    Column {
                                        id: routeTripsColumn
                                        Layout.fillWidth: true
                                        spacing: 6
                                        Repeater {
                                            model: productionController.routeTripRows
                                            delegate: Rectangle {
                                                property var row: modelData
                                                width: routeTripsColumn.width
                                                height: mainCol.implicitHeight + 16
                                                radius: 8
                                                color: "#0a1526"
                                                border.color: row.warning ? "#8c2e2e" : "#1e3554"
                                                
                                                ColumnLayout {
                                                    id: mainCol
                                                    anchors.left: parent.left
                                                    anchors.right: parent.right
                                                    anchors.top: parent.top
                                                    anchors.margins: 8
                                                    spacing: 8
                                                    
                                                    RowLayout {
                                                        id: contentLayout
                                                        Layout.fillWidth: true
                                                        spacing: 12
                                                        
                                                        // Left side: Trip info
                                                        ColumnLayout {
                                                            Layout.preferredWidth: 84
                                                            spacing: 6
                                                            Rectangle {
                                                                Layout.fillWidth: true
                                                                Layout.preferredHeight: 22
                                                                radius: 4
                                                                color: "#132b43"
                                                                Text { anchors.centerIn: parent; text: row.title || ""; color: "#5eead4"; font.family: "Segoe UI"; font.bold: true; font.pixelSize: 12 }
                                                            }
                                                            RowLayout {
                                                                spacing: 4
                                                                Text { text: tr("production.route_input") || "Ida:"; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 10 }
                                                                Item { Layout.fillWidth: true }
                                                                Text { text: String(row.inputSlots || 0) + "/" + String(row.capacity || 0); color: "#ffd166"; font.family: "Segoe UI"; font.pixelSize: 11; font.bold: true }
                                                            }
                                                            RowLayout {
                                                                spacing: 4
                                                                Text { text: tr("production.route_output") || "Volta:"; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 10 }
                                                                Item { Layout.fillWidth: true }
                                                                Text { text: String(row.outputCrates || 0) + "/" + String(row.capacity || 0); color: "#8ab4ff"; font.family: "Segoe UI"; font.pixelSize: 11; font.bold: true }
                                                            }
                                                        }
                                                        
                                                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#1e3554"; Layout.topMargin: 2; Layout.bottomMargin: 2 }
                                                        
                                                        // Middle: Materials to Take
                                                        ColumnLayout {
                                                            Layout.fillWidth: true
                                                            Layout.alignment: Qt.AlignTop
                                                            spacing: 4
                                                            Text { text: tr("production.route_take") || "Levar"; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 11; font.bold: true }
                                                            Text { text: row.materials || "-"; color: "#edf6ff"; font.family: "Segoe UI"; font.pixelSize: 11; wrapMode: Text.WordWrap; maximumLineCount: 4; Layout.fillWidth: true; lineHeight: 1.2 }
                                                        }
                                                        
                                                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#1e3554"; Layout.topMargin: 2; Layout.bottomMargin: 2 }
                                                        
                                                        // Right: Items to Collect
                                                        ColumnLayout {
                                                            Layout.fillWidth: true
                                                            Layout.alignment: Qt.AlignTop
                                                            spacing: 4
                                                            Text { text: tr("production.route_collect") || "Retirar"; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 11; font.bold: true }
                                                            Text { text: row.orders || "-"; color: "#edf6ff"; font.family: "Segoe UI"; font.pixelSize: 11; wrapMode: Text.WordWrap; maximumLineCount: 4; Layout.fillWidth: true; lineHeight: 1.2 }
                                                        }
                                                    }
                                                    
                                                    Rectangle {
                                                        Layout.fillWidth: true
                                                        Layout.minimumHeight: 26
                                                        implicitHeight: warningRow.implicitHeight + 8
                                                        radius: 4
                                                        color: "#2a1111"
                                                        border.color: "#5c2b2b"
                                                        visible: Boolean(row.warning)
                                                        RowLayout {
                                                            id: warningRow
                                                            anchors.fill: parent
                                                            anchors.margins: 4
                                                            spacing: 6
                                                            Text { text: "⚠️"; font.pixelSize: 12; Layout.alignment: Qt.AlignTop }
                                                            Text { 
                                                                text: row.warning || ""
                                                                color: "#ff9999"
                                                                font.family: "Segoe UI"
                                                                font.pixelSize: 11
                                                                font.bold: true
                                                                Layout.fillWidth: true
                                                                wrapMode: Text.WordWrap
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
                }
            }
        }
    }
}
