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
            color: settingsController.textColor
            font.family: "Segoe UI"
            font.pixelSize: 26
            font.bold: true
            Layout.fillWidth: true
            elide: Text.ElideRight
        }

        Text {
            text: tr("settings.subtitle")
            color: settingsController.mutedTextColor
            font.family: "Segoe UI"
            font.pixelSize: 13
            font.bold: true
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }

        Rectangle {
            Layout.fillWidth: true
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor
            implicitHeight: languageColumn.implicitHeight + 32

            ColumnLayout {
                id: languageColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 12

                Text {
                    text: tr("settings.language_title")
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 18
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
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
                            radius: settingsController.cardRadius
                            color: active ? settingsController.accentPanelColor : settingsController.backgroundColor
                            border.color: active ? settingsController.accentColor : settingsController.borderColor
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
                                color: settingsController.textColor
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
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: settingsController.accentColor
            implicitHeight: personalizationColumn.implicitHeight + 32

            RowLayout {
                id: personalizationColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 14

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text {
                        text: tr("settings.personalization_shortcut_title")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Text {
                        text: tr("settings.personalization_shortcut_body")
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                }

                PrimaryButton {
                    Layout.preferredWidth: 190
                    text: tr("settings.open_personalization")
                    onClicked: appController.setCurrentPage("personalization")
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor
            implicitHeight: debugColumn.implicitHeight + 24

            ColumnLayout {
                id: debugColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 12
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: "Debug"
                            color: settingsController.secondaryTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            Layout.fillWidth: true
                        }
                        Text {
                            text: "Atalho global: " + debugController.hotkeyLabel + ". Registra API, WebSocket, chat, stockpile, updater e eventos principais do app."
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }
                    ToggleSwitch {
                        checked: debugController.enabled
                        onClicked: debugController.setEnabled(checked)
                    }
                }

                Text {
                    text: debugController.logPath !== "" ? ("Log atual: " + debugController.logPath) : "Log atual: nenhum arquivo criado ainda"
                    color: settingsController.secondaryTextColor
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    elide: Text.ElideMiddle
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    PrimaryButton {
                        Layout.preferredWidth: 112
                        implicitHeight: 32
                        text: debugController.enabled ? "Desligar" : "Ligar"
                        fill: settingsController.controlColor
                        hoverFill: settingsController.controlHoverColor
                        textFill: settingsController.textColor
                        font.pixelSize: 11
                        onClicked: debugController.toggleDebug()
                    }
                    PrimaryButton {
                        Layout.preferredWidth: 112
                        implicitHeight: 32
                        text: "Abrir logs"
                        fill: settingsController.controlColor
                        hoverFill: settingsController.controlHoverColor
                        textFill: settingsController.textColor
                        font.pixelSize: 11
                        onClicked: debugController.openLogFolder()
                    }
                    PrimaryButton {
                        Layout.preferredWidth: 128
                        implicitHeight: 32
                        text: "Marcar evento"
                        fill: settingsController.controlColor
                        hoverFill: settingsController.controlHoverColor
                        textFill: settingsController.textColor
                        font.pixelSize: 11
                        onClicked: debugController.writeMarker("settings")
                    }
                    Text {
                        text: debugController.status
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 10
                        Layout.fillWidth: true
                        elide: Text.ElideMiddle
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor
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
                    color: settingsController.textColor
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
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 13
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    PrimaryComboBox {
                        id: closeActionCombo
                        Layout.preferredWidth: 190
                        Layout.preferredHeight: 42
                        model: [tr("settings.close_ask"), tr("settings.close_tray"), tr("settings.close_exit")]
                        currentIndex: root.closeActionIndex()
                        onActivated: settingsController.setCloseAction(root.closeActionKeys[index])
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
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: tr("settings.startup_command") + ": " + settingsController.startupCommand
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            elide: Text.ElideMiddle
                        }
                        Text {
                            text: settingsController.status
                            visible: settingsController.status !== ""
                            color: settingsController.warningColor
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }
                    ToggleSwitch {
                        checked: settingsController.startWithWindows
                        onClicked: settingsController.setStartWithWindows(checked)
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor
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
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 18
                    font.bold: true
                    Layout.fillWidth: true
                }
                Text {
                    text: tr("settings.sound_body")
                    color: settingsController.mutedTextColor
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
                        radius: settingsController.cardRadius
                        color: settingsController.backgroundColor
                        border.color: settingsController.borderColor

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 10
                            ToggleSwitch {
                                checked: root.notificationChecked(modelData.key)
                                onClicked: settingsController.setNotificationEnabled(modelData.key, checked)
                            }
                            Text {
                                text: tr(modelData.labelKey)
                                color: settingsController.textColor
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
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor
            implicitHeight: 280

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10
                Text {
                    text: tr("settings.runtime_title")
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 18
                    font.bold: true
                    Layout.fillWidth: true
                }
                Text {
                    text: tr("settings.settings_file") + ": " + settingsController.settingsPath()
                    color: settingsController.mutedTextColor
                    font.family: "Segoe UI"
                    Layout.fillWidth: true
                    elide: Text.ElideMiddle
                }
                RowLayout {
                    PrimaryButton { text: tr("settings.check_updates"); onClicked: updateController.check() }
                    Text {
                        text: updateController.status
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }
                TextArea {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    text: root.settingsJsonText()
                    readOnly: true
                    color: settingsController.textColor
                    font.family: "Consolas"
                    font.pixelSize: 11
                    wrapMode: TextArea.NoWrap
                    background: Rectangle {
                        radius: settingsController.cardRadius
                        color: settingsController.backgroundColor
                        border.color: settingsController.borderColor
                    }
                }
            }
        }
    }
}
