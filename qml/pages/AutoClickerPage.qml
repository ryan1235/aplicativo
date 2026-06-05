import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: content.implicitHeight + 24

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    function trArg(key, token, value) {
        return tr(key).replace(token, value)
    }

    function parsePositiveInt(text, fallback) {
        var value = parseInt(text)
        return isNaN(value) ? fallback : Math.max(0, value)
    }

    function comboIndex(model, value) {
        var index = model.indexOf(value)
        return index >= 0 ? index : 0
    }

    ColumnLayout {
        id: content
        width: root.width
        spacing: 8

        Text {
            text: tr("clicker.title")
            color: "#edf6ff"
            font.family: "Segoe UI"
            font.pixelSize: 22
            font.bold: true
            Layout.fillWidth: true
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "#111c31"
            border.color: autoClickerController.active ? "#5eead4" : "#24486d"
            implicitHeight: statusContent.implicitHeight + 18
            Behavior on border.color { ColorAnimation { duration: 160 } }

            ColumnLayout {
                id: statusContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 9
                spacing: 7

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Rectangle {
                        Layout.preferredWidth: 84
                        Layout.preferredHeight: 28
                        radius: 7
                        color: autoClickerController.active ? "#123c35" : "#263a55"
                        border.color: autoClickerController.active ? "#5eead4" : "#3d5878"
                        Text {
                            anchors.centerIn: parent
                            text: autoClickerController.active ? tr("clicker.on_badge") : tr("clicker.paused_badge")
                            color: autoClickerController.active ? "#5eead4" : "#c7d7ed"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    Text {
                        text: autoClickerController.status
                        color: autoClickerController.available ? "#edf6ff" : "#ff7a90"
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        font.bold: true
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    PrimaryButton {
                        text: autoClickerController.running ? tr("clicker.pause") : tr("clicker.resume")
                        enabled: autoClickerController.available
                        onClicked: autoClickerController.toggle()
                    }
                    PrimaryButton {
                        text: tr("clicker.capture")
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        enabled: autoClickerController.available
                        onClicked: autoClickerController.captureFoxhole()
                    }
                    PrimaryButton {
                        text: tr("overlay.preview")
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: overlayController.preview()
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 980 ? 4 : root.width > 660 ? 2 : 1
            columnSpacing: 8
            rowSpacing: 8

            Repeater {
                model: [
                    {"label": "clicker.key", "value": autoClickerController.hotkey, "setter": "auto"},
                    {"label": "clicker.key_move", "value": autoClickerController.moveHotkey, "setter": "move"},
                    {"label": "clicker.key_fixed", "value": autoClickerController.fixedHotkey, "setter": "fixed"},
                    {"label": "clicker.key_pilot", "value": autoClickerController.pilotHotkey, "setter": "pilot"}
                ]
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    radius: 8
                    color: "#111c31"
                    border.color: "#24486d"
                    implicitHeight: 48

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 6
                        Text {
                            text: tr(modelData.label)
                            color: "#99abc4"
                            font.bold: true
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        ComboBox {
                            Layout.preferredWidth: 94
                            Layout.preferredHeight: 28
                            model: autoClickerController.hotkeys
                            currentIndex: comboIndex(autoClickerController.hotkeys, modelData.value)
                            onActivated: {
                                if (modelData.setter === "auto")
                                    autoClickerController.setHotkey(currentText)
                                else if (modelData.setter === "move")
                                    autoClickerController.setMoveHotkey(currentText)
                                else if (modelData.setter === "fixed")
                                    autoClickerController.setFixedHotkey(currentText)
                                else
                                    autoClickerController.setPilotHotkey(currentText)
                            }
                        }
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 820 ? 3 : 1
            columnSpacing: 8
            rowSpacing: 8

            Rectangle {
                Layout.fillWidth: true
                radius: 8
                color: "#111c31"
                border.color: "#24486d"
                implicitHeight: 50
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6
                    Text {
                        text: tr("clicker.button")
                        color: "#99abc4"
                        font.bold: true
                        font.family: "Segoe UI"
                        font.pixelSize: 11
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    ComboBox {
                        id: mouseCombo
                        Layout.preferredWidth: 124
                        Layout.preferredHeight: 28
                        model: autoClickerController.mouseButtons
                        currentIndex: comboIndex(autoClickerController.mouseButtons, autoClickerController.mouseButton)
                        onActivated: autoClickerController.setMouseButton(currentText)
                        delegate: ItemDelegate {
                            width: mouseCombo.width
                            text: tr(autoClickerController.mouseButtonLabel(modelData))
                        }
                        contentItem: Text {
                            text: tr(autoClickerController.mouseButtonLabel(mouseCombo.currentText))
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 12
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 8
                color: "#111c31"
                border.color: "#24486d"
                implicitHeight: 50
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6
                    Text { text: tr("clicker.speed"); color: "#99abc4"; font.bold: true; font.family: "Segoe UI"; font.pixelSize: 11; Layout.preferredWidth: 56; elide: Text.ElideRight }
                    RowLayout {
                        Layout.fillWidth: true
                        Slider {
                            id: interval
                            from: 0.03
                            to: 0.5
                            value: autoClickerController.interval
                            Layout.fillWidth: true
                            onMoved: autoClickerController.setInterval(value)
                        }
                        Text {
                            text: interval.value.toFixed(2) + "s"
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            Layout.preferredWidth: 40
                            font.pixelSize: 11
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 8
                color: "#111c31"
                border.color: "#24486d"
                implicitHeight: 50
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8
                    Text { text: tr("clicker.shortcuts_title"); color: "#99abc4"; font.bold: true; font.family: "Segoe UI"; font.pixelSize: 11; Layout.preferredWidth: 70; elide: Text.ElideRight }
                    Text {
                        text: trArg("clicker.shortcuts_auto", "{hotkey}", autoClickerController.hotkey)
                        color: "#edf6ff"
                        font.family: "Segoe UI"
                        font.pixelSize: 10
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Text {
                        text: tr("clicker.f5_menu_subtitle")
                        color: "#7f93ad"
                        font.family: "Segoe UI"
                        font.pixelSize: 10
                        Layout.preferredWidth: 110
                        elide: Text.ElideRight
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
            implicitHeight: slotsGrid.implicitHeight + 18

            ColumnLayout {
                id: slotsGrid
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 9
                spacing: 6

                Text {
                    text: tr("clicker.slot_positions")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    font.bold: true
                    Layout.fillWidth: true
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 900 ? 4 : root.width > 560 ? 2 : 1
                    columnSpacing: 6
                    rowSpacing: 6

                    Repeater {
                        model: autoClickerController.slotModel
                        delegate: Rectangle {
                            required property int slotNumber
                            required property int slotX
                            required property int slotY
                            Layout.fillWidth: true
                            radius: 8
                            color: "#0e1a2d"
                            border.color: "#1e3554"
                            implicitHeight: 46

                            function commit() {
                                autoClickerController.setSlotPosition(
                                    slotNumber,
                                    parsePositiveInt(slotXField.text, slotX),
                                    parsePositiveInt(slotYField.text, slotY)
                                )
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 5
                                Text {
                                    text: tr("clicker.slot") + " " + slotNumber
                                    color: "#8ab4ff"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                    font.bold: true
                                    Layout.preferredWidth: 42
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Text { text: "X"; color: "#99abc4"; font.family: "Segoe UI"; font.bold: true }
                                    TextField {
                                        id: slotXField
                                        text: slotX.toString()
                                        selectByMouse: true
                                        inputMethodHints: Qt.ImhDigitsOnly
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 26
                                        onEditingFinished: commit()
                                    }
                                    Text { text: "Y"; color: "#99abc4"; font.family: "Segoe UI"; font.bold: true }
                                    TextField {
                                        id: slotYField
                                        text: slotY.toString()
                                        selectByMouse: true
                                        inputMethodHints: Qt.ImhDigitsOnly
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 26
                                        onEditingFinished: commit()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 900 ? 2 : 1
            columnSpacing: 6
            rowSpacing: 6

            Rectangle {
                Layout.fillWidth: true
                radius: 8
                color: "#111c31"
                border.color: "#24486d"
                implicitHeight: overlayColumn.implicitHeight + 18

                ColumnLayout {
                    id: overlayColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 9
                    spacing: 6

                    Text {
                        text: tr("overlay.title")
                        color: "#edf6ff"
                        font.family: "Segoe UI"
                        font.pixelSize: 13
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 640 ? 4 : 2
                        columnSpacing: 10
                        rowSpacing: 4
                        ToggleSwitch {
                            checked: overlayController.enabled
                            Layout.alignment: Qt.AlignVCenter
                            onClicked: overlayController.setEnabled(checked)
                        }
                        Text {
                            text: tr("overlay.show")
                            color: "#c7d7ed"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: tr("overlay.hotkey")
                            color: "#99abc4"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            font.bold: true
                            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                        }
                        ComboBox {
                            Layout.preferredWidth: 112
                            Layout.preferredHeight: 28
                            model: overlayController.hotkeys
                            currentIndex: comboIndex(overlayController.hotkeys, overlayController.hotkey)
                            onActivated: overlayController.setHotkey(currentText)
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Text {
                            text: tr("overlay.color")
                            color: "#99abc4"
                            font.family: "Segoe UI"
                            Layout.fillWidth: true
                        }
                        ComboBox {
                            id: colorCombo
                            Layout.preferredWidth: 142
                            Layout.preferredHeight: 28
                            model: overlayController.colors
                            currentIndex: comboIndex(overlayController.colors, overlayController.colorName)
                            onActivated: overlayController.setColorName(currentText)
                            delegate: ItemDelegate {
                                width: colorCombo.width
                                text: tr(overlayController.colorLabelKey(modelData))
                            }
                            contentItem: Text {
                                text: tr(overlayController.colorLabelKey(colorCombo.currentText))
                                color: "#edf6ff"
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 12
                                elide: Text.ElideRight
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 540 ? 2 : 1
                        columnSpacing: 6
                        rowSpacing: 3

                        Repeater {
                            model: [
                                {"label": "overlay.profile", "checked": overlayController.showProfile, "setter": "profile"},
                                {"label": "overlay.clicker_title", "checked": overlayController.showClicker, "setter": "clicker"},
                                {"label": "overlay.target", "checked": overlayController.showTarget, "setter": "target"},
                                {"label": "overlay.upload_notification", "checked": overlayController.notificationEnabled, "setter": "notification"}
                            ]
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true
                                implicitHeight: 28
                                radius: 6
                                color: "#0e1a2d"
                                border.color: "#1e3554"
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 6
                                    anchors.rightMargin: 6
                                    spacing: 9
                                    ToggleSwitch {
                                        checked: modelData.checked
                                        Layout.alignment: Qt.AlignVCenter
                                        onClicked: {
                                            if (modelData.setter === "profile")
                                                overlayController.setShowProfile(checked)
                                            else if (modelData.setter === "clicker")
                                                overlayController.setShowClicker(checked)
                                            else if (modelData.setter === "target")
                                                overlayController.setShowTarget(checked)
                                            else
                                                overlayController.setNotificationEnabled(checked)
                                        }
                                    }
                                    Text {
                                        text: tr(modelData.label)
                                        color: "#c7d7ed"
                                        font.family: "Segoe UI"
                                        font.pixelSize: 10
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 8
                color: "#111c31"
                border.color: "#24486d"
                implicitHeight: ordersColumn.implicitHeight + 18

                ColumnLayout {
                    id: ordersColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 9
                    spacing: 6

                    Text {
                        text: tr("clicker.f5_menu_title")
                        color: "#edf6ff"
                        font.family: "Segoe UI"
                        font.pixelSize: 13
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    ListView {
                        id: orderList
                        Layout.fillWidth: true
                        Layout.preferredHeight: 92
                        clip: true
                        spacing: 4
                        model: autoClickerController.orderModel
                        currentIndex: 0
                        onCountChanged: {
                            if (count > 0 && currentIndex < 0)
                                currentIndex = 0
                            if (count > 0 && currentIndex >= count)
                                currentIndex = count - 1
                        }

                        delegate: Rectangle {
                            required property int index
                            required property string name
                            width: orderList.width
                            height: 30
                            radius: 7
                            color: ListView.isCurrentItem ? "#1d3353" : "#0e1a2d"
                            border.color: ListView.isCurrentItem ? "#5eead4" : "#1e3554"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 4
                                spacing: 6
                                TextField {
                                    text: name
                                    selectByMouse: true
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 24
                                    onActiveFocusChanged: if (activeFocus) orderList.currentIndex = index
                                    onEditingFinished: autoClickerController.setOrderName(index, text)
                                }
                                PrimaryButton {
                                    text: tr("clicker.remove_order")
                                    implicitHeight: 24
                                    fill: "#431926"
                                    hoverFill: "#5f2034"
                                    textFill: "#edf6ff"
                                    onClicked: autoClickerController.removeOrder(index)
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                z: -1
                                onClicked: orderList.currentIndex = index
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 5
                        PrimaryButton {
                            text: tr("clicker.add_order")
                            fill: "#1d3353"
                            hoverFill: "#2d496f"
                            textFill: "#edf6ff"
                            onClicked: autoClickerController.addOrder()
                        }
                        PrimaryButton {
                            text: tr("clicker.start_selected_order")
                            onClicked: autoClickerController.startOrder(orderList.currentIndex)
                        }
                    }

                    Text {
                        text: tr("clicker.f5_stock_title")
                        color: "#99abc4"
                        font.family: "Segoe UI"
                        font.bold: true
                        font.pixelSize: 10
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 5
                        PrimaryButton {
                            text: tr("clicker.f5_open_stockpile")
                            fill: "#1d3353"
                            hoverFill: "#2d496f"
                            textFill: "#edf6ff"
                            onClicked: appController.setCurrentPage("stockpile")
                        }
                        PrimaryButton {
                            text: tr("clicker.f5_refresh_stockpile")
                            fill: "#1d3353"
                            hoverFill: "#2d496f"
                            textFill: "#edf6ff"
                            onClicked: {
                                appController.setCurrentPage("stockpile")
                                stockpileController.extractOnce()
                            }
                        }
                    }
                }
            }
        }
    }
}
