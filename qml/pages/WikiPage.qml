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
        damagePenField.text = ""
        duelPenField.text = ""
        damageDialog.open()
        Qt.callLater(function() {
            if (duelLeftFactionCombo) duelLeftFactionCombo.currentIndex = 0
            if (duelRightFactionCombo) duelRightFactionCombo.currentIndex = 0
            if (duelLeftSelect && duelLeftSelect.count > 0) {
                duelLeftSelect.currentIndex = 0
                duelLeftField.text = duelLeftSelect.currentText
            }
            if (duelRightSelect && duelRightSelect.count > 1) {
                duelRightSelect.currentIndex = 1
                duelRightField.text = duelRightSelect.currentText
            } else if (duelRightSelect && duelRightSelect.count > 0) {
                duelRightSelect.currentIndex = 0
                duelRightField.text = duelRightSelect.currentText
            }
            if (duelAmmoSelect && duelAmmoSelect.count > 0) {
                duelAmmoSelect.currentIndex = 0
                duelAmmoField.text = ""
            }
            root.scheduleDuelAuto()
        })
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

    function factionChoices() {
        i18nController.revision
        return [
            { text: tr("wiki.faction_all"), value: "" },
            { text: tr("wiki.faction_warden"), value: "warden" },
            { text: tr("wiki.faction_colonial"), value: "colonial" }
        ]
    }

    function selectedFactionValue(combo) {
        if (!combo || combo.currentIndex < 0 || !combo.model)
            return ""
        var entry = combo.model[combo.currentIndex]
        return entry && entry.value !== undefined ? String(entry.value) : ""
    }

    function updateDuelSuggestions(side) {
        if (side === "right") {
            itemSearchController.searchDamageDuelTarget(duelRightField.text, "right", selectedFactionValue(duelRightFactionCombo))
            return
        }
        itemSearchController.searchDamageDuelTarget(duelLeftField.text, "left", selectedFactionValue(duelLeftFactionCombo))
    }

    function tryAutoDuel() {
        var leftName = duelLeftSelect && duelLeftSelect.currentIndex >= 0 ? duelLeftSelect.currentText : duelLeftField.text
        var rightName = duelRightSelect && duelRightSelect.currentIndex >= 0 ? duelRightSelect.currentText : duelRightField.text
        var ammoChoice = ""
        if (duelAmmoSelect && duelAmmoSelect.currentIndex >= 0 && duelAmmoSelect.model) {
            var ammoEntry = duelAmmoSelect.model[duelAmmoSelect.currentIndex]
            ammoChoice = ammoEntry && ammoEntry.value !== undefined ? String(ammoEntry.value) : ""
        }
        duelLeftField.text = leftName || ""
        duelRightField.text = rightName || ""
        duelAmmoField.text = ammoChoice || ""
        if (duelLeftField.text.trim() !== "" && duelRightField.text.trim() !== "") {
            itemSearchController.calculateTankDuel(
                duelLeftField.text, duelRightField.text,
                duelAmmoField.text, duelPenField.text
            )
        }
    }

    function scheduleDuelAuto() {
        if (duelAutoTimer)
            duelAutoTimer.restart()
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
                            visible: itemSearchController.wikiDisplayTitle !== "" && itemSearchController.wikiDisplayTitle !== itemSearchController.wikiName
                            text: itemSearchController.wikiDisplayTitle
                            color: settingsController.accentColor
                            font.family: "Segoe UI"
                            font.pixelSize: 11
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

                        Text {
                            visible: wikiTechRepeater.count > 0
                            text: tr("wiki.tech_summary")
                            color: settingsController.accentColor
                            font.family: "Segoe UI"
                            font.pixelSize: 10
                            font.bold: true
                            font.letterSpacing: 1.0
                            Layout.fillWidth: true
                            opacity: 0.9
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: wikiTechRepeater.count > 0

                            Repeater {
                                id: wikiTechRepeater
                                model: itemSearchController.wikiTechRows

                                delegate: Rectangle {
                                    implicitHeight: 26
                                    implicitWidth: techLabel.implicitWidth + techValue.implicitWidth + 26
                                    radius: Math.min(8, settingsController.cardRadius)
                                    color: Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.08)
                                    border.color: root.rowKindColor(model.kind || "")
                                    border.width: 1

                                    Row {
                                        anchors.centerIn: parent
                                        spacing: 6

                                        Text {
                                            id: techLabel
                                            text: model.label || ""
                                            color: settingsController.mutedTextColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 9
                                            font.bold: true
                                            opacity: 0.9
                                        }

                                        Text {
                                            id: techValue
                                            text: model.value || "-"
                                            color: settingsController.textColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 10
                                            font.bold: true
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: itemSearchController.wikiStatusKey !== "item_search.wiki_empty"

                            Rectangle {
                                visible: wikiCategoriesRepeater.count > 0
                                implicitWidth: metaCategoriesText.implicitWidth + 20
                                implicitHeight: 24
                                radius: Math.min(7, settingsController.cardRadius)
                                color: settingsController.backgroundColor
                                border.color: settingsController.borderColor

                                Text {
                                    id: metaCategoriesText
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    text: tr("wiki.categories") + ": " + String(wikiCategoriesRepeater.count)
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 10
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                            }

                            Rectangle {
                                visible: wikiFieldsRepeater.count > 0
                                implicitWidth: metaFieldsText.implicitWidth + 20
                                implicitHeight: 24
                                radius: Math.min(7, settingsController.cardRadius)
                                color: settingsController.backgroundColor
                                border.color: settingsController.borderColor

                                Text {
                                    id: metaFieldsText
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    text: tr("item_search.wiki_fields") + ": " + String(wikiFieldsRepeater.count)
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 10
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                            }

                            Rectangle {
                                visible: wikiSectionsRepeater.count > 0
                                implicitWidth: metaSectionsText.implicitWidth + 20
                                implicitHeight: 24
                                radius: Math.min(7, settingsController.cardRadius)
                                color: settingsController.backgroundColor
                                border.color: settingsController.borderColor

                                Text {
                                    id: metaSectionsText
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    text: tr("wiki.sections") + ": " + String(wikiSectionsRepeater.count)
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 10
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                            }

                            Rectangle {
                                visible: wikiProductionRepeater.count > 0
                                implicitWidth: metaProductionText.implicitWidth + 20
                                implicitHeight: 24
                                radius: Math.min(7, settingsController.cardRadius)
                                color: settingsController.backgroundColor
                                border.color: settingsController.borderColor

                                Text {
                                    id: metaProductionText
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    text: tr("item_search.wiki_production") + ": " + String(wikiProductionRepeater.count)
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 10
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                            }

                            Rectangle {
                                visible: itemSearchController.wikiSourceUrl !== ""
                                implicitWidth: metaSourceText.implicitWidth + 20
                                implicitHeight: 24
                                radius: Math.min(7, settingsController.cardRadius)
                                color: settingsController.backgroundColor
                                border.color: settingsController.borderColor

                                Text {
                                    id: metaSourceText
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    text: tr("wiki.source") + ": foxhole.wiki.gg"
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 10
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                            }
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
        property bool wideLayout: width >= 860
        property bool compactLayout: width < 620
        width: Math.min(920, root.width - 24)
        height: Math.min(720, root.height - 24)
        x: Math.round((root.width - width) / 2)
        y: Math.round((root.height - height) / 2)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        Timer {
            id: duelAutoTimer
            interval: 250
            repeat: false
            onTriggered: root.tryAutoDuel()
        }

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
                            onClicked: {
                                damageModeBar.currentIndex = 1
                                root.scheduleDuelAuto()
                            }
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
                        GridLayout {
                            Layout.fillWidth: true
                            columns: damageDialog.compactLayout ? 1 : 3
                            columnSpacing: 8
                            rowSpacing: 8

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
                                Layout.preferredWidth: 120
                                Layout.fillWidth: damageDialog.compactLayout
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
                                Layout.preferredWidth: 110
                                Layout.fillWidth: damageDialog.compactLayout
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

                        // Ammo attacking target preview
                        Rectangle {
                            Layout.fillWidth: true
                            height: (itemSearchController.damageAmmoImage !== "" || itemSearchController.damageTargetImage !== "") ? 86 : 0
                            visible: itemSearchController.damageAmmoImage !== "" || itemSearchController.damageTargetImage !== ""
                            radius: 9
                            color: settingsController.backgroundColor
                            border.color: settingsController.borderColor

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 8

                                Rectangle {
                                    Layout.preferredWidth: 148
                                    Layout.fillHeight: true
                                    radius: 8
                                    color: settingsController.surfaceColor
                                    border.color: itemSearchController.damageAmmoImage !== "" ? settingsController.accentColor : settingsController.borderColor

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        spacing: 7

                                        Rectangle {
                                            width: 56
                                            Layout.fillHeight: true
                                            radius: 7
                                            color: settingsController.backgroundColor
                                            border.color: settingsController.borderColor

                                            Image {
                                                anchors.fill: parent
                                                anchors.margins: 5
                                                source: itemSearchController.damageAmmoImage
                                                visible: itemSearchController.damageAmmoImage !== ""
                                                fillMode: Image.PreserveAspectFit
                                                asynchronous: true
                                            }

                                            Text {
                                                anchors.centerIn: parent
                                                visible: itemSearchController.damageAmmoImage === ""
                                                text: "DMG"
                                                color: settingsController.mutedTextColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 11
                                                font.bold: true
                                                opacity: 0.55
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Layout.alignment: Qt.AlignVCenter
                                            spacing: 2

                                            Text {
                                                text: damageAmmoField.text.trim() !== "" ? damageAmmoField.text : tr("wiki.damage_ammo")
                                                color: settingsController.textColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 12
                                                font.bold: true
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                text: tr("wiki.damage_ammo")
                                                color: settingsController.accentColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 9
                                                font.bold: true
                                                font.capitalization: Font.AllUppercase
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                                opacity: 0.8
                                            }
                                        }
                                    }
                                }

                                Text {
                                    Layout.preferredWidth: 28
                                    text: "->"
                                    color: settingsController.accentColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 16
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    radius: 8
                                    color: settingsController.surfaceColor
                                    border.color: settingsController.borderColor

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        spacing: 8

                                        Rectangle {
                                            width: 64
                                            Layout.fillHeight: true
                                            radius: 7
                                            color: settingsController.backgroundColor
                                            border.color: settingsController.borderColor

                                            Image {
                                                anchors.fill: parent
                                                anchors.margins: 5
                                                source: itemSearchController.damageTargetImage
                                                visible: itemSearchController.damageTargetImage !== ""
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
                                                color: settingsController.mutedTextColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 10
                                                font.bold: true
                                                font.capitalization: Font.AllUppercase
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                }
                            }

                            Behavior on height { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
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

                        TextField {
                            id: duelLeftField
                            visible: false
                            Layout.preferredHeight: 0
                            text: duelLeftSelect.currentText
                        }

                        TextField {
                            id: duelRightField
                            visible: false
                            Layout.preferredHeight: 0
                            text: duelRightSelect.currentText
                        }

                        TextField {
                            id: duelAmmoField
                            visible: false
                            Layout.preferredHeight: 0
                            text: ""
                        }

                        ComboBox {
                            id: duelLeftFactionCombo
                            visible: false
                            Layout.preferredHeight: 0
                            model: root.factionChoices()
                            textRole: "text"
                            valueRole: "value"
                            currentIndex: 0
                            onActivated: root.scheduleDuelAuto()
                        }

                        ComboBox {
                            id: duelRightFactionCombo
                            visible: false
                            Layout.preferredHeight: 0
                            model: root.factionChoices()
                            textRole: "text"
                            valueRole: "value"
                            currentIndex: 0
                            onActivated: root.scheduleDuelAuto()
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: damageDialog.wideLayout ? 3 : 1
                            columnSpacing: 10
                            rowSpacing: 8

                            Rectangle {
                                Layout.fillWidth: true
                                height: 86
                                radius: 10
                                color: Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.08)
                                border.color: settingsController.accentColor

                                ComboBox {
                                    id: duelLeftSelect
                                    anchors.fill: parent
                                    anchors.margins: 1
                                    model: itemSearchController.damageDuelPresets("")
                                    textRole: "name"
                                    valueRole: "name"
                                    currentIndex: 0
                                    onActivated: {
                                        duelLeftField.text = currentText
                                        root.scheduleDuelAuto()
                                    }
                                    contentItem: RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 12
                                        spacing: 10

                                        Image {
                                            Layout.preferredWidth: 62
                                            Layout.preferredHeight: 62
                                            source: duelLeftSelect.currentIndex >= 0 && duelLeftSelect.model[duelLeftSelect.currentIndex] ? (duelLeftSelect.model[duelLeftSelect.currentIndex].image || "") : ""
                                            fillMode: Image.PreserveAspectFit
                                            asynchronous: true
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Layout.alignment: Qt.AlignVCenter
                                            spacing: 3

                                            Text {
                                                text: tr("wiki.damage_tank_a")
                                                color: settingsController.accentColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 10
                                                font.bold: true
                                                font.capitalization: Font.AllUppercase
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                text: duelLeftSelect.currentText || tr("wiki.damage_preset")
                                                color: settingsController.textColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 14
                                                font.bold: true
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                text: duelLeftSelect.currentIndex >= 0 && duelLeftSelect.model[duelLeftSelect.currentIndex] ? (duelLeftSelect.model[duelLeftSelect.currentIndex].detail || "") : ""
                                                color: settingsController.mutedTextColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 10
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                    delegate: ItemDelegate {
                                        width: duelLeftSelect.width
                                        height: 54
                                        contentItem: RowLayout {
                                            spacing: 9
                                            Image {
                                                Layout.preferredWidth: 42
                                                Layout.preferredHeight: 42
                                                source: model.image || ""
                                                fillMode: Image.PreserveAspectFit
                                                asynchronous: true
                                            }
                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 1
                                                Text {
                                                    text: model.name || ""
                                                    color: settingsController.textColor
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 12
                                                    font.bold: true
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }
                                                Text {
                                                    text: model.detail || ""
                                                    color: settingsController.mutedTextColor
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 9
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }
                                            }
                                        }
                                    }
                                    background: Item {}
                                }
                            }

                            Rectangle {
                                Layout.preferredWidth: damageDialog.wideLayout ? 92 : parent.width
                                height: 86
                                radius: 10
                                color: settingsController.accentPanelColor
                                border.color: settingsController.accentColor

                                Text {
                                    anchors.centerIn: parent
                                    text: "VS"
                                    color: settingsController.accentColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 24
                                    font.bold: true
                                    font.letterSpacing: 2
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 86
                                radius: 10
                                color: Qt.rgba(settingsController.warningColor.r, settingsController.warningColor.g, settingsController.warningColor.b, 0.08)
                                border.color: settingsController.warningColor

                                ComboBox {
                                    id: duelRightSelect
                                    anchors.fill: parent
                                    anchors.margins: 1
                                    model: itemSearchController.damageDuelPresets("")
                                    textRole: "name"
                                    valueRole: "name"
                                    currentIndex: count > 1 ? 1 : 0
                                    onActivated: {
                                        duelRightField.text = currentText
                                        root.scheduleDuelAuto()
                                    }
                                    contentItem: RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 12
                                        spacing: 10

                                        Image {
                                            Layout.preferredWidth: 62
                                            Layout.preferredHeight: 62
                                            source: duelRightSelect.currentIndex >= 0 && duelRightSelect.model[duelRightSelect.currentIndex] ? (duelRightSelect.model[duelRightSelect.currentIndex].image || "") : ""
                                            fillMode: Image.PreserveAspectFit
                                            asynchronous: true
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Layout.alignment: Qt.AlignVCenter
                                            spacing: 3

                                            Text {
                                                text: tr("wiki.damage_tank_b")
                                                color: settingsController.warningColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 10
                                                font.bold: true
                                                font.capitalization: Font.AllUppercase
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                text: duelRightSelect.currentText || tr("wiki.damage_preset")
                                                color: settingsController.textColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 14
                                                font.bold: true
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                text: duelRightSelect.currentIndex >= 0 && duelRightSelect.model[duelRightSelect.currentIndex] ? (duelRightSelect.model[duelRightSelect.currentIndex].detail || "") : ""
                                                color: settingsController.mutedTextColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 10
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                    delegate: ItemDelegate {
                                        width: duelRightSelect.width
                                        height: 54
                                        contentItem: RowLayout {
                                            spacing: 9
                                            Image {
                                                Layout.preferredWidth: 42
                                                Layout.preferredHeight: 42
                                                source: model.image || ""
                                                fillMode: Image.PreserveAspectFit
                                                asynchronous: true
                                            }
                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 1
                                                Text {
                                                    text: model.name || ""
                                                    color: settingsController.textColor
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 12
                                                    font.bold: true
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }
                                                Text {
                                                    text: model.detail || ""
                                                    color: settingsController.mutedTextColor
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 9
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }
                                            }
                                        }
                                    }
                                    background: Item {}
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 38
                            radius: 9
                            color: Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.12)
                            border.color: Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.45)

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 10

                                Text {
                                    text: tr("wiki.damage_arena")
                                    color: settingsController.accentColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                    font.capitalization: Font.AllUppercase
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: itemSearchController.damageDuelWinnerName !== ""
                                        ? tr("wiki.damage_winner") + ": " + itemSearchController.damageDuelWinnerName
                                        : tr("wiki.damage_waiting")
                                    color: itemSearchController.damageDuelWinnerName !== "" ? settingsController.textColor : settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    font.bold: true
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignRight
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        // Tank preview cards (A vs B) with faction-colored borders and VS win-bar
                        GridLayout {
                            Layout.fillWidth: true
                            columns: damageDialog.wideLayout ? 3 : 1
                            columnSpacing: 8
                            rowSpacing: 6

                            // Tank A card
                            Rectangle {
                                Layout.fillWidth: true
                                height: 148
                                radius: 10
                                color: Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.08)
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
                                        width: 96
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

                                        Rectangle {
                                            width: 74
                                            height: 18
                                            radius: 6
                                            visible: itemSearchController.damageDuelLeftFaction !== ""
                                            color: Qt.rgba(
                                                factionColor(itemSearchController.damageDuelLeftFaction).r,
                                                factionColor(itemSearchController.damageDuelLeftFaction).g,
                                                factionColor(itemSearchController.damageDuelLeftFaction).b,
                                                0.15
                                            )
                                            border.color: factionColor(itemSearchController.damageDuelLeftFaction)

                                            Text {
                                                anchors.centerIn: parent
                                                text: itemSearchController.damageDuelLeftFaction === "warden" ? tr("wiki.faction_warden") : tr("wiki.faction_colonial")
                                                color: factionColor(itemSearchController.damageDuelLeftFaction)
                                                font.pixelSize: 8
                                                font.bold: true
                                                elide: Text.ElideRight
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
                                Layout.preferredWidth: damageDialog.wideLayout ? 110 : parent.width
                                height: damageDialog.wideLayout ? 148 : 72

                                // Background
                                Rectangle {
                                    anchors.fill: parent
                                    radius: 10
                                    color: Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.1)
                                    border.color: settingsController.accentColor
                                }

                                // Win bar — left side
                                property real leftP: itemSearchController.damageDuelLeftProb
                                property real rightP: itemSearchController.damageDuelRightProb
                                property bool hasProb: leftP >= 0 && rightP >= 0

                                Rectangle {
                                    visible: parent.hasProb && damageDialog.wideLayout
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
                                    visible: parent.hasProb && damageDialog.wideLayout
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

                                Column {
                                    anchors.centerIn: parent
                                    spacing: 5

                                    Rectangle {
                                        width: 48
                                        height: 48
                                        radius: 8
                                        visible: itemSearchController.damageDuelAmmoImage !== "" && damageDialog.wideLayout
                                        color: settingsController.backgroundColor
                                        border.color: settingsController.borderColor

                                        Image {
                                            anchors.fill: parent
                                            anchors.margins: 4
                                            source: itemSearchController.damageDuelAmmoImage
                                            fillMode: Image.PreserveAspectFit
                                            asynchronous: true
                                        }
                                    }

                                    Text {
                                        text: "VS"
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 18
                                        font.bold: true
                                        font.letterSpacing: 2
                                        style: Text.Outline
                                        styleColor: settingsController.backgroundColor
                                        horizontalAlignment: Text.AlignHCenter
                                    }
                                }
                            }

                            // Tank B card
                            Rectangle {
                                Layout.fillWidth: true
                                height: 148
                                radius: 10
                                color: Qt.rgba(settingsController.warningColor.r, settingsController.warningColor.g, settingsController.warningColor.b, 0.07)
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
                                        width: 96
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

                                        Rectangle {
                                            width: 74
                                            height: 18
                                            radius: 6
                                            visible: itemSearchController.damageDuelRightFaction !== ""
                                            color: Qt.rgba(
                                                factionColor(itemSearchController.damageDuelRightFaction).r,
                                                factionColor(itemSearchController.damageDuelRightFaction).g,
                                                factionColor(itemSearchController.damageDuelRightFaction).b,
                                                0.15
                                            )
                                            border.color: factionColor(itemSearchController.damageDuelRightFaction)

                                            Text {
                                                anchors.centerIn: parent
                                                text: itemSearchController.damageDuelRightFaction === "warden" ? tr("wiki.faction_warden") : tr("wiki.faction_colonial")
                                                color: factionColor(itemSearchController.damageDuelRightFaction)
                                                font.pixelSize: 8
                                                font.bold: true
                                                elide: Text.ElideRight
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

                        GridLayout {
                            Layout.fillWidth: true
                            columns: damageDialog.wideLayout ? 3 : 1
                            columnSpacing: 8
                            rowSpacing: 6

                            Rectangle {
                                Layout.fillWidth: true
                                height: 50
                                radius: 9
                                color: settingsController.backgroundColor
                                border.color: Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.45)

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 2

                                    Text {
                                        text: itemSearchController.damageDuelLeftName !== "" ? itemSearchController.damageDuelLeftName : tr("wiki.damage_tank_a")
                                        color: settingsController.accentColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 10
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        text: "HP " + (itemSearchController.damageDuelLeftHp !== "" ? itemSearchController.damageDuelLeftHp : "--") + "  |  " + tr("wiki.damage_avg_shots") + " " + (itemSearchController.damageDuelLeftShots !== "" ? itemSearchController.damageDuelLeftShots : "--")
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 50
                                radius: 9
                                color: Qt.rgba(settingsController.accentColor.r, settingsController.accentColor.g, settingsController.accentColor.b, 0.08)
                                border.color: settingsController.borderColor

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 8

                                    Image {
                                        Layout.preferredWidth: 34
                                        Layout.preferredHeight: 34
                                        source: itemSearchController.damageDuelAmmoImage
                                        visible: itemSearchController.damageDuelAmmoImage !== ""
                                        fillMode: Image.PreserveAspectFit
                                        asynchronous: true
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        Text {
                                            text: itemSearchController.damageDuelAmmoName !== "" ? itemSearchController.damageDuelAmmoName : tr("wiki.damage_selected_ammo")
                                            color: settingsController.textColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 11
                                            font.bold: true
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            text: itemSearchController.damageDuelAmmoDamage !== "" ? itemSearchController.damageDuelAmmoDamage : tr("wiki.damage_waiting")
                                            color: settingsController.mutedTextColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 10
                                            font.bold: true
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 50
                                radius: 9
                                color: settingsController.backgroundColor
                                border.color: Qt.rgba(settingsController.warningColor.r, settingsController.warningColor.g, settingsController.warningColor.b, 0.45)

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 2

                                    Text {
                                        text: itemSearchController.damageDuelRightName !== "" ? itemSearchController.damageDuelRightName : tr("wiki.damage_tank_b")
                                        color: settingsController.warningColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 10
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        text: "HP " + (itemSearchController.damageDuelRightHp !== "" ? itemSearchController.damageDuelRightHp : "--") + "  |  " + tr("wiki.damage_avg_shots") + " " + (itemSearchController.damageDuelRightShots !== "" ? itemSearchController.damageDuelRightShots : "--")
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }

                        // Ammo + penetration controls auto-update the duel.
                        GridLayout {
                            Layout.fillWidth: true
                            columns: damageDialog.compactLayout ? 1 : 2
                            columnSpacing: 8
                            rowSpacing: 8

                            Rectangle {
                                Layout.fillWidth: true
                                height: 42
                                radius: 9
                                color: settingsController.backgroundColor
                                border.color: duelAmmoSelect.activeFocus ? settingsController.accentColor : settingsController.borderColor

                                ComboBox {
                                    id: duelAmmoSelect
                                    anchors.fill: parent
                                    anchors.margins: 1
                                    model: itemSearchController.damageDuelAmmoOptions()
                                    textRole: "name"
                                    valueRole: "value"
                                    currentIndex: 0
                                    onActivated: {
                                        var entry = model && currentIndex >= 0 ? model[currentIndex] : null
                                        duelAmmoField.text = entry && entry.value !== undefined ? String(entry.value) : ""
                                        root.scheduleDuelAuto()
                                    }
                                    contentItem: RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 12
                                        spacing: 8

                                        Rectangle {
                                            Layout.preferredWidth: 28
                                            Layout.preferredHeight: 28
                                            radius: 7
                                            color: settingsController.surfaceColor
                                            border.color: settingsController.borderColor

                                            Text {
                                                anchors.centerIn: parent
                                                visible: !(duelAmmoSelect.currentIndex >= 0 && duelAmmoSelect.model[duelAmmoSelect.currentIndex] && duelAmmoSelect.model[duelAmmoSelect.currentIndex].image)
                                                text: "AUTO"
                                                color: settingsController.accentColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 7
                                                font.bold: true
                                            }

                                            Image {
                                                anchors.fill: parent
                                                anchors.margins: 4
                                                source: duelAmmoSelect.currentIndex >= 0 && duelAmmoSelect.model[duelAmmoSelect.currentIndex] ? (duelAmmoSelect.model[duelAmmoSelect.currentIndex].image || "") : ""
                                                fillMode: Image.PreserveAspectFit
                                                asynchronous: true
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Layout.alignment: Qt.AlignVCenter
                                            spacing: 0

                                            Text {
                                                text: duelAmmoSelect.currentText || tr("wiki.damage_selected_ammo")
                                                color: settingsController.textColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 12
                                                font.bold: true
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                text: duelAmmoSelect.currentIndex >= 0 && duelAmmoSelect.model[duelAmmoSelect.currentIndex] ? (duelAmmoSelect.model[duelAmmoSelect.currentIndex].detail || tr("wiki.damage_selected_ammo")) : tr("wiki.damage_selected_ammo")
                                                color: settingsController.mutedTextColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 9
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                    delegate: ItemDelegate {
                                        width: duelAmmoSelect.width
                                        height: 48
                                        contentItem: RowLayout {
                                            spacing: 8

                                            Rectangle {
                                                Layout.preferredWidth: 32
                                                Layout.preferredHeight: 32
                                                radius: 7
                                                color: settingsController.surfaceColor
                                                border.color: highlighted ? settingsController.accentColor : settingsController.borderColor

                                                Text {
                                                    anchors.centerIn: parent
                                                    visible: !(model.image || "")
                                                    text: "AUTO"
                                                    color: settingsController.accentColor
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 7
                                                    font.bold: true
                                                }

                                                Image {
                                                    anchors.fill: parent
                                                    anchors.margins: 4
                                                    source: model.image || ""
                                                    fillMode: Image.PreserveAspectFit
                                                    asynchronous: true
                                                }
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 1
                                                Text {
                                                    text: model.name || ""
                                                    color: settingsController.textColor
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 12
                                                    font.bold: true
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }
                                                Text {
                                                    text: model.detail || ""
                                                    color: settingsController.mutedTextColor
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 9
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }
                                            }
                                        }
                                    }
                                    background: Item {}
                                }

                                Behavior on border.color { ColorAnimation { duration: 120 } }
                            }

                            Rectangle {
                                Layout.preferredWidth: 150
                                Layout.fillWidth: damageDialog.compactLayout
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
                                        onTextEdited: root.scheduleDuelAuto()
                                        onAccepted: root.tryAutoDuel()
                                        background: Item {}
                                    }
                                }

                                Behavior on border.color { ColorAnimation { duration: 120 } }
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

                            GridLayout {
                                id: duelResultGrid
                                width: parent.width
                                columns: width > 620 ? 2 : 1
                                columnSpacing: 6
                                rowSpacing: 6

                                Repeater {
                                    model: itemSearchController.damageDuelRows

                                    delegate: Item {
                                        Layout.fillWidth: true
                                        Layout.columnSpan: isWinner || isLoser ? duelResultGrid.columns : 1
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
