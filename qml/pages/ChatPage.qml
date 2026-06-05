import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: root
    color: "transparent"
    property int lastMessageCount: 0
    property string lastSelectedRoom: ""
    property bool preservingOlderMessages: false
    property bool stickMessagesToBottom: true
    property real olderContentHeight: 0
    property real olderContentY: 0

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    function messageFlickable() {
        return messageScroll && messageScroll.contentItem ? messageScroll.contentItem : null
    }

    function scrollMessagesToBottom() {
        var flickable = messageFlickable()
        if (!flickable || flickable.contentY === undefined)
            return
        var target = Math.max(0, flickable.contentHeight - flickable.height)
        flickable.contentY = target
        stickMessagesToBottom = true
    }

    function updateMessageStickState() {
        var flickable = messageFlickable()
        if (!flickable || flickable.contentY === undefined || preservingOlderMessages)
            return
        var maxY = Math.max(0, flickable.contentHeight - flickable.height)
        stickMessagesToBottom = flickable.contentY >= maxY - 28
    }

    function syncMessageScroll() {
        var count = chatController.messagesRows.length
        var room = chatController.selectedRoom || ""
        var roomChanged = room !== lastSelectedRoom
        var flickable = messageFlickable()

        if (preservingOlderMessages && count > lastMessageCount && flickable && flickable.contentY !== undefined) {
            var addedHeight = Math.max(0, messagesColumn.implicitHeight - olderContentHeight)
            flickable.contentY = Math.max(0, olderContentY + addedHeight)
            preservingOlderMessages = false
            stickMessagesToBottom = false
        } else if (roomChanged || (count > 0 && lastMessageCount === 0) || (count > lastMessageCount && stickMessagesToBottom)) {
            scrollMessagesToBottom()
        } else if (preservingOlderMessages && !chatController.loadingOlderMessages && count === lastMessageCount) {
            preservingOlderMessages = false
        } else {
            updateMessageStickState()
        }

        lastSelectedRoom = room
        lastMessageCount = count
    }

    Connections {
        target: chatController
        function onChanged() {
            Qt.callLater(root.syncMessageScroll)
        }
    }

    Dialog {
        id: gifDialog
        title: tr("home.chat.gif_title")
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        width: Math.min(root.width - 80, 520)
        x: (root.width - width) / 2
        y: 80
        onAccepted: {
            chatController.sendGif(gifInput.text)
            gifInput.text = ""
        }
        contentItem: TextField {
            id: gifInput
            placeholderText: tr("home.chat.gif_prompt")
            color: "#edf6ff"
            selectByMouse: true
            background: Rectangle { radius: 7; color: "#0e1a2d"; border.color: "#2d496f" }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 12

        Rectangle {
            Layout.preferredWidth: 292
            Layout.fillHeight: true
            radius: 8
            color: "#111c31"
            border.color: "#24486d"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10
                Text {
                    text: tr("home.chat.title")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 20
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Text {
                    text: chatController.status
                    color: chatController.connected ? "#8ab4ff" : "#99abc4"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    maximumLineCount: 3
                }
                RowLayout {
                    Layout.fillWidth: true
                    PrimaryButton {
                        text: chatController.connected ? tr("home.chat.connected") : tr("home.chat.connect")
                        visible: !chatController.connected
                        onClicked: chatController.connectWithSteam()
                    }
                    PrimaryButton {
                        text: tr("home.chat.refresh")
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: chatController.refreshRooms()
                    }
                }

                Text {
                    text: tr("home.chat.rooms") + " (" + chatController.roomsRows.length + ")"
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                    font.bold: true
                    Layout.fillWidth: true
                }

                ScrollView {
                    id: roomsScroll
                    Layout.fillWidth: true
                    Layout.preferredHeight: 210
                    clip: true
                    Column {
                        id: roomsColumn
                        width: roomsScroll.width
                        spacing: 8
                        Repeater {
                            model: chatController.roomsRows
                            delegate: Rectangle {
                                width: roomsColumn.width
                                height: 46
                                radius: 7
                                color: chatController.selectedRoom === modelData.slug ? "#1d3353" : mouse.containsMouse ? "#172943" : "#0e1a2d"
                                border.color: chatController.selectedRoom === modelData.slug ? "#5eead4" : "transparent"
                                Behavior on color { ColorAnimation { duration: 120 } }
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    Text {
                                        text: modelData.label
                                        color: "#edf6ff"
                                        font.family: "Segoe UI"
                                        font.bold: true
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                    Rectangle {
                                        visible: modelData.unread > 0
                                        Layout.preferredWidth: Math.max(24, unreadText.implicitWidth + 12)
                                        Layout.preferredHeight: 22
                                        radius: 8
                                        color: "#5eead4"
                                        Text {
                                            id: unreadText
                                            anchors.centerIn: parent
                                            text: modelData.unread
                                            color: "#041014"
                                            font.family: "Segoe UI"
                                            font.pixelSize: 11
                                            font.bold: true
                                        }
                                    }
                                }
                                MouseArea {
                                    id: mouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: chatController.selectRoom(modelData.slug)
                                }
                            }
                        }
                    }
                }

                Text {
                    text: tr("home.chat.online") + " (" + chatController.onlineRows.length + ")"
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                    font.bold: true
                    Layout.fillWidth: true
                }

                ScrollView {
                    id: onlineScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    Column {
                        id: onlineColumn
                        width: onlineScroll.width
                        spacing: 7
                        Repeater {
                            model: chatController.onlineRows
                            delegate: Rectangle {
                                width: onlineColumn.width
                                height: 44
                                radius: 7
                                color: "#0e1a2d"
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 8
                                    Rectangle {
                                        Layout.preferredWidth: 28
                                        Layout.preferredHeight: 28
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
                                        Text { text: modelData.name; color: "#edf6ff"; font.family: "Segoe UI"; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Text { text: modelData.detail || ("@" + modelData.mention); color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 8
            color: "#111c31"
            border.color: "#24486d"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: chatController.selectedRoomLabel || tr("home.chat.select")
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: chatController.currentUserName ? tr("home.chat.connected_as") + " " + chatController.currentUserName : tr("home.chat.no_user")
                            color: "#99abc4"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                    PrimaryButton {
                        text: chatController.loadingOlderMessages ? tr("home.chat.loading_older") : tr("home.chat.load_older")
                        enabled: chatController.hasOlderMessages && !chatController.loadingOlderMessages
                        fill: enabled ? "#1d3353" : "#0e1a2d"
                        hoverFill: "#1d3353"
                        textFill: enabled ? "#edf6ff" : "#60728c"
                        onClicked: {
                            var flickable = root.messageFlickable()
                            root.preservingOlderMessages = true
                            root.stickMessagesToBottom = false
                            root.olderContentHeight = messagesColumn.implicitHeight
                            root.olderContentY = flickable && flickable.contentY !== undefined ? flickable.contentY : 0
                            chatController.loadOlderMessages()
                        }
                    }
                }

                ScrollView {
                    id: messageScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    Connections {
                        target: messageScroll.contentItem
                        function onContentYChanged() {
                            root.updateMessageStickState()
                        }
                        function onHeightChanged() {
                            root.updateMessageStickState()
                        }
                        function onContentHeightChanged() {
                            if (root.stickMessagesToBottom && !root.preservingOlderMessages)
                                Qt.callLater(root.scrollMessagesToBottom)
                            else
                                root.updateMessageStickState()
                        }
                    }
                    Column {
                        id: messagesColumn
                        width: messageScroll.width
                        spacing: 8
                        onImplicitHeightChanged: {
                            if (root.stickMessagesToBottom && !root.preservingOlderMessages)
                                Qt.callLater(root.scrollMessagesToBottom)
                        }
                        Repeater {
                            model: chatController.messagesRows
                            delegate: Rectangle {
                                width: messagesColumn.width
                                implicitHeight: messageCardColumn.implicitHeight + 20
                                radius: 8
                                color: modelData.mentioned ? "#25351f" : modelData.mine ? "#173444" : "#0e1a2d"
                                border.color: modelData.mentioned ? "#ffd166" : "transparent"
                                Behavior on color { ColorAnimation { duration: 120 } }

                                ColumnLayout {
                                    id: messageCardColumn
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: 10
                                    spacing: 6
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Rectangle {
                                            Layout.preferredWidth: 30
                                            Layout.preferredHeight: 30
                                            radius: 15
                                            color: "#1d3353"
                                            Image {
                                                anchors.fill: parent
                                                anchors.margins: 1
                                                source: modelData.avatar
                                                fillMode: Image.PreserveAspectCrop
                                                visible: modelData.avatar !== ""
                                            }
                                        }
                                        Text { text: modelData.author; color: "#5eead4"; font.bold: true; font.family: "Segoe UI"; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Text { text: modelData.meta; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 11 }
                                    }
                                    Text {
                                        text: modelData.body
                                        color: "#edf6ff"
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                    AnimatedImage {
                                        visible: modelData.mediaUrl !== "" && modelData.isGif
                                        source: modelData.mediaUrl
                                        playing: visible
                                        Layout.preferredWidth: Math.min(420, messageScroll.width - 48)
                                        Layout.preferredHeight: visible ? Math.min(230, implicitHeight > 0 ? implicitHeight : 180) : 0
                                        fillMode: Image.PreserveAspectFit
                                        cache: false
                                    }
                                    Image {
                                        visible: modelData.mediaUrl !== "" && !modelData.isGif
                                        source: modelData.mediaUrl
                                        asynchronous: true
                                        sourceSize.width: Math.min(420, messageScroll.width - 48)
                                        sourceSize.height: 220
                                        Layout.preferredWidth: Math.min(420, messageScroll.width - 48)
                                        Layout.preferredHeight: visible ? 220 : 0
                                        fillMode: Image.PreserveAspectFit
                                        cache: false
                                    }
                                }
                            }
                        }
                    }
                }

                ListView {
                    id: mentionList
                    Layout.fillWidth: true
                    Layout.preferredHeight: count > 0 ? 42 : 0
                    orientation: ListView.Horizontal
                    spacing: 8
                    clip: true
                    model: chatController.mentionSuggestionRows
                    delegate: Button {
                        width: Math.min(180, Math.max(96, mentionText.implicitWidth + 32))
                        height: 34
                        onClicked: {
                            messageInput.text = chatController.applyMention(messageInput.text, modelData.mention)
                            messageInput.forceActiveFocus()
                            chatController.updateMentionSuggestions(messageInput.text)
                        }
                        background: Rectangle {
                            radius: 8
                            color: "#172943"
                            border.color: "#2d496f"
                        }
                        contentItem: Text {
                            id: mentionText
                            text: "@" + modelData.mention
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    ListView {
                        Layout.preferredWidth: 272
                        Layout.preferredHeight: 38
                        orientation: ListView.Horizontal
                        model: chatController.quickEmojis
                        spacing: 6
                        delegate: Button {
                            width: 34
                            height: 34
                            text: modelData
                            font.pixelSize: 16
                            onClicked: {
                                messageInput.text = messageInput.text + (messageInput.text.endsWith(" ") || messageInput.text.length === 0 ? "" : " ") + modelData + " "
                                messageInput.forceActiveFocus()
                            }
                            background: Rectangle {
                                radius: 8
                                color: hovered ? "#1d3353" : "#0e1a2d"
                                border.color: "#24486d"
                            }
                        }
                    }

                    PrimaryButton {
                        text: tr("home.chat.gif")
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: gifDialog.open()
                    }

                    TextField {
                        id: messageInput
                        Layout.fillWidth: true
                        placeholderText: tr("home.chat.message")
                        color: "#edf6ff"
                        selectByMouse: true
                        onTextChanged: chatController.updateMentionSuggestions(text)
                        onAccepted: {
                            chatController.sendMessage(text)
                            text = ""
                            chatController.updateMentionSuggestions("")
                        }
                        background: Rectangle { radius: 7; color: "#0e1a2d"; border.color: "#2d496f" }
                    }
                    PrimaryButton {
                        text: tr("home.chat.send")
                        onClicked: {
                            chatController.sendMessage(messageInput.text)
                            messageInput.text = ""
                            chatController.updateMentionSuggestions("")
                        }
                    }
                }
            }
        }
    }
}
