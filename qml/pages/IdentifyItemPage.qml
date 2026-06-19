import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: content.height
    boundsBehavior: Flickable.StopAtBounds
    interactive: contentHeight > height + 1
    property int scrollBarContentPadding: 14

    ScrollBar.vertical: ScrollBar {
        policy: root.contentHeight > root.height + 1 ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
        active: root.moving || root.flicking
    }

    Component.onCompleted: identifyItemController.ensureLoaded()

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    ColumnLayout {
        id: content
        width: Math.max(0, root.width - root.scrollBarContentPadding)
        height: Math.max(root.height, implicitHeight + 36)
        spacing: 16

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3
            Text {
                text: tr("identify.title")
                color: settingsController.textColor
                font.family: "Segoe UI"
                font.pixelSize: 26
                font.bold: true
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            Text {
                text: tr("identify.subtitle")
                color: settingsController.accentHoverColor
                font.family: "Segoe UI"
                font.pixelSize: 12
                font.bold: true
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: identifyItemController.status.toLowerCase().indexOf("missing") >= 0 ? settingsController.dangerColor : settingsController.borderColor
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
                    color: identifyItemController.status.toLowerCase().indexOf("missing") >= 0 ? settingsController.dangerColor : settingsController.mutedTextColor
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
                        fill: settingsController.controlColor
                        hoverFill: settingsController.controlHoverColor
                        textFill: settingsController.textColor
                        onClicked: identifyItemController.pasteClipboard()
                    }
                    PrimaryButton {
                        text: tr("identify.clear_reference")
                        fill: settingsController.controlColor
                        hoverFill: settingsController.controlHoverColor
                        textFill: settingsController.textColor
                        onClicked: identifyItemController.clearReference()
                    }
                    Item { Layout.fillWidth: true }
                    PrimaryButton {
                        text: tr("identify.detection_on")
                        enabled: identifyItemController.monitorAvailable
                        fill: settingsController.accentColor
                        hoverFill: settingsController.accentHoverColor
                        textFill: settingsController.textInverseColor
                        onClicked: identifyItemController.showMonitorOverlay()
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 860 ? 4 : 2
            columnSpacing: 12
            rowSpacing: 12

            MetricCard {
                Layout.fillWidth: true
                title: tr("identify.detection")
                value: identifyItemController.monitoring ? tr("identify.on") : tr("identify.off")
                detail: identifyItemController.monitorTarget !== "" ? identifyItemController.monitorTarget : tr("identify.no_image")
                accent: identifyItemController.monitoring ? settingsController.successColor : settingsController.mutedTextColor
                valuePixelSize: 20
            }
            MetricCard {
                Layout.fillWidth: true
                title: tr("identify.live_matches")
                value: String(identifyItemController.monitorMatchCount)
                detail: tr("identify.overlay_title")
                accent: settingsController.accentColor
            }
            MetricCard {
                Layout.fillWidth: true
                title: tr("identify.confidence")
                value: identifyItemController.monitorBestScoreText
                detail: tr("identify.color_cv")
                accent: settingsController.accentHoverColor
            }
            MetricCard {
                Layout.fillWidth: true
                title: tr("identify.engine")
                value: "OpenCV"
                detail: tr("identify.direct_match")
                accent: settingsController.warningColor
                valuePixelSize: 20
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 860 ? 2 : 1
            columnSpacing: 12
            rowSpacing: 12

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 430
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10
                    Text {
                        text: tr("identify.reference")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 17
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: settingsController.cardRadius
                        color: settingsController.accentPanelColor
                        border.color: settingsController.borderColor
                        Image {
                            anchors.fill: parent
                            anchors.margins: 12
                            source: identifyItemController.selectedImageUrl
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            cache: false
                            visible: identifyItemController.selectedImageUrl !== ""
                        }
                        Text {
                            anchors.centerIn: parent
                            width: parent.width - 32
                            text: tr("identify.crop_hint")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignHCenter
                            visible: identifyItemController.selectedImageUrl === ""
                        }
                    }
                    Text {
                        text: identifyItemController.selectedPath !== "" ? identifyItemController.selectedPath : tr("identify.no_image")
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 11
                        Layout.fillWidth: true
                        elide: Text.ElideMiddle
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 430
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10
                    Text {
                        text: tr("identify.live")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 17
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    Text {
                        text: identifyItemController.monitorSummary
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    ListView {
                        id: detectionResults
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: identifyItemController.monitorMatchesModel
                        spacing: 8
                        clip: true
                        delegate: Rectangle {
                            required property int matchX
                            required property int matchY
                            required property int matchW
                            required property int matchH
                            required property real matchScore
                            required property string scoreText
                            width: ListView.view.width
                            height: 64
                            radius: settingsController.cardRadius
                            color: index % 2 ? settingsController.surfaceAltColor : settingsController.surfaceRaisedColor
                            border.color: settingsController.borderColor
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 12
                                Rectangle {
                                    Layout.preferredWidth: 42
                                    Layout.preferredHeight: 42
                                    radius: 21
                                    color: settingsController.accentPanelColor
                                    border.color: settingsController.accentColor
                                    Text {
                                        anchors.centerIn: parent
                                        text: String(index + 1)
                                        color: settingsController.accentColor
                                        font.family: "Segoe UI"
                                        font.bold: true
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text {
                                        text: tr("identify.position") + " " + matchX + ", " + matchY
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        text: matchW + " x " + matchH
                                        color: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                    }
                                }
                                Rectangle {
                                    Layout.preferredWidth: 78
                                    Layout.preferredHeight: 30
                                    radius: 15
                                    color: matchScore >= 0.9 ? settingsController.successColor : settingsController.accentColor
                                    Text {
                                        anchors.centerIn: parent
                                        text: scoreText
                                        color: settingsController.textInverseColor
                                        font.family: "Segoe UI"
                                        font.bold: true
                                    }
                                }
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            text: identifyItemController.monitoring ? tr("identify.no_detections") : tr("identify.off")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            visible: detectionResults.count === 0
                        }
                    }
                }
            }
        }
    }
}
