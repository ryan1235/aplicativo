import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import Qt5Compat.GraphicalEffects
import "components"

ApplicationWindow {
    id: window
    width: 1180
    height: 720
    minimumWidth: 920
    minimumHeight: 600
    visible: true
    title: appController.appTitle
    color: "#070b16"
    flags: Qt.Window | Qt.FramelessWindowHint

    header: Rectangle {
        id: customTitleBar
        width: parent.width
        height: 32
        color: "#0a1020"
        z: 9999

        MouseArea {
            anchors.fill: parent
            onPressed: function(mouse) { window.startSystemMove() }
            onDoubleClicked: window.visibility === Window.Maximized ? window.showNormal() : window.showMaximized()
        }

        RowLayout {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            spacing: 8
            
            Text {
                text: window.title
                color: "#99abc4"
                font.family: "Segoe UI"
                font.pixelSize: 12
                font.bold: true
                Layout.alignment: Qt.AlignVCenter
            }
        }

        RowLayout {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            spacing: 0

            Button {
                Layout.preferredWidth: 46
                Layout.fillHeight: true
                background: Rectangle {
                    color: parent.hovered ? "#1d3353" : "transparent"
                }
                contentItem: Text {
                    text: "—"
                    color: "#edf6ff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: window.showMinimized()
            }

            Button {
                Layout.preferredWidth: 46
                Layout.fillHeight: true
                background: Rectangle {
                    color: parent.hovered ? "#1d3353" : "transparent"
                }
                contentItem: Text {
                    text: window.visibility === Window.Maximized ? "❐" : "☐"
                    color: "#edf6ff"
                    font.pixelSize: 14
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: window.visibility === Window.Maximized ? window.showNormal() : window.showMaximized()
            }

            Button {
                Layout.preferredWidth: 46
                Layout.fillHeight: true
                background: Rectangle {
                    color: parent.hovered ? "#e81123" : "transparent"
                }
                contentItem: Text {
                    text: "✕"
                    color: "#edf6ff"
                    font.pixelSize: 12
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: window.close()
            }
        }
    }

    property bool sidebarOpen: true
    property bool exiting: false
    property int interactiveOverlayFlags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus
    property int passiveOverlayFlags: interactiveOverlayFlags
    property int passthroughOverlayFlags: passiveOverlayFlags | Qt.WindowTransparentForInput

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    Component.onCompleted: chatController.autoConnectWithSavedDiscord()

    function pageSource(page) {
        if (page === "home") return "pages/HomePage.qml"
        if (page === "profile") return "pages/ProfilePage.qml"
        if (page === "profile") return "pages/ProfilePage.qml"
        if (page === "chat") return "pages/ChatPage.qml"
        if (page === "autoClicker") return "pages/AutoClickerPage.qml"
        if (page === "stockpile") return "pages/StockpilePage.qml"
        if (page === "itemSearch") return "pages/ItemSearchPage.qml"
        if (page === "identifyItem") return "pages/IdentifyItemPage.qml"
        if (page === "production") return "pages/ProductionPage.qml"
        if (page === "timeTask") return "pages/TimeTaskPage.qml"
        if (page === "notifications") return "pages/NotificationsPage.qml"
        if (page === "settings") return "pages/SettingsPage.qml"
        return "pages/HomePage.qml"
    }

    function hideToTray() {
        window.visible = false
        trayController.showMessage(appController.appTitle, tr("tray.running"))
    }

    function exitApplication() {
        window.exiting = true
        Qt.quit()
    }

    function handleCloseRequest() {
        var action = settingsController.closeAction
        if (action === "tray") {
            hideToTray()
        } else if (action === "exit") {
            exitApplication()
        } else {
            closeDialog.open()
        }
    }

    onClosing: function(close) {
        if (window.exiting) {
            close.accepted = true
            return
        }
        close.accepted = false
        handleCloseRequest()
    }

    Connections {
        target: trayController
        function onRestoreRequested() {
            window.visible = true
            window.raise()
            window.requestActivate()
        }
        function onQuitRequested() {
            exitApplication()
        }
        function onOpenFoxholeRequested() {
            appController.openFoxhole()
        }
        function onToggleAutoClickerRequested() {
            autoClickerController.toggle()
        }
        function onToggleMacroRequested() {
            if (timeTaskController.recording) {
                timeTaskController.stopRecording()
            } else {
                timeTaskController.startRecording()
            }
        }
    }

    Connections {
        target: appController
        function onCloseRequested() {
            window.close()
        }
    }

    Connections {
        target: timeTaskController
        function onRestoreAppRequested() {
            window.visible = true
            window.raise()
            window.requestActivate()
        }
    }

    Timer {
        interval: 700
        running: true
        repeat: false
        onTriggered: appController.runStartupPrompts()
    }

    Dialog {
        id: closeDialog
        modal: true
        width: Math.min(430, window.width - 48)
        x: Math.round((window.width - width) / 2)
        y: Math.round((window.height - height) / 2)
        closePolicy: Popup.CloseOnEscape
        title: tr("close.title")
        property bool rememberChoice: false

        background: Rectangle {
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
        }

        contentItem: ColumnLayout {
            spacing: 12
            Text {
                text: tr("close.heading")
                color: "#edf6ff"
                font.family: "Segoe UI"
                font.pixelSize: 19
                font.bold: true
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Text {
                text: tr("close.body")
                color: "#99abc4"
                font.family: "Segoe UI"
                font.pixelSize: 12
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                ToggleSwitch {
                    id: rememberCloseChoice
                    checked: closeDialog.rememberChoice
                    onClicked: closeDialog.rememberChoice = checked
                }
                Text {
                    text: tr("close.remember")
                    color: "#c7d7ed"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    verticalAlignment: Text.AlignVCenter
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }
        }

        footer: Item {
            implicitHeight: 58
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                anchors.bottomMargin: 18
                spacing: 10
                PrimaryButton {
                    text: tr("close.tray")
                    Layout.fillWidth: true
                    onClicked: {
                        if (closeDialog.rememberChoice)
                            settingsController.setCloseAction("tray")
                        closeDialog.close()
                        hideToTray()
                    }
                }
                PrimaryButton {
                    text: tr("close.exit")
                    Layout.fillWidth: true
                    fill: "#1d3353"
                    hoverFill: "#2d496f"
                    textFill: "#edf6ff"
                    onClicked: {
                        if (closeDialog.rememberChoice)
                            settingsController.setCloseAction("exit")
                        closeDialog.close()
                        exitApplication()
                    }
                }
            }
        }

        onClosed: {
            rememberChoice = false
            rememberCloseChoice.checked = false
        }
    }

    Dialog {
        id: startupDialog
        modal: true
        visible: appController.startupDialogVisible
        width: Math.min(620, window.width - 48)
        height: Math.min(appController.startupDialogImageUrl !== "" ? 600 : 460, window.height - 48)
        x: Math.round((window.width - width) / 2)
        y: Math.round((window.height - height) / 2)
        closePolicy: Popup.NoAutoClose
        title: ""

        background: Rectangle {
            radius: 16
            color: Qt.rgba(0.04, 0.08, 0.15, 0.97)
            border.color: appController.startupDialogKind === "error" ? "#ff6b6b" : "#2d6f8f"
            border.width: 1
            layer.enabled: true
            layer.effect: DropShadow {
                transparentBorder: true
                color: Qt.rgba(0, 0, 0, 0.62)
                radius: 30
                samples: 61
            }
        }

        contentItem: ColumnLayout {
            spacing: 14
            anchors.margins: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                Rectangle {
                    Layout.preferredWidth: appController.startupDialogImageUrl !== "" ? 86 : 0
                    Layout.preferredHeight: appController.startupDialogImageUrl !== "" ? 86 : 0
                    visible: appController.startupDialogImageUrl !== ""
                    radius: 18
                    color: "#071426"
                    border.color: "#24486d"
                    border.width: 1
                    clip: true

                    AnimatedImage {
                        id: startupDialogGif
                        anchors.fill: parent
                        anchors.margins: 5
                        source: appController.startupDialogImageUrl
                        fillMode: Image.PreserveAspectCrop
                        layer.enabled: true
                        layer.effect: OpacityMask {
                            maskSource: Rectangle {
                                width: startupDialogGif.width
                                height: startupDialogGif.height
                                radius: 14
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Text {
                        text: appController.startupDialogTitle
                        color: appController.startupDialogKind === "error" ? "#ff6b6b" : "#5eead4"
                        font.family: "Segoe UI"
                        font.pixelSize: 24
                        font.bold: true
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        text: appController.startupDialogSubtitle
                        visible: text !== ""
                        color: "#8ab4ff"
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        font.bold: true
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                }
            }

            TextArea {
                Layout.fillWidth: true
                Layout.fillHeight: true
                text: appController.startupDialogBody
                textFormat: TextEdit.MarkdownText
                readOnly: true
                selectByMouse: true
                color: "#edf6ff"
                font.family: "Segoe UI"
                font.pixelSize: 13
                wrapMode: TextArea.Wrap
                background: Rectangle {
                    radius: 8
                    color: "#07111f"
                    border.color: "#27587d"
                    border.width: 1
                }
            }
        }

        footer: Item {
            implicitHeight: 66
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                anchors.bottomMargin: 22
                Item { Layout.fillWidth: true }
                PrimaryButton {
                    text: tr("release.ok")
                    Layout.preferredWidth: 140
                    Layout.preferredHeight: 38
                    fill: "#5eead4"
                    hoverFill: "#2dd4bf"
                    textFill: "#022c22"
                    onClicked: appController.acceptStartupDialog()
                }
            }
        }
    }

    Dialog {
        id: updateOfferDialog
        modal: true
        visible: updateController.offerVisible
        width: Math.min(680, window.width - 48)
        height: Math.min(600, window.height - 48)
        x: Math.round((window.width - width) / 2)
        y: Math.round((window.height - height) / 2)
        closePolicy: Popup.NoAutoClose

        background: Rectangle {
            radius: 16
            color: Qt.rgba(0.04, 0.08, 0.15, 0.96)
            border.color: "#5eead4"
            border.width: 1
            layer.enabled: true
            layer.effect: DropShadow {
                transparentBorder: true
                color: Qt.rgba(0, 0, 0, 0.6)
                radius: 32
                samples: 65
            }
        }

        contentItem: ColumnLayout {
            spacing: 16
            anchors.margins: 8

            RowLayout {
                spacing: 14
                Rectangle {
                    Layout.preferredWidth: 58
                    Layout.preferredHeight: 58
                    radius: 12
                    color: "#071426"
                    border.color: "#24486d"
                    clip: true
                    AnimatedImage {
                        anchors.fill: parent
                        anchors.margins: 4
                        source: appController.assetUrl("img/ggimege.gif")
                        fillMode: Image.PreserveAspectCrop
                    }
                }
                ColumnLayout {
                    spacing: 4
                    Layout.fillWidth: true
                    Text {
                        text: tr("update.available_title")
                        color: "#5eead4"
                        font.family: "Segoe UI"
                        font.pixelSize: 22
                        font.bold: true
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        text: updateController.updateName + " - " + updateController.updateAssetName
                        color: "#8ab4ff"
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }
            }

            Text {
                text: updateController.updateAvailableBody
                color: "#a4b9d6"
                font.family: "Segoe UI"
                font.pixelSize: 14
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: updateNoticeText.implicitHeight + 24
                radius: 10
                color: Qt.rgba(0.06, 0.12, 0.20, 0.6)
                border.color: "#24486d"
                border.width: 1

                Text {
                    id: updateNoticeText
                    anchors.fill: parent
                    anchors.margins: 12
                    text: tr("update.offer_notice")
                    color: "#a4b9d6"
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    lineHeight: 1.4
                    wrapMode: Text.WordWrap
                    verticalAlignment: Text.AlignVCenter
                }
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                
                background: Rectangle {
                    radius: 10
                    color: Qt.rgba(0.04, 0.06, 0.1, 0.8)
                    border.color: "#1e3554"
                    border.width: 1
                }

                TextArea {
                    text: updateController.updateBody
                    textFormat: TextEdit.MarkdownText
                    readOnly: true
                    selectByMouse: true
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 14
                    wrapMode: TextArea.Wrap
                    topPadding: 16
                    bottomPadding: 16
                    leftPadding: 16
                    rightPadding: 16
                    background: Item {}
                }
            }
        }

        footer: Item {
            implicitHeight: 64
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                anchors.bottomMargin: 24
                spacing: 12
                PrimaryButton {
                    text: tr("update.later")
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    fill: "#111c31"
                    hoverFill: "#1d3353"
                    textFill: "#99abc4"
                    onClicked: updateController.dismissOffer()
                }
                PrimaryButton {
                    text: tr("update.install_now")
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    fill: "#5eead4"
                    hoverFill: "#2dd4bf"
                    textFill: "#022c22"
                    onClicked: updateController.installAvailableUpdate()
                }
            }
        }
    }

    Dialog {
        id: updateProgressDialog
        modal: true
        visible: updateController.progressVisible
        width: Math.min(580, window.width - 48)
        x: Math.round((window.width - width) / 2)
        y: Math.round((window.height - height) / 2)
        closePolicy: Popup.NoAutoClose

        background: Rectangle {
            radius: 16
            color: Qt.rgba(0.04, 0.08, 0.15, 0.96)
            border.color: updateController.progressAccent
            border.width: 1
            layer.enabled: true
            layer.effect: DropShadow {
                transparentBorder: true
                color: Qt.rgba(0, 0, 0, 0.6)
                radius: 32
                samples: 65
            }
        }

        contentItem: ColumnLayout {
            spacing: 18
            anchors.margins: 12

            RowLayout {
                spacing: 14
                Item {
                    Layout.preferredWidth: 58
                    Layout.preferredHeight: 58

                    Rectangle {
                        anchors.centerIn: parent
                        width: 58
                        height: 58
                        radius: 29
                        color: "#071426"
                        border.color: updateController.progressAccent
                        border.width: 1
                    }

                    Rectangle {
                        anchors.centerIn: parent
                        width: 14
                        height: 14
                        radius: 7
                        color: updateController.progressAccent

                        SequentialAnimation on opacity {
                            loops: Animation.Infinite
                            running: updateController.progressVisible
                            NumberAnimation { from: 0.25; to: 1; duration: 700; easing.type: Easing.InOutSine }
                            NumberAnimation { from: 1; to: 0.25; duration: 700; easing.type: Easing.InOutSine }
                        }
                    }
                }
                ColumnLayout {
                    spacing: 4
                    Layout.fillWidth: true
                    Text {
                        text: tr("update.progress_title")
                        color: "#edf6ff"
                        font.family: "Segoe UI"
                        font.pixelSize: 20
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Text {
                        text: updateController.progressText
                        color: "#a4b9d6"
                        font.family: "Segoe UI"
                        font.pixelSize: 14
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                    Rectangle {
                        Layout.preferredHeight: 24
                        Layout.preferredWidth: updatePhaseText.implicitWidth + 22
                        radius: 12
                        color: Qt.rgba(1, 1, 1, 0.04)
                        border.color: updateController.progressAccent
                        border.width: 1
                        Text {
                            id: updatePhaseText
                            anchors.centerIn: parent
                            text: tr(updateController.progressPhaseKey)
                            color: updateController.progressAccent
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }
                }
            }

            Rectangle {
                visible: updateController.restarting
                Layout.fillWidth: true
                Layout.preferredHeight: restartNoticeLayout.implicitHeight + 32
                radius: 12
                color: Qt.rgba(0.18, 0.12, 0.04, 0.4)
                border.color: Qt.rgba(1.0, 0.75, 0.2, 0.3)
                border.width: 1

                RowLayout {
                    id: restartNoticeLayout
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 16
                    Text {
                        text: updateController.restartCountdown
                        color: "#ffd166"
                        font.family: "Segoe UI"
                        font.pixelSize: 42
                        font.bold: true
                        Layout.preferredWidth: 52
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Text {
                        text: tr("update.restart_notice")
                        color: "#fef3c7"
                        font.family: "Segoe UI"
                        font.pixelSize: 15
                        lineHeight: 1.4
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            ProgressBar {
                Layout.fillWidth: true
                value: updateController.progressValue / 100
                background: Rectangle {
                    implicitHeight: 18
                    radius: 9
                    color: "#070b16"
                    border.color: "#1e3554"
                    border.width: 1
                }
                contentItem: Item {
                    implicitHeight: 18
                    Rectangle {
                        width: parent.width * (updateController.progressValue / 100)
                        height: parent.height
                        radius: 9
                        color: updateController.progressAccent
                        Behavior on width { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: updateController.progressDetail
                    color: "#8ab4ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                Text {
                    text: updateController.progressValue + "%"
                    color: updateController.progressAccent
                    font.family: "Segoe UI"
                    font.pixelSize: 16
                    font.bold: true
                }
            }
        }
    }

    Dialog {
        id: updateErrorDialog
        modal: true
        visible: updateController.errorVisible
        width: Math.min(500, window.width - 48)
        x: Math.round((window.width - width) / 2)
        y: Math.round((window.height - height) / 2)
        closePolicy: Popup.CloseOnEscape
        onRejected: updateController.dismissError()

        background: Rectangle {
            radius: 16
            color: Qt.rgba(0.04, 0.08, 0.15, 0.96)
            border.color: "#ff3366"
            border.width: 1
            layer.enabled: true
            layer.effect: DropShadow {
                transparentBorder: true
                color: Qt.rgba(0, 0, 0, 0.6)
                radius: 32
                samples: 65
            }
        }

        contentItem: ColumnLayout {
            spacing: 12
            anchors.margins: 12

            Text {
                text: tr("update.error_title")
                color: "#ff3366"
                font.family: "Segoe UI"
                font.pixelSize: 20
                font.bold: true
                Layout.fillWidth: true
            }

            TextArea {
                id: updateErrorText
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(180, Math.max(96, contentHeight + 24))
                text: updateController.errorText
                textFormat: TextEdit.PlainText
                readOnly: true
                selectByMouse: true
                color: "#edf6ff"
                font.family: "Segoe UI"
                font.pixelSize: 13
                wrapMode: TextArea.Wrap
                background: Rectangle {
                    radius: 8
                    color: "#07111f"
                    border.color: "#4b1d31"
                    border.width: 1
                }
            }
        }

        footer: Item {
            implicitHeight: 64
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                anchors.bottomMargin: 24
                Item { Layout.fillWidth: true }
                PrimaryButton {
                    text: tr("release.ok")
                    Layout.preferredWidth: 128
                    Layout.preferredHeight: 40
                    fill: "#ff3366"
                    hoverFill: "#e62e5c"
                    textFill: "#ffffff"
                    onClicked: updateController.dismissError()
                }
            }
        }
    }

    Dialog {
        id: tutorialDialog
        modal: true
        visible: appController.tutorialDialogVisible
        width: Math.min(600, window.width - 48)
        height: Math.min(560, window.height - 48)
        x: Math.round((window.width - width) / 2)
        y: Math.round((window.height - height) / 2)
        title: appController.tutorialDialogTitle
        closePolicy: Popup.CloseOnEscape
        onRejected: appController.dismissTutorial()

        background: Rectangle {
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
        }

        contentItem: ColumnLayout {
            spacing: 12
            Text {
                text: appController.tutorialDialogTitle
                color: "#edf6ff"
                font.family: "Segoe UI"
                font.pixelSize: 19
                font.bold: true
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            TextArea {
                Layout.fillWidth: true
                Layout.fillHeight: true
                text: appController.tutorialDialogBody
                textFormat: TextEdit.MarkdownText
                readOnly: true
                selectByMouse: true
                color: "#edf6ff"
                font.family: "Segoe UI"
                font.pixelSize: 12
                wrapMode: TextArea.Wrap
                background: Rectangle {
                    radius: 7
                    color: "#07111f"
                    border.color: "#24486d"
                }
            }
        }

        footer: Item {
            implicitHeight: 58
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                anchors.bottomMargin: 18
                Item { Layout.fillWidth: true }
                PrimaryButton {
                    text: tr("release.ok")
                    Layout.preferredWidth: 128
                    onClicked: appController.dismissTutorial()
                }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#070b16"

        RowLayout {
            id: mainLayout
            anchors.fill: parent
            spacing: 0

            Rectangle {
                id: sidebar
                Layout.fillHeight: true
                Layout.preferredWidth: window.sidebarOpen ? 286 : 72
                color: "#0a1020"
                clip: true
                Behavior on Layout.preferredWidth { NumberAnimation { duration: 190; easing.type: Easing.OutCubic } }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 54
                        spacing: 10

                        Rectangle {
                            Layout.preferredWidth: 44
                            Layout.preferredHeight: 44
                            radius: 8
                            color: "#111c31"
                            AnimatedImage {
                                anchors.centerIn: parent
                                width: 36
                                height: 36
                                source: appController.assetUrl("img/ggimege.gif")
                                playing: window.visible
                                fillMode: Image.PreserveAspectFit
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: window.sidebarOpen
                            opacity: window.sidebarOpen ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: 120 } }
                            Text {
                                text: appController.appTitle
                                color: "#edf6ff"
                                font.family: "Segoe UI"
                                font.pixelSize: 17
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            Text {
                                text: tr("app.subtitle")
                                color: "#99abc4"
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: window.sidebarOpen ? 86 : 54
                        radius: 8
                        color: profileMouseArea.containsMouse ? "#172943" : "#0e1a2d"
                        border.color: "#1e3554"
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: 150 } }
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 160 } }

                        MouseArea {
                            id: profileMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                if (chatController.currentProvider === "discord") {
                                    appController.setCurrentPage("profile")
                                } else {
                                    chatController.connectWithDiscord()
                                }
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: window.sidebarOpen ? 12 : 0
                            spacing: window.sidebarOpen ? 12 : 0

                            Item {
                                Layout.preferredWidth: window.sidebarOpen ? 42 : parent.width
                                Layout.fillWidth: !window.sidebarOpen
                                Layout.fillHeight: true

                                Rectangle {
                                    width: 42
                                    height: 42
                                    anchors.centerIn: parent
                                    radius: 21
                                    color: "#1d3353"

                                    Image {
                                        id: profileImage
                                        anchors.fill: parent
                                        source: chatController.currentUserAvatar
                                        fillMode: Image.PreserveAspectCrop
                                        visible: chatController.currentUserAvatar !== ""
                                        layer.enabled: true
                                        layer.effect: OpacityMask {
                                            maskSource: Rectangle {
                                                width: profileImage.width
                                                height: profileImage.height
                                                radius: width / 2
                                            }
                                        }
                                    }
                                    Text {
                                        anchors.centerIn: parent
                                        text: chatController.currentUserName !== "" ? chatController.currentUserName.charAt(0).toUpperCase() : "GG"
                                        visible: chatController.currentUserAvatar === ""
                                        color: "#5eead4"
                                        font.bold: true
                                    }
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                visible: window.sidebarOpen
                                opacity: window.sidebarOpen ? 1 : 0
                                spacing: 2
                                Behavior on opacity { NumberAnimation { duration: 120 } }

                                Text {
                                    text: {
                                        var p = chatController.userProfile;
                                        var reg = (p && p.regiment) ? "[" + p.regiment + "] " : "";
                                        return reg + (chatController.currentUserName || "Usuário");
                                    }
                                    color: "#edf6ff"
                                    font.family: "Segoe UI"
                                    font.bold: true
                                    font.pixelSize: 14
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                RowLayout {
                                    spacing: 4
                                    Layout.fillWidth: true
                                    Rectangle {
                                        width: 8
                                        height: 8
                                        radius: 4
                                        color: chatController.currentProvider === "discord" ? "#5865F2" : "#5eead4"
                                    }
                                    Text {
                                        text: chatController.currentProvider === "discord" ? "Discord Online" : steamController.status
                                        color: "#99abc4"
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }

                    ListView {
                        id: navList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: navItems
                        clip: true
                        spacing: 6
                        delegate: Rectangle {
                            id: navRow
                            width: navList.width
                            height: 48
                            radius: 8
                            color: appController.currentPage === key ? "#1d3353" : mouse.containsMouse ? "#172943" : "transparent"
                            border.color: appController.currentPage === key ? "#2d496f" : "transparent"
                            Behavior on color { ColorAnimation { duration: 130 } }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: window.sidebarOpen ? 12 : 0
                                anchors.rightMargin: window.sidebarOpen ? 12 : 0
                                spacing: window.sidebarOpen ? 12 : 0

                                Item {
                                    visible: !window.sidebarOpen
                                    Layout.fillWidth: true
                                }

                                Image {
                                    id: menuIcon
                                    source: {
                                        var map = {
                                            "home": "home.png",
                                            "user": "generic.png",
                                            "chat": "aovivo.png",
                                            "bolt": "autoclicker.png",
                                            "timer": "generic.png",
                                            "database": "estoque.png",
                                            "factory": "calculadora.png",
                                            "search": "buscar.png",
                                            "target": "buscariten.png",
                                            "bell": "notificação.png",
                                            "settings": "config.png"
                                        }
                                        return map[icon] ? appController.assetUrl("img/iconmenu/" + map[icon]) : ""
                                    }
                                    visible: source != ""
                                    Layout.preferredWidth: 32
                                    Layout.preferredHeight: 32
                                    Layout.alignment: Qt.AlignVCenter
                                    fillMode: Image.PreserveAspectFit
                                    mipmap: true
                                    smooth: true
                                }
                                Text {
                                    text: icon.length > 0 ? icon.substring(0, 1).toUpperCase() : "-"
                                    color: appController.currentPage === key ? "#5eead4" : "#8ab4ff"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 14
                                    font.bold: true
                                    Layout.preferredWidth: 24
                                    horizontalAlignment: Text.AlignHCenter
                                    visible: menuIcon.source == ""
                                }
                                Item {
                                    visible: !window.sidebarOpen
                                    Layout.fillWidth: true
                                }
                                Text {
                                    text: tr(labelKey)
                                    color: appController.currentPage === key ? "#edf6ff" : "#99abc4"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 13
                                    font.bold: appController.currentPage === key
                                    visible: window.sidebarOpen
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: mouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: appController.setCurrentPage(key)
                            }
                        }
                    }

                    Text {
                        text: "v" + appController.version
                        color: "#60728c"
                        font.family: "Segoe UI"
                        font.pixelSize: 11
                        horizontalAlignment: Text.AlignHCenter
                        Layout.fillWidth: true
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 72
                    color: "#070b16"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 22
                        anchors.rightMargin: 22
                        spacing: 12

                        PrimaryButton {
                            text: window.sidebarOpen ? "<" : ">"
                            fill: "#111c31"
                            hoverFill: "#1d3353"
                            textFill: "#edf6ff"
                            onClicked: window.sidebarOpen = !window.sidebarOpen
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: tr(navTitleKey())
                                color: "#edf6ff"
                                font.family: "Segoe UI"
                                font.pixelSize: 20
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            Text {
                                text: appController.foxholeStatus
                                color: "#99abc4"
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }

                        PrimaryButton {
                            text: "?"
                            visible: appController.hasTutorial
                            Layout.preferredWidth: 42
                            fill: "#111c31"
                            hoverFill: "#1d3353"
                            textFill: "#5eead4"
                            onClicked: appController.showTutorial()
                            ToolTip.visible: hovered
                            ToolTip.text: tr("tutorial.help")
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#070b16"

                    Loader {
                        id: pageLoader
                        anchors.fill: parent
                        anchors.margins: 22
                        source: pageSource(appController.currentPage)
                        asynchronous: true
                        opacity: status === Loader.Ready ? 1 : 0
                        visible: opacity > 0
                        Behavior on opacity { NumberAnimation { duration: 170; easing.type: Easing.OutCubic } }
                    }
                }
        }
        }

        // Discord Login Overlay
        Item {
            id: discordLoginOverlay
            anchors.fill: parent
            z: 9999
            visible: chatController.profileGateVisible
            property bool awaitingDiscordLogin: chatController.discordOAuthInFlight
            property bool validatingProfile: !awaitingDiscordLogin && (chatController.authInFlight || chatController.profileLoading)
            property bool waitingForProfile: awaitingDiscordLogin || validatingProfile
            property bool loginHasError: chatController.authErrorVisible
            property bool accessDenied: chatController.authDenied
            property bool profileNeedsRetry: (loginHasError || (chatController.connected && !chatController.profileReady)) && !waitingForProfile

            MouseArea {
                anchors.fill: parent
                hoverEnabled: true // Block all mouse events behind it
                onWheel: function(wheel) { wheel.accepted = true; } // Block scroll
            }

            FastBlur {
                anchors.fill: parent
                source: mainLayout
                radius: 56
                transparentBorder: false
            }

            Rectangle {
                anchors.fill: parent
                color: "#040810"
                opacity: 0.40 // Make it very transparent to see the blur
            }

            Rectangle {
                anchors.centerIn: parent
                width: Math.min(500, parent.width - 48)
                height: Math.min(520, parent.height - 64)
                radius: 18
                color: Qt.rgba(0.045, 0.08, 0.14, 0.94)
                border.color: discordLoginOverlay.accessDenied ? "#ff3366" : (discordLoginOverlay.awaitingDiscordLogin ? "#5865F2" : "#1e3554")
                border.width: 1

                layer.enabled: true
                layer.effect: DropShadow {
                    transparentBorder: true
                    color: Qt.rgba(0, 0, 0, 0.6)
                    radius: 20
                    samples: 41
                    verticalOffset: 6
                }

                Behavior on border.color { ColorAnimation { duration: 220 } }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 34
                    spacing: 18

                    Item {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: 132
                        Layout.preferredHeight: 132

                        Rectangle {
                            anchors.centerIn: parent
                            width: 126
                            height: 126
                            radius: 63
                            color: "transparent"
                            border.color: discordLoginOverlay.accessDenied ? "#ff3366" : (discordLoginOverlay.awaitingDiscordLogin ? "#5865F2" : "#2d496f")
                            border.width: 2
                            opacity: 0.85
                        }

                        Item {
                            id: orbitRing
                            anchors.centerIn: parent
                            width: 126
                            height: 126
                            visible: discordLoginOverlay.waitingForProfile

                            RotationAnimation on rotation {
                                loops: Animation.Infinite
                                running: orbitRing.visible
                                from: 0
                                to: 360
                                duration: 2400
                                easing.type: Easing.Linear
                            }

                            Rectangle {
                                x: parent.width - 10
                                y: parent.height / 2 - 5
                                width: 10
                                height: 10
                                radius: 5
                                color: "#8ab4ff"
                            }

                            Rectangle {
                                x: -5
                                y: parent.height / 2 - 5
                                width: 10
                                height: 10
                                radius: 5
                                color: "#edf6ff"
                            }
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            width: 94
                            height: 94
                            radius: 47
                            color: "#071426"
                            opacity: 0.55
                            layer.enabled: true
                            layer.effect: DropShadow {
                                transparentBorder: true
                                color: discordLoginOverlay.accessDenied ? Qt.rgba(1, 0.2, 0.4, 0.55) : Qt.rgba(0.368, 0.917, 0.831, 0.5)
                                radius: 20
                                samples: 41
                                spread: 0.12
                            }
                        }

                        Rectangle {
                            id: floatingLogo
                            anchors.centerIn: parent
                            width: 92
                            height: 92
                            radius: 46
                            color: "#040810"
                            border.color: "#2d496f"
                            border.width: 1
                            clip: true

                            SequentialAnimation on anchors.verticalCenterOffset {
                                loops: Animation.Infinite
                                running: discordLoginOverlay.visible
                                NumberAnimation { from: 0; to: -8; duration: 1600; easing.type: Easing.InOutSine }
                                NumberAnimation { from: -8; to: 0; duration: 1600; easing.type: Easing.InOutSine }
                            }

                            AnimatedImage {
                                id: floatingLogoGif
                                anchors.fill: parent
                                anchors.margins: 6
                                source: appController.assetUrl("img/ggimege.gif")
                                fillMode: Image.PreserveAspectCrop
                                playing: discordLoginOverlay.visible
                                layer.enabled: true
                                layer.effect: OpacityMask {
                                    maskSource: Rectangle {
                                        width: floatingLogoGif.width
                                        height: floatingLogoGif.height
                                        radius: 38
                                    }
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        spacing: 9
                        Layout.alignment: Qt.AlignHCenter
                        Layout.fillWidth: true

                        Text {
                            text: discordLoginOverlay.accessDenied ? tr("loading.access_denied_title") : (discordLoginOverlay.awaitingDiscordLogin ? tr("loading.discord_wait_title") : (discordLoginOverlay.validatingProfile ? tr("loading.profile_title") : (discordLoginOverlay.profileNeedsRetry ? tr("loading.profile_retry_title") : tr("loading.discord_title"))))
                            color: discordLoginOverlay.accessDenied ? "#ff6b8a" : "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 27
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            Layout.preferredWidth: parent.width
                            Layout.fillWidth: true
                        }
                        Text {
                            text: discordLoginOverlay.accessDenied ? tr("loading.access_denied_body") : (discordLoginOverlay.awaitingDiscordLogin ? tr("loading.discord_wait_body") : (discordLoginOverlay.validatingProfile ? (chatController.status || tr("loading.profile_body")) : (discordLoginOverlay.profileNeedsRetry ? (chatController.status || tr("loading.profile_retry_body")) : tr("loading.discord_body"))))
                            color: discordLoginOverlay.accessDenied ? "#ffc0cb" : "#99abc4"
                            font.family: "Segoe UI"
                            font.pixelSize: 15
                            lineHeight: 1.4
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            Layout.preferredWidth: parent.width
                            Layout.fillWidth: true
                        }
                    }

                    Rectangle {
                        visible: discordLoginOverlay.waitingForProfile
                        Layout.fillWidth: true
                        Layout.preferredHeight: 76
                        radius: 10
                        color: Qt.rgba(0.06, 0.11, 0.19, 0.88)
                        border.color: "#223b5d"
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 12

                            Repeater {
                                model: [
                                    { "label": tr("loading.step_browser"), "active": discordLoginOverlay.awaitingDiscordLogin, "done": discordLoginOverlay.validatingProfile },
                                    { "label": tr("loading.step_verify"), "active": discordLoginOverlay.validatingProfile, "done": false },
                                    { "label": tr("loading.step_unlock"), "active": false, "done": false }
                                ]

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 7

                                    Rectangle {
                                        Layout.preferredWidth: 9
                                        Layout.preferredHeight: 9
                                        radius: 5
                                        color: modelData.active ? "#5eead4" : (modelData.done ? "#8ab4ff" : "#334761")
                                        opacity: modelData.active ? 1 : 0.68

                                        SequentialAnimation on opacity {
                                            loops: Animation.Infinite
                                            running: modelData.active
                                            NumberAnimation { from: 0.45; to: 1; duration: 560; easing.type: Easing.InOutSine }
                                            NumberAnimation { from: 1; to: 0.45; duration: 560; easing.type: Easing.InOutSine }
                                        }
                                    }

                                    Text {
                                        text: modelData.label
                                        color: modelData.active ? "#edf6ff" : "#7f93ad"
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        font.bold: modelData.active
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        visible: discordLoginOverlay.waitingForProfile || discordLoginOverlay.accessDenied
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(86, loginHelpText.implicitHeight + 28)
                        radius: 10
                        color: discordLoginOverlay.accessDenied ? Qt.rgba(0.20, 0.05, 0.10, 0.92) : Qt.rgba(0.035, 0.075, 0.13, 0.9)
                        border.color: discordLoginOverlay.accessDenied ? "#ff3366" : "#1d3353"
                        border.width: 1

                        Text {
                            id: loginHelpText
                            anchors.fill: parent
                            anchors.margins: 14
                            text: discordLoginOverlay.accessDenied ? tr("loading.access_denied_help") : (discordLoginOverlay.awaitingDiscordLogin ? tr("loading.discord_wait_help") : tr("loading.profile_verify_help"))
                            color: discordLoginOverlay.accessDenied ? "#ffd6df" : "#93a9c4"
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            lineHeight: 1.32
                            horizontalAlignment: Text.AlignLeft
                            verticalAlignment: Text.AlignVCenter
                            wrapMode: Text.WordWrap
                        }
                    }

                    Item { Layout.fillHeight: true }

                    PrimaryButton {
                        visible: !discordLoginOverlay.waitingForProfile
                        text: discordLoginOverlay.profileNeedsRetry ? tr("loading.retry") : tr("loading.login_discord")
                        fill: discordLoginOverlay.accessDenied ? "#ff3366" : "#5865F2"
                        hoverFill: discordLoginOverlay.accessDenied ? "#e62e5c" : "#4752C4"
                        textFill: "#ffffff"
                        enabled: visible
                        Layout.preferredHeight: 52
                        Layout.fillWidth: true
                        font.pixelSize: 16
                        font.bold: true
                        onClicked: chatController.connectWithDiscord()
                    }
                }
            }
        }
    }

    Window {
        id: overlayWindow
        width: 260
        height: Math.max(78, overlayContent.implicitHeight + 20)
        visible: overlayController.visible
        color: "transparent"
        transientParent: null
        flags: window.interactiveOverlayFlags
        property real dragStartX: 0
        property real dragStartY: 0
        property bool dragging: false
        property bool systemMoving: false

        function clampToScreen() {
            var screenWidth = Screen.width > 0 ? Screen.width : 1920
            var screenHeight = Screen.height > 0 ? Screen.height : 1080
            x = Math.max(8, Math.min(x, screenWidth - width - 8))
            y = Math.max(8, Math.min(y, screenHeight - height - 8))
        }

        function placeFromSettings() {
            var screenWidth = Screen.width > 0 ? Screen.width : 1920
            if (overlayController.panelX >= 0 && overlayController.panelY >= 0) {
                x = overlayController.panelX
                y = overlayController.panelY
            } else {
                x = screenWidth - width - 28
                y = 120
            }
            clampToScreen()
        }

        Component.onCompleted: placeFromSettings()
        onVisibleChanged: if (visible) placeFromSettings()

        Rectangle {
            id: overlayPanel
            anchors.fill: parent
            radius: 8
            color: overlayController.backgroundColor
            border.color: overlayController.accentColor
            border.width: 1
            opacity: 0.94
            Behavior on color { ColorAnimation { duration: 160 } }
            Behavior on border.color { ColorAnimation { duration: 160 } }

            MouseArea {
                anchors.fill: parent
                onPressed: function(mouse) {
                    overlayWindow.dragging = true
                    overlayWindow.systemMoving = overlayWindow.startSystemMove()
                    overlayWindow.dragStartX = mouse.x
                    overlayWindow.dragStartY = mouse.y
                }
                onPositionChanged: function(mouse) {
                    if (!overlayWindow.dragging || overlayWindow.systemMoving)
                        return
                    overlayWindow.x = Math.round(overlayWindow.x + mouse.x - overlayWindow.dragStartX)
                    overlayWindow.y = Math.round(overlayWindow.y + mouse.y - overlayWindow.dragStartY)
                    overlayWindow.clampToScreen()
                }
                onReleased: {
                    overlayWindow.dragging = false
                    overlayWindow.systemMoving = false
                    overlayController.savePanelPosition(Math.round(overlayWindow.x), Math.round(overlayWindow.y))
                }
            }

            ColumnLayout {
                id: overlayContent
                anchors.fill: parent
                anchors.margins: 10
                spacing: 5

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Text {
                        text: autoClickerController.active ? tr("overlay.clicker_active") : tr("overlay.clicker_paused")
                        color: autoClickerController.active ? "#62d7a4" : "#ffd166"
                        font.family: "Segoe UI"
                        font.pixelSize: 11
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Button {
                        Layout.preferredWidth: 24
                        Layout.preferredHeight: 22
                        text: "X"
                        onClicked: overlayController.setEnabled(false)
                        contentItem: Text {
                            text: parent.text
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 10
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            radius: 5
                            color: parent.hovered ? "#5f2034" : "#431926"
                        }
                    }
                }

                Text {
                    visible: overlayController.showProfile
                    text: steamController.personaName !== "" ? steamController.personaName : tr("user.unknown")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                Text {
                    visible: overlayController.showClicker
                    text: autoClickerController.overlayPrimaryText
                    color: "#c7d7ed"
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                    font.bold: autoClickerController.active
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    visible: overlayController.showClicker && autoClickerController.overlayHintText !== ""
                    text: autoClickerController.overlayHintText
                    color: "#7f93ad"
                    font.family: "Segoe UI"
                    font.pixelSize: 10
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    visible: overlayController.showTarget
                    text: autoClickerController.targetTitle !== "" ? autoClickerController.targetTitle : tr("overlay.target_default")
                    color: overlayController.accentColor
                    font.family: "Segoe UI"
                    font.pixelSize: 10
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }
        }
    }

    Window {
        id: squadlockOverlayWindow
        width: 148
        height: notificationsController.squadlockFinished ? 118 : 82
        visible: notificationsController.overlayVisible
        color: "transparent"
        transientParent: null
        flags: window.interactiveOverlayFlags

        property real dragStartX: 0
        property real dragStartY: 0
        property bool dragging: false
        property bool systemMoving: false

        function clampToScreen() {
            var screenWidth = Screen.width > 0 ? Screen.width : 1920
            var screenHeight = Screen.height > 0 ? Screen.height : 1080
            x = Math.max(8, Math.min(x, screenWidth - width - 8))
            y = Math.max(8, Math.min(y, screenHeight - height - 8))
        }

        function placeFromSettings() {
            var screenWidth = Screen.width > 0 ? Screen.width : 1920
            x = notificationsController.overlayX >= 0 ? notificationsController.overlayX : screenWidth - width - 24
            y = notificationsController.overlayY >= 0 ? notificationsController.overlayY : 222
            clampToScreen()
        }

        Component.onCompleted: placeFromSettings()
        onVisibleChanged: if (visible) placeFromSettings()
        onHeightChanged: if (visible) clampToScreen()

        Rectangle {
            anchors.fill: parent
            anchors.margins: 3
            radius: 8
            color: "#0d1828"
            border.color: notificationsController.squadlockFinished ? "#62d7a4" : "#39506f"
            border.width: 1
            opacity: 0.96

            MouseArea {
                anchors.fill: parent
                onPressed: function(mouse) {
                    squadlockOverlayWindow.dragStartX = mouse.x
                    squadlockOverlayWindow.dragStartY = mouse.y
                    squadlockOverlayWindow.dragging = true
                    squadlockOverlayWindow.systemMoving = squadlockOverlayWindow.startSystemMove()
                    notificationsController.holdOverlayVisible(1500)
                }
                onPositionChanged: function(mouse) {
                    if (!squadlockOverlayWindow.dragging || squadlockOverlayWindow.systemMoving)
                        return
                    squadlockOverlayWindow.x = Math.round(squadlockOverlayWindow.x + mouse.x - squadlockOverlayWindow.dragStartX)
                    squadlockOverlayWindow.y = Math.round(squadlockOverlayWindow.y + mouse.y - squadlockOverlayWindow.dragStartY)
                    notificationsController.holdOverlayVisible(1000)
                }
                onReleased: {
                    squadlockOverlayWindow.dragging = false
                    squadlockOverlayWindow.systemMoving = false
                    squadlockOverlayWindow.clampToScreen()
                    notificationsController.setOverlayPosition(Math.round(squadlockOverlayWindow.x), Math.round(squadlockOverlayWindow.y))
                }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                anchors.topMargin: 5
                anchors.bottomMargin: 8
                spacing: 1

                Text {
                    text: window.tr("notifications.overlay_title")
                    color: "#a8bfdc"
                    font.family: "Segoe UI"
                    font.pixelSize: 9
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Text {
                    text: notificationsController.timeText
                    color: notificationsController.squadlockFinished ? "#62d7a4" : "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 21
                    font.bold: true
                    Layout.fillWidth: true
                }
                Text {
                    text: notificationsController.squadlockFinished ? window.tr("notifications.finished") : window.tr("notifications.vehicle")
                    color: notificationsController.squadlockFinished ? "#62d7a4" : "#7f93ad"
                    font.family: "Segoe UI"
                    font.pixelSize: 9
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: notificationsController.squadlockFinished ? 28 : 0
                    visible: notificationsController.squadlockFinished
                    spacing: 6

                    PrimaryButton {
                        text: window.tr("notifications.reset")
                        Layout.fillWidth: true
                        implicitHeight: 24
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        font.pixelSize: 9
                        onPressed: notificationsController.holdOverlayVisible(1500)
                        onClicked: notificationsController.resetSquadlock()
                    }
                    PrimaryButton {
                        text: window.tr("notifications.finish")
                        Layout.fillWidth: true
                        implicitHeight: 24
                        fill: "#5eead4"
                        hoverFill: "#8ab4ff"
                        textFill: "#041014"
                        font.pixelSize: 9
                        onPressed: notificationsController.holdOverlayVisible(1500)
                        onClicked: notificationsController.finishSquadlock()
                    }
                }
            }
        }
    }

    Window {
        id: identifyMonitorOverlayWindow
        x: 0
        y: 0
        width: Screen.width > 0 ? Screen.width : 1920
        height: Screen.height > 0 ? Screen.height : 1080
        visible: identifyItemController.monitorOverlayVisible
        color: "transparent"
        transientParent: null
        flags: window.passthroughOverlayFlags

        Repeater {
            model: identifyItemController.monitorMatchesModel
            delegate: Rectangle {
                required property int matchX
                required property int matchY
                required property int matchW
                required property int matchH
                x: matchX
                y: matchY
                width: matchW
                height: matchH
                radius: Math.min(width, height) / 2
                color: "transparent"
                border.color: "#4ef7b2"
                border.width: 3
                opacity: 0.92
            }
        }
    }

    Window {
        id: chatMentionWindow
        width: 340
        height: Math.max(92, mentionPanel.implicitHeight + 18)
        visible: chatController.mentionOverlayVisible
        color: "transparent"
        transientParent: null
        flags: window.passiveOverlayFlags

        function place() {
            var screenWidth = Screen.width > 0 ? Screen.width : 1920
            var screenHeight = Screen.height > 0 ? Screen.height : 1080
            x = screenWidth - width - 24
            y = screenHeight - height - 70
        }

        onVisibleChanged: if (visible) place()
        onHeightChanged: if (visible) place()

        Rectangle {
            id: mentionPanel
            anchors.fill: parent
            anchors.margins: 3
            implicitHeight: mentionLayout.implicitHeight + 24
            radius: 8
            color: "#111c31"
            border.color: "#ffd166"
            border.width: 1
            opacity: 0.97

            ColumnLayout {
                id: mentionLayout
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 12
                spacing: 4
                Text {
                    text: chatController.mentionOverlayTitle
                    color: "#ffd166"
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Text {
                    text: chatController.mentionOverlayBody
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: chatController.dismissMentionOverlay()
            }
        }
    }

    Window {
        id: mentionHoverWindow
        x: chatController.mentionHoverX
        y: chatController.mentionHoverY
        width: 320
        height: Math.max(76, mentionHoverPanel.implicitHeight + 20)
        visible: chatController.mentionHoverVisible
        color: "transparent"
        transientParent: null
        flags: Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowTransparentForInput | Qt.WindowStaysOnTopHint

        function clampToScreen() {
            var screenWidth = Screen.width > 0 ? Screen.width : 1920
            var screenHeight = Screen.height > 0 ? Screen.height : 1080
            var desiredX = chatController.mentionHoverX
            var desiredY = chatController.mentionHoverY
            
            if (desiredX + width > screenWidth - 12) {
                desiredX = screenWidth - width - 12
            }
            if (desiredY + height > screenHeight - 12) {
                desiredY = chatController.mentionHoverY - height - 32
            }
            
            x = desiredX
            y = desiredY
        }

        onVisibleChanged: if (visible) clampToScreen()
        onWidthChanged: if (visible) clampToScreen()
        onHeightChanged: if (visible) clampToScreen()

        Rectangle {
            id: mentionHoverPanel
            anchors.fill: parent
            anchors.margins: 10
            implicitHeight: hoverLayout.implicitHeight + 16
            radius: 12
            color: "#0a1321"
            border.color: "#3b82f6"
            border.width: 1
            opacity: 0.98
            layer.enabled: true
            layer.effect: DropShadow { color: Qt.rgba(0,0,0,0.8); radius: 18; samples: 25; verticalOffset: 6 }

            RowLayout {
                id: hoverLayout
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 12
                spacing: 14

                Rectangle {
                    Layout.preferredWidth: 52
                    Layout.preferredHeight: 52
                    radius: 26
                    color: "#1d3353"
                    clip: true
                    Image {
                        anchors.fill: parent
                        source: chatController.mentionHoverAvatar || ""
                        fillMode: Image.PreserveAspectCrop
                        visible: chatController.mentionHoverAvatar !== ""
                        asynchronous: true
                        cache: false
                    }
                    Text {
                        anchors.centerIn: parent
                        visible: chatController.mentionHoverAvatar === ""
                        text: (chatController.mentionHoverName || "?").substring(0,2).toUpperCase()
                        color: "#60a5fa"
                        font.bold: true
                        font.pixelSize: 18
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Text {
                        text: chatController.mentionHoverName
                        color: "#ffffff"
                        font.family: "Segoe UI"
                        font.pixelSize: 16
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Rectangle {
                            Layout.preferredWidth: 10
                            Layout.preferredHeight: 10
                            radius: 5
                            color: chatController.mentionHoverOnline ? "#22c55e" : "#64748b"
                        }
                        Text {
                            text: (chatController.mentionHoverOnline ? "Online" : "Offline") + (chatController.mentionHoverRegiment ? (" • " + chatController.mentionHoverRegiment) : "")
                            color: "#94a3b8"
                            font.pixelSize: 13
                            font.family: "Segoe UI"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }

    Window {
        id: stockpileUploadWindow
        width: 380
        height: Math.max(116, stockpileUploadPanel.implicitHeight + 18)
        visible: stockpileController.uploadOverlayVisible
        color: "transparent"
        transientParent: null
        flags: window.passiveOverlayFlags

        function place() {
            var screenWidth = Screen.width > 0 ? Screen.width : 1920
            var screenHeight = Screen.height > 0 ? Screen.height : 1080
            x = screenWidth - width - 24
            y = screenHeight - height - 170
        }

        onVisibleChanged: if (visible) place()
        onHeightChanged: if (visible) place()

        Rectangle {
            id: stockpileUploadPanel
            anchors.fill: parent
            anchors.margins: 3
            implicitHeight: stockpileUploadLayout.implicitHeight + 24
            radius: 8
            color: "#0d1828"
            border.color: stockpileController.uploadOverlayAccent
            border.width: 1
            opacity: 0.97

            ColumnLayout {
                id: stockpileUploadLayout
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 12
                spacing: 7

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Rectangle {
                        Layout.preferredWidth: 9
                        Layout.preferredHeight: 9
                        radius: 5
                        color: stockpileController.uploadOverlayAccent
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Text {
                        text: window.tr(stockpileController.uploadOverlayTitleKey)
                        color: stockpileController.uploadOverlayAccent
                        font.family: "Segoe UI"
                        font.pixelSize: 13
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }

                Text {
                    text: stockpileController.uploadOverlayBody
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Text {
                    text: stockpileController.uploadOverlayDetail
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 5
                    radius: 3
                    color: "#172943"
                    clip: true

                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: Math.max(8, parent.width * Math.max(0, Math.min(100, stockpileController.uploadOverlayProgress)) / 100)
                        radius: 3
                        color: stockpileController.uploadOverlayAccent
                        Behavior on width { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                    }
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: stockpileController.dismissUploadOverlay()
            }
        }
    }

    Window {
        id: timeTaskRecordWindow
        width: 440
        height: recordColumn.implicitHeight + 40
        visible: timeTaskController.recordOverlayVisible
        color: "transparent"
        transientParent: null
        flags: window.interactiveOverlayFlags

        property real dragStartX: 0
        property real dragStartY: 0
        property bool dragging: false
        property bool systemMoving: false

        function clampToScreen() {
            var screenWidth = Screen.width > 0 ? Screen.width : 1920
            var screenHeight = Screen.height > 0 ? Screen.height : 1080
            x = Math.max(8, Math.min(x, screenWidth - width - 8))
            y = Math.max(8, Math.min(y, screenHeight - height - 8))
        }

        function placeFromSettings() {
            var screenWidth = Screen.width > 0 ? Screen.width : 1920
            x = timeTaskController.recordOverlayX >= 0 ? timeTaskController.recordOverlayX : screenWidth - width - 24
            y = timeTaskController.recordOverlayY >= 0 ? timeTaskController.recordOverlayY : 28
            clampToScreen()
        }

        Component.onCompleted: placeFromSettings()
        onVisibleChanged: if (visible) placeFromSettings()

        Rectangle {
            anchors.fill: parent
            anchors.margins: 4
            radius: 12
            color: "#0a121e"
            border.color: timeTaskController.recordOverlayAccent
            border.width: 1
            opacity: 0.98

            MouseArea {
                anchors.fill: parent
                onPressed: function(mouse) {
                    timeTaskRecordWindow.dragStartX = mouse.x
                    timeTaskRecordWindow.dragStartY = mouse.y
                    timeTaskRecordWindow.dragging = true
                    timeTaskRecordWindow.systemMoving = timeTaskRecordWindow.startSystemMove()
                }
                onPositionChanged: function(mouse) {
                    if (!timeTaskRecordWindow.dragging || timeTaskRecordWindow.systemMoving)
                        return
                    timeTaskRecordWindow.x = Math.round(timeTaskRecordWindow.x + mouse.x - timeTaskRecordWindow.dragStartX)
                    timeTaskRecordWindow.y = Math.round(timeTaskRecordWindow.y + mouse.y - timeTaskRecordWindow.dragStartY)
                }
                onReleased: {
                    timeTaskRecordWindow.dragging = false
                    timeTaskRecordWindow.systemMoving = false
                    timeTaskRecordWindow.clampToScreen()
                    timeTaskController.setRecordOverlayPosition(Math.round(timeTaskRecordWindow.x), Math.round(timeTaskRecordWindow.y))
                }
            }

            ColumnLayout {
                id: recordColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: timeTaskController.recordOverlayAccent
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Text {
                        text: timeTaskController.recordOverlayTitle
                        color: timeTaskController.recordOverlayAccent
                        font.family: "Segoe UI"
                        font.pixelSize: 14
                        font.bold: true
                        font.letterSpacing: 0.5
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    Rectangle {
                        width: 24
                        height: 24
                        radius: 12
                        color: closeRecordMouse.containsMouse ? "#ff7a90" : "transparent"
                        Text {
                            anchors.centerIn: parent
                            text: "×"
                            color: closeRecordMouse.containsMouse ? "#ffffff" : "#60728c"
                            font.pixelSize: 22
                            font.family: "Segoe UI"
                            anchors.verticalCenterOffset: -2
                        }
                        MouseArea {
                            id: closeRecordMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: timeTaskController.hideRecordOverlay()
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: "#1d3353"
                    opacity: 0.6
                }

                Text {
                    text: timeTaskController.recordOverlayDetail
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 14
                    font.bold: true
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    text: timeTaskController.recordOverlayHint
                    color: "#8ab4ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    opacity: 0.8
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 8
                    spacing: 12

                    PrimaryButton {
                        text: window.tr("timetask.start")
                        Layout.fillWidth: true
                        implicitHeight: 36
                        font.pixelSize: 12
                        onClicked: timeTaskController.beginCountdownRecording()
                    }
                    PrimaryButton {
                        text: window.tr("timetask.pause")
                        Layout.fillWidth: true
                        implicitHeight: 36
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        font.pixelSize: 12
                        onClicked: timeTaskController.pauseResume()
                    }
                    PrimaryButton {
                        text: window.tr("timetask.stop")
                        Layout.fillWidth: true
                        implicitHeight: 36
                        fill: "#ff7a90"
                        hoverFill: "#b94a5d"
                        textFill: "#111c31"
                        font.pixelSize: 12
                        onClicked: timeTaskController.stopRecording()
                    }
                }
            }
        }
    }

    Window {
        id: timeTaskReplayWindow
        width: 420
        height: replayColumn.implicitHeight + 40
        visible: timeTaskController.replayOverlayVisible
        color: "transparent"
        transientParent: null
        flags: window.interactiveOverlayFlags

        property real dragStartX: 0
        property real dragStartY: 0
        property bool dragging: false
        property bool systemMoving: false

        function clampToScreen() {
            var screenWidth = Screen.width > 0 ? Screen.width : 1920
            var screenHeight = Screen.height > 0 ? Screen.height : 1080
            x = Math.max(8, Math.min(x, screenWidth - width - 8))
            y = Math.max(8, Math.min(y, screenHeight - height - 8))
        }

        function placeFromSettings() {
            var screenWidth = Screen.width > 0 ? Screen.width : 1920
            x = timeTaskController.replayOverlayX >= 0 ? timeTaskController.replayOverlayX : screenWidth - width - 24
            y = timeTaskController.replayOverlayY >= 0 ? timeTaskController.replayOverlayY : 170
            clampToScreen()
        }

        Component.onCompleted: placeFromSettings()
        onVisibleChanged: if (visible) placeFromSettings()

        Rectangle {
            anchors.fill: parent
            anchors.margins: 4
            radius: 12
            color: "#0a121e"
            border.color: timeTaskController.replayOverlayAccent
            border.width: 1
            opacity: 0.98

            MouseArea {
                anchors.fill: parent
                enabled: !timeTaskController.replaying
                onPressed: function(mouse) {
                    timeTaskReplayWindow.dragStartX = mouse.x
                    timeTaskReplayWindow.dragStartY = mouse.y
                    timeTaskReplayWindow.dragging = true
                    timeTaskReplayWindow.systemMoving = timeTaskReplayWindow.startSystemMove()
                }
                onPositionChanged: function(mouse) {
                    if (!timeTaskReplayWindow.dragging || timeTaskReplayWindow.systemMoving)
                        return
                    timeTaskReplayWindow.x = Math.round(timeTaskReplayWindow.x + mouse.x - timeTaskReplayWindow.dragStartX)
                    timeTaskReplayWindow.y = Math.round(timeTaskReplayWindow.y + mouse.y - timeTaskReplayWindow.dragStartY)
                }
                onReleased: {
                    timeTaskReplayWindow.dragging = false
                    timeTaskReplayWindow.systemMoving = false
                    timeTaskReplayWindow.clampToScreen()
                    timeTaskController.setReplayOverlayPosition(Math.round(timeTaskReplayWindow.x), Math.round(timeTaskReplayWindow.y))
                }
            }

            ColumnLayout {
                id: replayColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: timeTaskController.replayOverlayAccent
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Text {
                        text: timeTaskController.replayOverlayTitle
                        color: timeTaskController.replayOverlayAccent
                        font.family: "Segoe UI"
                        font.pixelSize: 14
                        font.bold: true
                        font.letterSpacing: 0.5
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    Rectangle {
                        width: 24
                        height: 24
                        radius: 12
                        color: closeReplayMouse.containsMouse ? "#ff7a90" : "transparent"
                        Text {
                            anchors.centerIn: parent
                            text: "×"
                            color: closeReplayMouse.containsMouse ? "#ffffff" : "#60728c"
                            font.pixelSize: 22
                            font.family: "Segoe UI"
                            anchors.verticalCenterOffset: -2
                        }
                        MouseArea {
                            id: closeReplayMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: timeTaskController.hideReplayOverlay()
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: "#1d3353"
                    opacity: 0.6
                }

                Text {
                    text: timeTaskController.replayOverlayDetail
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 14
                    font.bold: true
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    text: tr("timetask.macro_running_warning")
                    color: "#ffd166"
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    Layout.fillWidth: true
                    visible: timeTaskController.replaying
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 8
                    spacing: 12
                    visible: !timeTaskController.replaying

                    PrimaryButton {
                        text: window.tr("timetask.play")
                        Layout.fillWidth: true
                        implicitHeight: 36
                        fill: "#62d7a4"
                        hoverFill: "#5eead4"
                        textFill: "#041014"
                        font.pixelSize: 12
                        onClicked: timeTaskController.playSelected()
                    }
                    PrimaryButton {
                        text: window.tr("timetask.pause")
                        Layout.fillWidth: true
                        implicitHeight: 36
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        font.pixelSize: 12
                        onClicked: timeTaskController.pauseResume()
                    }
                    PrimaryButton {
                        text: window.tr("timetask.stop")
                        Layout.fillWidth: true
                        implicitHeight: 36
                        fill: "#ff7a90"
                        hoverFill: "#b94a5d"
                        textFill: "#111c31"
                        font.pixelSize: 12
                        onClicked: timeTaskController.stopReplay()
                    }
                }
            }
        }
    }

    function navTitleKey() {
        for (var i = 0; i < navItems.count(); i++) {
            var item = navItems.get(i)
            if (item.key === appController.currentPage)
                return item.labelKey
        }
        return "nav.home"
    }
}
