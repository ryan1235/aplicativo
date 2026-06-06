import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: root
    color: "transparent"

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
            spacing: 10

            ComboBox {
                id: modeBox
                Layout.preferredWidth: 130
                model: productionController.modes
                currentIndex: Math.max(0, productionController.modes.indexOf(productionController.mode))
                onActivated: productionController.setMode(currentText)
            }
            ComboBox {
                Layout.preferredWidth: 150
                model: productionController.factions
                currentIndex: Math.max(0, productionController.factions.indexOf(productionController.faction))
                onActivated: productionController.setFaction(currentText)
            }
            RowLayout {
                visible: productionController.mode === "factory"
                spacing: 6
                Text { text: tr("production.factories"); color: "#99abc4"; font.family: "Segoe UI"; font.bold: true }
                SpinBox {
                    from: 1
                    to: 2
                    value: productionController.factoryMultiplier
                    onValueModified: productionController.setFactoryMultiplier(value)
                    Layout.preferredWidth: 90
                }
            }
            TextField {
                Layout.fillWidth: true
                placeholderText: tr("production.search_placeholder")
                color: "#edf6ff"
                onTextChanged: productionController.search(text)
                background: Rectangle { radius: 7; color: "#0e1a2d"; border.color: "#2d496f" }
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
                    model: productionController.categoryRows
                    delegate: Button {
                        property var row: modelData
                        width: 112
                        height: 46
                        onClicked: productionController.setCategory(row.name || "")
                        background: Rectangle {
                            radius: 8
                            color: row.active ? "#5eead4" : "#111c31"
                            border.color: row.active ? "#5eead4" : "#24486d"
                            Behavior on color { ColorAnimation { duration: 120 } }
                        }
                        contentItem: ColumnLayout {
                            spacing: 1
                            Item {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 25
                                Image {
                                    anchors.centerIn: parent
                                    source: row.icon || ""
                                    width: 24
                                    height: 24
                                    fillMode: Image.PreserveAspectFit
                                    visible: String(row.icon || "") !== ""
                                }
                                Text {
                                    anchors.centerIn: parent
                                    text: row.mark || ""
                                    color: row.active ? "#041014" : "#edf6ff"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                    font.bold: true
                                    visible: String(row.icon || "") === ""
                                }
                                Rectangle {
                                    visible: (row.count || 0) > 0
                                    anchors.right: parent.right
                                    anchors.rightMargin: 26
                                    anchors.top: parent.top
                                    width: Math.max(16, countText.implicitWidth + 8)
                                    height: 16
                                    radius: 7
                                    color: row.active ? "#07111f" : "#5eead4"
                                    border.color: row.active ? "#041014" : "#5eead4"
                                    Text {
                                        id: countText
                                        anchors.centerIn: parent
                                        text: String(row.count || 0)
                                        color: row.active ? "#5eead4" : "#041014"
                                        font.family: "Segoe UI"
                                        font.pixelSize: 9
                                        font.bold: true
                                    }
                                }
                            }
                            Text {
                                text: row.name || ""
                                color: row.active ? "#041014" : "#99abc4"
                                font.family: "Segoe UI"
                                font.pixelSize: 9
                                horizontalAlignment: Text.AlignHCenter
                                Layout.fillWidth: true
                                elide: Text.ElideRight
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

                    ScrollView {
                        id: productScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        background: Rectangle { color: "transparent" }

                        Flow {
                            width: productScroll.availableWidth
                            spacing: 8

                            Repeater {
                                model: productionController.availableItemRows
                                delegate: Rectangle {
                                    property var row: modelData
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
                                            source: row.icon || ""
                                            Layout.alignment: Qt.AlignHCenter
                                            Layout.preferredWidth: 30
                                            Layout.preferredHeight: 30
                                            fillMode: Image.PreserveAspectFit
                                        }
                                        Text {
                                            text: row.name || "-"
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
                                            text: (row.faction || "-") + " | " + String(row.quantityPerCrate || 0) + "/crate"
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
                                                productionController.removeItemByKey(row.key || "")
                                            else if ((event.modifiers & Qt.ShiftModifier) || (event.modifiers & Qt.ControlModifier))
                                                productionController.fillCategoryWithItem(row.key || "")
                                            else
                                                productionController.addItemByKey(row.key || "")
                                        }
                                    }
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

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 8
                        rowSpacing: 8
                        MetricCard {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 88
                            title: tr("production.summary")
                            value: productionController.summary
                            detail: productionController.orders
                            contentMargins: 10
                            contentSpacing: 3
                            valuePixelSize: 19
                            detailPixelSize: 10
                            detailMaximumLineCount: 2
                        }
                        MetricCard {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 88
                            title: tr("production.materials")
                            value: productionController.materialSummary
                            detail: productionController.materialDetail
                            accent: "#8ab4ff"
                            contentMargins: 10
                            contentSpacing: 3
                            valuePixelSize: 17
                            detailPixelSize: 10
                            detailMaximumLineCount: 2
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
                                        ComboBox {
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
                                                height: 84
                                                radius: 7
                                                color: "#07111f"
                                                border.color: "#1e3554"
                                                RowLayout {
                                                    anchors.fill: parent
                                                    anchors.margins: 7
                                                    spacing: 8
                                                    ColumnLayout {
                                                        Layout.preferredWidth: 78
                                                        spacing: 2
                                                        Text { text: row.title || ""; color: "#5eead4"; font.family: "Segoe UI"; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                                                        Text { text: row.vehicle || ""; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                                                        Text { text: String(row.inputSlots || 0) + "/" + String(row.capacity || 0) + " " + tr("production.route_input"); color: "#ffd166"; font.family: "Segoe UI"; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                                                        Text { text: String(row.outputCrates || 0) + "/" + String(row.capacity || 0) + " " + tr("production.route_output"); color: "#8ab4ff"; font.family: "Segoe UI"; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                                                    }
                                                    ColumnLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 2
                                                        Text { text: tr("production.route_take"); color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 10; font.bold: true }
                                                        Text { text: row.materials || "-"; color: "#edf6ff"; font.family: "Segoe UI"; font.pixelSize: 10; wrapMode: Text.WordWrap; maximumLineCount: 3; Layout.fillWidth: true }
                                                    }
                                                    ColumnLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 2
                                                        Text { text: tr("production.route_collect"); color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 10; font.bold: true }
                                                        Text { text: row.orders || "-"; color: "#edf6ff"; font.family: "Segoe UI"; font.pixelSize: 10; wrapMode: Text.WordWrap; maximumLineCount: 3; Layout.fillWidth: true }
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
