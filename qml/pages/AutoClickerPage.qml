import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import "../components"

Flickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: content.implicitHeight + 40

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    function trReplaceWZ(key) {
        var text = tr(key)
        var letter = autoClickerController.wHoldLetter || "W"
        try {
            return text.replace(/\b[WZ]\b/g, letter)
        } catch (e) {
            return text
        }
    }

    function comboIndex(model, value) {
        var index = model.indexOf(value)
        return index >= 0 ? index : 0
    }

    function actionLabel(active) {
        return active ? "Soltar" : "Ativar"
    }

    component ModeCard: Rectangle {
        id: card
        property string title: ""
        property string detail: ""
        property string hotkey: ""
        property bool active: false
        property bool modeEnabled: true
        property color accent: settingsController.accentColor
        property string buttonText: root.actionLabel(active)
        default property alias extraContent: extraBox.data
        signal action()
        signal hotkeySelected(string key)
        signal modeToggled(bool value)

        Layout.fillWidth: true
        implicitHeight: cardContent.implicitHeight + 28
        Layout.minimumHeight: 168
        radius: 8
        opacity: modeEnabled ? 1.0 : 0.68
        color: active ? Qt.rgba(0.03, 0.12, 0.15, 0.92) : Qt.rgba(0.03, 0.07, 0.13, 0.92)
        border.color: !modeEnabled ? "#31425c" : (active ? accent : "#1d3353")
        border.width: active ? 1.5 : 1
        layer.enabled: true
        layer.effect: DropShadow {
            transparentBorder: true
            color: Qt.rgba(0, 0, 0, card.active ? 0.34 : 0.18)
            radius: card.active ? 18 : 10
            samples: card.active ? 37 : 21
            verticalOffset: card.active ? 6 : 3
        }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: card.accent
            opacity: !card.modeEnabled ? 0.015 : (card.active ? 0.10 : 0.035)
        }

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 4
            radius: 2
            color: card.accent
            opacity: !card.modeEnabled ? 0.22 : (card.active ? 1 : 0.45)
        }

        ColumnLayout {
            id: cardContent
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 14
            anchors.topMargin: 14
            anchors.bottomMargin: 14
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    Layout.preferredWidth: 9
                    Layout.preferredHeight: 9
                    radius: 5
                    color: !card.modeEnabled ? "#3f5878" : (card.active ? card.accent : "#2d496f")
                }

                Text {
                    text: card.title
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 15
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Rectangle {
                    Layout.preferredWidth: statusText.implicitWidth + 16
                    Layout.preferredHeight: 24
                    radius: 7
                    color: card.active ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(1, 1, 1, 0.04)
                    border.color: card.active ? card.accent : "#2d496f"
                    border.width: 1

                    Text {
                        id: statusText
                        anchors.centerIn: parent
                        text: !card.modeEnabled ? tr("clicker.mode_disabled") : (card.active ? "ATIVO" : "PRONTO")
                        color: !card.modeEnabled ? "#7f93ad" : (card.active ? card.accent : "#7f93ad")
                        font.family: "Segoe UI"
                        font.pixelSize: 10
                        font.bold: true
                    }
                }

                ToggleSwitch {
                    checked: card.modeEnabled
                    onClicked: card.modeToggled(checked)
                }
            }

            Text {
                text: card.detail
                color: "#99abc4"
                font.family: "Segoe UI"
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
                Layout.fillWidth: true
                Layout.preferredHeight: 34
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                HotkeyPicker {
                    Layout.preferredWidth: 82
                    enabled: card.modeEnabled
                    currentKey: card.hotkey
                    onKeySelected: function(key) { card.hotkeySelected(key) }
                }

                PrimaryButton {
                    text: card.buttonText
                    Layout.preferredWidth: 92
                    fill: card.active ? "#24324a" : card.accent
                    hoverFill: card.active ? "#31405f" : "#8ab4ff"
                    textFill: card.active ? "#edf6ff" : "#041014"
                    enabled: autoClickerController.available && card.modeEnabled
                    onClicked: card.action()
                }

                Item { Layout.fillWidth: true }
            }

            ColumnLayout {
                id: extraBox
                Layout.fillWidth: true
                spacing: 8
            }
        }
    }

    component SettingLine: RowLayout {
        property string label: ""
        property bool checked: false
        property bool showLine: true
        signal changed(bool value)

        visible: showLine
        Layout.fillWidth: true
        spacing: 10

        ToggleSwitch {
            checked: parent.checked
            onClicked: parent.changed(checked)
        }

        Text {
            text: parent.label
            color: "#c7d7ed"
            font.family: "Segoe UI"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    ColumnLayout {
        id: content
        width: Math.max(320, parent.width - 40)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 20
        spacing: 18

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Text {
                    text: tr("clicker.automation_overlay")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 25
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Text {
                    text: autoClickerController.overlayPrimaryText
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            Rectangle {
                Layout.preferredWidth: 92
                Layout.preferredHeight: 30
                radius: 8
                color: autoClickerController.active ? settingsController.accentPanelStrongColor : "#13233a"
                border.color: autoClickerController.active ? settingsController.accentColor : "#2d496f"

                Text {
                    anchors.centerIn: parent
                    text: autoClickerController.active ? tr("clicker.on_badge") : tr("clicker.paused_badge")
                    color: autoClickerController.active ? settingsController.accentColor : "#c7d7ed"
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                    font.bold: true
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: Qt.rgba(0.03, 0.06, 0.11, 0.88)
            border.color: autoClickerController.available ? "#1d3353" : "#743047"
            implicitHeight: statusRows.implicitHeight + 28
            layer.enabled: true
            layer.effect: DropShadow {
                transparentBorder: true
                color: Qt.rgba(0, 0, 0, 0.22)
                radius: 18
                samples: 37
                verticalOffset: 5
            }

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: autoClickerController.active ? settingsController.accentColor : "#8ab4ff"
                opacity: autoClickerController.active ? 0.07 : 0.035
            }

            ColumnLayout {
                id: statusRows
                anchors.fill: parent
                anchors.margins: 14
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3

                        Text {
                            text: autoClickerController.targetTitle
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 15
                            font.bold: true
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        Text {
                            text: autoClickerController.status
                            color: autoClickerController.available ? "#99abc4" : "#ff7a90"
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }

                    PrimaryButton {
                        text: autoClickerController.running ? tr("clicker.pause_all") : tr("clicker.resume")
                        Layout.preferredWidth: 120
                        enabled: autoClickerController.available
                        onClicked: autoClickerController.toggle()
                    }

                    PrimaryButton {
                        text: tr("clicker.capture")
                        Layout.preferredWidth: 154
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        enabled: autoClickerController.available
                        onClicked: autoClickerController.captureFoxhole()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        text: "Modo: " + autoClickerController.modeSummary
                        color: settingsController.accentColor
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        font.bold: true
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Text {
                        text: "Resposta " + autoClickerController.interval.toFixed(1) + "s"
                        color: "#8ab4ff"
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        font.bold: true
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width >= 1080 ? 3 : (root.width >= 720 ? 2 : 1)
            columnSpacing: 12
            rowSpacing: 12

            ModeCard {
                title: tr("clicker.auto_clicker_label").replace(":", "")
                detail: tr("clicker.button") + " " + tr(autoClickerController.mouseButtonLabel(autoClickerController.mouseButton)) + " | " + autoClickerController.interval.toFixed(1) + "s"
                hotkey: autoClickerController.hotkey
                active: autoClickerController.running
                modeEnabled: autoClickerController.autoModeEnabled
                accent: settingsController.accentColor
                buttonText: active ? tr("clicker.pause") : tr("clicker.resume")
                onAction: autoClickerController.toggle()
                onHotkeySelected: function(key) { autoClickerController.setHotkey(key) }
                onModeToggled: function(value) { autoClickerController.setModeEnabled("auto", value) }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    PrimaryComboBox {
                        id: mouseCombo
                        Layout.preferredWidth: 122
                        Layout.preferredHeight: 32
                        model: autoClickerController.mouseButtons
                        currentIndex: comboIndex(autoClickerController.mouseButtons, autoClickerController.mouseButton)
                        onActivated: autoClickerController.setMouseButton(currentText)
                        contentItem: Text {
                            text: tr(autoClickerController.mouseButtonLabel(mouseCombo.currentText))
                            color: "#edf6ff"
                            font.pixelSize: 12
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 10
                            elide: Text.ElideRight
                        }
                    }

                    SettingLine {
                        label: tr("clicker.hold_shift")
                        checked: autoClickerController.shiftEnabled
                        onChanged: function(value) { autoClickerController.setShiftEnabled(value) }
                    }
                }
            }

            ModeCard {
                title: tr("clicker.move_click_hold")
                detail: "Esc ou " + autoClickerController.moveHotkey + " solta"
                hotkey: autoClickerController.moveHotkey
                active: autoClickerController.moveRunning
                modeEnabled: autoClickerController.moveModeEnabled
                accent: "#8ab4ff"
                onAction: autoClickerController.toggleMoveClick()
                onHotkeySelected: function(key) { autoClickerController.setMoveHotkey(key) }
                onModeToggled: function(value) { autoClickerController.setModeEnabled("move", value) }
            }

            ModeCard {
                title: autoClickerController.wHoldLabel.replace(":", "")
                detail: trReplaceWZ("clicker.hold_w_hint") + " | S pausa"
                hotkey: autoClickerController.pilotHotkey
                active: autoClickerController.pilotRunning
                modeEnabled: autoClickerController.pilotModeEnabled
                accent: settingsController.accentColor
                onAction: autoClickerController.togglePilot()
                onHotkeySelected: function(key) { autoClickerController.setPilotHotkey(key) }
                onModeToggled: function(value) { autoClickerController.setModeEnabled("pilot", value) }

                SettingLine {
                    label: trReplaceWZ("clicker.w_double_tap_enable")
                    checked: autoClickerController.wDoubleTapEnabled
                    onChanged: function(value) { autoClickerController.setWDoubleTapEnabled(value) }
                }

                SettingLine {
                    showLine: autoClickerController.frWOverrideAvailable
                    label: tr("clicker.force_w_in_fr")
                    checked: autoClickerController.frWOverride
                    onChanged: function(value) { autoClickerController.setFrWOverride(value) }
                }
            }

            ModeCard {
                title: tr("clicker.right_hold_short")
                detail: tr("clicker.hold_right_hint")
                hotkey: autoClickerController.rightHoldHotkey
                active: autoClickerController.rightHoldRunning
                modeEnabled: autoClickerController.rightHoldModeEnabled
                accent: "#8ab4ff"
                onAction: autoClickerController.toggleRightHold()
                onHotkeySelected: function(key) { autoClickerController.setRightHoldHotkey(key) }
                onModeToggled: function(value) { autoClickerController.setModeEnabled("right_hold", value) }

                SettingLine {
                    label: tr("clicker.right_double_tap_enable")
                    checked: autoClickerController.rightDoubleTapEnabled
                    onChanged: function(value) { autoClickerController.setRightDoubleTapEnabled(value) }
                }
            }

            ModeCard {
                title: tr("clicker.key_fixed").replace("Tecla ", "").replace("Key ", "")
                detail: tr("clicker.shortcuts_slots").replace("{hotkey}", autoClickerController.fixedHotkey)
                hotkey: autoClickerController.fixedHotkey
                active: autoClickerController.fixedRunning
                modeEnabled: autoClickerController.fixedModeEnabled
                accent: "#f8c15d"
                onAction: autoClickerController.toggleFixedClick()
                onHotkeySelected: function(key) { autoClickerController.setFixedHotkey(key) }
                onModeToggled: function(value) { autoClickerController.setModeEnabled("fixed", value) }
            }

            ModeCard {
                title: tr("clicker.artillery_label").replace(":", "")
                detail: tr("clicker.artillery_hint")
                hotkey: autoClickerController.artilleryHotkey
                active: autoClickerController.artilleryRunning
                modeEnabled: autoClickerController.artilleryModeEnabled
                accent: "#ff7a90"
                onAction: autoClickerController.toggleArtillery()
                onHotkeySelected: function(key) { autoClickerController.setArtilleryHotkey(key) }
                onModeToggled: function(value) { autoClickerController.setModeEnabled("artillery", value) }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: Qt.rgba(0.03, 0.06, 0.11, 0.88)
            border.color: "#1d3353"
            implicitHeight: overlayColumn.implicitHeight + 28
            layer.enabled: true
            layer.effect: DropShadow {
                transparentBorder: true
                color: Qt.rgba(0, 0, 0, 0.18)
                radius: 14
                samples: 29
                verticalOffset: 4
            }

            ColumnLayout {
                id: overlayColumn
                anchors.fill: parent
                anchors.margins: 14
                spacing: 14

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text {
                        text: tr("overlay.in_game_title")
                        color: "#edf6ff"
                        font.family: "Segoe UI"
                        font.pixelSize: 16
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    SettingLine {
                        Layout.preferredWidth: 230
                        label: tr("overlay.show")
                        checked: overlayController.enabled
                        onChanged: function(value) { overlayController.setEnabled(value) }
                    }

                    PrimaryButton {
                        text: tr("overlay.preview_8s")
                        Layout.preferredWidth: 160
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: overlayController.preview()
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width >= 760 ? 4 : 2
                    columnSpacing: 16
                    rowSpacing: 10

                    SettingLine {
                        label: tr("overlay.clicker_title")
                        checked: overlayController.showClicker
                        onChanged: function(value) { overlayController.setShowClicker(value) }
                    }

                    SettingLine {
                        label: tr("overlay.profile")
                        checked: overlayController.showProfile
                        onChanged: function(value) { overlayController.setShowProfile(value) }
                    }

                    SettingLine {
                        label: tr("overlay.target")
                        checked: overlayController.showTarget
                        onChanged: function(value) { overlayController.setShowTarget(value) }
                    }

                    SettingLine {
                        label: tr("overlay.upload_notification")
                        checked: overlayController.notificationEnabled
                        onChanged: function(value) { overlayController.setNotificationEnabled(value) }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: overlayPreview.implicitHeight + 24
                    radius: 8
                    color: Qt.rgba(0, 0, 0, 0.16)
                    border.color: Qt.rgba(1, 1, 1, 0.08)

                    RowLayout {
                        id: overlayPreview
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12

                        Rectangle {
                            Layout.preferredWidth: 46
                            Layout.preferredHeight: 46
                            radius: 8
                            color: Qt.rgba(1, 1, 1, 0.07)
                            border.color: settingsController.accentColor

                            Text {
                                anchors.centerIn: parent
                                text: autoClickerController.active ? "ON" : "II"
                                color: autoClickerController.active ? settingsController.accentColor : settingsController.warningColor
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                font.bold: true
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3

                            Text {
                                text: autoClickerController.overlayPrimaryText
                                color: "#edf6ff"
                                font.family: "Segoe UI"
                                font.pixelSize: 13
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Text {
                                text: autoClickerController.overlayHintText !== "" ? autoClickerController.overlayHintText : tr("overlay.compact_hint")
                                color: "#99abc4"
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text {
                        text: tr("overlay.color_label")
                        color: "#99abc4"
                        font.pixelSize: 12
                        font.bold: true
                    }

                    PrimaryComboBox {
                        id: colorCombo
                        Layout.preferredWidth: 130
                        Layout.preferredHeight: 32
                        model: overlayController.colors
                        currentIndex: comboIndex(overlayController.colors, overlayController.colorName)
                        onActivated: overlayController.setColorName(currentText)
                        contentItem: Text {
                            text: tr(overlayController.colorLabelKey(colorCombo.currentText))
                            color: "#edf6ff"
                            font.pixelSize: 12
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 10
                            elide: Text.ElideRight
                        }
                    }

                    Item { Layout.fillWidth: true }

                    Text {
                        text: tr("overlay.hide_hotkey")
                        color: "#99abc4"
                        font.pixelSize: 12
                        font.bold: true
                    }

                    HotkeyPicker {
                        Layout.preferredWidth: 82
                        currentKey: overlayController.hotkey
                        onKeySelected: function(key) { overlayController.setHotkey(key) }
                    }
                }
            }
        }
    }
}


