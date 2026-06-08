import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
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

    function comboIndex(model, value) {
        var index = model.indexOf(value)
        return index >= 0 ? index : 0
    }

    ColumnLayout {
        id: content
        width: parent.width - 40
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 20
        spacing: 16

        Text {
            text: tr("clicker.automation_overlay")
            color: "#edf6ff"
            font.family: "Segoe UI"
            font.pixelSize: 26
            font.bold: true
            Layout.fillWidth: true
        }

        // Status Card
        Rectangle {
            Layout.fillWidth: true
            radius: 12
            color: "#0a1321"
            border.color: autoClickerController.active ? "#5eead4" : "#1d3353"
            implicitHeight: statusContent.implicitHeight + 32
            Behavior on border.color { ColorAnimation { duration: 160 } }

            ColumnLayout {
                id: statusContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 16

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

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
                        font.pixelSize: 13
                        font.bold: true
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    PrimaryButton {
                        text: autoClickerController.running ? tr("clicker.pause_all") : tr("clicker.resume")
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
                }
            }
        }

        // Clicker Principal e Artilharia
        Rectangle {
            Layout.fillWidth: true
            radius: 12
            color: "#0a1321"
            border.color: "#1d3353"
            implicitHeight: mainClicker.implicitHeight + 32

            ColumnLayout {
                id: mainClicker
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16

                Text { text: tr("clicker.main_controls"); color: "#edf6ff"; font.family: "Segoe UI"; font.pixelSize: 16; font.bold: true }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: "#1d3353" }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text { text: tr("clicker.auto_clicker_label"); color: "#99abc4"; font.bold: true; font.pixelSize: 13; Layout.preferredWidth: 100 }
                    
                    HotkeyPicker {
                        Layout.preferredWidth: 80
                        currentKey: autoClickerController.hotkey
                        onKeySelected: function(key) { autoClickerController.setHotkey(key) }
                    }

                    PrimaryComboBox {
                        id: mouseCombo
                        Layout.preferredWidth: 110
                        Layout.preferredHeight: 32
                        model: autoClickerController.mouseButtons
                        currentIndex: comboIndex(autoClickerController.mouseButtons, autoClickerController.mouseButton)
                        onActivated: autoClickerController.setMouseButton(currentText)
                        contentItem: Text { text: tr(autoClickerController.mouseButtonLabel(mouseCombo.currentText)); color: "#edf6ff"; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter; leftPadding: 10; elide: Text.ElideRight }
                    }

                    Text { text: "(0.3s)"; color: "#5eead4"; font.pixelSize: 12; Layout.leftMargin: 4; font.bold: true }
                    Item { Layout.fillWidth: true }
                    
                    ToggleSwitch {
                        id: shiftSwitch
                        checked: autoClickerController.shiftEnabled
                        onClicked: autoClickerController.setShiftEnabled(checked)
                    }
                    Text { text: tr("clicker.hold_shift"); color: "#c7d7ed"; font.pixelSize: 12 }
                }

                // W Hold section
                Rectangle {
                    Layout.fillWidth: true
                    radius: 6
                    color: "#0e1a2d"
                    border.color: "#1e3554"
                    implicitHeight: wHoldRow.implicitHeight + 16

                    ColumnLayout {
                        id: wHoldRow
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Text { text: tr("clicker.w_hold_label"); color: "#edf6ff"; font.bold: true; font.pixelSize: 13; Layout.preferredWidth: 100 }
                            
                            HotkeyPicker {
                                Layout.preferredWidth: 80
                                currentKey: autoClickerController.pilotHotkey
                                onKeySelected: function(key) { autoClickerController.setPilotHotkey(key) }
                            }
                            
                            Text { text: tr("clicker.hold_w_hint"); color: "#99abc4"; font.pixelSize: 12 }
                            Item { Layout.fillWidth: true }
                            
                            ToggleSwitch {
                                checked: autoClickerController.wDoubleTapEnabled
                                onClicked: autoClickerController.setWDoubleTapEnabled(checked)
                            }
                            Text { text: tr("clicker.w_double_tap_enable"); color: "#c7d7ed"; font.pixelSize: 12 }
                        }
                        
                        Text {
                            text: tr("clicker.w_hold_help")
                            color: "#5d7a99"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                        }
                    }
                }


                // Right Hold section
                Rectangle {
                    Layout.fillWidth: true
                    radius: 6
                    color: "#0e1a2d"
                    border.color: "#1e3554"
                    implicitHeight: rightHoldRow.implicitHeight + 16

                    ColumnLayout {
                        id: rightHoldRow
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Text { text: tr("clicker.right_hold_label"); color: "#edf6ff"; font.bold: true; font.pixelSize: 13; Layout.preferredWidth: 100 }

                            HotkeyPicker {
                                Layout.preferredWidth: 80
                                currentKey: autoClickerController.rightHoldHotkey
                                onKeySelected: function(key) { autoClickerController.setRightHoldHotkey(key) }
                            }

                            Text { text: tr("clicker.hold_right_hint"); color: "#99abc4"; font.pixelSize: 12 }
                            Item { Layout.fillWidth: true }

                            ToggleSwitch {
                                checked: autoClickerController.rightDoubleTapEnabled
                                onClicked: autoClickerController.setRightDoubleTapEnabled(checked)
                            }
                            Text { text: tr("clicker.right_double_tap_enable"); color: "#c7d7ed"; font.pixelSize: 12 }
                        }

                        Text {
                            text: tr("clicker.right_hold_help")
                            color: "#5d7a99"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: "#1d3353"; opacity: 0.5 }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text { text: tr("clicker.artillery_label"); color: "#5eead4"; font.bold: true; font.pixelSize: 13; Layout.preferredWidth: 100 }
                    
                    HotkeyPicker {
                        Layout.preferredWidth: 80
                        currentKey: autoClickerController.artilleryHotkey
                        onKeySelected: function(key) { autoClickerController.setArtilleryHotkey(key) }
                    }
                    
                    Text { 
                        text: tr("clicker.artillery_hint")
                        color: "#99abc4"
                        font.pixelSize: 12
                        Layout.fillWidth: true 
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        // Modos Secundários
        Rectangle {
            Layout.fillWidth: true
            radius: 12
            color: "#0a1321"
            border.color: "#1d3353"
            implicitHeight: extraModes.implicitHeight + 32

            ColumnLayout {
                id: extraModes
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16

                Text { text: tr("clicker.extra_modes"); color: "#edf6ff"; font.family: "Segoe UI"; font.pixelSize: 16; font.bold: true }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: "#1d3353" }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    ColumnLayout {
                        spacing: 4
                        Text { text: tr("clicker.move_click_hold"); color: "#99abc4"; font.pixelSize: 12 }
                        HotkeyPicker {
                            currentKey: autoClickerController.moveHotkey
                            onKeySelected: function(key) { autoClickerController.setMoveHotkey(key) }
                        }
                    }

                    ColumnLayout {
                        spacing: 4
                        Text { text: tr("clicker.right_hold_short"); color: "#99abc4"; font.pixelSize: 12 }
                        HotkeyPicker {
                            currentKey: autoClickerController.rightHoldHotkey
                            onKeySelected: function(key) { autoClickerController.setRightHoldHotkey(key) }
                        }
                    }
                    
                    Item { Layout.fillWidth: true }
                }
            }
        }

        // Overlay Minimalista
        Rectangle {
            Layout.fillWidth: true
            radius: 12
            color: "#0a1321"
            border.color: "#1d3353"
            implicitHeight: overlayColumn.implicitHeight + 32

            ColumnLayout {
                id: overlayColumn
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16

                Text { text: tr("overlay.in_game_title"); color: "#edf6ff"; font.family: "Segoe UI"; font.pixelSize: 16; font.bold: true }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: "#1d3353" }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    ToggleSwitch {
                        checked: overlayController.enabled
                        onClicked: overlayController.setEnabled(checked)
                    }
                    Text { text: tr("overlay.enable_floating_panel"); color: "#edf6ff"; font.pixelSize: 13; Layout.fillWidth: true }

                    PrimaryButton {
                        text: tr("overlay.preview_8s")
                        Layout.preferredWidth: 160
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: overlayController.preview()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    radius: 8
                    color: "#0e1a2d"
                    border.color: "#1e3554"
                    implicitHeight: overlayContentOptions.implicitHeight + 18

                    ColumnLayout {
                        id: overlayContentOptions
                        anchors.fill: parent
                        anchors.margins: 9
                        spacing: 10

                        Text {
                            text: tr("overlay.panel_content")
                            color: "#8ab4ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            font.bold: true
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 22
                            rowSpacing: 10

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                ToggleSwitch {
                                    checked: overlayController.showClicker
                                    onClicked: overlayController.setShowClicker(checked)
                                }
                                Text { text: tr("overlay.clicker_title"); color: "#c7d7ed"; font.pixelSize: 12; Layout.fillWidth: true }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                ToggleSwitch {
                                    checked: overlayController.showProfile
                                    onClicked: overlayController.setShowProfile(checked)
                                }
                                Text { text: tr("overlay.profile"); color: "#c7d7ed"; font.pixelSize: 12; Layout.fillWidth: true }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                ToggleSwitch {
                                    checked: overlayController.showTarget
                                    onClicked: overlayController.setShowTarget(checked)
                                }
                                Text { text: tr("overlay.target"); color: "#c7d7ed"; font.pixelSize: 12; Layout.fillWidth: true }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                ToggleSwitch {
                                    checked: overlayController.notificationEnabled
                                    onClicked: overlayController.setNotificationEnabled(checked)
                                }
                                Text { text: tr("overlay.upload_notification"); color: "#c7d7ed"; font.pixelSize: 12; Layout.fillWidth: true }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text { text: tr("overlay.color_label"); color: "#99abc4"; font.pixelSize: 12; font.bold: true }
                    PrimaryComboBox {
                        id: colorCombo
                        Layout.preferredWidth: 120
                        Layout.preferredHeight: 32
                        model: overlayController.colors
                        currentIndex: comboIndex(overlayController.colors, overlayController.colorName)
                        onActivated: overlayController.setColorName(currentText)
                        contentItem: Text { text: tr(overlayController.colorLabelKey(colorCombo.currentText)); color: "#edf6ff"; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter; leftPadding: 10 }
                    }

                    Item { Layout.fillWidth: true }

                    Text { text: tr("overlay.hide_hotkey"); color: "#99abc4"; font.pixelSize: 12; font.bold: true }
                    HotkeyPicker {
                        Layout.preferredWidth: 80
                        currentKey: overlayController.hotkey
                        onKeySelected: function(key) { overlayController.setHotkey(key) }
                    }
                }

                Text {
                    text: tr("overlay.compact_hint")
                    color: "#5d7a99"
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
