import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    width: 320
    height: 600 // Increased height slightly to accommodate wind controls

    signal saveRequested()
    signal clearRequested()

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
                        color: parent.containsMouse ? "#ef4444" : settingsController.secondaryTextColor
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
                    color: "#3b82f6" // accent color
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
                    Text { text: "📌 Tipo:"; color: settingsController.secondaryTextColor; font.pixelSize: 12; Layout.fillWidth: true }
                    Text { text: infoCard.getInfo("type", "-"); color: "white"; font.bold: true; font.pixelSize: 12; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                    
                    // Munição
                    Text { text: "💣 Munição:"; color: settingsController.secondaryTextColor; font.pixelSize: 12; Layout.fillWidth: true }
                    Text { text: infoCard.getInfo("ammo", "-"); color: "white"; font.bold: true; font.pixelSize: 12; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                    
                    // Alcance
                    Text { text: "📏 Alcance:"; color: settingsController.secondaryTextColor; font.pixelSize: 12; Layout.fillWidth: true }
                    Text { 
                        text: infoCard.getNestedInfo("range", "minimum", "-") + "m - " + infoCard.getNestedInfo("range", "maximum", "-") + "m"
                        color: "#10b981" // emerald green
                        font.bold: true; font.pixelSize: 12; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true 
                    }
                    
                    // Dispersão
                    Text { text: "🎯 Dispersão:"; color: settingsController.secondaryTextColor; font.pixelSize: 12; Layout.fillWidth: true }
                    Text { 
                        text: infoCard.getNestedInfo("dispersion", "minimum", "-") + "m - " + infoCard.getNestedInfo("dispersion", "maximum", "-") + "m"
                        color: "#f59e0b" // amber
                        font.bold: true; font.pixelSize: 12; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true 
                    }
                    
                    // Tripulação
                    Text { text: "👥 Tripulação:"; color: settingsController.secondaryTextColor; font.pixelSize: 12; Layout.fillWidth: true }
                    Text { 
                        text: infoCard.getInfo("minimumCrew", "-") + " - " + infoCard.getInfo("recommendedCrew", "-")
                        color: "white"; font.bold: true; font.pixelSize: 12; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true 
                    }
                }
            }

            Item { Layout.fillHeight: true } // Flexible spacer
            
            // Wind Controls
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                
                Text {
                    text: "🌬️ VENTO (TIER: " + Math.round(artilleryController.windTier) + " | AZM: " + Math.round(artilleryController.windDirection) + "°)"
                    color: "#38bdf8"
                    font.pixelSize: 11
                    font.bold: true
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Força"; color: "white"; font.pixelSize: 12; Layout.preferredWidth: 40 }
                    Slider {
                        Layout.fillWidth: true
                        from: 0; to: 5; stepSize: 1
                        value: artilleryController.windTier
                        onValueChanged: artilleryController.windTier = value
                    }
                }
                // Wind Rose 3x3 Grid
                GridLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                    columns: 3
                    rowSpacing: 4
                    columnSpacing: 4

                    Repeater {
                        model: [
                            {label: "NW", angle: 315}, {label: "N", angle: 0}, {label: "NE", angle: 45},
                            {label: "W", angle: 270},  {label: "•", angle: -1}, {label: "E", angle: 90},
                            {label: "SW", angle: 225}, {label: "S", angle: 180}, {label: "SE", angle: 135}
                        ]
                        delegate: Rectangle {
                            width: 44
                            height: 36
                            radius: 6
                            color: modelData.angle === -1 ? "transparent" : (Math.round(artilleryController.windDirection) === modelData.angle ? "#38bdf8" : Qt.rgba(255/255, 255/255, 255/255, 0.05))
                            border.color: modelData.angle === -1 ? "transparent" : (Math.round(artilleryController.windDirection) === modelData.angle ? "#0284c7" : Qt.rgba(255/255, 255/255, 255/255, 0.15))
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: modelData.label
                                color: modelData.angle === -1 ? "#38bdf8" : (Math.round(artilleryController.windDirection) === modelData.angle ? "#0f172a" : "#94a3b8")
                                font.pixelSize: modelData.angle === -1 ? 18 : 11
                                font.bold: true
                            }

                            MouseArea {
                                anchors.fill: parent
                                enabled: modelData.angle !== -1
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    artilleryController.windDirection = modelData.angle;
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Qt.rgba(255/255, 255/255, 255/255, 0.1)
            }
            
            // Save Button
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                
                Button {
                    Layout.fillWidth: true
                    text: "📌 Fixar"
                    font.bold: true
                    background: Rectangle {
                        color: parent.down ? "#1d4ed8" : "#2563eb"
                        radius: 6
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.bold: true
                    }
                    onClicked: {
                        if (typeof root.parent !== "undefined") {
                            root.saveRequested()
                        }
                    }
                }
                
                Button {
                    Layout.preferredWidth: 80
                    text: "🗑️ Limpar"
                    font.bold: true
                    background: Rectangle {
                        color: parent.down ? "#991b1b" : "#dc2626"
                        radius: 6
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.bold: true
                    }
                    onClicked: {
                        if (typeof root.parent !== "undefined") {
                            root.clearRequested()
                        }
                    }
                }
            }
            
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
