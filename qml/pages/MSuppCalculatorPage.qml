import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import QtQuick.Dialogs
import "../components"

Item {
    id: root
    clip: true
    anchors.fill: parent

    component GlassPanel: Rectangle {
        id: panel
        property color accent: settingsController.accentColor
        default property alias content: panelContent.data

        Layout.fillWidth: true
        radius: 8
        color: "transparent"
        border.color: "transparent"
        border.width: 0
        Rectangle { anchors.fill: parent; radius: parent.radius; color: settingsController.scrimColor; opacity: 0.2 }
        Rectangle { anchors.fill: parent; radius: parent.radius; color: "transparent"; border.color: Qt.rgba(1, 1, 1, 0.08); border.width: 1 }
        implicitHeight: panelContent.implicitHeight + 28
        layer.enabled: true
        layer.effect: DropShadow {
            transparentBorder: true
            color: Qt.rgba(0, 0, 0, 0.20)
            radius: 18
            samples: 37
            verticalOffset: 5
        }
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: panel.accent
            opacity: 0.035
        }
        ColumnLayout {
            id: panelContent
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12
        }
    }

    Dialog {
        id: addBaseDialog
        title: "Adicionar Nova Base"
        modal: true
        anchors.centerIn: parent
        width: Math.min(400, root.width - 40)
        
        property string selectedImagePath: ""

        background: Rectangle {
            color: settingsController.backgroundColor
            radius: 10
            border.color: Qt.rgba(1,1,1,0.1)
        }

        onClosed: {
            nameInput.text = ""
            hourlyInput.text = ""
            stockInput.text = "1000"
            selectedImagePath = ""
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 15

            Text {
                text: "Local / Nome da Base"
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 13
            }
            TextField {
                id: nameInput
                Layout.fillWidth: true
                placeholderText: "Ex: Fábrica de SC no Hex X"
                color: settingsController.textColor
                background: Rectangle { radius: 7; color: settingsController.scrimColor; opacity: 0.3; border.color: Qt.rgba(1,1,1,0.1) }
            }

            Text {
                text: "Consumo Atual (M-Supps / Hora)"
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 13
            }
            TextField {
                id: hourlyInput
                Layout.fillWidth: true
                placeholderText: "Ex: 45"
                validator: IntValidator {bottom: 1; top: 99999}
                color: settingsController.textColor
                background: Rectangle { radius: 7; color: settingsController.scrimColor; opacity: 0.3; border.color: Qt.rgba(1,1,1,0.1) }
            }

            Text {
                text: "Estoque Atual no Túnel/Base"
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 13
            }
            TextField {
                id: stockInput
                Layout.fillWidth: true
                text: "1000" // Maximum tunnel capacity by default
                validator: IntValidator {bottom: 0; top: 999999}
                color: settingsController.textColor
                background: Rectangle { radius: 7; color: settingsController.scrimColor; opacity: 0.3; border.color: Qt.rgba(1,1,1,0.1) }
            }

            Text {
                text: "Foto do Mapa (Opcional)"
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 13
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                PrimaryButton {
                    text: "Escolher Imagem"
                    onClicked: {
                        var path = msuppController.pick_image()
                        if (path !== "") {
                            addBaseDialog.selectedImagePath = path
                        }
                    }
                }
                Text {
                    text: addBaseDialog.selectedImagePath !== "" ? "Imagem Selecionada" : "Nenhuma imagem"
                    color: settingsController.mutedTextColor
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignRight
                spacing: 10
                Button {
                    text: "Cancelar"
                    onClicked: addBaseDialog.close()
                }
                PrimaryButton {
                    text: "Salvar Base"
                    fill: settingsController.accentColor
                    textFill: settingsController.textInverseColor
                    onClicked: {
                        if (nameInput.text === "" || hourlyInput.text === "") return
                        msuppController.add_base(
                            nameInput.text,
                            parseInt(hourlyInput.text) || 0,
                            parseInt(stockInput.text) || 0,
                            addBaseDialog.selectedImagePath
                        )
                        addBaseDialog.close()
                    }
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Text {
                    text: "Bases Tracker"
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 26
                    font.bold: true
                    Layout.fillWidth: true
                }
                Text {
                    text: "Acompanhe o consumo e tempo de vida útil das suas bases."
                    color: settingsController.accentColor
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    font.bold: true
                    Layout.fillWidth: true
                }
            }

            PrimaryButton {
                text: "+ Nova Base"
                fill: settingsController.accentColor
                textFill: settingsController.textInverseColor
                onClicked: addBaseDialog.open()
            }
        }

        ListView {
            id: basesList
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: msuppController.bases
            spacing: 12
            clip: true

            delegate: GlassPanel {
                accent: settingsController.accentColor
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    // Thumbnail do Mapa
                    Rectangle {
                        width: 80
                        height: 80
                        radius: 8
                        color: Qt.rgba(0,0,0,0.3)
                        border.color: Qt.rgba(1,1,1,0.1)
                        clip: true
                        
                        Image {
                            anchors.fill: parent
                            source: modelData.image_path !== "" ? modelData.image_path : ""
                            fillMode: Image.PreserveAspectCrop
                            visible: modelData.image_path !== ""
                        }
                        
                        Text {
                            anchors.centerIn: parent
                            text: "Sem Foto"
                            color: settingsController.mutedTextColor
                            font.pixelSize: 10
                            visible: modelData.image_path === ""
                        }
                    }

                    // Informações
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            text: modelData.name
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 18
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }

                        RowLayout {
                            spacing: 15
                            
                            ColumnLayout {
                                spacing: 2
                                Text { text: "Consumo"; color: settingsController.mutedTextColor; font.pixelSize: 11; font.bold: true }
                                Text { text: modelData.hourly_rate + " / Hora"; color: settingsController.warningColor; font.pixelSize: 13; font.bold: true }
                            }
                            
                            ColumnLayout {
                                spacing: 2
                                Text { text: "Estoque Atual"; color: settingsController.mutedTextColor; font.pixelSize: 11; font.bold: true }
                                Text { text: modelData.current_stock + " M-Supps"; color: settingsController.infoColor; font.pixelSize: 13; font.bold: true }
                            }

                            ColumnLayout {
                                spacing: 2
                                Text { text: "Tempo Restante (M-Supps)"; color: settingsController.mutedTextColor; font.pixelSize: 11; font.bold: true }
                                Text {
                                    property int hoursLeft: modelData.hourly_rate > 0 ? Math.floor(modelData.current_stock / modelData.hourly_rate) : 999
                                    property int days: Math.floor(hoursLeft / 24)
                                    property int hours: hoursLeft % 24
                                    text: modelData.hourly_rate > 0 ? (days > 0 ? days + "d " + hours + "h" : hours + "h") : "Infinito"
                                    color: hoursLeft < 12 ? settingsController.errorColor : settingsController.successColor
                                    font.pixelSize: 13
                                    font.bold: true
                                }
                            }
                        }
                        
                        Text {
                            text: "Após acabar, existe um Grace Period de ~24 horas antes das estruturas começarem a receber dano de Decay (em Rapid Decay Zones esse tempo é menor)."
                            color: Qt.rgba(1,1,1,0.4)
                            font.pixelSize: 10
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }

                    // Ações
                    Button {
                        text: "X"
                        Layout.alignment: Qt.AlignTop
                        onClicked: msuppController.remove_base(index)
                    }
                }
            }
        }

        Text {
            text: "Nenhuma base rastreada. Clique em '+ Nova Base' para adicionar."
            color: settingsController.mutedTextColor
            visible: msuppController.bases.length === 0
            font.pixelSize: 14
            Layout.alignment: Qt.AlignCenter
        }
    }
}
