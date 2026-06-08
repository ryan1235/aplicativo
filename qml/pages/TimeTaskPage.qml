import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: content.implicitHeight + 36

    Component.onCompleted: timeTaskController.ensureLoaded()

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    ColumnLayout {
        id: content
        width: root.width
        spacing: 16

        Text {
            text: tr("timetask.title")
            color: "#edf6ff"
            font.family: "Segoe UI"
            font.pixelSize: 26
            font.bold: true
            Layout.fillWidth: true
        }

        Text {
            text: tr("timetask.subtitle")
            color: "#8ab4ff"
            font.family: "Segoe UI"
            font.pixelSize: 13
            font.bold: true
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
            implicitHeight: 252

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Text {
                    text: tr("timetask.record_title")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 19
                    font.bold: true
                    Layout.fillWidth: true
                }

                Text {
                    text: tr("timetask.warning")
                    color: "#ffd166"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 720 ? 3 : 1
                    columnSpacing: 12
                    rowSpacing: 10

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 5
                        Text { text: tr("timetask.name"); color: "#99abc4"; font.family: "Segoe UI"; font.bold: true }
                        TextField {
                            Layout.fillWidth: true
                            text: timeTaskController.macroName
                            enabled: timeTaskController.available && !timeTaskController.recording
                            onEditingFinished: timeTaskController.setMacroName(text)
                            color: "#edf6ff"
                            font.family: "Segoe UI"
                            background: Rectangle { radius: 7; color: "#07111f"; border.color: "#24486d" }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 5
                        Text { text: tr("timetask.status"); color: "#99abc4"; font.family: "Segoe UI"; font.bold: true }
                        Text {
                            text: timeTaskController.status
                            color: timeTaskController.available ? "#edf6ff" : "#ff7a90"
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 5
                        Text { text: tr("timetask.metric_empty"); color: "#99abc4"; font.family: "Segoe UI"; font.bold: true }
                        Text {
                            text: timeTaskController.metric
                            color: "#8ab4ff"
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    PrimaryButton {
                        text: tr("timetask.open_record_overlay")
                        enabled: timeTaskController.available
                        onClicked: timeTaskController.showRecordOverlay()
                    }
                    PrimaryButton {
                        text: timeTaskController.paused ? tr("timetask.play") : tr("timetask.pause")
                        enabled: timeTaskController.recording || timeTaskController.replaying
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: timeTaskController.pauseResume()
                    }
                    PrimaryButton {
                        text: tr("timetask.save")
                        enabled: timeTaskController.available
                        fill: "#62d7a4"
                        hoverFill: "#5eead4"
                        textFill: "#041014"
                        onClicked: timeTaskController.saveCurrent()
                    }
                    PrimaryButton {
                        text: tr("timetask.stop")
                        enabled: timeTaskController.recording
                        fill: "#ff7a90"
                        hoverFill: "#b94a5d"
                        textFill: "#edf6ff"
                        onClicked: timeTaskController.stopRecording()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
            implicitHeight: 224

            GridLayout {
                anchors.fill: parent
                anchors.margins: 16
                columns: root.width > 900 ? 4 : root.width > 620 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: tr("timetask.speed"); color: "#99abc4"; font.family: "Segoe UI"; font.bold: true }
                    PrimaryComboBox {
                        Layout.fillWidth: true
                        model: timeTaskController.speedOptions
                        currentIndex: Math.max(0, timeTaskController.speedOptions.indexOf(timeTaskController.speed))
                        onActivated: timeTaskController.setSpeed(currentText)
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: tr("timetask.repeat"); color: "#99abc4"; font.family: "Segoe UI"; font.bold: true }
                    TextField {
                        Layout.fillWidth: true
                        text: timeTaskController.repeat
                        onEditingFinished: timeTaskController.setRepeat(text)
                        color: "#edf6ff"
                        font.family: "Segoe UI"
                        background: Rectangle { radius: 7; color: "#07111f"; border.color: "#24486d" }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: tr("timetask.delay"); color: "#99abc4"; font.family: "Segoe UI"; font.bold: true }
                    PrimaryComboBox {
                        Layout.fillWidth: true
                        model: timeTaskController.delayOptions
                        currentIndex: Math.max(0, timeTaskController.delayOptions.indexOf(timeTaskController.delay))
                        onActivated: timeTaskController.setDelay(currentText)
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: tr("timetask.stock_interval"); color: "#99abc4"; font.family: "Segoe UI"; font.bold: true }
                    TextField {
                        Layout.fillWidth: true
                        text: timeTaskController.stockInterval
                        onEditingFinished: timeTaskController.setStockInterval(text)
                        color: "#edf6ff"
                        font.family: "Segoe UI"
                        background: Rectangle { radius: 7; color: "#07111f"; border.color: "#24486d" }
                    }
                }

                ColumnLayout {
                    Layout.columnSpan: root.width > 900 ? 2 : 1
                    Layout.fillWidth: true
                    Text { text: tr("timetask.stock_macro"); color: "#99abc4"; font.family: "Segoe UI"; font.bold: true }
                    PrimaryComboBox {
                        Layout.fillWidth: true
                        model: timeTaskController.stockMacroOptions
                        currentIndex: Math.max(0, timeTaskController.stockMacroOptions.indexOf(timeTaskController.stockMacroName))
                        onActivated: timeTaskController.setStockMacroName(currentText)
                    }
                }

                RowLayout {
                    Layout.columnSpan: root.width > 900 ? 2 : 1
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignBottom
                    spacing: 10
                    PrimaryButton {
                        text: tr("timetask.play")
                        enabled: timeTaskController.available
                        fill: "#62d7a4"
                        hoverFill: "#5eead4"
                        textFill: "#041014"
                        onClicked: timeTaskController.playSelected()
                    }
                    PrimaryButton {
                        text: tr("timetask.cancel")
                        enabled: timeTaskController.replaying
                        fill: "#ff7a90"
                        hoverFill: "#b94a5d"
                        textFill: "#edf6ff"
                        onClicked: timeTaskController.stopReplay()
                    }
                    PrimaryButton {
                        text: tr("timetask.delete")
                        enabled: timeTaskController.selectedMacroName !== ""
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: timeTaskController.deleteSelectedMacro()
                    }
                    PrimaryButton {
                        text: tr("timetask.refresh")
                        fill: "#0e1a2d"
                        hoverFill: "#1d3353"
                        textFill: "#edf6ff"
                        onClicked: timeTaskController.refreshMacros()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
            implicitHeight: 340

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: tr("timetask.replay_title")
                        color: "#edf6ff"
                        font.family: "Segoe UI"
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    Text {
                        text: timeTaskController.selectedMacroName || tr("timetask.replay_empty")
                        color: "#99abc4"
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        Layout.maximumWidth: 260
                    }
                }

                ListView {
                    id: macroList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: timeTaskController.macros
                    spacing: 8
                    clip: true
                    delegate: Rectangle {
                        width: macroList.width
                        height: 62
                        radius: 8
                        color: selected ? "#1d3353" : mouse.containsMouse ? "#172943" : "#0e1a2d"
                        border.color: selected ? "#5eead4" : "#24486d"
                        Behavior on color { ColorAnimation { duration: 120 } }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 12
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Text {
                                    text: name
                                    color: "#edf6ff"
                                    font.family: "Segoe UI"
                                    font.bold: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: createdAt
                                    color: "#99abc4"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }
                            Text {
                                text: duration
                                color: "#8ab4ff"
                                font.family: "Segoe UI"
                                Layout.preferredWidth: 76
                                horizontalAlignment: Text.AlignRight
                            }
                            Text {
                                text: events + " events"
                                color: "#99abc4"
                                font.family: "Segoe UI"
                                Layout.preferredWidth: 100
                                horizontalAlignment: Text.AlignRight
                            }
                        }

                        MouseArea {
                            id: mouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: timeTaskController.selectMacro(index)
                        }
                    }
                }
            }
        }

        Text {
            text: tr("timetask.folder").replace("{path}", timeTaskController.macroFolder)
            color: "#60728c"
            font.family: "Segoe UI"
            font.pixelSize: 11
            Layout.fillWidth: true
            elide: Text.ElideMiddle
        }
    }
}
