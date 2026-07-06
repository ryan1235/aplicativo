import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Popup {
    id: root
    width: Math.min(600, parent.width - 56)
    height: Math.min(650, parent.height - 56)
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    
    // Properties for form data
    property string newSessionName: ""
    property bool isPrivate: false
    property string newSessionPassword: ""
    property int currentTab: 0 // 0=Ativas, 1=Meus Mapas, 2=Gerenciar
    
    // Properties for management
    property var activeUsers: []
    property var historicUsers: []
    // Model for active sessions
    ListModel {
        id: sessionsModel
    }

    Connections {
        target: typeof mapSessionController !== "undefined" ? mapSessionController : null
        function onRoomsFetched(data) {
            sessionsModel.clear();
            try {
                var rooms = JSON.parse(data);
                for (var i = 0; i < rooms.length; i++) {
                    var r = rooms[i];
                    var c = r.creator || {};
                    sessionsModel.append({
                        roomId: r.id,
                        sessionName: r.name || "Sem Nome",
                        creator: c.personaname || "Desconhecido",
                        isPrivate: r.isPrivate === true,
                        players: r.playersCount || 0
                    });
                }
            } catch (e) {
                console.log("Error parsing rooms", e);
            }
        }
        function onMyRoomsFetched(data) {
            sessionsModel.clear();
            try {
                var rooms = JSON.parse(data);
                for (var i = 0; i < rooms.length; i++) {
                    var r = rooms[i];
                    var c = r.creator || {};
                    sessionsModel.append({
                        roomId: r.id,
                        sessionName: r.name || "Sem Nome",
                        creator: c.personaname || "Desconhecido",
                        isPrivate: r.isPrivate === true,
                        players: r.playersCount || 0
                    });
                }
            } catch (e) {
                console.log("Error parsing my rooms", e);
            }
        }
    }

    onOpened: {
        if (typeof mapSessionController !== "undefined") {
            mapSessionController.fetchRooms();
        }
    }

    background: Rectangle {
        color: Qt.rgba(settingsController.surfaceColor.r, settingsController.surfaceColor.g, settingsController.surfaceColor.b, 0.9)
        radius: 16
        border.color: Qt.rgba(255/255, 255/255, 255/255, 0.1)
        border.width: 1
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 20

        // Header
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "Sessões de Mapa (Multiplayer)"
                font.pixelSize: 22
                font.bold: true
                color: settingsController.textColor
                Layout.fillWidth: true
            }
            Rectangle {
                width: 32
                height: 32
                radius: 16
                color: Qt.rgba(255/255, 255/255, 255/255, 0.05)
                border.color: Qt.rgba(255/255, 255/255, 255/255, 0.1)
                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    color: settingsController.textColor
                    font.pixelSize: 14
                    font.bold: true
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.close()
                    hoverEnabled: true
                    onEntered: parent.color = Qt.rgba(255/255, 255/255, 255/255, 0.1)
                    onExited: parent.color = Qt.rgba(255/255, 255/255, 255/255, 0.05)
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: settingsController.borderColor
        }

        // Tabs for Sessions
        RowLayout {
            Layout.fillWidth: true
            spacing: 20
            
            Text {
                text: "Salas Ativas"
                font.pixelSize: 15
                font.bold: true
                color: root.currentTab === 0 ? settingsController.textColor : settingsController.secondaryTextColor
                
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -10
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.currentTab = 0
                        if (typeof mapSessionController !== "undefined") mapSessionController.fetchRooms();
                    }
                }
            }
            
            Text {
                text: "Minhas Salas"
                font.pixelSize: 15
                font.bold: true
                color: root.currentTab === 1 ? settingsController.textColor : settingsController.secondaryTextColor
                
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -10
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.currentTab = 1
                        if (typeof mapSessionController !== "undefined") mapSessionController.fetchMyRooms();
                    }
                }
            }

            Text {
                text: "Criar Sala"
                font.pixelSize: 15
                font.bold: true
                color: root.currentTab === 2 ? settingsController.textColor : settingsController.secondaryTextColor
                
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -10
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.currentTab = 2
                }
            }
            
            Text {
                text: "⚙ Configurações da Sala"
                font.pixelSize: 15
                font.bold: true
                color: root.currentTab === 3 ? settingsController.accentColor : settingsController.secondaryTextColor
                visible: typeof mapSessionController !== "undefined" && mapSessionController.currentRoom !== "" && (mapSessionController.currentRoomCreator || "").toLowerCase() === (typeof chatController !== "undefined" && chatController.currentUserName ? chatController.currentUserName.toLowerCase() : "")
                
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -10
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.currentTab = 3
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            
            // TAB 0 & 1 (Rooms List) are now handled by a shared component or we just duplicate the listview?
            // Actually, we can put the ListView outside the StackLayout and toggle its model/visibility based on currentTab?
            // No, it's easier to put the ListView in Item 0, and another in Item 1, or just let Item 0 handle both 0 and 1.
            // Let's make StackLayout have 3 items: Item0 (List), Item1 (Create), Item2 (Manage).
            // So currentIndex will be: (root.currentTab === 0 || root.currentTab === 1) ? 0 : (root.currentTab === 2 ? 1 : 2)
            currentIndex: (root.currentTab === 0 || root.currentTab === 1) ? 0 : (root.currentTab === 2 ? 1 : 2)
            
            ColumnLayout {
                spacing: 20
                
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: sessionsModel
                    spacing: 10
                    
                    delegate: Rectangle {
                        width: ListView.view.width
                        height: 70
                        radius: 12
                        color: Qt.rgba(255/255, 255/255, 255/255, 0.03)
                        border.color: Qt.rgba(255/255, 255/255, 255/255, 0.08)
                        border.width: 1
                        
                        MouseArea {
                            id: roomCardHover
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            hoverEnabled: true
                            onEntered: parent.color = Qt.rgba(255/255, 255/255, 255/255, 0.08)
                            onExited: parent.color = Qt.rgba(255/255, 255/255, 255/255, 0.03)
                            onClicked: {
                                if (typeof mapSessionController !== "undefined") {
                                    var pwd = model.isPrivate ? root.newSessionPassword : "";
                                    mapSessionController.joinRoom(model.roomId, pwd, model.creator);
                                    root.close();
                                }
                            }
                        }
                        
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 16
                            
                            Rectangle {
                                width: 40
                                height: 40
                                radius: 20
                                color: Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.2)
                                border.color: settingsController.accentColor
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: model.sessionName.charAt(0).toUpperCase()
                                    color: settingsController.accentColor
                                    font.bold: true
                                    font.pixelSize: 18
                                }
                            }
                            
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: model.sessionName
                                    font.pixelSize: 15
                                    font.bold: true
                                    color: settingsController.textColor
                                }
                                RowLayout {
                                    spacing: 8
                                    Text {
                                        text: "👤 " + model.creator
                                        font.pixelSize: 11
                                        color: settingsController.secondaryTextColor
                                    }
                                    Text {
                                        text: "•"
                                        font.pixelSize: 11
                                        color: settingsController.secondaryTextColor
                                    }
                                    Text {
                                        text: "👥 " + model.players + " online"
                                        font.pixelSize: 11
                                        color: settingsController.secondaryTextColor
                                    }
                                }
                            }
                            
                            Rectangle {
                                width: 80
                                height: 26
                                radius: 13
                                color: model.isPrivate ? Qt.rgba(239/255, 68/255, 68/255, 0.2) : Qt.rgba(16/255, 185/255, 129/255, 0.2)
                                border.color: model.isPrivate ? "#ef4444" : "#10b981"
                                border.width: 1
                                Layout.alignment: Qt.AlignVCenter
                                Text {
                                    anchors.centerIn: parent
                                    text: model.isPrivate ? "🔒 Privado" : "🌐 Público"
                                    font.pixelSize: 11
                                    font.bold: true
                                    color: model.isPrivate ? "#ef4444" : "#10b981"
                                }
                            }
                            
                            PrimaryButton {
                                id: enterBtn
                                text: (typeof chatController !== "undefined" && chatController.currentUserName && model.creator.toLowerCase() === chatController.currentUserName.toLowerCase()) ? "Abrir" : "Entrar"
                                width: 80
                                height: 36
                                Layout.alignment: Qt.AlignVCenter
                                onClicked: {
                                    if (typeof mapSessionController !== "undefined") {
                                        var pwd = model.isPrivate ? root.newSessionPassword : "";
                                        mapSessionController.joinRoom(model.roomId, pwd, model.creator);
                                        root.close();
                                    }
                                }
                            }
                            
                            Rectangle {
                                width: 80
                                height: 36
                                radius: 6
                                color: "#ef4444" // red for delete
                                visible: (typeof chatController !== "undefined" && chatController.currentUserName && model.creator.toLowerCase() === chatController.currentUserName.toLowerCase())
                                Layout.alignment: Qt.AlignVCenter
                                
                                Text {
                                    anchors.centerIn: parent
                                    text: "Excluir"
                                    color: "#ffffff"
                                    font.bold: true
                                    font.pixelSize: 12
                                }
                                
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (typeof mapSessionController !== "undefined") {
                                            mapSessionController.deleteRoom(model.roomId);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            } // End of Tab 0/1 List
            
            // Tab 2: Create Session
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                
                ColumnLayout {
                    width: parent.width
                    spacing: 24

                    Rectangle {
                        Layout.fillWidth: true
                        height: 60
                        color: "transparent"
                        
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Criar uma Nova Sala de Mapa"
                            font.pixelSize: 20
                            font.bold: true
                            color: settingsController.textColor
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 1
                        rowSpacing: 16

                        Text { text: "Nome da Sala:"; color: settingsController.secondaryTextColor; font.pixelSize: 13; font.bold: true }
                        TextField {
                            Layout.fillWidth: true
                            placeholderText: "Ex: Coordenação de Artilharia"
                            color: settingsController.textColor
                            font.pixelSize: 15
                            background: Rectangle {
                                color: Qt.rgba(0,0,0,0.2)
                                radius: 8
                                border.color: settingsController.borderColor
                            }
                            onTextChanged: root.newSessionName = text
                        }

                        Item { Layout.preferredHeight: 8 }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            ToggleSwitch {
                                id: privateToggle
                                checked: root.isPrivate
                                onCheckedChanged: root.isPrivate = checked
                            }
                            ColumnLayout {
                                spacing: 2
                                Text {
                                    text: "Sala Privada"
                                    color: settingsController.textColor
                                    font.pixelSize: 15
                                    font.bold: true
                                }
                                Text {
                                    text: root.isPrivate ? "Somente quem tem a senha poderá entrar" : "A sala será listada publicamente"
                                    color: settingsController.secondaryTextColor
                                    font.pixelSize: 12
                                }
                            }
                        }

                        Item { Layout.preferredHeight: 8 }

                        Text {
                            text: "Senha da Sala:"
                            color: settingsController.secondaryTextColor
                            font.pixelSize: 13
                            font.bold: true
                            visible: root.isPrivate
                        }
                        TextField {
                            Layout.fillWidth: true
                            placeholderText: "Defina uma senha"
                            echoMode: TextInput.Password
                            color: settingsController.textColor
                            font.pixelSize: 15
                            visible: root.isPrivate
                            background: Rectangle {
                                color: Qt.rgba(0,0,0,0.2)
                                radius: 8
                                border.color: settingsController.borderColor
                            }
                            onTextChanged: root.newSessionPassword = text
                        }
                    }

                    Item { Layout.fillHeight: true }

                    PrimaryButton {
                        Layout.fillWidth: true
                        height: 48
                        text: "Criar Sala"
                        onClicked: {
                            if (root.newSessionName.trim() === "") return;
                            if (typeof mapSessionController !== "undefined") {
                                mapSessionController.createRoom(root.newSessionName, root.isPrivate, root.newSessionPassword);
                            }
                            root.close()
                        }
                    }
                }
            } // End of Tab 2
            
            // Tab 2: Manage Room
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                
                ColumnLayout {
                    width: parent.width
                    spacing: 20
                    
                    Text {
                        text: "Configurações da Sala"
                        color: settingsController.textColor
                        font.pixelSize: 16
                        font.bold: true
                    }
                    
                    Text {
                        text: "Alterar Nome da Sala"
                        color: settingsController.secondaryTextColor
                        font.pixelSize: 12
                    }
                    TextField {
                        id: nameInput
                        Layout.fillWidth: true
                        placeholderText: "Novo nome da sala"
                        color: settingsController.textColor
                        background: Rectangle {
                            color: settingsController.backgroundColor
                            radius: 4
                            border.color: nameInput.activeFocus ? settingsController.accentColor : settingsController.borderColor
                        }
                    }
                    Item { Layout.preferredHeight: 8 }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        ToggleSwitch {
                            id: managePrivateToggle
                        }
                        ColumnLayout {
                            spacing: 2
                            Text {
                                text: "Sala Privada"
                                color: settingsController.textColor
                                font.pixelSize: 15
                                font.bold: true
                            }
                            Text {
                                text: managePrivateToggle.checked ? "Requer senha para entrar" : "Pública (qualquer um entra e a senha é removida)"
                                color: settingsController.secondaryTextColor
                                font.pixelSize: 12
                            }
                        }
                    }
                    
                    Item { Layout.preferredHeight: 8 }

                    Text {
                        text: "Nova Senha:"
                        color: settingsController.secondaryTextColor
                        font.pixelSize: 13
                        font.bold: true
                        visible: managePrivateToggle.checked
                    }
                    TextField {
                        id: pwdInput
                        Layout.fillWidth: true
                        placeholderText: "Nova senha"
                        color: settingsController.textColor
                        echoMode: TextInput.Password
                        visible: managePrivateToggle.checked
                        background: Rectangle {
                            color: settingsController.backgroundColor
                            radius: 4
                            border.color: pwdInput.activeFocus ? settingsController.accentColor : settingsController.borderColor
                        }
                    }
                    
                    Item { Layout.fillHeight: true }
                    
                    PrimaryButton {
                        text: "Salvar Alterações"
                        Layout.fillWidth: true
                        height: 48
                        onClicked: {
                            if (typeof mapSessionController !== "undefined") {
                                var finalPwd = managePrivateToggle.checked ? pwdInput.text : "";
                                mapSessionController.editRoom(mapSessionController.currentRoom, nameInput.text, finalPwd);
                                root.close();
                            }
                        }
                    }
                    
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: settingsController.borderColor
                        Layout.topMargin: 10
                        Layout.bottomMargin: 10
                    }
                    
                    Text {
                        text: "Usuários Ativos (Interagiram recentemente)"
                        color: settingsController.textColor
                        font.pixelSize: 14
                        font.bold: true
                    }
                    
                    ListView {
                        id: activeUsersList
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(120, (root.activeUsers.length + 1) * 44)
                        clip: true
                        model: {
                            var users = [];
                            var ownerName = typeof mapSessionController !== "undefined" ? mapSessionController.currentRoomCreator : "Dono";
                            users.push({ name: ownerName + " (👑 Dono)", id: "owner" });
                            for (var i = 0; i < root.activeUsers.length; i++) {
                                users.push(root.activeUsers[i]);
                            }
                            return users;
                        }
                        interactive: false // Don't scroll inside scrollview
                        delegate: Rectangle {
                            width: activeUsersList.width
                            height: 40
                            color: Qt.rgba(255/255, 255/255, 255/255, index % 2 === 0 ? 0.02 : 0.05)
                            radius: 6
                            border.color: Qt.rgba(255/255, 255/255, 255/255, 0.05)
                            
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                
                                Text {
                                    text: modelData.name
                                    color: modelData.id === "owner" ? settingsController.accentColor : settingsController.textColor
                                    Layout.fillWidth: true
                                    font.pixelSize: 13
                                    font.bold: modelData.id === "owner"
                                }
                                
                                Rectangle {
                                    width: 60
                                    height: 24
                                    color: "#ef4444"
                                    radius: 4
                                    visible: modelData.id !== "owner"
                                    Text {
                                        anchors.centerIn: parent
                                        text: "Kick"
                                        color: "#ffffff"
                                        font.pixelSize: 11
                                        font.bold: true
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (typeof mapSessionController !== "undefined" && modelData.id !== "owner") {
                                                mapSessionController.kickUser(mapSessionController.currentRoom, modelData.id);
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    Text {
                        text: "Histórico de Editores (No Mapa)"
                        color: settingsController.textColor
                        font.pixelSize: 14
                        font.bold: true
                        Layout.topMargin: 10
                    }
                    
                    ListView {
                        id: historicUsersList
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(120, root.historicUsers.length * 40)
                        clip: true
                        model: root.historicUsers
                        interactive: false
                        delegate: Rectangle {
                            width: historicUsersList.width
                            height: 40
                            color: index % 2 === 0 ? "transparent" : settingsController.backgroundColor
                            radius: 4
                            
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.leftMargin: 10
                                text: modelData
                                color: settingsController.secondaryTextColor
                                font.pixelSize: 12
                            }
                        }
                    }
                }
            } // End of Tab 2
        }
    }
}
