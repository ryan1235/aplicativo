import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: content.implicitHeight + 32

    property bool wide: width >= 1120

    Component.onCompleted: itemSearchController.ensureLoaded()

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    function trOr(key, fallback) {
        var value = tr(key)
        return value === key ? fallback : value
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

    function wikiStatusText() {
        var key = itemSearchController.wikiStatusKey
        if (key === "item_search.wiki_error")
            return trOr(key, "Wiki: {message}").replace("{message}", itemSearchController.wikiStatusMessage)
        if (key === "item_search.wiki_loading")
            return trOr(key, "Buscando dados na Foxhole Wiki...")
        if (key === "item_search.wiki_loaded")
            return trOr(key, "Dados encontrados na Wiki.")
        if (key === "item_search.wiki_empty")
            return trOr(key, "Digite ou escolha um item para consultar a Wiki.")
        return trOr(key, key)
    }

    ColumnLayout {
        id: content
        width: root.width
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3

                Text {
                    text: tr("item_search.title")
                    color: settingsController.textColor
                    font.family: "Segoe UI"
                    font.pixelSize: 26
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                Text {
                    text: tr("item_search.subtitle")
                    color: settingsController.mutedTextColor
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
                Layout.preferredWidth: 156
                onClicked: itemSearchController.refresh()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: settingsController.cardRadius
            color: settingsController.surfaceColor
            border.color: search.activeFocus ? settingsController.accentColor : settingsController.borderColor
            implicitHeight: searchPanel.implicitHeight + 28

            ColumnLayout {
                id: searchPanel
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 56
                        radius: settingsController.cardRadius
                        color: settingsController.backgroundColor
                        border.color: search.activeFocus ? settingsController.accentColor : settingsController.borderColor

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 10
                            spacing: 10

                            Text {
                                text: "Search"
                                color: search.activeFocus ? settingsController.accentColor : settingsController.mutedTextColor
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                font.bold: true
                                Layout.preferredWidth: 52
                                horizontalAlignment: Text.AlignHCenter
                            }

                            TextField {
                                id: search
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                text: itemSearchController.query
                                placeholderText: tr("item_search.placeholder")
                                placeholderTextColor: settingsController.mutedTextColor
                                color: settingsController.textColor
                                selectedTextColor: settingsController.backgroundColor
                                selectionColor: settingsController.accentColor
                                selectByMouse: true
                                font.family: "Segoe UI"
                                font.pixelSize: 18
                                font.bold: true
                                onTextEdited: itemSearchController.search(text)
                                background: Item {}
                            }

                            Rectangle {
                                visible: search.text !== ""
                                Layout.preferredWidth: 32
                                Layout.preferredHeight: 32
                                radius: Math.min(8, settingsController.cardRadius)
                                color: clearMouse.containsMouse ? settingsController.accentPanelColor : "transparent"

                                Text {
                                    anchors.centerIn: parent
                                    text: "x"
                                    color: clearMouse.containsMouse ? settingsController.textColor : settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 13
                                    font.bold: true
                                }

                                MouseArea {
                                    id: clearMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: itemSearchController.search("")
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: root.wide ? 285 : 230
                        Layout.preferredHeight: 56
                        radius: settingsController.cardRadius
                        color: itemSearchController.statusKey === "item_search.error" ? settingsController.dangerPanelColor : settingsController.backgroundColor
                        border.color: itemSearchController.statusKey === "item_search.error" ? settingsController.warningColor : settingsController.borderColor

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 9
                            spacing: 1

                            Text {
                                text: tr("item_search.index_status")
                                color: settingsController.mutedTextColor
                                font.family: "Segoe UI"
                                font.pixelSize: 10
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Text {
                                text: root.statusText()
                                color: itemSearchController.statusKey === "item_search.error" ? settingsController.warningColor : settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                ListView {
                    id: suggestionList
                    Layout.fillWidth: true
                    Layout.preferredHeight: count > 0 ? 44 : 0
                    visible: count > 0
                    clip: true
                    orientation: ListView.Horizontal
                    spacing: 8
                    reuseItems: true
                    model: itemSearchController.suggestionRows

                    delegate: Button {
                        height: 38
                        width: Math.min(310, Math.max(144, chipLabel.implicitWidth + (model.alias ? 98 : 34)))
                        onClicked: itemSearchController.chooseSuggestion(String(model.name || ""))

                        contentItem: RowLayout {
                            spacing: 7

                            Rectangle {
                                visible: model.alias !== ""
                                Layout.preferredWidth: Math.min(72, Math.max(38, aliasText.implicitWidth + 12))
                                Layout.preferredHeight: 21
                                radius: Math.min(6, settingsController.cardRadius)
                                color: settingsController.warningColor

                                Text {
                                    id: aliasText
                                    anchors.fill: parent
                                    anchors.leftMargin: 6
                                    anchors.rightMargin: 6
                                    text: model.alias || ""
                                    color: settingsController.backgroundColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 10
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                            }

                            Text {
                                id: chipLabel
                                text: model.name || ""
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                font.bold: true
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }
                        }

                        background: Rectangle {
                            radius: settingsController.cardRadius
                            color: parent.hovered ? settingsController.accentPanelColor : settingsController.backgroundColor
                            border.color: model.source === "slang" ? settingsController.warningColor : settingsController.borderColor
                            Behavior on color { ColorAnimation { duration: 120 } }
                        }

                        ToolTip.visible: hovered && model.detail !== ""
                        ToolTip.text: model.detail || ""
                    }

                    ScrollBar.horizontal: ScrollBar { active: suggestionList.moving }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 960 ? 3 : 1
            columnSpacing: 12
            rowSpacing: 12

            MetricCard {
                Layout.fillWidth: true
                title: itemSearchController.selectedName !== "" ? fmt("item_search.result_title", "{item}", itemSearchController.selectedName) : tr("item_search.title")
                value: itemSearchController.selectedName !== "" ? String(itemSearchController.total) : "-"
                detail: tr("item_search.total").replace("{total}", String(itemSearchController.total))
                accent: settingsController.accentColor
            }

            MetricCard {
                Layout.fillWidth: true
                title: tr("item_search.available_items")
                value: itemSearchController.loaded ? String(itemSearchController.statusCount) : "-"
                detail: tr("item_search.last_update").replace("{value}", itemSearchController.lastUpdate)
                accent: settingsController.successColor
            }

            MetricCard {
                Layout.fillWidth: true
                title: trOr("item_search.wiki_title", "Wiki do item")
                value: itemSearchController.wikiLoading ? "..." : (itemSearchController.wikiName !== "" ? itemSearchController.wikiName : "-")
                detail: root.wikiStatusText()
                accent: settingsController.warningColor
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.wide ? 2 : 1
            columnSpacing: 12
            rowSpacing: 12

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(430, root.height - 286)
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                text: itemSearchController.selectedName !== "" ? fmt("item_search.result_title", "{item}", itemSearchController.selectedName) : tr("item_search.empty")
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 18
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Text {
                                text: tr("item_search.alias_hint")
                                color: settingsController.mutedTextColor
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }

                        Text {
                            text: String(results.count) + " " + tr("item_search.rows")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            font.bold: true
                        }
                    }

                    ListView {
                        id: results
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 7
                        reuseItems: true
                        model: itemSearchController.resultRows
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar { active: results.moving }

                        delegate: Rectangle {
                            width: results.width
                            height: model.rowType === "region" ? 42 : 62
                            radius: settingsController.cardRadius
                            color: model.rowType === "region"
                                ? settingsController.accentPanelColor
                                : (index % 2 ? settingsController.backgroundColor : settingsController.surfaceColor)
                            border.color: model.rowType === "region" ? settingsController.accentColor : settingsController.borderColor

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: model.rowType === "region" ? 10 : 8
                                spacing: 10

                                Image {
                                    visible: model.rowType !== "region"
                                    source: model.icon || ""
                                    Layout.preferredWidth: 38
                                    Layout.preferredHeight: 38
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                    cache: false
                                    sourceSize.width: 46
                                    sourceSize.height: 46
                                }

                                ColumnLayout {
                                    Layout.fillWidth: model.rowType === "region"
                                    Layout.preferredWidth: model.rowType === "region" ? -1 : Math.min(260, Math.max(170, results.width * 0.18))
                                    Layout.minimumWidth: model.rowType === "region" ? 0 : 150
                                    Layout.alignment: Qt.AlignVCenter
                                    spacing: 1

                                    Text {
                                        text: model.rowType === "region"
                                            ? tr("item_search.region_total").replace("{region}", model.region || "-").replace("{total}", String(model.total || 0))
                                            : model.code || "-"
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: model.rowType === "region" ? 13 : 16
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }

                                Text {
                                    visible: model.rowType !== "region"
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 180
                                    Layout.alignment: Qt.AlignVCenter
                                    text: model.place || model.warehouse || "-"
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 15
                                    font.bold: true
                                    horizontalAlignment: Text.AlignLeft
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideMiddle
                                }

                                Text {
                                    visible: model.rowType !== "region"
                                    Layout.preferredWidth: Math.min(330, Math.max(245, results.width * 0.26))
                                    Layout.alignment: Qt.AlignVCenter
                                    text: tr("item_search.last_update").replace("{value}", model.updatedAt || "-") + (model.updatedAgo ? " (" + model.updatedAgo + ")" : "")
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    horizontalAlignment: Text.AlignRight
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }

                                Rectangle {
                                    visible: model.rowType !== "region"
                                    Layout.preferredWidth: 106
                                    Layout.preferredHeight: 38
                                    radius: Math.min(8, settingsController.cardRadius)
                                    color: settingsController.accentPanelColor
                                    border.color: settingsController.accentColor

                                    Text {
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        text: String(model.quantity || 0)
                                        color: settingsController.accentColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 16
                                        font.bold: true
                                        horizontalAlignment: Text.AlignRight
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            width: parent.width - 36
                            height: 120
                            text: tr("item_search.empty")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            wrapMode: Text.WordWrap
                            visible: results.count === 0 && !itemSearchController.loading
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: !root.wide
                Layout.preferredWidth: root.wide ? 392 : 0
                Layout.preferredHeight: root.wide ? Math.max(430, root.height - 286) : Math.max(380, wikiColumn.implicitHeight + 28)
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor

                Flickable {
                    anchors.fill: parent
                    anchors.margins: 14
                    clip: true
                    contentWidth: width
                    contentHeight: wikiColumn.implicitHeight

                    ColumnLayout {
                        id: wikiColumn
                        width: parent.width
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Rectangle {
                                Layout.preferredWidth: 72
                                Layout.preferredHeight: 72
                                radius: settingsController.cardRadius
                                color: settingsController.backgroundColor
                                border.color: settingsController.borderColor

                                Image {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    source: itemSearchController.wikiImage
                                    visible: itemSearchController.wikiImage !== ""
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                }

                                Text {
                                    anchors.centerIn: parent
                                    visible: itemSearchController.wikiImage === ""
                                    text: "Wiki"
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    text: trOr("item_search.wiki_title", "Wiki do item")
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 10
                                    font.bold: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: itemSearchController.wikiName !== "" ? itemSearchController.wikiName : trOr("item_search.wiki_empty", "Digite ou escolha um item para consultar a Wiki.")
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 17
                                    font.bold: true
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }

                                Text {
                                    text: root.wikiStatusText()
                                    color: itemSearchController.wikiStatusKey === "item_search.wiki_error" ? settingsController.warningColor : settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            visible: itemSearchController.wikiDescription !== ""
                            radius: settingsController.cardRadius
                            color: settingsController.backgroundColor
                            border.color: settingsController.borderColor
                            implicitHeight: wikiDescription.implicitHeight + 22

                            Text {
                                id: wikiDescription
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 11
                                text: itemSearchController.wikiDescription
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                lineHeight: 1.15
                                wrapMode: Text.WordWrap
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 7
                            visible: wikiFieldsRepeater.count > 0

                            Text {
                                text: trOr("item_search.wiki_fields", "Ficha tecnica")
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 13
                                font.bold: true
                                Layout.fillWidth: true
                            }

                            Repeater {
                                id: wikiFieldsRepeater
                                model: itemSearchController.wikiFields

                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: Math.max(32, fieldValue.implicitHeight + 12)
                                    radius: 0
                                    color: "transparent"

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 2
                                        anchors.rightMargin: 2
                                        spacing: 8

                                        Text {
                                            text: model.label || "-"
                                            color: settingsController.mutedTextColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 11
                                            font.bold: true
                                            Layout.preferredWidth: 124
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            id: fieldValue
                                            text: model.value || "-"
                                            color: settingsController.textColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 12
                                            font.bold: true
                                            Layout.fillWidth: true
                                            wrapMode: Text.WordWrap
                                        }
                                    }

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: 1
                                        color: settingsController.borderColor
                                        opacity: 0.55
                                    }
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 7
                            visible: wikiProductionRepeater.count > 0

                            Text {
                                text: trOr("item_search.wiki_production", "Producao")
                                color: settingsController.textColor
                                font.family: "Segoe UI"
                                font.pixelSize: 13
                                font.bold: true
                                Layout.fillWidth: true
                            }

                            Repeater {
                                id: wikiProductionRepeater
                                model: itemSearchController.wikiProduction

                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: Math.max(58, prodText.implicitHeight + 20)
                                    radius: Math.min(6, settingsController.cardRadius)
                                    color: settingsController.accentPanelColor
                                    border.color: settingsController.borderColor

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        spacing: 2

                                        Text {
                                            text: (model.site || "-") + (model.time ? " - " + model.time : "")
                                            color: settingsController.accentColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 12
                                            font.bold: true
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            id: prodText
                                            text: (model.input || "-") + (model.output ? " -> " + model.output : "")
                                            color: settingsController.textColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 11
                                            Layout.fillWidth: true
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: itemSearchController.wikiStatusKey === "item_search.wiki_empty" && !itemSearchController.wikiLoading
                            text: trOr("item_search.wiki_no_data", "A Wiki nao retornou detalhes para este item ainda.")
                            color: settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                        }

                        PrimaryButton {
                            Layout.fillWidth: true
                            text: trOr("item_search.wiki_open", "Abrir pagina da Wiki")
                            enabled: itemSearchController.wikiSourceUrl !== ""
                            onClicked: itemSearchController.openWikiPage()
                        }
                    }
                }
            }
        }
    }
}
