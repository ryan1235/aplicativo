import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import "../components"

Rectangle {
    id: root
    color: "transparent"

    property string selectedRange: "month"
    property var profile: chatController.userProfile || {}
    property var metrics: chatController.userMetrics || {}
    property var account: metrics.account || profile
    property var counters: account.counters || {}
    property var actions: metrics.actions || {}
    property var categories: (actions.categories && actions.categories.length) ? actions.categories : (chatController.activityCategories || [])
    property var topActions: (actions.actions && actions.actions.length) ? actions.actions : (chatController.activityActions || [])
    property var recentLogs: (metrics.recentLogs && metrics.recentLogs.length) ? metrics.recentLogs : (chatController.activityLogs || [])

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    function safeImageSource(value, fallback) {
        var text = String(value || "")
        if (text.indexOf("http://") === 0 || text.indexOf("https://") === 0 || text.indexOf("file:") === 0 || text.indexOf("qrc:") === 0 || text.indexOf("data:") === 0)
            return text
        return fallback || ""
    }

    function loadProfileMetrics() {
        if (!chatController.apiToken)
            return
        chatController.fetchCurrentUserMetrics(selectedRange)
    }

    onVisibleChanged: {
        if (visible) {
            chatController.ensureStarted()
            loadProfileMetrics()
        }
    }

    Component.onCompleted: loadProfileMetrics()

    function setRange(value) {
        selectedRange = value
        loadProfileMetrics()
    }

    function profileName() {
        return account.globalName || account.displayName || account.personaname || account.username || chatController.currentUserName || tr("profile.default_user")
    }

    function profileHandle() {
        var username = account.username || account.discordUsername || ""
        if (username)
            return "@" + username
        return account.discordId || account.steamId || account.id || tr("profile.unknown_user")
    }

    function avatarSource() {
        return safeImageSource(account.avatar || account.discordAvatarUrl || account.avatarfull || account.avatarUrl || account.avatarmedium || chatController.currentUserAvatar, "")
    }

    function canOpenAdminPanel() {
        var role = String(account.role || "").toUpperCase()
        return role === "DEV" || role === "WINNER" || role === "ADMIN"
    }

    function numberValue(value) {
        var n = Number(value)
        if (isNaN(n))
            return 0
        return n
    }

    function compactNumber(value) {
        var n = numberValue(value)
        if (n >= 1000000)
            return (Math.round(n / 100000) / 10) + "M"
        if (n >= 1000)
            return (Math.round(n / 100) / 10) + "k"
        return String(Math.round(n))
    }

    function formatTime(seconds) {
        var total = Math.floor(numberValue(seconds))
        if (total <= 0)
            return "0m"
        var days = Math.floor(total / 86400)
        var hours = Math.floor((total % 86400) / 3600)
        var minutes = Math.floor((total % 3600) / 60)
        if (days > 0)
            return days + "d " + hours + "h"
        if (hours > 0)
            return hours + "h " + minutes + "m"
        if (minutes > 0)
            return minutes + "m"
        return total + "s"
    }

    function formatDate(isoString) {
        if (!isoString)
            return "-"
        var date = new Date(isoString)
        if (isNaN(date.getTime()))
            return "-"
        return date.toLocaleDateString() + " " + date.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})
    }

    function formatRelative(isoString) {
        if (!isoString)
            return "-"
        var date = new Date(isoString)
        if (isNaN(date.getTime()))
            return "-"
        var diff = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000))
        if (diff < 60)
            return tr("profile.just_now")
        if (diff < 3600)
            return tr("profile.minutes_ago").replace("{count}", Math.floor(diff / 60))
        if (diff < 86400)
            return tr("profile.hours_ago").replace("{count}", Math.floor(diff / 3600))
        return tr("profile.days_ago").replace("{count}", Math.floor(diff / 86400))
    }

    function loginEvents(rangeName) {
        var rows = metrics.logins || {}
        var row = rows[rangeName || selectedRange] || {}
        return numberValue(row.events)
    }

    function labelText(item) {
        if (!item)
            return "-"
        return String(item.category || item.action || item.series || item.bucket || item.label || "-")
    }

    function actionLabel(item) {
        if (!item)
            return "-"
        var category = String(item.category || "")
        var action = String(item.action || "")
        if (category && action)
            return category + " / " + action
        return category || action || "-"
    }

    function barMax(rows, key) {
        var max = 1
        for (var i = 0; i < rows.length; i++) {
            var value = numberValue(rows[i] ? rows[i][key] : 0)
            if (value > max)
                max = value
        }
        return max
    }

    function barRatio(value, max) {
        if (!max || max <= 0)
            return 0
        return Math.max(0.05, Math.min(1, numberValue(value) / max))
    }

    function mentionTotal() {
        return numberValue(counters.mentionsReceived) + numberValue(counters.mentionsSent)
    }

    function lastLogText() {
        if (!recentLogs || recentLogs.length === 0)
            return tr("profile.no_data")
        var item = recentLogs[0]
        return actionLabel(item) + " x" + compactNumber(item.quantity || 1)
    }

    ScrollView {
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width - 40
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.margins: 20
            spacing: 16

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: root.width > 980 ? 286 : (root.width > 680 ? 430 : 680)
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor
                border.width: 1
                clip: true

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: 142
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: "#b10f6d" }
                        GradientStop { position: 0.48; color: settingsController.accentPanelColor }
                        GradientStop { position: 1.0; color: settingsController.accentColor }
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: 142
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop { position: 1.0; color: settingsController.surfaceColor }
                    }
                }

                RowLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 22
                    spacing: 18

                    Rectangle {
                        width: 108
                        height: 108
                        radius: 54
                        color: settingsController.controlColor
                        border.color: account.online ? settingsController.successColor : settingsController.borderColor
                        border.width: 3
                        Layout.alignment: Qt.AlignTop

                        Rectangle {
                            id: avatarMask
                            anchors.fill: parent
                            anchors.margins: 5
                            radius: 50
                            visible: false
                        }
                        Image {
                            id: avatarImage
                            anchors.fill: avatarMask
                            source: avatarSource()
                            fillMode: Image.PreserveAspectCrop
                            visible: false
                        }
                        OpacityMask {
                            anchors.fill: avatarMask
                            source: avatarImage
                            maskSource: avatarMask
                            visible: avatarImage.source !== ""
                        }
                        Text {
                            anchors.centerIn: parent
                            visible: avatarImage.source === ""
                            text: profileName().charAt(0).toUpperCase()
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 32
                            font.bold: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                text: profileName()
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 28
                                font.bold: true
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                maximumLineCount: 2
                            }

                            Rectangle {
                                visible: String(account.role || "") !== ""
                                height: 24
                                width: roleText.implicitWidth + 18
                                radius: 6
                                color: settingsController.accentPanelColor
                                border.color: settingsController.accentColor

                                Text {
                                    id: roleText
                                    anchors.centerIn: parent
                                    text: String(account.role || "")
                                    color: settingsController.accentColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                            }
                        }

                        Text {
                            text: profileHandle()
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 14
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        Text {
                            text: tr("profile.summary_title")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            Layout.maximumWidth: 760
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 8

                            Repeater {
                                model: [
                                    account.online ? tr("profile.online_now") : tr("profile.offline_now"),
                                    account.regiment || tr("profile.no_regiment"),
                                    account.panelAccessLevel !== undefined ? tr("profile.access_level") + ": " + account.panelAccessLevel : tr("profile.access_level_unknown"),
                                    account.appVersion ? tr("profile.app_version").replace("{version}", account.appVersion) : ""
                                ].filter(function(item) { return String(item || "") !== "" })

                                delegate: Rectangle {
                                    height: 30
                                    width: chipText.implicitWidth + 20
                                    radius: 8
                                    color: index === 0 && account.online ? settingsController.accentPanelColor : settingsController.controlColor
                                    border.color: index === 0 && account.online ? settingsController.successColor : settingsController.borderColor

                                    Text {
                                        id: chipText
                                        anchors.centerIn: parent
                                        text: String(modelData)
                                        color: index === 0 && account.online ? settingsController.successColor : settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 12
                                        font.bold: true
                                    }
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.alignment: Qt.AlignTop
                        Layout.preferredWidth: 210
                        spacing: 8

                        Rectangle {
                            visible: canOpenAdminPanel()
                            Layout.fillWidth: true
                            height: 36
                            radius: 8
                            color: adminHover.containsMouse ? settingsController.accentHoverColor : settingsController.accentColor

                            Text {
                                anchors.centerIn: parent
                                text: tr("profile.open_admin")
                                color: settingsController.textInverseColor
                                font.family: "Segoe UI"
                                font.pixelSize: 13
                                font.bold: true
                            }

                            MouseArea {
                                id: adminHover
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: appController.openAdminPanel(chatController.apiToken)
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 36
                            radius: 8
                            color: logoutHover.containsMouse ? settingsController.dangerColor : settingsController.controlColor
                            border.color: logoutHover.containsMouse ? settingsController.dangerColor : settingsController.borderColor

                            Text {
                                anchors.centerIn: parent
                                text: tr("profile.logout")
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 13
                                font.bold: true
                            }

                            MouseArea {
                                id: logoutHover
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    chatController.logout()
                                    appController.setCurrentPage("chat")
                                }
                            }
                        }
                    }
                }

                GridLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 18
                    columns: root.width > 980 ? 4 : 2
                    columnSpacing: 10
                    rowSpacing: 10

                    MetricCard {
                        Layout.fillWidth: true
                        title: tr("profile.total_online")
                        value: formatTime(account.totalOnlineSeconds)
                        detail: tr("profile.last_presence").replace("{time}", formatRelative(account.lastPresenceAt || account.updatedAt))
                        accent: settingsController.accentColor
                        valuePixelSize: 20
                    }
                    MetricCard {
                        Layout.fillWidth: true
                        title: tr("profile.account_age")
                        value: compactNumber(account.accountAgeDays || 0) + "d"
                        detail: tr("profile.created_at_short").replace("{date}", formatDate(account.createdAt))
                        accent: settingsController.infoColor
                        valuePixelSize: 20
                    }
                    MetricCard {
                        Layout.fillWidth: true
                        title: tr("profile.login_metric")
                        value: compactNumber(loginEvents(selectedRange))
                        detail: tr("profile.last_login_short").replace("{date}", formatRelative(account.lastLoginAt))
                        accent: settingsController.successColor
                        valuePixelSize: 20
                    }
                    MetricCard {
                        Layout.fillWidth: true
                        title: tr("profile.latest_title")
                        value: lastLogText()
                        detail: tr("profile.period_label_" + selectedRange)
                        accent: settingsController.warningColor
                        valuePixelSize: 18
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 54
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8

                    Text {
                        text: tr("profile.period")
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        font.bold: true
                    }

                    Repeater {
                        model: [
                            {key: "today", label: tr("profile.period_today")},
                            {key: "week", label: tr("profile.period_week")},
                            {key: "month", label: tr("profile.period_month")},
                            {key: "total", label: tr("profile.period_total")}
                        ]

                        delegate: Rectangle {
                            height: 34
                            width: periodText.implicitWidth + 24
                            radius: 8
                            color: selectedRange === modelData.key ? settingsController.accentPanelColor : settingsController.controlColor
                            border.color: selectedRange === modelData.key ? settingsController.accentColor : settingsController.borderColor

                            Text {
                                id: periodText
                                anchors.centerIn: parent
                                text: modelData.label
                                color: selectedRange === modelData.key ? settingsController.accentColor : settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                font.bold: true
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: setRange(modelData.key)
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }

                    Text {
                        text: metrics.generatedAt ? tr("profile.updated_at").replace("{time}", formatRelative(metrics.generatedAt)) : ""
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 11
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1040 ? 4 : root.width > 720 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                MetricCard {
                    Layout.fillWidth: true
                    title: tr("profile.metric_events")
                    value: compactNumber(actions.totalEvents || 0)
                    detail: tr("profile.metric_events_detail")
                    accent: settingsController.successColor
                }
                MetricCard {
                    Layout.fillWidth: true
                    title: tr("profile.metric_quantity")
                    value: compactNumber(actions.totalQuantity || 0)
                    detail: tr("profile.metric_quantity_detail")
                    accent: settingsController.accentColor
                }
                MetricCard {
                    Layout.fillWidth: true
                    title: tr("profile.messages")
                    value: compactNumber(counters.messages || 0)
                    detail: tr("profile.messages_detail").replace("{count}", compactNumber(counters.whisperMessages || 0))
                    accent: settingsController.infoColor
                }
                MetricCard {
                    Layout.fillWidth: true
                    title: tr("profile.interactions")
                    value: compactNumber(numberValue(counters.messageReactions) + mentionTotal())
                    detail: tr("profile.interactions_detail").replace("{count}", compactNumber(counters.newsViews || 0))
                    accent: settingsController.warningColor
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 900 ? 2 : 1
                columnSpacing: 14
                rowSpacing: 14

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 300
                    radius: settingsController.cardRadius
                    color: settingsController.surfaceColor
                    border.color: settingsController.borderColor
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: tr("profile.graph_categories")
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 18
                                font.bold: true
                                Layout.fillWidth: true
                            }
                            Text {
                                text: tr("profile.graph_categories_hint")
                                color: settingsController.mutedTextColor
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                            }
                        }

                        Text {
                            visible: categories.length === 0
                            text: tr("profile.no_data")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                        }

                        Repeater {
                            model: categories

                            delegate: ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                visible: index < 5

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        text: labelText(modelData)
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                    Text {
                                        text: compactNumber(modelData.totalEvents || modelData.totalQuantity || 0)
                                        color: settingsController.accentColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 12
                                        font.bold: true
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 9
                                    radius: 5
                                    color: settingsController.controlColor

                                    Rectangle {
                                        width: parent.width * barRatio(modelData.totalEvents || modelData.totalQuantity || 0, barMax(categories, "totalEvents"))
                                        height: parent.height
                                        radius: 5
                                        color: settingsController.accentColor
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 300
                    radius: settingsController.cardRadius
                    color: settingsController.surfaceColor
                    border.color: settingsController.borderColor
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: tr("profile.top_actions")
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 18
                                font.bold: true
                                Layout.fillWidth: true
                            }
                            Text {
                                text: tr("profile.top_actions_hint")
                                color: settingsController.mutedTextColor
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                            }
                        }

                        Text {
                            visible: topActions.length === 0
                            text: tr("profile.no_data")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                        }

                        Repeater {
                            model: topActions

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                height: 38
                                visible: index < 5
                                radius: 8
                                color: index % 2 === 0 ? settingsController.backgroundColor : settingsController.controlColor
                                border.color: settingsController.borderColor

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 10

                                    Text {
                                        text: actionLabel(modelData)
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }

                                    Text {
                                        text: compactNumber(modelData.totalEvents || 0) + " / " + compactNumber(modelData.totalQuantity || 0)
                                        color: settingsController.successColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 12
                                        font.bold: true
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 340
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor
                border.width: 1
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: tr("profile.recent_logs")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                            Layout.fillWidth: true
                        }
                        Text {
                            text: tr("profile.recent_logs_hint")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                        }
                    }

                    Text {
                        visible: recentLogs.length === 0
                        text: tr("profile.no_data")
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 13
                    }

                    Repeater {
                        model: Math.min(recentLogs.length, 5)

                        delegate: Rectangle {
                            property var rowData: recentLogs[index] || {}
                            Layout.fillWidth: true
                            height: 36
                            radius: 8
                            color: index % 2 === 0 ? settingsController.backgroundColor : settingsController.controlColor
                            border.color: settingsController.borderColor

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10

                                Text {
                                    text: String(rowData.category || "-")
                                    color: settingsController.accentColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                    Layout.preferredWidth: 120
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: String(rowData.action || "-")
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: "x" + compactNumber(rowData.quantity || 1)
                                    color: settingsController.successColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                    Layout.preferredWidth: 54
                                    horizontalAlignment: Text.AlignRight
                                }
                                Text {
                                    text: formatRelative(rowData.occurredAt || rowData.createdAt)
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                    Layout.preferredWidth: 120
                                    horizontalAlignment: Text.AlignRight
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
