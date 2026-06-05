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

    function fmt(key, token, value) {
        return tr(key).replace(token, value)
    }

    ColumnLayout {
        id: content
        width: root.width
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Text {
                    text: tr("identify.title")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 26
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Text {
                    text: tr("identify.subtitle")
                    color: "#8ab4ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.bold: true
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
            }

            PrimaryButton {
                text: tr("identify.reindex")
                fill: "#1d3353"
                hoverFill: "#2d496f"
                textFill: "#edf6ff"
                onClicked: identifyItemController.reindex()
            }
            PrimaryButton {
                text: tr("identify.open_search")
                fill: "#1d3353"
                hoverFill: "#2d496f"
                textFill: "#edf6ff"
                onClicked: appController.setCurrentPage("itemSearch")
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "#111c31"
            border.color: identifyItemController.status.toLowerCase().indexOf("missing") >= 0 ? "#ff7a90" : "#24486d"
            implicitHeight: actionColumn.implicitHeight + 28

            ColumnLayout {
                id: actionColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 14
                spacing: 12

                Text {
                    text: identifyItemController.status
                    color: identifyItemController.status.toLowerCase().indexOf("missing") >= 0 ? "#ffb3c0" : "#99abc4"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    PrimaryButton {
                        text: tr("identify.select")
                        onClicked: identifyItemController.selectImage()
                    }
                    PrimaryButton {
                        text: tr("identify.paste")
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: identifyItemController.pasteClipboard()
                    }
                    PrimaryButton {
                        text: tr("identify.capture")
                        fill: "#1d3353"
                        hoverFill: "#2d496f"
                        textFill: "#edf6ff"
                        onClicked: identifyItemController.captureScreen()
                    }
                    PrimaryButton {
                        text: identifyItemController.scanning ? tr("identify.scanning") : tr("identify.scan")
                        enabled: !identifyItemController.scanning
                        onClicked: identifyItemController.scanSelected()
                    }
                    PrimaryButton {
                        text: identifyItemController.monitoring ? tr("identify.monitor_stop") : tr("identify.monitor_start")
                        enabled: identifyItemController.monitorAvailable
                        fill: identifyItemController.monitoring ? "#5eead4" : "#1d3353"
                        hoverFill: identifyItemController.monitoring ? "#8ab4ff" : "#2d496f"
                        textFill: identifyItemController.monitoring ? "#041014" : "#edf6ff"
                        onClicked: identifyItemController.toggleMonitor()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
            implicitHeight: settingsRow.implicitHeight + 28

            RowLayout {
                id: settingsRow
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 14
                spacing: 12

                Text {
                    text: tr("identify.mode")
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    font.bold: true
                }
                ComboBox {
                    Layout.preferredWidth: 140
                    model: identifyItemController.modes
                    currentIndex: Math.max(0, identifyItemController.modes.indexOf(identifyItemController.mode))
                    onActivated: identifyItemController.setMode(currentText)
                }
                Text {
                    text: tr("identify.threshold")
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    font.bold: true
                }
                Slider {
                    id: thresholdSlider
                    from: 0.5
                    to: 0.99
                    value: identifyItemController.threshold
                    Layout.preferredWidth: 240
                    onMoved: identifyItemController.setThreshold(value)
                }
                Text {
                    text: thresholdSlider.value.toFixed(2)
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.bold: true
                    Layout.preferredWidth: 42
                }
                Text {
                    text: fmt("identify.templates", "{count}", String(identifyItemController.indexedCount))
                    color: "#99abc4"
                    font.family: "Segoe UI"
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignRight
                    elide: Text.ElideLeft
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 860 ? 2 : 1
            columnSpacing: 12
            rowSpacing: 12

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 420
                radius: 8
                color: "#111c31"
                border.color: "#24486d"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10
                    Text {
                        text: tr("identify.target")
                        color: "#edf6ff"
                        font.family: "Segoe UI"
                        font.pixelSize: 17
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 8
                        color: "#0e1a2d"
                        border.color: "#2d496f"
                        Image {
                            anchors.fill: parent
                            anchors.margins: 12
                            source: identifyItemController.selectedImageUrl
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            visible: identifyItemController.selectedImageUrl !== ""
                        }
                        Text {
                            anchors.centerIn: parent
                            width: parent.width - 32
                            text: tr("identify.crop_hint")
                            color: "#99abc4"
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignHCenter
                            visible: identifyItemController.selectedImageUrl === ""
                        }
                    }
                    Text {
                        text: identifyItemController.selectedPath !== "" ? identifyItemController.selectedPath : tr("identify.no_image")
                        color: "#99abc4"
                        font.family: "Segoe UI"
                        font.pixelSize: 11
                        Layout.fillWidth: true
                        elide: Text.ElideMiddle
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 420
                radius: 8
                color: "#111c31"
                border.color: "#24486d"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10
                    Text {
                        text: tr("identify.matches")
                        color: "#edf6ff"
                        font.family: "Segoe UI"
                        font.pixelSize: 17
                        font.bold: true
                    }
                    ListView {
                        id: identifyResults
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: identifyItemController.resultsModel
                        spacing: 8
                        clip: true
                        delegate: Rectangle {
                            width: ListView.view.width
                            height: 58
                            radius: 8
                            color: index % 2 ? "#0e1a2d" : "#13213a"
                            border.color: "#24486d"
                            MouseArea {
                                anchors.fill: parent
                                onClicked: identifyItemController.selectResult(index)
                            }
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 9
                                spacing: 10
                                Image {
                                    source: icon
                                    Layout.preferredWidth: 38
                                    Layout.preferredHeight: 38
                                    fillMode: Image.PreserveAspectFit
                                }
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
                                        text: path
                                        color: "#99abc4"
                                        font.family: "Segoe UI"
                                        font.pixelSize: 10
                                        Layout.fillWidth: true
                                        elide: Text.ElideMiddle
                                    }
                                }
                                Rectangle {
                                    Layout.preferredWidth: 70
                                    Layout.preferredHeight: 30
                                    radius: 15
                                    color: score >= identifyItemController.threshold ? "#5eead4" : "#1d3353"
                                    Text {
                                        anchors.centerIn: parent
                                        text: scoreText
                                        color: score >= identifyItemController.threshold ? "#041014" : "#edf6ff"
                                        font.family: "Segoe UI"
                                        font.bold: true
                                    }
                                }
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            text: tr("identify.no_image")
                            color: "#99abc4"
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            visible: identifyResults.count === 0
                        }
                    }
                }
            }
        }
    }
}
