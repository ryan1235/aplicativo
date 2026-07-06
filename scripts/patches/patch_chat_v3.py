import re

with open(r'qml/pages/ChatPage.qml', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add properties to root
root_target = '''    property int lastMessageCount: 0
    property string replyingTo: ""
    property string replyingToLabel: ""'''
root_replacement = '''    property int lastMessageCount: 0
    property string replyingTo: ""
    property string replyingToLabel: ""
    property string reactingToMsgId: ""
    property string whisperingTo: ""
    property string whisperingToLabel: ""'''
code = code.replace(root_target, root_replacement)

# 2. Update pickerPopup
picker_target = '''                                onClicked: {
                                    messageInput.text += modelData
                                    pickerPopup.close()
                                    messageInput.forceActiveFocus()
                                }'''
picker_replacement = '''                                onClicked: {
                                    if (root.reactingToMsgId !== "") {
                                        chatController.reactMessage(root.reactingToMsgId, modelData)
                                        root.reactingToMsgId = ""
                                        pickerPopup.close()
                                    } else {
                                        messageInput.text += modelData
                                        pickerPopup.close()
                                        messageInput.forceActiveFocus()
                                    }
                                }'''
code = code.replace(picker_target, picker_replacement)

# 3. Change MouseArea to HoverHandler and add Whisper button
hover_target = '''                                MouseArea {
                                    id: mouseMsg
                                    anchors.fill: parent
                                    hoverEnabled: true
                                }

                                ColumnLayout {'''
hover_replacement = '''                                HoverHandler {
                                    id: hoverMsg
                                }

                                ColumnLayout {'''
code = code.replace(hover_target, hover_replacement)

# 4. Update the hover action row
action_target = '''                                // Hover action row (Reply, React, Whisper)
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
action_replacement = '''                                // Hover action row (Reply, React, Whisper)
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
                                        color: hoverReact.containsMouse ? "#24486d" : "#1d3353"
                                        Text { anchors.centerIn: parent; text: "😀"; font.pixelSize: 14 }
                                        MouseArea {
                                            id: hoverReact
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            onClicked: {
                                                root.reactingToMsgId = modelData.id
                                                var pos = hoverReact.mapToItem(root, 0, 0)
                                                pickerPopup.x = Math.max(0, pos.x - 140)
                                                pickerPopup.y = Math.max(0, pos.y - pickerPopup.height - 10)
                                                pickerPopup.open()
                                            }
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
                                }'''
code = code.replace(action_target, action_replacement)

# Fix hovering background color logic
bg_target = '''                                color: modelData.mentioned ? "#2a3b22" : (mouseMsg.containsMouse ? "#122036" : (modelData.mine ? "#0a1321" : "transparent"))'''
bg_replacement = '''                                color: modelData.mentioned ? "#2a3b22" : (hoverMsg.hovered ? "#122036" : (modelData.mine ? "#0a1321" : "transparent"))'''
code = code.replace(bg_target, bg_replacement)

# 5. Add whisper UI to input row
input_target = '''                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        radius: 6
                        color: "#1d3353"
                        visible: root.replyingTo !== ""'''
input_replacement = '''                    Rectangle {
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
                        visible: root.replyingTo !== ""'''
code = code.replace(input_target, input_replacement)

# 6. Update send logic
send_target = '''                        onAccepted: {
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
                        }'''
send_replacement = '''                        onAccepted: {
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
                        }'''
code = code.replace(send_target, send_replacement)

send_btn_target = '''                        onClicked: {
                            if (messageInput.text.trim().length > 0) {
                                if (root.replyingTo !== "") {
                                    chatController.sendMessageReply(messageInput.text, root.replyingTo)
                                    root.replyingTo = ""
                                    root.replyingToLabel = ""
                                } else {
                                    chatController.sendMessage(messageInput.text)
                                }
                                messageInput.text = ""
                                chatController.updateMentionSuggestions("")
                            }
                        }'''
send_btn_replacement = '''                        onClicked: {
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
                        }'''
code = code.replace(send_btn_target, send_btn_replacement)


with open(r'qml/pages/ChatPage.qml', 'w', encoding='utf-8') as f:
    f.write(code)

print('Patched successfully')
