import re

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qml\Main.qml', 'r', encoding='utf-8') as f:
    code = f.read()

profile_card_target = '''                        MouseArea {
                            id: profileMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                if (chatController.currentProvider !== "discord") {
                                    chatController.connectWithDiscord()
                                }
                            }
                        }'''

profile_card_replacement = '''                        MouseArea {
                            id: profileMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                if (chatController.currentProvider === "discord") {
                                    appController.currentView = "profile"
                                } else {
                                    chatController.connectWithDiscord()
                                }
                            }
                        }'''

code = code.replace(profile_card_target, profile_card_replacement)

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qml\Main.qml', 'w', encoding='utf-8') as f:
    f.write(code)

print("Main patched")
