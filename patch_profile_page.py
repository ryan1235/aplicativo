import os

code = '''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import "../components"

Rectangle {
    id: root
    color: "transparent"

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    onVisibleChanged: {
        if (visible) {
            chatController.fetchProfile()
        }
    }

    property var profile: chatController.userProfile || {}

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: Math.min(600, parent.width - 40)
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.margins: 20
            spacing: 20

            // Header Card
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 280
                radius: 8
                color: "#111c31"
                border.color: "#24486d"
                clip: true

                // Banner
                Rectangle {
                    id: bannerRect
                    width: parent.width
                    height: 120
                    color: profile.accentColor ? profile.accentColor : "#1a293e"
                    
                    Image {
                        anchors.fill: parent
                        source: profile.banner ? profile.banner : ""
                        fillMode: Image.PreserveAspectCrop
                        visible: profile.banner !== undefined && profile.banner !== null
                    }
                }

                // Avatar
                Rectangle {
                    id: avatarContainer
                    width: 100
                    height: 100
                    radius: 50
                    color: "#1d3353"
                    border.color: "#111c31"
                    border.width: 4
                    anchors.bottom: bannerRect.bottom
                    anchors.bottomMargin: -50
                    anchors.left: parent.left
                    anchors.leftMargin: 30

                    Rectangle {
                        id: maskAvatar
                        anchors.fill: parent
                        anchors.margins: 4
                        radius: 46
                        visible: false
                    }
                    Image {
                        id: imgAvatar
                        anchors.fill: maskAvatar
                        source: profile.avatarfull ? profile.avatarfull : chatController.currentUserAvatar
                        fillMode: Image.PreserveAspectCrop
                        visible: false
                    }
                    OpacityMask {
                        anchors.fill: maskAvatar
                        source: imgAvatar
                        maskSource: maskAvatar
                        visible: imgAvatar.source != ""
                    }
                }

                // Logout Button
                PrimaryButton {
                    text: "Sair"
                    anchors.right: parent.right
                    anchors.top: bannerRect.bottom
                    anchors.topMargin: 15
                    anchors.rightMargin: 20
                    onClicked: {
                        chatController.logout()
                        appController.setCurrentPage("chat")
                    }
                }

                // Info
                ColumnLayout {
                    anchors.left: parent.left
                    anchors.leftMargin: 30
                    anchors.top: avatarContainer.bottom
                    anchors.topMargin: 10
                    spacing: 4

                    RowLayout {
                        spacing: 8
                        Text {
                            text: profile.globalName || profile.displayName || chatController.currentUserName || "Usuário"
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 24
                            font.bold: true
                        }
                        Rectangle {
                            visible: profile.role !== undefined && profile.role !== null && profile.role !== ""
                            color: "#5eead4"
                            radius: 4
                            Layout.preferredHeight: 20
                            Layout.preferredWidth: roleText.implicitWidth + 12
                            Text {
                                id: roleText
                                anchors.centerIn: parent
                                text: profile.role || ""
                                color: "#0a1321"
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }
                    }

                    Text {
                        text: "@" + (profile.username || chatController.currentUserName || "unknown")
                        color: "#99abc4"
                        font.family: "Segoe UI"
                        font.pixelSize: 14
                    }
                }
            }

            // Body Info
            RowLayout {
                Layout.fillWidth: true
                spacing: 20

                // Left Col - Stats
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 180
                    radius: 8
                    color: "#111c31"
                    border.color: "#24486d"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 12

                        Text {
                            text: "Estatísticas"
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                        }

                        RowLayout {
                            spacing: 10
                            Text { text: "📦 Atualizações de Estoque:"; color: "#99abc4"; font.pixelSize: 14 }
                            Text { text: (profile.stockUpdateHelpCount || 0).toString(); color: "#5eead4"; font.bold: true; font.pixelSize: 14 }
                        }

                        RowLayout {
                            spacing: 10
                            Text { text: "🕒 Tempo Online (Segundos):"; color: "#99abc4"; font.pixelSize: 14 }
                            Text { text: (profile.totalOnlineSeconds || 0).toString(); color: "#5eead4"; font.bold: true; font.pixelSize: 14 }
                        }
                        
                        Item { Layout.fillHeight: true }
                    }
                }

                // Right Col - Regiment
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 180
                    radius: 8
                    color: "#111c31"
                    border.color: "#24486d"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 12

                        Text {
                            text: "Regimento"
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                        }

                        TextField {
                            id: regimentInput
                            Layout.fillWidth: true
                            placeholderText: "Ex: [BR] Logi"
                            text: profile.regiment || ""
                            color: "#edf6ff"
                            background: Rectangle {
                                color: "#0e1a2d"
                                radius: 4
                                border.color: regimentInput.activeFocus ? "#5eead4" : "#1d3353"
                            }
                        }

                        PrimaryButton {
                            text: "Atualizar Regimento"
                            Layout.alignment: Qt.AlignRight
                            onClicked: {
                                chatController.updateRegiment(regimentInput.text)
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }
            }
            
            Item { Layout.preferredHeight: 40 }
        }
    }
}
'''

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qml\pages\ProfilePage.qml', 'w', encoding='utf-8') as f:
    f.write(code)

print("ProfilePage.qml patched")
