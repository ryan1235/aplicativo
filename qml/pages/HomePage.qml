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

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    ColumnLayout {
        id: content
        width: root.width
        spacing: 16

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 246
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
            clip: true

            Image {
                anchors.fill: parent
                source: appController.assetUrl("img/wallpeper.png")
                fillMode: Image.PreserveAspectCrop
                opacity: 0.28
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 22
                spacing: 10

                Text {
                    text: tr("home.title")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 28
                    font.bold: true
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    text: tr("home.body")
                    color: "#c7d7ed"
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    Layout.maximumWidth: 760
                    Layout.fillWidth: true
                }

                RowLayout {
                    spacing: 10
                    PrimaryButton {
                        text: tr("home.open_foxhole")
                        onClicked: appController.openFoxhole()
                    }
                    PrimaryButton {
                        text: tr("nav.auto_clicker")
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: appController.setCurrentPage("autoClicker")
                    }
                    PrimaryButton {
                        text: tr("stockpile.nav")
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: appController.setCurrentPage("stockpile")
                    }
                }

                Item { Layout.fillHeight: true }

                Text {
                    text: appController.foxholeStatus + " | " + steamController.status
                    color: "#8ab4ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 980 ? 4 : root.width > 640 ? 2 : 1
            columnSpacing: 12
            rowSpacing: 12

            MetricCard {
                Layout.fillWidth: true
                title: tr("home.metric_steam")
                value: steamController.personaName
                detail: steamController.steamId || tr("sidebar.searching_steam")
            }
            MetricCard {
                Layout.fillWidth: true
                title: tr("home.metric_auto_clicker")
                value: autoClickerController.running ? tr("home.state_running") : tr("home.state_paused")
                detail: autoClickerController.status
                accent: "#8ab4ff"
            }
            MetricCard {
                Layout.fillWidth: true
                title: tr("home.metric_stockpile")
                value: stockpileController.running ? tr("home.state_watching") : tr("home.state_idle")
                detail: stockpileController.lastResponse
                accent: "#62d7a4"
            }
            MetricCard {
                Layout.fillWidth: true
                title: tr("home.metric_updates")
                value: appController.version
                detail: updateController.status
                accent: "#ffd166"
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
            implicitHeight: 330

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: tr("home.chat.title")
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: tr("home.chat.subtitle")
                            color: "#99abc4"
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                    PrimaryButton {
                        text: chatController.connected ? tr("home.chat.connected") : tr("home.chat.connect")
                        onClicked: chatController.connectWithSteam()
                    }
                    PrimaryButton {
                        text: tr("home.open")
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: appController.setCurrentPage("chat")
                    }
                }

                Text {
                    text: chatController.status
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                ScrollView {
                    id: onlinePreview
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    Flow {
                        id: onlinePreviewFlow
                        width: onlinePreview.width
                        spacing: 12

                        Repeater {
                            model: chatController.onlineRows
                            delegate: Item {
                                width: 44
                                height: 44

                                Rectangle {
                                    anchors.fill: parent
                                    radius: 22
                                    color: "#1d3353"
                                    border.color: hoverArea.containsMouse ? "#5eead4" : "transparent"
                                    border.width: 2
                                    clip: true

                                    Behavior on border.color { ColorAnimation { duration: 150 } }

                                    Rectangle {
                                        id: maskRect
                                        anchors.fill: parent
                                        anchors.margins: 2
                                        radius: width / 2
                                        visible: false
                                    }

                                    Image {
                                        id: avatarImg
                                        anchors.fill: maskRect
                                        source: modelData.avatar
                                        fillMode: Image.PreserveAspectCrop
                                        visible: false
                                    }

                                    OpacityMask {
                                        anchors.fill: maskRect
                                        source: avatarImg
                                        maskSource: maskRect
                                        visible: modelData.avatar !== ""
                                    }
                                    
                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.name.substring(0, 2).toUpperCase()
                                        color: "#5eead4"
                                        font.bold: true
                                        font.pixelSize: 16
                                        visible: modelData.avatar === ""
                                    }
                                }

                                MouseArea {
                                    id: hoverArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                }

                                ToolTip.visible: hoverArea.containsMouse
                                ToolTip.text: modelData.name + (modelData.detail ? "\n" + modelData.detail : "")
                                ToolTip.delay: 150
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        width: parent.width - 36
                        text: tr("home.chat.online_empty")
                        color: "#99abc4"
                        font.family: "Segoe UI"
                        font.pixelSize: 13
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        visible: chatController.onlineRows.length === 0
                    }
                }
            }
        }
    }
}
