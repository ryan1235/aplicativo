import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    width: 320
    height: 480

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: 12
        color: Qt.rgba(15/255, 23/255, 42/255, 0.95) // Deep slate background
        border.color: Qt.rgba(255/255, 255/255, 255/255, 0.15)
        border.width: 1

        // Subtle gradient glow effect at the top
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 100
            radius: 12
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(59/255, 130/255, 246/255, 0.15) } // Blueish glow
                GradientStop { position: 1.0; color: "transparent" }
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 16

            // Header
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "Calculadora de Artilharia"
                    color: "white"
                    font.pixelSize: 16
                    font.bold: true
                    font.family: "Segoe UI"
                    Layout.fillWidth: true
                }
                
                MouseArea {
                    width: 24
                    height: 24
                    cursorShape: Qt.PointingHandCursor
                    Text {
                        anchors.centerIn: parent
                        text: "❌" // times icon
                        color: parent.containsMouse ? "#ef4444" : settingsController.subtextColor
                        font.pixelSize: 12
                    }
                    onClicked: root.visible = false
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Qt.rgba(255/255, 255/255, 255/255, 0.1)
            }

            // Weapon Selector
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                
                Text {
                    text: "SELECIONE A ARMA"
                    color: settingsController.accentColor || "#3b82f6"
                    font.pixelSize: 11
                    font.bold: true
                    font.letterSpacing: 1
                }

                PrimaryComboBox {
                    id: weaponCombo
                    Layout.fillWidth: true
                    model: artilleryController.weaponsList
                    currentIndex: artilleryController.activeWeaponIndex
                    onActivated: (index) => {
                        artilleryController.activeWeaponIndex = index
                    }
                }
            }

            // Info Card
            Rectangle {
                id: infoCard
                Layout.fillWidth: true
                Layout.preferredHeight: infoLayout.implicitHeight + 24
                color: Qt.rgba(255/255, 255/255, 255/255, 0.03)
                border.color: Qt.rgba(255/255, 255/255, 255/255, 0.08)
                radius: 8
                
                function getInfo(key, fallback) {
                    var info = artilleryController.weaponInfo
                    if (!info) return fallback;
                    var val = info[key]
                    return val !== undefined ? val : fallback
                }
                
                function getNestedInfo(key1, key2, fallback) {
                    var info = artilleryController.weaponInfo
                    if (!info || !info[key1]) return fallback;
                    var val = info[key1][key2]
                    return val !== undefined ? val : fallback
                }

                GridLayout {
                    id: infoLayout
                    anchors.fill: parent
                    anchors.margins: 12
                    columns: 2
                    rowSpacing: 12
                    columnSpacing: 8

                    // Tipo
                    Text { text: "📌 Tipo:"; color: settingsController.subtextColor; font.pixelSize: 12; Layout.fillWidth: true }
                    Text { text: infoCard.getInfo("type", "-"); color: "white"; font.bold: true; font.pixelSize: 12; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                    
                    // Munição
                    Text { text: "💣 Munição:"; color: settingsController.subtextColor; font.pixelSize: 12; Layout.fillWidth: true }
                    Text { text: infoCard.getInfo("ammo", "-"); color: "white"; font.bold: true; font.pixelSize: 12; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                    
                    // Alcance
                    Text { text: "🎯 Alcance:"; color: settingsController.subtextColor; font.pixelSize: 12; Layout.fillWidth: true }
                    Text { 
                        text: infoCard.getNestedInfo("range", "minimum", "-") + "m - " + infoCard.getNestedInfo("range", "maximum", "-") + "m"
                        color: "#10b981" // emerald green
                        font.bold: true; font.pixelSize: 12; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true 
                    }
                    
                    // Dispersão
                    Text { text: "💥 Dispersão:"; color: settingsController.subtextColor; font.pixelSize: 12; Layout.fillWidth: true }
                    Text { 
                        text: infoCard.getNestedInfo("dispersion", "minimum", "-") + "m - " + infoCard.getNestedInfo("dispersion", "maximum", "-") + "m"
                        color: "#f59e0b" // amber
                        font.bold: true; font.pixelSize: 12; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true 
                    }
                    
                    // Tripulação
                    Text { text: "👥 Tripulação:"; color: settingsController.subtextColor; font.pixelSize: 12; Layout.fillWidth: true }
                    Text { 
                        text: infoCard.getInfo("minimumCrew", "-") + " - " + infoCard.getInfo("recommendedCrew", "-")
                        color: "white"; font.bold: true; font.pixelSize: 12; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true 
                    }
                }
            }

            Item { Layout.fillHeight: true } // Flexible spacer
            
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Qt.rgba(255/255, 255/255, 255/255, 0.1)
            }

            // Toggles
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Mostrar Alcance (Anéis)"; color: "white"; font.pixelSize: 13; Layout.fillWidth: true }
                    ToggleSwitch {
                        checked: artilleryController.showRange
                        onCheckedChanged: artilleryController.showRange = checked
                    }
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Mostrar Dispersão"; color: "white"; font.pixelSize: 13; Layout.fillWidth: true }
                    ToggleSwitch {
                        checked: artilleryController.showDispersion
                        onCheckedChanged: artilleryController.showDispersion = checked
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Mostrar Linha de Tiro"; color: "white"; font.pixelSize: 13; Layout.fillWidth: true }
                    ToggleSwitch {
                        checked: artilleryController.showLine
                        onCheckedChanged: artilleryController.showLine = checked
                    }
                }
            }
        }
    }
}
