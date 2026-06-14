import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: content.implicitHeight + 36

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    function customThemeColor(key) {
        settingsController.revision
        return settingsController.customThemeColor(key)
    }

    Component.onCompleted: settingsController.notifyExternalChange()

    ColumnLayout {
        id: content
        width: root.width
        spacing: 16

        Text {
            text: tr("settings.theme_title")
            color: settingsController.textColor
            font.family: "Segoe UI"
            font.pixelSize: 26
            font.bold: true
            Layout.fillWidth: true
            elide: Text.ElideRight
        }

        Text {
            text: tr("settings.theme_body")
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
            implicitHeight: presetsColumn.implicitHeight + 32

            ColumnLayout {
                id: presetsColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 12

                Text {
                    text: tr("settings.theme_presets_title")
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 18
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 980 ? 3 : root.width > 640 ? 2 : 1
                    columnSpacing: 10
                    rowSpacing: 10

                    Repeater {
                        model: settingsController.themePresets
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 88
                            radius: settingsController.cardRadius
                            color: modelData.active ? modelData.accentPanel : settingsController.backgroundColor
                            border.color: modelData.active ? modelData.accent : settingsController.borderColor
                            border.width: modelData.active ? 1.5 : 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 12

                                Column {
                                    Layout.preferredWidth: 36
                                    spacing: 4
                                    Repeater {
                                        model: [modelData.background, modelData.accent, modelData.success, modelData.warning]
                                        Rectangle {
                                            width: 32
                                            height: 12
                                            radius: 4
                                            color: modelData
                                            border.color: settingsController.borderColor
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Text {
                                        text: tr(modelData.labelKey)
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        text: tr(modelData.descriptionKey)
                                        color: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        Layout.fillWidth: true
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2
                                        elide: Text.ElideRight
                                    }
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: settingsController.setThemePreset(modelData.key)
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
            border.color: settingsController.accentColor
            implicitHeight: customColumn.implicitHeight + 32

            ColumnLayout {
                id: customColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 14

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3
                        Text {
                            text: tr("settings.theme_custom_editor")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: tr("settings.theme_custom_hint")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }

                    PrimaryButton {
                        Layout.preferredWidth: 120
                        Layout.preferredHeight: 38
                        text: tr("settings.theme_reset")
                        fill: settingsController.accentPanelColor
                        textFill: settingsController.textColor
                        onClicked: settingsController.resetCustomTheme()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3
                        Text {
                            text: tr("settings.theme_gradient")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: tr("settings.theme_gradient_detail")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }
                    ToggleSwitch {
                        checked: settingsController.gradientEnabled
                        onClicked: settingsController.setThemeGradientEnabled(checked)
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 900 ? 2 : 1
                    columnSpacing: 12
                    rowSpacing: 12

                    Rectangle {
                        Layout.fillWidth: true
                        radius: settingsController.cardRadius
                        color: settingsController.backgroundColor
                        border.color: settingsController.borderColor
                        implicitHeight: buttonStyleColumn.implicitHeight + 24

                        ColumnLayout {
                            id: buttonStyleColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 12
                            spacing: 10

                            Text {
                                text: tr("settings.button_style_title")
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 13
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                columnSpacing: 8
                                rowSpacing: 8

                                Repeater {
                                    model: settingsController.buttonStyleOptions
                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 38
                                        radius: settingsController.buttonStyle === modelData.key ? settingsController.buttonRadius : 7
                                        color: settingsController.buttonStyle === modelData.key ? settingsController.accentPanelColor : settingsController.surfaceColor
                                        border.color: settingsController.buttonStyle === modelData.key ? settingsController.accentColor : settingsController.borderColor
                                        border.width: 1

                                        Text {
                                            anchors.centerIn: parent
                                            width: parent.width - 16
                                            text: tr(modelData.labelKey)
                                            color: settingsController.buttonStyle === modelData.key ? settingsController.textColor : settingsController.mutedTextColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 12
                                            font.bold: settingsController.buttonStyle === modelData.key
                                            horizontalAlignment: Text.AlignHCenter
                                            elide: Text.ElideRight
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: settingsController.setThemeButtonStyle(modelData.key)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        radius: settingsController.cardRadius
                        color: settingsController.backgroundColor
                        border.color: settingsController.borderColor
                        implicitHeight: radiusColumn.implicitHeight + 24

                        ColumnLayout {
                            id: radiusColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 12
                            spacing: 10

                            Text {
                                text: tr("settings.card_radius_title")
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 13
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 3
                                columnSpacing: 8
                                rowSpacing: 8

                                Repeater {
                                    model: settingsController.cardRadiusOptions
                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 38
                                        radius: Number(modelData.key)
                                        color: settingsController.cardRadius === Number(modelData.key) ? settingsController.accentPanelColor : settingsController.surfaceColor
                                        border.color: settingsController.cardRadius === Number(modelData.key) ? settingsController.accentColor : settingsController.borderColor
                                        border.width: 1

                                        Text {
                                            anchors.centerIn: parent
                                            width: parent.width - 16
                                            text: tr(modelData.labelKey)
                                            color: settingsController.cardRadius === Number(modelData.key) ? settingsController.textColor : settingsController.mutedTextColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 12
                                            font.bold: settingsController.cardRadius === Number(modelData.key)
                                            horizontalAlignment: Text.AlignHCenter
                                            elide: Text.ElideRight
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: settingsController.setThemeCardRadius(modelData.key)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 900 ? 4 : root.width > 620 ? 2 : 1
                    columnSpacing: 10
                    rowSpacing: 10

                    Repeater {
                        model: settingsController.themeColorFields
                        delegate: ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Text {
                                text: tr(modelData.labelKey)
                                color: settingsController.mutedTextColor
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Rectangle {
                                    Layout.preferredWidth: 34
                                    Layout.preferredHeight: 34
                                    radius: 7
                                    color: root.customThemeColor(modelData.key)
                                    border.color: settingsController.borderColor
                                }
                                TextField {
                                    id: colorInput
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 38
                                    text: root.customThemeColor(modelData.key)
                                    selectByMouse: true
                                    color: settingsController.textColor
                                    selectedTextColor: settingsController.backgroundColor
                                    selectionColor: settingsController.accentColor
                                    font.family: "Consolas"
                                    font.pixelSize: 12
                                    validator: RegularExpressionValidator { regularExpression: /^#?[0-9a-fA-F]{0,6}$/ }
                                    onAccepted: settingsController.setCustomThemeColor(modelData.key, text)
                                    onEditingFinished: settingsController.setCustomThemeColor(modelData.key, text)
                                    background: Rectangle {
                                        radius: settingsController.cardRadius
                                        color: colorInput.hovered || colorInput.activeFocus ? settingsController.accentPanelColor : settingsController.backgroundColor
                                        border.color: colorInput.activeFocus ? settingsController.accentColor : settingsController.borderColor
                                        border.width: colorInput.activeFocus ? 1.5 : 1
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
