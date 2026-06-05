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
                text: stockpileController.running ? tr("stockpile.stop") : tr("stockpile.start")
                onClicked: stockpileController.running ? stockpileController.stop() : stockpileController.start()
            }
            PrimaryButton {
                text: tr("stockpile.extract_once")
                fill: "#1d3353"
                hoverFill: "#2d496f"
                textFill: "#edf6ff"
                onClicked: stockpileController.extractOnce()
            }
        }

        Rectangle {
            id: visualPanel
            Layout.fillWidth: true
            implicitHeight: visualContent.implicitHeight + 24
            radius: 8
            color: "#111c31"
            border.color: "#24486d"

            ColumnLayout {
                id: visualContent
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6

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
                    ComboBox {
                        id: visualWarehouseBox
                        Layout.preferredWidth: Math.min(300, Math.max(210, root.width * 0.25))
                        Layout.preferredHeight: 32
                        enabled: stockpileController.visualWarehouseOptions.length > 0
                        model: stockpileController.visualWarehouseOptions
                        currentIndex: Math.max(0, stockpileController.visualWarehouseOptions.indexOf(stockpileController.visualWarehouse))
                        onActivated: stockpileController.setVisualWarehouse(currentText)
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
                                        width: 72
                                        height: 27
                                        radius: 2
                                        color: tileMouse.containsMouse ? "#1d3353" : "#0f1d32"
                                        border.color: "#2b4565"
                                        Behavior on color { ColorAnimation { duration: 100 } }

                                        Image {
                                            anchors.left: parent.left
                                            anchors.leftMargin: 2
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: 22
                                            height: 22
                                            source: itemRow.icon || ""
                                            fillMode: Image.PreserveAspectFit
                                        }
                                        Rectangle {
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.bottom: parent.bottom
                                            width: 37
                                            color: "#172943"
                                            border.color: "#2b4565"
                                            Text {
                                                anchors.centerIn: parent
                                                text: String(itemRow.quantity || 0)
                                                color: "#edf6ff"
                                                font.family: "Segoe UI"
                                                font.pixelSize: 10
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
