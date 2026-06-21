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

    ColumnLayout {
        id: content
        width: root.width
        spacing: 16

        Text {
            text: tr("notifications.title")
            color: settingsController.textColor
            font.family: "Segoe UI"
            font.pixelSize: 26
            font.bold: true
            Layout.fillWidth: true
        }

        Text {
            text: tr("notifications.subtitle")
            color: settingsController.accentColor
            font.family: "Segoe UI"
            font.pixelSize: 13
            font.bold: true
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "transparent"
            border.color: "transparent"
            Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.2 }
            Rectangle { anchors.fill: parent; radius: 8; color: settingsController.accentColor; opacity: 0.035 }
            Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: settingsController.accentColor; opacity: 0.2; border.width: 1 }
            implicitHeight: 284

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text {
                            text: tr("notifications.squadlock_title")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 20
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: tr("notifications.squadlock_body")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: 150
                        Layout.preferredHeight: 42
                        radius: 8
                        color: "transparent"
                        border.color: "transparent"
                        Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.4 }
                        Rectangle { anchors.fill: parent; radius: 8; color: settingsController.accentColor; opacity: notificationsController.overlayVisible ? 0.2 : 0.0 }
                        Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: notificationsController.overlayVisible ? settingsController.accentColor : Qt.rgba(1,1,1,0.1); border.width: 1 }
                        Behavior on color { ColorAnimation { duration: 140 } }
                        Text {
                            anchors.centerIn: parent
                            text: notificationsController.overlayVisible ? tr("notifications.overlay_live") : tr("notifications.overlay_idle")
                            color: notificationsController.overlayVisible ? settingsController.accentColor : settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            font.bold: true
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 22

                    Text {
                        text: notificationsController.timeText
                        color: notificationsController.squadlockFinished ? settingsController.successColor : settingsController.warningColor
                        font.family: "Segoe UI"
                        font.pixelSize: 54
                        font.bold: true
                        Layout.preferredWidth: 220
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text {
                            text: tr(notificationsController.statusKey)
                            color: settingsController.secondaryTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 14
                            font.bold: true
                            Layout.fillWidth: true
                        }
                        ProgressBar {
                            Layout.fillWidth: true
                            value: notificationsController.progress
                            background: Rectangle {
                                implicitHeight: 10
                                radius: 5
                                color: "transparent"
                                Rectangle { anchors.fill: parent; radius: 5; color: settingsController.scrimColor; opacity: 0.3 }
                                border.color: Qt.rgba(1,1,1,0.1)
                            }
                            contentItem: Item {
                                implicitHeight: 10
                                Rectangle {
                                    width: parent.width * notificationsController.progress
                                    height: parent.height
                                    radius: 5
                                    color: notificationsController.squadlockFinished ? settingsController.successColor : settingsController.accentColor
                                    Behavior on width { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            ToggleSwitch {
                                id: overlaySwitch
                                checked: notificationsController.overlayEnabled
                                onToggled: notificationsController.setOverlayEnabled(checked)
                            }
                            Text {
                                text: tr("notifications.show_overlay")
                                color: settingsController.mutedTextColor
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    PrimaryButton {
                        text: tr("notifications.start")
                        onClicked: notificationsController.startSquadlock()
                    }
                    PrimaryButton {
                        text: tr("notifications.reset")
                        enabled: notificationsController.squadlockRunning || notificationsController.squadlockFinished
                        fill: Qt.rgba(0,0,0,0.4)
                        hoverFill: Qt.rgba(1,1,1,0.1)
                        textFill: settingsController.accentColor
                        onClicked: notificationsController.resetSquadlock()
                    }
                    PrimaryButton {
                        text: tr("notifications.finish")
                        enabled: notificationsController.squadlockRunning || notificationsController.squadlockFinished
                        fill: Qt.rgba(0,0,0,0.4)
                        hoverFill: Qt.rgba(1,1,1,0.1)
                        textFill: settingsController.accentColor
                        onClicked: notificationsController.finishSquadlock()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "transparent"
            border.color: "transparent"
            Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.2 }
            Rectangle { anchors.fill: parent; radius: 8; color: settingsController.accentColor; opacity: 0.035 }
            Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: settingsController.accentColor; opacity: 0.2; border.width: 1 }
            implicitHeight: settingsColumn.implicitHeight + 32

            ColumnLayout {
                id: settingsColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 10

                Text {
                    text: tr("notifications.runtime_alerts")
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 18
                    font.bold: true
                    Layout.fillWidth: true
                }

                Repeater {
                    model: notificationsController.notifications
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 66
                        radius: 7
                        color: "transparent"
                        border.color: "transparent"
                        Rectangle { anchors.fill: parent; radius: 7; color: settingsController.scrimColor; opacity: 0.4 }
                        Rectangle { anchors.fill: parent; radius: 7; color: "transparent"; border.color: Qt.rgba(1,1,1,0.1); border.width: 1 }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 10
                            ToggleSwitch {
                                checked: active
                                onToggled: notificationsController.setNotificationEnabled(key, checked)
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: tr(labelKey)
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.bold: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: tr(detailKey)
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}


