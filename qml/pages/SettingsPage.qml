import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: content.implicitHeight + 36

    property var closeActionKeys: ["ask", "tray", "exit"]

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    function closeActionIndex() {
        var index = closeActionKeys.indexOf(settingsController.closeAction)
        return index >= 0 ? index : 0
    }

    function settingsJsonText() {
        settingsController.revision
        return settingsController.settingsJson()
    }

    function notificationChecked(key) {
        settingsController.revision
        if (key === "stockpile_sound_enabled")
            return settingsController.stockpileSoundEnabled
        if (key === "squadlock_overlay_enabled")
            return settingsController.squadlockOverlayEnabled
        if (key === "squadlock_sound_enabled")
            return settingsController.squadlockSoundEnabled
        if (key === "chat_mention_overlay_enabled")
            return settingsController.chatMentionOverlayEnabled
        if (key === "chat_mention_sound_enabled")
            return settingsController.chatMentionSoundEnabled
        return false
    }

    Component.onCompleted: settingsController.notifyExternalChange()

    ColumnLayout {
        id: content
        width: root.width
        spacing: 16

        Text {
            text: tr("settings.title")
            color: "#edf6ff"
            font.family: "Segoe UI"
            font.pixelSize: 26
            font.bold: true
            Layout.fillWidth: true
        }

        Text {
            text: tr("settings.subtitle")
            color: "#8ab4ff"
            font.family: "Segoe UI"
            font.pixelSize: 13
            font.bold: true
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
            implicitHeight: 170

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12
                Text {
                    text: tr("settings.language_title")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 17
                    font.bold: true
                    Layout.fillWidth: true
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 72
                    orientation: ListView.Horizontal
                    spacing: 10
                    model: languagesModel
                    delegate: Button {
                        width: 150
                        height: 52
                        text: name
                        onClicked: i18nController.setLanguage(code)
                        background: Rectangle {
                            radius: 8
                            color: active ? "#1d3353" : "#0e1a2d"
                            border.color: active ? "#5eead4" : "#2d496f"
                            Behavior on color { ColorAnimation { duration: 140 } }
                        }
                        contentItem: RowLayout {
                            spacing: 8
                            Item { Layout.fillWidth: true }
                            Image {
                                source: flag
                                Layout.preferredWidth: 24
                                Layout.preferredHeight: 16
                                fillMode: Image.PreserveAspectFit
                            }
                            Text {
                                text: name
                                color: "#edf6ff"
                                font.family: "Segoe UI"
                                font.bold: true
                                elide: Text.ElideRight
                            }
                            Item { Layout.fillWidth: true }
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
            implicitHeight: appSettingsColumn.implicitHeight + 32

            ColumnLayout {
                id: appSettingsColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 12

                Text {
                    text: tr("settings.app_title")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 18
                    font.bold: true
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14
                    Text {
                        text: tr("settings.close_action")
                        color: "#c7d7ed"
                        font.family: "Segoe UI"
                        font.pixelSize: 13
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    ComboBox {
                        id: closeActionCombo
                        Layout.preferredWidth: 190
                        implicitHeight: 38
                        model: [tr("settings.close_ask"), tr("settings.close_tray"), tr("settings.close_exit")]
                        currentIndex: root.closeActionIndex()
                        onActivated: settingsController.setCloseAction(root.closeActionKeys[index])
                        delegate: ItemDelegate {
                            width: closeActionCombo.width
                            height: 38
                            highlighted: closeActionCombo.highlightedIndex === index
                            contentItem: Text {
                                text: modelData
                                color: parent.highlighted ? "#5eead4" : "#edf6ff"
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                font.bold: parent.highlighted
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }
                            background: Rectangle {
                                color: parent.highlighted ? "#173c35" : "#0e1a2d"
                                border.color: parent.highlighted ? "#5eead4" : "transparent"
                            }
                        }
                        indicator: Text {
                            x: closeActionCombo.width - width - 12
                            y: closeActionCombo.topPadding + (closeActionCombo.availableHeight - height) / 2
                            text: closeActionCombo.popup.visible ? "â–²" : "â–¼"
                            color: closeActionCombo.enabled ? "#8ab4ff" : "#52657f"
                            font.family: "Segoe UI"
                            font.pixelSize: 10
                        }
                        background: Rectangle {
                            radius: 7
                            color: closeActionCombo.down ? "#13213a" : "#0e1a2d"
                            border.color: closeActionCombo.activeFocus || closeActionCombo.popup.visible ? "#5eead4" : "#2d496f"
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Behavior on border.color { ColorAnimation { duration: 120 } }
                        }
                        contentItem: Text {
                            text: closeActionCombo.displayText
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            font.bold: true
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 12
                            rightPadding: 30
                            elide: Text.ElideRight
                        }
                        popup: Popup {
                            y: closeActionCombo.height + 6
                            width: closeActionCombo.width
                            implicitHeight: contentItem.implicitHeight + 2
                            padding: 1
                            background: Rectangle {
                                radius: 7
                                color: "#0b1424"
                                border.color: "#2d496f"
                            }
                            contentItem: ListView {
                                clip: true
                                implicitHeight: contentHeight
                                model: closeActionCombo.popup.visible ? closeActionCombo.delegateModel : null
                                currentIndex: closeActionCombo.highlightedIndex
                            }
                        }
                    }
                    Connections {
                        target: settingsController
                        function onChanged() {
                            closeActionCombo.currentIndex = root.closeActionIndex()
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3
                        Text {
                            text: tr("settings.start_windows")
                            color: "#c7d7ed"
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: tr("settings.startup_command") + ": " + settingsController.startupCommand
                            color: "#7f93ad"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            elide: Text.ElideMiddle
                        }
                        Text {
                            text: settingsController.status
                            visible: settingsController.status !== ""
                            color: "#ff7a90"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }
                    ToggleSwitch {
                        id: startupSwitch
                        checked: settingsController.startWithWindows
                        onClicked: settingsController.setStartWithWindows(checked)
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
            implicitHeight: soundColumn.implicitHeight + 32

            ColumnLayout {
                id: soundColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 10

                Text {
                    text: tr("settings.sound_title")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 18
                    font.bold: true
                    Layout.fillWidth: true
                }
                Text {
                    text: tr("settings.sound_body")
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: [
                        { "key": "stockpile_sound_enabled", "labelKey": "settings.sound_stockpile" },
                        { "key": "squadlock_overlay_enabled", "labelKey": "notifications.show_overlay" },
                        { "key": "squadlock_sound_enabled", "labelKey": "settings.sound_squadlock" },
                        { "key": "chat_mention_overlay_enabled", "labelKey": "settings.chat_mention_overlay" },
                        { "key": "chat_mention_sound_enabled", "labelKey": "settings.chat_mention_sound" }
                    ]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 48
                        radius: 7
                        color: "#0e1a2d"
                        border.color: "#1e3554"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 10
                            ToggleSwitch {
                                id: optionSwitch
                                checked: root.notificationChecked(modelData.key)
                                onClicked: settingsController.setNotificationEnabled(modelData.key, checked)
                            }
                            Text {
                                text: tr(modelData.labelKey)
                                color: "#edf6ff"
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
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
            implicitHeight: 280
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10
                Text {
                    text: tr("settings.runtime_title")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 17
                    font.bold: true
                    Layout.fillWidth: true
                }
                Text {
                    text: tr("settings.settings_file") + ": " + settingsController.settingsPath()
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    Layout.fillWidth: true
                    elide: Text.ElideMiddle
                }
                RowLayout {
                    PrimaryButton { text: tr("settings.check_updates"); onClicked: updateController.check() }
                    Text { text: updateController.status; color: "#99abc4"; font.family: "Segoe UI"; Layout.fillWidth: true; elide: Text.ElideRight }
                }
                TextArea {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    text: root.settingsJsonText()
                    readOnly: true
                    color: "#edf6ff"
                    font.family: "Consolas"
                    font.pixelSize: 11
                    wrapMode: TextArea.NoWrap
                    background: Rectangle { radius: 7; color: "#07111f"; border.color: "#24486d" }
                }
            }
        }
    }
}
