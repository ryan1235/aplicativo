import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: content.implicitHeight + 36

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    Component.onCompleted: stockpileController.refreshApiSnapshot()

    ColumnLayout {
        id: content
        width: root.width
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Text {
                    text: tr("stockpile.title")
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 26
                    font.bold: true
                    Layout.fillWidth: true
                }
                Text {
                    text: tr("stockpile.subtitle")
                    color: settingsController.infoColor
                    font.family: "Segoe UI"
                    font.pixelSize: 11
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    wrapMode: Text.WordWrap
                }
            }
            PrimaryButton {
                text: "Atualizar"
                fill: settingsController.accentColor
                hoverFill: settingsController.accentHoverColor
                textFill: settingsController.textInverseColor
                onClicked: stockpileController.refreshApiSnapshot()
            }
            Item { Layout.fillWidth: true }
            RowLayout {
                spacing: 8
                Text {
                    text: "HUD:"
                    color: settingsController.mutedTextColor
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.bold: true
                }
                
                Rectangle {
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                    radius: 4
                    color: "transparent"
                    border.color: "transparent"
                    border.width: 0
                    Rectangle { anchors.fill: parent; radius: parent.radius; color: settingsController.accentColor; opacity: minusMouse.containsMouse ? 0.15 : 0.0 }
                    Rectangle { anchors.fill: parent; radius: parent.radius; color: "transparent"; border.color: settingsController.accentColor; opacity: 0.2; border.width: 1 }
                    Text {
                        anchors.centerIn: parent
                        text: "-"
                        color: stockpileController.hudScale > 0.5 ? settingsController.textColor : settingsController.disabledTextColor
                        font.pixelSize: 16
                        font.bold: true
                        anchors.verticalCenterOffset: -1
                    }
                    MouseArea {
                        id: minusMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            if (stockpileController.hudScale > 0.5) {
                                stockpileController.setHudScale(Math.round((stockpileController.hudScale - 0.1) * 10) / 10)
                            }
                        }
                    }
                }

                Text {
                    text: Math.round(stockpileController.hudScale * 100) + "%"
                    color: settingsController.accentColor
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.bold: true
                    Layout.preferredWidth: 40
                    horizontalAlignment: Text.AlignHCenter
                }

                Rectangle {
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                    radius: 4
                    color: "transparent"
                    border.color: "transparent"
                    border.width: 0
                    Rectangle { anchors.fill: parent; radius: parent.radius; color: settingsController.accentColor; opacity: plusMouse.containsMouse ? 0.15 : 0.0 }
                    Rectangle { anchors.fill: parent; radius: parent.radius; color: "transparent"; border.color: settingsController.accentColor; opacity: 0.2; border.width: 1 }
                    Text {
                        anchors.centerIn: parent
                        text: "+"
                        color: stockpileController.hudScale < 3.0 ? settingsController.textColor : settingsController.disabledTextColor
                        font.pixelSize: 16
                        font.bold: true
                        anchors.verticalCenterOffset: -1
                    }
                    MouseArea {
                        id: plusMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            if (stockpileController.hudScale < 3.0) {
                                stockpileController.setHudScale(Math.round((stockpileController.hudScale + 0.1) * 10) / 10)
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            id: visualPanel
            Layout.fillWidth: true
            implicitHeight: stockpileController.apiLoading ? 200 : visualContent.implicitHeight + 24
            radius: 8
            color: "transparent"
            border.color: "transparent"
            border.width: 0
            Rectangle { anchors.fill: parent; radius: parent.radius; color: settingsController.scrimColor; opacity: 0.2 }
            Rectangle { anchors.fill: parent; radius: parent.radius; color: settingsController.accentColor; opacity: 0.035 }
            Rectangle { anchors.fill: parent; radius: parent.radius; color: "transparent"; border.color: settingsController.accentColor; opacity: 0.2; border.width: 1 }

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 16
                visible: stockpileController.apiLoading

                Item {
                    Layout.alignment: Qt.AlignHCenter
                    width: 48
                    height: 48
                    
                    Canvas {
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d");
                            ctx.clearRect(0, 0, width, height);
                            ctx.beginPath();
                            ctx.arc(width / 2, height / 2, width / 2 - 4, 0, Math.PI * 2);
                            ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
                            ctx.lineWidth = 4;
                            ctx.stroke();

                            ctx.beginPath();
                            ctx.arc(width / 2, height / 2, width / 2 - 4, -Math.PI / 2, Math.PI * 0.7);
                            ctx.strokeStyle = settingsController.accentColor;
                            ctx.lineWidth = 4;
                            ctx.lineCap = "round";
                            ctx.stroke();
                        }
                        
                        RotationAnimation on rotation {
                            loops: Animation.Infinite
                            from: 0
                            to: 360
                            duration: 1000
                            running: stockpileController.apiLoading
                        }
                    }
                }

                Text {
                    text: "Puxando estoques..."
                    color: settingsController.accentColor
                    font.family: "Segoe UI"
                    font.pixelSize: 16
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                }
            }

            ColumnLayout {
                id: visualContent
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6
                visible: !stockpileController.apiLoading

                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: tr("stockpile.visual_title")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 17
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: tr("stockpile.visual_updated").replace("{value}", stockpileController.visualWarehouseUpdatedAt)
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 10
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            visible: stockpileController.visualWarehouseInactive
                            text: tr("stockpile.visual_depot_inactive_warning")
                            color: settingsController.dangerColor
                            font.family: "Segoe UI"
                            font.pixelSize: 10
                            font.bold: true
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }
                    PrimaryComboBox {
                        id: visualWarehouseBox
                        Layout.preferredWidth: Math.min(380, Math.max(240, root.width * 0.34))
                        Layout.preferredHeight: 32
                        enabled: stockpileController.visualWarehouseOptions.length > 0
                        textRole: "text"
                        popupStartsAtTop: true
                        popupScrollbarTextPadding: 14
                        model: stockpileController.visualWarehouseOptions
                        currentIndex: {
                            var opts = stockpileController.visualWarehouseOptions;
                            for (var i = 0; i < opts.length; i++) {
                                if (opts[i] && opts[i].id === stockpileController.visualWarehouse) return i;
                            }
                            return 0;
                        }
                        onActivated: {
                            var selected = stockpileController.visualWarehouseOptions[currentIndex];
                            if (selected && selected.id) {
                                stockpileController.setVisualWarehouse(selected.id);
                            }
                        }
                        contentItem: Text {
                            text: visualWarehouseBox.displayText
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            font.bold: true
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 10
                            elide: Text.ElideRight
                        }
                        background: Rectangle {
                            radius: 6
                            color: "transparent"
                            border.color: "transparent"
                            border.width: 0
                            Rectangle { anchors.fill: parent; radius: parent.radius; color: settingsController.scrimColor; opacity: 0.4 }
                            Rectangle { anchors.fill: parent; radius: parent.radius; color: "transparent"; border.color: visualWarehouseBox.activeFocus ? settingsController.accentColor : settingsController.accentColor; opacity: visualWarehouseBox.activeFocus ? 1.0 : 0.2; border.width: 1 }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: stockpileController.visualGroupRows.length === 0
                    text: tr("stockpile.visual_empty")
                    color: settingsController.mutedTextColor
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    topPadding: 26
                    bottomPadding: 26
                }

                Repeater {
                    model: stockpileController.visualGroupRows
                    delegate: Rectangle {
                        property var groupRow: modelData
                        Layout.fillWidth: true
                        implicitHeight: groupColumn.implicitHeight + 8
                        radius: 0
                        color: "transparent"

                        ColumnLayout {
                            id: groupColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            spacing: 3

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Qt.rgba(1, 1, 1, 0.1)
                            }
                            Text {
                                text: tr(groupRow.titleKey || "")
                                color: settingsController.accentColor
                                font.family: "Segoe UI"
                                font.pixelSize: 9
                                font.bold: true
                                Layout.fillWidth: true
                            }
                            Flow {
                                Layout.fillWidth: true
                                Layout.preferredHeight: childrenRect.height
                                spacing: 4

                                Repeater {
                                    model: groupRow.items || []
                                    delegate: Rectangle {
                                        property var itemRow: modelData
                                        property real scaleFactor: stockpileController.hudScale
                                        width: 72 * scaleFactor
                                        height: 27 * scaleFactor
                                        radius: 2
                                        color: "transparent"
                                        border.color: "transparent"
                                        border.width: 0
                                        Rectangle { anchors.fill: parent; radius: parent.radius; color: settingsController.scrimColor; opacity: 0.3 }
                                        Rectangle { anchors.fill: parent; radius: parent.radius; color: settingsController.accentColor; opacity: tileMouse.containsMouse ? 0.15 : 0.03; Behavior on opacity { NumberAnimation { duration: 100 } } }
                                        Rectangle { anchors.fill: parent; radius: parent.radius; color: "transparent"; border.color: settingsController.accentColor; opacity: tileMouse.containsMouse ? 0.8 : 0.15; border.width: 1; Behavior on opacity { NumberAnimation { duration: 100 } } }
                                        Behavior on width { NumberAnimation { duration: 100 } }
                                        Behavior on height { NumberAnimation { duration: 100 } }

                                        Image {
                                            anchors.left: parent.left
                                            anchors.leftMargin: 2 * scaleFactor
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: 22 * scaleFactor
                                            height: 22 * scaleFactor
                                            source: itemRow.icon || ""
                                            fillMode: Image.PreserveAspectFit
                                        }
                                        Rectangle {
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.bottom: parent.bottom
                                            width: 37 * scaleFactor
                                            color: "transparent"
                                            border.color: "transparent"
                                            border.width: 0
                                            Rectangle { anchors.fill: parent; color: settingsController.scrimColor; opacity: 0.2 }
                                            Rectangle { anchors.fill: parent; color: settingsController.accentColor; opacity: 0.05 }
                                            Rectangle { anchors.fill: parent; color: "transparent"; border.color: settingsController.accentColor; opacity: 0.15; border.width: 1 }
                                            Text {
                                                anchors.centerIn: parent
                                                text: String(itemRow.quantity || 0)
                                                color: settingsController.textColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: Math.max(9, 10 * scaleFactor)
                                                font.bold: true
                                            }
                                        }
                                        MouseArea {
                                            id: tileMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                        }
                                        ToolTip.visible: tileMouse.containsMouse
                                        ToolTip.text: (itemRow.name || "-") + " | " + (itemRow.category || "-")
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}


