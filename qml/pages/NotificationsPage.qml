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
            color: "#edf6ff"
            font.family: "Segoe UI"
            font.pixelSize: 26
            font.bold: true
            Layout.fillWidth: true
        }

        Text {
            text: tr("notifications.subtitle")
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
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 20
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: tr("notifications.squadlock_body")
                            color: "#99abc4"
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
                        color: notificationsController.overlayVisible ? "#173c35" : "#0e1a2d"
                        border.color: notificationsController.overlayVisible ? "#5eead4" : "#2d496f"
                        Behavior on color { ColorAnimation { duration: 140 } }
                        Text {
                            anchors.centerIn: parent
                            text: notificationsController.overlayVisible ? tr("notifications.overlay_live") : tr("notifications.overlay_idle")
                            color: notificationsController.overlayVisible ? "#5eead4" : "#99abc4"
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
                        color: notificationsController.squadlockFinished ? "#62d7a4" : "#ffd166"
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
                            color: "#c7d7ed"
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
                                color: "#07111f"
                                border.color: "#24486d"
                            }
                            contentItem: Item {
                                implicitHeight: 10
                                Rectangle {
                                    width: parent.width * notificationsController.progress
                                    height: parent.height
                                    radius: 5
                                    color: notificationsController.squadlockFinished ? "#62d7a4" : "#5eead4"
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
                                color: "#99abc4"
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
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: notificationsController.resetSquadlock()
                    }
                    PrimaryButton {
                        text: tr("notifications.finish")
                        enabled: notificationsController.squadlockRunning || notificationsController.squadlockFinished
                        fill: "#0e1a2d"
                        hoverFill: "#1d3353"
                        textFill: "#edf6ff"
                        onClicked: notificationsController.finishSquadlock()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
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
                    color: "#edf6ff"
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
                        color: "#0e1a2d"
                        border.color: "#1e3554"

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
                                    color: "#edf6ff"
                                    font.family: "Segoe UI"
                                    font.bold: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: tr(detailKey)
                                    color: "#99abc4"
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
