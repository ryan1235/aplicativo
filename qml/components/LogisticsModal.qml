import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import "SlangTerms.js" as SlangTerms

// Full-screen overlay modal for the logistics tool.
// Flow: 1) Select destination depot  →  2) Search & pick items  →  3) Review & calculate routes

Item {
    id: logisticsModal
    anchors.fill: parent
    visible: false
    z: 500

    // ── Public API ──────────────────────────────────────────────
    signal routesCalculated(var routes)
    signal closed()

    property var mapItems: []          // bound to mapController.mapItemsModel

    function open() {
        _step = 1;
        _selectedDestination = null;
        _depotSearch = "";
        _itemSearch = "";
        _selectedItems = [];
        _searchResults = [];
        visible = true;
        openAnim.start();
    }

    function close() {
        visible = false;
        closed();
    }

    // ── Internal state ──────────────────────────────────────────
    property int _step: 1                     // 1, 2, or 3
    property var _selectedDestination: null    // mapItem chosen as destination
    property string _depotSearch: ""
    property string _itemSearch: ""
    property var _selectedItems: []           // [{name, icon, qty, maxQty}]
    property var _searchResults: []           // [{name, icon, totalQty, sources:[]}]

    function tr(key, fallback) {
        if (typeof i18nController !== "undefined") {
            i18nController.revision;
            var t = i18nController.t(key);
            if (t !== key) return t;
        }
        return fallback;
    }

    // ── Helper: get all depots with stock ──────────────────────
    function _getDepots() {
        var depots = [];
        if (!mapItems) return depots;
        for (var i = 0; i < mapItems.length; i++) {
            var item = mapItems[i];
            if (!item.stock) continue;
            var totalItems = 0;
            var warehouseNames = [];
            for (var w = 0; w < item.stock.length; w++) {
                var wh = item.stock[w];
                if (wh && wh.items) totalItems += wh.items.length;
                if (wh && wh.warehouse_name) warehouseNames.push(wh.warehouse_name);
            }
            if (totalItems > 0) {
                depots.push({
                    mapItem: item,
                    name: item.name || "Unknown",
                    warehouseNames: warehouseNames,
                    itemCount: totalItems,
                    type: item.type
                });
            }
        }
        depots.sort(function(a, b) { return a.name.localeCompare(b.name); });
        return depots;
    }

    // ── Helper: search items across ALL depots ─────────────────
    function _searchAllItems(query) {
        if (!query || query.length < 2) return [];
        var q = query.toLowerCase();
        var aggregated = {};  // name -> {name, icon, totalQty, sources:[{mapItem, warehouseName, qty}]}

        if (!mapItems) return [];
        for (var i = 0; i < mapItems.length; i++) {
            var item = mapItems[i];
            // skip the destination itself
            if (_selectedDestination && item.name === _selectedDestination.name) continue;
            if (!item.stock) continue;

            for (var w = 0; w < item.stock.length; w++) {
                var wh = item.stock[w];
                if (!wh || !wh.items) continue;
                for (var it = 0; it < wh.items.length; it++) {
                    var si = wh.items[it];
                    if (!si.name) continue;
                    if (!SlangTerms.hasMatch(si.name, q)) continue;

                    if (!aggregated[si.name]) {
                        aggregated[si.name] = {
                            name: si.name,
                            icon: si.icon || "",
                            totalQty: 0,
                            sources: []
                        };
                    }
                    aggregated[si.name].totalQty += (si.quantity || 0);
                    aggregated[si.name].sources.push({
                        mapItem: item,
                        warehouseName: wh.warehouse_name || item.name,
                        qty: si.quantity || 0
                    });
                    // keep best icon
                    if (!aggregated[si.name].icon && si.icon) {
                        aggregated[si.name].icon = si.icon;
                    }
                }
            }
        }

        var results = [];
        for (var key in aggregated) results.push(aggregated[key]);
        results.sort(function(a, b) { return a.name.localeCompare(b.name); });
        if (results.length > 30) results = results.slice(0, 30);
        return results;
    }

    // ── Helper: calculate logistics routes ─────────────────────
    function _calculateRoutes() {
        if (!_selectedDestination || _selectedItems.length === 0) return;
        var dest = _selectedDestination;
        var generatedRoutes = [];

        console.log("[Logistics] Calculating routes for destination:", dest.name);

        for (var r = 0; r < _selectedItems.length; r++) {
            var req = _selectedItems[r];
            var needed = parseInt(req.qty);
            if (isNaN(needed) || needed <= 0) continue;

            // Find sources for this item across all depots (not dest)
            var sources = [];
            if (!mapItems) continue;
            for (var i = 0; i < mapItems.length; i++) {
                var item = mapItems[i];
                if (item.name === dest.name || !item.stock) continue;

                var totalQty = 0;
                for (var w = 0; w < item.stock.length; w++) {
                    var wh = item.stock[w];
                    if (!wh || !wh.items) continue;
                    for (var it = 0; it < wh.items.length; it++) {
                        if (wh.items[it].name === req.name) {
                            totalQty += (wh.items[it].quantity || 0);
                        }
                    }
                }

                if (totalQty > 0) {
                    var dx = (item.x || 0) - (dest.x || 0);
                    var dy = (item.y || 0) - (dest.y || 0);
                    var dist = Math.sqrt(dx * dx + dy * dy);
                    sources.push({ mapItem: item, qty: totalQty, dist: dist });
                }
            }

            // Sort by distance (closest first)
            sources.sort(function(a, b) { return a.dist - b.dist; });

            // Allocate from closest sources
            for (var s = 0; s < sources.length && needed > 0; s++) {
                var src = sources[s];
                var take = Math.min(needed, src.qty);
                needed -= take;

                // Merge into existing route from same source
                var existingRoute = null;
                for (var g = 0; g < generatedRoutes.length; g++) {
                    if (generatedRoutes[g].start.name === src.mapItem.name) {
                        existingRoute = generatedRoutes[g];
                        break;
                    }
                }

                if (existingRoute) {
                    existingRoute.cargo.push({ name: req.name, qty: take, icon: req.icon || "" });
                } else {
                    generatedRoutes.push({
                        start: src.mapItem,
                        end: dest,
                        cargo: [{ name: req.name, qty: take, icon: req.icon || "" }]
                    });
                }
            }
        }

        console.log("[Logistics] Calculated", generatedRoutes.length, "routes!");
        routesCalculated(generatedRoutes);
        close();
    }

    // ── Animations ──────────────────────────────────────────────
    NumberAnimation {
        id: openAnim
        target: modalCard
        property: "opacity"
        from: 0; to: 1; duration: 200
        easing.type: Easing.OutCubic
    }
    NumberAnimation {
        id: openScale
        target: modalCard
        property: "scale"
        from: 0.95; to: 1.0; duration: 250
        easing.type: Easing.OutCubic
    }

    // ── Backdrop ────────────────────────────────────────────────
    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.6

        MouseArea {
            anchors.fill: parent
            onClicked: logisticsModal.close()
        }
    }

    // ── Modal Card ──────────────────────────────────────────────
    Rectangle {
        id: modalCard
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.8, 900)
        height: Math.min(parent.height * 0.8, 700)
        radius: 16
        color: settingsController.surfaceColor
        border.color: settingsController.borderColor
        border.width: 1
        clip: true

        Component.onCompleted: { openAnim.start(); openScale.start(); }

        MultiEffect {
            source: modalCard
            anchors.fill: modalCard
            shadowEnabled: true
            shadowOpacity: 0.5
            shadowBlur: 1.0
            shadowVerticalOffset: 8
            shadowColor: "black"
        }

        // Prevent clicks from propagating through
        MouseArea { anchors.fill: parent }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 0
            spacing: 0

            // ════════════ HEADER ════════════
            Rectangle {
                Layout.fillWidth: true
                height: 60
                color: "transparent"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 24
                    anchors.rightMargin: 16
                    spacing: 12

                    // Back button (steps 2 & 3)
                    Rectangle {
                        width: 32; height: 32; radius: 16
                        color: backMa.containsMouse ? settingsController.controlHoverColor : settingsController.controlColor
                        visible: logisticsModal._step > 1

                        Text {
                            anchors.centerIn: parent
                            text: "←"
                            color: settingsController.textColor
                            font.pixelSize: 16; font.bold: true
                        }
                        MouseArea {
                            id: backMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: logisticsModal._step = logisticsModal._step - 1
                        }
                    }

                    // Title
                    Text {
                        text: {
                            if (logisticsModal._step === 1) return "🚚 " + logisticsModal.tr("logistics.step1", "Selecionar Destino");
                            if (logisticsModal._step === 2) return "📦 " + logisticsModal.tr("logistics.step2", "Buscar e Selecionar Itens");
                            return "📋 " + logisticsModal.tr("logistics.step3", "Revisar e Calcular Rotas");
                        }
                        color: settingsController.textColor
                        font.family: "Segoe UI"
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    // Step indicator
                    Row {
                        spacing: 6
                        Repeater {
                            model: 3
                            delegate: Rectangle {
                                width: index + 1 === logisticsModal._step ? 24 : 8
                                height: 8
                                radius: 4
                                color: index + 1 <= logisticsModal._step ? settingsController.accentColor : settingsController.borderColor
                                Behavior on width { NumberAnimation { duration: 200 } }
                                Behavior on color { ColorAnimation { duration: 200 } }
                            }
                        }
                    }

                    // Close button
                    Rectangle {
                        width: 32; height: 32; radius: 16
                        color: closeMa.containsMouse ? settingsController.dangerColor : settingsController.controlColor

                        Text {
                            anchors.centerIn: parent
                            text: "✕"
                            color: closeMa.containsMouse ? "white" : settingsController.textColor
                            font.pixelSize: 14; font.bold: true
                        }
                        MouseArea {
                            id: closeMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: logisticsModal.close()
                        }
                    }
                }

                // Separator
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width; height: 1
                    color: settingsController.borderColor
                }
            }

            // ════════════ CONTENT AREA ════════════
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                // ───── STEP 1: Select destination ─────
                Item {
                    anchors.fill: parent
                    visible: logisticsModal._step === 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 12

                        // Subtitle
                        Text {
                            text: logisticsModal.tr("logistics.step1_desc", "Escolha o depósito que receberá os itens:")
                            color: settingsController.secondaryTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                        }

                        // Search field
                        TextField {
                            id: depotSearchField
                            Layout.fillWidth: true
                            height: 40
                            placeholderText: logisticsModal.tr("logistics.search_depot", "🔍 Buscar depósito por nome...")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 14
                            selectedTextColor: settingsController.backgroundColor
                            selectionColor: settingsController.accentColor
                            selectByMouse: true
                            background: Rectangle {
                                color: settingsController.backgroundColor
                                radius: 8
                                border.width: 1
                                border.color: depotSearchField.activeFocus ? settingsController.accentColor : settingsController.borderColor
                            }
                            onTextChanged: logisticsModal._depotSearch = text
                        }

                        // Depot list
                        ListView {
                            id: depotList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 6

                            model: {
                                var depots = logisticsModal._getDepots();
                                if (logisticsModal._depotSearch) {
                                    var q = logisticsModal._depotSearch.toLowerCase();
                                    depots = depots.filter(function(d) {
                                        return d.name.toLowerCase().indexOf(q) >= 0 ||
                                               d.warehouseNames.join(" ").toLowerCase().indexOf(q) >= 0;
                                    });
                                }
                                return depots;
                            }

                            delegate: Rectangle {
                                width: depotList.width
                                height: 64
                                radius: 10
                                color: depotItemMa.containsMouse ? Qt.rgba(
                                    Qt.color(settingsController.accentColor).r,
                                    Qt.color(settingsController.accentColor).g,
                                    Qt.color(settingsController.accentColor).b, 0.15
                                ) : settingsController.backgroundColor
                                border.color: depotItemMa.containsMouse ? settingsController.accentColor : settingsController.borderColor
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 12

                                    // Depot icon
                                    Rectangle {
                                        width: 40; height: 40; radius: 20
                                        color: settingsController.accentColor
                                        opacity: 0.2

                                        Text {
                                            anchors.centerIn: parent
                                            text: "📦"
                                            font.pixelSize: 20
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        Text {
                                            text: modelData.name
                                            color: settingsController.textColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 14
                                            font.bold: true
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                        Text {
                                            text: modelData.warehouseNames.join(", ")
                                            color: settingsController.mutedTextColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                    }

                                    // Item count badge
                                    Rectangle {
                                        width: countText.implicitWidth + 16
                                        height: 28
                                        radius: 14
                                        color: settingsController.accentColor

                                        Text {
                                            id: countText
                                            anchors.centerIn: parent
                                            text: modelData.itemCount + " itens"
                                            color: "white"
                                            font.family: "Segoe UI"
                                            font.pixelSize: 12
                                            font.bold: true
                                        }
                                    }
                                }

                                MouseArea {
                                    id: depotItemMa
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        logisticsModal._selectedDestination = modelData.mapItem;
                                        logisticsModal._step = 2;
                                        itemSearchField.forceActiveFocus();
                                    }
                                }
                            }

                            // Empty state
                            Text {
                                anchors.centerIn: parent
                                visible: depotList.count === 0
                                text: logisticsModal.tr("logistics.no_depots", "Nenhum depósito com estoque encontrado.\nAguarde os dados serem carregados.")
                                color: settingsController.mutedTextColor
                                font.family: "Segoe UI"
                                font.pixelSize: 14
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }

                // ───── STEP 2: Search & select items ─────
                Item {
                    anchors.fill: parent
                    visible: logisticsModal._step === 2

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 12

                        // Destination info
                        Rectangle {
                            Layout.fillWidth: true
                            height: 40
                            radius: 8
                            color: Qt.rgba(
                                Qt.color(settingsController.accentColor).r,
                                Qt.color(settingsController.accentColor).g,
                                Qt.color(settingsController.accentColor).b, 0.1
                            )

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 8

                                Text {
                                    text: "🎯"
                                    font.pixelSize: 16
                                }
                                Text {
                                    text: logisticsModal.tr("logistics.destination", "Destino") + ": "
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                }
                                Text {
                                    text: logisticsModal._selectedDestination ? logisticsModal._selectedDestination.name : ""
                                    color: settingsController.accentColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 13
                                    font.bold: true
                                    Layout.fillWidth: true
                                }
                            }
                        }

                        // Search field
                        TextField {
                            id: itemSearchField
                            Layout.fillWidth: true
                            height: 40
                            placeholderText: logisticsModal.tr("logistics.search_item", "🔍 Buscar item em todos os estoques...")
                            color: settingsController.textColor
                            font.family: "Segoe UI"
                            font.pixelSize: 14
                            selectedTextColor: settingsController.backgroundColor
                            selectionColor: settingsController.accentColor
                            selectByMouse: true
                            background: Rectangle {
                                color: settingsController.backgroundColor
                                radius: 8
                                border.width: 1
                                border.color: itemSearchField.activeFocus ? settingsController.accentColor : settingsController.borderColor
                            }
                            onTextChanged: {
                                logisticsModal._itemSearch = text;
                                logisticsModal._searchResults = logisticsModal._searchAllItems(text);
                            }
                        }

                        // Two columns layout
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 16

                            // LEFT: Search results
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.preferredWidth: 1
                                spacing: 6

                                Text {
                                    text: logisticsModal.tr("logistics.available", "Disponíveis")
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                    font.bold: true
                                    font.capitalization: Font.AllUppercase
                                }

                                ListView {
                                    id: searchResultsList
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    spacing: 4

                                    model: logisticsModal._searchResults

                                    delegate: Rectangle {
                                        width: searchResultsList.width
                                        height: 52
                                        radius: 8
                                        color: searchResultMa.containsMouse ? settingsController.controlHoverColor : settingsController.backgroundColor
                                        border.color: settingsController.borderColor
                                        border.width: 1

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 8
                                            spacing: 8

                                            // Item icon
                                            Rectangle {
                                                width: 36; height: 36; radius: 4
                                                color: settingsController.controlColor

                                                Image {
                                                    anchors.fill: parent
                                                    anchors.margins: 4
                                                    source: modelData.icon || ""
                                                    fillMode: Image.PreserveAspectFit
                                                    visible: modelData.icon !== ""
                                                }
                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "📦"
                                                    font.pixelSize: 16
                                                    visible: !modelData.icon
                                                }
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 1

                                                Text {
                                                    text: modelData.name
                                                    color: settingsController.textColor
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 12
                                                    font.bold: true
                                                    elide: Text.ElideRight
                                                    Layout.fillWidth: true
                                                }
                                                Text {
                                                    text: logisticsModal.tr("logistics.total_available", "Total") + ": " + modelData.totalQty + " (" + modelData.sources.length + " " + logisticsModal.tr("logistics.sources", "fontes") + ")"
                                                    color: settingsController.mutedTextColor
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 10
                                                }
                                            }

                                            // Quantity input
                                            TextField {
                                                id: qtyInput
                                                Layout.preferredWidth: 60
                                                height: 32
                                                placeholderText: "Qtd"
                                                validator: IntValidator { bottom: 1; top: 99999 }
                                                color: settingsController.textColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 13
                                                horizontalAlignment: Text.AlignHCenter
                                                selectByMouse: true
                                                background: Rectangle {
                                                    color: settingsController.backgroundColor
                                                    radius: 6
                                                    border.width: 1
                                                    border.color: qtyInput.activeFocus ? settingsController.accentColor : settingsController.borderColor
                                                }
                                            }

                                            // Add button
                                            Rectangle {
                                                width: 32; height: 32; radius: 6
                                                color: addMa.containsMouse ? settingsController.accentHoverColor : settingsController.accentColor

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "+"
                                                    color: "white"
                                                    font.pixelSize: 18
                                                    font.bold: true
                                                }
                                                MouseArea {
                                                    id: addMa
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        var qtyText = qtyInput.text;
                                                        var qty = parseInt(qtyText);
                                                        if (isNaN(qty) || qty <= 0) qty = 1;

                                                        // Check if already in list, merge
                                                        var items = logisticsModal._selectedItems.slice();
                                                        var found = false;
                                                        for (var i = 0; i < items.length; i++) {
                                                            if (items[i].name === modelData.name) {
                                                                items[i].qty += qty;
                                                                found = true;
                                                                break;
                                                            }
                                                        }
                                                        if (!found) {
                                                            items.push({
                                                                name: modelData.name,
                                                                icon: modelData.icon || "",
                                                                qty: qty,
                                                                maxQty: modelData.totalQty
                                                            });
                                                        }
                                                        logisticsModal._selectedItems = items;
                                                        qtyInput.text = "";
                                                    }
                                                }
                                            }
                                        }

                                        MouseArea {
                                            id: searchResultMa
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            // don't block children (input/button)
                                            propagateComposedEvents: true
                                            acceptedButtons: Qt.NoButton
                                        }
                                    }

                                    // Empty state
                                    Text {
                                        anchors.centerIn: parent
                                        visible: searchResultsList.count === 0
                                        text: logisticsModal._itemSearch.length < 2
                                              ? logisticsModal.tr("logistics.type_to_search", "Digite para buscar itens...")
                                              : logisticsModal.tr("logistics.no_results", "Nenhum item encontrado")
                                        color: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        horizontalAlignment: Text.AlignHCenter
                                    }
                                }
                            }

                            // Vertical separator
                            Rectangle {
                                Layout.fillHeight: true
                                width: 1
                                color: settingsController.borderColor
                            }

                            // RIGHT: Selected items
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.preferredWidth: 1
                                spacing: 6

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        text: logisticsModal.tr("logistics.selected", "Selecionados")
                                        color: settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        font.bold: true
                                        font.capitalization: Font.AllUppercase
                                        Layout.fillWidth: true
                                    }
                                    Rectangle {
                                        width: selCountText.implicitWidth + 12
                                        height: 20
                                        radius: 10
                                        color: settingsController.accentColor
                                        visible: logisticsModal._selectedItems.length > 0

                                        Text {
                                            id: selCountText
                                            anchors.centerIn: parent
                                            text: logisticsModal._selectedItems.length
                                            color: "white"
                                            font.family: "Segoe UI"
                                            font.pixelSize: 10
                                            font.bold: true
                                        }
                                    }
                                }

                                ListView {
                                    id: selectedItemsList
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    spacing: 4

                                    model: logisticsModal._selectedItems

                                    delegate: Rectangle {
                                        width: selectedItemsList.width
                                        height: 44
                                        radius: 8
                                        color: settingsController.backgroundColor
                                        border.color: settingsController.borderColor
                                        border.width: 1

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 8
                                            spacing: 8

                                            // Item icon
                                            Rectangle {
                                                width: 28; height: 28; radius: 4
                                                color: settingsController.controlColor

                                                Image {
                                                    anchors.fill: parent
                                                    anchors.margins: 3
                                                    source: modelData.icon || ""
                                                    fillMode: Image.PreserveAspectFit
                                                    visible: source !== ""
                                                }
                                            }

                                            Text {
                                                text: modelData.name
                                                color: settingsController.textColor
                                                font.family: "Segoe UI"
                                                font.pixelSize: 12
                                                elide: Text.ElideRight
                                                Layout.fillWidth: true
                                            }

                                            // Qty badge
                                            Rectangle {
                                                width: qtyBadgeText.implicitWidth + 12
                                                height: 24
                                                radius: 4
                                                color: settingsController.accentColor

                                                Text {
                                                    id: qtyBadgeText
                                                    anchors.centerIn: parent
                                                    text: "×" + modelData.qty
                                                    color: "white"
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 12
                                                    font.bold: true
                                                }
                                            }

                                            // Remove button
                                            Rectangle {
                                                width: 24; height: 24; radius: 12
                                                color: removeMa.containsMouse ? settingsController.dangerColor : settingsController.controlColor

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "✕"
                                                    color: removeMa.containsMouse ? "white" : settingsController.mutedTextColor
                                                    font.pixelSize: 10
                                                    font.bold: true
                                                }
                                                MouseArea {
                                                    id: removeMa
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        var items = logisticsModal._selectedItems.slice();
                                                        items.splice(index, 1);
                                                        logisticsModal._selectedItems = items;
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    // Empty state
                                    ColumnLayout {
                                        anchors.centerIn: parent
                                        visible: selectedItemsList.count === 0
                                        spacing: 8

                                        Text {
                                            text: "📋"
                                            font.pixelSize: 32
                                            Layout.alignment: Qt.AlignHCenter
                                        }
                                        Text {
                                            text: logisticsModal.tr("logistics.no_items", "Nenhum item selecionado.\nBusque e adicione itens à lista.")
                                            color: settingsController.mutedTextColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 13
                                            horizontalAlignment: Text.AlignHCenter
                                        }
                                    }
                                }

                                // Next button
                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 42
                                    radius: 8
                                    color: logisticsModal._selectedItems.length > 0
                                           ? (nextStepMa.containsMouse ? settingsController.accentHoverColor : settingsController.accentColor)
                                           : settingsController.controlColor
                                    opacity: logisticsModal._selectedItems.length > 0 ? 1.0 : 0.5

                                    Text {
                                        anchors.centerIn: parent
                                        text: logisticsModal.tr("logistics.next_step", "Próximo → Revisar e Calcular")
                                        color: logisticsModal._selectedItems.length > 0 ? "white" : settingsController.mutedTextColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 14
                                        font.bold: true
                                    }
                                    MouseArea {
                                        id: nextStepMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: logisticsModal._selectedItems.length > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                                        onClicked: {
                                            if (logisticsModal._selectedItems.length > 0)
                                                logisticsModal._step = 3;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ───── STEP 3: Review & calculate ─────
                Item {
                    anchors.fill: parent
                    visible: logisticsModal._step === 3

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 16

                        // Destination info
                        Rectangle {
                            Layout.fillWidth: true
                            height: 48
                            radius: 8
                            color: Qt.rgba(
                                Qt.color(settingsController.accentColor).r,
                                Qt.color(settingsController.accentColor).g,
                                Qt.color(settingsController.accentColor).b, 0.1
                            )

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10

                                Text { text: "🎯"; font.pixelSize: 20 }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1
                                    Text {
                                        text: logisticsModal.tr("logistics.destination", "Destino")
                                        color: settingsController.mutedTextColor
                                        font.family: "Segoe UI"; font.pixelSize: 10
                                    }
                                    Text {
                                        text: logisticsModal._selectedDestination ? logisticsModal._selectedDestination.name : ""
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"; font.pixelSize: 14; font.bold: true
                                    }
                                }
                            }
                        }

                        // Summary header
                        Text {
                            text: logisticsModal.tr("logistics.review_summary", "Resumo dos itens a transportar:")
                            color: settingsController.secondaryTextColor
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                        }

                        // Items summary
                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 4

                            model: logisticsModal._selectedItems

                            delegate: Rectangle {
                                width: parent ? parent.width : 0
                                height: 48
                                radius: 8
                                color: settingsController.backgroundColor
                                border.color: settingsController.borderColor
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 10

                                    Rectangle {
                                        width: 32; height: 32; radius: 4
                                        color: settingsController.controlColor

                                        Image {
                                            anchors.fill: parent
                                            anchors.margins: 4
                                            source: modelData.icon || ""
                                            fillMode: Image.PreserveAspectFit
                                            visible: source !== ""
                                        }
                                    }

                                    Text {
                                        text: modelData.name
                                        color: settingsController.textColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 13
                                        Layout.fillWidth: true
                                    }

                                    Text {
                                        text: "×" + modelData.qty
                                        color: settingsController.accentColor
                                        font.family: "Segoe UI"
                                        font.pixelSize: 15
                                        font.bold: true
                                    }
                                }
                            }
                        }

                        // Vehicle cost preview
                        Rectangle {
                            Layout.fillWidth: true
                            height: vehicleCostCol.implicitHeight + 24
                            radius: 8
                            color: settingsController.backgroundColor
                            border.color: settingsController.borderColor
                            border.width: 1

                            ColumnLayout {
                                id: vehicleCostCol
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8

                                Text {
                                    text: "🚛 " + logisticsModal.tr("logistics.estimated_vehicles", "Estimativa de Veículos (total)")
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 13
                                    font.bold: true
                                }

                                property int totalCrates: {
                                    var t = 0;
                                    for (var i = 0; i < logisticsModal._selectedItems.length; i++)
                                        t += logisticsModal._selectedItems[i].qty;
                                    return t;
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 20

                                    // Dunne
                                    RowLayout {
                                        spacing: 6
                                        Rectangle {
                                            width: 8; height: 8; radius: 4; color: "#3b82f6"
                                        }
                                        Text {
                                            text: "Dunne (15): " + Math.ceil(vehicleCostCol.totalCrates / 15) + " viagens"
                                            color: settingsController.textColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 12
                                        }
                                    }
                                    // Flatbed
                                    RowLayout {
                                        spacing: 6
                                        Rectangle {
                                            width: 8; height: 8; radius: 4; color: "#22c55e"
                                        }
                                        Text {
                                            text: "Flatbed (60): " + Math.ceil(vehicleCostCol.totalCrates / 60) + " viagens"
                                            color: settingsController.textColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 12
                                        }
                                    }
                                    // Ironship
                                    RowLayout {
                                        spacing: 6
                                        Rectangle {
                                            width: 8; height: 8; radius: 4; color: "#eab308"
                                        }
                                        Text {
                                            text: "Ironship (300): " + Math.ceil(vehicleCostCol.totalCrates / 300) + " viagens"
                                            color: settingsController.textColor
                                            font.family: "Segoe UI"
                                            font.pixelSize: 12
                                        }
                                    }
                                }
                            }
                        }

                        // Calculate button
                        Rectangle {
                            Layout.fillWidth: true
                            height: 48
                            radius: 10
                            color: calcMa.containsMouse ? settingsController.accentHoverColor : settingsController.accentColor

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 8

                                Text {
                                    text: "🗺️"
                                    font.pixelSize: 18
                                }
                                Text {
                                    text: logisticsModal.tr("logistics.calculate", "Calcular Rotas e Mostrar no Mapa")
                                    color: "white"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 15
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                id: calcMa
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: logisticsModal._calculateRoutes()
                            }
                        }
                    }
                }
            }
        }
    }
}
