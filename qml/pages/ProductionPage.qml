import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: root
    color: "transparent"
    property int scrollBarContentPadding: 14
    property bool compactPlanningLayout: width < 1120

    Component.onCompleted: productionController.ensureLoaded()

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    Flickable {
        id: pageScroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: content.height
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height + 1

        ScrollBar.vertical: ScrollBar {
            policy: pageScroll.contentHeight > pageScroll.height + 1 ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
            active: pageScroll.moving || pageScroll.flicking
        }

        ColumnLayout {
            id: content
            width: Math.max(0, pageScroll.width - root.scrollBarContentPadding)
            height: Math.max(pageScroll.height, implicitHeight)
            spacing: 12

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: tr("production.title")
                color: settingsController.textColor
                font.family: "Segoe UI"
                font.pixelSize: 26
                font.bold: true
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            PrimaryButton {
                text: tr("production.reload_db")
                fill: Qt.rgba(0,0,0,0.4)
                hoverFill: Qt.rgba(1,1,1,0.1)
                textFill: settingsController.accentColor
                onClicked: productionController.reload()
            }
            PrimaryButton {
                text: tr("production.clear")
                fill: Qt.rgba(0,0,0,0.4)
                hoverFill: Qt.rgba(1,1,1,0.1)
                textFill: settingsController.accentColor
                onClicked: productionController.clear()
            }
        }

        Text {
            text: productionController.status
            color: productionController.status.indexOf("missing") >= 0 || productionController.status.indexOf("error") >= 0 ? settingsController.dangerColor : settingsController.mutedTextColor
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
                spacing: 6
                Repeater {
                    model: [
                        { "label": tr("production.mode_factory"), "value": "factory", "fill": settingsController.controlColor },
                        { "label": tr("production.mode_mpf"), "value": "mpf", "fill": settingsController.infoColor }
                    ]
                    delegate: Button {
                        id: modeButton
                        text: modelData.label
                        checkable: true
                        hoverEnabled: true
                        checked: productionController.mode === modelData.value
                        Layout.preferredWidth: Math.max(118, modeLabel.implicitWidth + 30)
                        Layout.preferredHeight: 32
                        onClicked: productionController.setMode(modelData.value)
                        contentItem: Text {
                            id: modeLabel
                            text: modeButton.text
                            color: modeButton.checked ? settingsController.textInverseColor : settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        background: Rectangle {
                            radius: 7
                            color: "transparent"
                            border.color: "transparent"
                            Rectangle { anchors.fill: parent; radius: 7; color: modeButton.checked ? settingsController.accentColor : settingsController.scrimColor; opacity: modeButton.checked ? 1.0 : (modeButton.hovered ? 0.55 : 0.3); Behavior on opacity { NumberAnimation { duration: 120 } } }
                            Rectangle { anchors.fill: parent; radius: 7; color: "transparent"; border.color: modeButton.checked || modeButton.hovered ? settingsController.accentColor : Qt.rgba(1,1,1,0.1); border.width: modeButton.checked || modeButton.hovered ? 2 : 1; opacity: modeButton.checked ? 1.0 : (modeButton.hovered ? 0.75 : 1.0) }
                        }
                    }
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
                        color: settingsController.textColor; font.family: "Segoe UI"; font.pixelSize: 14; font.bold: true
                    }
                    PrimaryButton {
                        text: "+"
                        leftPadding: 0; rightPadding: 0
                        implicitWidth: 24; implicitHeight: 24; font.pixelSize: 12
                        onClicked: productionController.setFactoryMultiplier(productionController.factoryMultiplier + 1)
                    }
                }
            }

            Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 20; color: settingsController.borderColor }

            // Faction Selection
            RowLayout {
                spacing: 6
                Repeater {
                    model: [
                        { "label": tr("production.faction_neutral"), "value": "Neutral", "fill": settingsController.controlColor },
                        { "label": tr("production.faction_warden"), "value": "Warden", "fill": settingsController.infoColor },
                        { "label": tr("production.faction_colonial"), "value": "Colonial", "fill": settingsController.successColor }
                    ]
                    delegate: Button {
                        id: factionButton
                        text: modelData.label
                        checkable: true
                        hoverEnabled: true
                        checked: productionController.faction === modelData.value
                        Layout.preferredWidth: Math.max(92, factionLabel.implicitWidth + 30)
                        Layout.preferredHeight: 32
                        onClicked: productionController.setFaction(modelData.value)
                        contentItem: Text {
                            id: factionLabel
                            text: factionButton.text
                            color: factionButton.checked ? settingsController.textInverseColor : settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        background: Rectangle {
                            radius: 7
                            color: "transparent"
                            border.color: "transparent"
                            Rectangle { anchors.fill: parent; radius: 7; color: factionButton.checked ? settingsController.accentColor : settingsController.scrimColor; opacity: factionButton.checked ? 1.0 : (factionButton.hovered ? 0.55 : 0.3); Behavior on opacity { NumberAnimation { duration: 120 } } }
                            Rectangle { anchors.fill: parent; radius: 7; color: "transparent"; border.color: factionButton.checked || factionButton.hovered ? settingsController.accentColor : Qt.rgba(1,1,1,0.1); border.width: factionButton.checked || factionButton.hovered ? 2 : 1; opacity: factionButton.checked ? 1.0 : (factionButton.hovered ? 0.75 : 1.0) }
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true } // Spacer
        }

        Item {
            id: categories
            Layout.fillWidth: true
            Layout.preferredHeight: 72
            clip: false

            RowLayout {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Repeater {
                    model: productionController.categoriesModel
                    delegate: Button {
                        id: categoryButton
                        hoverEnabled: true
                        Layout.preferredWidth: 76
                        Layout.preferredHeight: 64
                        onClicked: productionController.setCategory(String(model.name || ""))
                        background: Rectangle {
                            radius: 4
                            color: "transparent"
                            border.color: "transparent"
                            Rectangle { anchors.fill: parent; radius: 4; color: model.active ? settingsController.accentColor : settingsController.scrimColor; opacity: model.active ? 0.32 : (categoryButton.hovered ? 0.38 : 0.2); Behavior on opacity { NumberAnimation { duration: 120 } } }
                            Rectangle { anchors.fill: parent; radius: 4; color: "transparent"; border.color: settingsController.accentColor; opacity: model.active ? 1.0 : (categoryButton.hovered ? 0.65 : 0.2); border.width: model.active || categoryButton.hovered ? 2 : 1; Behavior on opacity { NumberAnimation { duration: 120 } } }
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
                                color: model.active ? settingsController.accentColor : settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }
                    }
                }
            }
        }

        GridLayout {
            id: planningLayout
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: root.compactPlanningLayout ? 980 : 560
            columns: root.compactPlanningLayout ? 1 : 2
            columnSpacing: 8
            rowSpacing: 8

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: !root.compactPlanningLayout
                Layout.minimumWidth: root.compactPlanningLayout ? 0 : 620
                Layout.preferredHeight: root.compactPlanningLayout ? Math.max(420, Math.min(560, root.height * 0.55)) : 560
                radius: 8
                color: "transparent"
                border.color: "transparent"
                Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.2 }
                Rectangle { anchors.fill: parent; radius: 8; color: settingsController.accentColor; opacity: 0.035 }
                Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: settingsController.accentColor; opacity: 0.2; border.width: 1 }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Text {
                            text: tr("production.items")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 17
                            font.bold: true
                        }
                        TextField {
                            Layout.fillWidth: true
                            Layout.maximumWidth: 280
                            Layout.preferredHeight: 32
                            placeholderText: tr("production.search_placeholder") || "Buscar item..."
                            color: settingsController.textColor
                            onTextChanged: productionController.search(text)
                            background: Rectangle { radius: 7; color: "transparent"; Rectangle { anchors.fill: parent; radius: 7; color: settingsController.scrimColor; opacity: 0.3 } border.color: Qt.rgba(1,1,1,0.1) }
                        }
                    }

                    GridView {
                        id: productGrid
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        reuseItems: true
                        property int columnCount: Math.max(1, Math.floor(width / 118))
                        cellWidth: Math.max(112, Math.floor(width / columnCount))
                        cellHeight: 92
                        model: productionController.availableItemsModel
                        ScrollBar.vertical: ScrollBar { active: productGrid.moving }

                        delegate: Rectangle {
                            width: Math.max(104, productGrid.cellWidth - 10)
                            height: 84
                            radius: 8
                            color: "transparent"
                            border.color: "transparent"
                            Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.3 }
                            Rectangle { anchors.fill: parent; radius: 8; color: settingsController.accentColor; opacity: mouse.containsMouse ? 0.15 : 0.03 }
                            Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: settingsController.accentColor; opacity: mouse.containsMouse ? 0.8 : 0.15; border.width: 1 }

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
                                    color: settingsController.textColor
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
                                    color: settingsController.mutedTextColor
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
                Layout.fillWidth: root.compactPlanningLayout
                Layout.preferredWidth: root.compactPlanningLayout ? planningLayout.width : Math.min(520, Math.max(440, root.width * 0.32))
                Layout.minimumWidth: root.compactPlanningLayout ? 0 : 420
                Layout.maximumWidth: root.compactPlanningLayout ? 16777215 : 540
                Layout.fillHeight: true
                radius: 8
                color: "transparent"
                border.color: "transparent"
                Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.2 }
                Rectangle { anchors.fill: parent; radius: 8; color: settingsController.accentColor; opacity: 0.035 }
                Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: settingsController.accentColor; opacity: 0.2; border.width: 1 }

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
                            color: "transparent"
                            border.color: "transparent"
                            Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.4 }
                            Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: Qt.rgba(1,1,1,0.1); border.width: 1 }
                            
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
                                    Text { text: tr("production.summary"); color: settingsController.mutedTextColor; font.family: "Segoe UI"; font.pixelSize: 11; font.bold: true }
                                    Text { text: productionController.summary; color: settingsController.textColor; font.family: "Segoe UI"; font.pixelSize: 16; font.bold: true }
                                    Text { text: productionController.orders; color: settingsController.mutedTextColor; font.family: "Segoe UI"; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                                }
                                
                                Rectangle {
                                    Layout.preferredWidth: 1
                                    Layout.fillHeight: true
                                    color: Qt.rgba(1,1,1,0.1)
                                }
                                
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Text { text: tr("production.materials"); color: settingsController.mutedTextColor; font.family: "Segoe UI"; font.pixelSize: 11; font.bold: true }
                                    Text { text: productionController.materialDetail; color: settingsController.textColor; font.family: "Segoe UI"; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true; wrapMode: Text.WordWrap; maximumLineCount: 2 }
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
                                    color: settingsController.backgroundColor
                                    border.color: Qt.rgba(1,1,1,0.1)
                                    
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
                                            Text { text: model.label || ""; color: settingsController.mutedTextColor; font.family: "Segoe UI"; font.pixelSize: 10; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                                            RowLayout {
                                                spacing: 4
                                                Text { text: String(model.quantity || 0); color: settingsController.accentColor; font.family: "Segoe UI"; font.pixelSize: 13; font.bold: true }
                                                Text { text: String(model.crates || 0) + "cx"; color: settingsController.textColor; font.family: "Segoe UI"; font.pixelSize: 9; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
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
                        color: settingsController.warningTextColor
                        border.color: settingsController.warningColor
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 7
                            Text {
                                text: "!"
                                color: settingsController.warningColor
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                font.bold: true
                                Layout.preferredWidth: 12
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Text {
                                id: warningText
                                text: productionController.warning
                                color: settingsController.warningColor
                                font.family: "Segoe UI"
                                font.pixelSize: 10
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }
                    }

                    ScrollView {
                        id: planningScroll
                        property int scrollGutter: 14
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        background: Rectangle { color: "transparent" }

                        Column {
                            id: planningContent
                            width: Math.max(0, planningScroll.availableWidth - planningScroll.scrollGutter)
                            spacing: 8

                            RowLayout {
                                width: planningContent.width
                                spacing: 8
                                Text {
                                    text: tr("production.queue")
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 15
                                    font.bold: true
                                    Layout.fillWidth: true
                                }
                                PrimaryButton {
                                    text: tr("production.clear") || "Limpar Tudo"
                                    fill: Qt.rgba(0,0,0,0.4)
                                    hoverFill: Qt.rgba(1,1,1,0.1)
                                    textFill: settingsController.accentColor
                                    implicitHeight: 22
                                    font.pixelSize: 10
                                    onClicked: productionController.clear()
                                }
                            }

                            Column {
                                id: queueColumn
                                width: planningContent.width
                                spacing: 6
                                Repeater {
                                    model: productionController.queueCategoryRows
                                    delegate: Rectangle {
                                        property var row: modelData
                                        width: queueColumn.width
                                        height: 42
                                        radius: 8
                                        color: "transparent"
                                        border.color: "transparent"
                                        Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.4 }
                                        Rectangle { anchors.fill: parent; radius: 8; color: settingsController.accentColor; opacity: row.active ? 0.15 : 0.0; Behavior on opacity { NumberAnimation { duration: 120 } } }
                                        Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: row.active ? settingsController.accentColor : Qt.rgba(1,1,1,0.1); border.width: 1 }
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 6
                                            spacing: 8
                                            Image {
                                                source: row.icon || ""
                                                Layout.preferredWidth: 28
                                                Layout.preferredHeight: 28
                                                fillMode: Image.PreserveAspectFit
                                            }
                                            ColumnLayout {
                                                Layout.preferredWidth: 48
                                                spacing: 0
                                                Text { text: row.mark || ""; color: row.active ? settingsController.accentColor : settingsController.textColor; font.family: "Segoe UI"; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                                Text { text: String(row.count || 0) + "/" + String(row.limit || 0); color: settingsController.mutedTextColor; font.family: "Segoe UI"; font.pixelSize: 10; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                            }

                                            Item { Layout.fillWidth: true }

                                            Flow {
                                                spacing: 5
                                                Repeater {
                                                    model: row.slots || []
                                                    delegate: Rectangle {
                                                        property var slot: modelData
                                                        width: 30
                                                        height: 30
                                                        radius: 6
                                                        color: "transparent"
                                                        border.color: "transparent"
                                                        Rectangle { anchors.fill: parent; radius: 6; color: settingsController.scrimColor; opacity: slot.filled ? 0.0 : 0.3 }
                                                        Rectangle { anchors.fill: parent; radius: 6; color: settingsController.accentColor; opacity: slot.filled ? 0.2 : 0.0 }
                                                        Rectangle { anchors.fill: parent; radius: 6; color: "transparent"; border.color: slot.filled ? settingsController.accentColor : Qt.rgba(1,1,1,0.1); border.width: 1 }
                                                        opacity: slot.filled ? 1.0 : 0.72

                                                        Image {
                                                            anchors.centerIn: parent
                                                            source: slot.icon || ""
                                                            width: 26
                                                            height: 26
                                                            fillMode: Image.PreserveAspectFit
                                                            visible: slot.filled && String(slot.icon || "") !== ""
                                                        }
                                                        Text {
                                                            anchors.centerIn: parent
                                                            text: slot.filled ? String(slot.name || "").slice(0, 2).toUpperCase() : ""
                                                            color: settingsController.textColor
                                                            font.family: "Segoe UI"
                                                            font.pixelSize: 9
                                                            font.bold: true
                                                            visible: slot.filled && String(slot.icon || "") === ""
                                                        }
                                                        Rectangle {
                                                            visible: slot.filled && (slot.discount || 0) > 0
                                                            anchors.right: parent.right
                                                            anchors.top: parent.top
                                                            anchors.margins: 1
                                                            width: 15
                                                            height: 11
                                                            radius: 3
                                                            color: "transparent"
                                                            Rectangle { anchors.fill: parent; radius: 3; color: settingsController.scrimColor; opacity: 0.5 }
                                                            border.color: settingsController.accentColor
                                                            Text {
                                                                anchors.centerIn: parent
                                                                text: String(slot.discount || 0)
                                                                color: settingsController.accentColor
                                                                font.family: "Segoe UI"
                                                                font.pixelSize: 8
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
                                                        ToolTip.text: (slot.name || "") + (slot.priceTooltip ? "\n" + slot.priceTooltip : "")
                                                    }
                                                }
                                            }

                                            Button {
                                                text: "âœ•"
                                                Layout.preferredWidth: 28
                                                Layout.preferredHeight: 28
                                                visible: (row.count || 0) > 0
                                                onClicked: productionController.clearCategory(row.name || "")
                                                background: Rectangle {
                                                    color: parent.hovered ? settingsController.dangerHoverColor : "transparent"
                                                    radius: 4
                                                }
                                                contentItem: Text {
                                                    text: parent.text
                                                    color: parent.hovered ? settingsController.textColor : settingsController.mutedTextColor
                                                    horizontalAlignment: Text.AlignHCenter
                                                    verticalAlignment: Text.AlignVCenter
                                                    font.pixelSize: 12
                                                    font.bold: true
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Text {
                                width: planningContent.width
                                text: tr("production.routes")
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 15
                                font.bold: true
                            }

                            Rectangle {
                                width: planningContent.width
                                height: Math.max(170, routesContent.implicitHeight + 16)
                                radius: 8
                                color: "transparent"
                                border.color: "transparent"
                                Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.4 }
                                Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: Qt.rgba(1,1,1,0.1); border.width: 1 }

                                ColumnLayout {
                                    id: routesContent
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 6

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text {
                                            text: productionController.routeSummary
                                            color: settingsController.textColor
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
                                                color: "transparent"
                                                border.color: "transparent"
                                                Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.5 }
                                                Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: row.warning ? settingsController.warningColor : Qt.rgba(1,1,1,0.1); border.width: 1 }
                                                
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
                                                            Layout.preferredWidth: 98
                                                            spacing: 6
                                                            Rectangle {
                                                                Layout.fillWidth: true
                                                                Layout.preferredHeight: 22
                                                                radius: 4
                                                                color: Qt.rgba(0,0,0,0.4)
                                                                Text {
                                                                    anchors.fill: parent
                                                                    anchors.leftMargin: 4
                                                                    anchors.rightMargin: 4
                                                                    text: row.title || ""
                                                                    color: settingsController.accentColor
                                                                    font.family: "Segoe UI"
                                                                    font.bold: true
                                                                    font.pixelSize: 11
                                                                    horizontalAlignment: Text.AlignHCenter
                                                                    verticalAlignment: Text.AlignVCenter
                                                                    elide: Text.ElideRight
                                                                }
                                                            }
                                                            RowLayout {
                                                                spacing: 4
                                                                Text { text: tr("production.route_input") || "Ida:"; color: settingsController.mutedTextColor; font.family: "Segoe UI"; font.pixelSize: 10; font.capitalization: Font.Capitalize }
                                                                Item { Layout.fillWidth: true }
                                                                Text { text: String(row.inputSlots || 0) + "/" + String(row.capacity || 0); color: settingsController.warningColor; font.family: "Segoe UI"; font.pixelSize: 11; font.bold: true }
                                                            }
                                                        }
                                                        
                                                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Qt.rgba(1,1,1,0.1); Layout.topMargin: 2; Layout.bottomMargin: 2 }
                                                        
                                                        // Middle: Materials to Take
                                                        ColumnLayout {
                                                            Layout.fillWidth: true
                                                            Layout.alignment: Qt.AlignTop
                                                            spacing: 4
                                                            Text { text: tr("production.route_take") || "Levar"; color: settingsController.mutedTextColor; font.family: "Segoe UI"; font.pixelSize: 11; font.bold: true }
                                                            Repeater {
                                                                model: row.materialsList || []
                                                                delegate: RowLayout {
                                                                    spacing: 6
                                                                    Image {
                                                                        source: modelData.icon || ""
                                                                        Layout.preferredWidth: 16
                                                                        Layout.preferredHeight: 16
                                                                        fillMode: Image.PreserveAspectFit
                                                                        visible: String(modelData.icon || "") !== ""
                                                                    }
                                                                    Text {
                                                                        text: (row.vehicle === "Flatbed" ? modelData.crates + "x crates " : modelData.quantity + "x ") + modelData.label
                                                                        color: settingsController.textColor
                                                                        font.family: "Segoe UI"
                                                                        font.pixelSize: 11
                                                                        Layout.fillWidth: true
                                                                        elide: Text.ElideRight
                                                                    }
                                                                }
                                                            }
                                                            Text {
                                                                visible: (!row.materialsList || row.materialsList.length === 0)
                                                                text: "-"
                                                                color: settingsController.textColor
                                                                font.family: "Segoe UI"
                                                                font.pixelSize: 11
                                                            }
                                                        }
                                                        
                                                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Qt.rgba(1,1,1,0.1); Layout.topMargin: 2; Layout.bottomMargin: 2 }
                                                        
                                                        // Right: Items to Collect
                                                        ColumnLayout {
                                                            Layout.fillWidth: true
                                                            Layout.alignment: Qt.AlignTop
                                                            spacing: 4
                                                            Text { text: tr("production.route_collect") || "Retirar"; color: settingsController.mutedTextColor; font.family: "Segoe UI"; font.pixelSize: 11; font.bold: true }
                                                            Repeater {
                                                                model: row.ordersList || []
                                                                delegate: RowLayout {
                                                                    spacing: 6
                                                                    Image {
                                                                        source: modelData.icon || ""
                                                                        Layout.preferredWidth: 16
                                                                        Layout.preferredHeight: 16
                                                                        fillMode: Image.PreserveAspectFit
                                                                        visible: String(modelData.icon || "") !== ""
                                                                    }
                                                                    Text {
                                                                        text: modelData.count + "x " + modelData.name + " (" + modelData.count + " caixas)"
                                                                        color: settingsController.textColor
                                                                        font.family: "Segoe UI"
                                                                        font.pixelSize: 11
                                                                        Layout.fillWidth: true
                                                                        elide: Text.ElideRight
                                                                    }
                                                                }
                                                            }
                                                            Text {
                                                                visible: (!row.ordersList || row.ordersList.length === 0)
                                                                text: "-"
                                                                color: settingsController.textColor
                                                                font.family: "Segoe UI"
                                                                font.pixelSize: 11
                                                            }
                                                        }
                                                    }
                                                    
                                                    Rectangle {
                                                        Layout.fillWidth: true
                                                        Layout.minimumHeight: 26
                                                        implicitHeight: warningRow.implicitHeight + 8
                                                        radius: 4
                                                        color: settingsController.dangerPanelColor
                                                        border.color: settingsController.dangerColor
                                                        visible: Boolean(row.warning)
                                                        RowLayout {
                                                            id: warningRow
                                                            anchors.fill: parent
                                                            anchors.margins: 4
                                                            spacing: 6
                                                            Text { text: "âš ï¸"; font.pixelSize: 12; Layout.alignment: Qt.AlignTop }
                                                            Text { 
                                                                text: row.warning || ""
                                                                color: settingsController.dangerColor
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
}
