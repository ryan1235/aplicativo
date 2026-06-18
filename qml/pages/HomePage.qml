import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: content.implicitHeight + 36

    Component.onCompleted: {
        if (chatController.apiToken) {
            newsController.fetchNews()
        }
    }

    Connections {
        target: chatController
        function onChanged() {
            console.log("ChatController changed! apiToken:", chatController.apiToken, "newsCount:", newsController.newsModel ? newsController.newsModel.length : 0, "loading:", newsController.loading)
            if (chatController.apiToken && (!newsController.newsModel || newsController.newsModel.length === 0) && !newsController.loading) {
                newsController.fetchNews()
            }
        }
    }

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    function newsCategory(item) {
        var raw = String((item && item.type) || "general").toLowerCase()
        var normalized = raw.replace(/[^a-z0-9_-]+/g, "-")
        var key = "home.news.category." + normalized
        var translated = tr(key)
        if (translated !== key)
            return translated
        return (item && item.category) ? item.category : raw
    }

    function newsDate(value) {
        if (!value)
            return ""
        var date = new Date(value)
        if (isNaN(date.getTime()))
            return ""
        var dateMask = i18nController.language === "en" ? "MM/dd/yyyy" : "dd/MM/yyyy"
        return Qt.formatDateTime(date, dateMask + " HH:mm")
    }

    function newsAge(value) {
        if (!value)
            return ""
        var date = new Date(value)
        if (isNaN(date.getTime()))
            return ""
        var seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000))
        if (seconds < 60)
            return tr("home.news.just_now")
        var minutes = Math.floor(seconds / 60)
        if (minutes < 60)
            return minutes + " " + tr(minutes === 1 ? "home.news.minute_ago" : "home.news.minutes_ago")
        var hours = Math.floor(minutes / 60)
        if (hours < 24)
            return hours + " " + tr(hours === 1 ? "home.news.hour_ago" : "home.news.hours_ago")
        var days = Math.floor(hours / 24)
        return days + " " + tr(days === 1 ? "home.news.day_ago" : "home.news.days_ago")
    }

    function newsMeta(item) {
        var parts = [newsCategory(item)]
        var ageText = newsAge(item ? item.date : "")
        if (ageText)
            parts.push(ageText)
        parts.push(String((item && item.viewCount) || 0) + " " + tr("home.news.views"))
        return parts.join("  |  ")
    }

    ColumnLayout {
        id: content
        width: root.width
        spacing: 16

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 246
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor
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
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 28
                    font.bold: true
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    text: tr("home.body")
                    color: settingsController.mutedTextColor
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
                        fill: settingsController.controlColor
                        hoverFill: settingsController.controlHoverColor
                        textFill: settingsController.textColor
                        onClicked: appController.setCurrentPage("autoClicker")
                    }
                    PrimaryButton {
                        text: tr("stockpile.nav")
                        fill: settingsController.controlColor
                        hoverFill: settingsController.controlHoverColor
                        textFill: settingsController.textColor
                        onClicked: appController.setCurrentPage("stockpile")
                    }
                }

                Item { Layout.fillHeight: true }

                Text {
                    text: appController.foxholeStatus + " | " + steamController.status
                    color: settingsController.accentColor
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
                accent: settingsController.accentColor
            }
            MetricCard {
                Layout.fillWidth: true
                title: tr("home.metric_stockpile")
                value: stockpileController.running ? tr("home.state_watching") : tr("home.state_idle")
                detail: stockpileController.lastResponse
                accent: settingsController.successColor
            }
            MetricCard {
                Layout.fillWidth: true
                title: tr("home.metric_updates")
                value: appController.version
                detail: updateController.status
                accent: settingsController.warningColor
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor
            implicitHeight: 520

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
                            text: tr("home.news.title")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: tr("home.news.subtitle")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                    PrimaryButton {
                        text: tr("home.news.refresh")
                        onClicked: newsController.fetchNews()
                        visible: !newsController.loading
                    }
                }

                Text {
                    text: newsController.error ? tr("home.news.error") + ": " + newsController.error : (newsController.loading ? tr("home.news.loading") : "")
                    color: settingsController.warningColor
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    visible: newsController.error !== "" || newsController.loading
                }

                GridView {
                    id: newsGrid
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    cellWidth: width > 1080 ? Math.floor(width / 3) : width > 720 ? Math.floor(width / 2) : width
                    cellHeight: 318
                    reuseItems: true
                    model: newsController.newsModel

                    delegate: Rectangle {
                        width: newsGrid.cellWidth - 16
                        height: newsGrid.cellHeight - 14
                        radius: settingsController.cardRadius
                        color: hoverArea.containsMouse ? settingsController.accentPanelColor : settingsController.backgroundColor
                        border.color: hoverArea.containsMouse ? settingsController.accentColor : settingsController.borderColor
                        border.width: 1
                        clip: true

                        Behavior on color { ColorAnimation { duration: 150 } }
                        Behavior on border.color { ColorAnimation { duration: 150 } }

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 0

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 138
                                color: settingsController.surfaceColor
                                clip: true

                                Image {
                                    anchors.fill: parent
                                    source: modelData.image || appController.assetUrl("img/wallpeper.png")
                                    fillMode: Image.PreserveAspectCrop
                                    opacity: modelData.image ? 1 : 0.34
                                }

                                Rectangle {
                                    anchors.fill: parent
                                    color: settingsController.scrimColor
                                    opacity: hoverArea.containsMouse ? 0.08 : 0.20
                                }

                                Text {
                                    anchors.left: parent.left
                                    anchors.bottom: parent.bottom
                                    anchors.leftMargin: 16
                                    anchors.bottomMargin: 14
                                    width: parent.width - 32
                                    text: modelData.image ? "" : "GG COALITION NEWS"
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 18
                                    font.bold: true
                                    elide: Text.ElideRight
                                    visible: text !== ""
                                }

                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.top: parent.top
                                    anchors.leftMargin: 14
                                    anchors.topMargin: 12
                                    width: Math.min(parent.width - 28, categoryText.implicitWidth + 22)
                                    height: 26
                                    radius: 6
                                    color: settingsController.accentPanelColor
                                    border.color: settingsController.accentHoverColor

                                    Text {
                                        id: categoryText
                                        anchors.centerIn: parent
                                        width: parent.width - 14
                                        text: root.newsCategory(modelData)
                                        color: settingsController.accentColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.leftMargin: 18
                                Layout.rightMargin: 18
                                Layout.topMargin: 14
                                Layout.bottomMargin: 12
                                spacing: 7

                                Text {
                                    text: root.newsAge(modelData.date)
                                    color: settingsController.accentColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                    font.bold: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: modelData.title || ""
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.bold: true
                                    font.pixelSize: 17
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: modelData.excerpt || modelData.body || ""
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 13
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 3
                                    elide: Text.ElideRight
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Rectangle {
                                        Layout.preferredWidth: 24
                                        Layout.preferredHeight: 24
                                        radius: 12
                                        color: settingsController.accentPanelColor
                                        border.color: settingsController.accentColor

                                        Text {
                                            anchors.centerIn: parent
                                            text: String(modelData.authorName || "G").substring(0, 1).toUpperCase()
                                            color: settingsController.accentColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 11
                                            font.bold: true
                                        }
                                    }

                                    Text {
                                        text: modelData.authorName || "GG Coalition"
                                        color: settingsController.warningColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 12
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        text: root.newsDate(modelData.date)
                                        color: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                        visible: text !== ""
                                    }

                                    Text {
                                        text: String(modelData.viewCount || 0) + " " + tr("home.news.views")
                                        color: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }

                        MouseArea {
                            id: hoverArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                newsModal.newsItem = modelData
                                newsModal.open()
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        width: parent.width - 36
                        text: chatController.apiToken ? tr("home.news.empty") : tr("home.news.login_required")
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 13
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        visible: newsGrid.count === 0 && !newsController.loading && !newsController.error
                    }
                }
            }
        }
    }

    NewsModal {
        id: newsModal
    }
}


