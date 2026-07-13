import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import QtQuick.Layouts
import "SlangTerms.js" as SlangTerms
import "Vehicles.js" as VehiclesData
import GG.Map 1.0

Item {
    id: root
    clip: true

    property string baseUrl: typeof mapController !== "undefined" && mapController ? mapController.baseUrl : "https://foxlogi.com/map-tiles/patch-64/{z}/{x}/{y}.webp"
    property string fallbackUrl: typeof mapController !== "undefined" && mapController ? mapController.fallbackUrl : "https://foxlogi.com/map-tiles/patch-64/{z}/{x}/{y}.webp"
    property bool localTilesAvailable: typeof mapController !== "undefined" && mapController ? mapController.localTilesAvailable : false
    property int tileSize: localTilesAvailable && typeof mapController !== "undefined" && mapController ? mapController.localTileSize : 256
    property int minZoom: localTilesAvailable ? 0 : 2
    property int maxZoom: localTilesAvailable && typeof mapController !== "undefined" && mapController ? mapController.localMaxZoom : 7
    property int currentZoom: 2

    // --- Debug calibração malha (ajuste manual) ---
    property bool showCalibrationDebug: true
    property real debugMapScale: 1.0
    property real debugMapOffsetX: 0.0
    property real debugMapOffsetY: 0.0
    property real debugZoomMultX: 1.0
    property real debugZoomMultY: 1.0
    property string debugZoomMode: "pow2" // pow2 | manifest | foxlogi

    function debugBaseZoomScaleX(z) {
        if (debugZoomMode === "manifest" && localTilesAvailable && typeof mapController !== "undefined" && mapController)
            return mapController.getLocalTileLevelWidth(z) / mapController.getLocalTileLevelWidth(0);
        if (debugZoomMode === "foxlogi" && localTilesAvailable && typeof mapController !== "undefined" && mapController)
            return 128.0 * mapController.getLocalTileLevelWidth(z) / 32768.0;
        return Math.pow(2, z);
    }

    function debugBaseZoomScaleY(z) {
        if (debugZoomMode === "manifest" && localTilesAvailable && typeof mapController !== "undefined" && mapController)
            return mapController.getLocalTileLevelHeight(z) / mapController.getLocalTileLevelHeight(0);
        if (debugZoomMode === "foxlogi" && localTilesAvailable && typeof mapController !== "undefined" && mapController)
            return 128.0 * mapController.getLocalTileLevelHeight(z) / 32768.0;
        return Math.pow(2, z);
    }

    // The center of the view in map pixels at the current zoom level
    property real mapWidthAtZoom: localTilesAvailable && typeof mapController !== "undefined" && mapController ? mapController.getLocalTileLevelWidth(currentZoom) : Math.pow(2, currentZoom) * tileSize
    property real mapHeightAtZoom: localTilesAvailable && typeof mapController !== "undefined" && mapController ? mapController.getLocalTileLevelHeight(currentZoom) : Math.pow(2, currentZoom) * tileSize
    property real mapZoomScaleX: debugBaseZoomScaleX(currentZoom) * debugZoomMultX
    property real mapZoomScaleY: debugBaseZoomScaleY(currentZoom) * debugZoomMultY
    property real centerX: mapWidthAtZoom / 2
    property real centerY: mapHeightAtZoom / 2

    function mapLevelWidth(z) {
        if (localTilesAvailable && typeof mapController !== "undefined" && mapController)
            return mapController.getLocalTileLevelWidth(z);
        return Math.pow(2, z) * tileSize;
    }

    function mapLevelHeight(z) {
        if (localTilesAvailable && typeof mapController !== "undefined" && mapController)
            return mapController.getLocalTileLevelHeight(z);
        return Math.pow(2, z) * tileSize;
    }

    function layerScaleRatio(fromZoom, toZoom) {
        if (localTilesAvailable && typeof mapController !== "undefined" && mapController) {
            var wFrom = mapController.getLocalTileLevelWidth(fromZoom);
            var wTo = mapController.getLocalTileLevelWidth(toZoom);
            return wFrom > 0 ? wTo / wFrom : Math.pow(2, toZoom - fromZoom);
        }
        return Math.pow(2, toZoom - fromZoom);
    }

    function layerScaleRatioY(fromZoom, toZoom) {
        if (localTilesAvailable && typeof mapController !== "undefined" && mapController) {
            var hFrom = mapController.getLocalTileLevelHeight(fromZoom);
            var hTo = mapController.getLocalTileLevelHeight(toZoom);
            return hFrom > 0 ? hTo / hFrom : Math.pow(2, toZoom - fromZoom);
        }
        return Math.pow(2, toZoom - fromZoom);
    }
    
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
        if (typeof mapController !== "undefined" && mapController) {
            mapController.updateViewport(centerX, centerY, width, height, currentZoom);
        }
        updateCullingSignal();
    }
    // --- DRAWING SYSTEM PROPERTIES ---
    property string activeTool: "pan" // "pan", "brush", "arrow", "polygon", "eraser", "vehicle", "artillery"
    
    // Artillery state
    property var artilleryCannon: null
    property var artilleryTarget: null
    property int artilleryStep: 0
    property var savedArtilleries: []
    
    function saveCurrentArtillery() {
        if (artilleryCannon && artilleryTarget) {
            var newSaved = savedArtilleries.slice();
            
            var cAPI = root.worldToApi(artilleryCannon.x, artilleryCannon.y);
            var tAPI = root.worldToApi(artilleryTarget.x, artilleryTarget.y);
            var windD = typeof artilleryController !== "undefined" && artilleryController ? artilleryController.windDirection : 0;
            var windT = typeof artilleryController !== "undefined" && artilleryController ? artilleryController.windTier : 0;
            
            var mRes = typeof mapController !== "undefined" && mapController ? mapController.calculateArtillery(cAPI.x, cAPI.y, tAPI.x, tAPI.y, windD, windT) : null;
            var dist = mRes ? (mRes.distance_meters || 0) : 0;
            var azm = mRes ? (mRes.bearing || 0) : 0;
            var rads = typeof artilleryController !== "undefined" && artilleryController ? artilleryController.getOverlayData(dist) : null;
            var icon = typeof artilleryController !== "undefined" && artilleryController.weaponInfo && artilleryController.weaponInfo.icon ? "../../" + artilleryController.weaponInfo.icon : "";
            
            newSaved.push({
                cannon: artilleryCannon,
                target: artilleryTarget,
                windDirection: windD,
                windTier: windT,
                mathRes: mRes,
                dist_meters: dist,
                azm: azm,
                radii: rads,
                weaponIcon: icon
            });
            savedArtilleries = newSaved;
            
            // Reset state so user can place another immediately
            artilleryStep = 0;
            artilleryCannon = null;
            artilleryTarget = null;
            console.log("MapView: Battery saved! Total saved:", savedArtilleries.length);
        }
    }
    
    onActiveToolChanged: {
        root.selectedVehicleIndex = -1
        if (activeTool === "artillery") {
            artilleryModal.visible = true;
        } else {
            artilleryModal.visible = false;
        }
    }
    
    property string activeColor: "#ef4444" // default red
    property string activeVehicleImage: "Blacksteele.png"
    property real activeVehicleRotation: 0
    property real activeVehicleScale: 1.0
    property string activeVehicleName: ""
    property int activeVehicleCount: 1
    
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
    property bool textToolDialogVisible: false
    property var currentTextLocation: null
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

    function getZoomFactor() {
        return Math.pow(2, currentZoom - 6);
    }

    function screenToWorld(sx, sy) {
        var mapX = sx - (root.width / 2) + root.centerX;
        var mapY = sy - (root.height / 2) + root.centerY;
        var zf = getZoomFactor();
        return {
            x: mapX / zf,
            y: mapY / zf
        };
    }
    
    function findNearestNode(wp, thresholdPixels) {
        if (!root.drawings) return null;
        var zf = getZoomFactor();
        var thresholdWorld = thresholdPixels / zf;
        var bestDist = thresholdWorld;
        var bestNode = null;
        
        for (var i = 0; i < root.drawings.length; i++) {
            var d = root.drawings[i];
            if (!d) continue;
            
            if ((d.type === "route" || d.type === "polygon" || d.type === "brush") && d.points) {
                for (var j = 0; j < d.points.length; j++) {
                    var p = d.points[j];
                    var dist = Math.sqrt(Math.pow(p.x - wp.x, 2) + Math.pow(p.y - wp.y, 2));
                    if (dist < bestDist) {
                        bestDist = dist;
                        bestNode = {x: p.x, y: p.y};
                    }
                }
            } else if (d.type === "arrow" && d.start && d.end) {
                var distStart = Math.sqrt(Math.pow(d.start.x - wp.x, 2) + Math.pow(d.start.y - wp.y, 2));
                if (distStart < bestDist) {
                    bestDist = distStart;
                    bestNode = {x: d.start.x, y: d.start.y};
                }
                var distEnd = Math.sqrt(Math.pow(d.end.x - wp.x, 2) + Math.pow(d.end.y - wp.y, 2));
                if (distEnd < bestDist) {
                    bestDist = distEnd;
                    bestNode = {x: d.end.x, y: d.end.y};
                }
            } else if (d.type === "parabola" || d.type === "artillery") {
                // For parabola and artillery, start and end are in API coords, so convert them to world first to check snapping
                if (d.start && d.end) {
                    var wStart = apiToWorld(d.start.x, d.start.y);
                    var wEnd = apiToWorld(d.end.x, d.end.y);
                    
                    var distStart2 = Math.sqrt(Math.pow(wStart.x - wp.x, 2) + Math.pow(wStart.y - wp.y, 2));
                    if (distStart2 < bestDist) {
                        bestDist = distStart2;
                        bestNode = {x: wStart.x, y: wStart.y}; // Snap to World coordinate
                    }
                    var distEnd2 = Math.sqrt(Math.pow(wEnd.x - wp.x, 2) + Math.pow(wEnd.y - wp.y, 2));
                    if (distEnd2 < bestDist) {
                        bestDist = distEnd2;
                        bestNode = {x: wEnd.x, y: wEnd.y};
                    }
                }
            }
        }
        return bestNode;
    }

    function worldToCanvas(wx, wy) {
        var zf = getZoomFactor();
        var mapX = wx * zf;
        var mapY = wy * zf;
        var sx = mapX + (root.width / 2) - root.centerX;
        var sy = mapY + (root.height / 2) - root.centerY;
        return {x: sx, y: sy};
    }

    function apiToWorld(apiX, apiY) {
        var wX = apiX * 80.0;
        var wY = -apiY * 80.0 - 4024.0;
        return {x: wX, y: wY};
    }
    
    function worldToApi(wX, wY) {
        var apiX = wX / 80.0;
        var apiY = -(wY + 4024.0) / 80.0;
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
        interval: 150
        repeat: false
        onTriggered: {
            root.updateCulling();
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
        if (root.currentZoom < root.minZoom) root.currentZoom = root.minZoom;
        else if (root.currentZoom > root.maxZoom) root.currentZoom = root.maxZoom;
        if (typeof cullingTimer !== "undefined") cullingTimer.restart();
        var activeLayer = (activeLayerIndex === 0) ? layerA : layerB;
        activeLayer.layerZoom = root.currentZoom;
        root.updateCulling();
    }
    
    Component.onCompleted: {
        layerA.freezeCenter = false;
        layerB.freezeCenter = true;
        layerA.layerZoom = root.currentZoom;
        if (typeof mapController !== "undefined" && mapController) {
            mapController.mapScale = root.debugMapScale;
            mapController.mapOffsetX = root.debugMapOffsetX;
            mapController.mapOffsetY = root.debugMapOffsetY;
            mapController.fetchStockData();
        }
        root.updateCulling();
    }

    onDebugMapScaleChanged: if (typeof mapController !== "undefined" && mapController) mapController.mapScale = debugMapScale
    onDebugMapOffsetXChanged: if (typeof mapController !== "undefined" && mapController) mapController.mapOffsetX = debugMapOffsetX
    onDebugMapOffsetYChanged: if (typeof mapController !== "undefined" && mapController) mapController.mapOffsetY = debugMapOffsetY

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
        
        centerX: root.centerX * root.layerScaleRatio(root.currentZoom, layerA.layerZoom)
        centerY: root.centerY * root.layerScaleRatioY(root.currentZoom, layerA.layerZoom)
        
        transform: Scale {
            origin.x: layerA.viewWidth / 2 - layerA.x
            origin.y: layerA.viewHeight / 2 - layerA.y
            xScale: root.layerScaleRatio(layerA.layerZoom, root.currentZoom)
            yScale: root.layerScaleRatioY(layerA.layerZoom, root.currentZoom)
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
        
        centerX: root.centerX * root.layerScaleRatio(root.currentZoom, layerB.layerZoom)
        centerY: root.centerY * root.layerScaleRatioY(root.currentZoom, layerB.layerZoom)
        
        transform: Scale {
            origin.x: layerB.viewWidth / 2 - layerB.x
            origin.y: layerB.viewHeight / 2 - layerB.y
            xScale: root.layerScaleRatio(layerB.layerZoom, root.currentZoom)
            yScale: root.layerScaleRatioY(layerB.layerZoom, root.currentZoom)
        }
    }

    // Overlay Manager Container
    Item {
        id: overlayManager
        x: (root.width / 2) - root.centerX
        y: (root.height / 2) - root.centerY
        width: root.mapWidthAtZoom
        height: root.mapHeightAtZoom
        z: 2 // Always on top of map layers
        
        MapIconsRenderer {
            anchors.fill: parent
            itemsData: typeof mapController !== "undefined" && mapController ? mapController.mapItemsModel : []
            mapScale: typeof mapController !== "undefined" && mapController ? mapController.mapScale : 1
            mapOffsetX: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetX : 0
            mapOffsetY: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetY : 0
            mapZoomScaleX: root.mapZoomScaleX
            mapZoomScaleY: root.mapZoomScaleY
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
                property real worldPxX: modelData.x * 80.0
                property real worldPxY: -modelData.y * 80.0 - 4024.0
                
                x: (worldPxX * getZoomFactor()) + (root.width / 2) - root.centerX - width / 2
                y: (worldPxY * getZoomFactor()) + (root.height / 2) - root.centerY - height / 2
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
        mapZoomScaleX: root.mapZoomScaleX
        mapZoomScaleY: root.mapZoomScaleY
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
        onSaveRequested: root.saveCurrentArtillery()
        onClearRequested: {
            root.savedArtilleries = [];
            console.log("MapView: All saved batteries cleared.");
        }
    }

    Item {
        id: drawingContainer
        anchors.fill: parent
        z: 3 // Above map, below UI filters
        
        Repeater {
            model: root.savedArtilleries
            delegate: ArtilleryOverlay {
                cannonX: modelData.cannon.x
                cannonY: modelData.cannon.y
                targetX: modelData.target.x
                targetY: modelData.target.y
                isDynamic: false
                externalMathRes: modelData.mathRes
                externalRadii: modelData.radii
                externalIcon: modelData.weaponIcon
                isActive: true
                mapController: typeof mapController !== "undefined" ? mapController : null
                currentZoom: root.currentZoom
                mapScale: typeof mapController !== "undefined" && mapController ? mapController.mapScale : 1
                mapOffsetX: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetX : 0
                mapOffsetY: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetY : 0
                mapZoomScaleX: root.getZoomFactor()
                mapZoomScaleY: root.getZoomFactor()
                centerX: root.centerX
                centerY: root.centerY
            }
        }

        ArtilleryOverlay {
            id: dynamicArtilleryOverlay
            isActive: (root.activeTool === "artillery" && root.artilleryCannon !== null)
            mapController: typeof mapController !== "undefined" ? mapController : null
            currentZoom: root.currentZoom
            mapScale: typeof mapController !== "undefined" && mapController ? mapController.mapScale : 1
            mapOffsetX: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetX : 0
            mapOffsetY: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetY : 0
            mapZoomScaleX: root.getZoomFactor()
            mapZoomScaleY: root.getZoomFactor()
            
            centerX: root.centerX
            centerY: root.centerY
            
            cannonX: root.artilleryCannon ? root.artilleryCannon.x : 0
            cannonY: root.artilleryCannon ? root.artilleryCannon.y : 0
            targetX: root.artilleryTarget ? root.artilleryTarget.x : 0
            targetY: root.artilleryTarget ? root.artilleryTarget.y : 0
        }
        
        MapDrawingsRenderer {
            id: mapDrawingsRenderer
            anchors.fill: parent
            drawings: root.drawings
            currentDrawing: root.currentDrawing || {}
            dashOffset: root.dashOffset
            mapScale: typeof mapController !== "undefined" && mapController ? mapController.mapScale : 1.0
            mapOffsetX: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetX : 0.0
            mapOffsetY: typeof mapController !== "undefined" && mapController ? mapController.mapOffsetY : 0.0
            mapZoomScaleX: root.mapZoomScaleX
            mapZoomScaleY: root.mapZoomScaleY
            currentZoom: root.currentZoom
            centerX: root.centerX
            centerY: root.centerY
            hoveredRoute: root.logisticsHoveredRoute || {}
        }

        // High-fidelity QML overlays for Remote Cursors
        Repeater {
            model: remoteCursorsModel
            delegate: Item {
                property real targetWx: model.wx
                property real targetWy: model.wy
                
                Behavior on targetWx { NumberAnimation { duration: 150; easing.type: Easing.OutQuad } }
                Behavior on targetWy { NumberAnimation { duration: 150; easing.type: Easing.OutQuad } }
                
                x: (targetWx * getZoomFactor()) - root.centerX + (root.width / 2)
                y: (targetWy * getZoomFactor()) - root.centerY + (root.height / 2)
                z: 200 // On top of canvas

                // Cursor Arrow
                Text {
                    text: "🡔" // default arrow
                    font.pixelSize: 24
                    color: "#f59e0b" // orange
                    x: -6
                    y: -12
                    style: Text.Outline
                    styleColor: "white"
                    visible: !model.tool || model.tool === "pan"
                }

                // Tool Icon
                Text {
                    text: {
                        if (model.tool === "brush") return "🖌️";
                        if (model.tool === "arrow") return "↗️";
                        if (model.tool === "polygon") return "⬟";
                        if (model.tool === "route") return "🛣️";
                        if (model.tool === "eraser") return "🧽";
                        if (model.tool === "vehicle") return "🚙";
                        if (model.tool === "artillery") return "🎯";
                        if (model.tool === "text") return "📝";
                        return "✏️";
                    }
                    font.pixelSize: 18
                    x: 2
                    y: -14
                    visible: model.tool && model.tool !== "pan"
                }

                // Avatar container at bottom right
                Rectangle {
                    x: 10
                    y: 10
                    width: 32
                    height: 32
                    radius: 16
                    color: "#111827"
                    border.color: "#f59e0b" // orange
                    border.width: 2
                    
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 2
                        radius: 14
                        color: "transparent"
                        border.color: "white"
                        border.width: 1
                        z: 5
                    }
                    
                    Image {
                        anchors.fill: parent
                        anchors.margins: 2
                        source: model.avatar || ""
                        fillMode: Image.PreserveAspectCrop
                        visible: model.avatar !== ""
                        layer.enabled: true
                        layer.effect: OpacityMask {
                            maskSource: Rectangle { width: 28; height: 28; radius: 14 }
                        }
                    }
                    
                    Text {
                        anchors.centerIn: parent
                        text: model.nick ? model.nick.substring(0,1).toUpperCase() : "?"
                        color: "#ffffff"
                        font.bold: true
                        font.pixelSize: 14
                        visible: model.avatar === ""
                    }
                }
                
                // Name Tag
                Rectangle {
                    anchors.top: parent.top
                    anchors.topMargin: 46
                    anchors.horizontalCenter: parent.left
                    anchors.horizontalCenterOffset: 26
                    color: "#d9111827"
                    radius: 4
                    border.color: "#f59e0b"
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
                
                x: (wx * getZoomFactor()) - root.centerX + (root.width / 2) - width/2
                y: (wy * getZoomFactor()) - root.centerY + (root.height / 2) - height/2
                z: root.selectedVehicleIndex === index ? 155 : 150
                
                width: vehColumn.implicitWidth
                height: vehColumn.implicitHeight
                
                rotation: root.selectedVehicleIndex === index ? root.liveVehicleRotation : (modelData.rotation || 0)
                
                Column {
                    id: vehColumn
                    anchors.centerIn: parent
                    spacing: 4
                    Image {
                        property string resolutionFolder: {
                            if (root.mapZoomScaleX > 4.0) return "/large/";
                            if (root.mapZoomScaleX > 1.5) return "/medium/";
                            return "/small/";
                        }
                        property string imagePath: (modelData.image || "Blacksteele.png").replace("/small/", resolutionFolder)
                        source: typeof appController !== "undefined" ? appController.assetUrl("img/map-layer/" + imagePath) : "file:///c:/Users/ryanl/OneDrive/Desktop/aplicativo/img/map-layer/" + imagePath
                        
                        property real computedScale: root.selectedVehicleIndex === index ? root.liveVehicleScale : (modelData.scale || 1.0)
                        property real refZoomScale: root.localTilesAvailable && typeof mapController !== "undefined" && mapController ? mapController.getMapZoomScaleX(2) : 4
                        property real zoomFactor: root.mapZoomScaleX / refZoomScale
                        
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
                                              
                        var globalMouse = mapToItem(root, mouse.x, mouse.y);
                        startMouseWorldX = globalMouse.x;
                        startMouseWorldY = globalMouse.y;
                        startWx = vehItem.wx;
                        startWy = vehItem.wy;
                    }
                    onPositionChanged: function(mouse) {
                        if (pressed) {
                            var globalMouse = mapToItem(root, mouse.x, mouse.y);
                            var dx = globalMouse.x - startMouseWorldX;
                            var dy = globalMouse.y - startMouseWorldY;
                            vehItem.wx = startWx + (dx / getZoomFactor());
                            vehItem.wy = startWy + (dy / getZoomFactor());
                            
                            // Update start positions for continuous dragging without feedback loop
                            startMouseWorldX = globalMouse.x;
                            startMouseWorldY = globalMouse.y;
                            startWx = vehItem.wx;
                            startWy = vehItem.wy;
                        }
                    }
                    onReleased: function(mouse) {
                        if (startWx !== vehItem.wx || startWy !== vehItem.wy) {
                            var newDrawings = [];
                            for (var i = 0; i < root.drawings.length; i++) {
                                newDrawings.push(root.drawings[i]);
                            }
                            var modified = Object.assign({}, newDrawings[index]);
                            modified.x = vehItem.wx;
                            modified.y = vehItem.wy;
                            newDrawings[index] = modified;
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
        property real lastCursorSyncTime: 0
        
        function eraseAt(sx, sy) {
            var wp = screenToWorld(sx, sy);
            var threshold = 15 / root.mapZoomScaleX;
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
                        if (dist <= threshold + (d.thickness || 3) / root.mapZoomScaleX) {
                            hit = true; break;
                        }
                    }
                } else if (d.type === "arrow" || d.type === "artillery") {
                    var dist2 = distanceToSegment(wp.x, wp.y, d.start.x, d.start.y, d.end.x, d.end.y);
                    if (dist2 <= threshold + (d.thickness || 3) / root.mapZoomScaleX) {
                        hit = true;
                    }
                } else if (d.type === "parabola") {
                    var sWp = apiToWorld(d.start.x, d.start.y);
                    var eWp = apiToWorld(d.end.x, d.end.y);
                    var pDist = distanceToParabola(wp.x, wp.y, sWp.x, sWp.y, eWp.x, eWp.y);
                    if (pDist <= threshold + (d.thickness || 3) / root.mapZoomScaleX) {
                        hit = true;
                    }
                } else if (d.type === "vehicle") {
                    var distVeh = Math.sqrt(Math.pow(wp.x - d.x, 2) + Math.pow(wp.y - d.y, 2));
                    if (distVeh <= (30 * (d.scale || 1.0)) / root.mapZoomScaleX) {
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
            } else if (root.activeTool === "arrow") {
                var wp2 = screenToWorld(mouse.x, mouse.y);
                var nearestNode2 = findNearestNode(wp2, 15);
                if (nearestNode2) wp2 = nearestNode2;
                var cUserArrow = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                root.currentDrawing = { type: "arrow", color: root.activeColor, thickness: root.activeThickness, start: wp2, end: wp2, user: cUserArrow };
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
                }
            } else if (root.activeTool === "route") {
                cursorShape = Qt.CrossCursor;
                if (!didPan && !root.routeNameDialogVisible) {
                    var wpRoute = screenToWorld(mouse.x, mouse.y);
                    var nearestNodeR = findNearestNode(wpRoute, 15);
                    if (nearestNodeR) wpRoute = nearestNodeR;
                    if (!root.currentDrawing || root.currentDrawing.type !== "route") {
                        var cUserRoute = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                        root.currentDrawing = { type: "route", color: root.activeColor, thickness: root.activeThickness, points: [wpRoute], user: cUserRoute };
                    } else {
                        var route = Object.assign({}, root.currentDrawing);
                        route.points = route.points.slice();
                        route.points.push(wpRoute);
                        root.currentDrawing = route;
                    }
                }
            } else if (root.activeTool === "vehicle") {
                cursorShape = Qt.CrossCursor;
                if (!didPan && !root.wasEditingOnPress) {
                    var wpVeh = screenToWorld(mouse.x, mouse.y);
                    var cUserVeh = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                    var newDrawings = root.drawings.slice();
                    var count = root.activeVehicleCount || 1;
                    var scaleFactor = (1.0 / (root.localTilesAvailable && typeof mapController !== "undefined" && mapController ? mapController.getMapZoomScaleX(2) : 4));
                    var finalScale = root.activeVehicleScale * scaleFactor;
                    
                    var angleRad = (root.activeVehicleRotation + 90) * Math.PI / 180.0;
                    var spacing = 60 * finalScale;
                    
                    for (var k = 0; k < count; k++) {
                        var offset_idx = k - (count - 1) / 2.0;
                        var dx = Math.cos(angleRad) * spacing * offset_idx;
                        var dy = Math.sin(angleRad) * spacing * offset_idx;
                        
                        newDrawings.push({
                            type: "vehicle",
                            user: cUserVeh,
                            x: wpVeh.x + dx,
                            y: wpVeh.y + dy,
                            image: root.activeVehicleImage,
                            rotation: root.activeVehicleRotation,
                            scale: finalScale,
                            name: root.activeVehicleName + (count > 1 ? (" " + (k + 1)) : "")
                        });
                    }
                    root.drawings = newDrawings;
                }
            } else if (root.activeTool === "text") {
                cursorShape = Qt.CrossCursor;
                if (!didPan && !root.textToolDialogVisible) {
                    var wpText = screenToWorld(mouse.x, mouse.y);
                    var nearestNodeT = findNearestNode(wpText, 15);
                    if (nearestNodeT) wpText = nearestNodeT;
                    
                    root.currentTextLocation = wpText;
                    root.textToolDialogVisible = true;
                }
            } else if (root.activeTool === "artillery") {
                cursorShape = Qt.CrossCursor;
                if (!didPan) {
                    var wpArt = screenToWorld(mouse.x, mouse.y);
                    if (root.artilleryStep === 0) {
                        root.artilleryCannon = wpArt;
                        root.artilleryTarget = wpArt;
                        root.artilleryStep = 1;
                    } else if (root.artilleryStep === 1) {
                        root.artilleryTarget = wpArt;
                        root.artilleryStep = 2;
                    } else if (root.artilleryStep === 2) {
                        root.artilleryTarget = wpArt;
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
            if (root.activeTool === "artillery" && root.artilleryStep === 1) {
                var wpArt = screenToWorld(mouse.x, mouse.y);
                root.artilleryTarget = wpArt;
            }
            if (isDragging) {
                if (root.activeTool === "pan" || root.activeTool === "polygon" || root.activeTool === "route" || root.activeTool === "vehicle") {
                    var dx = mouse.x - lastX;
                    var dy = mouse.y - lastY;
                    
                    var dist = Math.sqrt(Math.pow(mouse.x - pressX, 2) + Math.pow(mouse.y - pressY, 2));
                    if (dist > 5) {
                        didPan = true;
                    }
                    
                    if (didPan || root.activeTool === "pan") {
                        root.centerX = Math.max(0, Math.min(root.mapWidthAtZoom, root.centerX - dx));
                        root.centerY = Math.max(0, Math.min(root.mapHeightAtZoom, root.centerY - dy));
                        lastX = mouse.x;
                        lastY = mouse.y;
                    }
                } else if (root.activeTool === "brush" && root.currentDrawing) {
                    var lastPt = root.currentDrawing.points[root.currentDrawing.points.length - 1];
                    var wp = screenToWorld(mouse.x, mouse.y);
                    var spLast = worldToCanvas(lastPt.x, lastPt.y);
                    var distBrush = Math.sqrt(Math.pow(mouse.x - spLast.x, 2) + Math.pow(mouse.y - spLast.y, 2));
                    if (distBrush > 4) {
                        var b = Object.assign({}, root.currentDrawing);
                        var newPoints = [];
                        for (var i = 0; i < root.currentDrawing.points.length; i++) {
                            newPoints.push(root.currentDrawing.points[i]);
                        }
                        newPoints.push(wp);
                        b.points = newPoints;
                        root.currentDrawing = b;
                    }
                } else if (root.activeTool === "arrow" && root.currentDrawing) {
                    var wp2 = screenToWorld(mouse.x, mouse.y);
                    var spStart = worldToCanvas(root.currentDrawing.start.x, root.currentDrawing.start.y);
                    var distArrow = Math.sqrt(Math.pow(mouse.x - spStart.x, 2) + Math.pow(mouse.y - spStart.y, 2));
                    // Only update arrow if it changed significantly
                    var prevEnd = root.currentDrawing.end;
                    var spPrevEnd = worldToCanvas(prevEnd.x, prevEnd.y);
                    var distArrowDelta = Math.sqrt(Math.pow(mouse.x - spPrevEnd.x, 2) + Math.pow(mouse.y - spPrevEnd.y, 2));
                    if (distArrowDelta > 3) {
                        var arr = Object.assign({}, root.currentDrawing);
                        // Ensure start is a pure JS object so it doesn't lose properties in PySide Variant
                        arr.start = { x: root.currentDrawing.start.x, y: root.currentDrawing.start.y };
                        arr.end = { x: wp2.x, y: wp2.y };
                        root.currentDrawing = arr;
                    }
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
                        if (rdist < 20 / root.mapZoomScaleX) {
                            foundHover = route;
                            break;
                        }
                    }
                    if (root.logisticsHoveredRoute !== foundHover) {
                        root.logisticsHoveredRoute = foundHover;
                    }
                }
                
                // Hover for drawings
                if (!isDragging && root.drawings) {
                    var hoverWp = screenToWorld(mouse.x, mouse.y);
                    var hoverThreshold = 15 / root.mapZoomScaleX;
                    var foundHoverDrawing = null;
                    
                    for (var i = root.drawings.length - 1; i >= 0; i--) {
                        var d = root.drawings[i];
                        var hit = false;
                        if (d.type === "polygon") {
                            hit = isPointInPolygon(hoverWp.x, hoverWp.y, d.points);
                        } else if (d.type === "brush" || d.type === "route") {
                            for (var j = 0; j < d.points.length - 1; j++) {
                                var segmentDist = distanceToSegment(hoverWp.x, hoverWp.y, d.points[j].x, d.points[j].y, d.points[j+1].x, d.points[j+1].y);
                                if (segmentDist <= hoverThreshold + (d.thickness || 3) / root.mapZoomScaleX) {
                                    hit = true; break;
                                }
                            }
                        } else if (d.type === "arrow") {
                            var arrowDist = distanceToSegment(hoverWp.x, hoverWp.y, d.start.x, d.start.y, d.end.x, d.end.y);
                            if (arrowDist <= hoverThreshold + (d.thickness || 3) / root.mapZoomScaleX) {
                                hit = true;
                            }
                        } else if (d.type === "artillery") {
                            var aStartWp = apiToWorld(d.start.x, d.start.y);
                            var aEndWp = apiToWorld(d.end.x, d.end.y);
                            var artDist = distanceToSegment(hoverWp.x, hoverWp.y, aStartWp.x, aStartWp.y, aEndWp.x, aEndWp.y);
                            if (artDist <= hoverThreshold + (d.thickness || 3) / root.mapZoomScaleX) {
                                hit = true;
                            }
                        } else if (d.type === "vehicle") {
                            var vDist = Math.sqrt(Math.pow(hoverWp.x - d.x, 2) + Math.pow(hoverWp.y - d.y, 2));
                            if (vDist <= (30 * (d.scale || 1.0)) / root.mapZoomScaleX) {
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
                
                var scaleFactorX = root.mapLevelWidth(newZoom) / root.mapLevelWidth(root.currentZoom);
                var scaleFactorY = root.mapLevelHeight(newZoom) / root.mapLevelHeight(root.currentZoom);
                var newMx = mx * scaleFactorX;
                var newMy = my * scaleFactorY;
                
                var newCenterX = root.centerX + (newMx - mx);
                var newCenterY = root.centerY + (newMy - my);
                
                var finalCenterX = Math.max(0, Math.min(root.mapLevelWidth(newZoom), newCenterX));
                var finalCenterY = Math.max(0, Math.min(root.mapLevelHeight(newZoom), newCenterY));
                
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
            // Text Tool
            Rectangle {
                width: 36
                height: 36
                radius: 18
                color: root.activeTool === "text" ? settingsController.accentColor : "transparent"
                border.color: root.activeTool === "text" ? settingsController.accentColor : settingsController.borderColor
                Text {
                    anchors.centerIn: parent
                    text: "T"
                    font.pixelSize: 18
                    font.bold: true
                    color: root.activeTool === "text" ? "white" : settingsController.textColor
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (root.activeTool === "text") {
                            root.showToolSettings = !root.showToolSettings;
                        } else {
                            if (root.currentDrawing) root.currentDrawing = null;
                            root.activeTool = "text";
                            root.showToolSettings = false; // no settings for now except color
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
        height: root.selectedVehicleIndex !== -1 ? 260 : (root.activeTool === "eraser" ? 80 : (root.activeTool === "vehicle" ? 480 : 120))
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
            visible: root.activeTool !== "eraser" && root.activeTool !== "vehicle" && root.selectedVehicleIndex === -1
            
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
                        if (root.selectedVehicleIndex !== -1 && root.liveVehicleRotation !== value) {
                            root.liveVehicleRotation = value;
                        }
                    }
                    onPressedChanged: {
                        if (!pressed && root.selectedVehicleIndex !== -1 && root.drawings[root.selectedVehicleIndex]) {
                            if (root.drawings[root.selectedVehicleIndex].rotation !== root.liveVehicleRotation) {
                                var newDrawings = root.drawings.slice();
                                var modified = Object.assign({}, newDrawings[root.selectedVehicleIndex]);
                                modified.rotation = root.liveVehicleRotation;
                                newDrawings[root.selectedVehicleIndex] = modified;
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
                        if (root.selectedVehicleIndex !== -1 && root.liveVehicleScale !== value) {
                            root.liveVehicleScale = value;
                        }
                    }
                    onPressedChanged: {
                        if (!pressed && root.selectedVehicleIndex !== -1 && root.drawings[root.selectedVehicleIndex]) {
                            if (root.drawings[root.selectedVehicleIndex].scale !== root.liveVehicleScale) {
                                var newDrawings = root.drawings.slice();
                                var modified = Object.assign({}, newDrawings[root.selectedVehicleIndex]);
                                modified.scale = root.liveVehicleScale;
                                newDrawings[root.selectedVehicleIndex] = modified;
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
                                var modified = Object.assign({}, newDrawings[root.selectedVehicleIndex]);
                                modified.name = root.liveVehicleName;
                                newDrawings[root.selectedVehicleIndex] = modified;
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
                text: "Catálogo de Embarcações e Veículos"
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 14
            }
            
            RowLayout {
                width: parent.width
                spacing: 8
                Text {
                    text: "Qtd ao clicar:"
                    color: settingsController.textColor
                    font.bold: true
                    font.pixelSize: 12
                }
                
                Rectangle {
                    width: 32; height: 32
                    radius: 4
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor
                    border.width: 1
                    Text { anchors.centerIn: parent; text: "-"; color: settingsController.textColor; font.bold: true }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: if (root.activeVehicleCount > 1) root.activeVehicleCount--
                        cursorShape: Qt.PointingHandCursor
                    }
                }
                Text {
                    text: root.activeVehicleCount.toString()
                    color: settingsController.textColor
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                }
                Rectangle {
                    width: 32; height: 32
                    radius: 4
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor
                    border.width: 1
                    Text { anchors.centerIn: parent; text: "+"; color: settingsController.textColor; font.bold: true }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: if (root.activeVehicleCount < 50) root.activeVehicleCount++
                        cursorShape: Qt.PointingHandCursor
                    }
                }
            }
            
            TextField {
                width: parent.width
                placeholderText: "Buscar..."
                color: settingsController.textColor
                font.pixelSize: 12
                background: Rectangle { color: settingsController.backgroundColor; border.color: settingsController.borderColor; border.width: 1; radius: 6 }
                onTextEdited: vehicleSearchCol.searchText = text.toLowerCase()
            }
            
            ScrollView {
                width: parent.width
                height: 290
                clip: true
                
                Column {
                    width: parent.width
                    spacing: 16
                    
                    Repeater {
                        model: {
                            if (typeof VehiclesData === "undefined" || !VehiclesData.data.categories) return [];
                            return VehiclesData.data.categories;
                        }
                        
                        delegate: Column {
                            width: parent.width
                            spacing: 8
                            visible: itemsRepeater.count > 0
                            
                            Text {
                                text: modelData.name
                                color: settingsController.accentColor
                                font.bold: true
                                font.pixelSize: 13
                            }
                            
                            Grid {
                                columns: 3
                                spacing: 12
                                
                                Repeater {
                                    id: itemsRepeater
                                    model: {
                                        var res = [];
                                        var items = modelData.items;
                                        for (var i = 0; i < items.length; i++) {
                                            if (vehicleSearchCol.searchText === "" || items[i].name.toLowerCase().indexOf(vehicleSearchCol.searchText) !== -1) {
                                                res.push(items[i]);
                                            }
                                        }
                                        return res;
                                    }
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
                        }
                    }
                }
            }
        }
    }

    // --- TEXT TOOL MODAL ---
    Rectangle {
        id: textToolModal
        visible: root.textToolDialogVisible
        anchors.centerIn: parent
        width: 320
        height: 180
        radius: 8
        color: settingsController.surfaceColor
        border.color: settingsController.borderColor
        border.width: 1
        z: 200
        
        MultiEffect {
            source: textToolModal
            anchors.fill: textToolModal
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
                text: "Adicionar Texto"
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 16
                Layout.fillWidth: true
            }
            
            TextField {
                id: textToolInput
                Layout.fillWidth: true
                placeholderText: "Ex: Alvo Principal 1"
                color: settingsController.textColor
                background: Rectangle {
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor
                    border.width: 1
                    radius: 4
                }
                onAccepted: finishTextBtn.clicked()
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
                            onClicked: root.activeColor = modelData;
                            cursorShape: Qt.PointingHandCursor
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
                        root.textToolDialogVisible = false;
                        root.currentTextLocation = null;
                        textToolInput.text = "";
                    }
                }
                
                Button {
                    id: finishTextBtn
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
                        if (root.currentTextLocation && textToolInput.text.trim() !== "") {
                            var cUserText = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                            var newTextDrawing = {
                                type: "text",
                                text: textToolInput.text.trim(),
                                color: root.activeColor,
                                start: root.currentTextLocation, // Use start to hold the coordinate
                                user: cUserText
                            };
                            
                            var newDrawings = root.drawings.slice();
                            newDrawings.push(newTextDrawing);
                            root.drawings = newDrawings;
                        }
                        root.textToolDialogVisible = false;
                        root.currentTextLocation = null;
                        textToolInput.text = "";
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
        property real lastSentWx: -99999
        property real lastSentWy: -99999
        property string lastSentDrawingsJson: ""
        
        Timer {
            interval: 50
            running: true
            repeat: true
            onTriggered: {
                if (globalHoverTracker.hovered && Qt.application.active) {
                    var mx = globalHoverTracker.point.position.x;
                    var my = globalHoverTracker.point.position.y;
                    var wp = screenToWorld(mx, my);
                    if (Math.abs(wp.x - parent.lastSentWx) > 0.1 || Math.abs(wp.y - parent.lastSentWy) > 0.1) {
                        parent.lastSentWx = wp.x;
                        parent.lastSentWy = wp.y;
                        var userId = (typeof chatController !== "undefined" && chatController.currentUserId) ? chatController.currentUserId : "";
                        if (typeof mapSessionController !== "undefined" && mapSessionController.currentRoom !== "") {
                            var payload = {
                                user: {
                                    id: userId,
                                    nick: typeof chatController !== "undefined" && chatController.currentUserName ? chatController.currentUserName : "Unknown",
                                    avatar: typeof chatController !== "undefined" && chatController.currentUserAvatar ? chatController.currentUserAvatar : "",
                                    status: { x: wp.x, y: wp.y },
                                    tool: root.activeTool
                                }
                            };
                            mapSessionController.sendMapUpdate(JSON.stringify(payload));
                        }
                    }
                }
            }
        }
        
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
                
                var drawingsStr = JSON.stringify(allDrawings);
                var drawingsChanged = (drawingsStr !== parent.lastSentDrawingsJson);
                
                var mx = globalHoverTracker.hovered ? globalHoverTracker.point.position.x : mapMouseArea.mouseX;
                var my = globalHoverTracker.hovered ? globalHoverTracker.point.position.y : mapMouseArea.mouseY;
                var wp = screenToWorld(mx, my);
                var isMouseActive = globalHoverTracker.hovered && Qt.application.active;
                
                var data = {
                    user: {
                        nick: typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido",
                        avatar: typeof chatController !== "undefined" ? chatController.currentUserAvatar : "",
                        id: currentUserId,
                        status: isMouseActive ? { x: wp.x, y: wp.y } : null,
                        tool: root.activeTool
                    }
                };
                
                if (drawingsChanged) {
                    data.drawings = allDrawings;
                }
                
                var jsonStr = JSON.stringify(data);
                
                // For debug log: show local user + all active remote users separately
                var debugLog = {
                    me: data.user,
                    active_users: root.remoteCursorsDict, // dictionary of remote users
                    drawings_synced: drawingsChanged
                };
                var debugStr = JSON.stringify(debugLog, function(key, val) {
                    if (val && typeof val.x === 'number') val.x = Math.round(val.x * 100) / 100;
                    if (val && typeof val.y === 'number') val.y = Math.round(val.y * 100) / 100;
                    return val;
                }, 2);
                debugStr = debugStr.replace(/\{\n\s+"x": ([\d.-]+),\n\s+"y": ([\d.-]+)\n\s+\}/g, '{ "x": $1, "y": $2 }');
                jsonDebugWindow.jsonOutput = debugStr;
                
                if (typeof mapSessionController !== "undefined" && mapSessionController.currentRoom !== "") {
                    mapSessionController.sendMapUpdate(jsonStr);
                    if (drawingsChanged) {
                        parent.lastSentDrawingsJson = drawingsStr;
                    }
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
        width: tooltipRow.implicitWidth + 20
        height: tooltipRow.implicitHeight + 12
        color: "#f00f172a" // sleek slate 900
        border.color: "#3b82f6" // blue 500
        border.width: 1
        radius: 6
        z: 9999
        
        Row {
            id: tooltipRow
            anchors.centerIn: parent
            spacing: 6
            Text {
                text: "✏️"
                font.pixelSize: 12
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                color: "#e2e8f0"
                font.pixelSize: 13
                font.bold: true
                text: drawingHoverTooltip.tooltipText
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
