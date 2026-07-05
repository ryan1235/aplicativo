import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import "SlangTerms.js" as SlangTerms

Item {
    id: root
    clip: true

    property string baseUrl: typeof mapController !== "undefined" && mapController ? mapController.baseUrl : "https://foxlogi.com/map-tiles/patch-64/{z}/{x}/{y}.webp"
    property string fallbackUrl: typeof mapController !== "undefined" && mapController ? mapController.fallbackUrl : "https://foxlogi.com/map-tiles/patch-64/{z}/{x}/{y}.webp"
    property int tileSize: 256
    property int minZoom: 2
    property int maxZoom: 7
    property int currentZoom: 2

    // The center of the view in map pixels at the current zoom level
    property real centerX: (Math.pow(2, currentZoom) * tileSize) / 2
    property real centerY: (Math.pow(2, currentZoom) * tileSize) / 2
    
    function tr(key, fallback) {
        if (typeof i18nController !== "undefined") {
            i18nController.revision;
            var t = i18nController.t(key);
            if (t !== key) return t;
        }
        return fallback;
    }
    
    // Map Filters
    property bool showHexNames: true
    property bool showMajorCities: false
    property bool showMinorCities: false
    property bool showResources: false
    property bool showIcons: false
    property bool showStockFilter: true
    
    // Culling system to prevent rendering items outside the screen
    signal updateCulling()
    
    // --- DRAWING SYSTEM PROPERTIES ---
    property string activeTool: "pan" // "pan", "brush", "arrow", "polygon", "eraser"
    property string activeColor: "#ef4444" // default red
    property int activeThickness: 3
    property bool showToolSettings: false
    property var drawings: [] // stores objects like {type: "brush", color: "red", thickness: 3, points: [{x,y}...]}
    property var currentDrawing: null // currently active drawing while mouse is pressed
    property bool polygonNameDialogVisible: false
    
    // --- LOGISTICS PROPERTIES ---
    property bool logisticsModalVisible: false
    property var logisticsRoutes: [] // Generated routes
    property var logisticsHoveredRoute: null

    function distanceToSegment(px, py, vx, vy, wx, wy) {
        var l2 = Math.pow(vx - wx, 2) + Math.pow(vy - wy, 2);
        if (l2 === 0) return Math.sqrt(Math.pow(px - vx, 2) + Math.pow(py - vy, 2));
        var t = ((px - vx) * (wx - vx) + (py - vy) * (wy - vy)) / l2;
        t = Math.max(0, Math.min(1, t));
        return Math.sqrt(Math.pow(px - (vx + t * (wx - vx)), 2) + Math.pow(py - (vy + t * (wy - vy)), 2));
    }

    function isPointInPolygon(px, py, points) {
        var isInside = false;
        for (var i = 0, j = points.length - 1; i < points.length; j = i++) {
            var xi = points[i].x, yi = points[i].y;
            var xj = points[j].x, yj = points[j].y;
            
            var intersect = ((yi > py) !== (yj > py))
                && (px < (xj - xi) * (py - yi) / (yj - yi) + xi);
            if (intersect) isInside = !isInside;
        }
        return isInside;
    }

    function screenToWorld(sx, sy) {
        var mapX = sx - (root.width / 2) + root.centerX;
        var mapY = sy - (root.height / 2) + root.centerY;
        var zoomFactor = Math.pow(2, root.currentZoom);
        return {x: mapX / zoomFactor, y: mapY / zoomFactor};
    }

    function worldToCanvas(wx, wy) {
        var zoomFactor = Math.pow(2, drawingCanvas.lastPaintZoom);
        var mapX = wx * zoomFactor;
        var mapY = wy * zoomFactor;
        var sx = mapX + (root.width / 2) - drawingCanvas.lastPaintCenterX;
        var sy = mapY + (root.height / 2) - drawingCanvas.lastPaintCenterY;
        return {x: sx, y: sy};
    }

    function drawArrow(ctx, fromx, fromy, tox, toy, headlen) {
        var angle = Math.atan2(toy - fromy, tox - fromx);
        ctx.beginPath();
        ctx.moveTo(fromx, fromy);
        ctx.lineTo(tox, toy);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(tox, toy);
        ctx.lineTo(tox - headlen * Math.cos(angle - Math.PI / 6), toy - headlen * Math.sin(angle - Math.PI / 6));
        ctx.lineTo(tox - headlen * Math.cos(angle + Math.PI / 6), toy - headlen * Math.sin(angle + Math.PI / 6));
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
    }
    // ---------------------------------
    
    Timer {
        id: cullingTimer
        interval: 100
        repeat: false
        onTriggered: {
            root.updateCulling();
            drawingCanvas.requestPaint();
        }
    }
    
    onCenterXChanged: cullingTimer.restart()
    onCenterYChanged: cullingTimer.restart()
    
    // Global tooltip to avoid instantiating 3000+ ToolTip objects which causes massive lag
    Rectangle {
        id: globalToolTip
        z: 1000
        visible: false
        color: "#ffffff"
        border.color: "#333333"
        border.width: 1
        radius: 4
        width: tooltipText.implicitWidth + 16
        height: tooltipText.implicitHeight + 10
        
        property alias text: tooltipText.text
        
        Text {
            id: tooltipText
            anchors.centerIn: parent
            color: "#111111"
            font.pixelSize: 12
        }
    }


    property int activeLayerIndex: 0
    property bool activeLayerLoaded: (activeLayerIndex === 0) ? layerA.isLoaded : layerB.isLoaded
    
    onCurrentZoomChanged: {
        if (typeof cullingTimer !== "undefined") cullingTimer.restart();
        var activeLayer = (activeLayerIndex === 0) ? layerA : layerB;
        activeLayer.layerZoom = root.currentZoom;
    }
    
    Component.onCompleted: {
        layerA.freezeCenter = false;
        layerB.freezeCenter = true;
        layerA.layerZoom = root.currentZoom;
        if (typeof mapController !== "undefined" && mapController) {
            mapController.fetchStockData();
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: false
        onTriggered: {
            console.log("--- MAP DIAGNOSTICS ---");
            console.log("Root Size:", root.width, "x", root.height);
            console.log("BaseUrl:", root.baseUrl);
            console.log("LayerA ViewSize:", layerA.viewWidth, "x", layerA.viewHeight);
            console.log("LayerA pos:", layerA.x, layerA.y);
            console.log("LayerA center:", layerA.centerX, layerA.centerY);
            console.log("LayerA Zoom:", layerA.layerZoom, "Scale:", layerA.scale);
            console.log("LayerA poolCount:", layerA.poolCount);
            console.log("LayerA visible:", layerA.visible, "z:", layerA.z);
            console.log("-----------------------");
        }
    }

    TileLayer {
        id: layerA
        baseUrl: root.baseUrl
        fallbackUrl: root.fallbackUrl
        tileSize: root.tileSize
        z: root.activeLayerIndex === 0 ? 1 : 0
        isBackground: root.activeLayerIndex !== 0
        hideTiles: isBackground && root.activeLayerLoaded
        freezeCenter: false
        
        viewWidth: root.width
        viewHeight: root.height
        
        centerX: root.centerX * Math.pow(2, layerA.layerZoom - root.currentZoom)
        centerY: root.centerY * Math.pow(2, layerA.layerZoom - root.currentZoom)
        
        transform: Scale {
            origin.x: layerA.viewWidth / 2 - layerA.x
            origin.y: layerA.viewHeight / 2 - layerA.y
            xScale: Math.pow(2, root.currentZoom - layerA.layerZoom)
            yScale: Math.pow(2, root.currentZoom - layerA.layerZoom)
        }
    }

    TileLayer {
        id: layerB
        baseUrl: root.baseUrl
        fallbackUrl: root.fallbackUrl
        tileSize: root.tileSize
        z: root.activeLayerIndex === 1 ? 1 : 0
        isBackground: root.activeLayerIndex !== 1
        hideTiles: isBackground && root.activeLayerLoaded
        freezeCenter: true
        
        viewWidth: root.width
        viewHeight: root.height
        
        centerX: root.centerX * Math.pow(2, layerB.layerZoom - root.currentZoom)
        centerY: root.centerY * Math.pow(2, layerB.layerZoom - root.currentZoom)
        
        transform: Scale {
            origin.x: layerB.viewWidth / 2 - layerB.x
            origin.y: layerB.viewHeight / 2 - layerB.y
            xScale: Math.pow(2, root.currentZoom - layerB.layerZoom)
            yScale: Math.pow(2, root.currentZoom - layerB.layerZoom)
        }
    }

    // Overlay Manager Container
    Item {
        id: overlayManager
        x: (root.width / 2) - root.centerX
        y: (root.height / 2) - root.centerY
        width: Math.pow(2, root.currentZoom) * root.tileSize
        height: Math.pow(2, root.currentZoom) * root.tileSize
        z: 2 // Always on top of map layers
        
        Repeater {
            model: typeof mapController !== "undefined" && mapController ? mapController.testItemsModel : []
            
            delegate: Item {
                property real zoomFactor: Math.pow(2, root.currentZoom)
                
                property real worldPxX: ((modelData.x * mapController.mapScale) + mapController.mapOffsetX) * zoomFactor
                property real worldPxY: ((-modelData.y * mapController.mapScale) + mapController.mapOffsetY) * zoomFactor
                
                x: worldPxX - width / 2
                y: worldPxY - height / 2
                width: 30
                height: 30
                
                // Visibility logic based only on zoom (culling is handled by root's clip: true natively)
                visible: true
                
                Canvas {
                    anchors.fill: parent
                    onPaint: {
                        var ctx = getContext("2d");
                        ctx.reset();
                        ctx.beginPath();
                        ctx.moveTo(width / 2, 2);
                        ctx.lineTo(width - 2, height - 2);
                        ctx.lineTo(2, height - 2);
                        ctx.closePath();
                        ctx.fillStyle = "#fbbf24"; // yellow-400
                        ctx.fill();
                        ctx.strokeStyle = "#b45309"; // amber-700
                        ctx.lineWidth = 2;
                        ctx.stroke();
                    }
                }
                
                HoverHandler {
                    id: hoverHandler
                    onHoveredChanged: {
                        if (hovered) {
                            // In Qt6 Pointer Handlers, point.position gives the hover point in local coordinates
                            var p = mapToItem(root, hoverHandler.point.position.x, hoverHandler.point.position.y);
                            globalToolTip.x = p.x + 15;
                            globalToolTip.y = p.y + 15;
                            globalToolTip.text = modelData.name + "\n\n" + (modelData.items ? modelData.items.join("\n") : "Empty");
                            globalToolTip.visible = true;
                            parent.scale = 1.2;
                        } else {
                            globalToolTip.visible = false;
                            parent.scale = 1.0;
                        }
                    }
                }
                
                TapHandler {
                    onTapped: {
                        console.log("Clicked:", modelData.name);
                    }
                }
            }
        }

        Repeater {
            model: typeof mapController !== "undefined" && mapController ? mapController.mapTextItemsModel : []
            
            delegate: Item {
                property real zoomFactor: Math.pow(2, root.currentZoom)
                
                property real worldPxX: ((modelData.x * mapController.mapScale) + mapController.mapOffsetX) * zoomFactor
                property real worldPxY: ((-modelData.y * mapController.mapScale) + mapController.mapOffsetY) * zoomFactor
                
                x: worldPxX - width / 2
                y: worldPxY - height / 2
                
                width: itemLoader.item ? itemLoader.item.implicitWidth : 0
                height: itemLoader.item ? itemLoader.item.implicitHeight : 0
                
                property bool inBounds: true
                
                function checkBounds() {
                    var screenX = worldPxX + (root.width / 2) - root.centerX;
                    var screenY = worldPxY + (root.height / 2) - root.centerY;
                    inBounds = (screenX >= -200 && screenX <= root.width + 200 &&
                                screenY >= -200 && screenY <= root.height + 200);
                }
                
                Connections {
                    target: root
                    function onUpdateCulling() { checkBounds(); }
                }
                
                Component.onCompleted: checkBounds()
                
                property bool shouldShow: {
                    if (!inBounds) return false;
                    
                    if (modelData.mapMarkerType === "Hex") return root.showHexNames && root.currentZoom >= 0;
                    if (modelData.mapMarkerType === "Major") return root.showMajorCities && root.currentZoom >= 4;
                    if (modelData.mapMarkerType === "Minor") return root.showMinorCities && root.currentZoom >= 5;
                    return true;
                }
                
                visible: shouldShow
                
                property bool isMajor: modelData.mapMarkerType === "Major"
                property bool isHex: modelData.mapMarkerType === "Hex"
                
                Loader {
                    id: itemLoader
                    active: shouldShow
                    sourceComponent: Text {
                        text: modelData.text || ""
                        
                        // Hex is white with black outline. Major is white. Minor is light grey.
                        color: isHex ? "#ffffff" : (isMajor ? "#ffffff" : "#dddddd")
                        
                        font.pixelSize: {
                            if (isHex) return root.currentZoom <= 2 ? 11 : (root.currentZoom >= 5 ? 36 : 18);
                            if (isMajor) return root.currentZoom >= 6 ? 22 : 14;
                            return root.currentZoom >= 6 ? 15 : 10;
                        }
                        font.bold: isHex || isMajor
                        font.family: "Segoe UI"
                        font.capitalization: Font.AllUppercase
                        font.letterSpacing: 0
                        
                        opacity: isHex ? 0.75 : (isMajor ? 1.0 : (root.currentZoom >= 5 ? 0.9 : 0.6))
                        
                        style: Text.Outline
                        styleColor: isHex ? "#cc000000" : "#e6000000"
                    }
                }
            }
        }
        Repeater {
            model: typeof mapController !== "undefined" && mapController ? mapController.mapItemsModel : []
            
            delegate: Item {
                property real zoomFactor: Math.pow(2, root.currentZoom)
                
                property real worldPxX: ((modelData.x * mapController.mapScale) + mapController.mapOffsetX) * zoomFactor
                property real worldPxY: ((-modelData.y * mapController.mapScale) + mapController.mapOffsetY) * zoomFactor
                
                x: worldPxX - width / 2
                y: worldPxY - height / 2
                
                property bool inBounds: true
                
                function checkBounds() {
                    var screenX = worldPxX + (root.width / 2) - root.centerX;
                    var screenY = worldPxY + (root.height / 2) - root.centerY;
                    inBounds = (screenX >= -100 && screenX <= root.width + 100 &&
                                screenY >= -100 && screenY <= root.height + 100);
                }
                
                Connections {
                    target: root
                    function onUpdateCulling() { checkBounds(); }
                }
                
                Component.onCompleted: checkBounds()
                
                property bool isResource: {
                    var t = Number(modelData.iconType);
                    // Fields: 20(Salvage), 21(Component), 22(Fuel), 23(Sulfur), 61(Coal), 62(Oil)
                    // Mines: 32(Sulfur), 38(Component), 40(Salvage)
                    return t === 20 || t === 21 || t === 22 || t === 23 || 
                           t === 32 || t === 38 || t === 40 || 
                           t === 61 || t === 62;
                }
                
                property bool hasStock: root.showStockFilter && modelData.stock !== undefined
                
                property bool shouldShow: {
                    if (!inBounds) return false;
                    if (hasStock) return true;
                    if (root.currentZoom < 5) return false;
                    if (isResource) return root.showResources;
                    return root.showIcons;
                }
                
                visible: shouldShow
                
                // Set appropriate icon size
                width: hasStock ? 30 : 24
                height: hasStock ? 30 : 24
                
                // (Removed pulsing logistics target indicator)
                
                Loader {
                    anchors.fill: parent
                    active: shouldShow
                    sourceComponent: Item {
                        anchors.fill: parent
                        
                Image {
                    id: baseIcon
                    anchors.fill: parent
                    source: {
                        var type = modelData.type;
                        var iconMap = {
                            5: "MapIconTownBaseTier1.webp",
                            6: "MapIconTownBaseTier2.webp",
                            7: "MapIconTownBaseTier3.webp",
                            8: "MapIconTownBaseTier1.webp",
                            9: "MapIconTownBaseTier2.webp",
                            10: "MapIconTownBaseTier3.webp",
                            11: "MapIconHospital.webp",
                            12: "MapIconVehicle.webp",
                            16: "MapIconManufacturing.webp",
                            17: "MapIconManufacturing.webp", // Refinery
                            18: "Shipyard.webp",
                            19: "MapIconTechCenter.webp",
                            20: "MapIconSalvageColor.webp", // Salvage Field
                            21: "MapIconComponentsColor.webp", // Component Field
                            22: "MapIconFuel.webp", // Fuel Field
                            23: "MapIconSulfurColor.webp", // Sulfur Field
                            27: "MapIconsKeep.webp",
                            28: "MapIconObservationTower.webp",
                            29: "MapIconRelicBase.webp", // Fort
                            31: "MapIconSulfurMineColor.webp",
                            32: "MapIconSulfurMineColor.webp",
                            33: "MapIconStorageFacility.webp",
                            34: "MapIconFactory.webp",
                            35: "MapIconSafehouse.webp", // Garrison Station
                            36: "MapIconFactory.webp", // Ammo Factory
                            37: "MapIconRocketSite.webp",
                            38: "MapIconSalvageMineColor.webp",
                            39: "MapIconConstructionYard.webp",
                            40: "MapIconComponentMineColor.webp",
                            41: "MapIconFacilityMineOilRig.webp", // Oil Well
                            42: "MapIconRocketTarget.webp",
                            43: "MapIconMortarHouse.webp",
                            45: "MapIconRelicBase.webp",
                            46: "MapIconRelicBase.webp",
                            47: "MapIconRelicBase.webp",
                            48: "MapIconStormcannon.webp",
                            49: "MapIconIntelcenter.webp",
                            50: "MapIconBorderBase.webp",
                            51: "MapIconMassProductionFactory.webp",
                            52: "MapIconSeaport.webp",
                            53: "MapIconCoastalGun.webp",
                            54: "MapIconFactory.webp", // Soul Factory
                            55: "MapIconBorderBase.webp",
                            56: "MapIconTownBaseTier1.webp",
                            57: "MapIconTownBaseTier2.webp",
                            58: "MapIconTownBaseTier3.webp",
                            59: "MapIconStormcannon.webp",
                            60: "MapIconIntelcenter.webp",
                            61: "MapIconCoalFieldColor.webp",
                            62: "MapIconOilFieldColor.webp",
                            70: "MapIconRocketTarget.webp",
                            71: "MapIconRocketGroundZero.webp",
                            84: "MapIconMaintenanceTunnel.webp",
                            85: "MapIconTrainBridge.webp",
                            86: "Shipyard.webp", // Dry Dock
                            87: "MapIconFacilityMineOilRig.webp", // Offshore Platform
                            88: "MapIconAircraftDeposit.webp"
                        };
                        var filename = iconMap[type] || "unknown.webp";
                        return typeof appController !== "undefined" ? appController.assetUrl("img/iconmap/" + filename) : "file:///" + filename;
                    }
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    mipmap: true
                    // Hide base image only if we are applying a color effect
                    visible: !(modelData.team === 1 || modelData.team === 2)
                }
                
                Component {
                    id: teamColorEffect
                    MultiEffect {
                        anchors.fill: parent
                        source: baseIcon
                        colorization: 1.0
                        colorizationColor: modelData.team === 1 ? "#3b82f6" : "#22c55e"
                    }
                }
                
                Loader {
                    anchors.fill: baseIcon
                    active: modelData.team === 1 || modelData.team === 2
                    sourceComponent: teamColorEffect
                }
                
                HoverHandler {
                    id: mapHoverHandler
                    onHoveredChanged: {
                        if (hovered) {
                            if (!hasStock) {
                                var p = mapToItem(root, mapHoverHandler.point.position.x, mapHoverHandler.point.position.y);
                                globalToolTip.x = p.x + 15;
                                globalToolTip.y = p.y + 15;
                                globalToolTip.text = modelData.name + " (Type: " + modelData.type + ")";
                                globalToolTip.visible = true;
                            }
                            parent.scale = 1.2;
                        } else {
                            globalToolTip.visible = false;
                            parent.scale = 1.0;
                        }
                    }
                }
                
                TapHandler {
                    onTapped: {
                        console.log("Clicked:", modelData.name);
                    }
                }
                
                Rectangle {
                    anchors.centerIn: baseIcon
                    width: baseIcon.width + 4
                    height: baseIcon.height + 4
                    radius: width / 2
                    color: "transparent"
                    border.color: "#FFD700"
                    border.width: 2
                    visible: hasStock
                    
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: -4
                        radius: width / 2
                        color: "transparent"
                        border.color: "#FFD700"
                        border.width: 1
                        opacity: 0.5
                    }
                }
                
                Rectangle {
                    id: stockHoverCard
                    z: 50
                    // Keep visible if either the map icon is hovered or the panel itself is hovered/pinned
                    property bool isPinned: false
                    visible: hasStock && (mapHoverHandler.hovered || panelHoverHandler.hovered || isPinned)
                    opacity: visible ? 1 : 0
                    
                    // Position directly next to the icon without a gap, so hover is continuous
                    x: baseIcon.width
                    y: -height / 2 + baseIcon.height / 2
                    
                    // Default sizes
                    width: 600
                    height: stockHoverContent.implicitHeight + 20
                    radius: 8
                    color: settingsController.surfaceColor 
                    border.color: settingsController.borderColor
                    border.width: 1
                    
                    Behavior on opacity { NumberAnimation { duration: 150 } }
                    
                    HoverHandler {
                        id: panelHoverHandler
                    }
                    
                    TapHandler {
                        onTapped: {
                            stockHoverCard.isPinned = !stockHoverCard.isPinned;
                        }
                    }

                    Rectangle {
                        anchors.fill: parent
                        radius: parent.radius
                        color: settingsController.backgroundColor
                        opacity: 0.2
                    }

                    // Keep track of which warehouse is selected
                    property int selectedWarehouseIndex: 0
                    property var currentWarehouse: (modelData.stock && modelData.stock.length > selectedWarehouseIndex) ? modelData.stock[selectedWarehouseIndex] : null

                    // Helper to group items by category
                    function getItemsByCategory(catKey) {
                        if (!currentWarehouse || !currentWarehouse.items) return [];
                        var res = [];
                        for (var i = 0; i < currentWarehouse.items.length; i++) {
                            var item = currentWarehouse.items[i];
                            // Match categories (or map multiple API categories to the UI category)
                            if (catKey === "Priority" && item.category === "Priority") {
                                res.push(item);
                            } else if (catKey === "Supplies" && (item.category === "Supplies" || item.category === "Medical" || item.category === "Utility")) {
                                res.push(item);
                            } else if (catKey === "CommonLogi" && (item.category === "Small Arms" || item.category === "Heavy Arms" || item.category === "Heavy Ammo")) {
                                res.push(item);
                            } else if (catKey === "Vehicles" && item.category === "Vehicles") {
                                res.push(item);
                            } else if (catKey === "Others" && item.category !== "Priority" && item.category !== "Supplies" && item.category !== "Medical" && item.category !== "Utility" && item.category !== "Small Arms" && item.category !== "Heavy Arms" && item.category !== "Heavy Ammo" && item.category !== "Vehicles") {
                                res.push(item);
                            }
                        }
                        return res;
                    }

                    ColumnLayout {
                        id: stockHoverContent
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 12

                        // Header row
                        RowLayout {
                            Layout.fillWidth: true
                            
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: root.tr("map.stock.title", "Visual do estoque")
                                    color: settingsController.textColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 16
                                    font.bold: true
                                }
                                Text {
                                    text: root.tr("map.stock.updated", "Atualizado") + ": " + modelData.name + " - " + (stockHoverCard.currentWarehouse ? stockHoverCard.currentWarehouse.last_update : "")
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                }
                            }
                            
                            // Warehouse Selector
                            ComboBox {
                                id: warehouseCombo
                                Layout.preferredWidth: 150
                                visible: modelData.stock && modelData.stock.length > 1
                                model: {
                                    var arr = [];
                                    if (modelData.stock) {
                                        for (var i = 0; i < modelData.stock.length; i++) {
                                            arr.push(modelData.stock[i].warehouse_name);
                                        }
                                    }
                                    return arr;
                                }
                                currentIndex: stockHoverCard.selectedWarehouseIndex
                                onCurrentIndexChanged: {
                                    if (currentIndex >= 0) {
                                        stockHoverCard.selectedWarehouseIndex = currentIndex;
                                    }
                                }
                                
                                background: Rectangle {
                                    color: settingsController.backgroundColor
                                    border.color: settingsController.borderColor
                                    radius: 4
                                }
                                contentItem: Text {
                                    text: warehouseCombo.currentText
                                    color: "white"
                                    verticalAlignment: Text.AlignVCenter
                                    font.pixelSize: 12
                                    leftPadding: 10
                                }
                            }
                            
                            // Optional pin indicator
                            Text {
                                text: stockHoverCard.isPinned ? "📌" : ""
                                color: "#FFD700"
                                font.pixelSize: 14
                                visible: stockHoverCard.isPinned
                            }
                        }
                        
                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: settingsController.borderColor
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: settingsController.borderColor
                        }
                        
                        // Dynamic categories
                        Repeater {
                            model: [
                                { key: "Priority", label: root.tr("map.stock.priority", "PRIORIDADE") },
                                { key: "Supplies", label: root.tr("map.stock.supplies", "SUPRIMENTOS") },
                                { key: "CommonLogi", label: root.tr("map.stock.common_logi", "LOGI COMUM") },
                                { key: "Vehicles", label: root.tr("map.stock.vehicles", "VEÍCULOS") },
                                { key: "Others", label: root.tr("map.stock.others", "OUTROS") }
                            ]
                            delegate: ColumnLayout {
                                property var catItems: stockHoverCard.getItemsByCategory(modelData.key)
                                visible: catItems.length > 0
                                spacing: 4
                                Layout.fillWidth: true

                                Text {
                                    text: modelData.label
                                    color: settingsController.mutedTextColor
                                    font.family: "Segoe UI"
                                    font.pixelSize: 10
                                    font.bold: true
                                }
                                
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Repeater {
                                        model: catItems
                                        delegate: Rectangle {
                                            width: 60
                                            height: 28
                                            color: settingsController.backgroundColor
                                            border.color: settingsController.borderColor
                                            border.width: 1
                                            radius: 3
                                            
                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.margins: 4
                                                spacing: 4
                                                Image {
                                                    source: modelData.icon || ""
                                                    sourceSize.width: 20
                                                    sourceSize.height: 20
                                                    Layout.preferredWidth: 20
                                                    Layout.preferredHeight: 20
                                                    fillMode: Image.PreserveAspectFit
                                                }
                                                Text {
                                                    text: modelData.quantity || "0"
                                                    color: settingsController.textColor
                                                    font.family: "Segoe UI"
                                                    font.pixelSize: 12
                                                    font.bold: true
                                                    Layout.fillWidth: true
                                                    horizontalAlignment: Text.AlignRight
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
            }
        }
    }

    // --- DRAWING CANVAS ---
    Item {
        id: drawingContainer
        anchors.fill: parent
        z: 3 // Above map, below UI filters
        
        // This ensures the canvas moves instantly with the map without waiting for repaint
        transform: Translate {
            x: drawingCanvas.lastPaintCenterX - root.centerX
            y: drawingCanvas.lastPaintCenterY - root.centerY
        }
        
        Canvas {
            id: drawingCanvas
            anchors.fill: parent
            
            property real lastPaintCenterX: root.centerX
            property real lastPaintCenterY: root.centerY
            property real lastPaintZoom: root.currentZoom
            
            onPaint: {
                lastPaintCenterX = root.centerX;
                lastPaintCenterY = root.centerY;
                lastPaintZoom = root.currentZoom;
                
                var ctx = getContext("2d");
                ctx.clearRect(0, 0, width, height);
                
                var allDrawings = root.drawings;
                if (root.currentDrawing) {
                    allDrawings = allDrawings.concat([root.currentDrawing]);
                }
                
                for (var i = 0; i < allDrawings.length; i++) {
                    var d = allDrawings[i];
                    if (!d) continue;
                    
                    ctx.strokeStyle = d.color;
                    ctx.fillStyle = d.color;
                    ctx.lineWidth = d.thickness || 3;
                    ctx.lineCap = "round";
                    ctx.lineJoin = "round";
                    
                    if (d.type === "brush" && d.points && d.points.length > 0) {
                        ctx.beginPath();
                        var sp = worldToCanvas(d.points[0].x, d.points[0].y);
                        ctx.moveTo(sp.x, sp.y);
                        for (var j = 1; j < d.points.length; j++) {
                            var p = worldToCanvas(d.points[j].x, d.points[j].y);
                            ctx.lineTo(p.x, p.y);
                        }
                        ctx.stroke();
                    } else if (d.type === "arrow" && d.start && d.end) {
                        var p1 = worldToCanvas(d.start.x, d.start.y);
                        var p2 = worldToCanvas(d.end.x, d.end.y);
                        var headSize = 10 + (d.thickness || 3) * 1.5;
                        drawArrow(ctx, p1.x, p1.y, p2.x, p2.y, headSize);
                    } else if (d.type === "polygon" && d.points && d.points.length > 0) {
                        ctx.beginPath();
                        var sp2 = worldToCanvas(d.points[0].x, d.points[0].y);
                        ctx.moveTo(sp2.x, sp2.y);
                        for (var k = 1; k < d.points.length; k++) {
                            var pk = worldToCanvas(d.points[k].x, d.points[k].y);
                            ctx.lineTo(pk.x, pk.y);
                        }
                        if (d.points.length > 2) {
                            ctx.closePath();
                        }
                        
                        if (d.points.length > 2) {
                            ctx.save();
                            ctx.globalAlpha = 0.3;
                            ctx.fillStyle = d.color;
                            ctx.fill();
                            ctx.restore();
                        }
                        
                        ctx.stroke();
                        
                        if (d.name) {
                            var cx = 0, cy = 0;
                            for (var m = 0; m < d.points.length; m++) {
                                var ptm = worldToCanvas(d.points[m].x, d.points[m].y);
                                cx += ptm.x;
                                cy += ptm.y;
                            }
                            cx /= d.points.length;
                            cy /= d.points.length;
                            
                            ctx.fillStyle = "#ffffff";
                            ctx.font = "bold 14px Segoe UI";
                            ctx.textAlign = "center";
                            ctx.textBaseline = "middle";
                            ctx.strokeStyle = "#000000";
                            ctx.lineWidth = 3;
                            ctx.strokeText(d.name, cx, cy);
                            ctx.fillText(d.name, cx, cy);
                            ctx.lineWidth = d.thickness || 3;
                        }
                    }
                }
                
                for (var rIndex = 0; rIndex < root.logisticsRoutes.length; rIndex++) {
                    var lr = root.logisticsRoutes[rIndex];
                    var sP = worldToCanvas(lr.start.x, lr.start.y);
                    var eP = worldToCanvas(lr.end.x, lr.end.y);
                    
                    ctx.beginPath();
                    ctx.moveTo(sP.x, sP.y);
                    var cx = (sP.x + eP.x) / 2;
                    var cy = (sP.y + eP.y) / 2;
                    var dx = eP.x - sP.x;
                    var dy = eP.y - sP.y;
                    
                    var ctrlX = cx - dy * 0.2;
                    var ctrlY = cy + dx * 0.2;
                    
                    ctx.quadraticCurveTo(ctrlX, ctrlY, eP.x, eP.y);
                    
                    ctx.lineWidth = root.logisticsHoveredRoute === lr ? 6 : 4;
                    ctx.strokeStyle = root.logisticsHoveredRoute === lr ? "#eab308" : "#3b82f6";
                    ctx.setLineDash([10, 10]);
                    ctx.stroke();
                    ctx.setLineDash([]);
                }
            }
        }
    }

    // --- MAP FILTERS UI ---
    
    component StyledCheckBox: CheckBox {
        id: control
        contentItem: Text {
            text: control.text
            color: settingsController.textColor
            font.pixelSize: 14
            leftPadding: control.indicator.width + control.spacing
            verticalAlignment: Text.AlignVCenter
        }
        indicator: Rectangle {
            implicitWidth: 18
            implicitHeight: 18
            x: control.leftPadding
            y: parent.height / 2 - height / 2
            radius: 4
            color: control.down ? Qt.darker(settingsController.backgroundColor, 1.2) : (control.hovered ? settingsController.surfaceColor : settingsController.backgroundColor)
            border.color: control.checked ? settingsController.accentColor : settingsController.borderColor
            border.width: control.checked ? 0 : 1

            Rectangle {
                width: 10
                height: 10
                x: 4
                y: 4
                radius: 2
                color: settingsController.accentColor
                visible: control.checked
            }
        }
    }

    Button {
        id: filterButton
        text: "⚙️ " + root.tr("map.filter.title", "Filtros do Mapa")
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 20
        z: 100
        
        onClicked: filterPopup.visible = !filterPopup.visible
        
        background: Rectangle {
            color: filterButton.hovered ? settingsController.surfaceColor : settingsController.backgroundColor
            border.color: settingsController.borderColor
            border.width: 1
            radius: 6
            
            MultiEffect {
                source: parent
                anchors.fill: parent
                shadowEnabled: true
                shadowOpacity: 0.3
                shadowBlur: 0.5
                shadowVerticalOffset: 2
                shadowColor: "black"
            }
        }
        contentItem: Text {
            text: filterButton.text
            color: settingsController.textColor
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 14
            font.bold: true
        }
    }
    
    Item {
        id: filterPopup
        visible: false
        width: filterColumn.implicitWidth + 40
        height: filterColumn.implicitHeight + 30
        anchors.top: filterButton.bottom
        anchors.right: parent.right
        anchors.topMargin: 12
        anchors.rightMargin: 20
        z: 100
        
        Rectangle {
            id: popupBg
            anchors.fill: parent
            color: settingsController.surfaceColor
            border.color: settingsController.borderColor
            border.width: 1
            radius: 8
        }
        
        MultiEffect {
            source: popupBg
            anchors.fill: popupBg
            shadowEnabled: true
            shadowOpacity: 0.5
            shadowBlur: 1.0
            shadowVerticalOffset: 4
            shadowColor: "black"
        }
        
        Column {
            id: filterColumn
            anchors.centerIn: parent
            spacing: 12
            
            StyledCheckBox { 
                text: root.tr("map.filter.hex", "Regiões (Hex)")
                checked: root.showHexNames
                onCheckedChanged: root.showHexNames = checked
            }
            StyledCheckBox { 
                text: root.tr("map.filter.major", "Cidades Principais")
                checked: root.showMajorCities
                onCheckedChanged: root.showMajorCities = checked
            }
            StyledCheckBox { 
                text: root.tr("map.filter.minor", "Sub-regiões (Vilas)")
                checked: root.showMinorCities
                onCheckedChanged: root.showMinorCities = checked
            }
            StyledCheckBox { 
                text: root.tr("map.filter.resources", "Recursos (Campos/Minas)")
                checked: root.showResources
                onCheckedChanged: root.showResources = checked
            }
            StyledCheckBox { 
                text: root.tr("map.filter.icons", "Estruturas Gerais")
                checked: root.showIcons
                onCheckedChanged: root.showIcons = checked
            }
            StyledCheckBox { 
                text: root.tr("map.filter.stock", "Depósitos com Estoque")
                checked: root.showStockFilter
                onCheckedChanged: root.showStockFilter = checked
            }
        }
    }

    MouseArea {
        id: mapMouseArea
        anchors.fill: parent
        hoverEnabled: true
        
        property real lastX: 0
        property real lastY: 0
        property real pressX: 0
        property real pressY: 0
        property bool isDragging: false
        property bool didPan: false
        
        function eraseAt(sx, sy) {
            var wp = screenToWorld(sx, sy);
            var threshold = 15 / Math.pow(2, root.currentZoom);
            var removed = false;
            var newDrawings = [];
            
            for (var i = 0; i < root.drawings.length; i++) {
                var d = root.drawings[i];
                var hit = false;
                if (d.type === "polygon") {
                    hit = isPointInPolygon(wp.x, wp.y, d.points);
                } else if (d.type === "brush") {
                    for (var j = 0; j < d.points.length - 1; j++) {
                        var dist = distanceToSegment(wp.x, wp.y, d.points[j].x, d.points[j].y, d.points[j+1].x, d.points[j+1].y);
                        if (dist <= threshold + (d.thickness || 3) / Math.pow(2, root.currentZoom)) {
                            hit = true; break;
                        }
                    }
                } else if (d.type === "arrow") {
                    var dist2 = distanceToSegment(wp.x, wp.y, d.start.x, d.start.y, d.end.x, d.end.y);
                    if (dist2 <= threshold + (d.thickness || 3) / Math.pow(2, root.currentZoom)) {
                        hit = true;
                    }
                }
                
                if (hit) {
                    removed = true;
                } else {
                    newDrawings.push(d);
                }
            }
            
            if (removed) {
                root.drawings = newDrawings;
                drawingCanvas.requestPaint();
            }
        }
        
        onPressed: function(mouse) {
            lastX = mouse.x;
            lastY = mouse.y;
            pressX = mouse.x;
            pressY = mouse.y;
            isDragging = true;
            didPan = false;
            
            if (root.activeTool !== "pan") {
                root.showToolSettings = false;
            }
            
            if (root.activeTool === "pan") {
                cursorShape = Qt.ClosedHandCursor;
            } else if (root.activeTool === "brush") {
                var wp = screenToWorld(mouse.x, mouse.y);
                root.currentDrawing = { type: "brush", color: root.activeColor, thickness: root.activeThickness, points: [wp] };
                drawingCanvas.requestPaint();
            } else if (root.activeTool === "arrow") {
                var wp2 = screenToWorld(mouse.x, mouse.y);
                root.currentDrawing = { type: "arrow", color: root.activeColor, thickness: root.activeThickness, start: wp2, end: wp2 };
                drawingCanvas.requestPaint();
            } else if (root.activeTool === "polygon") {
                cursorShape = Qt.ClosedHandCursor; // Will reset to cross on release if no pan
            } else if (root.activeTool === "eraser") {
                eraseAt(mouse.x, mouse.y);
            }
        }
        
        onReleased: {
            isDragging = false;
            if (root.activeTool === "pan") {
                cursorShape = Qt.OpenHandCursor;
            } else if (root.activeTool === "polygon") {
                cursorShape = Qt.CrossCursor;
                if (!didPan && !root.polygonNameDialogVisible) {
                    var wp = screenToWorld(mouse.x, mouse.y);
                    if (!root.currentDrawing || root.currentDrawing.type !== "polygon") {
                        root.currentDrawing = { type: "polygon", color: root.activeColor, thickness: root.activeThickness, points: [wp] };
                    } else {
                        var poly = Object.assign({}, root.currentDrawing);
                        poly.points = poly.points.slice();
                        poly.points.push(wp);
                        root.currentDrawing = poly;
                    }
                    drawingCanvas.requestPaint();
                }
            } else {
                if (root.currentDrawing) {
                    var newDrawings = root.drawings.slice();
                    newDrawings.push(root.currentDrawing);
                    root.drawings = newDrawings;
                    root.currentDrawing = null;
                }
            }
        }
        
        onEntered: {
            if (root.activeTool === "pan") {
                cursorShape = isDragging ? Qt.ClosedHandCursor : Qt.OpenHandCursor;
            } else {
                cursorShape = Qt.CrossCursor;
            }
        }
        
        onExited: {
            cursorShape = Qt.ArrowCursor;
            isDragging = false;
            if (root.currentDrawing && root.activeTool !== "polygon") {
                var newDrawings = root.drawings.slice();
                newDrawings.push(root.currentDrawing);
                root.drawings = newDrawings;
                root.currentDrawing = null;
            }
        }
        
        onPositionChanged: function(mouse) {
            if (isDragging) {
                if (root.activeTool === "pan" || root.activeTool === "polygon") {
                    var dx = mouse.x - lastX;
                    var dy = mouse.y - lastY;
                    
                    var dist = Math.sqrt(Math.pow(mouse.x - pressX, 2) + Math.pow(mouse.y - pressY, 2));
                    if (dist > 5) {
                        didPan = true;
                    }
                    
                    if (didPan || root.activeTool === "pan") {
                        var mapSize = Math.pow(2, root.currentZoom) * root.tileSize;
                        root.centerX = Math.max(0, Math.min(mapSize, root.centerX - dx));
                        root.centerY = Math.max(0, Math.min(mapSize, root.centerY - dy));
                        lastX = mouse.x;
                        lastY = mouse.y;
                        drawingCanvas.requestPaint();
                    }
                } else if (root.activeTool === "brush" && root.currentDrawing) {
                    var wp = screenToWorld(mouse.x, mouse.y);
                    root.currentDrawing.points.push(wp);
                    drawingCanvas.requestPaint();
                } else if (root.activeTool === "arrow" && root.currentDrawing) {
                    var wp2 = screenToWorld(mouse.x, mouse.y);
                    root.currentDrawing.end = wp2;
                    drawingCanvas.requestPaint();
                } else if (root.activeTool === "eraser") {
                    eraseAt(mouse.x, mouse.y);
                }
            } else {
                if (root.logisticsRoutes.length > 0) {
                    var hwp = screenToWorld(mouse.x, mouse.y);
                    var foundHover = null;
                    for (var r = 0; r < root.logisticsRoutes.length; r++) {
                        var route = root.logisticsRoutes[r];
                        var rdist = distanceToSegment(hwp.x, hwp.y, route.start.x, route.start.y, route.end.x, route.end.y);
                        if (rdist < 20 / Math.pow(2, root.currentZoom)) {
                            foundHover = route;
                            break;
                        }
                    }
                    if (root.logisticsHoveredRoute !== foundHover) {
                        root.logisticsHoveredRoute = foundHover;
                        drawingCanvas.requestPaint();
                    }
                }
            }
        }
        
        onWheel: function(wheel) {
            var zoomDelta = wheel.angleDelta.y > 0 ? 1 : -1;
            var newZoom = Math.max(root.minZoom, Math.min(root.maxZoom, root.currentZoom + zoomDelta));
            
            if (newZoom !== root.currentZoom) {
                // Calculate map world origin relative to screen
                var mapOriginX = (root.width / 2) - root.centerX;
                var mapOriginY = (root.height / 2) - root.centerY;

                // Adjust centerX and centerY to zoom in on the mouse point
                var mx = wheel.x - mapOriginX;
                var my = wheel.y - mapOriginY;
                
                var scaleFactor = Math.pow(2, newZoom - root.currentZoom);
                var newMx = mx * scaleFactor;
                var newMy = my * scaleFactor;
                
                var newCenterX = root.centerX + (newMx - mx);
                var newCenterY = root.centerY + (newMy - my);
                
                var mapSize = Math.pow(2, newZoom) * root.tileSize;
                var finalCenterX = Math.max(0, Math.min(mapSize, newCenterX));
                var finalCenterY = Math.max(0, Math.min(mapSize, newCenterY));
                
                var activeLayer = (activeLayerIndex === 0) ? layerA : layerB;
                var inactiveLayer = (activeLayerIndex === 0) ? layerB : layerA;
                
                if (activeLayer.isLoaded) {
                    activeLayer.freezeCenter = true;
                    inactiveLayer.freezeCenter = false;
                    activeLayerIndex = (activeLayerIndex + 1) % 2;
                }
                
                root.centerX = finalCenterX;
                root.centerY = finalCenterY;
                root.currentZoom = newZoom;
                drawingCanvas.requestPaint();
            }
        }
    }

    // --- BOTTOM DRAWING TOOLBAR ---
    Rectangle {
        id: drawingToolbar
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        anchors.horizontalCenter: parent.horizontalCenter
        height: 50
        width: toolbarRow.implicitWidth + 32
        radius: 25
        color: settingsController.surfaceColor
        border.color: settingsController.borderColor
        border.width: 1
        z: 100

        MultiEffect {
            source: drawingToolbar
            anchors.fill: drawingToolbar
            shadowEnabled: true
            shadowOpacity: 0.4
            shadowBlur: 0.8
            shadowVerticalOffset: 4
            shadowColor: "black"
        }

        Row {
            id: toolbarRow
            anchors.centerIn: parent
            spacing: 16

            // Pan Tool
            Rectangle {
                width: 36
                height: 36
                radius: 18
                color: root.activeTool === "pan" ? settingsController.accentColor : "transparent"
                border.color: root.activeTool === "pan" ? settingsController.accentColor : settingsController.borderColor
                Text {
                    anchors.centerIn: parent
                    text: "✋"
                    font.pixelSize: 18
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        root.activeTool = "pan";
                        root.showToolSettings = false;
                    }
                    cursorShape: Qt.PointingHandCursor
                }
            }

            // Brush Tool
            Rectangle {
                width: 36
                height: 36
                radius: 18
                color: root.activeTool === "brush" ? settingsController.accentColor : "transparent"
                border.color: root.activeTool === "brush" ? settingsController.accentColor : settingsController.borderColor
                Text {
                    anchors.centerIn: parent
                    text: "🖌️"
                    font.pixelSize: 18
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (root.activeTool === "brush") {
                            root.showToolSettings = !root.showToolSettings;
                        } else {
                            root.activeTool = "brush";
                            root.showToolSettings = true;
                        }
                    }
                    cursorShape: Qt.PointingHandCursor
                }
            }

            // Arrow Tool
            Rectangle {
                width: 36
                height: 36
                radius: 18
                color: root.activeTool === "arrow" ? settingsController.accentColor : "transparent"
                border.color: root.activeTool === "arrow" ? settingsController.accentColor : settingsController.borderColor
                Text {
                    anchors.centerIn: parent
                    text: "↗️"
                    font.pixelSize: 18
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (root.activeTool === "arrow") {
                            root.showToolSettings = !root.showToolSettings;
                        } else {
                            root.activeTool = "arrow";
                            root.showToolSettings = true;
                        }
                    }
                    cursorShape: Qt.PointingHandCursor
                }
            }

            // Polygon Tool
            Rectangle {
                width: 36
                height: 36
                radius: 18
                color: root.activeTool === "polygon" ? settingsController.accentColor : "transparent"
                border.color: root.activeTool === "polygon" ? settingsController.accentColor : settingsController.borderColor
                Text {
                    anchors.centerIn: parent
                    text: "⬟"
                    font.pixelSize: 18
                    color: root.activeTool === "polygon" ? "white" : settingsController.textColor
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (root.activeTool === "polygon") {
                            root.showToolSettings = !root.showToolSettings;
                        } else {
                            if (root.currentDrawing && root.currentDrawing.type === "polygon") {
                                root.currentDrawing = null; // discard if changing tool
                            }
                            root.activeTool = "polygon";
                            root.showToolSettings = true;
                        }
                    }
                    cursorShape: Qt.PointingHandCursor
                }
            }
            
            Rectangle {
                width: 1
                height: 24
                color: settingsController.borderColor
                anchors.verticalCenter: parent.verticalCenter
            }
            // Logistics Tool
            Rectangle {
                width: 36
                height: 36
                radius: 18
                color: root.logisticsModalVisible ? settingsController.accentColor : "transparent"
                border.color: root.logisticsModalVisible ? settingsController.accentColor : settingsController.borderColor
                Text {
                    anchors.centerIn: parent
                    text: "🚚"
                    font.pixelSize: 18
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        logisticsModal.open();
                    }
                    cursorShape: Qt.PointingHandCursor
                }
            }
            
            Rectangle {
                width: 1
                height: 24
                color: settingsController.borderColor
                anchors.verticalCenter: parent.verticalCenter
            }
            // Eraser Tool
            Rectangle {
                width: 36
                height: 36
                radius: 18
                color: root.activeTool === "eraser" ? settingsController.accentColor : "transparent"
                border.color: root.activeTool === "eraser" ? settingsController.accentColor : settingsController.borderColor
                Text {
                    anchors.centerIn: parent
                    text: "🧽"
                    font.pixelSize: 18
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (root.activeTool === "eraser") {
                            root.showToolSettings = !root.showToolSettings;
                        } else {
                            if (root.currentDrawing && root.currentDrawing.type === "polygon") {
                                root.currentDrawing = null;
                            }
                            root.activeTool = "eraser";
                            root.showToolSettings = true;
                        }
                    }
                    cursorShape: Qt.PointingHandCursor
                }
            }
        }
    }

    // --- TOOL SETTINGS MODAL ---
    Rectangle {
        id: toolSettingsModal
        visible: root.showToolSettings && (root.activeTool === "brush" || root.activeTool === "arrow" || root.activeTool === "polygon" || root.activeTool === "eraser")
        anchors.bottom: drawingToolbar.top
        anchors.bottomMargin: 12
        anchors.horizontalCenter: parent.horizontalCenter
        width: 240
        height: root.activeTool === "eraser" ? 80 : 120
        radius: 12
        color: settingsController.surfaceColor
        border.color: settingsController.borderColor
        border.width: 1
        z: 100

        MultiEffect {
            source: toolSettingsModal
            anchors.fill: toolSettingsModal
            shadowEnabled: true
            shadowOpacity: 0.3
            shadowBlur: 0.8
            shadowVerticalOffset: 2
            shadowColor: "black"
        }

        Column {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12
            visible: root.activeTool !== "eraser"
            
            Text {
                text: root.activeTool === "brush" ? "Espessura e Cor do Pincel" : (root.activeTool === "arrow" ? "Espessura e Cor da Seta" : "Espessura e Cor da Área")
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 12
            }
            
            Row {
                spacing: 8
                Repeater {
                    model: ["#ef4444", "#3b82f6", "#22c55e", "#eab308", "#ffffff", "#000000"]
                    delegate: Rectangle {
                        width: 24
                        height: 24
                        radius: 12
                        color: modelData
                        border.color: root.activeColor === modelData ? settingsController.accentColor : "#888888"
                        border.width: root.activeColor === modelData ? 3 : 1
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.activeColor = modelData
                            cursorShape: Qt.PointingHandCursor
                        }
                    }
                }
            }
            
            RowLayout {
                width: parent.width
                spacing: 8
                
                Rectangle {
                    width: 24
                    height: 24
                    color: "transparent"
                    Layout.alignment: Qt.AlignVCenter
                    
                    Rectangle {
                        anchors.centerIn: parent
                        width: Math.min(24, Math.max(4, root.activeThickness))
                        height: width
                        radius: width / 2
                        color: root.activeColor
                        border.color: root.activeColor === "#000000" ? "#ffffff" : "transparent"
                        border.width: 1
                    }
                }
                
                Slider {
                    Layout.fillWidth: true
                    from: 1
                    to: 20
                    value: root.activeThickness
                    stepSize: 1
                    onValueChanged: root.activeThickness = value
                }
            }
        }
        
        Column {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12
            visible: root.activeTool === "eraser"
            
            Text {
                text: "Opções da Borracha"
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 12
            }
            
            Button {
                width: parent.width
                height: 32
                background: Rectangle {
                    color: "#ef4444"
                    radius: 4
                }
                contentItem: Text {
                    text: "Limpar Todos os Desenhos"
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.bold: true
                }
                onClicked: {
                    root.drawings = [];
                    root.currentDrawing = null;
                    drawingCanvas.requestPaint();
                    root.showToolSettings = false;
                    root.activeTool = "pan";
                }
            }
        }
        
        // Removed old logistics configuration block
    }

    // --- LOGISTICS ROUTE HOVER TOOLTIP ---
    Rectangle {
        id: logisticsHoverTooltip
        visible: root.logisticsHoveredRoute !== null
        x: mapMouseArea.mouseX + 15
        y: mapMouseArea.mouseY + 15
        width: 250
        height: routeContent.implicitHeight + 20
        radius: 8
        color: settingsController.surfaceColor
        border.color: settingsController.borderColor
        border.width: 1
        z: 300
        
        Column {
            id: routeContent
            anchors.fill: parent
            anchors.margins: 10
            spacing: 8
            
            Text {
                text: root.logisticsHoveredRoute ? ("De: " + root.logisticsHoveredRoute.start.name + "\nPara: " + root.logisticsHoveredRoute.end.name) : ""
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 13
                wrapMode: Text.WordWrap
                width: parent.width
            }
            
            Rectangle { width: parent.width; height: 1; color: settingsController.borderColor }
            
            Text {
                text: "📦 Cargas:"
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 12
            }
            
            Repeater {
                model: root.logisticsHoveredRoute ? root.logisticsHoveredRoute.cargo : []
                delegate: RowLayout {
                    width: parent.width
                    spacing: 6
                    Rectangle {
                        width: 20; height: 20; radius: 4
                        color: settingsController.controlColor
                        Image {
                            anchors.fill: parent; anchors.margins: 2
                            source: modelData.icon || ""
                            visible: source !== ""
                            fillMode: Image.PreserveAspectFit
                        }
                    }
                    Text {
                        text: modelData.qty + "x " + modelData.name
                        color: settingsController.textColor
                        font.pixelSize: 12
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }
            }
            
            Rectangle { width: parent.width; height: 1; color: settingsController.borderColor }
            
            Text {
                property int totalCrates: {
                    if (!root.logisticsHoveredRoute) return 0;
                    var t = 0;
                    for (var i = 0; i < root.logisticsHoveredRoute.cargo.length; i++) {
                        t += root.logisticsHoveredRoute.cargo[i].qty;
                    }
                    return t;
                }
                text: "🚛 Veículos (Viagens):\n" +
                      "• Dunne (15): " + Math.ceil(totalCrates / 15) + "\n" +
                      "• Flatbed (60): " + Math.ceil(totalCrates / 60) + "\n" +
                      "• Ironship (300): " + Math.ceil(totalCrates / 300)
                color: settingsController.textColor
                font.pixelSize: 12
            }
        }
    }

    Rectangle {
        visible: root.activeTool === "polygon" && root.currentDrawing && root.currentDrawing.type === "polygon" && root.currentDrawing.points.length >= 2 && !root.polygonNameDialogVisible
        anchors.bottom: toolSettingsModal.visible ? toolSettingsModal.top : drawingToolbar.top
        anchors.bottomMargin: 12
        anchors.horizontalCenter: parent.horizontalCenter
        width: 140
        height: 36
        radius: 18
        color: settingsController.accentColor
        z: 100
        
        Text {
            anchors.centerIn: parent
            text: "✅ Finalizar Área"
            color: "white"
            font.bold: true
            font.pixelSize: 13
        }
        
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                root.polygonNameDialogVisible = true;
                polygonNameInput.forceActiveFocus();
            }
        }
    }
    
    // --- POLYGON NAME MODAL ---
    Rectangle {
        id: polygonNameModal
        visible: root.polygonNameDialogVisible
        anchors.centerIn: parent
        width: 300
        height: 140
        radius: 8
        color: settingsController.surfaceColor
        border.color: settingsController.borderColor
        border.width: 1
        z: 200
        
        MultiEffect {
            source: polygonNameModal
            anchors.fill: polygonNameModal
            shadowEnabled: true
            shadowOpacity: 0.5
            shadowBlur: 1.0
            shadowVerticalOffset: 4
            shadowColor: "black"
        }
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12
            
            Text {
                text: "Nome da Área Marcada"
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 16
                Layout.fillWidth: true
            }
            
            TextField {
                id: polygonNameInput
                Layout.fillWidth: true
                placeholderText: "Ex: Base Principal"
                color: settingsController.textColor
                background: Rectangle {
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor
                    border.width: 1
                    radius: 4
                }
                onAccepted: finishPolygonBtn.clicked()
            }
            
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                
                Button {
                    Layout.fillWidth: true
                    text: "Cancelar"
                    onClicked: {
                        root.polygonNameDialogVisible = false;
                        root.currentDrawing = null;
                        drawingCanvas.requestPaint();
                    }
                }
                
                Button {
                    id: finishPolygonBtn
                    Layout.fillWidth: true
                    text: "Salvar"
                    background: Rectangle {
                        color: settingsController.accentColor
                        radius: 4
                    }
                    contentItem: Text {
                        text: "Salvar"
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.bold: true
                    }
                    onClicked: {
                        if (root.currentDrawing && root.currentDrawing.type === "polygon") {
                            root.currentDrawing.name = polygonNameInput.text;
                            var newDrawings = root.drawings.slice();
                            newDrawings.push(root.currentDrawing);
                            root.drawings = newDrawings;
                            root.currentDrawing = null;
                            polygonNameInput.text = "";
                            root.polygonNameDialogVisible = false;
                            drawingCanvas.requestPaint();
                        }
                    }
                }
            }
        }
    }

    // --- DEBUG DATA MODAL (TEMPORARY) ---
    Rectangle {
        id: debugDataModal
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.margins: 20
        width: 320
        height: Math.min(parent.height - 40, debugColumn.implicitHeight + 40)
        radius: 8
        color: Qt.rgba(settingsController.surfaceColor.r, settingsController.surfaceColor.g, settingsController.surfaceColor.b, 0.9)
        border.color: settingsController.borderColor
        border.width: 1
        z: 999
        clip: true
        
        property string jsonOutput: ""
        
        Timer {
            interval: 500
            running: true
            repeat: true
            onTriggered: {
                var currentUserId = "";
                if (typeof chatController !== "undefined") {
                     currentUserId = typeof chatController.currentUserId !== "undefined" ? chatController.currentUserId : "";
                }
                
                var allDrawings = root.drawings.slice();
                if (root.currentDrawing) {
                    allDrawings.push(root.currentDrawing);
                }
                
                var data = {
                    user: {
                        nick: typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido",
                        avatar: typeof chatController !== "undefined" ? chatController.currentUserAvatar : "",
                        id: currentUserId
                    },
                    drawings: allDrawings
                };
                
                var jsonStr = JSON.stringify(data, function(key, val) {
                    if (val && typeof val.x === 'number') {
                        val.x = Math.round(val.x * 100) / 100;
                    }
                    if (val && typeof val.y === 'number') {
                        val.y = Math.round(val.y * 100) / 100;
                    }
                    return val;
                }, 2);
                
                // Otimiza visualmente as coordenadas para ocupar apenas 1 linha em vez de 4
                jsonStr = jsonStr.replace(/\{\n\s+"x": ([\d.-]+),\n\s+"y": ([\d.-]+)\n\s+\}/g, '{ "x": $1, "y": $2 }');
                
                debugDataModal.jsonOutput = jsonStr;
            }
        }
        
        Flickable {
            anchors.fill: parent
            anchors.margins: 10
            contentHeight: debugColumn.implicitHeight
            clip: true
            
            Column {
                id: debugColumn
                width: parent.width
                spacing: 10
                
                RowLayout {
                    width: parent.width
                    Image {
                        source: typeof chatController !== "undefined" && chatController.currentUserAvatar ? chatController.currentUserAvatar : ""
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        visible: source !== ""
                        fillMode: Image.PreserveAspectCrop
                        Rectangle {
                            anchors.fill: parent
                            radius: 16
                            color: "transparent"
                            border.color: settingsController.borderColor
                            border.width: 1
                        }
                    }
                    Text {
                        text: "Usuário: " + (typeof chatController !== "undefined" ? chatController.currentUserName : "-")
                        color: settingsController.textColor
                        font.bold: true
                        Layout.fillWidth: true
                    }
                }
                
                Text {
                    text: "JSON dos Desenhos:"
                    color: settingsController.accentColor
                    font.bold: true
                }
                
                Text {
                    width: parent.width
                    text: debugDataModal.jsonOutput
                    color: settingsController.textColor
                    font.family: "Consolas"
                    font.pixelSize: 10
                    wrapMode: Text.WrapAnywhere
}
}
            }
        }
    }
