import QtQuick
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

    function safeImageSource(value, fallback) {
        var text = String(value || "")
        if (text.indexOf("http://") === 0 || text.indexOf("https://") === 0 || text.indexOf("file:") === 0 || text.indexOf("qrc:") === 0 || text.indexOf("data:") === 0)
            return text
        return fallback || ""
    }

    onVisibleChanged: {
        if (visible) {
            chatController.ensureStarted()
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
        return date.toLocaleDateString() + " " + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            // Utilizando quase todo o espaÃ§o disponÃ­vel
            width: parent.width - 40
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.margins: 20
            spacing: 24

            // Top Header Card
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 320
                radius: 12
                color: settingsController.backgroundColor
                border.color: settingsController.controlColor
                border.width: 1
                clip: true

                // Banner
                Rectangle {
                    id: bannerRect
                    width: parent.width
                    height: 140
                    color: profile.accentColor ? profile.accentColor : settingsController.surfaceRaisedColor
                    
                    Image {
                        anchors.fill: parent
                        // Fallback pra imagem bonitona da web se nÃ£o tiver banner
                        source: safeImageSource(profile.banner, "https://images.unsplash.com/photo-1614850523459-c2f4c699c52e?q=80&w=1200&auto=format&fit=crop")
                        fillMode: Image.PreserveAspectCrop
                        visible: true
                    }
                    
                    // Gradient overlay for smoother transition
                    Rectangle {
                        anchors.fill: parent
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 1.0; color: settingsController.backgroundColor }
                        }
                    }
                }

                // Avatar
                Rectangle {
                    id: avatarContainer
                    width: 120
                    height: 120
                    radius: 60
                    color: settingsController.controlColor
                    border.color: settingsController.backgroundColor
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
                        source: safeImageSource(profile.avatarfull || profile.avatarUrl || profile.avatarmedium || chatController.currentUserAvatar, "")
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
                    color: logoutHover.containsMouse ? settingsController.dangerColor : settingsController.controlColor
                    border.color: logoutHover.containsMouse ? settingsController.dangerColor : "transparent"
                    border.width: 1
                    Behavior on color { ColorAnimation { duration: 150 } }
                    
                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        Text { text: tr("profile.logout"); color: settingsController.textColor; font.family: "Segoe UI"; font.bold: true; font.pixelSize: 13 }
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
                            text: profile.globalName || profile.displayName || chatController.currentUserName || tr("profile.default_user")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 28
                            font.bold: true
                        }
                        Rectangle {
                            visible: profile.role !== undefined && profile.role !== null && profile.role !== ""
                            color: settingsController.accentColor
                            radius: 6
                            Layout.preferredHeight: 22
                            Layout.preferredWidth: roleText.implicitWidth + 16
                            Text {
                                id: roleText
                                anchors.centerIn: parent
                                text: profile.role || ""
                                color: settingsController.backgroundColor
                                font.pixelSize: 12
                                font.bold: true
                                font.letterSpacing: 0.5
                            }
                        }
                    }

                    Text {
                        text: "@" + (profile.username || chatController.currentUserName || tr("profile.unknown_user"))
                        color: settingsController.mutedTextColor
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
                    color: settingsController.backgroundColor
                    border.color: settingsController.controlColor
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 16

                        Text {
                            text: tr("profile.overview")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                        }
                        
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: settingsController.controlColor
                        }

                        // SubstituÃ­do GridLayout por ColumnLayout -> RowLayout para evitar cortes de texto longo
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 14

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: tr("profile.stock_updates"); color: settingsController.mutedTextColor; font.pixelSize: 14 }
                                Item { Layout.fillWidth: true }
                                Text { text: (profile.stockUpdateHelpCount || 0).toString(); color: settingsController.accentColor; font.bold: true; font.pixelSize: 14 }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: tr("profile.online_time"); color: settingsController.mutedTextColor; font.pixelSize: 14 }
                                Item { Layout.fillWidth: true }
                                Text { text: formatTime(profile.totalOnlineSeconds); color: settingsController.accentColor; font.bold: true; font.pixelSize: 14 }
                            }
                            
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: tr("profile.last_login"); color: settingsController.mutedTextColor; font.pixelSize: 14 }
                                Item { Layout.fillWidth: true }
                                Text { 
                                    text: formatDate(profile.lastLoginAt)
                                    color: settingsController.accentColor
                                    font.bold: true
                                    font.pixelSize: 14
                                    elide: Text.ElideRight
                                    Layout.maximumWidth: 200
                                }
                            }
                            
                            RowLayout {
                                Layout.fillWidth: true
                                visible: profile.createdAt !== undefined
                                Text { text: tr("profile.created_at"); color: settingsController.mutedTextColor; font.pixelSize: 14 }
                                Item { Layout.fillWidth: true }
                                Text { 
                                    text: formatDate(profile.createdAt)
                                    color: settingsController.accentColor
                                    font.bold: true
                                    font.pixelSize: 14 
                                    elide: Text.ElideRight
                                    Layout.maximumWidth: 200
                                }
                            }
                        }
                        
                        Item { Layout.fillHeight: true }
                    }
                }

                // Right Col - Regiment
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 250
                    radius: 12
                    color: settingsController.backgroundColor
                    border.color: settingsController.controlColor
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 16

                        Text {
                            text: tr("profile.regiment")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                        }
                        
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: settingsController.controlColor
                        }
                        
                        Text {
                            text: tr("profile.regiment_hint")
                            color: settingsController.mutedTextColor
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        PrimaryComboBox {
                            id: regimentCombo
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            model: [tr("profile.regiment_none"), "STORM", "WRG", "LIDA", "7CMD", "FELB", "GDO", "DOGZ", "REQ"]
                            
                            Component.onCompleted: {
                                var current = profile.regiment || tr("profile.regiment_none");
                                var idx = find(current);
                                if (idx === -1) idx = 0;
                                currentIndex = idx;
                            }
                            
                            // Elegant ComboBox styling
                            background: Rectangle {
                                color: settingsController.surfaceRaisedColor
                                radius: 6
                                border.color: regimentCombo.activeFocus ? settingsController.accentColor : settingsController.controlColor
                                border.width: 1
                            }
                            contentItem: Text {
                                text: regimentCombo.currentText
                                color: settingsController.textColor
                                font.pixelSize: 14
                                font.bold: true
                                verticalAlignment: Text.AlignVCenter
                                anchors.left: parent.left
                                anchors.leftMargin: 12
                            }
                        }

                        Item { Layout.fillHeight: true }

                        PrimaryButton {
                            id: updateBtn
                            text: tr("profile.update_regiment")
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            onClicked: {
                                var val = regimentCombo.currentText;
                                if (val === tr("profile.regiment_none")) val = "";
                                chatController.updateRegiment(val)
                                updateBtn.text = tr("profile.saved_success")
                                updateTimer.start()
                            }
                        }

                        Timer {
                            id: updateTimer
                            interval: 2000
                            onTriggered: updateBtn.text = tr("profile.update_regiment")
                        }
                    }
                }
            }
            
            // Painel Administrativo
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 60
                radius: 12
                color: settingsController.controlColor
                border.color: settingsController.accentColor
                border.width: 1
                visible: chatController.canOpenAdminPanel

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    Text {
                        text: tr("profile.admin_panel")
                        color: settingsController.accentColor
                        font.family: "Segoe UI"
                        font.pixelSize: 16
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    PrimaryButton {
                        text: tr("profile.open_panel")
                        Layout.preferredWidth: 150
                        Layout.preferredHeight: 36
                        onClicked: appController.openAdminPanel(chatController.apiToken)
                    }
                }
            }
            
            Item { Layout.preferredHeight: 40 }
        }
    }
}


