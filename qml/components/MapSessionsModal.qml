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
    property bool showMyMaps: false
    
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
        color: settingsController.surfaceColor
        radius: 12
        border.color: settingsController.borderColor
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
                width: 30
                height: 30
                radius: 15
                color: "transparent"
                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    color: settingsController.textColor
                    font.pixelSize: 16
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.close()
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
                text: "Sessões Ativas"
                font.pixelSize: 16
                font.bold: true
                color: root.showMyMaps ? settingsController.secondaryTextColor : settingsController.textColor
                
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -5 // extend click area
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.showMyMaps = false
                        if (typeof mapSessionController !== "undefined") {
                            mapSessionController.fetchRooms();
                        }
                    }
                }
            }
            
            Text {
                text: "Meus Mapas"
                font.pixelSize: 16
                font.bold: true
                color: root.showMyMaps ? settingsController.textColor : settingsController.secondaryTextColor
                
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -5
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.showMyMaps = true
                        if (typeof mapSessionController !== "undefined") {
                            mapSessionController.fetchMyRooms();
                        }
                    }
                }
            }
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: sessionsModel
            spacing: 10
            
            delegate: Rectangle {
                width: ListView.view.width
                height: 60
                radius: 8
                color: settingsController.backgroundColor
                border.color: settingsController.borderColor
                border.width: 1
                
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof mapSessionController !== "undefined") {
                            var pwd = model.isPrivate ? root.newSessionPassword : "";
                            mapSessionController.joinRoom(model.roomId, pwd);
                            root.close();
                        }
                    }
                }
                
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12
                    
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text {
                            text: model.sessionName
                            font.pixelSize: 16
                            font.bold: true
                            color: settingsController.textColor
                        }
                        Text {
                            text: "Criado por: " + model.creator + " | Jogadores: " + model.players
                            font.pixelSize: 12
                            color: settingsController.secondaryTextColor
                        }
                    }
                    
                    Text {
                        text: model.isPrivate ? "🔒 Privado" : "🌐 Público"
                        font.pixelSize: 12
                        color: model.isPrivate ? "#ef4444" : "#10b981"
                        Layout.alignment: Qt.AlignVCenter
                    }
                    
                    PrimaryButton {
                        id: enterBtn
                        text: model.creator === (typeof chatController !== "undefined" ? chatController.currentUserName : "") ? "Abrir" : "Entrar"
                        width: 80
                        height: 32
                        Layout.alignment: Qt.AlignVCenter
                        onClicked: {
                            if (typeof mapSessionController !== "undefined") {
                                var pwd = model.isPrivate ? root.newSessionPassword : "";
                                mapSessionController.joinRoom(model.roomId, pwd);
                                root.close();
                            }
                        }
                    }
                    
                    Rectangle {
                        width: 80
                        height: 32
                        radius: 6
                        color: "#ef4444" // red for delete
                        visible: model.creator === (typeof chatController !== "undefined" ? chatController.currentUserName : "")
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

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: settingsController.borderColor
        }

        // Create New Session Form
        Text {
            text: "Criar Nova Sessão"
            font.pixelSize: 16
            font.bold: true
            color: settingsController.textColor
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            rowSpacing: 12
            columnSpacing: 12

            Text { text: "Nome do Mapa:"; color: settingsController.textColor; font.pixelSize: 14 }
            TextField {
                Layout.fillWidth: true
                placeholderText: "Ex: Coordenação de Artilharia"
                color: settingsController.textColor
                background: Rectangle {
                    color: settingsController.backgroundColor
                    radius: 4
                    border.color: settingsController.borderColor
                }
                onTextChanged: root.newSessionName = text
            }

            Text { text: "Mapa Privado:"; color: settingsController.textColor; font.pixelSize: 14 }
            RowLayout {
                Layout.fillWidth: true
                ToggleSwitch {
                    id: privateToggle
                    checked: root.isPrivate
                    onCheckedChanged: root.isPrivate = checked
                }
                Text {
                    text: root.isPrivate ? "Requer senha para entrar" : "Qualquer um pode entrar"
                    color: settingsController.secondaryTextColor
                    font.pixelSize: 12
                }
            }

            Text {
                text: "Senha:"
                color: settingsController.textColor
                font.pixelSize: 14
                visible: root.isPrivate
            }
            TextField {
                Layout.fillWidth: true
                placeholderText: "Defina uma senha"
                echoMode: TextInput.Password
                color: settingsController.textColor
                visible: root.isPrivate
                background: Rectangle {
                    color: settingsController.backgroundColor
                    radius: 4
                    border.color: settingsController.borderColor
                }
                onTextChanged: root.newSessionPassword = text
            }
        }

        PrimaryButton {
            Layout.fillWidth: true
            Layout.topMargin: 10
            height: 44
            text: "Criar e Entrar na Sessão"
            onClicked: {
                if (root.newSessionName.trim() === "") {
                    return;
                }
                if (typeof mapSessionController !== "undefined") {
                    mapSessionController.createRoom(root.newSessionName, root.isPrivate, root.newSessionPassword);
                }
                root.close()
            }
        }
    }
}
