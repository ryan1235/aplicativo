import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: root
    color: "transparent"

    property int lastMessageCount: 0
    property string replyingTo: ""
    property string replyingToLabel: ""
    property string lastSelectedRoom: ""
    property string highlightMessageId: ""
    property bool preservingOlderMessages: false
    property bool stickMessagesToBottom: true
    property bool clampingMessageScroll: false
    property real olderContentHeight: 0
    property real olderContentY: 0

    Component.onCompleted: {
        chatController.ensureStarted()
        Qt.callLater(root.syncMessageScroll)
    }

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    function messageFlickable() {
        return messageList
    }

    function minContentY(view) {
        return view && view.originY !== undefined ? view.originY : 0
    }

    function maxContentY(view) {
        if (!view)
            return 0

        var minY = minContentY(view)
        var maxY = Math.max(minY, minY + view.contentHeight - view.height)

        if (view === messageList && view.count > 0) {
            var lastItem = view.itemAtIndex(view.count - 1)
            if (lastItem)
                maxY = Math.min(maxY, Math.max(minY, lastItem.y + lastItem.height - view.height))
        }

        return maxY
    }

    function clampContentY(view, value) {
        var minY = minContentY(view)
        return Math.max(minY, Math.min(value, maxContentY(view)))
    }

    function enforceMessageScrollBounds(stopAnimation) {
        if (!messageList || clampingMessageScroll)
            return
        var boundedY = clampContentY(messageList, messageList.contentY)
        if (Math.abs(boundedY - messageList.contentY) > 0.5) {
            if (stopAnimation !== false && messageWheelAnimation && messageWheelAnimation.running)
                messageWheelAnimation.stop()
            clampingMessageScroll = true
            messageList.contentY = boundedY
            clampingMessageScroll = false
        }
    }

    function smoothWheel(view, animation, event) {
        var delta = 0
        if (event.pixelDelta && event.pixelDelta.y !== 0)
            delta = event.pixelDelta.y
        else if (event.angleDelta && event.angleDelta.y !== 0)
            delta = event.angleDelta.y / 120 * 78
        if (delta === 0)
            return

        if (maxContentY(view) <= minContentY(view) + 1) {
            event.accepted = true
            return
        }

        var currentTarget = animation.running ? animation.to : view.contentY
        var targetY = clampContentY(view, currentTarget - delta)
        animation.stop()
        animation.from = view.contentY
        animation.to = targetY
        animation.duration = Math.max(140, Math.min(280, 150 + Math.abs(targetY - view.contentY) * 0.22))
        animation.start()
        event.accepted = true
    }

    function scrollToMessage(msgId) {
        for (var i = 0; i < chatController.messagesModel.count(); i++) {
            var row = chatController.messagesModel.get(i)
            if (row && row.id === msgId) {
                highlightMessageId = msgId
                messageList.positionViewAtIndex(i, ListView.Contain)
                highlightReset.restart()
                return
            }
        }
    }

    function scrollMessagesToBottom() {
        if (!messageList)
            return
        messageList.contentY = maxContentY(messageList)
        stickMessagesToBottom = true
    }

    function updateMessageStickState() {
        if (!messageList || preservingOlderMessages)
            return
        var maxY = maxContentY(messageList)
        stickMessagesToBottom = messageList.contentY >= maxY - 28
    }

    function syncMessageScroll() {
        var count = messageList.count
        var room = chatController.selectedRoom || ""
        var roomChanged = room !== lastSelectedRoom

        if (preservingOlderMessages && count > lastMessageCount) {
            var addedHeight = Math.max(0, messageList.contentHeight - olderContentHeight)
            messageList.contentY = clampContentY(messageList, olderContentY + addedHeight)
            preservingOlderMessages = false
            stickMessagesToBottom = false
        } else if (roomChanged || (count > 0 && lastMessageCount === 0) || (count > lastMessageCount && stickMessagesToBottom)) {
            Qt.callLater(root.scrollMessagesToBottom)
        } else if (preservingOlderMessages && !chatController.loadingOlderMessages && count === lastMessageCount) {
            preservingOlderMessages = false
        } else {
            updateMessageStickState()
        }

        lastSelectedRoom = room
        lastMessageCount = count
    }

    Timer {
        id: highlightReset
        interval: 1000
        onTriggered: root.highlightMessageId = ""
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

                PrimaryButton {
                    text: chatController.connected ? tr("home.chat.connected") : tr("home.chat.connect_discord")
                    visible: !chatController.connected
                    onClicked: chatController.connectWithDiscord()
                }

                Text {
                    text: tr("home.chat.rooms") + " (" + roomsList.count + ")"
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                    font.bold: true
                    Layout.fillWidth: true
                }

                ListView {
                    id: roomsList
                    Layout.fillWidth: true
                    Layout.preferredHeight: 210
                    clip: true
                    spacing: 8
                    reuseItems: true
                    boundsBehavior: Flickable.StopAtBounds
                    maximumFlickVelocity: 4200
                    flickDeceleration: 1800
                    model: chatController.roomsModel
                    NumberAnimation {
                        id: roomsWheelAnimation
                        target: roomsList
                        property: "contentY"
                        duration: 170
                        easing.type: Easing.OutCubic
                    }
                    WheelHandler {
                        target: null
                        acceptedDevices: PointerDevice.Mouse
                        onWheel: function(event) { root.smoothWheel(roomsList, roomsWheelAnimation, event) }
                    }
                    delegate: Rectangle {
                        property string rowSlug: String(slug || "")
                        property string rowLabel: String(label || "")
                        property int rowUnread: Number(unread || 0)

                        width: roomsList.width
                        height: 46
                        radius: 7
                        color: chatController.selectedRoom === rowSlug ? "#1d3353" : roomMouse.containsMouse ? "#172943" : "#0e1a2d"
                        border.color: chatController.selectedRoom === rowSlug ? "#5eead4" : "transparent"
                        Behavior on color { ColorAnimation { duration: 120 } }
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            Text {
                                text: rowLabel
                                color: "#edf6ff"
                                font.family: "Segoe UI"
                                font.bold: true
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Rectangle {
                                visible: rowUnread > 0
                                Layout.preferredWidth: Math.max(24, unreadText.implicitWidth + 12)
                                Layout.preferredHeight: 22
                                radius: 8
                                color: "#5eead4"
                                Text {
                                    id: unreadText
                                    anchors.centerIn: parent
                                    text: String(rowUnread)
                                    color: "#041014"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }
                        }
                        MouseArea {
                            id: roomMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: chatController.selectRoom(rowSlug)
                        }
                    }
                    ScrollBar.vertical: ScrollBar { active: roomsList.moving }
                }

                Text {
                    text: tr("home.chat.online") + " (" + onlineList.count + ")"
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                    font.bold: true
                    Layout.fillWidth: true
                }

                ListView {
                    id: onlineList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 7
                    reuseItems: true
                    boundsBehavior: Flickable.StopAtBounds
                    maximumFlickVelocity: 4200
                    flickDeceleration: 1800
                    model: chatController.onlineUsersModel
                    NumberAnimation {
                        id: onlineWheelAnimation
                        target: onlineList
                        property: "contentY"
                        duration: 170
                        easing.type: Easing.OutCubic
                    }
                    WheelHandler {
                        target: null
                        acceptedDevices: PointerDevice.Mouse
                        onWheel: function(event) { root.smoothWheel(onlineList, onlineWheelAnimation, event) }
                    }
                    delegate: Rectangle {
                        property string rowName: String(name || "")
                        property string rowDetail: String(detail || "")
                        property string rowAvatar: String(avatar || "")
                        property string rowMention: String(mention || "")
                        property string rowDiscordId: String(discordId || "")

                        width: onlineList.width
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
                                clip: true
                                Image {
                                    anchors.fill: parent
                                    anchors.margins: 1
                                    source: rowAvatar
                                    fillMode: Image.PreserveAspectCrop
                                    asynchronous: true
                                    cache: false
                                    sourceSize.width: 48
                                    sourceSize.height: 48
                                    visible: rowAvatar !== ""
                                }
                                Text {
                                    anchors.centerIn: parent
                                    text: (rowName || "?").substring(0, 2).toUpperCase()
                                    color: "#5eead4"
                                    font.bold: true
                                    font.pixelSize: 12
                                    visible: rowAvatar === ""
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                Text { text: rowName; color: "#edf6ff"; font.family: "Segoe UI"; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                Text { text: rowDetail || ("@" + rowMention); color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                            }
                        }
                    }
                    ScrollBar.vertical: ScrollBar { active: onlineList.moving }
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
                            root.preservingOlderMessages = true
                            root.stickMessagesToBottom = false
                            root.olderContentHeight = messageList.contentHeight
                            root.olderContentY = messageList.contentY
                            chatController.loadOlderMessages()
                        }
                    }
                }

                Item {
                    id: messageListFrame
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    ListView {
                        id: messageList
                        width: messageListFrame.width
                        height: Math.min(messageListFrame.height, Math.max(1, contentHeight))
                        y: Math.max(0, messageListFrame.height - height)
                        clip: true
                        spacing: 8
                        boundsBehavior: Flickable.StopAtBounds
                        boundsMovement: Flickable.StopAtBounds
                        maximumFlickVelocity: 5600
                        flickDeceleration: 1650
                        cacheBuffer: Math.max(700, height * 1.2)
                        model: chatController.messagesModel
                        NumberAnimation {
                            id: messageWheelAnimation
                            target: messageList
                            property: "contentY"
                            duration: 220
                            easing.type: Easing.OutCubic
                            onStopped: root.enforceMessageScrollBounds()
                        }
                        WheelHandler {
                            target: null
                            onWheel: function(event) {
                                root.stickMessagesToBottom = false
                                root.smoothWheel(messageList, messageWheelAnimation, event)
                            }
                        }
                        onContentYChanged: {
                            root.enforceMessageScrollBounds()
                            root.updateMessageStickState()
                        }
                        onHeightChanged: {
                            root.enforceMessageScrollBounds()
                            root.updateMessageStickState()
                        }
                        onContentHeightChanged: {
                            if (root.stickMessagesToBottom && !root.preservingOlderMessages)
                                Qt.callLater(root.scrollMessagesToBottom)
                            else {
                                Qt.callLater(root.enforceMessageScrollBounds)
                                root.updateMessageStickState()
                            }
                        }
                        onCountChanged: Qt.callLater(root.enforceMessageScrollBounds)
                        onMovementEnded: root.enforceMessageScrollBounds()
                        delegate: Rectangle {
                            property string rowId: String(model.id || "")
                            property string rowAuthor: String(author || "")
                            property string rowBody: String(body || "")
                            property string rowMeta: String(meta || "")
                            property string rowAvatar: String(avatar || "")
                            property string rowMediaUrl: String(mediaUrl || "")
                            property string rowReplyToId: String(replyToMessageId || "")
                            property string rowReplyToAuthor: String(replyToAuthor || "")
                            property string rowReplyToBody: String(replyToBody || "")
                            property string rowAuthorDiscordId: String(authorDiscordId || "")
                            property bool rowIsGif: Boolean(isGif)
                            property bool rowMentioned: Boolean(mentioned)
                            property bool rowMine: Boolean(mine)

                            width: messageList.width
                            implicitHeight: Math.max(58, messageCardColumn.implicitHeight + 20)
                            height: implicitHeight
                            radius: 8
                            color: rowId === root.highlightMessageId || rowMentioned ? "#2a3b22" : (hoverMsg.hovered ? "#122036" : (rowMine ? "#0a1321" : "transparent"))
                            border.color: rowMentioned ? "#ffd166" : "transparent"
                            Behavior on color { ColorAnimation { duration: 120 } }

                            HoverHandler { id: hoverMsg }

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
                                    visible: rowReplyToId !== ""
                                    MouseArea {
                                        id: hoverReplyTarget
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: root.scrollToMessage(rowReplyToId)
                                    }
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 4
                                        spacing: 4
                                        Text { text: "< " + rowReplyToAuthor; color: "#8ab4ff"; font.bold: true; font.pixelSize: 10 }
                                        Text { text: rowReplyToBody; color: "#99abc4"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
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
                                        clip: true
                                        Image {
                                            anchors.fill: parent
                                            anchors.margins: 1
                                            source: rowAvatar
                                            fillMode: Image.PreserveAspectCrop
                                            asynchronous: true
                                            cache: false
                                            sourceSize.width: 56
                                            sourceSize.height: 56
                                            visible: rowAvatar !== ""
                                        }
                                        Text {
                                            anchors.centerIn: parent
                                            text: (rowAuthor || "?").substring(0, 2).toUpperCase()
                                            color: "#5eead4"
                                            font.bold: true
                                            font.pixelSize: 13
                                            visible: rowAvatar === ""
                                        }
                                    }
                                    Text { text: rowAuthor; color: "#5eead4"; font.bold: true; font.family: "Segoe UI"; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Text { text: rowMeta; color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 11 }
                                }

                                Flow {
                                    Layout.fillWidth: true
                                    width: Math.max(160, messageList.width - 96)
                                    Repeater {
                                        model: chatController.parseMessageSegments(rowMediaUrl !== "" ? rowBody.replace(rowMediaUrl, "").trim() : rowBody)
                                        delegate: Item {
                                            property var seg: modelData
                                            implicitWidth: content.implicitWidth
                                            implicitHeight: content.implicitHeight
                                            Text {
                                                id: content
                                                text: seg.mention && seg.mention.length > 0 ? ("@" + seg.mention) : seg.text
                                                color: seg.mention && seg.mention.length > 0 ? "#ffd166" : "#edf6ff"
                                                font.family: "Segoe UI"
                                                font.pixelSize: 13
                                                wrapMode: Text.WordWrap
                                                elide: Text.ElideRight
                                            }
                                            MouseArea {
                                                anchors.fill: content
                                                hoverEnabled: true
                                                visible: seg.mention && seg.mention.length > 0
                                                onEntered: {
                                                    var targetWindow = root.window || Qt.application.activeWindow
                                                    var p
                                                    var winX = 0
                                                    var winY = 0
                                                    if (targetWindow) {
                                                        try {
                                                            p = content.mapToItem(targetWindow.contentItem || targetWindow, 0, content.height)
                                                            winX = (typeof targetWindow.x !== 'undefined') ? targetWindow.x : 0
                                                            winY = (typeof targetWindow.y !== 'undefined') ? targetWindow.y : 0
                                                        } catch (e) {
                                                            p = content.mapToItem(null, 0, content.height)
                                                        }
                                                    } else {
                                                        p = content.mapToItem(null, 0, content.height)
                                                    }
                                                    var globalX = (p && p.x ? p.x : 0) + winX
                                                    var globalY = (p && p.y ? p.y : 0) + winY + 4
                                                    var avatar = (seg.user && seg.user.avatar) ? seg.user.avatar : ""
                                                    var online = false
                                                    try {
                                                        online = chatController.userIsOnline ? chatController.userIsOnline(seg.mention) : false
                                                    } catch (e) { online = false }
                                                    chatController.showMentionHover(seg.mention, (seg.user && seg.user.regiment) ? seg.user.regiment : "", avatar, online, globalX, globalY)
                                                }
                                                onExited: chatController.dismissMentionHover()
                                            }
                                        }
                                    }
                                }

                                AnimatedImage {
                                    visible: rowMediaUrl !== "" && rowIsGif
                                    source: rowMediaUrl
                                    playing: visible
                                    asynchronous: true
                                    Layout.preferredWidth: Math.min(420, messageList.width - 48)
                                    Layout.preferredHeight: visible ? 200 : 0
                                    fillMode: Image.PreserveAspectFit
                                    cache: false
                                }

                                Image {
                                    visible: rowMediaUrl !== "" && !rowIsGif
                                    source: rowMediaUrl
                                    asynchronous: true
                                    sourceSize.width: Math.min(420, messageList.width - 48)
                                    sourceSize.height: 200
                                    Layout.preferredWidth: Math.min(420, messageList.width - 48)
                                    Layout.preferredHeight: visible ? 200 : 0
                                    fillMode: Image.PreserveAspectFit
                                    cache: false
                                }
                            }

                            RowLayout {
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.rightMargin: 8
                                anchors.topMargin: 6
                                spacing: 4
                                visible: hoverMsg.hovered
                                z: 2

                                Rectangle {
                                    Layout.preferredWidth: 30
                                    Layout.preferredHeight: 30
                                    radius: 15
                                    color: hoverReply.containsMouse ? "#24486d" : "#1d3353"
                                    Text { anchors.centerIn: parent; text: "<"; font.pixelSize: 14; color: "#edf6ff"; font.bold: true }
                                    MouseArea {
                                        id: hoverReply
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: {
                                            root.replyingTo = rowId
                                            root.replyingToLabel = rowAuthor + ": " + rowBody
                                        }
                                    }
                                }
                            }
                        }
                        ScrollBar.vertical: ScrollBar { active: messageList.moving }
                    }
                }

                ListView {
                    id: mentionList
                    Layout.fillWidth: true
                    Layout.preferredHeight: count > 0 ? 42 : 0
                    orientation: ListView.Horizontal
                    spacing: 8
                    clip: true
                    reuseItems: true
                    model: chatController.mentionSuggestionsModel
                    delegate: Button {
                        property string rowMention: String(mention || "")
                        width: Math.min(180, Math.max(96, mentionText.implicitWidth + 32))
                        height: 34
                        onClicked: {
                            messageInput.text = chatController.applyMention(messageInput.text, rowMention)
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
                            text: "@" + rowMention
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
                        color: "#1d3353"
                        visible: root.replyingTo !== ""
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 8
                            Text { text: tr("home.chat.reply_to") + root.replyingToLabel; color: "#edf6ff"; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                            Text {
                                text: "x"
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
                            Layout.preferredWidth: 44
                            Layout.preferredHeight: 44
                            text: "\uD83D\uDE00"
                            font.pixelSize: 20
                            font.bold: true
                            background: Rectangle {
                                radius: 22
                                color: pickerButton.hovered ? "#1d3353" : "#0e1a2d"
                                border.color: "#24486d"
                            }
                            onClicked: {
                                var pos = pickerButton.mapToItem(root, 0, 0)
                                pickerPopup.x = Math.max(0, pos.x - 140)
                                pickerPopup.y = Math.max(0, pos.y - pickerPopup.height - 10)
                                pickerPopup.open()
                            }
                        }

                        TextField {
                            id: messageInput
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            placeholderText: tr("home.chat.message")
                            color: "#edf6ff"
                            font.pixelSize: 15
                            verticalAlignment: TextInput.AlignVCenter
                            topPadding: 10
                            bottomPadding: 10
                            leftPadding: 15
                            rightPadding: 15
                            selectByMouse: true
                            onTextChanged: chatController.updateMentionSuggestions(text)
                            onAccepted: {
                                if (text.trim().length > 0) {
                                    if (root.replyingTo !== "") {
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
                            background: Rectangle { radius: 22; color: "#0e1a2d"; border.color: "#2d496f" }
                        }
                    }
                }
            }
        }
    }
}
