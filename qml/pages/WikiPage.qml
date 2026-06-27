import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    clip: true

    property bool wide: width >= 980
    property int pagePadding: 14

    Component.onCompleted: {
        itemSearchController.ensureLoaded()
        if (itemSearchController.query !== "") {
            Qt.callLater(function() {
                search.forceActiveFocus()
                search.selectAll()
            })
        }
    }

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

    function wikiStatusText() {
        var key = itemSearchController.wikiStatusKey
        if (key === "item_search.wiki_error")
            return tr(key).replace("{message}", itemSearchController.wikiStatusMessage)
        return tr(key)
    }

    function chooseWikiItem(name) {
        var title = String(name || "").trim()
        if (title === "")
            return
        itemSearchController.chooseSuggestion(title)
        itemSearchController.fetchWikiInfo(title)
    }

    function openDamageDialog() {
        itemSearchController.prepareDamageCalculator()
        damageModeBar.currentIndex = 0
        damageAmmoField.text = ""
        duelAmmoField.text = ""
        duelLeftField.text = ""
        duelRightField.text = ""
        damagePenField.text = ""
        duelPenField.text = ""
        damageDialog.open()
    }

    function rowKindColor(kind) {
        if (kind === "success")
            return settingsController.successColor
        if (kind === "warning")
            return settingsController.warningColor
        if (kind === "note")
            return settingsController.mutedTextColor
        return settingsController.accentColor
    }

    function factionColor(faction) {
        if (faction === "warden")   return "#3a85d4"  // Warden blue
        if (faction === "colonial") return "#3ab86a"  // Colonial green
        return settingsController.accentColor
    }

    function tryAutoDuel() {
        if (duelLeftField.text.trim() !== "" && duelRightField.text.trim() !== "") {
            itemSearchController.calculateTankDuel(
                duelLeftField.text, duelRightField.text,
                duelAmmoField.text, duelPenField.text
            )
        }
    }

    Flickable {
        id: pageScroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: pageContent.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height + 1

        ScrollBar.vertical: ScrollBar {
            policy: pageScroll.contentHeight > pageScroll.height + 1 ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
            active: pageScroll.moving || pageScroll.flicking
        }

        ColumnLayout {
            id: pageContent
            width: Math.max(0, pageScroll.width - root.pagePadding)
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: tr("wiki.title")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 25
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    Text {
                        text: tr("wiki.subtitle")
                        color: settingsController.mutedTextColor
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        font.bold: true
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                }

                PrimaryButton {
                    text: itemSearchController.wikiLoading ? tr("wiki.loading") : tr("wiki.refresh")
                    enabled: !itemSearchController.wikiLoading
                    Layout.preferredWidth: 136
                    onClicked: itemSearchController.fetchWikiInfo(itemSearchController.selectedName !== "" ? itemSearchController.selectedName : search.text)
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: search.activeFocus ? settingsController.accentColor : settingsController.borderColor
                implicitHeight: searchColumn.implicitHeight + 24

                ColumnLayout {
                    id: searchColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.minimumWidth: root.wide ? 360 : 220
                            Layout.preferredHeight: 52
                            radius: settingsController.cardRadius
                            color: settingsController.backgroundColor
                            border.color: search.activeFocus ? settingsController.accentColor : settingsController.borderColor

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 14
                                anchors.rightMargin: 10
                                spacing: 10

                                Canvas {
                                    Layout.preferredWidth: 18
                                    Layout.preferredHeight: 18
                                    property color strokeColor: search.activeFocus ? settingsController.accentColor : settingsController.mutedTextColor
                                    onStrokeColorChanged: requestPaint()
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.clearRect(0, 0, width, height)
                                        ctx.strokeStyle = strokeColor
                                        ctx.lineWidth = 2
                                        ctx.lineCap = "round"
                                        ctx.beginPath()
                                        ctx.arc(7.5, 7.5, 5.5, 0, Math.PI * 2)
                                        ctx.stroke()
                                        ctx.beginPath()
                                        ctx.moveTo(12, 12)
                                        ctx.lineTo(16, 16)
                                        ctx.stroke()
                                    }
                                }

                                TextField {
                                    id: search
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    text: itemSearchController.query
                                    placeholderText: tr("wiki.placeholder")
                                    placeholderTextColor: settingsController.mutedTextColor
                                    color: settingsController.textColor
                                    selectedTextColor: settingsController.backgroundColor
                                    selectionColor: settingsController.accentColor
                                    selectByMouse: true
                                    font.family: "Segoe UI"
                                    font.pixelSize: 17
                                    font.bold: true
                                    onTextEdited: itemSearchController.search(text)
                                    onAccepted: root.chooseWikiItem(itemSearchController.bestMatch !== "" ? itemSearchController.bestMatch : text)
                                    background: Item {}
                                }

                                Rectangle {
                                    visible: search.text !== ""
                                    Layout.preferredWidth: 30
                                    Layout.preferredHeight: 30
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
                            visible: root.wide
                            Layout.preferredWidth: 150
                            Layout.preferredHeight: 52
                            radius: settingsController.cardRadius
                            color: settingsController.backgroundColor
                            border.color: settingsController.borderColor

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 0

                                Text {
                                    text: tr("item_search.available_items")
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 10
                                    font.bold: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: itemSearchController.loaded ? String(itemSearchController.statusCount) : "-"
                                    color: settingsController.successColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 18
                                    font.bold: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Rectangle {
                            visible: root.wide
                            Layout.preferredWidth: 220
                            Layout.preferredHeight: 52
                            radius: settingsController.cardRadius
                            color: itemSearchController.statusKey === "item_search.error" ? settingsController.dangerPanelColor : settingsController.backgroundColor
                            border.color: itemSearchController.statusKey === "item_search.error" ? settingsController.warningColor : settingsController.borderColor

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
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
                                    font.pixelSize: 11
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
                        Layout.preferredHeight: count > 0 ? 40 : 0
                        visible: count > 0
                        clip: true
                        orientation: ListView.Horizontal
                        spacing: 8
                        reuseItems: true
                        model: itemSearchController.suggestionRows

                        delegate: Button {
                            height: 34
                            width: Math.min(280, Math.max(132, chipLabel.implicitWidth + (model.alias ? 92 : 28)))
                            onClicked: root.chooseWikiItem(String(model.name || ""))

                            contentItem: RowLayout {
                                spacing: 7

                                Rectangle {
                                    visible: model.alias !== ""
                                    Layout.preferredWidth: Math.min(68, Math.max(38, aliasText.implicitWidth + 12))
                                    Layout.preferredHeight: 20
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

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredWidth: root.wide ? 390 : pageContent.width
                    Layout.alignment: Qt.AlignTop
                    radius: settingsController.cardRadius
                    color: settingsController.surfaceColor
                    border.color: settingsController.borderColor
                    implicitHeight: summaryColumn.implicitHeight + 28

                    ColumnLayout {
                        id: summaryColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 14
                        spacing: 12

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: itemSearchController.wikiImage !== "" ? 150 : 92
                            radius: settingsController.cardRadius
                            color: settingsController.backgroundColor
                            border.color: settingsController.borderColor

                            Image {
                                anchors.fill: parent
                                anchors.margins: 12
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
                                font.pixelSize: 18
                                font.bold: true
                            }
                        }

                        Text {
                            text: itemSearchController.wikiName !== "" ? itemSearchController.wikiName : tr("wiki.empty_title")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 21
                            font.bold: true
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            text: root.wikiStatusText()
                            color: itemSearchController.wikiStatusKey === "item_search.wiki_error" ? settingsController.warningColor : settingsController.mutedTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }

                        Flow {
                            id: categoryFlow
                            Layout.fillWidth: true
                            Layout.preferredHeight: visible ? implicitHeight : 0
                            visible: wikiCategoriesRepeater.count > 0
                            spacing: 7

                            Repeater {
                                id: wikiCategoriesRepeater
                                model: itemSearchController.wikiCategories

                                delegate: Rectangle {
                                    width: Math.min(categoryFlow.width, Math.max(74, categoryText.implicitWidth + 20))
                                    height: 26
                                    radius: Math.min(7, settingsController.cardRadius)
                                    color: settingsController.accentPanelColor
                                    border.color: settingsController.borderColor

                                    Text {
                                        id: categoryText
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        text: model.label || ""
                                        color: settingsController.accentColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                    }
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

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            PrimaryButton {
                                Layout.fillWidth: true
                                text: tr("wiki.damage_open")
                                onClicked: root.openDamageDialog()
                            }

                            PrimaryButton {
                                Layout.fillWidth: true
                                text: tr("item_search.wiki_open")
                                enabled: itemSearchController.wikiSourceUrl !== ""
                                onClicked: itemSearchController.openWikiPage()
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: root.wide ? Math.max(480, pageContent.width - 414) : pageContent.width
                    Layout.alignment: Qt.AlignTop
                    visible: root.wide
                    spacing: 12

                    Loader {
                        Layout.fillWidth: true
                        sourceComponent: detailsComponent
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.wide
                spacing: 12

                Loader {
                    Layout.fillWidth: true
                    sourceComponent: detailsComponent
                }
            }
        }
    }

    Component {
        id: detailsComponent

        ColumnLayout {
            spacing: 12

            Rectangle {
                Layout.fillWidth: true
                visible: wikiFieldsRepeater.count > 0
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor
                implicitHeight: fieldsColumn.implicitHeight + 26

                ColumnLayout {
                    id: fieldsColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 13
                    spacing: 7

                    Text {
                        text: tr("item_search.wiki_fields")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 15
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    Repeater {
                        id: wikiFieldsRepeater
                        model: itemSearchController.wikiFields

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: Math.max(46, Math.max(fieldLabel.implicitHeight, fieldValue.implicitHeight) + 20)
                            radius: Math.min(5, settingsController.cardRadius)
                            color: index % 2 === 0 ? settingsController.backgroundColor : "transparent"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                anchors.topMargin: 8
                                anchors.bottomMargin: 8
                                spacing: 14

                                Text {
                                    id: fieldLabel
                                    text: model.label || "-"
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                    Layout.preferredWidth: root.wide ? 190 : 132
                                    Layout.maximumWidth: root.wide ? 230 : 150
                                    Layout.alignment: Qt.AlignVCenter
                                    wrapMode: Text.WordWrap
                                }

                                Text {
                                    id: fieldValue
                                    text: model.value || "-"
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignVCenter
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                visible: wikiSectionsRepeater.count > 0
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor
                implicitHeight: sectionsColumn.implicitHeight + 26

                ColumnLayout {
                    id: sectionsColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 13
                    spacing: 8

                    Text {
                        text: tr("wiki.sections")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 15
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    Repeater {
                        id: wikiSectionsRepeater
                        model: itemSearchController.wikiSections

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: sectionBody.implicitHeight + 42
                            radius: Math.min(6, settingsController.cardRadius)
                            color: settingsController.backgroundColor
                            border.color: settingsController.borderColor

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 5

                                Text {
                                    text: model.title || "-"
                                    color: settingsController.accentColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 13
                                    font.bold: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                Text {
                                    id: sectionBody
                                    text: model.body || ""
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    lineHeight: 1.12
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                visible: wikiProductionRepeater.count > 0
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor
                implicitHeight: productionColumn.implicitHeight + 26

                ColumnLayout {
                    id: productionColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 13
                    spacing: 7

                    Text {
                        text: tr("item_search.wiki_production")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 15
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
                                anchors.margins: 9
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
            }

            Rectangle {
                Layout.fillWidth: true
                visible: wikiFieldsRepeater.count === 0 && wikiProductionRepeater.count === 0 && wikiSectionsRepeater.count === 0
                radius: settingsController.cardRadius
                color: settingsController.surfaceColor
                border.color: settingsController.borderColor
                implicitHeight: 118

                Text {
                    anchors.centerIn: parent
                    width: parent.width - 32
                    text: tr("item_search.wiki_no_data")
                    color: settingsController.mutedTextColor
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    wrapMode: Text.WordWrap
                }
            }
        }
    }


    Dialog {
        id: damageDialog
        modal: true
        width: Math.min(920, root.width - 24)
        height: Math.min(720, root.height - 24)
        x: Math.round((root.width - width) / 2)
        y: Math.round((root.height - height) / 2)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: 14
            color: settingsController.surfaceColor
            border.color: settingsController.accentColor
            border.width: 1.5

            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 64
                radius: 14
                color: Qt.rgba(
                    Qt.darker(settingsController.accentColor, 2).r,
                    Qt.darker(settingsController.accentColor, 2).g,
                    Qt.darker(settingsController.accentColor, 2).b,
                    0.55
                )
                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 14
                    color: parent.color
                }
            }
        }

        contentItem: ColumnLayout {
            spacing: 0

            // ── Header ──────────────────────────────────────────────
            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 2
                Layout.leftMargin: 4
                Layout.rightMargin: 4
                spacing: 10

                // Icon
                Rectangle {
                    width: 38
                    height: 38
                    radius: 10
                    color: settingsController.accentPanelColor
                    border.color: settingsController.accentColor

                    Canvas {
                        anchors.centerIn: parent
                        width: 22
                        height: 22
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)
                            ctx.strokeStyle = settingsController.accentColor
                            ctx.lineWidth = 2
                            ctx.lineCap = "round"
                            // crosshair
                            ctx.beginPath()
                            ctx.arc(11, 11, 7, 0, Math.PI * 2)
                            ctx.stroke()
                            ctx.beginPath()
                            ctx.moveTo(11, 2); ctx.lineTo(11, 5)
                            ctx.moveTo(11, 17); ctx.lineTo(11, 20)
                            ctx.moveTo(2, 11); ctx.lineTo(5, 11)
                            ctx.moveTo(17, 11); ctx.lineTo(20, 11)
                            ctx.stroke()
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1

                    Text {
                        text: tr("wiki.damage_title")
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    Text {
                        text: itemSearchController.wikiName !== "" ? itemSearchController.wikiName : tr("wiki.empty_title")
                        color: settingsController.accentColor
                        font.family: "Segoe UI"
                        font.pixelSize: 11
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        opacity: 0.9
                    }
                }

                // Tab selector styled as pills
                Row {
                    spacing: 0

                    Rectangle {
                        id: tabBreak
                        width: 130
                        height: 34
                        radius: 8
                        color: damageModeBar.currentIndex === 0 ? settingsController.accentColor : settingsController.backgroundColor
                        border.color: damageModeBar.currentIndex === 0 ? settingsController.accentColor : settingsController.borderColor

                        Text {
                            anchors.centerIn: parent
                            text: tr("wiki.damage_break")
                            color: damageModeBar.currentIndex === 0 ? settingsController.textInverseColor : settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            font.bold: true
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: damageModeBar.currentIndex = 0
                        }

                        Behavior on color { ColorAnimation { duration: 140 } }
                    }

                    Item { width: 6; height: 1 }

                    Rectangle {
                        id: tabDuel
                        width: 140
                        height: 34
                        radius: 8
                        color: damageModeBar.currentIndex === 1 ? settingsController.accentColor : settingsController.backgroundColor
                        border.color: damageModeBar.currentIndex === 1 ? settingsController.accentColor : settingsController.borderColor

                        Text {
                            anchors.centerIn: parent
                            text: tr("wiki.damage_duel")
                            color: damageModeBar.currentIndex === 1 ? settingsController.textInverseColor : settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            font.bold: true
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: damageModeBar.currentIndex = 1
                        }

                        Behavior on color { ColorAnimation { duration: 140 } }
                    }
                }

                // Hidden TabBar for logic only
                TabBar {
                    id: damageModeBar
                    visible: false
                    TabButton {}
                    TabButton {}
                }

                Rectangle {
                    width: 34
                    height: 34
                    radius: 8
                    color: closeBtnMouse.containsMouse ? Qt.rgba(1,0.2,0.2,0.22) : settingsController.backgroundColor
                    border.color: closeBtnMouse.containsMouse ? "#e05555" : settingsController.borderColor

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: closeBtnMouse.containsMouse ? "#e05555" : settingsController.mutedTextColor
                        font.pixelSize: 13
                        font.bold: true
                    }

                    MouseArea {
                        id: closeBtnMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: damageDialog.close()
                    }

                    Behavior on color { ColorAnimation { duration: 120 } }
                }
            }

            // Divider
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: settingsController.borderColor
                opacity: 0.5
                Layout.topMargin: 8
                Layout.bottomMargin: 10
                Layout.leftMargin: 4
                Layout.rightMargin: 4
            }

            // ── Pages ────────────────────────────────────────────────
            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.leftMargin: 4
                Layout.rightMargin: 4
                Layout.bottomMargin: 4
                currentIndex: damageModeBar.currentIndex

                // ===== PAGE 0: Quebrar Alvo =====
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8

                        // Input row
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Rectangle {
                                Layout.fillWidth: true
                                height: 42
                                radius: 9
                                color: settingsController.backgroundColor
                                border.color: damageAmmoField.activeFocus ? settingsController.accentColor : settingsController.borderColor

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 10
                                    spacing: 8

                                    Text {
                                        text: "🔫"
                                        font.pixelSize: 14
                                    }

                                    TextField {
                                        id: damageAmmoField
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        placeholderText: tr("wiki.damage_ammo")
                                        color: settingsController.textColor
                                        placeholderTextColor: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        selectByMouse: true
                                        onTextEdited: itemSearchController.searchDamageAmmo(text)
                                        onAccepted: itemSearchController.calculateDamageTarget(text, damagePenField.text)
                                        background: Item {}
                                    }
                                }

                                Behavior on border.color { ColorAnimation { duration: 120 } }
                            }

                            Rectangle {
                                width: 120
                                height: 42
                                radius: 9
                                color: settingsController.backgroundColor
                                border.color: damagePenField.activeFocus ? settingsController.accentColor : settingsController.borderColor

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 8
                                    spacing: 6

                                    Text {
                                        text: "%"
                                        color: settingsController.mutedTextColor
                                        font.pixelSize: 14
                                        font.bold: true
                                    }

                                    TextField {
                                        id: damagePenField
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        placeholderText: tr("wiki.damage_pen")
                                        color: settingsController.textColor
                                        placeholderTextColor: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        selectByMouse: true
                                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                                        background: Item {}
                                    }
                                }

                                Behavior on border.color { ColorAnimation { duration: 120 } }
                            }

                            Rectangle {
                                width: 110
                                height: 42
                                radius: 9
                                color: calcBtnMouse.containsMouse ? Qt.lighter(settingsController.accentColor, 1.1) : settingsController.accentColor

                                Text {
                                    anchors.centerIn: parent
                                    text: tr("wiki.damage_calculate")
                                    color: settingsController.textInverseColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                }

                                MouseArea {
                                    id: calcBtnMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: itemSearchController.calculateDamageTarget(damageAmmoField.text, damagePenField.text)
                                }

                                Behavior on color { ColorAnimation { duration: 120 } }
                            }
                        }

                        // Target image + info banner
                        Rectangle {
                            Layout.fillWidth: true
                            height: itemSearchController.damageTargetImage !== "" ? 72 : 0
                            visible: itemSearchController.damageTargetImage !== ""
                            radius: 9
                            color: settingsController.backgroundColor
                            border.color: settingsController.borderColor

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 10

                                Rectangle {
                                    width: 80
                                    Layout.fillHeight: true
                                    radius: 7
                                    color: settingsController.surfaceColor
                                    border.color: settingsController.borderColor

                                    Image {
                                        anchors.fill: parent
                                        anchors.margins: 5
                                        source: itemSearchController.damageTargetImage
                                        fillMode: Image.PreserveAspectFit
                                        asynchronous: true
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignVCenter
                                    spacing: 3

                                    Text {
                                        text: itemSearchController.wikiName !== "" ? itemSearchController.wikiName : "-"
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 14
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        text: tr("wiki.damage_title")
                                        color: settingsController.accentColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 10
                                        font.bold: true
                                        font.capitalization: Font.AllUppercase
                                        opacity: 0.8
                                    }
                                }
                            }

                            Behavior on height { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                        }

                        // Ammo suggestion chips
                        ListView {
                            Layout.fillWidth: true
                            Layout.preferredHeight: count > 0 ? 36 : 0
                            visible: count > 0
                            orientation: ListView.Horizontal
                            spacing: 6
                            clip: true
                            model: itemSearchController.damageAmmoSuggestions

                            delegate: Rectangle {
                                height: 30
                                width: Math.min(220, Math.max(80, ammoChipLabel.implicitWidth + 24))
                                radius: 7
                                color: ammoChipMouse.containsMouse ? settingsController.accentPanelColor : settingsController.surfaceColor
                                border.color: ammoChipMouse.containsMouse ? settingsController.accentColor : settingsController.borderColor

                                Text {
                                    id: ammoChipLabel
                                    anchors.centerIn: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    text: model.name || ""
                                    color: ammoChipMouse.containsMouse ? settingsController.accentColor : settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                    font.bold: true
                                    elide: Text.ElideRight
                                }

                                MouseArea {
                                    id: ammoChipMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        damageAmmoField.text = model.name || ""
                                        itemSearchController.searchDamageAmmo(damageAmmoField.text)
                                        itemSearchController.calculateDamageTarget(damageAmmoField.text, damagePenField.text)
                                    }
                                }

                                ToolTip.visible: ammoChipMouse.containsMouse && model.detail !== ""
                                ToolTip.text: model.detail || ""

                                Behavior on color { ColorAnimation { duration: 100 } }
                                Behavior on border.color { ColorAnimation { duration: 100 } }
                            }

                            ScrollBar.horizontal: ScrollBar { active: parent.moving }
                        }

                        // Results grid
                        Flickable {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            contentWidth: width
                            contentHeight: damageResultGrid.implicitHeight + 4

                            ScrollBar.vertical: ScrollBar { active: parent.moving || parent.flicking }

                            GridLayout {
                                id: damageResultGrid
                                width: parent.width
                                columns: width > 540 ? 2 : 1
                                columnSpacing: 8
                                rowSpacing: 8

                                Repeater {
                                    model: itemSearchController.damageResultRows

                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: Math.max(76, dmgVal.implicitHeight + dmgLbl.implicitHeight + 32)
                                        radius: 10
                                        color: {
                                            if (model.kind === "success") return Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.12)
                                            if (model.kind === "warning") return Qt.rgba(settingsController.warningColor.r, settingsController.warningColor.g, settingsController.warningColor.b, 0.08)
                                            if (model.kind === "note")    return Qt.rgba(0.5, 0.5, 0.5, 0.08)
                                            return settingsController.backgroundColor
                                        }
                                        border.color: {
                                            if (model.kind === "success") return Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.4)
                                            if (model.kind === "warning") return Qt.rgba(settingsController.warningColor.r, settingsController.warningColor.g, settingsController.warningColor.b, 0.4)
                                            if (model.kind === "note")    return settingsController.borderColor
                                            return settingsController.borderColor
                                        }
                                        border.width: 1

                                        // left accent bar
                                        Rectangle {
                                            anchors.left: parent.left
                                            anchors.top: parent.top
                                            anchors.bottom: parent.bottom
                                            anchors.topMargin: 8
                                            anchors.bottomMargin: 8
                                            width: 3
                                            radius: 2
                                            color: root.rowKindColor(model.kind || "")
                                        }

                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 14
                                            anchors.rightMargin: 12
                                            anchors.topMargin: 10
                                            anchors.bottomMargin: 10
                                            spacing: 3

                                            Text {
                                                id: dmgVal
                                                text: model.value || "-"
                                                color: settingsController.textColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: model.kind === "note" ? 11 : 20
                                                font.bold: model.kind !== "note"
                                                Layout.fillWidth: true
                                                wrapMode: Text.WordWrap
                                            }

                                            Text {
                                                id: dmgLbl
                                                text: model.label || "-"
                                                color: root.rowKindColor(model.kind || "")
                                                font.family: "Segoe UI"
                                                font.pixelSize: 10
                                                font.bold: true
                                                font.capitalization: Font.AllUppercase
                                                Layout.fillWidth: true
                                                wrapMode: Text.WordWrap
                                                opacity: 0.85
                                            }
                                        }

                                        Behavior on color { ColorAnimation { duration: 150 } }
                                    }
                                }
                            }
                        }
                    }
                }

                // ===== PAGE 1: Duelo de Tanques =====
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8

                        // Tank selection row
                        GridLayout {
                            Layout.fillWidth: true
                            columns: root.wide ? 3 : 1
                            columnSpacing: 8
                            rowSpacing: 8

                            // Tank A input
                            Rectangle {
                                Layout.fillWidth: true
                                height: 42
                                radius: 9
                                color: settingsController.backgroundColor
                                border.color: duelLeftField.activeFocus ? settingsController.accentColor : settingsController.borderColor

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 8
                                    spacing: 8

                                    Rectangle {
                                        width: 20
                                        height: 20
                                        radius: 5
                                        color: settingsController.accentPanelColor
                                        border.color: settingsController.accentColor
                                        Text {
                                            anchors.centerIn: parent
                                            text: "A"
                                            color: settingsController.accentColor
                                            font.pixelSize: 10
                                            font.bold: true
                                        }
                                    }

                                    TextField {
                                        id: duelLeftField
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        placeholderText: tr("wiki.damage_tank_a")
                                        color: settingsController.textColor
                                        placeholderTextColor: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        selectByMouse: true
                                        onTextEdited: itemSearchController.searchDamageDuelTarget(text, "left")
                                        background: Item {}
                                    }
                                }

                                Behavior on border.color { ColorAnimation { duration: 120 } }
                            }

                            // VS center
                            Rectangle {
                                Layout.preferredWidth: root.wide ? 50 : parent.width
                                height: 42
                                radius: 9
                                color: settingsController.accentPanelColor
                                border.color: settingsController.accentColor

                                Text {
                                    anchors.centerIn: parent
                                    text: "VS"
                                    color: settingsController.accentColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 14
                                    font.bold: true
                                    font.letterSpacing: 1.5
                                }
                            }

                            // Tank B input
                            Rectangle {
                                Layout.fillWidth: true
                                height: 42
                                radius: 9
                                color: settingsController.backgroundColor
                                border.color: duelRightField.activeFocus ? settingsController.accentColor : settingsController.borderColor

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 8
                                    spacing: 8

                                    Rectangle {
                                        width: 20
                                        height: 20
                                        radius: 5
                                        color: Qt.rgba(settingsController.warningColor.r, settingsController.warningColor.g, settingsController.warningColor.b, 0.2)
                                        border.color: settingsController.warningColor
                                        Text {
                                            anchors.centerIn: parent
                                            text: "B"
                                            color: settingsController.warningColor
                                            font.pixelSize: 10
                                            font.bold: true
                                        }
                                    }

                                    TextField {
                                        id: duelRightField
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        placeholderText: tr("wiki.damage_tank_b")
                                        color: settingsController.textColor
                                        placeholderTextColor: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        selectByMouse: true
                                        onTextEdited: itemSearchController.searchDamageDuelTarget(text, "right")
                                        background: Item {}
                                    }
                                }

                                Behavior on border.color { ColorAnimation { duration: 120 } }
                            }
                        }

                        // Suggestions row
                        GridLayout {
                            Layout.fillWidth: true
                            columns: root.wide ? 2 : 1
                            columnSpacing: 8
                            rowSpacing: 4

                            ListView {
                                Layout.fillWidth: true
                                Layout.preferredHeight: count > 0 ? 34 : 0
                                visible: count > 0
                                orientation: ListView.Horizontal
                                spacing: 6
                                clip: true
                                model: itemSearchController.damageDuelLeftSuggestions

                                delegate: Rectangle {
                                    height: 28
                                    width: Math.min(210, Math.max(80, leftTankChip.implicitWidth + 22))
                                    radius: 7
                                    color: leftChipMouse.containsMouse ? settingsController.accentPanelColor : settingsController.surfaceColor
                                    border.color: leftChipMouse.containsMouse ? settingsController.accentColor : settingsController.borderColor

                                    Text {
                                        id: leftTankChip
                                        anchors.centerIn: parent
                                        text: model.name || ""
                                        color: leftChipMouse.containsMouse ? settingsController.accentColor : settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }

                                    MouseArea {
                                        id: leftChipMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            duelLeftField.text = model.name || ""
                                            itemSearchController.searchDamageDuelTarget(duelLeftField.text, "left")
                                            Qt.callLater(root.tryAutoDuel)
                                        }
                                    }

                                    Behavior on color { ColorAnimation { duration: 100 } }
                                }

                                ScrollBar.horizontal: ScrollBar { active: parent.moving }
                            }

                            ListView {
                                Layout.fillWidth: true
                                Layout.preferredHeight: count > 0 ? 34 : 0
                                visible: count > 0
                                orientation: ListView.Horizontal
                                spacing: 6
                                clip: true
                                model: itemSearchController.damageDuelRightSuggestions

                                delegate: Rectangle {
                                    height: 28
                                    width: Math.min(210, Math.max(80, rightTankChip.implicitWidth + 22))
                                    radius: 7
                                    color: rightChipMouse.containsMouse ? Qt.rgba(settingsController.warningColor.r, settingsController.warningColor.g, settingsController.warningColor.b, 0.15) : settingsController.surfaceColor
                                    border.color: rightChipMouse.containsMouse ? settingsController.warningColor : settingsController.borderColor

                                    Text {
                                        id: rightTankChip
                                        anchors.centerIn: parent
                                        text: model.name || ""
                                        color: rightChipMouse.containsMouse ? settingsController.warningColor : settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }

                                    MouseArea {
                                        id: rightChipMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            duelRightField.text = model.name || ""
                                            itemSearchController.searchDamageDuelTarget(duelRightField.text, "right")
                                            Qt.callLater(root.tryAutoDuel)
                                        }
                                    }

                                    Behavior on color { ColorAnimation { duration: 100 } }
                                }

                                ScrollBar.horizontal: ScrollBar { active: parent.moving }
                            }
                        }

                        // Tank preview cards (A vs B) with faction-colored borders and VS win-bar
                        GridLayout {
                            Layout.fillWidth: true
                            columns: root.wide ? 3 : 1
                            columnSpacing: 8
                            rowSpacing: 6

                            // Tank A card
                            Rectangle {
                                Layout.fillWidth: true
                                height: 120
                                radius: 10
                                color: settingsController.backgroundColor
                                border.color: {
                                    var fc = itemSearchController.damageDuelLeftFaction
                                    if (fc === "warden")   return Qt.rgba(0.23, 0.52, 0.83, 0.7)
                                    if (fc === "colonial") return Qt.rgba(0.23, 0.72, 0.42, 0.7)
                                    return Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.4)
                                }
                                border.width: 1.5

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 10

                                    Rectangle {
                                        width: 90
                                        Layout.fillHeight: true
                                        radius: 8
                                        color: settingsController.surfaceColor
                                        border.color: settingsController.borderColor

                                        Image {
                                            anchors.fill: parent
                                            anchors.margins: 6
                                            source: itemSearchController.damageDuelLeftImage
                                            visible: itemSearchController.damageDuelLeftImage !== ""
                                            fillMode: Image.PreserveAspectFit
                                            asynchronous: true
                                        }

                                        Text {
                                            anchors.centerIn: parent
                                            visible: itemSearchController.damageDuelLeftImage === ""
                                            text: "🛡"
                                            font.pixelSize: 26
                                            opacity: 0.4
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Layout.alignment: Qt.AlignVCenter
                                        spacing: 4

                                        Rectangle {
                                            width: 30
                                            height: 16
                                            radius: 4
                                            color: settingsController.accentColor

                                            Text {
                                                anchors.centerIn: parent
                                                text: "A"
                                                color: settingsController.textInverseColor
                                                font.pixelSize: 9
                                                font.bold: true
                                            }
                                        }

                                        Text {
                                            text: itemSearchController.damageDuelLeftName !== "" ? itemSearchController.damageDuelLeftName : tr("wiki.damage_tank_a")
                                            color: settingsController.textColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 13
                                            font.bold: true
                                            Layout.fillWidth: true
                                            wrapMode: Text.WordWrap
                                        }

                                        Text {
                                            text: itemSearchController.damageDuelLeftDetail !== "" ? itemSearchController.damageDuelLeftDetail : "—"
                                            color: settingsController.mutedTextColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 10
                                            Layout.fillWidth: true
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                            }

                            // VS center — faction win-chance bar
                            Item {
                                Layout.preferredWidth: root.wide ? 54 : parent.width
                                height: root.wide ? 120 : 54

                                // Background
                                Rectangle {
                                    anchors.fill: parent
                                    radius: 10
                                    color: settingsController.surfaceColor
                                    border.color: settingsController.borderColor
                                }

                                // Win bar — left side
                                property real leftP: itemSearchController.damageDuelLeftProb
                                property real rightP: itemSearchController.damageDuelRightProb
                                property bool hasProb: leftP >= 0 && rightP >= 0

                                Rectangle {
                                    visible: parent.hasProb && root.wide
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    anchors.left: parent.left
                                    anchors.margins: 4
                                    width: parent.hasProb ? Math.max(4, (parent.width - 8) * parent.leftP / (parent.leftP + parent.rightP)) : 0
                                    radius: 8
                                    color: factionColor(itemSearchController.damageDuelLeftFaction)
                                    opacity: 0.7
                                    Behavior on width { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
                                }

                                // Win bar — right side
                                Rectangle {
                                    visible: parent.hasProb && root.wide
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    anchors.right: parent.right
                                    anchors.margins: 4
                                    width: parent.hasProb ? Math.max(4, (parent.width - 8) * parent.rightP / (parent.leftP + parent.rightP)) : 0
                                    radius: 8
                                    color: factionColor(itemSearchController.damageDuelRightFaction)
                                    opacity: 0.7
                                    Behavior on width { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
                                }

                                // VS label
                                Text {
                                    anchors.centerIn: parent
                                    text: "VS"
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 14
                                    font.bold: true
                                    font.letterSpacing: 2
                                    style: Text.Outline
                                    styleColor: settingsController.backgroundColor
                                }
                            }

                            // Tank B card
                            Rectangle {
                                Layout.fillWidth: true
                                height: 120
                                radius: 10
                                color: settingsController.backgroundColor
                                border.color: {
                                    var fc = itemSearchController.damageDuelRightFaction
                                    if (fc === "warden")   return Qt.rgba(0.23, 0.52, 0.83, 0.7)
                                    if (fc === "colonial") return Qt.rgba(0.23, 0.72, 0.42, 0.7)
                                    return Qt.rgba(settingsController.warningColor.r, settingsController.warningColor.g, settingsController.warningColor.b, 0.4)
                                }
                                border.width: 1.5

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 10

                                    Rectangle {
                                        width: 90
                                        Layout.fillHeight: true
                                        radius: 8
                                        color: settingsController.surfaceColor
                                        border.color: settingsController.borderColor

                                        Image {
                                            anchors.fill: parent
                                            anchors.margins: 6
                                            source: itemSearchController.damageDuelRightImage
                                            visible: itemSearchController.damageDuelRightImage !== ""
                                            fillMode: Image.PreserveAspectFit
                                            asynchronous: true
                                        }

                                        Text {
                                            anchors.centerIn: parent
                                            visible: itemSearchController.damageDuelRightImage === ""
                                            text: "🛡"
                                            font.pixelSize: 26
                                            opacity: 0.4
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Layout.alignment: Qt.AlignVCenter
                                        spacing: 4

                                        Rectangle {
                                            width: 30
                                            height: 16
                                            radius: 4
                                            color: settingsController.warningColor

                                            Text {
                                                anchors.centerIn: parent
                                                text: "B"
                                                color: settingsController.backgroundColor
                                                font.pixelSize: 9
                                                font.bold: true
                                            }
                                        }

                                        Text {
                                            text: itemSearchController.damageDuelRightName !== "" ? itemSearchController.damageDuelRightName : tr("wiki.damage_tank_b")
                                            color: settingsController.textColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 13
                                            font.bold: true
                                            Layout.fillWidth: true
                                            wrapMode: Text.WordWrap
                                        }

                                        Text {
                                            text: itemSearchController.damageDuelRightDetail !== "" ? itemSearchController.damageDuelRightDetail : "—"
                                            color: settingsController.mutedTextColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 10
                                            Layout.fillWidth: true
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                            }
                        }

                        // Ammo + calc row
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Rectangle {
                                Layout.fillWidth: true
                                height: 42
                                radius: 9
                                color: settingsController.backgroundColor
                                border.color: duelAmmoField.activeFocus ? settingsController.accentColor : settingsController.borderColor

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 8
                                    spacing: 8

                                    Text {
                                        text: "💥"
                                        font.pixelSize: 13
                                    }

                                    TextField {
                                        id: duelAmmoField
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        placeholderText: tr("wiki.damage_ammo") + " (vazio = todas)"
                                        color: settingsController.textColor
                                        placeholderTextColor: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        selectByMouse: true
                                        background: Item {}
                                    }
                                }

                                Behavior on border.color { ColorAnimation { duration: 120 } }
                            }

                            Rectangle {
                                width: 110
                                height: 42
                                radius: 9
                                color: settingsController.backgroundColor
                                border.color: duelPenField.activeFocus ? settingsController.accentColor : settingsController.borderColor

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 8
                                    spacing: 6

                                    Text {
                                        text: "%"
                                        color: settingsController.mutedTextColor
                                        font.pixelSize: 14
                                        font.bold: true
                                    }

                                    TextField {
                                        id: duelPenField
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        placeholderText: tr("wiki.damage_pen")
                                        color: settingsController.textColor
                                        placeholderTextColor: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        selectByMouse: true
                                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                                        background: Item {}
                                    }
                                }

                                Behavior on border.color { ColorAnimation { duration: 120 } }
                            }

                            Rectangle {
                                width: 110
                                height: 42
                                radius: 9
                                color: duelCalcMouse.containsMouse ? Qt.lighter(settingsController.accentColor, 1.1) : settingsController.accentColor

                                Text {
                                    anchors.centerIn: parent
                                    text: tr("wiki.damage_calculate")
                                    color: settingsController.textInverseColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                }

                                MouseArea {
                                    id: duelCalcMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: itemSearchController.calculateTankDuel(duelLeftField.text, duelRightField.text, duelAmmoField.text, duelPenField.text)
                                }

                                Behavior on color { ColorAnimation { duration: 120 } }
                            }
                        }

                        // Duel results — scrollable card grid
                        Flickable {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            contentWidth: width
                            contentHeight: duelResultGrid.implicitHeight + 4

                            ScrollBar.vertical: ScrollBar { active: parent.moving || parent.flicking }

                            ColumnLayout {
                                id: duelResultGrid
                                width: parent.width
                                spacing: 6

                                Repeater {
                                    model: itemSearchController.damageDuelRows

                                    delegate: Item {
                                        Layout.fillWidth: true
                                        // Winner card: full width, tall, prominent
                                        implicitHeight: isWinner ? 100 : isLoser ? 72 : Math.max(58, duelVal.implicitHeight + duelLbl.implicitHeight + 28)

                                        property bool isWinner: model.kind === "winner"
                                        property bool isLoser:  model.kind === "loser"
                                        property bool isNote:   model.kind === "note"

                                        // Winner / Loser big card
                                        Rectangle {
                                            anchors.fill: parent
                                            visible: isWinner || isLoser
                                            radius: 12
                                            color: isWinner
                                                ? Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.18)
                                                : Qt.rgba(0.15, 0.15, 0.15, 0.5)
                                            border.color: isWinner
                                                ? Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.7)
                                                : settingsController.borderColor
                                            border.width: isWinner ? 2 : 1

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.margins: 14
                                                spacing: 12

                                                // Trophy / X icon
                                                Text {
                                                    text: isWinner ? "🏆" : "💀"
                                                    font.pixelSize: isWinner ? 32 : 22
                                                    opacity: isLoser ? 0.5 : 1.0
                                                }

                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 2

                                                    Text {
                                                        text: model.value || "-"
                                                        color: isWinner ? settingsController.accentColor : settingsController.mutedTextColor
                                                        font.family: "Segoe UI"
                                                        font.pixelSize: isWinner ? 22 : 16
                                                        font.bold: true
                                                        Layout.fillWidth: true
                                                        wrapMode: Text.WordWrap
                                                    }

                                                    Text {
                                                        text: model.label || ""
                                                        color: isWinner ? settingsController.accentColor : settingsController.mutedTextColor
                                                        font.family: "Segoe UI"
                                                        font.pixelSize: 10
                                                        font.bold: true
                                                        font.capitalization: Font.AllUppercase
                                                        Layout.fillWidth: true
                                                        wrapMode: Text.WordWrap
                                                        opacity: 0.8
                                                    }
                                                }
                                            }

                                            Behavior on color { ColorAnimation { duration: 200 } }
                                        }

                                        // Normal / compact card (success / warning / info / note)
                                        Rectangle {
                                            anchors.fill: parent
                                            visible: !isWinner && !isLoser
                                            radius: 9
                                            color: {
                                                if (model.kind === "success") return Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.1)
                                                if (model.kind === "warning") return Qt.rgba(settingsController.warningColor.r, settingsController.warningColor.g, settingsController.warningColor.b, 0.07)
                                                if (model.kind === "note")    return Qt.rgba(0.5, 0.5, 0.5, 0.06)
                                                return settingsController.backgroundColor
                                            }
                                            border.color: {
                                                if (model.kind === "success") return Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.3)
                                                if (model.kind === "warning") return Qt.rgba(settingsController.warningColor.r, settingsController.warningColor.g, settingsController.warningColor.b, 0.3)
                                                if (model.kind === "note")    return settingsController.borderColor
                                                return settingsController.borderColor
                                            }
                                            border.width: 1

                                            // Left accent bar
                                            Rectangle {
                                                anchors.left: parent.left
                                                anchors.top: parent.top
                                                anchors.bottom: parent.bottom
                                                anchors.topMargin: 7
                                                anchors.bottomMargin: 7
                                                width: 3
                                                radius: 2
                                                color: root.rowKindColor(model.kind || "")
                                                visible: !isNote
                                            }

                                            ColumnLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: 14
                                                anchors.rightMargin: 12
                                                anchors.topMargin: 9
                                                anchors.bottomMargin: 9
                                                spacing: 2

                                                Text {
                                                    id: duelVal
                                                    text: model.value || "-"
                                                    color: settingsController.textColor
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: isNote ? 10 : 15
                                                    font.bold: !isNote
                                                    Layout.fillWidth: true
                                                    wrapMode: Text.WordWrap
                                                }

                                                Text {
                                                    id: duelLbl
                                                    text: model.label || "-"
                                                    color: root.rowKindColor(model.kind || "")
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 9
                                                    font.bold: true
                                                    font.capitalization: Font.AllUppercase
                                                    Layout.fillWidth: true
                                                    wrapMode: Text.WordWrap
                                                    opacity: 0.85
                                                }
                                            }

                                            Behavior on color { ColorAnimation { duration: 150 } }
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
}
