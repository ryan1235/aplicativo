import re

with open(r'qml/pages/ChatPage.qml', 'r', encoding='utf-8') as f:
    code = f.read()

# Add whispering properties
root_props = '''    property string replyingTo: ""
    property string replyingToLabel: ""'''
new_root_props = '''    property string replyingTo: ""
    property string replyingToLabel: ""
    property string whisperingTo: ""
    property string whisperingToLabel: ""'''
code = code.replace(root_props, new_root_props)

# Add Whisper button in online users
old_online_card = '''                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 0
                                        Text { text: modelData.name; color: "#edf6ff"; font.family: "Segoe UI"; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Text { text: modelData.detail || ("@" + modelData.mention); color: "#99abc4"; font.family: "Segoe UI"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                    }'''
new_online_card = '''                                    ColumnLayout {
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
                                    }'''
code = code.replace(old_online_card, new_online_card)

# Add Whisper header
input_row = '''                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        radius: 6
                        color: "#1d3353"
                        visible: root.replyingTo !== ""'''
new_input_row = '''                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        radius: 6
                        color: "#2a1532"
                        visible: root.whisperingTo !== ""
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 8
                            Text { text: "🤫 Sussurrando para: " + root.whisperingToLabel; color: "#fbcfe8"; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                            Text {
                                text: "✕"
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
code = code.replace(input_row, new_input_row)

# Update send logic
old_send = '''                                    if (root.replyingTo !== "") {
                                        chatController.sendMessageReply(text, root.replyingTo)
                                        root.replyingTo = ""
                                        root.replyingToLabel = ""
                                    } else {
                                        chatController.sendMessage(text)
                                    }'''
new_send = '''                                    if (root.whisperingTo !== "") {
                                        chatController.sendWhisperToUser(root.whisperingTo, text)
                                        root.whisperingTo = ""
                                        root.whisperingToLabel = ""
                                    } else if (root.replyingTo !== "") {
                                        chatController.sendMessageReply(text, root.replyingTo)
                                        root.replyingTo = ""
                                        root.replyingToLabel = ""
                                    } else {
                                        chatController.sendMessage(text)
                                    }'''
code = code.replace(old_send, new_send)

old_send_btn = '''                                if (root.replyingTo !== "") {
                                    chatController.sendMessageReply(messageInput.text, root.replyingTo)
                                    root.replyingTo = ""
                                    root.replyingToLabel = ""
                                } else {
                                    chatController.sendMessage(messageInput.text)
                                }'''
new_send_btn = '''                                if (root.whisperingTo !== "") {
                                    chatController.sendWhisperToUser(root.whisperingTo, messageInput.text)
                                    root.whisperingTo = ""
                                    root.whisperingToLabel = ""
                                } else if (root.replyingTo !== "") {
                                    chatController.sendMessageReply(messageInput.text, root.replyingTo)
                                    root.replyingTo = ""
                                    root.replyingToLabel = ""
                                } else {
                                    chatController.sendMessage(messageInput.text)
                                }'''
code = code.replace(old_send_btn, new_send_btn)

with open(r'qml/pages/ChatPage.qml', 'w', encoding='utf-8') as f:
    f.write(code)

print('Patched whispers successfully')
