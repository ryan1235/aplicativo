import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: formRoot
    radius: 12
    color: "transparent"
    border.color: "transparent"

    signal saved(string name, int duration, bool active, bool sound, bool showOverlay)
    signal canceled()

    implicitHeight: mainLayout.implicitHeight + 40

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    ColumnLayout {
        id: mainLayout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 20
        spacing: 22

        Text {
            text: tr("notifications.custom.create")
            color: settingsController.textColor
            font.family: "Segoe UI"
            font.pixelSize: 22
            font.bold: true
            Layout.fillWidth: true
            Layout.bottomMargin: 8
        }

        // Name input
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Text {
                text: tr("notifications.custom.name_placeholder")
                color: settingsController.mutedTextColor
                font.family: "Segoe UI"
                font.pixelSize: 13
                font.bold: true
            }
            TextField {
                id: nameInput
                placeholderText: "Ex: " + tr("notifications.custom.name_placeholder")
                Layout.fillWidth: true
                color: settingsController.textColor
                font.pixelSize: 14
                background: Rectangle {
                    radius: 6
                    color: Qt.rgba(0,0,0,0.3)
                    border.color: nameInput.activeFocus ? settingsController.accentColor : Qt.rgba(1,1,1,0.1)
                    border.width: 1
                }
                padding: 12
            }
        }

        // Duration input
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Text {
                text: tr("notifications.custom.duration")
                color: settingsController.mutedTextColor
                font.family: "Segoe UI"
                font.pixelSize: 13
                font.bold: true
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                TextField {
                    id: durationInput
                    text: "10"
                    Layout.preferredWidth: 80
                    Layout.preferredHeight: 44
                    color: settingsController.textColor
                    font.pixelSize: 14
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    background: Rectangle {
                        radius: 6
                        color: Qt.rgba(0,0,0,0.3)
                        border.color: durationInput.activeFocus ? settingsController.accentColor : Qt.rgba(1,1,1,0.1)
                        border.width: 1
                    }
                    validator: IntValidator { bottom: 1; top: 9999 }
                }
                
                Rectangle {
                    id: unitSelector
                    Layout.preferredWidth: 160
                    Layout.preferredHeight: 44
                    radius: 6
                    color: Qt.rgba(0,0,0,0.3)
                    border.color: Qt.rgba(1,1,1,0.1)
                    border.width: 1
                    
                    property bool isHours: false
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 4
                        
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 4
                            color: !unitSelector.isHours ? settingsController.accentColor : "transparent"
                            Text {
                                anchors.centerIn: parent
                                text: tr("notifications.custom.minutes")
                                color: !unitSelector.isHours ? settingsController.textInverseColor : settingsController.textColor
                                font.pixelSize: 13
                                font.bold: true
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: unitSelector.isHours = false
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 4
                            color: unitSelector.isHours ? settingsController.accentColor : "transparent"
                            Text {
                                anchors.centerIn: parent
                                text: tr("notifications.custom.hours")
                                color: unitSelector.isHours ? settingsController.textInverseColor : settingsController.textColor
                                font.pixelSize: 13
                                font.bold: true
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: unitSelector.isHours = true
                            }
                        }
                    }
                }
                Item { Layout.fillWidth: true }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Qt.rgba(1,1,1,0.08)
            Layout.topMargin: 4
            Layout.bottomMargin: 4
        }

        // Options
        RowLayout {
            Layout.fillWidth: true
            spacing: 24

            RowLayout {
                spacing: 8
                ToggleSwitch { id: activeSwitch; checked: true }
                Text { text: tr("notifications.custom.active"); color: settingsController.textColor; font.pixelSize: 13 }
            }
            RowLayout {
                spacing: 8
                ToggleSwitch { id: soundSwitch; checked: true }
                Text { text: tr("notifications.custom.play_sound"); color: settingsController.textColor; font.pixelSize: 13 }
            }
            RowLayout {
                spacing: 8
                ToggleSwitch { id: overlaySwitch; checked: true }
                Text { text: tr("notifications.custom.show_overlay"); color: settingsController.textColor; font.pixelSize: 13 }
            }
        }

        Item { Layout.preferredHeight: 8 }

        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            
            Item { Layout.fillWidth: true }
            
            PrimaryButton {
                text: tr("notifications.custom.cancel")
                Layout.preferredWidth: 110
                fill: Qt.rgba(0,0,0,0.4)
                textFill: settingsController.accentColor
                hoverFill: Qt.rgba(1,1,1,0.1)
                onClicked: formRoot.canceled()
            }
            PrimaryButton {
                text: tr("notifications.custom.save")
                Layout.preferredWidth: 110
                fill: settingsController.accentColor
                textFill: settingsController.textInverseColor
                hoverFill: settingsController.accentHoverColor
                onClicked: {
                    var dur = parseInt(durationInput.text)
                    if (isNaN(dur)) dur = 1;
                    if (!unitSelector.isHours) dur *= 60; // minutes
                    else dur *= 3600; // hours
                    
                    var finalName = nameInput.text.trim();
                    if (finalName === "") finalName = "Timer";
                    
                    formRoot.saved(finalName, dur, activeSwitch.checked, soundSwitch.checked, overlaySwitch.checked)
                }
            }
        }
    }
}
