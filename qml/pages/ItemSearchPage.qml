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

    function statusText() {
        var key = itemSearchController.statusKey
        if (key === "item_search.loaded")
            return fmt(key, "{count}", String(itemSearchController.statusCount))
        if (key === "item_search.error")
            return fmt(key, "{message}", itemSearchController.statusMessage)
        if (key === "item_search.best_match")
            return fmt(key, "{item}", itemSearchController.bestMatch)
        return tr(key)
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
                    text: tr("item_search.title")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 26
                    font.bold: true
                    Layout.fillWidth: true
                }
                Text {
                    text: tr("item_search.subtitle")
                    color: "#8ab4ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.bold: true
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
            }

            PrimaryButton {
                text: itemSearchController.loading ? tr("item_search.loading") : tr("stockpile.debug_check_button")
                enabled: !itemSearchController.loading
                fill: "#1d3353"
                hoverFill: "#2d496f"
                textFill: "#edf6ff"
                onClicked: itemSearchController.refresh()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: 8
            color: "#111c31"
            border.color: "#24486d"
            implicitHeight: searchColumn.implicitHeight + 28

            ColumnLayout {
                id: searchColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 14
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    TextField {
                        id: search
                        Layout.fillWidth: true
                        text: itemSearchController.query
                        placeholderText: tr("item_search.placeholder")
                        placeholderTextColor: "#6f86a8"
                        color: "#edf6ff"
                        selectByMouse: true
                        onTextEdited: itemSearchController.search(text)
                        background: Rectangle {
                            radius: 7
                            color: "#0e1a2d"
                            border.color: search.activeFocus ? "#5eead4" : "#2d496f"
                            Behavior on border.color { ColorAnimation { duration: 140 } }
                        }
                    }
                    Rectangle {
                        Layout.preferredWidth: 220
                        Layout.preferredHeight: 40
                        radius: 7
                        color: itemSearchController.statusKey === "item_search.error" ? "#311523" : "#0e1a2d"
                        border.color: itemSearchController.statusKey === "item_search.error" ? "#ff7a90" : "#2d496f"
                        Text {
                            anchors.fill: parent
                            anchors.margins: 9
                            text: root.statusText()
                            color: itemSearchController.statusKey === "item_search.error" ? "#ffb3c0" : "#99abc4"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            font.bold: true
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }

                ScrollView {
                    id: suggestionScroll
                    Layout.fillWidth: true
                    Layout.preferredHeight: itemSearchController.suggestionRowItems.length > 0 ? 38 : 0
                    visible: itemSearchController.suggestionRowItems.length > 0
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AlwaysOff
                    background: Rectangle { color: "transparent" }

                    Row {
                        spacing: 8
                        Repeater {
                            model: itemSearchController.suggestionRowItems
                            delegate: Button {
                                property var row: modelData
                                height: 34
                                width: Math.max(116, label.implicitWidth + 28)
                                onClicked: itemSearchController.chooseSuggestion(row.name || "")
                                contentItem: Text {
                                    id: label
                                    text: row.name || ""
                                    color: "#edf6ff"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                                background: Rectangle {
                                    radius: 7
                                    color: parent.hovered ? "#2d496f" : "#1d3353"
                                    border.color: "#3b5d87"
                                    Behavior on color { ColorAnimation { duration: 120 } }
                                }
                            }
                        }
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 820 ? 3 : 1
            columnSpacing: 12
            rowSpacing: 12
            MetricCard {
                Layout.fillWidth: true
                title: itemSearchController.selectedName !== "" ? fmt("item_search.result_title", "{item}", itemSearchController.selectedName) : tr("item_search.title")
                value: itemSearchController.selectedName !== "" ? String(itemSearchController.total) : "-"
                detail: tr("item_search.total").replace("{total}", String(itemSearchController.total))
                accent: "#5eead4"
            }
            MetricCard {
                Layout.fillWidth: true
                title: tr("item_search.last_update").replace("{value}", itemSearchController.lastUpdate)
                value: itemSearchController.loaded ? String(itemSearchController.statusCount) : "-"
                detail: root.statusText()
                accent: "#8ab4ff"
            }
            MetricCard {
                Layout.fillWidth: true
                title: tr("item_search.best_match_empty")
                value: itemSearchController.bestMatch !== "" ? itemSearchController.bestMatch : "-"
                detail: tr("item_search.placeholder")
                accent: "#ffd166"
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(360, root.height - 250)
            radius: 8
            color: "#111c31"
            border.color: "#24486d"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Text {
                    text: itemSearchController.selectedName !== "" ? fmt("item_search.result_title", "{item}", itemSearchController.selectedName) : tr("item_search.empty")
                    color: "#edf6ff"
                    font.family: "Segoe UI"
                    font.pixelSize: 18
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                ScrollView {
                    id: results
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    background: Rectangle { color: "#0b1424"; radius: 7; border.color: "#1e3554" }

                    Column {
                        width: results.availableWidth
                        spacing: 6

                        Repeater {
                            model: itemSearchController.resultRowItems
                            delegate: Rectangle {
                                property var row: modelData
                                width: results.availableWidth
                                height: row.rowType === "region" ? 42 : 50
                                radius: 7
                                color: row.rowType === "region" ? "#102039" : (index % 2 ? "#0e1a2d" : "#13213a")
                                border.color: row.rowType === "region" ? "#24486d" : "#1e3554"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: row.rowType === "region" ? 10 : 8
                                    spacing: 10

                                    Image {
                                        visible: row.rowType !== "region"
                                        source: row.icon || ""
                                        Layout.preferredWidth: 32
                                        Layout.preferredHeight: 32
                                        fillMode: Image.PreserveAspectFit
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1
                                        Text {
                                            text: row.rowType === "region"
                                                ? tr("item_search.region_total").replace("{region}", row.region || "-").replace("{total}", String(row.total || 0))
                                                : row.code || "-"
                                            color: "#edf6ff"
                                            font.family: "Segoe UI"
                                            font.pixelSize: row.rowType === "region" ? 13 : 12
                                            font.bold: true
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                        Text {
                                            visible: row.rowType !== "region"
                                            text: (row.warehouse || "-") + " | " + tr("item_search.last_update").replace("{value}", row.updatedAt || "-")
                                            color: "#99abc4"
                                            font.family: "Segoe UI"
                                            font.pixelSize: 10
                                            Layout.fillWidth: true
                                            elide: Text.ElideMiddle
                                        }
                                    }

                                    Text {
                                        visible: row.rowType !== "region"
                                        text: String(row.quantity || 0)
                                        color: "#5eead4"
                                        font.family: "Segoe UI"
                                        font.pixelSize: 14
                                        font.bold: true
                                        Layout.preferredWidth: 80
                                        horizontalAlignment: Text.AlignRight
                                    }
                                }
                            }
                        }

                        Text {
                            width: results.availableWidth
                            height: 120
                            text: tr("item_search.empty")
                            color: "#99abc4"
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            wrapMode: Text.WordWrap
                            visible: itemSearchController.resultRowItems.length === 0 && !itemSearchController.loading
                        }
                    }
                }
            }
        }
    }
}
