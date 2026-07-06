import re

with open(r'qml/pages/ChatPage.qml', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add reply header inside messageCardColumn
old_message_card = '''                                ColumnLayout {
                                    id: messageCardColumn
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: 10
                                    spacing: 6
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 12'''
new_message_card = '''                                ColumnLayout {
                                    id: messageCardColumn
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: 10
                                    spacing: 6
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 20
                                        color: "#1a293e"
                                        radius: 4
                                        visible: modelData.replyToMessageId !== ""
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
                                        spacing: 12'''
code = code.replace(old_message_card, new_message_card)

# 2. Add Reactions row at the bottom of the message
old_bottom = '''                                    Image {
                                        visible: modelData.mediaUrl !== "" && !modelData.isGif
                                        source: modelData.mediaUrl
                                        asynchronous: true
                                        sourceSize.width: Math.min(420, messageScroll.width - 48)
                                        sourceSize.height: 220
                                        Layout.preferredWidth: Math.min(420, messageScroll.width - 48)
                                        Layout.preferredHeight: visible ? 220 : 0
                                        fillMode: Image.PreserveAspectFit
                                        cache: true
                                    }
                                }'''
new_bottom = '''                                    Image {
                                        visible: modelData.mediaUrl !== "" && !modelData.isGif
                                        source: modelData.mediaUrl
                                        asynchronous: true
                                        sourceSize.width: Math.min(420, messageScroll.width - 48)
                                        sourceSize.height: 220
                                        Layout.preferredWidth: Math.min(420, messageScroll.width - 48)
                                        Layout.preferredHeight: visible ? 220 : 0
                                        fillMode: Image.PreserveAspectFit
                                        cache: true
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 6
                                        visible: modelData.reactions && modelData.reactions.length > 0
                                        Repeater {
                                            model: modelData.reactions || []
                                            delegate: Rectangle {
                                                Layout.preferredHeight: 22
                                                Layout.preferredWidth: reactText.implicitWidth + 12
                                                radius: 4
                                                color: modelData.me ? "#24486d" : "#122036"
                                                border.color: modelData.me ? "#5eead4" : "#1d3353"
                                                RowLayout {
                                                    anchors.fill: parent
                                                    anchors.margins: 4
                                                    spacing: 4
                                                    Text { id: reactText; text: modelData.emoji + " " + modelData.count; color: "#edf6ff"; font.pixelSize: 11; font.bold: true }
                                                }
                                                MouseArea {
                                                    anchors.fill: parent
                                                    onClicked: chatController.reactMessage(modelData.id, modelData.emoji) // toggle reaction
                                                }
                                            }
                                        }
                                    }
                                }
                                
                                // Hover action row (Reply, React, Whisper)
                                RowLayout {
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.rightMargin: 8
                                    anchors.topMargin: -12
                                    spacing: 4
                                    visible: mouseMsg.containsMouse
                                    Rectangle {
                                        Layout.preferredWidth: 30
                                        Layout.preferredHeight: 30
                                        radius: 15
                                        color: hoverReact.containsMouse ? "#24486d" : "#1d3353"
                                        Text { anchors.centerIn: parent; text: "😀"; font.pixelSize: 14 }
                                        MouseArea {
                                            id: hoverReact
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            onClicked: chatController.reactMessage(modelData.id, "👍") // default reaction
                                        }
                                    }
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
                                }'''

code = code.replace(old_bottom, new_bottom)

# Add replying properties to root
root_start = '''Rectangle {
    id: root
    color: "transparent"
    property int lastMessageCount: 0'''
new_root_start = '''Rectangle {
    id: root
    color: "transparent"
    property int lastMessageCount: 0
    property string replyingTo: ""
    property string replyingToLabel: ""'''
code = code.replace(root_start, new_root_start)

# Add Reply UI above message input
input_row = '''                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Layout.preferredHeight: 46'''
new_input_row = '''                ColumnLayout {
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
                            Text { text: "↩ Resposta para: " + root.replyingToLabel; color: "#edf6ff"; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                            Text {
                                text: "✕"
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
                    Layout.preferredHeight: 46'''
code = code.replace(input_row, new_input_row)

# Update the input send logic
send_logic = '''                            onAccepted: {
                                if (text.trim().length > 0) {
                                    chatController.sendMessage(text)
                                    text = ""
                                }
                            }'''
new_send_logic = '''                            onAccepted: {
                                if (text.trim().length > 0) {
                                    if (root.replyingTo !== "") {
                                        chatController.sendMessageReply(text, root.replyingTo)
                                        root.replyingTo = ""
                                        root.replyingToLabel = ""
                                    } else {
                                        chatController.sendMessage(text)
                                    }
                                    text = ""
                                }
                            }'''
code = code.replace(send_logic, new_send_logic)

send_btn_logic = '''                        onClicked: {
                            if (messageInput.text.trim().length > 0) {
                                chatController.sendMessage(messageInput.text)
                                messageInput.text = ""
                            }
                        }'''
new_send_btn_logic = '''                        onClicked: {
                            if (messageInput.text.trim().length > 0) {
                                if (root.replyingTo !== "") {
                                    chatController.sendMessageReply(messageInput.text, root.replyingTo)
                                    root.replyingTo = ""
                                    root.replyingToLabel = ""
                                } else {
                                    chatController.sendMessage(messageInput.text)
                                }
                                messageInput.text = ""
                            }
                        }'''
code = code.replace(send_btn_logic, new_send_btn_logic)

# Close ColumnLayout for input_row patch
code = code.replace('''                ListView {
                    id: mentionList''', '''                }
                ListView {
                    id: mentionList''')

with open(r'qml/pages/ChatPage.qml', 'w', encoding='utf-8') as f:
    f.write(code)

print('Patched UI successfully')
