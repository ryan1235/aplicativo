import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: content.height
    boundsBehavior: Flickable.StopAtBounds
    interactive: contentHeight > height + 1
    property int scrollBarContentPadding: 14
    property string activeSection: "themes"

    ScrollBar.vertical: ScrollBar {
        policy: root.contentHeight > root.height + 1 ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
        active: root.moving || root.flicking
    }

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
        width: Math.max(0, root.width - root.scrollBarContentPadding)
        height: Math.max(root.height, implicitHeight + 36)
        spacing: 14

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 184
            radius: settingsController.cardRadius
            color: settingsController.backgroundColor
            border.color: settingsController.borderColor
            clip: true
            gradient: Gradient {
                GradientStop { position: 0.0; color: settingsController.gradientEnabled ? settingsController.gradientStartColor : settingsController.backgroundColor }
                GradientStop { position: 1.0; color: settingsController.gradientEnabled ? settingsController.gradientEndColor : settingsController.surfaceColor }
            }

            RowLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 8

                    Text {
                        text: tr("settings.theme_title")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 28
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
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        PrimaryButton {
                            Layout.preferredWidth: 142
                            Layout.preferredHeight: 38
                            text: tr("settings.theme_random")
                            fill: settingsController.accentColor
                            hoverFill: settingsController.accentHoverColor
                            textFill: settingsController.textInverseColor
                            onClicked: settingsController.randomizeCustomTheme()
                        }

                        PrimaryButton {
                            Layout.preferredWidth: 104
                            Layout.preferredHeight: 38
                            text: tr("settings.theme_reset")
                            fill: settingsController.controlColor
                            hoverFill: settingsController.controlHoverColor
                            textFill: settingsController.textColor
                            onClicked: settingsController.resetCustomTheme()
                        }
                    }

                    Text {
                        text: tr("settings.personalization_storage") + ": " + settingsController.personalizationPath()
                        color: settingsController.disabledTextColor
                        font.family: "Consolas"
                        font.pixelSize: 10
                        Layout.fillWidth: true
                        elide: Text.ElideMiddle
                    }
                }

                Rectangle {
                    Layout.preferredWidth: root.width > 900 ? 360 : 270
                    Layout.fillHeight: true
                    radius: settingsController.cardRadius
                    color: settingsController.surfaceColor
                    border.color: settingsController.accentColor

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Rectangle {
                                Layout.preferredWidth: 42
                                Layout.preferredHeight: 42
                                radius: settingsController.buttonRadius
                                color: settingsController.accentColor
                                border.color: settingsController.accentHoverColor
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Text {
                                    text: tr("settings.theme_preview_title")
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 13
                                    font.bold: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: settingsController.colorblindModeEnabled ? settingsController.colorblindProfile : settingsController.themePreset
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 48
                            radius: settingsController.cardRadius
                            color: settingsController.backgroundColor
                            border.color: settingsController.borderColor

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 8
                                Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; radius: settingsController.cardRadius; color: settingsController.surfaceRaisedColor; border.color: settingsController.borderColor }
                                Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; radius: settingsController.cardRadius; color: settingsController.accentPanelColor; border.color: settingsController.accentColor }
                                Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; radius: settingsController.buttonRadius; color: settingsController.accentColor }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 10; radius: 5; color: settingsController.successColor }
                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 10; radius: 5; color: settingsController.warningColor }
                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 10; radius: 5; color: settingsController.dangerColor }
                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 10; radius: 5; color: settingsController.infoColor }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 54
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8

                Repeater {
                    model: [
                        { "key": "themes", "label": tr("settings.theme_presets_title") },
                        { "key": "access", "label": tr("settings.colorblind_mode") },
                        { "key": "shape", "label": tr("settings.theme_shape_title") },
                        { "key": "colors", "label": tr("settings.theme_color_editor_title") }
                    ]
                    delegate: Rectangle {
                        property bool selected: root.activeSection === modelData.key
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        radius: settingsController.buttonRadius
                        color: selected ? settingsController.accentPanelColor : (tabMouse.containsMouse ? settingsController.controlColor : settingsController.backgroundColor)
                        border.color: selected ? settingsController.accentColor : settingsController.borderColor
                        border.width: selected ? 1.5 : 1

                        Text {
                            anchors.centerIn: parent
                            width: parent.width - 14
                            text: modelData.label
                            color: selected ? settingsController.textColor : settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            font.bold: selected
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                        }

                        MouseArea {
                            id: tabMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.activeSection = modelData.key
                        }
                    }
                }
            }
        }

        GridLayout {
            visible: root.activeSection === "themes"
            Layout.fillWidth: true
            columns: root.width > 1060 ? 2 : 1
            columnSpacing: 14
            rowSpacing: 14

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: presetsColumn.implicitHeight + 28
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor

                ColumnLayout {
                    id: presetsColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 14
                    spacing: 12

                    Text {
                        text: tr("settings.theme_presets_title")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 17
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 1320 ? 3 : root.width > 760 ? 2 : 1
                        columnSpacing: 10
                        rowSpacing: 10

                        Repeater {
                            model: settingsController.themePresets
                            delegate: Rectangle {
                                property var presetData: modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: 96
                                radius: settingsController.cardRadius
                                color: presetData.active ? settingsController.accentPanelColor : settingsController.backgroundColor
                                border.color: presetData.active ? presetData.accent : settingsController.borderColor
                                border.width: presetData.active ? 1.5 : 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 6
                                        Repeater {
                                            model: [presetData.background, presetData.surface, presetData.accent, presetData.warning, presetData.border]
                                            Rectangle {
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 16
                                                radius: 5
                                                color: modelData
                                                border.color: settingsController.borderColor
                                            }
                                        }
                                    }

                                    Text {
                                        text: tr(presetData.labelKey)
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        text: tr(presetData.descriptionKey)
                                        color: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 10
                                        Layout.fillWidth: true
                                        maximumLineCount: 2
                                        wrapMode: Text.WordWrap
                                        elide: Text.ElideRight
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: settingsController.setThemePreset(presetData.key)
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: quickColumn.implicitHeight + 28
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor

                ColumnLayout {
                    id: quickColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 14
                    spacing: 12

                    Text {
                        text: tr("settings.theme_palette_title")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 17
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 1260 ? 4 : root.width > 820 ? 3 : 2
                        columnSpacing: 8
                        rowSpacing: 8

                        Repeater {
                            model: settingsController.accentPaletteOptions
                            delegate: Rectangle {
                                property var paletteData: modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: 76
                                radius: settingsController.cardRadius
                                color: paletteMouse.containsMouse ? settingsController.controlColor : settingsController.backgroundColor
                                border.color: settingsController.borderColor

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    Text {
                                        Layout.fillWidth: true
                                        text: paletteData.label
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 12
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 24
                                        spacing: 5
                                        Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; radius: 7; color: paletteData.accent }
                                        Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; radius: 7; color: paletteData.support }
                                        Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; radius: 7; color: paletteData.warm }
                                    }
                                }

                                MouseArea {
                                    id: paletteMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: settingsController.applyAccentPalette(paletteData.key)
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 58
                        radius: settingsController.cardRadius
                        color: settingsController.backgroundColor
                        border.color: settingsController.borderColor

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            TextField {
                                id: accentSeed
                                Layout.fillWidth: true
                                Layout.preferredHeight: 38
                                text: settingsController.accentColor
                                selectByMouse: true
                                color: settingsController.textColor
                                selectedTextColor: settingsController.backgroundColor
                                selectionColor: settingsController.accentColor
                                font.family: "Consolas"
                                font.pixelSize: 12
                                validator: RegularExpressionValidator { regularExpression: /^#?[0-9a-fA-F]{0,6}$/ }
                                background: Rectangle {
                                    radius: settingsController.cardRadius
                                    color: accentSeed.hovered || accentSeed.activeFocus ? settingsController.accentPanelColor : settingsController.surfaceAltColor
                                    border.color: accentSeed.activeFocus ? settingsController.accentColor : settingsController.borderColor
                                    border.width: accentSeed.activeFocus ? 1.5 : 1
                                }
                            }

                            PrimaryButton {
                                Layout.preferredWidth: 150
                                Layout.preferredHeight: 38
                                text: tr("settings.theme_generate_from_color")
                                fill: settingsController.controlColor
                                hoverFill: settingsController.controlHoverColor
                                textFill: settingsController.textColor
                                onClicked: settingsController.generateThemeFromAccent(accentSeed.text)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 50
                        radius: settingsController.cardRadius
                        color: settingsController.backgroundColor
                        border.color: settingsController.borderColor

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 10
                            Text {
                                Layout.fillWidth: true
                                text: tr("settings.theme_gradient")
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 13
                                font.bold: true
                                elide: Text.ElideRight
                            }
                            ToggleSwitch {
                                checked: settingsController.gradientEnabled
                                onClicked: settingsController.setThemeGradientEnabled(checked)
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            visible: root.activeSection === "access"
            Layout.fillWidth: true
            Layout.preferredHeight: accessColumn.implicitHeight + 28
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: settingsController.colorblindModeEnabled ? settingsController.infoColor : settingsController.borderColor

            ColumnLayout {
                id: accessColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 14
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3
                        Text {
                            text: tr("settings.colorblind_question_title")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: tr("settings.colorblind_question_body")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            Layout.fillWidth: true
                            maximumLineCount: 2
                            wrapMode: Text.WordWrap
                            elide: Text.ElideRight
                        }
                    }

                    ToggleSwitch {
                        checked: settingsController.colorblindModeEnabled
                        onClicked: settingsController.setColorblindModeEnabled(checked)
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1120 ? 3 : root.width > 720 ? 2 : 1
                    columnSpacing: 10
                    rowSpacing: 10

                    Repeater {
                        model: settingsController.colorblindProfileOptions
                        delegate: Rectangle {
                            property var profileData: modelData
                            Layout.fillWidth: true
                            Layout.preferredHeight: 82
                            radius: settingsController.cardRadius
                            color: profileData.active ? settingsController.accentPanelColor : (profileMouse.containsMouse ? settingsController.controlColor : settingsController.backgroundColor)
                            border.color: profileData.active ? settingsController.infoColor : settingsController.borderColor
                            border.width: profileData.active ? 1.5 : 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 4

                                Text {
                                    text: tr(profileData.labelKey)
                                    color: profileData.active ? settingsController.textColor : settingsController.secondaryTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 13
                                    font.bold: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: tr(profileData.descriptionKey)
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 10
                                    Layout.fillWidth: true
                                    maximumLineCount: 2
                                    wrapMode: Text.WordWrap
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: profileMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: settingsController.setColorblindProfile(profileData.key)
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            visible: root.activeSection === "shape"
            Layout.fillWidth: true
            Layout.preferredHeight: shapeColumn.implicitHeight + 28
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor

            ColumnLayout {
                id: shapeColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 14
                spacing: 14

                Text {
                    text: tr("settings.theme_shape_title")
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 18
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: sidebarControls.implicitHeight + 24
                    radius: settingsController.cardRadius
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor

                    ColumnLayout {
                        id: sidebarControls
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            ColumnLayout {
                                Layout.preferredWidth: 180
                                spacing: 2
                                Text {
                                    text: tr("settings.sidebar_width_title")
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 13
                                    font.bold: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: settingsController.sidebarWidth + " px"
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }

                            Slider {
                                id: sidebarSlider
                                Layout.fillWidth: true
                                from: 240
                                to: 340
                                stepSize: 1
                                value: settingsController.sidebarWidth
                                live: true
                                onMoved: settingsController.setSidebarWidth(Math.round(value))
                                onPressedChanged: if (!pressed) settingsController.setSidebarWidth(Math.round(value))
                                background: Rectangle {
                                    x: sidebarSlider.leftPadding
                                    y: sidebarSlider.topPadding + sidebarSlider.availableHeight / 2 - height / 2
                                    width: sidebarSlider.availableWidth
                                    height: 6
                                    radius: 3
                                    color: settingsController.controlColor
                                    Rectangle {
                                        width: sidebarSlider.visualPosition * parent.width
                                        height: parent.height
                                        radius: parent.radius
                                        color: settingsController.accentColor
                                    }
                                }
                                handle: Rectangle {
                                    x: sidebarSlider.leftPadding + sidebarSlider.visualPosition * (sidebarSlider.availableWidth - width)
                                    y: sidebarSlider.topPadding + sidebarSlider.availableHeight / 2 - height / 2
                                    width: 22
                                    height: 22
                                    radius: 11
                                    color: sidebarSlider.pressed ? settingsController.accentHoverColor : settingsController.accentColor
                                    border.color: settingsController.textColor
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Repeater {
                                model: [
                                    { "label": "Compacta", "value": 240 },
                                    { "label": "Padrao", "value": 286 },
                                    { "label": "Ampla", "value": 340 }
                                ]
                                delegate: Rectangle {
                                    property bool selected: settingsController.sidebarWidth === modelData.value
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 34
                                    radius: settingsController.buttonRadius
                                    color: selected ? settingsController.accentPanelColor : settingsController.surfaceAltColor
                                    border.color: selected ? settingsController.accentColor : settingsController.borderColor
                                    border.width: selected ? 1.5 : 1

                                    Text {
                                        anchors.centerIn: parent
                                        width: parent.width - 12
                                        text: modelData.label
                                        color: selected ? settingsController.textColor : settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        font.bold: selected
                                        horizontalAlignment: Text.AlignHCenter
                                        elide: Text.ElideRight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: settingsController.setSidebarWidth(modelData.value)
                                    }
                                }
                            }
                        }
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 900 ? 4 : 2
                    columnSpacing: 10
                    rowSpacing: 10

                    Repeater {
                        model: settingsController.buttonStyleOptions
                        delegate: Rectangle {
                            property bool selected: settingsController.buttonStyle === modelData.key
                            Layout.fillWidth: true
                            Layout.preferredHeight: 76
                            radius: settingsController.cardRadius
                            color: selected ? settingsController.accentPanelColor : settingsController.backgroundColor
                            border.color: selected ? settingsController.accentColor : settingsController.borderColor
                            border.width: selected ? 1.5 : 1

                            PrimaryButton {
                                anchors.centerIn: parent
                                width: Math.min(parent.width - 24, 160)
                                height: 36
                                text: tr(modelData.labelKey)
                                fill: selected ? settingsController.accentColor : settingsController.controlColor
                                hoverFill: settingsController.accentHoverColor
                                textFill: selected ? settingsController.textInverseColor : settingsController.textColor
                                visualStyle: modelData.key
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

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 900 ? 5 : root.width > 620 ? 3 : 2
                    columnSpacing: 10
                    rowSpacing: 10

                    Repeater {
                        model: settingsController.cardRadiusOptions
                        delegate: Rectangle {
                            property bool selected: settingsController.cardRadius === Number(modelData.key)
                            Layout.fillWidth: true
                            Layout.preferredHeight: 64
                            radius: Number(modelData.key)
                            color: selected ? settingsController.accentPanelColor : settingsController.backgroundColor
                            border.color: selected ? settingsController.accentColor : settingsController.borderColor
                            border.width: selected ? 1.5 : 1

                            Text {
                                anchors.centerIn: parent
                                width: parent.width - 16
                                text: tr(modelData.labelKey)
                                color: selected ? settingsController.textColor : settingsController.mutedTextColor
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                font.bold: selected
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

        Rectangle {
            visible: root.activeSection === "colors"
            Layout.fillWidth: true
            Layout.preferredHeight: colorsColumn.implicitHeight + 28
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor

            ColumnLayout {
                id: colorsColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 14
                spacing: 12

                Text {
                    text: tr("settings.theme_color_editor_title")
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 18
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1180 ? 4 : root.width > 820 ? 3 : root.width > 560 ? 2 : 1
                    columnSpacing: 10
                    rowSpacing: 10

                    Repeater {
                        model: settingsController.themeColorFields
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 76
                            radius: settingsController.cardRadius
                            color: settingsController.backgroundColor
                            border.color: settingsController.borderColor

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 9
                                spacing: 5

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 7
                                    Rectangle {
                                        Layout.preferredWidth: 18
                                        Layout.preferredHeight: 18
                                        radius: 6
                                        color: root.customThemeColor(modelData.key)
                                        border.color: settingsController.borderColor
                                    }
                                    Text {
                                        text: tr(modelData.labelKey)
                                        color: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 10
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }

                                TextField {
                                    id: colorInput
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 34
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
                                        color: colorInput.hovered || colorInput.activeFocus ? settingsController.accentPanelColor : settingsController.surfaceAltColor
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
