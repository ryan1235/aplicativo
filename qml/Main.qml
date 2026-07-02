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
    visibility: Window.Maximized
    title: appController.appTitle
    color: settingsController.backgroundColor
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint

    header: Rectangle {
        id: customTitleBar
        width: parent.width
        height: 32
        color: settingsController.surfaceColor
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
                color: settingsController.mutedTextColor
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
            anchors.rightMargin: 8
            spacing: 4

            Button {
                id: debugPill
                visible: debugController.enabled
                Layout.preferredWidth: 92
                Layout.preferredHeight: 24
                Layout.alignment: Qt.AlignVCenter
                background: Rectangle {
                    radius: 4
                    color: debugPill.hovered ? settingsController.warningColor : settingsController.warningTextColor
                    border.color: settingsController.warningColor
                    border.width: 1
                    opacity: debugPill.hovered ? 0.95 : 0.82
                }
                contentItem: Text {
                    text: "DEBUG"
                    color: settingsController.backgroundColor
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: debugController.openLogFolder()
                ToolTip.visible: hovered
                ToolTip.text: debugController.logPath
            }

            Button {
                id: minBtn
                Layout.preferredWidth: 34
                Layout.preferredHeight: 24
                Layout.alignment: Qt.AlignVCenter
                background: Rectangle {
                    radius: 4
                    color: minBtn.hovered ? settingsController.controlColor : "transparent"
                    Behavior on color { ColorAnimation { duration: 150 } }
                }
                contentItem: Item {
                    Rectangle {
                        width: 12
                        height: 1.5
                        radius: 1
                        color: minBtn.hovered ? settingsController.textColor : settingsController.mutedTextColor
                        anchors.centerIn: parent
                        anchors.verticalCenterOffset: 3
                        Behavior on color { ColorAnimation { duration: 150 } }
                    }
                }
                onClicked: window.showMinimized()
            }

            Button {
                id: maxBtn
                Layout.preferredWidth: 34
                Layout.preferredHeight: 24
                Layout.alignment: Qt.AlignVCenter
                background: Rectangle {
                    radius: 4
                    color: maxBtn.hovered ? settingsController.controlColor : "transparent"
                    Behavior on color { ColorAnimation { duration: 150 } }
                }
                contentItem: Item {
                    Rectangle {
                        width: 11
                        height: 11
                        radius: 2
                        color: "transparent"
                        border.color: maxBtn.hovered ? settingsController.textColor : settingsController.mutedTextColor
                        border.width: 1.5
                        anchors.centerIn: parent
                        visible: window.visibility !== Window.Maximized
                        Behavior on border.color { ColorAnimation { duration: 150 } }
                    }
                    Item {
                        width: 11
                        height: 11
                        anchors.centerIn: parent
                        visible: window.visibility === Window.Maximized
                        Rectangle {
                            width: 8
                            height: 8
                            radius: 1.5
                            x: 3
                            y: 0
                            color: "transparent"
                            border.color: maxBtn.hovered ? settingsController.textColor : settingsController.mutedTextColor
                            border.width: 1.5
                            Behavior on border.color { ColorAnimation { duration: 150 } }
                        }
                        Rectangle {
                            width: 8
                            height: 8
                            radius: 1.5
                            x: 0
                            y: 3
                            color: maxBtn.hovered ? settingsController.controlColor : settingsController.backgroundColor
                            border.color: maxBtn.hovered ? settingsController.textColor : settingsController.mutedTextColor
                            border.width: 1.5
                            Behavior on color { ColorAnimation { duration: 150 } }
                            Behavior on border.color { ColorAnimation { duration: 150 } }
                        }
                    }
                }
                onClicked: window.visibility === Window.Maximized ? window.showNormal() : window.showMaximized()
            }

            Button {
                id: clsBtn
                Layout.preferredWidth: 34
                Layout.preferredHeight: 24
                Layout.alignment: Qt.AlignVCenter
                background: Rectangle {
                    radius: 4
                    color: clsBtn.hovered ? settingsController.dangerHoverColor : "transparent"
                    Behavior on color { ColorAnimation { duration: 150 } }
                }
                contentItem: Item {
                    Rectangle {
                        width: 12
                        height: 1.5
                        radius: 1
                        color: clsBtn.hovered ? settingsController.textColor : settingsController.mutedTextColor
                        anchors.centerIn: parent
                        rotation: 45
                        Behavior on color { ColorAnimation { duration: 150 } }
                    }
                    Rectangle {
                        width: 12
                        height: 1.5
                        radius: 1
                        color: clsBtn.hovered ? settingsController.textColor : settingsController.mutedTextColor
                        anchors.centerIn: parent
                        rotation: -45
                        Behavior on color { ColorAnimation { duration: 150 } }
                    }
                }
                onClicked: window.close()
            }
        }
    }

    property bool sidebarOpen: appController.sidebarOpen
    property bool exiting: false
    property int interactiveOverlayFlags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus
    property int passiveOverlayFlags: interactiveOverlayFlags
    property int passthroughOverlayFlags: passiveOverlayFlags | Qt.WindowTransparentForInput

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    Component.onCompleted: {
        if (visible)
            showMaximized()
        chatController.autoConnectWithSavedDiscord()
    }

    Shortcut {
        sequence: debugController.hotkeyLabel
        context: Qt.ApplicationShortcut
        onActivated: debugController.toggleDebug()
    }

    function pageSource(page) {
        if (page === "home") return "pages/HomePage.qml"
        if (page === "profile") return "pages/ProfilePage.qml"
        if (page === "profile") return "pages/ProfilePage.qml"
        if (page === "chat") return "pages/ChatPage.qml"
        if (page === "autoClicker") return "pages/AutoClickerPage.qml"
        if (page === "stockpile") return "pages/StockpilePage.qml"
        if (page === "itemSearch") return "pages/ItemSearchPage.qml"
        if (page === "wiki") return "pages/WikiPage.qml"
        if (page === "identifyItem") return "pages/IdentifyItemPage.qml"
        if (page === "production") return "pages/ProductionPage.qml"
        if (page === "timeTask") return "pages/TimeTaskPage.qml"
        if (page === "notifications") return "pages/NotificationsPage.qml"
        if (page === "settings") return "pages/SettingsPage.qml"
        if (page === "personalization") return "pages/PersonalizationPage.qml"
        return "pages/HomePage.qml"
    }

    function hideToTray() {
        window.visible = false
        trayController.showMessage(appController.appTitle, tr("tray.running"))
    }

    function restoreMainWindow() {
        window.visible = true
        if (window.visibility !== Window.Maximized && window.visibility !== Window.FullScreen)
            window.showMaximized()
        window.raise()
        window.requestActivate()
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
            restoreMainWindow()
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
            restoreMainWindow()
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
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor
        }

        contentItem: ColumnLayout {
            spacing: 12
            Text {
                text: tr("close.heading")
                color: settingsController.textColor
                font.family: "Segoe UI"
                font.pixelSize: 19
                font.bold: true
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Text {
                text: tr("close.body")
                color: settingsController.mutedTextColor
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
                    color: settingsController.secondaryTextColor
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
                    fill: settingsController.controlColor
                    hoverFill: settingsController.controlHoverColor
                    textFill: settingsController.textColor
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
            border.color: appController.startupDialogKind === "error" ? settingsController.dangerColor : settingsController.infoColor
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
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor
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
                        color: appController.startupDialogKind === "error" ? settingsController.dangerColor : settingsController.accentColor
                        font.family: "Segoe UI"
                        font.pixelSize: 24
                        font.bold: true
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        text: appController.startupDialogSubtitle
                        visible: text !== ""
                        color: settingsController.infoColor
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
                color: settingsController.textColor
                font.family: "Segoe UI"
                font.pixelSize: 13
                wrapMode: TextArea.Wrap
                background: Rectangle {
                    radius: 8
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor
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
                    fill: settingsController.accentColor
                    hoverFill: settingsController.accentHoverColor
                    textFill: settingsController.textInverseColor
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
            color: "transparent"
            border.color: "transparent"
            Rectangle { anchors.fill: parent; radius: 16; color: settingsController.scrimColor; opacity: 0.9 }
            Rectangle { anchors.fill: parent; radius: 16; color: "transparent"; border.color: settingsController.accentColor; border.width: 1 }
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
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor
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
                        color: settingsController.accentColor
                        font.family: "Segoe UI"
                        font.pixelSize: 22
                        font.bold: true
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        text: updateController.updateName + " - " + updateController.updateAssetName
                        color: settingsController.infoColor
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
                color: settingsController.secondaryTextColor
                font.family: "Segoe UI"
                font.pixelSize: 14
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: updateNoticeText.implicitHeight + 24
                radius: 10
                color: "transparent"
                border.color: "transparent"
                Rectangle { anchors.fill: parent; radius: 10; color: settingsController.scrimColor; opacity: 0.3 }
                Rectangle { anchors.fill: parent; radius: 10; color: "transparent"; border.color: settingsController.accentColor; border.width: 1; opacity: 0.3 }
                border.width: 1

                Text {
                    id: updateNoticeText
                    anchors.fill: parent
                    anchors.margins: 12
                    text: tr("update.offer_notice")
                    color: settingsController.secondaryTextColor
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
                    color: "transparent"
                    border.color: "transparent"
                    Rectangle { anchors.fill: parent; radius: 10; color: settingsController.scrimColor; opacity: 0.4 }
                    Rectangle { anchors.fill: parent; radius: 10; color: "transparent"; border.color: Qt.rgba(1,1,1,0.1); border.width: 1 }
                    border.width: 1
                }

                TextArea {
                    text: updateController.updateBody
                    textFormat: TextEdit.MarkdownText
                    readOnly: true
                    selectByMouse: true
                    color: settingsController.textColor
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
                    fill: Qt.rgba(0,0,0,0.4)
                    hoverFill: Qt.rgba(1,1,1,0.1)
                    textFill: settingsController.accentColor
                    onClicked: updateController.dismissOffer()
                }
                PrimaryButton {
                    text: tr("update.install_now")
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    fill: settingsController.accentColor
                    hoverFill: settingsController.accentHoverColor
                    textFill: settingsController.textInverseColor
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
            color: "transparent"
            border.color: "transparent"
            Rectangle { anchors.fill: parent; radius: 16; color: settingsController.scrimColor; opacity: 0.9 }
            Rectangle { anchors.fill: parent; radius: 16; color: "transparent"; border.color: updateController.progressAccent; border.width: 1 }
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
                        color: settingsController.backgroundColor
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
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 20
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Text {
                        text: updateController.progressText
                        color: settingsController.secondaryTextColor
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
                        color: settingsController.warningColor
                        font.family: "Segoe UI"
                        font.pixelSize: 42
                        font.bold: true
                        Layout.preferredWidth: 52
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Text {
                        text: tr("update.restart_notice")
                        color: settingsController.warningTextColor
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
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor
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
                    color: settingsController.infoColor
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
            color: "transparent"
            border.color: "transparent"
            Rectangle { anchors.fill: parent; radius: 16; color: settingsController.scrimColor; opacity: 0.9 }
            Rectangle { anchors.fill: parent; radius: 16; color: "transparent"; border.color: settingsController.dangerColor; border.width: 1 }
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
                color: settingsController.dangerColor
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
                color: settingsController.textColor
                font.family: "Segoe UI"
                font.pixelSize: 13
                wrapMode: TextArea.Wrap
                background: Rectangle {
                    radius: 8
                    color: "transparent"
                    Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.3 }
                    border.color: settingsController.dangerPanelColor
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
                    fill: settingsController.dangerColor
                    hoverFill: settingsController.dangerHoverColor
                    textFill: settingsController.textColor
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
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor
        }

        contentItem: ColumnLayout {
            spacing: 12
            Text {
                text: appController.tutorialDialogTitle
                color: settingsController.textColor
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
                color: settingsController.textColor
                font.family: "Segoe UI"
                font.pixelSize: 12
                wrapMode: TextArea.Wrap
                background: Rectangle {
                    radius: 7
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor
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
        color: settingsController.backgroundColor
        gradient: Gradient {
            GradientStop {
                position: 0.0
                color: settingsController.gradientEnabled ? settingsController.gradientStartColor : settingsController.backgroundColor
            }
            GradientStop {
                position: 1.0
                color: settingsController.gradientEnabled ? settingsController.gradientEndColor : settingsController.backgroundColor
            }
        }

        RowLayout {
            id: mainLayout
            anchors.fill: parent
            spacing: 0

            Rectangle {
                id: sidebar
                Layout.fillHeight: true
                Layout.preferredWidth: window.sidebarOpen ? settingsController.sidebarWidth : 72
                color: settingsController.surfaceColor
                clip: window.sidebarOpen
                z: 5
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
                            color: settingsController.surfaceColor
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
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 17
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            Text {
                                text: tr("app.subtitle")
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
                        Layout.preferredHeight: window.sidebarOpen ? 86 : 54
                        radius: 8
                        color: "transparent"
                        border.color: "transparent"
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 160 } }

                        Rectangle {
                            anchors.fill: parent
                            radius: 8
                            color: settingsController.accentColor
                            opacity: profileMouseArea.containsMouse ? 0.12 : 0.05
                            Behavior on opacity { NumberAnimation { duration: 150 } }
                        }
                        
                        Rectangle {
                            anchors.fill: parent
                            radius: 8
                            color: "transparent"
                            border.color: settingsController.accentColor
                            opacity: 0.3
                            border.width: 1
                        }

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
                                    color: settingsController.controlColor

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
                                        color: settingsController.accentColor
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
                                        return reg + (chatController.currentUserName || "UsuÃ¡rio");
                                    }
                                    color: settingsController.textColor
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
                                        color: chatController.currentProvider === "discord" ? settingsController.infoColor : settingsController.accentColor
                                    }
                                    Text {
                                        text: chatController.currentProvider === "discord" ? "Discord Online" : steamController.status
                                        color: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: window.sidebarOpen ? 42 : 0
                        visible: window.sidebarOpen
                        opacity: window.sidebarOpen ? 1 : 0
                        radius: 8
                        color: "transparent"
                        border.color: "transparent"
                        clip: true
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 170; easing.type: Easing.OutCubic } }
                        Behavior on opacity { NumberAnimation { duration: 130 } }

                        Rectangle {
                            anchors.fill: parent
                            radius: 8
                            color: settingsController.accentColor
                            opacity: 0.05
                        }

                        Rectangle {
                            anchors.fill: parent
                            radius: 8
                            color: "transparent"
                            border.color: settingsController.accentColor
                            opacity: navSearchInput.activeFocus ? 1.0 : 0.3
                            border.width: 1
                            Behavior on opacity { NumberAnimation { duration: 130 } }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 8
                            spacing: 8

                            Item {
                                Layout.preferredWidth: 18
                                Layout.preferredHeight: 18
                                Layout.alignment: Qt.AlignVCenter

                                Rectangle {
                                    width: 10
                                    height: 10
                                    radius: 5
                                    x: 2
                                    y: 2
                                    color: "transparent"
                                    border.color: navSearchInput.activeFocus ? settingsController.accentColor : settingsController.disabledTextColor
                                    border.width: 1.6
                                    Behavior on border.color { ColorAnimation { duration: 130 } }
                                }

                                Rectangle {
                                    width: 7
                                    height: 1.8
                                    radius: 1
                                    x: 10
                                    y: 12
                                    rotation: 45
                                    color: navSearchInput.activeFocus ? settingsController.accentColor : settingsController.disabledTextColor
                                    Behavior on color { ColorAnimation { duration: 130 } }
                                }
                            }

                            TextField {
                                id: navSearchInput
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                placeholderText: tr("sidebar.search_page")
                                placeholderTextColor: settingsController.disabledTextColor
                                color: settingsController.textColor
                                selectedTextColor: settingsController.textInverseColor
                                selectionColor: settingsController.accentColor
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                background: Item {}
                            }

                            Rectangle {
                                visible: navSearchInput.text !== ""
                                Layout.preferredWidth: 24
                                Layout.preferredHeight: 24
                                radius: 6
                                color: clearNavSearch.containsMouse ? settingsController.controlColor : "transparent"
                                Behavior on color { ColorAnimation { duration: 120 } }

                                Text {
                                    anchors.centerIn: parent
                                    text: "x"
                                    color: clearNavSearch.containsMouse ? settingsController.textColor : settingsController.disabledTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                }

                                MouseArea {
                                    id: clearNavSearch
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: navSearchInput.clear()
                                }
                            }
                        }
                    }

                    ListView {
                        id: navList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: navItems
                        clip: window.sidebarOpen
                        spacing: window.sidebarOpen ? 3 : 6
                        property string searchTerm: window.sidebarOpen ? navSearchInput.text.toLowerCase().trim() : ""
                        delegate: Rectangle {
                            id: navRow
                            width: navList.width
                            height: window.sidebarOpen ? ((showSectionHeader ? 34 : 0) + (itemVisible ? 48 : 0)) : 48
                            property bool selected: appController.currentPage === key
                            property bool searchActive: navList.searchTerm !== ""
                            property bool matchesSearch: window.navMatchesSearch(searchText, navList.searchTerm)
                            property bool showSectionHeader: window.sidebarOpen && window.isFirstVisibleInSection(index, section, navList.searchTerm) && (!searchActive || window.sectionMatchesSearch(section, navList.searchTerm))
                            property bool sectionExpanded: appController.sidebarSectionsRevision >= 0 && appController.sidebarSectionExpanded(section)
                            property bool itemVisible: !window.sidebarOpen || (searchActive ? matchesSearch : sectionExpanded)
                            property int animationDuration: window.sidebarOpen ? 190 : 0
                            radius: 8
                            color: "transparent"
                            border.color: "transparent"
                            Behavior on height { NumberAnimation { duration: navRow.animationDuration; easing.type: Easing.OutCubic } }
                            Behavior on color { ColorAnimation { duration: 130 } }

                            Item {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                height: navRow.showSectionHeader ? 30 : 0
                                visible: navRow.showSectionHeader
                                enabled: true
                                opacity: navRow.showSectionHeader ? 1 : 0
                                clip: true
                                Behavior on height { NumberAnimation { duration: navRow.animationDuration; easing.type: Easing.OutCubic } }
                                Behavior on opacity { NumberAnimation { duration: navRow.animationDuration } }

                                Rectangle {
                                    anchors.fill: parent
                                    anchors.leftMargin: 4
                                    anchors.rightMargin: 4
                                    anchors.topMargin: 2
                                    anchors.bottomMargin: 3
                                    radius: 6
                                    color: "transparent"

                                    Rectangle {
                                        anchors.fill: parent
                                        radius: 6
                                        color: settingsController.accentColor
                                        opacity: sectionMouse.containsMouse ? 0.1 : 0
                                        Behavior on opacity { NumberAnimation { duration: 150 } }
                                    }
                                    
                                    Rectangle {
                                        width: parent.width
                                        height: 1
                                        anchors.top: parent.top
                                        color: Qt.rgba(1, 1, 1, 0.03)
                                        visible: index > 0
                                    }
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    spacing: 8

                                    Rectangle {
                                        Layout.preferredWidth: 4
                                        Layout.preferredHeight: 4
                                        radius: 2
                                        color: navRow.sectionExpanded ? settingsController.accentColor : settingsController.disabledTextColor
                                        Layout.alignment: Qt.AlignVCenter
                                        layer.enabled: navRow.sectionExpanded
                                        layer.effect: DropShadow {
                                            transparentBorder: true
                                            color: settingsController.accentColor
                                            radius: 6
                                            samples: 13
                                        }
                                        Behavior on color { ColorAnimation { duration: 150 } }
                                    }

                                    Text {
                                        text: tr(sectionTitleKey(section))
                                        color: sectionMouse.containsMouse ? settingsController.textColor : (navRow.sectionExpanded ? settingsController.accentColor : settingsController.disabledTextColor)
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        font.bold: true
                                        font.letterSpacing: 0.5
                                        font.capitalization: Font.AllUppercase
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                        Behavior on color { ColorAnimation { duration: 150 } }
                                    }

                                    Text {
                                        text: navRow.sectionExpanded ? "v" : ">"
                                        color: navRow.sectionExpanded ? settingsController.accentColor : settingsController.disabledTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 12
                                        font.bold: true
                                        Layout.preferredWidth: 14
                                        horizontalAlignment: Text.AlignRight
                                        Behavior on color { ColorAnimation { duration: 150 } }
                                    }
                                }

                                MouseArea {
                                    id: sectionMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: appController.setSidebarSectionExpanded(section, !navRow.sectionExpanded)
                                }
                            }

                            Rectangle {
                                visible: navRow.itemVisible
                                x: window.sidebarOpen && mouse.containsMouse ? 5 : 0
                                width: parent.width - (window.sidebarOpen && mouse.containsMouse ? 10 : 0)
                                anchors.bottom: parent.bottom
                                height: 48
                                radius: 8
                                color: "transparent"
                                border.color: "transparent"
                                border.width: 1
                                Behavior on x { NumberAnimation { duration: navRow.animationDuration; easing.type: Easing.OutBack } }
                                Behavior on width { NumberAnimation { duration: navRow.animationDuration; easing.type: Easing.OutBack } }
                                
                                Rectangle {
                                    anchors.fill: parent
                                    radius: 8
                                    color: settingsController.accentColor
                                    opacity: navRow.selected ? 0.15 : (mouse.containsMouse ? 0.06 : 0)
                                    Behavior on opacity { NumberAnimation { duration: 150 } }
                                }

                                Rectangle {
                                    anchors.fill: parent
                                    radius: 8
                                    color: "transparent"
                                    border.color: settingsController.accentColor
                                    opacity: navRow.selected ? 0.4 : 0
                                    border.width: 1
                                    Behavior on opacity { NumberAnimation { duration: 150 } }
                                }

                                Rectangle {
                                    anchors.fill: parent
                                    radius: 8
                                    color: "transparent"
                                    border.color: Qt.rgba(1, 1, 1, 0.05)
                                    border.width: 1
                                    visible: navRow.selected
                                }
                            }

                            Rectangle {
                                visible: window.sidebarOpen && navRow.itemVisible
                                x: window.sidebarOpen && mouse.containsMouse ? 9 : 4
                                anchors.bottom: parent.bottom
                                anchors.bottomMargin: 9
                                width: 4
                                height: navRow.selected ? 30 : (mouse.containsMouse ? 22 : 0)
                                radius: 2
                                color: settingsController.accentColor
                                opacity: navRow.selected ? 1 : (mouse.containsMouse ? 0.5 : 0)
                                layer.enabled: navRow.selected
                                layer.effect: DropShadow {
                                    transparentBorder: true
                                    color: settingsController.accentColor
                                    radius: 8
                                    samples: 17
                                }
                                Behavior on x { NumberAnimation { duration: navRow.animationDuration; easing.type: Easing.OutBack } }
                                Behavior on height { NumberAnimation { duration: navRow.animationDuration; easing.type: Easing.OutCubic } }
                                Behavior on opacity { NumberAnimation { duration: navRow.animationDuration } }
                                Behavior on color { ColorAnimation { duration: 150 } }
                            }

                            RowLayout {
                                visible: navRow.itemVisible
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: 48
                                anchors.leftMargin: window.sidebarOpen ? 18 : 0
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
                                            "settings": "config.png",
                                            "palette": "config.png",
                                            "wiki": "wiki.png",
                                            "personalizacao.png": "personalizacao.png"
                                        }
                                        if (icon.indexOf(".png") !== -1) return appController.assetUrl("img/iconmenu/" + icon)
                                        return map[icon] ? appController.assetUrl("img/iconmenu/" + map[icon]) : ""
                                    }
                                    visible: source != ""
                                    Layout.preferredWidth: 42
                                    Layout.preferredHeight: 42
                                    Layout.alignment: Qt.AlignVCenter
                                    fillMode: Image.PreserveAspectFit
                                    mipmap: true
                                    smooth: true
                                    scale: window.sidebarOpen && mouse.containsMouse ? 1.06 : 1
                                    Behavior on scale { NumberAnimation { duration: navRow.animationDuration; easing.type: Easing.OutCubic } }
                                }
                                Text {
                                    text: icon.length > 0 ? icon.substring(0, 1).toUpperCase() : "-"
                                    color: navRow.selected ? settingsController.accentColor : settingsController.mutedTextColor
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
                                    color: navRow.selected ? settingsController.textColor : (mouse.containsMouse ? settingsController.textColor : settingsController.mutedTextColor)
                                    font.family: "Segoe UI"
                                    font.pixelSize: 13
                                    font.bold: navRow.selected
                                    visible: window.sidebarOpen
                                    opacity: window.sidebarOpen ? 1 : 0
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                    Behavior on opacity { NumberAnimation { duration: navRow.animationDuration } }
                                    Behavior on color { ColorAnimation { duration: 150 } }
                                }
                            }

                            MouseArea {
                                id: mouse
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: 48
                                enabled: navRow.itemVisible
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: appController.setCurrentPage(key)
                            }

                            Rectangle {
                                id: compactTooltip
                                visible: !window.sidebarOpen && navRow.itemVisible && mouse.containsMouse
                                opacity: visible ? 1 : 0
                                x: parent.width + 10
                                anchors.verticalCenter: parent.verticalCenter
                                width: Math.min(230, Math.max(150, compactTooltipTitle.implicitWidth + 28, compactTooltipLabel.implicitWidth + 28))
                                height: 50
                                radius: 9
                                color: settingsController.surfaceAltColor
                                border.color: navRow.selected ? settingsController.accentColor : settingsController.controlHoverColor
                                border.width: 1
                                z: 90
                                scale: visible ? 1 : 0.96
                                Behavior on opacity { NumberAnimation { duration: 110 } }
                                Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }

                                Rectangle {
                                    width: 10
                                    height: 10
                                    radius: 2
                                    color: compactTooltip.color
                                    border.color: compactTooltip.border.color
                                    border.width: 1
                                    x: -5
                                    anchors.verticalCenter: parent.verticalCenter
                                    rotation: 45
                                }

                                Column {
                                    anchors.fill: parent
                                    anchors.leftMargin: 14
                                    anchors.rightMargin: 12
                                    anchors.topMargin: 7
                                    spacing: 2

                                    Text {
                                        id: compactTooltipTitle
                                        width: parent.width
                                        text: tr(sectionTitleKey(section))
                                        color: settingsController.accentColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 10
                                        font.bold: true
                                        font.capitalization: Font.AllUppercase
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        id: compactTooltipLabel
                                        width: parent.width
                                        text: tr(labelKey)
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }
                                }
                            }

                        }

                        Text {
                            anchors.centerIn: parent
                            width: parent.width - 24
                            visible: navList.searchTerm !== "" && window.navSearchResultCount(navList.searchTerm) === 0
                            text: tr("sidebar.search_empty")
                            color: settingsController.disabledTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            z: 50
                        }
                    }

                    Text {
                        text: "v" + appController.version
                        color: settingsController.disabledTextColor
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
                    color: settingsController.backgroundColor

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 22
                        anchors.rightMargin: 22
                        spacing: 12

                        PrimaryButton {
                            text: window.sidebarOpen ? "<" : ">"
                            fill: settingsController.surfaceColor
                            hoverFill: settingsController.controlColor
                            textFill: settingsController.textColor
                            onClicked: {
                                window.sidebarOpen = !window.sidebarOpen
                                appController.setSidebarOpen(window.sidebarOpen)
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: tr(navTitleKey())
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 20
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            Text {
                                text: appController.foxholeStatus
                                color: settingsController.mutedTextColor
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
                            fill: settingsController.surfaceColor
                            hoverFill: settingsController.controlColor
                            textFill: settingsController.accentColor
                            onClicked: appController.showTutorial()
                            ToolTip.visible: hovered
                            ToolTip.text: tr("tutorial.help")
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "transparent"

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
                color: settingsController.backgroundColor
                opacity: 0.40 // Make it very transparent to see the blur
            }

            Rectangle {
                anchors.centerIn: parent
                width: Math.min(500, parent.width - 48)
                height: Math.min(520, parent.height - 64)
                radius: 18
                color: "transparent"
                border.color: "transparent"
                Rectangle { anchors.fill: parent; radius: 18; color: settingsController.scrimColor; opacity: 0.9 }
                Rectangle { anchors.fill: parent; radius: 18; color: "transparent"; border.color: discordLoginOverlay.accessDenied ? settingsController.dangerColor : (discordLoginOverlay.awaitingDiscordLogin ? settingsController.infoColor : settingsController.accentColor); border.width: 1 }
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
                            border.color: discordLoginOverlay.accessDenied ? settingsController.dangerColor : (discordLoginOverlay.awaitingDiscordLogin ? settingsController.infoColor : settingsController.controlHoverColor)
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
                                color: settingsController.infoColor
                            }

                            Rectangle {
                                x: -5
                                y: parent.height / 2 - 5
                                width: 10
                                height: 10
                                radius: 5
                                color: settingsController.textColor
                            }
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            width: 94
                            height: 94
                            radius: 47
                            color: settingsController.backgroundColor
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
                            color: settingsController.backgroundColor
                            border.color: settingsController.controlHoverColor
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
                            color: discordLoginOverlay.accessDenied ? settingsController.dangerColor : settingsController.textColor
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
                            color: discordLoginOverlay.accessDenied ? settingsController.dangerColor : settingsController.mutedTextColor
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
                        visible: chatController.secureReloginRequired && !discordLoginOverlay.waitingForProfile && !discordLoginOverlay.accessDenied
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(62, secureReloginText.implicitHeight + 28)
                        radius: 10
                        color: "transparent"
                        border.color: "transparent"
                        Rectangle { anchors.fill: parent; radius: 10; color: settingsController.infoColor; opacity: 0.10 }
                        Rectangle { anchors.fill: parent; radius: 10; color: "transparent"; border.color: settingsController.infoColor; border.width: 1; opacity: 0.45 }
                        Text {
                            id: secureReloginText
                            anchors.fill: parent
                            anchors.margins: 14
                            text: tr("loading.secure_relogin_notice")
                            color: settingsController.secondaryTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            lineHeight: 1.28
                            horizontalAlignment: Text.AlignLeft
                            verticalAlignment: Text.AlignVCenter
                            wrapMode: Text.WordWrap
                        }
                    }

                    Rectangle {
                        visible: discordLoginOverlay.waitingForProfile
                        Layout.fillWidth: true
                        Layout.preferredHeight: 76
                        radius: 10
                        color: "transparent"
                        border.color: "transparent"
                        Rectangle { anchors.fill: parent; radius: 10; color: settingsController.scrimColor; opacity: 0.4 }
                        Rectangle { anchors.fill: parent; radius: 10; color: "transparent"; border.color: Qt.rgba(1,1,1,0.1); border.width: 1 }
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
                                        color: modelData.active ? settingsController.accentColor : (modelData.done ? settingsController.infoColor : settingsController.borderColor)
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
                                        color: modelData.active ? settingsController.textColor : settingsController.disabledTextColor
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
                        color: "transparent"
                        border.color: "transparent"
                        Rectangle { anchors.fill: parent; radius: 10; color: settingsController.scrimColor; opacity: 0.5 }
                        Rectangle { anchors.fill: parent; radius: 10; color: "transparent"; border.color: discordLoginOverlay.accessDenied ? settingsController.dangerColor : Qt.rgba(1,1,1,0.1); border.width: 1 }
                        border.width: 1

                        Text {
                            id: loginHelpText
                            anchors.fill: parent
                            anchors.margins: 14
                            text: discordLoginOverlay.accessDenied ? tr("loading.access_denied_help") : (discordLoginOverlay.awaitingDiscordLogin ? tr("loading.discord_wait_help") : tr("loading.profile_verify_help"))
                            color: discordLoginOverlay.accessDenied ? settingsController.dangerColor : settingsController.secondaryTextColor
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
                        fill: discordLoginOverlay.accessDenied ? settingsController.dangerColor : settingsController.infoColor
                        hoverFill: discordLoginOverlay.accessDenied ? settingsController.dangerHoverColor : settingsController.controlHoverColor
                        textFill: settingsController.textColor
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

        AuthErrorOverlay {
            id: authErrorOverlay
            errorVisible: chatController.authErrorVisible
            errorCategory: chatController.authErrorCategory
            errorMessage: chatController.authErrorMessage
            blockedReason: chatController.authErrorBlockedReason
            blockedAt: chatController.authErrorBlockedAt
            currentLevel: chatController.authErrorCurrentLevel
            requiredLevel: chatController.authErrorRequiredLevel

            onLogoutClicked: chatController.logout()
            onRetryClicked: chatController.connectWithDiscord()
            onSigninClicked: chatController.connectWithDiscord()
            onGoBackClicked: chatController.authErrorVisible = false
            onCloseAppClicked: Qt.quit()
        }
    }

    Window {
        id: overlayWindow
        width: 310
        height: Math.max(96, overlayContent.implicitHeight + 30)
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
            anchors.margins: 4
            radius: 8
            color: "transparent"
            border.color: "transparent"
            Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.6 }
            Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: Qt.rgba(1,1,1,0.1); border.width: 1 }
            border.width: 1
            layer.enabled: true
            layer.effect: DropShadow {
                transparentBorder: true
                color: Qt.rgba(0, 0, 0, 0.42)
                radius: 18
                samples: 37
                verticalOffset: 6
            }
            Behavior on border.color { ColorAnimation { duration: 160 } }

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: overlayController.accentColor
                opacity: autoClickerController.active ? 0.12 : 0.07
            }

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 4
                radius: 2
                color: overlayController.accentColor
                opacity: autoClickerController.active ? 0.95 : 0.55
            }

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
                anchors.leftMargin: 16
                anchors.rightMargin: 12
                anchors.topMargin: 12
                anchors.bottomMargin: 12
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Rectangle {
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        radius: 8
                        color: Qt.rgba(1, 1, 1, 0.08)
                        border.color: overlayController.accentColor
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: autoClickerController.active ? "ON" : "II"
                            color: autoClickerController.active ? overlayController.accentColor : settingsController.warningColor
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1

                        Text {
                            text: autoClickerController.active ? tr("overlay.clicker_active") : tr("overlay.clicker_paused")
                            color: autoClickerController.active ? overlayController.accentColor : settingsController.warningColor
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }

                        Text {
                            visible: overlayController.showTarget
                            text: autoClickerController.targetTitle !== "" ? autoClickerController.targetTitle : tr("overlay.target_default")
                            color: settingsController.secondaryTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 10
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: Math.max(42, overlayHotkeyText.implicitWidth + 16)
                        Layout.preferredHeight: 24
                        radius: 7
                        color: Qt.rgba(1, 1, 1, 0.07)
                        border.color: Qt.rgba(1, 1, 1, 0.10)

                        Text {
                            id: overlayHotkeyText
                            anchors.centerIn: parent
                            text: overlayController.hotkey
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 10
                            font.bold: true
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: 24
                        Layout.preferredHeight: 24
                        radius: 12
                        color: closeAutoClickerMouse.containsMouse ? settingsController.dangerColor : "transparent"
                        Text {
                            anchors.centerIn: parent
                            text: "X"
                            color: closeAutoClickerMouse.containsMouse ? settingsController.textColor : settingsController.disabledTextColor
                            font.pixelSize: 14
                            font.family: "Segoe UI"
                            font.bold: true
                            anchors.verticalCenterOffset: -1
                        }
                        MouseArea {
                            id: closeAutoClickerMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: overlayController.setEnabled(false)
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: Qt.rgba(1, 1, 1, 0.10)
                }

                RowLayout {
                    visible: overlayController.showProfile
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        text: tr("overlay.profile")
                        color: settingsController.disabledTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 10
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    Text {
                        text: steamController.personaName !== "" ? steamController.personaName : tr("user.unknown")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 11
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }

                Rectangle {
                    visible: overlayController.showClicker
                    Layout.fillWidth: true
                    implicitHeight: clickerOverlayText.implicitHeight + (overlayHintText.visible ? overlayHintText.implicitHeight + 19 : 16)
                    radius: 8
                    color: Qt.rgba(0, 0, 0, 0.18)
                    border.color: Qt.rgba(1, 1, 1, 0.08)

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 3

                        Text {
                            id: clickerOverlayText
                            text: autoClickerController.overlayPrimaryText
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            font.bold: autoClickerController.active
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            id: overlayHintText
                            visible: autoClickerController.overlayHintText !== ""
                            text: autoClickerController.overlayHintText
                            color: settingsController.secondaryTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 10
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }
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
            color: "transparent"
            border.color: "transparent"
            Rectangle { anchors.fill: parent; radius: 8; color: settingsController.scrimColor; opacity: 0.8 }
            Rectangle { anchors.fill: parent; radius: 8; color: settingsController.accentColor; opacity: 0.08 }
            Rectangle { anchors.fill: parent; radius: 8; color: "transparent"; border.color: notificationsController.squadlockFinished ? settingsController.successColor : settingsController.accentColor; border.width: 1; opacity: 0.8 }

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
                    color: settingsController.secondaryTextColor
                    font.family: "Segoe UI"
                    font.pixelSize: 9
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Text {
                    text: notificationsController.timeText
                    color: notificationsController.squadlockFinished ? settingsController.successColor : settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 21
                    font.bold: true
                    Layout.fillWidth: true
                }
                Text {
                    text: notificationsController.squadlockFinished ? window.tr("notifications.finished") : window.tr("notifications.vehicle")
                    color: notificationsController.squadlockFinished ? settingsController.successColor : settingsController.disabledTextColor
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
                        fill: Qt.rgba(0,0,0,0.4)
                        hoverFill: Qt.rgba(1,1,1,0.1)
                        textFill: settingsController.accentColor
                        font.pixelSize: 9
                        onPressed: notificationsController.holdOverlayVisible(1500)
                        onClicked: notificationsController.resetSquadlock()
                    }
                    PrimaryButton {
                        text: window.tr("notifications.finish")
                        Layout.fillWidth: true
                        implicitHeight: 24
                        fill: settingsController.accentColor
                        hoverFill: settingsController.accentHoverColor
                        textFill: settingsController.textInverseColor
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
                required property string scoreText
                property int markerPad: Math.max(6, Math.round(Math.max(matchW, matchH) * 0.18))
                x: Math.max(0, matchX - markerPad)
                y: Math.max(0, matchY - markerPad)
                width: Math.min(identifyMonitorOverlayWindow.width - x, matchW + markerPad * 2)
                height: Math.min(identifyMonitorOverlayWindow.height - y, matchH + markerPad * 2)
                radius: Math.min(width, height) / 2
                color: "transparent"
                border.color: settingsController.successColor
                border.width: 3
                opacity: 0.92

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.leftMargin: 2
                    anchors.topMargin: -24
                    width: 58
                    height: 22
                    radius: 6
                    color: settingsController.surfaceColor
                    border.color: settingsController.successColor
                    Text {
                        anchors.centerIn: parent
                        text: scoreText
                        color: settingsController.successColor
                        font.family: "Segoe UI"
                        font.pixelSize: 11
                        font.bold: true
                    }
                }
            }
        }
    }

    Window {
        id: identifyControlOverlayWindow
        width: 340
        height: Math.max(150, identifyOverlayPanel.implicitHeight + 10)
        visible: identifyItemController.monitorControlVisible || identifyItemController.selectionBusy || identifyItemController.selectionOverlayVisible
        color: "transparent"
        transientParent: null
        flags: window.interactiveOverlayFlags

        function place() {
            var screenWidth = Screen.width > 0 ? Screen.width : 1920
            x = screenWidth - width - 24
            y = 24
        }

        onVisibleChanged: if (visible) place()
        onHeightChanged: if (visible) place()

        Rectangle {
            id: identifyOverlayPanel
            anchors.fill: parent
            anchors.margins: 3
            implicitHeight: identifyOverlayLayout.implicitHeight + 24
            radius: 8
            color: settingsController.surfaceColor
            border.color: settingsController.accentColor
            border.width: 1
            opacity: 0.96

            ColumnLayout {
                id: identifyOverlayLayout
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 12
                spacing: 7
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        text: window.tr("identify.overlay_title")
                        color: settingsController.accentColor
                        font.family: "Segoe UI"
                        font.pixelSize: 13
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    PrimaryButton {
                        text: "X"
                        Layout.preferredWidth: 34
                        implicitHeight: 26
                        fill: Qt.rgba(0,0,0,0.4)
                        hoverFill: Qt.rgba(1,1,1,0.1)
                        textFill: settingsController.accentColor
                        font.pixelSize: 11
                        onClicked: identifyItemController.hideMonitorOverlay()
                    }
                }
                Text {
                    text: identifyItemController.selectionBusy || identifyItemController.selectionOverlayVisible
                          ? window.tr("identify.select_stockpile_hint")
                          : identifyItemController.monitorSummary
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }
                RowLayout {
                    visible: identifyItemController.selectedImageUrl !== ""
                    Layout.fillWidth: true
                    spacing: 8
                    Rectangle {
                        Layout.preferredWidth: 44
                        Layout.preferredHeight: 44
                        radius: 6
                        color: settingsController.accentPanelColor
                        border.color: settingsController.borderColor
                        Image {
                            anchors.fill: parent
                            anchors.margins: 4
                            source: identifyItemController.selectedImageUrl
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            cache: false
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3
                        Text {
                            text: identifyItemController.monitorTarget !== "" ? identifyItemController.monitorTarget : window.tr("identify.no_reference")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: identifyItemController.monitoring ? window.tr("identify.on") : window.tr("identify.off")
                            color: identifyItemController.monitoring ? settingsController.successColor : settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        text: window.tr("identify.live_matches") + ": " + identifyItemController.monitorMatchCount
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 11
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Text {
                        text: window.tr("identify.confidence") + ": " + identifyItemController.monitorBestScoreText
                        color: settingsController.warningColor
                        font.family: "Segoe UI"
                        font.pixelSize: 11
                        font.bold: true
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    PrimaryButton {
                        text: window.tr("identify.select")
                        Layout.fillWidth: true
                        implicitHeight: 30
                        fill: Qt.rgba(0,0,0,0.4)
                        hoverFill: Qt.rgba(1,1,1,0.1)
                        textFill: settingsController.accentColor
                        font.pixelSize: 11
                        enabled: !identifyItemController.selectionBusy
                        onClicked: identifyItemController.selectImage()
                    }
                    PrimaryButton {
                        text: window.tr("identify.paste")
                        Layout.fillWidth: true
                        implicitHeight: 30
                        fill: Qt.rgba(0,0,0,0.4)
                        hoverFill: Qt.rgba(1,1,1,0.1)
                        textFill: settingsController.accentColor
                        font.pixelSize: 11
                        enabled: !identifyItemController.selectionBusy
                        onClicked: identifyItemController.pasteClipboard()
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    PrimaryButton {
                        property bool selectingStockpile: identifyItemController.selectionBusy || identifyItemController.selectionOverlayVisible
                        text: selectingStockpile
                              ? window.tr("identify.cancel_select")
                              : window.tr("identify.select_stockpile")
                        Layout.fillWidth: true
                        implicitHeight: 30
                        fill: selectingStockpile ? "#efc85f" : settingsController.controlColor
                        hoverFill: selectingStockpile ? "#ffd976" : settingsController.controlHoverColor
                        textFill: selectingStockpile ? "#101820" : settingsController.textColor
                        font.pixelSize: 11
                        onClicked: selectingStockpile
                                   ? identifyItemController.cancelStockpileItemSelection()
                                   : identifyItemController.beginStockpileItemSelection()
                    }
                    PrimaryButton {
                        text: window.tr("identify.clear_reference")
                        Layout.preferredWidth: 118
                        implicitHeight: 30
                        fill: Qt.rgba(0,0,0,0.4)
                        hoverFill: Qt.rgba(1,1,1,0.1)
                        textFill: settingsController.accentColor
                        font.pixelSize: 11
                        onClicked: identifyItemController.clearReference()
                    }
                }
            }
        }
    }

    Window {
        id: identifySelectionOverlayWindow
        x: 0
        y: 0
        width: Math.max(1, (Screen.width > 0 ? Screen.width : 1920) - identifyControlOverlayWindow.width - 48)
        height: Screen.height > 0 ? Screen.height : 1080
        visible: identifyItemController.selectionOverlayVisible
        color: "transparent"
        transientParent: null
        flags: window.interactiveOverlayFlags

        Rectangle {
            anchors.fill: parent
            color: settingsController.scrimColor
            opacity: 0.05
        }

        Repeater {
            model: identifyItemController.selectionCandidatesModel
            delegate: Rectangle {
                required property int candidateIndex
                required property int selectX
                required property int selectY
                required property int selectW
                required property int selectH
                property bool hot: false
                x: selectX
                y: selectY
                width: selectW
                height: selectH
                radius: 5
                scale: hot ? 1.03 : 1.0
                transformOrigin: Item.Center
                color: hot ? Qt.rgba(0.98, 0.78, 0.22, 0.30) : Qt.rgba(0.00, 0.88, 0.78, 0.16)
                border.color: hot ? "#f4d35e" : "#42e6d3"
                border.width: hot ? 3 : 2
                opacity: 1.0
                Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
                Behavior on color { ColorAnimation { duration: 120 } }
                Behavior on border.color { ColorAnimation { duration: 120 } }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onEntered: parent.hot = true
                    onExited: parent.hot = false
                    onClicked: identifyItemController.selectStockpileCandidate(parent.candidateIndex)
                }
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
            color: settingsController.surfaceColor
            border.color: settingsController.warningColor
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
                    color: settingsController.infoColor
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Text {
                    text: chatController.mentionOverlayBody
                    color: settingsController.textColor
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
            color: settingsController.backgroundColor
            border.color: settingsController.infoColor
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
                    color: settingsController.controlColor
                    clip: true
                    Image {
                        id: mentionHoverAvatarImage
                        anchors.fill: parent
                        anchors.margins: 1
                        source: chatController.mentionHoverAvatar || ""
                        fillMode: Image.PreserveAspectCrop
                        visible: chatController.mentionHoverAvatar !== ""
                        asynchronous: true
                        cache: false
                        layer.enabled: visible
                        layer.effect: OpacityMask {
                            maskSource: Rectangle {
                                width: mentionHoverAvatarImage.width
                                height: mentionHoverAvatarImage.height
                                radius: Math.min(width, height) / 2
                                visible: false
                            }
                        }
                    }
                    Text {
                        anchors.centerIn: parent
                        visible: chatController.mentionHoverAvatar === ""
                        text: (chatController.mentionHoverName || "?").substring(0,2).toUpperCase()
                        color: settingsController.infoColor
                        font.bold: true
                        font.pixelSize: 18
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Text {
                        text: chatController.mentionHoverName
                        color: settingsController.textColor
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
                            color: chatController.mentionHoverOnline ? settingsController.successColor : settingsController.disabledTextColor
                        }
                        Text {
                            text: (chatController.mentionHoverOnline ? "Online" : "Offline") + (chatController.mentionHoverRegiment ? (" â€¢ " + chatController.mentionHoverRegiment) : "")
                            color: settingsController.mutedTextColor
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
            color: settingsController.surfaceAltColor
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
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Text {
                    text: stockpileController.uploadOverlayDetail
                    color: settingsController.mutedTextColor
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
                    color: settingsController.surfaceRaisedColor
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
            color: "transparent"
            border.color: "transparent"
            Rectangle { anchors.fill: parent; radius: 12; color: settingsController.scrimColor; opacity: 0.8 }
            Rectangle { anchors.fill: parent; radius: 12; color: "transparent"; border.color: timeTaskController.recordOverlayAccent; border.width: 1; opacity: 0.6 }
            border.width: 1
            layer.enabled: true
            layer.effect: DropShadow {
                transparentBorder: true
                color: Qt.rgba(0, 0, 0, 0.42)
                radius: 20
                samples: 41
                verticalOffset: 7
            }

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: timeTaskController.recordOverlayAccent
                opacity: 0.10
            }

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 5
                radius: 3
                color: timeTaskController.recordOverlayAccent
            }

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
                anchors.leftMargin: 20
                anchors.rightMargin: 16
                anchors.topMargin: 16
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    
                    Rectangle {
                        width: 36
                        height: 36
                        radius: 9
                        color: Qt.rgba(1, 1, 1, 0.08)
                        border.color: timeTaskController.recordOverlayAccent
                        Layout.alignment: Qt.AlignVCenter

                        Rectangle {
                            anchors.centerIn: parent
                            width: 11
                            height: 11
                            radius: 6
                            color: timeTaskController.recordOverlayAccent
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1

                        Text {
                            text: timeTaskController.recordOverlayTitle
                            color: timeTaskController.recordOverlayAccent
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }

                        Text {
                            text: timeTaskController.captureSummary || ""
                            color: settingsController.secondaryTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 10
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }

                    Rectangle {
                        width: 24
                        height: 24
                        radius: 12
                        color: closeRecordMouse.containsMouse ? settingsController.dangerColor : "transparent"
                        Text {
                            anchors.centerIn: parent
                            text: "X"
                            color: closeRecordMouse.containsMouse ? settingsController.textColor : settingsController.disabledTextColor
                            font.pixelSize: 14
                            font.family: "Segoe UI"
                            font.bold: true
                            anchors.verticalCenterOffset: -1
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
                    color: Qt.rgba(1, 1, 1, 0.10)
                }

                Text {
                    text: timeTaskController.recordOverlayDetail
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 15
                    font.bold: true
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    text: timeTaskController.recordOverlayHint
                    color: settingsController.secondaryTextColor
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
                        fill: Qt.rgba(0,0,0,0.4)
                        hoverFill: Qt.rgba(1,1,1,0.1)
                        textFill: settingsController.accentColor
                        font.pixelSize: 12
                        onClicked: timeTaskController.pauseResume()
                    }
                    PrimaryButton {
                        text: window.tr("timetask.stop")
                        Layout.fillWidth: true
                        implicitHeight: 36
                        fill: settingsController.dangerColor
                        hoverFill: settingsController.dangerHoverColor
                        textFill: settingsController.surfaceColor
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
            color: "transparent"
            border.color: "transparent"
            Rectangle { anchors.fill: parent; radius: 12; color: settingsController.scrimColor; opacity: 0.8 }
            Rectangle { anchors.fill: parent; radius: 12; color: "transparent"; border.color: timeTaskController.recordOverlayAccent; border.width: 1; opacity: 0.6 }
            border.width: 1
            layer.enabled: true
            layer.effect: DropShadow {
                transparentBorder: true
                color: Qt.rgba(0, 0, 0, 0.42)
                radius: 20
                samples: 41
                verticalOffset: 7
            }

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: timeTaskController.replayOverlayAccent
                opacity: 0.10
            }

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 5
                radius: 3
                color: timeTaskController.replayOverlayAccent
            }

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
                anchors.leftMargin: 20
                anchors.rightMargin: 16
                anchors.topMargin: 16
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    
                    Rectangle {
                        width: 36
                        height: 36
                        radius: 9
                        color: Qt.rgba(1, 1, 1, 0.08)
                        border.color: timeTaskController.replayOverlayAccent
                        Layout.alignment: Qt.AlignVCenter

                        Rectangle {
                            anchors.centerIn: parent
                            width: 11
                            height: 11
                            radius: 6
                            color: timeTaskController.replayOverlayAccent
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1

                        Text {
                            text: timeTaskController.replayOverlayTitle
                            color: timeTaskController.replayOverlayAccent
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }

                        Text {
                            text: timeTaskController.selectedMacroName !== "" ? timeTaskController.selectedMacroName : window.tr("timetask.replay_empty")
                            color: settingsController.secondaryTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 10
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }

                    Rectangle {
                        width: 24
                        height: 24
                        radius: 12
                        color: closeReplayMouse.containsMouse ? settingsController.dangerColor : "transparent"
                        Text {
                            anchors.centerIn: parent
                            text: "X"
                            color: closeReplayMouse.containsMouse ? settingsController.textColor : settingsController.disabledTextColor
                            font.pixelSize: 14
                            font.family: "Segoe UI"
                            font.bold: true
                            anchors.verticalCenterOffset: -1
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
                    color: Qt.rgba(1, 1, 1, 0.10)
                }

                Text {
                    text: timeTaskController.replayOverlayDetail
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 15
                    font.bold: true
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    text: tr("timetask.macro_running_warning")
                    color: settingsController.dangerColor
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
                        fill: settingsController.accentColor
                        hoverFill: settingsController.accentHoverColor
                        textFill: settingsController.textInverseColor
                        font.pixelSize: 12
                        onClicked: timeTaskController.playSelected()
                    }
                    PrimaryButton {
                        text: window.tr("timetask.pause")
                        Layout.fillWidth: true
                        implicitHeight: 36
                        fill: Qt.rgba(0,0,0,0.4)
                        hoverFill: Qt.rgba(1,1,1,0.1)
                        textFill: settingsController.accentColor
                        font.pixelSize: 12
                        onClicked: timeTaskController.pauseResume()
                    }
                    PrimaryButton {
                        text: window.tr("timetask.stop")
                        Layout.fillWidth: true
                        implicitHeight: 36
                        fill: settingsController.dangerColor
                        hoverFill: settingsController.dangerHoverColor
                        textFill: settingsController.surfaceColor
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

    function navMatchesSearch(searchText, term) {
        var query = (term || "").toLowerCase().trim()
        if (query === "")
            return true
        return String(searchText || "").toLowerCase().indexOf(query) !== -1
    }

    function navSearchResultCount(term) {
        var count = 0
        for (var i = 0; i < navItems.count(); i++) {
            var item = navItems.get(i)
            if (navMatchesSearch(item.searchText, term))
                count += 1
        }
        return count
    }

    function isFirstVisibleInSection(index, section, term) {
        if ((term || "").trim() === "") {
            return index === 0 || navItems.get(index - 1).section !== section
        }
        for (var i = index - 1; i >= 0; i--) {
            var item = navItems.get(i)
            if (item.section !== section)
                break
            if (navMatchesSearch(item.searchText, term))
                return false
        }
        return true
    }

    function sectionMatchesSearch(section, term) {
        var query = (term || "").trim()
        if (query === "")
            return true
        for (var i = 0; i < navItems.count(); i++) {
            var item = navItems.get(i)
            if (item.section === section && navMatchesSearch(item.searchText, query))
                return true
        }
        return false
    }

    function sectionTitleKey(section) {
        if (section === "core") return "sidebar.navigation"
        if (section === "automation") return "sidebar.automation"
        if (section === "logistics") return "sidebar.logistics"
        if (section === "tools") return "sidebar.utilities"
        if (section === "config") return "sidebar.settings"
        return "sidebar.navigation"
    }
}


