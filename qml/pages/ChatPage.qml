import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import "../components"

Rectangle {
    id: root
    color: "transparent"
    property int lastMessageCount: 0
    property string replyingTo: ""
    property string replyingToLabel: ""
    property string reactingToMsgId: ""
    property string whisperingTo: ""
    property string whisperingToLabel: ""
    property string lastSelectedRoom: ""
    property bool preservingOlderMessages: false
    property bool stickMessagesToBottom: true
    property real olderContentHeight: 0
    property real olderContentY: 0

    function scrollToMessage(msgId) {
        for (var i = 0; i < messagesColumn.children.length; i++) {
            if (chatController.messagesRows[i] && chatController.messagesRows[i].id === msgId) {
                var targetY = messagesColumn.children[i].y;
                messageScroll.contentY = Math.max(0, Math.min(targetY, messagesColumn.height - messageScroll.height));
                
                // Add a small flash effect to highlight the message
                var item = messagesColumn.children[i]
                var oldColor = item.color
                item.color = "#2a3b22"
                Qt.callLater(function() {
                    var animation = Qt.createQmlObject('import QtQuick; ColorAnimation { target: item; property: "color"; to: "' + oldColor + '"; duration: 1000 }', item)
                    animation.start()
                })
                return;
            }
        }
    }

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

    EmojiGifPicker {
        id: pickerPopup
        onEmojiSelected: function(emoji) {
            messageInput.text += emoji
            messageInput.forceActiveFocus()
        }
        onGifSelected: function(gifUrl) {
            chatController.sendGif(gifUrl)
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
                        text: chatController.connected ? tr("home.chat.connected") : tr("home.chat.connect_discord")
                        visible: !chatController.connected
                        onClicked: chatController.connectWithDiscord()
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
                                        Layout.preferredWidth: 32
                                        Layout.preferredHeight: 32
                                        radius: 16
                                        color: "#1d3353"
                                        
                                        Rectangle {
                                            id: maskOnline
                                            anchors.fill: parent
                                            anchors.margins: 1
                                            radius: 15
                                            visible: false
                                        }
                                        Image {
                                            id: imgOnline
                                            anchors.fill: maskOnline
                                            source: modelData.avatar
                                            fillMode: Image.PreserveAspectCrop
                                            visible: false
                                        }
                                        OpacityMask {
                                            anchors.fill: maskOnline
                                            source: imgOnline
                                            maskSource: maskOnline
                                            visible: modelData.avatar !== ""
                                        }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 0
                                        Text { text: modelData.name; color: "#edf6ff"; font.family: "Segoe UI"; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Text { text: modelData.detail || ("@" + modelData.mention); color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                    }
                                    Rectangle {
                                        Layout.preferredWidth: 28
                                        Layout.preferredHeight: 28
                                        radius: 14
                                        color: whisperArea.containsMouse ? "#24486d" : "transparent"
                                        visible: modelData.discordId !== "" && modelData.discordId !== chatController.discordId
                                        Text { anchors.centerIn: parent; text: "💬"; font.pixelSize: 12 }
                                        MouseArea {
                                            id: whisperArea
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            onClicked: {
                                                root.whisperingTo = modelData.discordId
                                                root.whisperingToLabel = modelData.name
                                                messageInput.forceActiveFocus()
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
                                color: modelData.mentioned ? "#2a3b22" : (hoverMsg.hovered ? "#122036" : (modelData.mine ? "#0a1321" : "transparent"))
                                border.color: modelData.mentioned ? "#ffd166" : "transparent"
                                Behavior on color { ColorAnimation { duration: 120 } }
                                
                                HoverHandler {
                                    id: hoverMsg
                                }

                                ColumnLayout {
                                    id: messageCardColumn
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: 10
                                    spacing: 6
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 20
                                        color: hoverReplyTarget.containsMouse ? "#24395e" : "#1a293e"
                                        radius: 4
                                        visible: modelData.replyToMessageId !== ""
                                        MouseArea {
                                            id: hoverReplyTarget
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            onClicked: root.scrollToMessage(modelData.replyToMessageId)
                                        }
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 4
                                            spacing: 4
                                            Text { text: "↩ " + modelData.replyToAuthor; color: "#8ab4ff"; font.bold: true; font.pixelSize: 10 }
                                            Text { text: modelData.replyToBody; color: "#99abc4"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 12
                                        Rectangle {
                                            Layout.preferredWidth: 38
                                            Layout.preferredHeight: 38
                                            radius: 19
                                            color: "#1d3353"
                                            
                                            Rectangle {
                                                id: maskMsg
                                                anchors.fill: parent
                                                anchors.margins: 1
                                                radius: 18
                                                visible: false
                                            }
                                            Image {
                                                id: imgMsg
                                                anchors.fill: maskMsg
                                                source: modelData.avatar
                                                fillMode: Image.PreserveAspectCrop
                                                visible: false
                                            }
                                            OpacityMask {
                                                anchors.fill: maskMsg
                                                source: imgMsg
                                                maskSource: maskMsg
                                                visible: modelData.avatar !== ""
                                            }
                                        }
                                        Text { text: modelData.author; color: "#5eead4"; font.bold: true; font.family: "Segoe UI"; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Text { text: modelData.meta; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 11 }
                                    }
                                    Text {
                                        text: modelData.mediaUrl !== "" ? modelData.body.replace(modelData.mediaUrl, "").trim() : modelData.body
                                        visible: text.length > 0
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
                                        asynchronous: false
                                        Layout.preferredWidth: Math.min(420, messageScroll.width - 48)
                                        Layout.preferredHeight: visible ? 200 : 0
                                        fillMode: Image.PreserveAspectFit
                                        cache: true
                                    }
                                    Image {
                                        visible: modelData.mediaUrl !== "" && !modelData.isGif
                                        source: modelData.mediaUrl
                                        asynchronous: false
                                        sourceSize.width: Math.min(420, messageScroll.width - 48)
                                        sourceSize.height: 200
                                        Layout.preferredWidth: Math.min(420, messageScroll.width - 48)
                                        Layout.preferredHeight: visible ? 200 : 0
                                        fillMode: Image.PreserveAspectFit
                                        cache: true
                                    }

                                }
                                
                                // Hover action row (Reply, React, Whisper)
                                RowLayout {
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.rightMargin: 8
                                    anchors.topMargin: -12
                                    spacing: 4
                                    visible: hoverMsg.hovered

                                    Rectangle {
                                        Layout.preferredWidth: 30
                                        Layout.preferredHeight: 30
                                        radius: 15
                                        color: hoverReply.containsMouse ? "#24486d" : "#1d3353"
                                        Text { anchors.centerIn: parent; text: "↩"; font.pixelSize: 14; color: "#edf6ff" }
                                        MouseArea {
                                            id: hoverReply
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            onClicked: {
                                                root.replyingTo = modelData.id
                                                root.replyingToLabel = modelData.author + ": " + modelData.body
                                            }
                                        }
                                    }
                                    Rectangle {
                                        Layout.preferredWidth: 30
                                        Layout.preferredHeight: 30
                                        radius: 15
                                        color: hoverWhisper.containsMouse ? "#24486d" : "#1d3353"
                                        Text { anchors.centerIn: parent; text: "W"; font.pixelSize: 14; color: "#edf6ff"; font.bold: true }
                                        visible: modelData.authorDiscordId !== "" && !modelData.mine
                                        MouseArea {
                                            id: hoverWhisper
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            onClicked: {
                                                root.whisperingTo = modelData.authorDiscordId || ""
                                                root.whisperingToLabel = modelData.author
                                            }
                                        }
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

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        radius: 6
                        color: "#2a1636"
                        visible: root.whisperingTo !== ""
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 8
                            Text { text: "🔒 Sussurrando para: " + root.whisperingToLabel; color: "#f3e8ff"; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                            Text {
                                text: "✖ "
                                color: "#f87171"
                                font.pixelSize: 14
                                font.bold: true
                                MouseArea {
                                    anchors.fill: parent
                                    anchors.margins: -4
                                    onClicked: {
                                        root.whisperingTo = ""
                                        root.whisperingToLabel = ""
                                    }
                                }
                            }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        radius: 6
                        color: "#1d3353"
                        visible: root.replyingTo !== ""
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 8
                            Text { text: "↩ Resposta para: " + root.replyingToLabel; color: "#edf6ff"; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                            Text {
                                text: "✖ "
                                color: "#f87171"
                                font.pixelSize: 14
                                font.bold: true
                                MouseArea {
                                    anchors.fill: parent
                                    anchors.margins: -4
                                    onClicked: {
                                        root.replyingTo = ""
                                        root.replyingToLabel = ""
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Button {
                        id: pickerButton
                        Layout.preferredWidth: 40
                        Layout.preferredHeight: 40
                        text: "😀"
                        font.pixelSize: 18
                        background: Rectangle {
                            radius: 20
                            color: hovered ? "#1d3353" : "#0e1a2d"
                            border.color: "#24486d"
                        }
                        onClicked: {
                            // Calculate position relative to the main window or view
                            var pos = pickerButton.mapToItem(root, 0, 0)
                            pickerPopup.x = Math.max(0, pos.x - 140)
                            pickerPopup.y = Math.max(0, pos.y - pickerPopup.height - 10)
                            pickerPopup.open()
                        }
                    }

                    TextField {
                        id: messageInput
                        Layout.fillWidth: true
                        placeholderText: tr("home.chat.message")
                        color: "#edf6ff"
                        selectByMouse: true
                        onTextChanged: chatController.updateMentionSuggestions(text)
                        onAccepted: {
                            if (text.trim().length > 0) {
                                if (root.whisperingTo !== "") {
                                    chatController.sendWhisperToUser(root.whisperingTo, text)
                                } else if (root.replyingTo !== "") {
                                    chatController.sendMessageReply(text, root.replyingTo)
                                    root.replyingTo = ""
                                    root.replyingToLabel = ""
                                } else {
                                    chatController.sendMessage(text)
                                }
                                text = ""
                                chatController.updateMentionSuggestions("")
                            }
                        }
                        background: Rectangle { radius: 7; color: "#0e1a2d"; border.color: "#2d496f" }
                    }
                    PrimaryButton {
                        text: tr("home.chat.send")
                        onClicked: {
                            if (messageInput.text.trim().length > 0) {
                                if (root.whisperingTo !== "") {
                                    chatController.sendWhisperToUser(root.whisperingTo, messageInput.text)
                                } else if (root.replyingTo !== "") {
                                    chatController.sendMessageReply(messageInput.text, root.replyingTo)
                                    root.replyingTo = ""
                                    root.replyingToLabel = ""
                                } else {
                                    chatController.sendMessage(messageInput.text)
                                }
                                messageInput.text = ""
                                chatController.updateMentionSuggestions("")
                            }
                        }
                    }
                }
                } // Close ColumnLayout
            }
        }
    }
}
