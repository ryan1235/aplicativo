import re

with open(r'qml/pages/ChatPage.qml', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add scrollToMessage function to root
root_target = '''    function tr(key) {'''
root_replacement = '''    function scrollToMessage(msgId) {
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

    function tr(key) {'''
code = code.replace(root_target, root_replacement)


# 2. Make reply banner clickable
reply_banner_target = '''                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 20
                                        color: "#1a293e"
                                        radius: 4
                                        visible: modelData.replyToMessageId !== ""
                                        RowLayout {'''

reply_banner_replacement = '''                                    Rectangle {
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
                                        RowLayout {'''
code = code.replace(reply_banner_target, reply_banner_replacement)


# 3. Fix Images/GIFs
img_target = '''                                    AnimatedImage {
                                        visible: modelData.mediaUrl !== "" && modelData.isGif
                                        source: modelData.mediaUrl
                                        playing: visible
                                        asynchronous: true
                                        Layout.preferredWidth: Math.min(420, messageScroll.width - 48)
                                        Layout.preferredHeight: visible ? Math.min(230, implicitHeight > 0 ? implicitHeight : 180) : 0
                                        fillMode: Image.PreserveAspectFit
                                        cache: true
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
                                        cache: true
                                    }'''

img_replacement = '''                                    AnimatedImage {
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
                                    }'''
code = code.replace(img_target, img_replacement)


# 4. Remove Reactions repeater
react_repeater_target = '''                                    RowLayout {
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
                                    }'''
code = code.replace(react_repeater_target, "")


# 5. Remove React button from hover action row
react_btn_target = '''                                    Rectangle {
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
                                    }'''
code = code.replace(react_btn_target, "")


with open(r'qml/pages/ChatPage.qml', 'w', encoding='utf-8') as f:
    f.write(code)

print('Patched successfully')
