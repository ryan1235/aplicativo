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
                    Column {
                        id: onlinePreviewColumn
                        width: onlinePreview.width
                        spacing: 8
                        Repeater {
                            model: chatController.onlineRows
                            delegate: Rectangle {
                                width: onlinePreviewColumn.width
                                height: 48
                                radius: 7
                                color: "#0e1a2d"
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 10
                                    Rectangle {
                                        width: 28
                                        height: 28
                                        radius: 14
                                        color: "#1d3353"
                                        Image {
                                            anchors.fill: parent
                                            anchors.margins: 1
                                            source: modelData.avatar
                                            fillMode: Image.PreserveAspectCrop
                                            visible: modelData.avatar !== ""
                                        }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 0
                                        Text { text: modelData.name; color: "#edf6ff"; font.bold: true; font.family: "Segoe UI"; elide: Text.ElideRight; Layout.fillWidth: true }
                                        Text { text: modelData.detail; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                                    }
                                }
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
