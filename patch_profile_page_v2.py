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

    function formatTime(seconds) {
        if (!seconds || seconds <= 0) return "0s";
        var d = Math.floor(seconds / (3600*24));
        var h = Math.floor(seconds % (3600*24) / 3600);
        var m = Math.floor(seconds % 3600 / 60);
        
        var res = [];
        if (d > 0) res.push(d + "d");
        if (h > 0) res.push(h + "h");
        if (m > 0) res.push(m + "m");
        if (d === 0 && h === 0 && m === 0) res.push(seconds + "s");
        return res.join(" ");
    }

    function formatDate(isoString) {
        if (!isoString) return "-";
        var date = new Date(isoString);
        return date.toLocaleString();
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: Math.min(650, parent.width - 40)
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.margins: 20
            spacing: 24

            // Top Header Card
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 320
                radius: 12
                color: "#0a1321"
                border.color: "#1d3353"
                border.width: 1
                clip: true

                // Banner
                Rectangle {
                    id: bannerRect
                    width: parent.width
                    height: 140
                    color: profile.accentColor ? profile.accentColor : "#1a293e"
                    
                    Image {
                        anchors.fill: parent
                        source: profile.banner ? profile.banner : ""
                        fillMode: Image.PreserveAspectCrop
                        visible: profile.banner !== undefined && profile.banner !== null
                    }
                    
                    // Gradient overlay for smoother transition
                    Rectangle {
                        anchors.fill: parent
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 1.0; color: "#0a1321" }
                        }
                    }
                }

                // Avatar
                Rectangle {
                    id: avatarContainer
                    width: 120
                    height: 120
                    radius: 60
                    color: "#1d3353"
                    border.color: "#0a1321"
                    border.width: 6
                    anchors.bottom: bannerRect.bottom
                    anchors.bottomMargin: -60
                    anchors.left: parent.left
                    anchors.leftMargin: 30

                    Rectangle {
                        id: maskAvatar
                        anchors.fill: parent
                        anchors.margins: 2
                        radius: 56
                        visible: false
                    }
                    Image {
                        id: imgAvatar
                        anchors.fill: maskAvatar
                        source: profile.avatarfull ? profile.avatarfull : (chatController.currentUserAvatar || "")
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
                Rectangle {
                    width: 100
                    height: 36
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 16
                    radius: 18
                    color: logoutHover.containsMouse ? "#ef4444" : "#1d3353"
                    border.color: logoutHover.containsMouse ? "#f87171" : "transparent"
                    border.width: 1
                    Behavior on color { ColorAnimation { duration: 150 } }
                    
                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        Text { text: "Sair"; color: "#edf6ff"; font.family: "Segoe UI"; font.bold: true; font.pixelSize: 13 }
                    }
                    MouseArea {
                        id: logoutHover
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            chatController.logout()
                            appController.setCurrentPage("chat")
                        }
                    }
                }

                // Info Section
                ColumnLayout {
                    anchors.left: parent.left
                    anchors.leftMargin: 30
                    anchors.top: avatarContainer.bottom
                    anchors.topMargin: 15
                    spacing: 4

                    RowLayout {
                        spacing: 12
                        Text {
                            text: profile.globalName || profile.displayName || chatController.currentUserName || "Usuário"
                            color: "#ffffff"
                            font.family: "Segoe UI"
                            font.pixelSize: 28
                            font.bold: true
                        }
                        Rectangle {
                            visible: profile.role !== undefined && profile.role !== null && profile.role !== ""
                            color: "#5eead4"
                            radius: 6
                            Layout.preferredHeight: 22
                            Layout.preferredWidth: roleText.implicitWidth + 16
                            Text {
                                id: roleText
                                anchors.centerIn: parent
                                text: profile.role || ""
                                color: "#0a1321"
                                font.pixelSize: 12
                                font.bold: true
                                font.letterSpacing: 0.5
                            }
                        }
                    }

                    Text {
                        text: "@" + (profile.username || chatController.currentUserName || "unknown")
                        color: "#99abc4"
                        font.family: "Segoe UI"
                        font.pixelSize: 15
                    }
                }
            }

            // Two Columns Layout
            RowLayout {
                Layout.fillWidth: true
                spacing: 24

                // Left Col - Stats & Info
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 250
                    radius: 12
                    color: "#0a1321"
                    border.color: "#1d3353"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 16

                        Text {
                            text: "Visão Geral"
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                        }
                        
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: "#1d3353"
                        }

                        GridLayout {
                            columns: 2
                            rowSpacing: 16
                            columnSpacing: 12
                            Layout.fillWidth: true

                            // Row 1
                            Text { text: "📦 Atualizações de Estoque:"; color: "#99abc4"; font.pixelSize: 14 }
                            Text { text: (profile.stockUpdateHelpCount || 0).toString(); color: "#5eead4"; font.bold: true; font.pixelSize: 14 }

                            // Row 2
                            Text { text: "🕒 Tempo Online:"; color: "#99abc4"; font.pixelSize: 14 }
                            Text { text: formatTime(profile.totalOnlineSeconds); color: "#5eead4"; font.bold: true; font.pixelSize: 14 }
                            
                            // Row 3
                            Text { text: "🚪 Último Login:"; color: "#99abc4"; font.pixelSize: 14 }
                            Text { text: formatDate(profile.lastLoginAt); color: "#5eead4"; font.bold: true; font.pixelSize: 14 }
                            
                            // Row 4
                            Text { text: "📅 Conta Criada:"; color: "#99abc4"; font.pixelSize: 14; visible: profile.createdAt }
                            Text { text: formatDate(profile.createdAt); color: "#5eead4"; font.bold: true; font.pixelSize: 14; visible: profile.createdAt }
                        }
                        
                        Item { Layout.fillHeight: true }
                    }
                }

                // Right Col - Regiment
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 250
                    radius: 12
                    color: "#0a1321"
                    border.color: "#1d3353"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 16

                        Text {
                            text: "Regimento"
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                        }
                        
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: "#1d3353"
                        }
                        
                        Text {
                            text: "Selecione o seu esquadrão logístico ou regimento militar atual."
                            color: "#99abc4"
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        ComboBox {
                            id: regimentCombo
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            model: ["Nenhum", "CIB", "STORM", "WRG", "LIDA", "7CMD", "FELB", "GDO", "DOG'Z", "REQ (MeTaL)"]
                            
                            Component.onCompleted: {
                                var current = profile.regiment || "Nenhum";
                                var idx = find(current);
                                if (idx === -1) idx = 0;
                                currentIndex = idx;
                            }
                            
                            // Elegant ComboBox styling
                            background: Rectangle {
                                color: "#122036"
                                radius: 6
                                border.color: regimentCombo.activeFocus ? "#5eead4" : "#1d3353"
                                border.width: 1
                            }
                            contentItem: Text {
                                text: regimentCombo.currentText
                                color: "#edf6ff"
                                font.pixelSize: 14
                                font.bold: true
                                verticalAlignment: Text.AlignVCenter
                                anchors.left: parent.left
                                anchors.leftMargin: 12
                            }
                        }

                        Item { Layout.fillHeight: true }

                        PrimaryButton {
                            text: "Atualizar Regimento"
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            onClicked: {
                                var val = regimentCombo.currentText;
                                if (val === "Nenhum") val = "";
                                chatController.updateRegiment(val)
                            }
                        }
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

print("ProfilePage.qml updated")
