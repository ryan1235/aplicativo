import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Item {
    id: root
    anchors.fill: parent
    visible: false
    z: 9999
    
    signal commandExecuted(string commandId)

    // Dark overlay
    Rectangle {
        id: darkOverlay
        anchors.fill: parent
        color: "black"
        opacity: root.visible ? 0.6 : 0.0
        Behavior on opacity { NumberAnimation { duration: 200 } }
        
        MouseArea {
            anchors.fill: parent
            onClicked: root.close()
        }
    }

    Rectangle {
        id: paletteBg
        width: 480
        height: Math.min(400, searchCol.implicitHeight + 24)
        anchors.centerIn: parent
        anchors.verticalCenterOffset: root.visible ? -100 : -80
        radius: 16
        color: Qt.rgba(settingsController.surfaceColor.r, settingsController.surfaceColor.g, settingsController.surfaceColor.b, 0.85)
        border.color: Qt.rgba(settingsController.borderColor.r, settingsController.borderColor.g, settingsController.borderColor.b, 0.5)
        border.width: 1
        
        opacity: root.visible ? 1.0 : 0.0
        scale: root.visible ? 1.0 : 0.95
        Behavior on opacity { NumberAnimation { duration: 200; easing.type: Easing.OutQuad } }
        Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }
        Behavior on anchors.verticalCenterOffset { NumberAnimation { duration: 200; easing.type: Easing.OutQuad } }

        MultiEffect {
            source: paletteBg
            anchors.fill: paletteBg
            shadowEnabled: true
            shadowOpacity: 0.6
            shadowBlur: 2.0
            shadowVerticalOffset: 8
            shadowColor: "black"
            blurEnabled: true
            blur: 0.8
        }

        Column {
            id: searchCol
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12

            TextField {
                id: searchInput
                width: parent.width
                height: 48
                placeholderText: "> Digite um comando..."
                color: settingsController.textColor || "white"
                font.pixelSize: 16
                font.family: "Courier New"
                leftPadding: 16
                
                background: Rectangle {
                    color: Qt.rgba(settingsController.backgroundColor.r, settingsController.backgroundColor.g, settingsController.backgroundColor.b, 0.5)
                    border.color: searchInput.activeFocus ? (settingsController.accentColor || "#3b82f6") : Qt.rgba(settingsController.borderColor.r, settingsController.borderColor.g, settingsController.borderColor.b, 0.5)
                    border.width: searchInput.activeFocus ? 2 : 1
                    radius: 8
                    
                    Behavior on border.color { ColorAnimation { duration: 150 } }
                }
                
                onTextChanged: {
                    commandsModel.filter(text)
                }
                
                Keys.onDownPressed: {
                    commandsList.currentIndex = Math.min(commandsList.count - 1, commandsList.currentIndex + 1)
                }
                Keys.onUpPressed: {
                    commandsList.currentIndex = Math.max(0, commandsList.currentIndex - 1)
                }
                Keys.onReturnPressed: {
                    if (commandsList.currentIndex >= 0 && commandsList.currentIndex < commandsModel.count) {
                        var cmd = commandsModel.get(commandsList.currentIndex);
                        root.executeCommand(cmd.id);
                    }
                }
                Keys.onEscapePressed: {
                    root.close()
                }
            }

            ListView {
                id: commandsList
                width: parent.width
                height: Math.min(300, contentHeight)
                clip: true
                spacing: 4
                
                model: ListModel {
                    id: commandsModel
                    
                    property var allCommands: [
                        { id: "select_all", text: "Selecionar Tudo", icon: "⬚" },
                        { id: "clear_drawings", text: "Limpar Desenhos", icon: "🗑️" },
                        { id: "clear_artillery", text: "Limpar Artilharias", icon: "🎯" },
                        { id: "center_map", text: "Centralizar Mapa", icon: "📍" },
                        { id: "toggle_grid", text: "Alternar Grade", icon: "▦" },
                        { id: "export_map", text: "Exportar Mapa", icon: "💾" },
                        { id: "import_map", text: "Importar Mapa", icon: "📂" },
                        { id: "toggle_theme", text: "Alterar Tema", icon: "🌓" }
                    ]
                    
                    Component.onCompleted: filter("")
                    
                    function filter(query) {
                        clear();
                        var q = query.toLowerCase();
                        for (var i = 0; i < allCommands.length; i++) {
                            if (allCommands[i].text.toLowerCase().indexOf(q) !== -1 || q === "") {
                                append(allCommands[i]);
                            }
                        }
                        commandsList.currentIndex = count > 0 ? 0 : -1;
                    }
                }
                
                delegate: Rectangle {
                    width: commandsList.width
                    height: 48
                    radius: 8
                    color: ListView.isCurrentItem || mouseArea.containsMouse ? (settingsController.hoverColor || Qt.rgba(1,1,1,0.1)) : "transparent"
                    
                    Behavior on color { ColorAnimation { duration: 100 } }
                    
                    Row {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 16
                        
                        Text {
                            text: model.icon
                            color: settingsController.textColor || "white"
                            font.pixelSize: 16
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        
                        Text {
                            text: model.text
                            color: settingsController.textColor || "white"
                            font.pixelSize: 15
                            font.bold: ListView.isCurrentItem
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    
                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.executeCommand(model.id);
                        }
                    }
                }
            }
        }
    }
    
    function executeCommand(cmdId) {
        root.close();
        root.commandExecuted(cmdId);
    }
    
    function open() {
        root.visible = true;
        searchInput.text = "";
        commandsModel.filter("");
        searchInput.forceActiveFocus();
    }
    
    function close() {
        root.visible = false;
    }
}
