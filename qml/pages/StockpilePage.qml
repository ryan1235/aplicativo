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
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 26
                    font.bold: true
                    Layout.fillWidth: true
                }
                Text {
                    text: tr("stockpile.subtitle")
                    color: "#8ab4ff"
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
                fill: "#5eead4"
                hoverFill: "#2dd4bf"
                textFill: "#022c22"
                onClicked: stockpileController.refreshApiSnapshot()
            }
            Item { Layout.fillWidth: true }
            RowLayout {
                spacing: 8
                Text {
                    text: "HUD:"
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.bold: true
                }
                
                Rectangle {
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                    radius: 4
                    color: minusMouse.containsMouse ? "#1d3353" : "transparent"
                    border.color: "#24486d"
                    Text {
                        anchors.centerIn: parent
                        text: "-"
                        color: stockpileController.hudScale > 0.5 ? "#edf6ff" : "#4a6282"
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
                    color: "#5eead4"
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
                    color: plusMouse.containsMouse ? "#1d3353" : "transparent"
                    border.color: "#24486d"
                    Text {
                        anchors.centerIn: parent
                        text: "+"
                        color: stockpileController.hudScale < 3.0 ? "#edf6ff" : "#4a6282"
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
            color: "#111c31"
            border.color: "#24486d"

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
                            ctx.strokeStyle = "#1d3353";
                            ctx.lineWidth = 4;
                            ctx.stroke();

                            ctx.beginPath();
                            ctx.arc(width / 2, height / 2, width / 2 - 4, -Math.PI / 2, Math.PI * 0.7);
                            ctx.strokeStyle = "#5eead4";
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
                    color: "#5eead4"
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
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 17
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Text {
                            text: tr("stockpile.visual_updated").replace("{value}", stockpileController.visualWarehouseUpdatedAt)
                            color: "#99abc4"
                            font.family: "Segoe UI"
                            font.pixelSize: 10
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                    PrimaryComboBox {
                        id: visualWarehouseBox
                        Layout.preferredWidth: Math.min(300, Math.max(210, root.width * 0.25))
                        Layout.preferredHeight: 32
                        enabled: stockpileController.visualWarehouseOptions.length > 0
                        textRole: "text"
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
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            font.bold: true
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 10
                            elide: Text.ElideRight
                        }
                        background: Rectangle {
                            radius: 6
                            color: "#0e1a2d"
                            border.color: visualWarehouseBox.activeFocus ? "#5eead4" : "#2d496f"
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: stockpileController.visualGroupRows.length === 0
                    text: tr("stockpile.visual_empty")
                    color: "#99abc4"
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
                                color: "#1f324b"
                            }
                            Text {
                                text: tr(groupRow.titleKey || "")
                                color: groupRow.accent || "#aeb7c2"
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
                                        color: tileMouse.containsMouse ? "#1d3353" : "#0f1d32"
                                        border.color: "#2b4565"
                                        Behavior on color { ColorAnimation { duration: 100 } }
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
                                            color: "#172943"
                                            border.color: "#2b4565"
                                            Text {
                                                anchors.centerIn: parent
                                                text: String(itemRow.quantity || 0)
                                                color: "#edf6ff"
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
