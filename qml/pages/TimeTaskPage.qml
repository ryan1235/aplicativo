import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import "../components"

Flickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: content.implicitHeight + 36

    Component.onCompleted: timeTaskController.ensureLoaded()

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    function comboIndex(model, value) {
        var index = model.indexOf(value)
        return index >= 0 ? index : 0
    }

    function openSaveDialog(defaultName) {
        saveNameField.text = defaultName || timeTaskController.macroName || "macro"
        saveNameField.selectAll()
        saveNameDialog.open()
        saveNameField.forceActiveFocus()
    }

    function openRenameDialog(name) {
        renameField.text = name || timeTaskController.selectedMacroName
        renameField.selectAll()
        renameDialog.open()
        renameField.forceActiveFocus()
    }

    function openConfirm(kind, title, body) {
        confirmDialog.kind = kind
        confirmTitle.text = title
        confirmBody.text = body
        confirmDialog.open()
    }

    component GlassPanel: Rectangle {
        id: panel
        property color accent: settingsController.accentColor
        default property alias content: panelContent.data

        Layout.fillWidth: true
        radius: 8
        color: "transparent"
        border.color: "transparent"
        border.width: 0
        Rectangle { anchors.fill: parent; radius: parent.radius; color: settingsController.scrimColor; opacity: 0.2 }
        Rectangle { anchors.fill: parent; radius: parent.radius; color: "transparent"; border.color: Qt.rgba(1, 1, 1, 0.08); border.width: 1 }
        implicitHeight: panelContent.implicitHeight + 28
        layer.enabled: true
        layer.effect: DropShadow {
            transparentBorder: true
            color: Qt.rgba(0, 0, 0, 0.20)
            radius: 18
            samples: 37
            verticalOffset: 5
        }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: panel.accent
            opacity: 0.035
        }

        ColumnLayout {
            id: panelContent
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12
        }
    }

    component StatPill: Rectangle {
        property string label: ""
        property string value: ""
        property color accent: settingsController.accentColor

        Layout.fillWidth: true
        implicitHeight: 58
        radius: 8
        color: Qt.rgba(1, 1, 1, 0.05)
        border.color: Qt.rgba(1, 1, 1, 0.08)

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 3

            Text {
                text: label
                color: settingsController.disabledTextColor
                font.family: "Segoe UI"
                font.pixelSize: 10
                font.bold: true
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Text {
                text: value
                color: accent
                font.family: "Segoe UI"
                font.pixelSize: 14
                font.bold: true
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }
    }

    component FieldLabel: Text {
        color: settingsController.mutedTextColor
        font.family: "Segoe UI"
        font.pixelSize: 11
        font.bold: true
    }

    Connections {
        target: timeTaskController
        function onSavePromptRequested(defaultName) {
            openSaveDialog(defaultName)
        }
    }

    ColumnLayout {
        id: content
        width: Math.max(320, root.width - 40)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 18
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3

                Text {
                    text: tr("timetask.title")
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 26
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                Text {
                    text: tr("timetask.subtitle")
                    color: settingsController.accentColor
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    font.bold: true
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
            }

            Rectangle {
                Layout.preferredWidth: Math.max(104, liveStateText.implicitWidth + 28)
                Layout.preferredHeight: 34
                radius: 8
                color: "transparent"
                border.color: "transparent"
                Rectangle { anchors.fill: parent; radius: parent.radius; color: timeTaskController.recording ? settingsController.warningColor : timeTaskController.replaying ? settingsController.accentColor : settingsController.scrimColor; opacity: timeTaskController.recording || timeTaskController.replaying ? 0.2 : 0.3 }
                Rectangle { anchors.fill: parent; radius: parent.radius; color: "transparent"; border.color: timeTaskController.recording ? settingsController.warningColor : timeTaskController.replaying ? settingsController.accentColor : Qt.rgba(1,1,1,0.1); border.width: 1 }

                Text {
                    id: liveStateText
                    anchors.centerIn: parent
                    text: timeTaskController.recording ? tr("timetask.overlay_recording") : timeTaskController.replaying ? tr("timetask.overlay_playing") : tr("timetask.status_idle")
                    color: timeTaskController.recording ? settingsController.warningColor : timeTaskController.replaying ? settingsController.accentColor : settingsController.mutedTextColor
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                    font.bold: true
                    elide: Text.ElideRight
                }
            }
        }

        GlassPanel {
            accent: timeTaskController.recording ? settingsController.warningColor : settingsController.accentColor

            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                Rectangle {
                    Layout.preferredWidth: 6
                    Layout.preferredHeight: 62
                    radius: 3
                    color: timeTaskController.recording ? settingsController.warningColor : settingsController.accentColor
                    opacity: 0.95
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Text {
                        text: tr("timetask.record_title")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    Text {
                        text: tr("timetask.warning")
                        color: settingsController.accentColor
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        font.bold: true
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    Text {
                        text: timeTaskController.status
                        color: timeTaskController.available ? settingsController.secondaryTextColor : settingsController.dangerColor
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width >= 900 ? 3 : 1
                columnSpacing: 10
                rowSpacing: 10

                StatPill {
                    label: tr("timetask.status")
                    value: timeTaskController.recording ? tr("timetask.overlay_recording") : timeTaskController.replaying ? tr("timetask.overlay_playing") : tr("timetask.status_idle")
                    accent: timeTaskController.recording ? settingsController.warningColor : timeTaskController.replaying ? settingsController.accentColor : settingsController.infoColor
                }

                StatPill {
                    label: tr("timetask.metric_empty")
                    value: timeTaskController.captureSummary
                    accent: settingsController.accentColor
                }

                StatPill {
                    label: tr("timetask.replay_title")
                    value: timeTaskController.selectedMacroName !== "" ? timeTaskController.selectedMacroName : tr("timetask.replay_empty")
                    accent: settingsController.accentColor
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                PrimaryButton {
                    text: tr("timetask.start")
                    enabled: timeTaskController.available && !timeTaskController.recording
                    Layout.preferredWidth: 148
                    onClicked: timeTaskController.showRecordOverlay()
                }

                PrimaryButton {
                    text: timeTaskController.paused ? tr("timetask.play") : tr("timetask.pause")
                    enabled: timeTaskController.recording || timeTaskController.replaying
                    Layout.preferredWidth: 112
                    fill: Qt.rgba(0,0,0,0.4)
                    hoverFill: Qt.rgba(1,1,1,0.1)
                    textFill: settingsController.accentColor
                    onClicked: timeTaskController.pauseResume()
                }

                PrimaryButton {
                    text: tr("timetask.stop")
                    enabled: timeTaskController.recording
                    Layout.preferredWidth: 112
                    fill: settingsController.dangerColor
                    hoverFill: settingsController.dangerHoverColor
                    textFill: settingsController.surfaceColor
                    onClicked: timeTaskController.stopRecording()
                }

                PrimaryButton {
                    text: tr("timetask.save")
                    enabled: timeTaskController.available && timeTaskController.hasCapturedEvents
                    Layout.preferredWidth: 112
                    fill: settingsController.accentColor
                    hoverFill: settingsController.infoColor
                    textFill: settingsController.textInverseColor
                    onClicked: timeTaskController.requestSaveCurrent()
                }

                Item { Layout.fillWidth: true }

                PrimaryButton {
                    text: tr("timetask.open_record_overlay")
                    enabled: timeTaskController.available
                    Layout.preferredWidth: 176
                    fill: Qt.rgba(0,0,0,0.4)
                    hoverFill: Qt.rgba(1,1,1,0.1)
                    textFill: settingsController.accentColor
                    onClicked: timeTaskController.showRecordOverlay()
                }
            }
        }

        GlassPanel {
            accent: settingsController.accentColor

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    text: tr("timetask.playback_settings")
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 17
                    font.bold: true
                    Layout.fillWidth: true
                }

                PrimaryButton {
                    text: tr("timetask.play")
                    enabled: timeTaskController.available
                    Layout.preferredWidth: 118
                    fill: settingsController.accentColor
                    hoverFill: settingsController.infoColor
                    textFill: settingsController.textInverseColor
                    onClicked: timeTaskController.playSelected()
                }

                PrimaryButton {
                    text: tr("timetask.cancel")
                    enabled: timeTaskController.replaying
                    Layout.preferredWidth: 118
                    fill: settingsController.dangerColor
                    hoverFill: settingsController.dangerHoverColor
                    textFill: settingsController.textColor
                    onClicked: timeTaskController.stopReplay()
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width >= 980 ? 5 : root.width >= 720 ? 3 : 1
                columnSpacing: 12
                rowSpacing: 10

                ColumnLayout {
                    Layout.fillWidth: true
                    FieldLabel { text: tr("timetask.speed") }
                    PrimaryComboBox {
                        Layout.fillWidth: true
                        model: timeTaskController.speedOptions
                        currentIndex: comboIndex(timeTaskController.speedOptions, timeTaskController.speed)
                        onActivated: timeTaskController.setSpeed(currentText)
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    FieldLabel { text: tr("timetask.repeat") }
                    TextField {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        text: timeTaskController.repeat
                        onEditingFinished: timeTaskController.setRepeat(text)
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        verticalAlignment: Text.AlignVCenter
                        background: Rectangle { radius: 7; color: "transparent"
                        Rectangle { anchors.fill: parent; radius: 7; color: settingsController.scrimColor; opacity: 0.3 }
                        border.color: Qt.rgba(1,1,1,0.1) }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    FieldLabel { text: tr("timetask.delay") }
                    PrimaryComboBox {
                        Layout.fillWidth: true
                        model: timeTaskController.delayOptions
                        currentIndex: comboIndex(timeTaskController.delayOptions, timeTaskController.delay)
                        onActivated: timeTaskController.setDelay(currentText)
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    FieldLabel { text: tr("timetask.stock_interval") }
                    TextField {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        text: timeTaskController.stockInterval
                        onEditingFinished: timeTaskController.setStockInterval(text)
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        verticalAlignment: Text.AlignVCenter
                        background: Rectangle { radius: 7; color: "transparent"
                        Rectangle { anchors.fill: parent; radius: 7; color: settingsController.scrimColor; opacity: 0.3 }
                        border.color: Qt.rgba(1,1,1,0.1) }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    FieldLabel { text: tr("timetask.stock_macro") }
                    PrimaryComboBox {
                        Layout.fillWidth: true
                        model: timeTaskController.stockMacroOptions
                        currentIndex: comboIndex(timeTaskController.stockMacroOptions, timeTaskController.stockMacroName)
                        onActivated: timeTaskController.setStockMacroName(currentText)
                    }
                }
            }
        }

        GlassPanel {
            accent: settingsController.accentColor
            Layout.fillHeight: false

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    Text {
                        text: tr("timetask.replay_title")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    Text {
                        text: timeTaskController.selectedMacroName !== "" ? timeTaskController.selectedMacroName : tr("timetask.replay_empty")
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }

                PrimaryButton {
                    text: tr("timetask.refresh")
                    Layout.preferredWidth: 112
                    fill: Qt.rgba(0,0,0,0.4)
                    hoverFill: Qt.rgba(1,1,1,0.1)
                    textFill: settingsController.accentColor
                    onClicked: timeTaskController.refreshMacros()
                }
            }

            ListView {
                id: macroList
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(260, Math.min(430, contentHeight + 4))
                model: timeTaskController.macros
                spacing: 10
                clip: true

                Text {
                    anchors.centerIn: parent
                    visible: macroList.count === 0
                    text: tr("timetask.replay_empty")
                    color: settingsController.disabledTextColor
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    font.bold: true
                }

                delegate: Rectangle {
                    width: macroList.width
                    height: 118
                    radius: 8
                    color: "transparent"
                    border.color: "transparent"
                    border.width: 0
                    Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.2 }
                    Rectangle { anchors.fill: parent; radius: 8; color: settingsController.accentColor; opacity: selected ? 0.15 : (macroMouse.containsMouse ? 0.08 : 0.02); Behavior on opacity { NumberAnimation { duration: 120 } } }
                    Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: settingsController.accentColor; opacity: selected ? 1.0 : 0.2; border.width: selected ? 1.5 : 1; Behavior on opacity { NumberAnimation { duration: 120 } } }

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12
                        z: 1

                        Rectangle {
                            Layout.preferredWidth: 5
                            Layout.fillHeight: true
                            radius: 3
                            color: selected ? settingsController.accentColor : settingsController.infoColor
                            opacity: selected ? 1.0 : 0.65
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 5

                            Text {
                                text: name
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 15
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Text {
                                text: detail
                                color: settingsController.accentColor
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Text {
                                text: tr("timetask.created_at") + " " + createdAt + "    " + tr("timetask.updated_at") + " " + updatedAt
                                color: settingsController.mutedTextColor
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Text {
                                text: path
                                color: settingsController.disabledTextColor
                                font.family: "Segoe UI"
                                font.pixelSize: 10
                                Layout.fillWidth: true
                                elide: Text.ElideMiddle
                            }
                        }

                        ColumnLayout {
                            Layout.preferredWidth: root.width >= 900 ? 320 : 220
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                PrimaryButton {
                                    text: tr("timetask.play")
                                    Layout.fillWidth: true
                                    fill: settingsController.accentColor
                                    hoverFill: settingsController.infoColor
                                    textFill: settingsController.textInverseColor
                                    onClicked: {
                                        timeTaskController.selectMacro(index)
                                        timeTaskController.playSelected()
                                    }
                                }

                                PrimaryButton {
                                    text: tr("timetask.rename")
                                    Layout.fillWidth: true
                                    fill: Qt.rgba(0,0,0,0.4)
                                    hoverFill: Qt.rgba(1,1,1,0.1)
                                    textFill: settingsController.accentColor
                                    onClicked: {
                                        timeTaskController.selectMacro(index)
                                        openRenameDialog(name)
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                PrimaryButton {
                                    text: tr("timetask.overwrite")
                                    Layout.fillWidth: true
                                    enabled: timeTaskController.hasCapturedEvents
                                    fill: Qt.rgba(0,0,0,0.4)
                                    hoverFill: Qt.rgba(1,1,1,0.1)
                                    textFill: settingsController.accentColor
                                    onClicked: {
                                        timeTaskController.selectMacro(index)
                                        openConfirm("overwrite", tr("timetask.overwrite"), tr("timetask.overwrite_confirm").replace("{name}", name))
                                    }
                                }

                                PrimaryButton {
                                    text: tr("timetask.delete")
                                    Layout.fillWidth: true
                                    fill: settingsController.dangerPanelColor
                                    hoverFill: settingsController.dangerHoverColor
                                    textFill: settingsController.textColor
                                    onClicked: {
                                        timeTaskController.selectMacro(index)
                                        openConfirm("delete", tr("timetask.delete"), tr("timetask.delete_confirm").replace("{name}", name))
                                    }
                                }
                            }
                        }
                    }

                    MouseArea {
                        id: macroMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        z: 0
                        onClicked: timeTaskController.selectMacro(index)
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    active: true
                    policy: ScrollBar.AsNeeded
                }
            }
        }

        Text {
            text: tr("timetask.folder").replace("{path}", timeTaskController.macroFolder)
            color: settingsController.disabledTextColor
            font.family: "Segoe UI"
            font.pixelSize: 11
            Layout.fillWidth: true
            elide: Text.ElideMiddle
        }
    }

    Dialog {
        id: saveNameDialog
        modal: true
        width: Math.min(430, root.width - 48)
        x: Math.round((root.width - width) / 2)
        y: 96
        closePolicy: Popup.CloseOnEscape

        background: Rectangle {
            radius: 10
            color: settingsController.backgroundColor
            border.color: settingsController.accentColor
        }

        contentItem: ColumnLayout {
            spacing: 12

            Text {
                text: tr("timetask.save_name_title")
                color: settingsController.textColor
                font.family: "Segoe UI"
                font.pixelSize: 18
                font.bold: true
                Layout.fillWidth: true
            }

            Text {
                text: timeTaskController.captureSummary
                color: settingsController.mutedTextColor
                font.family: "Segoe UI"
                font.pixelSize: 12
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            TextField {
                id: saveNameField
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                color: settingsController.textColor
                font.family: "Segoe UI"
                verticalAlignment: Text.AlignVCenter
                selectByMouse: true
                background: Rectangle { radius: 7; color: "transparent"
                        Rectangle { anchors.fill: parent; radius: 7; color: settingsController.scrimColor; opacity: 0.3 }
                        border.color: Qt.rgba(1,1,1,0.1) }
                Keys.onReturnPressed: {
                    timeTaskController.saveCurrent(text)
                    saveNameDialog.close()
                }
            }
        }

        footer: Item {
            implicitHeight: 58
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                anchors.bottomMargin: 18
                spacing: 10
                PrimaryButton {
                    text: tr("timetask.cancel")
                    Layout.fillWidth: true
                    fill: Qt.rgba(0,0,0,0.4)
                    hoverFill: Qt.rgba(1,1,1,0.1)
                    textFill: settingsController.accentColor
                    onClicked: saveNameDialog.close()
                }
                PrimaryButton {
                    text: tr("timetask.save")
                    Layout.fillWidth: true
                    onClicked: {
                        timeTaskController.saveCurrent(saveNameField.text)
                        saveNameDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: renameDialog
        modal: true
        width: Math.min(430, root.width - 48)
        x: Math.round((root.width - width) / 2)
        y: 112
        closePolicy: Popup.CloseOnEscape

        background: Rectangle {
            radius: 10
            color: settingsController.backgroundColor
            border.color: settingsController.accentColor
        }

        contentItem: ColumnLayout {
            spacing: 12
            Text {
                text: tr("timetask.rename_title")
                color: settingsController.textColor
                font.family: "Segoe UI"
                font.pixelSize: 18
                font.bold: true
                Layout.fillWidth: true
            }
            TextField {
                id: renameField
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                color: settingsController.textColor
                font.family: "Segoe UI"
                verticalAlignment: Text.AlignVCenter
                selectByMouse: true
                background: Rectangle { radius: 7; color: "transparent"
                        Rectangle { anchors.fill: parent; radius: 7; color: settingsController.scrimColor; opacity: 0.3 }
                        border.color: Qt.rgba(1,1,1,0.1) }
                Keys.onReturnPressed: {
                    timeTaskController.renameSelectedMacro(text)
                    renameDialog.close()
                }
            }
        }

        footer: Item {
            implicitHeight: 58
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                anchors.bottomMargin: 18
                spacing: 10
                PrimaryButton {
                    text: tr("timetask.cancel")
                    Layout.fillWidth: true
                    fill: Qt.rgba(0,0,0,0.4)
                    hoverFill: Qt.rgba(1,1,1,0.1)
                    textFill: settingsController.accentColor
                    onClicked: renameDialog.close()
                }
                PrimaryButton {
                    text: tr("timetask.rename")
                    Layout.fillWidth: true
                    onClicked: {
                        timeTaskController.renameSelectedMacro(renameField.text)
                        renameDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: confirmDialog
        property string kind: ""
        modal: true
        width: Math.min(440, root.width - 48)
        x: Math.round((root.width - width) / 2)
        y: 126
        closePolicy: Popup.CloseOnEscape

        background: Rectangle {
            radius: 10
            color: settingsController.backgroundColor
            border.color: confirmDialog.kind === "delete" ? settingsController.dangerColor : settingsController.infoColor
        }

        contentItem: ColumnLayout {
            spacing: 10
            Text {
                id: confirmTitle
                color: settingsController.textColor
                font.family: "Segoe UI"
                font.pixelSize: 18
                font.bold: true
                Layout.fillWidth: true
            }
            Text {
                id: confirmBody
                color: settingsController.mutedTextColor
                font.family: "Segoe UI"
                font.pixelSize: 12
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
        }

        footer: Item {
            implicitHeight: 58
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                anchors.bottomMargin: 18
                spacing: 10
                PrimaryButton {
                    text: tr("timetask.cancel")
                    Layout.fillWidth: true
                    fill: Qt.rgba(0,0,0,0.4)
                    hoverFill: Qt.rgba(1,1,1,0.1)
                    textFill: settingsController.accentColor
                    onClicked: confirmDialog.close()
                }
                PrimaryButton {
                    text: confirmDialog.kind === "delete" ? tr("timetask.delete") : tr("timetask.overwrite")
                    Layout.fillWidth: true
                    fill: confirmDialog.kind === "delete" ? settingsController.dangerColor : settingsController.controlColor
                    hoverFill: confirmDialog.kind === "delete" ? settingsController.dangerHoverColor : settingsController.controlHoverColor
                    textFill: settingsController.textColor
                    onClicked: {
                        if (confirmDialog.kind === "delete")
                            timeTaskController.deleteSelectedMacro()
                        else if (confirmDialog.kind === "overwrite")
                            timeTaskController.overwriteSelectedMacro()
                        confirmDialog.close()
                    }
                }
            }
        }
    }
}


