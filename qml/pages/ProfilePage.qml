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
            width: parent.width - 60
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.margins: 30
            spacing: 32

            // --- PREMIUM HEADER ---
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 180

                Rectangle {
                    id: headerBg
                    anchors.fill: parent
                    radius: 24
                    color: settingsController.surfaceColor
                    border.color: Qt.rgba(1, 1, 1, 0.04)
                    border.width: 1
                    clip: true

                    // --- ANIMATED AURORA BACKGROUND ---
                    Rectangle {
                        width: 300
                        height: 300
                        radius: 150
                        color: settingsController.accentColor
                        opacity: 0.15
                        x: parent.width * 0.1
                        y: -50

                        SequentialAnimation on x {
                            loops: Animation.Infinite
                            running: true
                            NumberAnimation { to: headerBg.width * 0.5; duration: 20000; easing.type: Easing.InOutSine }
                            NumberAnimation { to: headerBg.width * 0.1; duration: 20000; easing.type: Easing.InOutSine }
                        }
                        SequentialAnimation on y {
                            loops: Animation.Infinite
                            running: true
                            NumberAnimation { to: 50; duration: 15000; easing.type: Easing.InOutSine }
                            NumberAnimation { to: -50; duration: 15000; easing.type: Easing.InOutSine }
                        }
                    }

                    Rectangle {
                        width: 400
                        height: 400
                        radius: 200
                        color: settingsController.infoColor
                        opacity: 0.1
                        x: parent.width * 0.6
                        y: -100

                        SequentialAnimation on x {
                            loops: Animation.Infinite
                            running: true
                            NumberAnimation { to: headerBg.width * 0.3; duration: 25000; easing.type: Easing.InOutSine }
                            NumberAnimation { to: headerBg.width * 0.6; duration: 25000; easing.type: Easing.InOutSine }
                        }
                        SequentialAnimation on y {
                            loops: Animation.Infinite
                            running: true
                            NumberAnimation { to: 20; duration: 18000; easing.type: Easing.InOutSine }
                            NumberAnimation { to: -100; duration: 18000; easing.type: Easing.InOutSine }
                        }
                    }

                    // Glass frost overlay to soften the orbs
                    Rectangle {
                        anchors.fill: parent
                        color: settingsController.surfaceColor
                        opacity: 0.45
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 30
                        spacing: 24

                        // Avatar
                        Item {
                            width: 110
                            height: 110

                            // Animated Pulse Ring
                            Rectangle {
                                anchors.centerIn: parent
                                width: parent.width
                                height: parent.height
                                radius: width / 2
                                color: "transparent"
                                border.color: account.online ? settingsController.successColor : settingsController.accentColor
                                border.width: 2
                                opacity: 0.6

                                SequentialAnimation on scale {
                                    loops: Animation.Infinite
                                    running: true
                                    NumberAnimation { to: 1.15; duration: 2500; easing.type: Easing.InOutSine }
                                    NumberAnimation { to: 1.0; duration: 2500; easing.type: Easing.InOutSine }
                                }
                                SequentialAnimation on opacity {
                                    loops: Animation.Infinite
                                    running: true
                                    NumberAnimation { to: 0.0; duration: 2500; easing.type: Easing.InOutSine }
                                    NumberAnimation { to: 0.6; duration: 2500; easing.type: Easing.InOutSine }
                                }
                            }

                            // Main Avatar Border
                            Rectangle {
                                anchors.fill: parent
                                radius: width / 2
                                color: settingsController.controlColor
                                border.color: account.online ? settingsController.successColor : Qt.rgba(1, 1, 1, 0.1)
                                border.width: 3

                                Rectangle {
                                    id: avatarMask
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    radius: (width / 2)
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
                                    font.pixelSize: 42
                                    font.bold: true
                                }
                            }
                        }

                        // Info Column
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            spacing: 4

                            RowLayout {
                                spacing: 12
                                Text {
                                    text: profileName()
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 32
                                    font.bold: true
                                    elide: Text.ElideRight
                                    Layout.maximumWidth: 400
                                }
                                Rectangle {
                                    visible: String(account.role || "") !== ""
                                    height: 24
                                    width: roleText.implicitWidth + 20
                                    radius: 12
                                    color: settingsController.accentPanelColor
                                    border.color: settingsController.accentColor
                                    Text {
                                        id: roleText
                                        anchors.centerIn: parent
                                        text: String(account.role || "")
                                        color: settingsController.accentColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        font.bold: true
                                        font.letterSpacing: 1.2
                                    }
                                }
                            }

                            Text {
                                text: profileHandle()
                                color: settingsController.mutedTextColor
                                font.family: "Segoe UI"
                                font.pixelSize: 16
                            }

                            RowLayout {
                                Layout.topMargin: 8
                                spacing: 8
                                Repeater {
                                    model: [
                                        account.online ? tr("profile.online_now") : tr("profile.offline_now"),
                                        account.regiment || tr("profile.no_regiment"),
                                        account.panelAccessLevel !== undefined ? tr("profile.access_level") + ": " + account.panelAccessLevel : tr("profile.access_level_unknown")
                                    ].filter(function(item) { return String(item || "") !== "" })

                                    delegate: Rectangle {
                                        height: 26
                                        width: chipText.implicitWidth + 20
                                        radius: 13
                                        color: index === 0 && account.online ? settingsController.accentPanelColor : Qt.rgba(1, 1, 1, 0.05)
                                        border.color: index === 0 && account.online ? settingsController.successColor : Qt.rgba(1, 1, 1, 0.05)
                                        border.width: 1
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

                        Item { Layout.fillWidth: true }

                        // Actions
                        Column {
                            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                            width: 220
                            spacing: 12

                            Rectangle {
                                visible: canOpenAdminPanel()
                                width: parent.width
                                height: 42
                                radius: 21
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
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: appController.openAdminPanel(chatController.apiToken)
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: 42
                                radius: 21
                                color: logoutHover.containsMouse ? Qt.rgba(1, 0, 0, 0.1) : "transparent"
                                border.color: logoutHover.containsMouse ? settingsController.dangerColor : Qt.rgba(1, 1, 1, 0.15)
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: tr("profile.logout")
                                    color: logoutHover.containsMouse ? settingsController.dangerColor : settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 13
                                    font.bold: true
                                }
                                MouseArea {
                                    id: logoutHover
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        chatController.logout()
                                        appController.setCurrentPage("chat")
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // --- COMPACT STATS ROW ---
            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1000 ? 4 : 2
                columnSpacing: 24
                rowSpacing: 24

                MetricCard {
                    Layout.fillWidth: true
                    title: tr("profile.total_online")
                    value: formatTime(account.totalOnlineSeconds)
                    detail: tr("profile.last_presence").replace("{time}", formatRelative(account.lastPresenceAt || account.updatedAt))
                    accent: settingsController.accentColor
                }
                MetricCard {
                    Layout.fillWidth: true
                    title: tr("profile.account_age")
                    value: compactNumber(account.accountAgeDays || 0) + "d"
                    detail: tr("profile.created_at_short").replace("{date}", formatDate(account.createdAt))
                    accent: settingsController.infoColor
                }
                MetricCard {
                    Layout.fillWidth: true
                    title: tr("profile.metric_events")
                    value: compactNumber(actions.totalEvents || 0)
                    detail: tr("profile.period_label_" + selectedRange)
                    accent: settingsController.successColor
                }
                MetricCard {
                    Layout.fillWidth: true
                    title: tr("profile.messages")
                    value: compactNumber(counters.messages || 0)
                    detail: tr("profile.messages_detail").replace("{count}", compactNumber(counters.whisperMessages || 0))
                    accent: settingsController.warningColor
                }
            }

            // --- PERIOD SELECTOR ---
            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 10
                Layout.bottomMargin: 10
                
                Item { Layout.fillWidth: true } // spacer left
                
                Rectangle {
                    height: 44
                    implicitWidth: periodRow.implicitWidth + 8
                    radius: 22
                    color: Qt.rgba(0, 0, 0, 0.25)
                    border.color: Qt.rgba(1, 1, 1, 0.05)
                    border.width: 1

                    Row {
                        id: periodRow
                        anchors.centerIn: parent
                        spacing: 2

                        Repeater {
                            model: [
                                {key: "today", label: tr("profile.period_today")},
                                {key: "week", label: tr("profile.period_week")},
                                {key: "month", label: tr("profile.period_month")},
                                {key: "total", label: tr("profile.period_total")}
                            ]

                            delegate: Rectangle {
                                height: 36
                                width: 110
                                radius: 18
                                color: selectedRange === modelData.key ? settingsController.accentColor : "transparent"
                                
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    color: selectedRange === modelData.key ? settingsController.textInverseColor : settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 14
                                    font.bold: selectedRange === modelData.key
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: setRange(modelData.key)
                                }
                            }
                        }
                    }
                }
                
                Item { Layout.fillWidth: true } // spacer right
            }

            // --- DATA CHARTS ROW ---
            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 900 ? 2 : 1
                columnSpacing: 32
                rowSpacing: 32

                // Top Actions
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: 20

                    Text {
                        text: tr("profile.top_actions")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 20
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    Text {
                        visible: topActions.length === 0
                        text: tr("profile.no_data")
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 14
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        
                        Repeater {
                            model: topActions

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                height: 54
                                visible: index < 5
                                radius: 12
                                color: Qt.rgba(1, 1, 1, 0.04)
                                border.color: Qt.rgba(1, 1, 1, 0.03)
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 12

                                    Text {
                                        text: actionLabel(modelData)
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 14
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                    Text {
                                        text: compactNumber(modelData.totalEvents || 0)
                                        color: settingsController.successColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 15
                                        font.bold: true
                                    }
                                }
                            }
                        }
                    }
                }

                // Recent Logs
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: 20

                    Text {
                        text: tr("profile.recent_logs")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 20
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    Text {
                        visible: recentLogs.length === 0
                        text: tr("profile.no_data")
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 14
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: Math.min(recentLogs.length, 5)

                            delegate: Rectangle {
                                property var rowData: recentLogs[index] || {}
                                Layout.fillWidth: true
                                height: 54
                                radius: 12
                                color: Qt.rgba(1, 1, 1, 0.04)
                                border.color: Qt.rgba(1, 1, 1, 0.03)
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 12

                                    Text {
                                        text: String(rowData.category || "-")
                                        color: settingsController.accentColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        font.bold: true
                                        Layout.preferredWidth: 100
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        text: String(rowData.action || "-")
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        text: "x" + compactNumber(rowData.quantity || 1)
                                        color: settingsController.successColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        font.bold: true
                                        Layout.preferredWidth: 40
                                        horizontalAlignment: Text.AlignRight
                                    }
                                    Text {
                                        text: formatRelative(rowData.occurredAt || rowData.createdAt)
                                        color: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 12
                                        Layout.preferredWidth: 70
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

}
