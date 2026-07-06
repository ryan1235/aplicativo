import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import "SlangTerms.js" as SlangTerms
import "Vehicles.js" as VehiclesData
import GG.Map 1.0

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
    property bool showMainStructures: true
    
    // Component Lifecycle
    Component.onDestruction: {
        if (typeof mapSessionController !== "undefined") {
            mapSessionController.leaveWsRoom();
        }
    }

    property real cullCenterX: centerX
    property real cullCenterY: centerY
    signal updateCullingSignal()
    function updateCulling() {
        cullCenterX = centerX;
        cullCenterY = centerY;
        updateCullingSignal();
    }
    // --- DRAWING SYSTEM PROPERTIES ---
    property string activeTool: "pan" // "pan", "brush", "arrow", "polygon", "eraser", "vehicle", "artillery"
    
    // Artillery state
    property var artilleryCannon: null
    property var artilleryTarget: null
    property int artilleryStep: 0
    onActiveToolChanged: root.selectedVehicleIndex = -1
    
    property string activeColor: "#ef4444" // default red
    property string activeVehicleImage: "Blacksteele.png"
    property real activeVehicleRotation: 0
    property real activeVehicleScale: 1.0
    property string activeVehicleName: ""
    
    property int selectedVehicleIndex: -1
    property real liveVehicleRotation: 0
    property real liveVehicleScale: 1.0
    property string liveVehicleName: ""
    property bool wasEditingOnPress: false

    // --- MULTIPLAYER SESSION ---
    property var remoteCursorsDict: ({})
    ListModel { id: remoteCursorsModel }

    Connections {
        target: typeof mapSessionController !== "undefined" ? mapSessionController : null
        function onRoomJoined(roomId, mapDataStr) {
            try {
                var mapData = JSON.parse(mapDataStr);
                if (mapData && mapData.drawings) {
                    root.drawings = mapData.drawings;
                    if (typeof drawingCanvas !== "undefined") drawingCanvas.requestPaint();
                }
            } catch (e) {}
        }
        function onMapUpdated(dataStr) {
            try {
                var date = new Date();
                var h = date.getHours();
                var m = date.getMinutes();
                root.lastSyncTime = (h < 10 ? "0" + h : h) + ":" + (m < 10 ? "0" + m : m);
                
                var data = JSON.parse(dataStr);
                var currentUserId = typeof chatController !== "undefined" ? chatController.currentUserId : "";
                
                if (data.user && data.user.id && data.user.id !== currentUserId) {
                    var cursors = root.remoteCursorsDict;
                    if (data.user.status === null) {
                        delete cursors[data.user.id];
                        for (var i = 0; i < remoteCursorsModel.count; i++) {
                            if (remoteCursorsModel.get(i).userId === data.user.id) {
                                remoteCursorsModel.remove(i);
                                break;
                            }
                        }
                    } else {
                        cursors[data.user.id] = data.user;
                        var found = false;
                        for (var j = 0; j < remoteCursorsModel.count; j++) {
                            if (remoteCursorsModel.get(j).userId === data.user.id) {
                                remoteCursorsModel.setProperty(j, "wx", data.user.status.x);
                                remoteCursorsModel.setProperty(j, "wy", data.user.status.y);
                                remoteCursorsModel.setProperty(j, "nick", data.user.nick || "");
                                remoteCursorsModel.setProperty(j, "avatar", data.user.avatar || "");
                                found = true;
                                break;
                            }
                        }
                        if (!found) {
                            remoteCursorsModel.append({
                                userId: data.user.id,
                                wx: data.user.status.x,
                                wy: data.user.status.y,
                                nick: data.user.nick || "",
                                avatar: data.user.avatar || ""
                            });
                        }
                    }
                    root.remoteCursorsDict = cursors;
                }
                
                if (!root.currentDrawing && data.drawings) {
                    root.drawings = data.drawings;
                    if (typeof drawingCanvas !== "undefined") drawingCanvas.requestPaint();
                }
            } catch (e) {}
        }
        function onUserKicked() {
            kickedPopup.open();
        }
    }
    property int activeThickness: 3
    property bool showToolSettings: false
    property var drawings: [] // stores objects like {type: "brush", color: "red", thickness: 3, points: [{x,y}...]}
    property var currentDrawing: null // currently active drawing while mouse is pressed
    property bool polygonNameDialogVisible: false
    property bool routeNameDialogVisible: false
    property int dashOffset: 0
    
    property var activeUsers: []
    property var historicUsers: []
    property string lastSyncTime: ""
    
    onDrawingsChanged: {
        var hUsers = [];
        for (var i = 0; i < root.drawings.length; i++) {
            var d = root.drawings[i];
            if (d && d.user && hUsers.indexOf(d.user) === -1) {
                hUsers.push(d.user);
            }
        }
        root.historicUsers = hUsers;
    }
    
    onRemoteCursorsDictChanged: {
        var aUsers = [];
        var keys = Object.keys(root.remoteCursorsDict);
        for (var i = 0; i < keys.length; i++) {
            var obj = root.remoteCursorsDict[keys[i]];
            aUsers.push({ id: obj.id, name: keys[i], avatar: obj.avatar });
        }
        root.activeUsers = aUsers;
    }
    
    property bool hasAnimatedDrawings: {
        for (var i = 0; i < root.drawings.length; i++) {
            var d = root.drawings[i];
            if (d && (d.type === "route" || d.type === "parabola")) return true;
        }
        if (root.currentDrawing && (root.currentDrawing.type === "route" || root.currentDrawing.type === "parabola")) return true;
        return false;
    }

    // Timer to animate flowing dashed lines along logistics routes and drawings
    Timer {
        id: lineAnimationTimer
        interval: 35
        running: root.hasAnimatedDrawings
        repeat: true
        onTriggered: {
            root.dashOffset = (root.dashOffset + 1) % 48;
            drawingCanvas.requestPaint();
        }
    }
    
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
    
    function distanceToParabola(px, py, sx, sy, ex, ey) {
        var cx = (sx + ex) / 2;
        var cy = (sy + ey) / 2;
        var dx = ex - sx;
        var dy = ey - sy;
        var ctrlX = cx - dy * 0.3;
        var ctrlY = cy + dx * 0.3;
        
        var minDist = 999999;
        var segments = 10;
        var lastX = sx, lastY = sy;
        for (var st = 1; st <= segments; st++) {
            var t = st / segments;
            var invT = 1 - t;
            var curX = invT * invT * sx + 2 * invT * t * ctrlX + t * t * ex;
            var curY = invT * invT * sy + 2 * invT * t * ctrlY + t * t * ey;
            var dist = distanceToSegment(px, py, lastX, lastY, curX, curY);
            if (dist < minDist) minDist = dist;
            lastX = curX;
            lastY = curY;
        }
        return minDist;
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

    function apiToWorld(apiX, apiY) {
        if (typeof mapController === "undefined" || !mapController) return {x: apiX, y: apiY};
        var wX = (apiX * mapController.mapScale) + mapController.mapOffsetX;
        var wY = (-apiY * mapController.mapScale) + mapController.mapOffsetY;
        return {x: wX, y: wY};
    }
    
    function worldToApi(wX, wY) {
        if (typeof mapController === "undefined" || !mapController) return {x: wX, y: wY};
        var apiX = (wX - mapController.mapOffsetX) / mapController.mapScale;
        var apiY = -(wY - mapController.mapOffsetY) / mapController.mapScale;
        return {x: apiX, y: apiY};
    }

    function getRouteMidpointX(d) {
        if (!d || !d.start || !d.end) return 0;
        var aStart = apiToWorld(d.start.x, d.start.y);
        var aEnd = apiToWorld(d.end.x, d.end.y);
        var cx = (aStart.x + aEnd.x) / 2;
        var cy = (aStart.y + aEnd.y) / 2;
        var dx = aEnd.x - aStart.x;
        var dy = aEnd.y - aStart.y;
        var ctrlX = cx - dy * 0.3;
        var ctrlY = cy + dx * 0.3;
        var midX = 0.25 * aStart.x + 0.5 * ctrlX + 0.25 * aEnd.x;
        var p = worldToCanvas(midX, 0);
        return p.x;
    }

    function getRouteMidpointY(d) {
        if (!d || !d.start || !d.end) return 0;
        var aStart = apiToWorld(d.start.x, d.start.y);
        var aEnd = apiToWorld(d.end.x, d.end.y);
        var cx = (aStart.x + aEnd.x) / 2;
        var cy = (aStart.y + aEnd.y) / 2;
        var dx = aEnd.x - aStart.x;
        var dy = aEnd.y - aStart.y;
        var ctrlX = cx - dy * 0.3;
        var ctrlY = cy + dx * 0.3;
        var midY = 0.25 * aStart.y + 0.5 * ctrlY + 0.25 * aEnd.y;
        var p = worldToCanvas(0, midY);
        return p.y;
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

    StockpileModal {
        id: stockpileModal
        z: 100
    }
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
        
        MapIconsRenderer {
            anchors.fill: parent
            itemsData: typeof mapController !== "undefined" && mapController ? mapController.mapItemsModel : []
            mapScale: typeof mapController !== "undefined" && mapController ? mapController.mapScale : 1
            mapOffsetX: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetX : 0
            mapOffsetY: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetY : 0
            currentZoom: root.currentZoom
            centerX: root.centerX
            centerY: root.centerY
            showResources: root.showResources
            showIcons: root.showIcons
            showStockFilter: root.showStockFilter
            showMainStructures: root.showMainStructures
            
            onItemHovered: function(itemData, hx, hy) {
                if (itemData && itemData.name) {
                    var hasStock = itemData.stock !== undefined && root.showStockFilter;
                    if (!hasStock) {
                        var p = mapToItem(root, hx, hy);
                        globalToolTip.x = p.x + 15;
                        globalToolTip.y = p.y + 15;
                        globalToolTip.text = itemData.name + " (Type: " + (itemData.type !== undefined ? itemData.type : "") + ")";
                        globalToolTip.visible = true;
                        
                        // Hide stock modal hover
                        if (typeof stockpileModal !== "undefined") {
                            stockpileModal.isHoveredMapItem = false;
                        }
                    } else {
                        globalToolTip.visible = false;
                        if (typeof stockpileModal !== "undefined") {
                            stockpileModal.modelData = itemData;
                            var pStock = mapToItem(root, hx, hy);
                            stockpileModal.x = pStock.x + 10;
                            stockpileModal.y = pStock.y - stockpileModal.height / 2;
                            stockpileModal.isHoveredMapItem = true;
                        }
                    }
                } else {
                    globalToolTip.visible = false;
                    if (typeof stockpileModal !== "undefined") {
                        stockpileModal.isHoveredMapItem = false;
                    }
                }
            }
            
            onItemClicked: function(itemData) {
                if (itemData && itemData.name) {
                    var name = itemData.name;
                    var type = itemData.type !== undefined ? itemData.type : 0;
                    console.log("Map icon clicked:", name);
                    
                    var hasStock = itemData.stock !== undefined && root.showStockFilter;
                    if (hasStock && typeof stockpileModal !== "undefined") {
                        stockpileModal.isPinned = !stockpileModal.isPinned;
                    }
                }
            }
        }

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

        // Text rendering moved to MapTextRenderer (outside overlayManager)
    }

    MapTextRenderer {
        anchors.fill: parent
        z: 4 // Above map layers and icons
        itemsData: typeof mapController !== "undefined" && mapController ? mapController.mapTextItemsModel : []
        mapScale: typeof mapController !== "undefined" && mapController ? mapController.mapScale : 1
        mapOffsetX: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetX : 0
        mapOffsetY: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetY : 0
        currentZoom: root.currentZoom
        centerX: root.centerX
        centerY: root.centerY
        showHexNames: root.showHexNames
        showMajorCities: root.showMajorCities
        showMinorCities: root.showMinorCities
    }

    // --- DRAWING CANVAS ---
    AuthErrorOverlay {
        id: authErrorOverlay
        anchors.fill: parent
        z: 9999
    }
    
    ArtilleryModal {
        id: artilleryModal
        x: root.width - width - 20
        y: 80
        visible: false
        z: 100
    }

    Item {
        id: drawingContainer
        anchors.fill: parent
        z: 3 // Above map, below UI filters
        
        ArtilleryOverlay {
            id: artilleryOverlay
            isActive: (root.activeTool === "artillery" || root.artilleryCannon !== null)
            mapController: typeof mapController !== "undefined" ? mapController : null
            currentZoom: root.currentZoom
            mapScale: typeof mapController !== "undefined" && mapController ? mapController.mapScale : 1
            mapOffsetX: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetX : 0
            mapOffsetY: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetY : 0
            
            centerX: drawingCanvas.lastPaintCenterX
            centerY: drawingCanvas.lastPaintCenterY
            
            cannonX: root.artilleryCannon ? root.worldToApi(root.artilleryCannon.x, root.artilleryCannon.y).x : 0
            cannonY: root.artilleryCannon ? root.worldToApi(root.artilleryCannon.x, root.artilleryCannon.y).y : 0
            targetX: root.artilleryTarget ? root.worldToApi(root.artilleryTarget.x, root.artilleryTarget.y).x : 0
            targetY: root.artilleryTarget ? root.worldToApi(root.artilleryTarget.x, root.artilleryTarget.y).y : 0
        }
        
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
                            ctx.font = "bold 14px sans-serif";
                            ctx.textAlign = "center";
                            ctx.textBaseline = "middle";
                            ctx.strokeStyle = "#000000";
                            ctx.lineWidth = 3;
                            ctx.strokeText(d.name, cx, cy);
                            ctx.fillText(d.name, cx, cy);
                            ctx.lineWidth = d.thickness || 3;
                        }
                    } else if (d.type === "route" && d.points && d.points.length > 0) {
                        ctx.beginPath();
                        var rStart = worldToCanvas(d.points[0].x, d.points[0].y);
                        ctx.moveTo(rStart.x, rStart.y);
                        for (var rj = 1; rj < d.points.length; rj++) {
                            var rp = worldToCanvas(d.points[rj].x, d.points[rj].y);
                            ctx.lineTo(rp.x, rp.y);
                        }
                        
                        ctx.save();
                        ctx.strokeStyle = d.color || "#3b82f6";
                        ctx.lineWidth = d.thickness || 4;
                        ctx.setLineDash([8, 6]); // Beautiful dotted/dashed line
                        ctx.lineDashOffset = -root.dashOffset;
                        ctx.stroke();
                        ctx.restore();

                        // Start indicator A (Início) with pulse effect
                        var startPulse = 10 + Math.sin(root.dashOffset * 0.15) * 1.5;
                        ctx.beginPath();
                        ctx.arc(rStart.x, rStart.y, startPulse + 3, 0, 2 * Math.PI);
                        ctx.fillStyle = (d.color || "#3b82f6") === "#ffffff" ? "rgba(255, 255, 255, 0.2)" : "rgba(59, 130, 246, 0.25)";
                        ctx.fill();

                        ctx.beginPath();
                        ctx.arc(rStart.x, rStart.y, 10, 0, 2 * Math.PI);
                        ctx.fillStyle = d.color || "#3b82f6";
                        ctx.fill();
                        ctx.strokeStyle = "#ffffff";
                        ctx.lineWidth = 2;
                        ctx.stroke();

                        ctx.font = "bold 11px sans-serif";
                        ctx.fillStyle = (d.color === "#ffffff" || d.color === "#ffffff" || d.color === "#eab308") ? "#111827" : "#ffffff";
                        ctx.textAlign = "center";
                        ctx.textBaseline = "middle";
                        ctx.fillText("A", rStart.x, rStart.y);

                        // End indicator B (Fim)
                        if (d.points.length > 1) {
                            var rEnd = worldToCanvas(d.points[d.points.length - 1].x, d.points[d.points.length - 1].y);
                            var endPulse = 10 + Math.cos(root.dashOffset * 0.15) * 1.5;
                            ctx.beginPath();
                            ctx.arc(rEnd.x, rEnd.y, endPulse + 3, 0, 2 * Math.PI);
                            ctx.fillStyle = (d.color || "#3b82f6") === "#ffffff" ? "rgba(255, 255, 255, 0.2)" : "rgba(59, 130, 246, 0.25)";
                            ctx.fill();

                            ctx.beginPath();
                            ctx.arc(rEnd.x, rEnd.y, 10, 0, 2 * Math.PI);
                            ctx.fillStyle = d.color || "#3b82f6";
                            ctx.fill();
                            ctx.strokeStyle = "#ffffff";
                            ctx.lineWidth = 2;
                            ctx.stroke();

                            ctx.font = "bold 11px sans-serif";
                            ctx.fillStyle = (d.color === "#ffffff" || d.color === "#ffffff" || d.color === "#eab308") ? "#111827" : "#ffffff";
                            ctx.textAlign = "center";
                            ctx.textBaseline = "middle";
                            ctx.fillText("B", rEnd.x, rEnd.y);
                        }

                        // Draw intermediate nodes for route
                        for (var ri = 1; ri < d.points.length - 1; ri++) {
                            var rNode = worldToCanvas(d.points[ri].x, d.points[ri].y);
                            ctx.beginPath();
                            ctx.arc(rNode.x, rNode.y, 4, 0, 2 * Math.PI);
                            ctx.fillStyle = "#ffffff";
                            ctx.fill();
                            ctx.strokeStyle = d.color || "#3b82f6";
                            ctx.lineWidth = 1.5;
                            ctx.stroke();
                        }

                        // Draw Route Name at center
                        if (d.name) {
                            var rcx = 0, rcy = 0;
                            for (var rm = 0; rm < d.points.length; rm++) {
                                var rptm = worldToCanvas(d.points[rm].x, d.points[rm].y);
                                rcx += rptm.x;
                                rcy += rptm.y;
                            }
                            rcx /= d.points.length;
                            rcy /= d.points.length;
                            
                            ctx.font = "bold 12px sans-serif";
                            var txtWidth = ctx.measureText(d.name).width;
                            ctx.fillStyle = "rgba(10, 15, 24, 0.85)";
                            ctx.fillRect(rcx - txtWidth / 2 - 8, rcy - 10, txtWidth + 16, 20);
                            ctx.strokeStyle = d.color || "#3b82f6";
                            ctx.lineWidth = 1;
                            ctx.strokeRect(rcx - txtWidth / 2 - 8, rcy - 10, txtWidth + 16, 20);

                            ctx.fillStyle = "#ffffff";
                            ctx.textAlign = "center";
                            ctx.textBaseline = "middle";
                            ctx.fillText(d.name, rcx, rcy);
                        }
                    } else if (d.type === "artillery" && d.start && d.end) {
                        var aStart = root.apiToWorld(d.start.x, d.start.y);
                        var aEnd = root.apiToWorld(d.end.x, d.end.y);
                        var aP1 = worldToCanvas(aStart.x, aStart.y);
                        var aP2 = worldToCanvas(aEnd.x, aEnd.y);
                        
                        ctx.beginPath();
                        ctx.moveTo(aP1.x, aP1.y);
                        ctx.lineTo(aP2.x, aP2.y);
                        ctx.strokeStyle = d.color || "#ef4444";
                        ctx.lineWidth = d.thickness || 2;
                        ctx.setLineDash([5, 5]);
                        ctx.stroke();
                        ctx.setLineDash([]);
                        
                        ctx.beginPath();
                        ctx.arc(aP2.x, aP2.y, 8, 0, 2 * Math.PI);
                        ctx.stroke();
                        ctx.beginPath();
                        ctx.moveTo(aP2.x - 12, aP2.y); ctx.lineTo(aP2.x + 12, aP2.y);
                        ctx.moveTo(aP2.x, aP2.y - 12); ctx.lineTo(aP2.x, aP2.y + 12);
                        ctx.stroke();
                        
                        if (d.info) {
                            var aCx = (aP1.x + aP2.x) / 2;
                            var aCy = (aP1.y + aP2.y) / 2;
                            ctx.font = "bold 13px sans-serif";
                            var aTxtW = ctx.measureText(d.info).width;
                            ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
                            ctx.fillRect(aCx - aTxtW / 2 - 4, aCy - 10, aTxtW + 8, 20);
                            ctx.fillStyle = "#ffffff";
                            ctx.textAlign = "center";
                            ctx.textBaseline = "middle";
                            ctx.fillText(d.info, aCx, aCy);
                        }
                    } else if (d.type === "parabola" && d.start && d.end) {
                        var aStart = apiToWorld(d.start.x, d.start.y);
                        var aEnd = apiToWorld(d.end.x, d.end.y);
                        var sP = worldToCanvas(aStart.x, aStart.y);
                        var eP = worldToCanvas(aEnd.x, aEnd.y);
                        
                        var cx = (sP.x + eP.x) / 2;
                        var cy = (sP.y + eP.y) / 2;
                        var dx = eP.x - sP.x;
                        var dy = eP.y - sP.y;
                        
                        // Increase curve factor for a nicer arc
                        var ctrlX = cx - dy * 0.3;
                        var ctrlY = cy + dx * 0.3;
                        
                        var isHovered = false;
                        if (root.logisticsHoveredRoute && root.logisticsHoveredRoute.start && root.logisticsHoveredRoute.end) {
                            if (Math.abs(root.logisticsHoveredRoute.start.x - d.start.x) < 0.1 && 
                                Math.abs(root.logisticsHoveredRoute.end.x - d.end.x) < 0.1) {
                                isHovered = true;
                            }
                        }

                        // 1. Draw glowing background path
                        ctx.beginPath();
                        ctx.moveTo(sP.x, sP.y);
                        ctx.quadraticCurveTo(ctrlX, ctrlY, eP.x, eP.y);
                        ctx.lineWidth = isHovered ? 10 : 6;
                        ctx.strokeStyle = isHovered ? "rgba(234, 179, 8, 0.35)" : "rgba(59, 130, 246, 0.3)";
                        ctx.stroke();

                        // 2. Draw modern dotted foreground path with animated flow
                        ctx.beginPath();
                        ctx.moveTo(sP.x, sP.y);
                        ctx.quadraticCurveTo(ctrlX, ctrlY, eP.x, eP.y);
                        ctx.lineWidth = isHovered ? 4.5 : 2.5;
                        ctx.strokeStyle = isHovered ? "#eab308" : String(d.color || "#3b82f6");
                        ctx.setLineDash([8, 6]);
                        ctx.lineDashOffset = -root.dashOffset;
                        ctx.stroke();
                        ctx.setLineDash([]);
                        ctx.lineDashOffset = 0;
                        
                        // 3. Draw origin waypoint (circle with an inner dot, matching route color)
                        ctx.beginPath();
                        ctx.arc(sP.x, sP.y, 7, 0, 2 * Math.PI);
                        ctx.fillStyle = isHovered ? "#eab308" : String(d.color || "#3b82f6");
                        ctx.fill();
                        ctx.strokeStyle = "#ffffff";
                        ctx.lineWidth = 1.5;
                        ctx.stroke();
                        
                        ctx.beginPath();
                        ctx.arc(sP.x, sP.y, 2.5, 0, 2 * Math.PI);
                        ctx.fillStyle = "#ffffff";
                        ctx.fill();
                        
                        // 4. Draw sleek modern arrowhead at eP
                        var headlen = 14 + (d.thickness || 4);
                        var angle = Math.atan2(eP.y - ctrlY, eP.x - ctrlX);
                        ctx.fillStyle = isHovered ? "#eab308" : String(d.color || "#3b82f6");
                        ctx.beginPath();
                        ctx.moveTo(eP.x, eP.y);
                        ctx.lineTo(eP.x - headlen * Math.cos(angle - Math.PI / 6), eP.y - headlen * Math.sin(angle - Math.PI / 6));
                        ctx.lineTo(eP.x - headlen * Math.cos(angle + Math.PI / 6), eP.y - headlen * Math.sin(angle + Math.PI / 6));
                        ctx.closePath();
                        ctx.fill();
                        
                        ctx.strokeStyle = "#ffffff";
                        ctx.lineWidth = 1.5;
                        ctx.stroke();
                    }
                } // End of allDrawings loop
            }
        }

        // High-fidelity QML overlays for Remote Cursors
        Repeater {
            model: remoteCursorsModel
            delegate: Item {
                x: (model.wx * Math.pow(2, root.currentZoom)) - root.centerX + (root.width / 2)
                y: (model.wy * Math.pow(2, root.currentZoom)) - root.centerY + (root.height / 2)
                z: 200 // On top of canvas

                // Avatar container
                Rectangle {
                    width: 40
                    height: 40
                    radius: 20
                    color: "#111827"
                    border.color: "#3b82f6"
                    border.width: 2
                    anchors.centerIn: parent
                    clip: true
                    
                    Image {
                        anchors.fill: parent
                        anchors.margins: 2 // space for border
                        source: model.avatar || ""
                        fillMode: Image.PreserveAspectCrop
                        visible: model.avatar !== ""
                    }
                    
                    Text {
                        anchors.centerIn: parent
                        text: model.nick ? model.nick.substring(0,1).toUpperCase() : "?"
                        color: "#ffffff"
                        font.bold: true
                        font.pixelSize: 18
                        visible: model.avatar === ""
                    }
                }
                
                // Name Tag
                Rectangle {
                    anchors.top: parent.verticalCenter
                    anchors.topMargin: 24
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: "#d9111827"
                    radius: 4
                    border.color: "#3b82f6"
                    border.width: 1
                    width: nameText.implicitWidth + 12
                    height: nameText.implicitHeight + 6
                    
                    Text {
                        id: nameText
                        anchors.centerIn: parent
                        text: model.nick
                        color: "#ffffff"
                        font.pixelSize: 11
                        font.bold: true
                    }
                }
            }
        }

        // High-fidelity QML overlays for cargo items on logistics routes
        Repeater {
            model: root.drawings
            delegate: Item {
                id: cargoCardWrapper
                visible: modelData.type === "parabola" && modelData.cargo && modelData.cargo.length > 0
                
                // Position centered at the curve's peak
                anchors.horizontalCenter: parent.left
                anchors.horizontalCenterOffset: root.getRouteMidpointX(modelData)
                anchors.verticalCenter: parent.top
                anchors.verticalCenterOffset: root.getRouteMidpointY(modelData)
                
                Rectangle {
                    anchors.centerIn: parent
                    implicitWidth: cargoRow.implicitWidth + 24
                    implicitHeight: 28
                    radius: 14
                    color: "#f00f172a" // Sleek slate 900 (rgba(15, 23, 42, 0.94))
                    border.width: 1.5
                    border.color: (root.logisticsHoveredRoute && root.logisticsHoveredRoute.start && root.logisticsHoveredRoute.end && 
                                   Math.abs(root.logisticsHoveredRoute.start.x - modelData.start.x) < 0.1 && 
                                   Math.abs(root.logisticsHoveredRoute.end.x - modelData.end.x) < 0.1) ? "#eab308" : String(modelData.color || "#3b82f6")
                    
                    MultiEffect {
                        source: parent
                        anchors.fill: parent
                        shadowEnabled: true
                        shadowOpacity: 0.4
                        shadowBlur: 0.8
                        shadowVerticalOffset: 2
                        shadowColor: "black"
                    }
                    
                    Row {
                        id: cargoRow
                        anchors.centerIn: parent
                        spacing: 8
                        
                        Repeater {
                            model: modelData.cargo
                            delegate: Row {
                                spacing: 4
                                anchors.verticalCenter: parent.verticalCenter
                                
                                Text {
                                    text: "•"
                                    color: "#66ffffff"
                                    font.pixelSize: 12
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: index > 0
                                }
                                
                                Image {
                                    source: modelData.icon || ""
                                    width: 16
                                    height: 16
                                    fillMode: Image.PreserveAspectFit
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: source !== ""
                                    
                                    // Fallback if image fails to load or empty
                                    onStatusChanged: {
                                        if (status === Image.Error) {
                                            visible = false;
                                        }
                                    }
                                }
                                
                                Text {
                                    text: modelData.qty + "x " + modelData.name
                                    color: "white"
                                    font.bold: true
                                    font.pixelSize: 11
                                    font.family: "Segoe UI"
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }
                    }
                }
            }
        }

        // Vehicles layer
        Repeater {
            model: root.drawings
            delegate: Item {
                id: vehItem
                visible: modelData.type === "vehicle"
                
                property real wx: modelData.x ? modelData.x : 0
                property real wy: modelData.y ? modelData.y : 0
                
                x: (wx * Math.pow(2, root.currentZoom)) - root.centerX + (root.width / 2) - width/2
                y: (wy * Math.pow(2, root.currentZoom)) - root.centerY + (root.height / 2) - height/2
                z: root.selectedVehicleIndex === index ? 155 : 150
                
                width: vehColumn.implicitWidth
                height: vehColumn.implicitHeight
                
                rotation: root.selectedVehicleIndex === index ? root.liveVehicleRotation : (modelData.rotation || 0)
                
                Column {
                    id: vehColumn
                    anchors.centerIn: parent
                    spacing: 4
                    Image {
                        source: typeof appController !== "undefined" ? appController.assetUrl("img/map-layer/" + (modelData.image || "Blacksteele.png")) : "file:///c:/Users/ryanl/OneDrive/Desktop/aplicativo/img/map-layer/" + (modelData.image || "Blacksteele.png")
                        
                        property real computedScale: root.selectedVehicleIndex === index ? root.liveVehicleScale : (modelData.scale || 1.0)
                        property real zoomFactor: Math.pow(2, root.currentZoom - 2)
                        
                        width: implicitWidth * 0.2 * computedScale * zoomFactor
                        height: implicitHeight * 0.2 * computedScale * zoomFactor
                        
                        anchors.horizontalCenter: parent.horizontalCenter
                        fillMode: Image.PreserveAspectFit
                    }
                    Text {
                        text: root.selectedVehicleIndex === index ? root.liveVehicleName : (modelData.name || "")
                        color: "white"
                        font.bold: true
                        font.pixelSize: 14
                        style: Text.Outline
                        styleColor: "black"
                        anchors.horizontalCenter: parent.horizontalCenter
                        visible: text !== ""
                    }
                }
                
                MouseArea {
                    anchors.fill: parent
                    drag.target: null
                    property real startMouseWorldX
                    property real startMouseWorldY
                    property real startWx
                    property real startWy
                    onPressed: function(mouse) {
                        root.selectedVehicleIndex = index;
                        root.liveVehicleRotation = modelData.rotation || 0;
                        root.liveVehicleScale = modelData.scale || 1.0;
                        root.liveVehicleName = modelData.name || "";
                        
                        var globalMouse = root.mapFromItem(vehItem, mouse.x, mouse.y);
                        startMouseWorldX = globalMouse.x;
                        startMouseWorldY = globalMouse.y;
                        startWx = vehItem.wx;
                        startWy = vehItem.wy;
                    }
                    onPositionChanged: function(mouse) {
                        if (pressed) {
                            var globalMouse = root.mapFromItem(vehItem, mouse.x, mouse.y);
                            var dx = globalMouse.x - startMouseWorldX;
                            var dy = globalMouse.y - startMouseWorldY;
                            vehItem.wx = startWx + (dx / Math.pow(2, root.currentZoom));
                            vehItem.wy = startWy + (dy / Math.pow(2, root.currentZoom));
                        }
                    }
                    onReleased: function(mouse) {
                        if (startWx !== vehItem.wx || startWy !== vehItem.wy) {
                            var newDrawings = root.drawings.slice();
                            newDrawings[index].x = vehItem.wx;
                            newDrawings[index].y = vehItem.wy;
                            root.drawings = newDrawings;
                        }
                    }
                    cursorShape: Qt.PointingHandCursor
                }
                
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: -8
                    color: "transparent"
                    border.color: "#eab308"
                    border.width: 2
                    radius: 4
                    visible: root.selectedVehicleIndex === index
                    
                    Rectangle {
                        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: -10
                        width: 20; height: 20; radius: 10; color: "#ef4444"
                        Text { anchors.centerIn: parent; text: "×"; color: "white"; font.bold: true; font.pixelSize: 14 }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                var newDrawings = root.drawings.slice();
                                newDrawings.splice(index, 1);
                                root.drawings = newDrawings;
                                root.selectedVehicleIndex = -1;
                                drawingCanvas.requestPaint();
                            }
                        }
                    }
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
                text: root.tr("map.filter.main_structures", "Estruturas Principais")
                checked: root.showMainStructures
                onCheckedChanged: root.showMainStructures = checked
            }
            StyledCheckBox { 
                text: root.tr("map.filter.icons", "Estruturas Secundárias")
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

    HoverHandler {
        id: globalHoverTracker
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
                } else if (d.type === "brush" || d.type === "route") {
                    for (var j = 0; j < d.points.length - 1; j++) {
                        var dist = distanceToSegment(wp.x, wp.y, d.points[j].x, d.points[j].y, d.points[j+1].x, d.points[j+1].y);
                        if (dist <= threshold + (d.thickness || 3) / Math.pow(2, root.currentZoom)) {
                            hit = true; break;
                        }
                    }
                } else if (d.type === "arrow" || d.type === "artillery") {
                    var dist2 = distanceToSegment(wp.x, wp.y, d.start.x, d.start.y, d.end.x, d.end.y);
                    if (dist2 <= threshold + (d.thickness || 3) / Math.pow(2, root.currentZoom)) {
                        hit = true;
                    }
                } else if (d.type === "parabola") {
                    var sWp = apiToWorld(d.start.x, d.start.y);
                    var eWp = apiToWorld(d.end.x, d.end.y);
                    var pDist = distanceToParabola(wp.x, wp.y, sWp.x, sWp.y, eWp.x, eWp.y);
                    if (pDist <= threshold + (d.thickness || 3) / Math.pow(2, root.currentZoom)) {
                        hit = true;
                    }
                } else if (d.type === "vehicle") {
                    var distVeh = Math.sqrt(Math.pow(wp.x - d.x, 2) + Math.pow(wp.y - d.y, 2));
                    if (distVeh <= (30 * (d.scale || 1.0)) / Math.pow(2, root.currentZoom)) {
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
            root.wasEditingOnPress = (root.selectedVehicleIndex !== -1);
            root.selectedVehicleIndex = -1;
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
                var cUserBrush = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                root.currentDrawing = { type: "brush", color: root.activeColor, thickness: root.activeThickness, points: [wp], user: cUserBrush };
                drawingCanvas.requestPaint();
            } else if (root.activeTool === "arrow") {
                var wp2 = screenToWorld(mouse.x, mouse.y);
                var cUserArrow = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                root.currentDrawing = { type: "arrow", color: root.activeColor, thickness: root.activeThickness, start: wp2, end: wp2, user: cUserArrow };
                drawingCanvas.requestPaint();
            } else if (root.activeTool === "polygon" || root.activeTool === "route" || root.activeTool === "vehicle") {
                cursorShape = Qt.ClosedHandCursor; // Will reset to cross on release if no pan
            } else if (root.activeTool === "eraser") {
                eraseAt(mouse.x, mouse.y);
            }
        }
        
        onReleased: function(mouse) {
            isDragging = false;
            if (root.activeTool === "pan") {
                cursorShape = Qt.OpenHandCursor;
            } else if (root.activeTool === "polygon") {
                cursorShape = Qt.CrossCursor;
                if (!didPan && !root.polygonNameDialogVisible) {
                    var wp = screenToWorld(mouse.x, mouse.y);
                    if (!root.currentDrawing || root.currentDrawing.type !== "polygon") {
                        var cUserPoly = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                        root.currentDrawing = { type: "polygon", color: root.activeColor, thickness: root.activeThickness, points: [wp], user: cUserPoly };
                    } else {
                        var poly = Object.assign({}, root.currentDrawing);
                        poly.points = poly.points.slice();
                        poly.points.push(wp);
                        root.currentDrawing = poly;
                    }
                    drawingCanvas.requestPaint();
                }
            } else if (root.activeTool === "route") {
                cursorShape = Qt.CrossCursor;
                if (!didPan && !root.routeNameDialogVisible) {
                    var wpRoute = screenToWorld(mouse.x, mouse.y);
                    if (!root.currentDrawing || root.currentDrawing.type !== "route") {
                        var cUserRoute = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                        root.currentDrawing = { type: "route", color: root.activeColor, thickness: root.activeThickness, points: [wpRoute], user: cUserRoute };
                    } else {
                        var route = Object.assign({}, root.currentDrawing);
                        route.points = route.points.slice();
                        route.points.push(wpRoute);
                        root.currentDrawing = route;
                    }
                    drawingCanvas.requestPaint();
                }
            } else if (root.activeTool === "vehicle") {
                cursorShape = Qt.CrossCursor;
                if (!didPan && !root.wasEditingOnPress) {
                    var wpVeh = screenToWorld(mouse.x, mouse.y);
                    var cUserVeh = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                    var newDrawings = root.drawings.slice();
                    newDrawings.push({
                        type: "vehicle",
                        user: cUserVeh,
                        x: wpVeh.x,
                        y: wpVeh.y,
                        image: root.activeVehicleImage,
                        rotation: root.activeVehicleRotation,
                        scale: root.activeVehicleScale * (1.0 / Math.pow(2, root.currentZoom - 2)),
                        name: root.activeVehicleName
                    });
                    root.drawings = newDrawings;
                    drawingCanvas.requestPaint();
                }
            } else if (root.activeTool === "artillery") {
                cursorShape = Qt.CrossCursor;
                console.log("MapView: artillery clicked! didPan:", didPan, "mouse:", mouse.x, mouse.y);
                if (!didPan) {
                    var wpArt = screenToWorld(mouse.x, mouse.y);
                    console.log("MapView: wpArt calculated:", wpArt.x, wpArt.y);
                    if (root.artilleryStep !== 1) {
                        root.artilleryCannon = wpArt;
                        root.artilleryTarget = wpArt;
                        root.artilleryStep = 1;
                        console.log("MapView: step 1, cannon set!");
                    } else {
                        root.artilleryTarget = wpArt;
                        
                        // Sync to drawing log
                        var wCannonAPI = root.worldToApi(root.artilleryCannon.x, root.artilleryCannon.y);
                        var wTargetAPI = root.worldToApi(wpArt.x, wpArt.y);
                        
                        // calculateArtillery expects API coordinates (which python engine calls World coordinates)
                        var mathRes = typeof mapController !== "undefined" && mapController ? mapController.calculateArtillery(wCannonAPI.x, wCannonAPI.y, wTargetAPI.x, wTargetAPI.y) : null;
                        var azm = mathRes ? (mathRes.bearing || 0) : 0;
                        var dist = mathRes ? (mathRes.distance_meters || 0) : 0;
                        var infoText = "AZM: " + Math.round(azm) + "° | DIST: " + Math.round(dist) + "m";
                        
                        var cUserArt = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                        var newArt = { 
                            type: "artillery", 
                            color: root.activeColor, 
                            thickness: root.activeThickness, 
                            start: wCannonAPI, 
                            end: wTargetAPI, 
                            user: cUserArt,
                            info: infoText
                        };
                        var nds = root.drawings.slice();
                        nds.push(newArt);
                        root.drawings = nds;
                        drawingCanvas.requestPaint();
                        
                        // Keep step 2 so overlay stays visible
                        root.artilleryStep = 2;
                        console.log("MapView: step 2, target set and synced to log!");
                    }
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
            if (root.currentDrawing && root.activeTool !== "polygon" && root.activeTool !== "route") {
                var newDrawings = root.drawings.slice();
                newDrawings.push(root.currentDrawing);
                root.drawings = newDrawings;
                root.currentDrawing = null;
            }
        }
        
        onPositionChanged: function(mouse) {
            if (isDragging) {
                if (root.activeTool === "pan" || root.activeTool === "polygon" || root.activeTool === "route" || root.activeTool === "vehicle") {
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
                if (root.activeTool === "artillery" && root.artilleryStep === 1) {
                    root.artilleryTarget = screenToWorld(mouse.x, mouse.y);
                }

                if (root.logisticsRoutes.length > 0) {
                    var hwp = screenToWorld(mouse.x, mouse.y);
                    var foundHover = null;
                    for (var r = 0; r < root.logisticsRoutes.length; r++) {
                        var route = root.logisticsRoutes[r];
                        var rdist = distanceToParabola(hwp.x, hwp.y, apiToWorld(route.start.x, route.start.y).x, apiToWorld(route.start.x, route.start.y).y, apiToWorld(route.end.x, route.end.y).x, apiToWorld(route.end.x, route.end.y).y);
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
                
                // Hover for drawings
                if (!isDragging && root.drawings) {
                    var hoverWp = screenToWorld(mouse.x, mouse.y);
                    var hoverThreshold = 15 / Math.pow(2, root.currentZoom);
                    var foundHoverDrawing = null;
                    
                    for (var i = root.drawings.length - 1; i >= 0; i--) {
                        var d = root.drawings[i];
                        var hit = false;
                        if (d.type === "polygon") {
                            hit = isPointInPolygon(hoverWp.x, hoverWp.y, d.points);
                        } else if (d.type === "brush" || d.type === "route") {
                            for (var j = 0; j < d.points.length - 1; j++) {
                                var segmentDist = distanceToSegment(hoverWp.x, hoverWp.y, d.points[j].x, d.points[j].y, d.points[j+1].x, d.points[j+1].y);
                                if (segmentDist <= hoverThreshold + (d.thickness || 3) / Math.pow(2, root.currentZoom)) {
                                    hit = true; break;
                                }
                            }
                        } else if (d.type === "arrow" || d.type === "artillery") {
                            var arrowDist = distanceToSegment(hoverWp.x, hoverWp.y, d.start.x, d.start.y, d.end.x, d.end.y);
                            if (arrowDist <= hoverThreshold + (d.thickness || 3) / Math.pow(2, root.currentZoom)) {
                                hit = true;
                            }
                        } else if (d.type === "vehicle") {
                            var vDist = Math.sqrt(Math.pow(hoverWp.x - d.x, 2) + Math.pow(hoverWp.y - d.y, 2));
                            if (vDist <= (30 * (d.scale || 1.0)) / Math.pow(2, root.currentZoom)) {
                                hit = true;
                            }
                        }
                        
                        if (hit) {
                            foundHoverDrawing = d;
                            break;
                        }
                    }
                    
                    if (foundHoverDrawing && foundHoverDrawing.user) {
                        drawingHoverTooltip.tooltipText = foundHoverDrawing.user;
                        drawingHoverTooltip.x = mouse.x + 15;
                        drawingHoverTooltip.y = mouse.y + 15;
                        drawingHoverTooltip.visible = true;
                    } else {
                        drawingHoverTooltip.visible = false;
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

            // Route Tool
            Rectangle {
                width: 36
                height: 36
                radius: 18
                color: root.activeTool === "route" ? settingsController.accentColor : "transparent"
                border.color: root.activeTool === "route" ? settingsController.accentColor : settingsController.borderColor
                Text {
                    anchors.centerIn: parent
                    text: "🛣️"
                    font.pixelSize: 18
                    color: root.activeTool === "route" ? "white" : settingsController.textColor
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (root.activeTool === "route") {
                            root.showToolSettings = !root.showToolSettings;
                        } else {
                            if (root.currentDrawing && root.currentDrawing.type === "route") {
                                root.currentDrawing = null; // discard if changing tool
                            }
                            root.activeTool = "route";
                            root.showToolSettings = true;
                        }
                    }
                    cursorShape: Qt.PointingHandCursor
                }
            }
            
            // Artillery Tool
            Rectangle {
                width: 36
                height: 36
                radius: 18
                color: root.activeTool === "artillery" ? settingsController.accentColor : "transparent"
                border.color: root.activeTool === "artillery" ? settingsController.accentColor : settingsController.borderColor
                Text {
                    anchors.centerIn: parent
                    text: "🎯"
                    font.pixelSize: 18
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (root.currentDrawing) root.currentDrawing = null;
                        
                        if (root.activeTool === "artillery") {
                            root.activeTool = "pan";
                            artilleryModal.visible = false;
                        } else {
                            root.activeTool = "artillery";
                            artilleryModal.visible = true;
                            root.showToolSettings = false;
                        }
                    }
                    cursorShape: Qt.PointingHandCursor
                }
            }

            // Vehicle Tool
            Rectangle {
                width: 36
                height: 36
                radius: 18
                color: root.activeTool === "vehicle" ? settingsController.accentColor : "transparent"
                border.color: root.activeTool === "vehicle" ? settingsController.accentColor : settingsController.borderColor
                Text {
                    anchors.centerIn: parent
                    text: "🚢"
                    font.pixelSize: 18
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (root.activeTool === "vehicle") {
                            root.showToolSettings = !root.showToolSettings;
                        } else {
                            if (root.currentDrawing) root.currentDrawing = null;
                            root.activeTool = "vehicle";
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
        visible: (root.showToolSettings && (root.activeTool === "brush" || root.activeTool === "arrow" || root.activeTool === "polygon" || root.activeTool === "route" || root.activeTool === "eraser" || root.activeTool === "vehicle")) || root.selectedVehicleIndex !== -1
        anchors.bottom: drawingToolbar.top
        anchors.bottomMargin: 12
        anchors.horizontalCenter: parent.horizontalCenter
        width: (root.selectedVehicleIndex !== -1 || root.activeTool === "vehicle") ? 320 : 240
        height: root.selectedVehicleIndex !== -1 ? 260 : (root.activeTool === "eraser" ? 80 : (root.activeTool === "vehicle" ? 380 : 120))
        radius: 12
        color: settingsController.surfaceColor
        border.color: settingsController.borderColor
        border.width: 1
        z: 100
        
        // Block clicks from propagating to map
        MouseArea { anchors.fill: parent }

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
            visible: root.activeTool !== "eraser" && root.activeTool !== "vehicle"
            
            Text {
                text: root.activeTool === "brush" ? "Espessura e Cor do Pincel" : (root.activeTool === "arrow" ? "Espessura e Cor da Seta" : (root.activeTool === "route" ? "Espessura e Cor da Rota" : "Espessura e Cor da Área"))
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
        
        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 16
            visible: root.selectedVehicleIndex !== -1
            
            RowLayout {
                width: parent.width
                Text {
                    text: "Editar Embarcação"
                    color: settingsController.textColor
                    font.bold: true
                    font.pixelSize: 14
                    Layout.fillWidth: true
                }
            }
            
            Column {
                width: parent.width
                spacing: 4
                Text { text: "Rotação"; color: settingsController.mutedTextColor; font.pixelSize: 11; font.bold: true }
                Slider {
                    width: parent.width
                    from: 0; to: 360; stepSize: 1
                    value: root.liveVehicleRotation
                    onValueChanged: {
                        if (root.selectedVehicleIndex !== -1) {
                            root.liveVehicleRotation = value;
                        }
                    }
                    onPressedChanged: {
                        if (!pressed && root.selectedVehicleIndex !== -1 && root.drawings[root.selectedVehicleIndex]) {
                            if (root.drawings[root.selectedVehicleIndex].rotation !== root.liveVehicleRotation) {
                                var newDrawings = root.drawings.slice();
                                newDrawings[root.selectedVehicleIndex].rotation = root.liveVehicleRotation;
                                root.drawings = newDrawings;
                            }
                        }
                    }
                }
            }
            
            Column {
                width: parent.width
                spacing: 4
                Text { text: "Tamanho"; color: settingsController.mutedTextColor; font.pixelSize: 11; font.bold: true }
                Slider {
                    width: parent.width
                    from: 0.05; to: 3.0; stepSize: 0.05
                    value: root.liveVehicleScale
                    onValueChanged: {
                        if (root.selectedVehicleIndex !== -1) {
                            root.liveVehicleScale = value;
                        }
                    }
                    onPressedChanged: {
                        if (!pressed && root.selectedVehicleIndex !== -1 && root.drawings[root.selectedVehicleIndex]) {
                            if (root.drawings[root.selectedVehicleIndex].scale !== root.liveVehicleScale) {
                                var newDrawings = root.drawings.slice();
                                newDrawings[root.selectedVehicleIndex].scale = root.liveVehicleScale;
                                root.drawings = newDrawings;
                            }
                        }
                    }
                }
            }
            
            Column {
                width: parent.width
                spacing: 4
                Text { text: "Nome da Embarcação"; color: settingsController.mutedTextColor; font.pixelSize: 11; font.bold: true }
                TextField {
                    width: parent.width
                    text: root.liveVehicleName
                    font.pixelSize: 12
                    onTextEdited: {
                        root.liveVehicleName = text;
                    }
                    onEditingFinished: {
                        if (root.selectedVehicleIndex !== -1 && root.drawings[root.selectedVehicleIndex]) {
                            if (root.drawings[root.selectedVehicleIndex].name !== root.liveVehicleName) {
                                var newDrawings = root.drawings.slice();
                                newDrawings[root.selectedVehicleIndex].name = root.liveVehicleName;
                                root.drawings = newDrawings;
                            }
                        }
                    }
                    color: settingsController.textColor
                    background: Rectangle { color: settingsController.backgroundColor; border.color: settingsController.borderColor; border.width: 1; radius: 6 }
                }
            }
        }
        
        Column {
            id: vehicleSearchCol
            anchors.fill: parent
            anchors.margins: 16
            spacing: 16
            visible: root.activeTool === "vehicle" && root.selectedVehicleIndex === -1
            
            property string searchText: ""
            
            Text {
                text: "Catálogo de Embarcações"
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 14
            }
            
            TextField {
                width: parent.width
                placeholderText: "Buscar embarcação..."
                color: settingsController.textColor
                font.pixelSize: 12
                background: Rectangle { color: settingsController.backgroundColor; border.color: settingsController.borderColor; border.width: 1; radius: 6 }
                onTextEdited: vehicleSearchCol.searchText = text.toLowerCase()
            }
            
            ScrollView {
                width: parent.width
                height: 290
                clip: true
                
                Grid {
                    columns: 3
                    spacing: 12
                    
                    property var allItems: {
                        if (typeof VehiclesData === "undefined" || !VehiclesData.data.categories || VehiclesData.data.categories.length === 0) return [];
                        var items = VehiclesData.data.categories[0].items;
                        var res = [];
                        for (var i = 0; i < items.length; i++) {
                            if (vehicleSearchCol.searchText === "" || items[i].name.toLowerCase().indexOf(vehicleSearchCol.searchText) !== -1) {
                                res.push(items[i]);
                            }
                        }
                        return res;
                    }
                    
                    Repeater {
                        model: parent.allItems
                        delegate: Rectangle {
                            width: 80
                            height: 88
                            radius: 8
                            color: settingsController.backgroundColor
                            border.color: root.activeVehicleImage === modelData.image ? settingsController.accentColor : settingsController.borderColor
                            border.width: root.activeVehicleImage === modelData.image ? 2 : 1
                            
                            Rectangle {
                                anchors.fill: parent
                                radius: 8
                                color: "white"
                                opacity: mouseArea.containsMouse ? 0.05 : 0.0
                                Behavior on opacity { NumberAnimation { duration: 150 } }
                            }
                            
                            Column {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 4
                                
                                Item {
                                    width: parent.width
                                    height: 50
                                    Image {
                                        anchors.centerIn: parent
                                        source: typeof appController !== "undefined" ? appController.assetUrl("img/map-layer/" + modelData.image) : "file:///c:/Users/ryanl/OneDrive/Desktop/aplicativo/img/map-layer/" + modelData.image
                                        width: parent.width
                                        height: parent.height
                                        fillMode: Image.PreserveAspectFit
                                        smooth: true
                                        mipmap: true
                                    }
                                }
                                
                                Text {
                                    text: modelData.name
                                    color: root.activeVehicleImage === modelData.image ? settingsController.accentColor : settingsController.textColor
                                    font.pixelSize: 10
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    width: parent.width
                                    elide: Text.ElideRight
                                }
                            }
                            
                            Rectangle {
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.margins: 6
                                width: 14
                                height: 14
                                radius: 3
                                color: modelData.faction === "w" ? "#2a5b8c" : (modelData.faction === "c" ? "#5a7a50" : "#888888")
                                visible: modelData.faction !== undefined
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.faction ? modelData.faction.toUpperCase() : ""
                                    color: "white"
                                    font.pixelSize: 9
                                    font.bold: true
                                }
                            }
                            
                            MouseArea {
                                id: mouseArea
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.activeVehicleImage = modelData.image;
                                    root.activeVehicleName = modelData.name;
                                }
                            }
                        }
                    }
                }
            }
        }
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

    Rectangle {
        visible: root.activeTool === "route" && root.currentDrawing && root.currentDrawing.type === "route" && root.currentDrawing.points.length >= 2 && !root.routeNameDialogVisible
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
            text: "✅ Finalizar Rota"
            color: "white"
            font.bold: true
            font.pixelSize: 13
        }
        
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                root.routeNameDialogVisible = true;
                routeNameInput.forceActiveFocus();
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

    // --- ROUTE NAME MODAL ---
    Rectangle {
        id: routeNameModal
        visible: root.routeNameDialogVisible
        anchors.centerIn: parent
        width: 320
        height: 250
        radius: 8
        color: settingsController.surfaceColor
        border.color: settingsController.borderColor
        border.width: 1
        z: 200
        
        MultiEffect {
            source: routeNameModal
            anchors.fill: routeNameModal
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
                text: "Configurar Rota"
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 16
                Layout.fillWidth: true
            }
            
            TextField {
                id: routeNameInput
                Layout.fillWidth: true
                placeholderText: "Ex: Rota de Abastecimento Norte"
                color: settingsController.textColor
                background: Rectangle {
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor
                    border.width: 1
                    radius: 4
                }
                onAccepted: finishRouteBtn.clicked()
            }
            
            Text {
                text: "Selecione a Cor"
                color: settingsController.mutedTextColor
                font.pixelSize: 11
                font.bold: true
            }
            
            Row {
                spacing: 8
                Layout.alignment: Qt.AlignHCenter
                Repeater {
                    model: ["#ef4444", "#3b82f6", "#22c55e", "#eab308", "#a855f7", "#ff7849"]
                    delegate: Rectangle {
                        width: 24
                        height: 24
                        radius: 12
                        color: modelData
                        border.color: root.activeColor === modelData ? settingsController.accentColor : "#888888"
                        border.width: root.activeColor === modelData ? 3 : 1
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                root.activeColor = modelData;
                                if (root.currentDrawing) {
                                    root.currentDrawing.color = modelData;
                                    drawingCanvas.requestPaint();
                                }
                            }
                            cursorShape: Qt.PointingHandCursor
                        }
                    }
                }
            }
            
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                
                Text {
                    text: "Espessura"
                    color: settingsController.mutedTextColor
                    font.pixelSize: 11
                    font.bold: true
                }
                
                Slider {
                    Layout.fillWidth: true
                    from: 2
                    to: 12
                    value: root.activeThickness
                    stepSize: 1
                    onValueChanged: {
                        root.activeThickness = value;
                        if (root.currentDrawing) {
                            root.currentDrawing.thickness = value;
                            drawingCanvas.requestPaint();
                        }
                    }
                }
            }
            
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                
                Button {
                    Layout.fillWidth: true
                    text: "Cancelar"
                    onClicked: {
                        root.routeNameDialogVisible = false;
                        root.currentDrawing = null;
                        drawingCanvas.requestPaint();
                    }
                }
                
                Button {
                    id: finishRouteBtn
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
                        if (root.currentDrawing && root.currentDrawing.type === "route") {
                            root.currentDrawing.name = routeNameInput.text;
                            root.currentDrawing.color = root.activeColor;
                            root.currentDrawing.thickness = root.activeThickness;
                            var newDrawings = root.drawings.slice();
                            newDrawings.push(root.currentDrawing);
                            root.drawings = newDrawings;
                            root.currentDrawing = null;
                            routeNameInput.text = "";
                            root.routeNameDialogVisible = false;
                            drawingCanvas.requestPaint();
                        }
                    }
                }
            }
        }
    }

    // --- JSON DEBUG WINDOW ---
    Rectangle {
        id: jsonDebugWindow
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 20
        width: 300
        height: 250
        radius: 8
        color: Qt.rgba(settingsController.surfaceColor.r, settingsController.surfaceColor.g, settingsController.surfaceColor.b, 0.9)
        border.color: settingsController.borderColor
        border.width: 1
        z: 999
        clip: true
        
        property string jsonOutput: ""
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 5
            
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "Log JSON dos Desenhos"
                    color: settingsController.textColor
                    font.bold: true
                    font.pixelSize: 12
                    Layout.fillWidth: true
                }
                Rectangle {
                    width: 50
                    height: 24
                    color: settingsController.accentColor
                    radius: 4
                    Text {
                        anchors.centerIn: parent
                        text: "Copiar"
                        color: "white"
                        font.pixelSize: 10
                        font.bold: true
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            jsonTextEdit.selectAll();
                            jsonTextEdit.copy();
                            jsonTextEdit.deselect();
                        }
                    }
                }
            }
            
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                
                TextEdit {
                    id: jsonTextEdit
                    text: jsonDebugWindow.jsonOutput
                    color: settingsController.textColor
                    font.family: "Consolas"
                    font.pixelSize: 10
                    wrapMode: TextEdit.WrapAnywhere
                    readOnly: true
                    selectByMouse: true
                }
            }
        }
    }

    // --- AUTO SAVE TIMER ---
    Item {
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
                
                var wp = screenToWorld(mapMouseArea.mouseX, mapMouseArea.mouseY);
                var isMouseActive = globalHoverTracker.hovered && Qt.application.active;
                var data = {
                    user: {
                        nick: typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido",
                        avatar: typeof chatController !== "undefined" ? chatController.currentUserAvatar : "",
                        id: currentUserId,
                        status: isMouseActive ? { x: wp.x, y: wp.y } : null
                    },
                    drawings: allDrawings
                };
                
                var jsonStr = JSON.stringify(data, function(key, val) {
                    if (val && typeof val.x === 'number') val.x = Math.round(val.x * 100) / 100;
                    if (val && typeof val.y === 'number') val.y = Math.round(val.y * 100) / 100;
                    return val;
                }, 2);
                jsonStr = jsonStr.replace(/\{\n\s+"x": ([\d.-]+),\n\s+"y": ([\d.-]+)\n\s+\}/g, '{ "x": $1, "y": $2 }');
                
                jsonDebugWindow.jsonOutput = jsonStr;
                
                if (typeof mapSessionController !== "undefined") {
                    mapSessionController.sendMapUpdate(jsonStr);
                    var date = new Date();
                    var h = date.getHours();
                    var m = date.getMinutes();
                    root.lastSyncTime = (h < 10 ? "0" + h : h) + ":" + (m < 10 ? "0" + m : m);
                }
            }
        }
    }

    // --- LOGISTICS MODAL OVERLAY ---
    LogisticsModal {
        id: logisticsModal
        mapItems: mapController.mapItemsModel
        onRoutesCalculated: (routes) => {
            root.logisticsRoutes = routes;
            
            // Push to drawings so it logs in JSON and syncs
            var newDrawings = [];
            for (var i = 0; i < routes.length; i++) {
                var r = routes[i];
                newDrawings.push({
                    type: "parabola",
                    start: { x: r.start.x, y: r.start.y },
                    end: { x: r.end.x, y: r.end.y },
                    cargo: r.cargo,
                    color: "#3b82f6",
                    thickness: 4,
                    user: typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido"
                });
            }
            var currentDrawings = root.drawings.slice();
            for (var j = 0; j < newDrawings.length; j++) {
                currentDrawings.push(newDrawings[j]);
            }
            root.drawings = currentDrawings;
            root.drawingsChanged();
            
            drawingCanvas.requestPaint();
        }
        onVisibleChanged: {
            root.logisticsModalVisible = visible;
        }
    }

    // --- MAP SESSIONS UI ---
    MapSessionsModal {
        id: mapSessionsModal
        activeUsers: root.activeUsers
        historicUsers: root.historicUsers
    }

    Rectangle {
        id: sessionPill
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.margins: 24
        height: 48
        width: sessionPillContent.width + 30
        radius: 24
        color: Qt.rgba(settingsController.surfaceColor.r, settingsController.surfaceColor.g, settingsController.surfaceColor.b, 0.8)
        border.color: settingsController.borderColor
        border.width: 1
        z: 990
        
        MultiEffect {
            source: sessionPill
            anchors.fill: sessionPill
            shadowEnabled: true
            shadowOpacity: 0.3
            shadowBlur: 2.0
            shadowVerticalOffset: 2
            shadowColor: "black"
        }

        RowLayout {
            id: sessionPillContent
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 15
            spacing: 12
            
            Rectangle {
                width: 32
                height: 32
                radius: 16
                color: settingsController.accentColor
                Text {
                    anchors.centerIn: parent
                    text: "🌐"
                    font.pixelSize: 16
                    color: "white"
                }
            }
            
            ColumnLayout {
                spacing: 0
                visible: typeof mapSessionController !== "undefined" && mapSessionController.currentRoom !== ""
                
                Text {
                    text: "Online: " + (root.activeUsers.length + 1)
                    color: settingsController.textColor
                    font.pixelSize: 12
                    font.bold: true
                }
                Text {
                    text: root.lastSyncTime === "" ? "Aguardando sincronização..." : "Sincronizado às " + root.lastSyncTime
                    color: settingsController.secondaryTextColor
                    font.pixelSize: 10
                }
            }
        }

        MouseArea {
            id: sessionBtnHover
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            hoverEnabled: true
            onClicked: mapSessionsModal.open()
        }
        
        ToolTip {
            visible: sessionBtnHover.containsMouse && (typeof mapSessionController === "undefined" || mapSessionController.currentRoom === "")
            text: "Sessões de Mapa"
            y: parent.height + 10
        }
    }
    
    Popup {
        id: kickedPopup
        width: 300
        height: 150
        anchors.centerIn: parent
        modal: true
        closePolicy: Popup.NoAutoClose
        
        background: Rectangle {
            color: "#1e1e1e"
            radius: 8
            border.color: "#ef4444"
            border.width: 2
        }
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 15
            
            Text {
                text: "⚠️ Expulso"
                color: "#ef4444"
                font.bold: true
                font.pixelSize: 18
                Layout.alignment: Qt.AlignHCenter
            }
            
            Text {
                text: "Você foi expulso desta sessão pelo criador da sala."
                color: "#ffffff"
                font.pixelSize: 14
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }
            
            PrimaryButton {
                text: "Voltar ao Lobby"
                Layout.alignment: Qt.AlignHCenter
                onClicked: {
                    kickedPopup.close();
                    root.drawings = [];
                    root.remoteCursorsDict = ({});
                    if (typeof mapSessionController !== "undefined") {
                        mapSessionController._current_room = "";
                    }
                }
            }
        }
    }
    
    Rectangle {
        id: drawingHoverTooltip
        property string tooltipText: ""
        visible: false
        width: tooltipLabel.width + 12
        height: tooltipLabel.height + 8
        color: "#1e1e1e"
        border.color: "#333333"
        border.width: 1
        radius: 4
        z: 9999
        
        Text {
            id: tooltipLabel
            anchors.centerIn: parent
            color: "#e2e8f0"
            font.pixelSize: 12
            text: drawingHoverTooltip.tooltipText
        }
    }
}
