import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import QtQuick.Layouts
import "SlangTerms.js" as SlangTerms
import "Vehicles.js" as VehiclesData
import "MapToolsData.js" as ToolsData
import GG.Map 1.0

Item {
    id: root
    clip: true
    focus: true

    CommandPalette {
        id: commandPalette
        onCommandExecuted: function(cmdId) {
            if (cmdId === "select_all") {
                // Not implemented yet
            } else if (cmdId === "clear_drawings") {
                if (typeof mapSessionController !== 'undefined') mapSessionController.pushEvent("clear_all", "all", "{}");
                root.currentDrawing = null;
            } else if (cmdId === "clear_artillery") {
                root.savedArtilleries = [];
            } else if (cmdId === "center_map") {
                root.centerX = root.mapWidthAtZoom / 2;
                root.centerY = root.mapHeightAtZoom / 2;
            } else if (cmdId === "toggle_grid") {
                // Custom logic
            } else if (cmdId === "export_map") {
                // Custom logic
            } else if (cmdId === "import_map") {
                // Custom logic
            } else if (cmdId === "toggle_theme") {
                // Custom logic
            }
        }
    }

    // --- KEYBOARD SHORTCUTS ---
    Shortcut { sequence: "Ctrl+K"; onActivated: commandPalette.open() }
    Shortcut { sequence: "V"; onActivated: if (!polygonNameDialogVisible && !routeNameDialogVisible && !commandPalette.visible) { root.activeTool = "pan"; root.showToolSettings = false; } }
    Shortcut { sequence: "B"; onActivated: if (!polygonNameDialogVisible && !routeNameDialogVisible && !commandPalette.visible) { root.activeTool = "brush"; root.showToolSettings = true; } }
    Shortcut { sequence: "L"; onActivated: if (!polygonNameDialogVisible && !routeNameDialogVisible && !commandPalette.visible) { root.activeTool = "arrow"; root.showToolSettings = true; } }
    Shortcut { sequence: "R"; onActivated: if (!polygonNameDialogVisible && !routeNameDialogVisible && !commandPalette.visible) { root.activeTool = "route"; root.showToolSettings = true; } }
    Shortcut { sequence: "P"; onActivated: if (!polygonNameDialogVisible && !routeNameDialogVisible && !commandPalette.visible) { root.activeTool = "polygon"; root.showToolSettings = true; } }
    Shortcut { sequence: "T"; onActivated: if (!polygonNameDialogVisible && !routeNameDialogVisible && !commandPalette.visible) { root.activeTool = "text"; root.showToolSettings = false; } }
    Shortcut { sequence: "M"; onActivated: if (!polygonNameDialogVisible && !routeNameDialogVisible && !commandPalette.visible) { root.activeTool = "vehicle"; root.showToolSettings = true; } }
    Shortcut { sequence: "A"; onActivated: if (!polygonNameDialogVisible && !routeNameDialogVisible && !commandPalette.visible) { root.activeTool = "artillery"; artilleryModal.visible = true; } }
    Shortcut { sequence: "E"; onActivated: if (!polygonNameDialogVisible && !routeNameDialogVisible && !commandPalette.visible) { root.activeTool = "eraser"; root.showToolSettings = true; } }
    Shortcut { sequence: "Esc"; onActivated: { if (commandPalette.visible) commandPalette.visible = false; else if (root.currentDrawing) root.currentDrawing = null; } }

    property var clipboardDrawing: null
    Shortcut { 
        sequence: "Ctrl+C"
        onActivated: {
            if (root.selectedVehicleIndex !== -1 && root.drawings[root.selectedVehicleIndex]) {
                root.clipboardDrawing = JSON.parse(JSON.stringify(root.drawings[root.selectedVehicleIndex]));
            }
        }
    }
    
    property string hoveredDrawingId: ""
    property var hoveredDrawing: null
    
    Shortcut { 
        sequence: "Ctrl+V"
        onActivated: {
            if (root.clipboardDrawing) {
                var newDrawing = JSON.parse(JSON.stringify(root.clipboardDrawing));
                newDrawing.id = "draw_" + Date.now();
                // Apply generic offset to all points if they exist
                if (newDrawing.points) {
                    for(var i=0; i<newDrawing.points.length; i++) {
                        newDrawing.points[i].x += 25;
                        newDrawing.points[i].y += 25;
                    }
                } else if (newDrawing.x !== undefined && newDrawing.y !== undefined) {
                    newDrawing.x += 25;
                    newDrawing.y += 25;
                } else if (newDrawing.start && newDrawing.end) {
                    newDrawing.start.x += 25; newDrawing.start.y += 25;
                    newDrawing.end.x += 25; newDrawing.end.y += 25;
                }
                
                if (typeof mapSessionController !== 'undefined') {
                    mapSessionController.pushEvent("add_drawing", newDrawing.id, JSON.stringify(newDrawing));
                }
            }
        }
    }
    Shortcut { 
        sequence: "Ctrl+X"
        onActivated: {
            if (root.selectedVehicleIndex !== -1 && root.drawings[root.selectedVehicleIndex]) {
                root.clipboardDrawing = JSON.parse(JSON.stringify(root.drawings[root.selectedVehicleIndex]));
                if (typeof mapSessionController !== 'undefined') {
                    mapSessionController.pushEvent("remove_drawing", root.drawings[root.selectedVehicleIndex].id, "{}");
                }
                root.selectedVehicleIndex = -1;
            }
        }
    }

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
    property bool showTacticalSymbols: true
    property bool showTacticalLines: true
    
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
    property int activeThickness: 3
    property real activeOpacity: 1.0
    property string activeLineStyle: "solid"
    property string activeArrowPosition: "end"
    property string activeArrowPlacement: "center"
    property string activeSymbol: "defense"
    property bool activeHighlight: false
    property int activeExpiration: 0
    property bool activeLocked: false
    property bool brushNameDialogVisible: false
    property bool skipBrushNameDialog: false

    property string inspectedDrawingId: ""
    property var inspectedDrawing: null
    property bool inspectMode: false

    Timer {
        id: expirationTimer
        interval: 1000
        running: true
        repeat: true
        onTriggered: {
            if (!root.drawings || root.drawings.length === 0) return;
            var now = Date.now();
            for (var i = 0; i < root.drawings.length; i++) {
                var d = root.drawings[i];
                if (d.expiresAt && d.expiresAt > 0 && d.expiresAt <= now) {
                    var dId = d.id || d._id || d.eventId;
                    if (typeof mapSessionController !== 'undefined') {
                        if (dId) {
                            mapSessionController.pushEvent("remove_drawing", dId, "{}");
                            removeDrawingLocally(dId);
                        }
                    }
                }
            }
        }
    }
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
    property var usersDict: ({})
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
        function onLogAppended(logStr) {
            try {
                var parsed = JSON.parse(logStr);
                
                if (parsed.serverVersion !== undefined) jsonDebugWindow.serverVersion = parsed.serverVersion;
                if (parsed.action !== undefined) jsonDebugWindow.latestLogType = parsed.action;
                if (parsed.category === 'SINCRONIZAÇÃO' && parsed.action === 'queue_event') {
                    jsonDebugWindow.pendingQueueSize += 1;
                }
                if (parsed.action === 'event_ack') {
                    jsonDebugWindow.pendingQueueSize = Math.max(0, jsonDebugWindow.pendingQueueSize - 1);
                }
                if (parsed.action === 'snapshot_download' || parsed.action === 'connect') {
                    jsonDebugWindow.pendingQueueSize = 0;
                }
                
                logStr = JSON.stringify(parsed, null, 2);
            } catch (e) {}
            var currentLog = jsonDebugWindow.jsonOutput || "";
            jsonDebugWindow.jsonOutput = logStr + "\n\n" + currentLog.substring(0, 10000);
        }
        function onMapUpdated(dataStr) {
            try {
                var date = new Date();
                var h = date.getHours();
                var m = date.getMinutes();
                root.lastSyncTime = (h < 10 ? "0" + h : h) + ":" + (m < 10 ? "0" + m : m);
                
                var data = JSON.parse(dataStr);
                // With Event Sourcing, data is an event object.
                
                if (data.type === "cursor_move") {
                    var cursors = root.usersDict;
                    if (data.payload.status === null) {
                        delete cursors[data.userId];
                        for (var i = 0; i < remoteCursorsModel.count; i++) {
                            if (remoteCursorsModel.get(i).userId === data.userId) {
                                remoteCursorsModel.remove(i);
                                break;
                            }
                        }
                    } else {
                        cursors[data.userId] = data.payload;
                        var found = false;
                        for (var j = 0; j < remoteCursorsModel.count; j++) {
                            if (remoteCursorsModel.get(j).userId === data.userId) {
                                remoteCursorsModel.setProperty(j, "wx", data.payload.status.x);
                                remoteCursorsModel.setProperty(j, "wy", data.payload.status.y);
                                remoteCursorsModel.setProperty(j, "nick", data.payload.nick || "");
                                remoteCursorsModel.setProperty(j, "avatar", data.payload.avatar || "");
                                remoteCursorsModel.setProperty(j, "tool", data.payload.tool || "pan");
                                found = true;
                                break;
                            }
                        }
                        if (!found) {
                            remoteCursorsModel.append({
                                userId: data.userId,
                                wx: data.payload.status.x,
                                wy: data.payload.status.y,
                                nick: data.payload.nick || "",
                                avatar: data.payload.avatar || "",
                                tool: data.payload.tool || "pan"
                            });
                        }
                    }
                    root.usersDict = cursors;
                } else if (data.type === "full_state") {
                    if (data.payload.drawings) {
                        root.drawings = data.payload.drawings;
                    }
                    if (data.payload.tacticalSymbols) {
                        root.tacticalSymbols = data.payload.tacticalSymbols;
                    }
                } else if (data.type === "add_drawing") {
                    var newDrawings = root.drawings.slice();
                    newDrawings.push(data.payload);
                    // Do not emit pushEvent since this came from the server
                    // root.drawings = newDrawings; // Managed by SyncManager via onMapUpdated
                }
            } catch (e) {}
        }
        function onUserKicked() {
            kickedPopup.open();
        }
    }

    property bool showToolSettings: false
    property var drawings: [] // stores objects like {type: "brush", color: "red", thickness: 3, points: [{x,y}...]}
    
    function removeDrawingLocally(dId) {
        if (!root.drawings || !dId) return;
        var newDrawings = [];
        for (var i = 0; i < root.drawings.length; i++) {
            var d = root.drawings[i];
            var thisId = d.id || d._id || d.eventId;
            if (thisId !== dId) {
                newDrawings.push(d);
            }
        }
        root.drawings = newDrawings;
    }
    
    property var tacticalSymbols: [] // stores objects like {type: "tactical_symbol", symbolId: "defense", ...}
    property var currentDrawing: null // currently active drawing while mouse is pressed
    property int selectedSymbolIndex: -1
    property real liveSymbolRotation: 0
    property real liveSymbolScale: 1.0
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
    
    onUsersDictChanged: {
        var aUsers = [];
        var keys = Object.keys(root.usersDict);
        for (var i = 0; i < keys.length; i++) {
            var obj = root.usersDict[keys[i]];
            aUsers.push({ id: obj.id, name: obj.nick || keys[i], avatar: obj.avatar || "" });
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
        running: root.hasAnimatedDrawings || root.hoveredDrawingId !== "" || root.inspectedDrawingId !== ""
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
            showTacticalLines: root.showTacticalLines
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
            hoveredDrawingId: root.hoveredDrawingId
            inspectedDrawingId: root.inspectMode && root.showToolSettings ? root.inspectedDrawingId : ""
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
                            // root.drawings = newDrawings; // Managed by SyncManager via onMapUpdated
                            if (typeof mapSessionController !== 'undefined') {
                                if (newDrawings.length > 0) {
                                    var lastAdded = newDrawings[newDrawings.length - 1];
                                    mapSessionController.pushEvent("add_drawing", "draw_" + Date.now(), JSON.stringify(lastAdded));
                                } else {
                                    mapSessionController.pushEvent("clear_all", "all", "{}");
                                }
                            }
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
                                // root.drawings = newDrawings; // Managed by SyncManager via onMapUpdated
                            if (typeof mapSessionController !== 'undefined') {
                                if (newDrawings.length > 0) {
                                    var lastAdded = newDrawings[newDrawings.length - 1];
                                    mapSessionController.pushEvent("add_drawing", "draw_" + Date.now(), JSON.stringify(lastAdded));
                                } else {
                                    mapSessionController.pushEvent("clear_all", "all", "{}");
                                }
                            }
                                root.selectedVehicleIndex = -1;
                            }
                        }
                    }
                }
            }
        }

        // Tactical Symbols layer
        Repeater {
            model: root.tacticalSymbols
            delegate: Item {
                id: tsItem
                visible: root.showTacticalSymbols
                
                property real wx: modelData.x ? modelData.x : 0
                property real wy: modelData.y ? modelData.y : 0
                property string symIcon: modelData.icon || "🛡"
                property string symColor: modelData.color || "#ffffff"
                
                x: (wx * getZoomFactor()) - root.centerX + (root.width / 2) - width/2
                y: (wy * getZoomFactor()) - root.centerY + (root.height / 2) - height/2
                z: root.selectedSymbolIndex === index ? 165 : 160
                
                width: 40 * (modelData.scale || 1.0)
                height: 40 * (modelData.scale || 1.0)
                
                rotation: root.selectedSymbolIndex === index ? root.liveSymbolRotation : (modelData.rotation || 0)
                
                Text {
                    anchors.centerIn: parent
                    text: tsItem.symIcon
                    color: tsItem.symColor
                    font.pixelSize: 32 * (modelData.scale || 1.0)
                    style: Text.Outline
                    styleColor: "black"
                }
                
                MouseArea {
                    anchors.fill: parent
                    drag.target: null
                    property real startMouseWorldX
                    property real startMouseWorldY
                    property real startWx
                    property real startWy
                    onPressed: function(mouse) {
                        root.selectedSymbolIndex = index;
                        root.liveSymbolRotation = modelData.rotation || 0;
                        root.liveSymbolScale = modelData.scale || 1.0;
                        
                        var globalMouse = mapToItem(root, mouse.x, mouse.y);
                        startMouseWorldX = globalMouse.x;
                        startMouseWorldY = globalMouse.y;
                        startWx = tsItem.wx;
                        startWy = tsItem.wy;
                    }
                    onPositionChanged: function(mouse) {
                        if (pressed) {
                            var globalMouse = mapToItem(root, mouse.x, mouse.y);
                            var dx = globalMouse.x - startMouseWorldX;
                            var dy = globalMouse.y - startMouseWorldY;
                            tsItem.wx = startWx + (dx / getZoomFactor());
                            tsItem.wy = startWy + (dy / getZoomFactor());
                            
                            startMouseWorldX = globalMouse.x;
                            startMouseWorldY = globalMouse.y;
                            startWx = tsItem.wx;
                            startWy = tsItem.wy;
                        }
                    }
                    onReleased: function(mouse) {
                        if (startWx !== tsItem.wx || startWy !== tsItem.wy) {
                            var modified = Object.assign({}, root.tacticalSymbols[index]);
                            modified.x = tsItem.wx;
                            modified.y = tsItem.wy;
                            if (typeof mapSessionController !== 'undefined') {
                                mapSessionController.pushEvent("update_tactical_symbol", modified.id, JSON.stringify(modified));
                            }
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
                    visible: root.selectedSymbolIndex === index
                    
                    Rectangle {
                        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: -10
                        width: 20; height: 20; radius: 10; color: "#ef4444"
                        Text { anchors.centerIn: parent; text: "×"; color: "white"; font.bold: true; font.pixelSize: 14 }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                var toDelete = root.tacticalSymbols[index];
                                if (typeof mapSessionController !== 'undefined') {
                                    mapSessionController.pushEvent("remove_tactical_symbol", toDelete.id, "{}");
                                }
                                root.selectedSymbolIndex = -1;
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
                text: root.tr("map.filter.tactical_symbols", "Mostrar Símbolos Táticos")
                checked: root.showTacticalSymbols
                onCheckedChanged: root.showTacticalSymbols = checked
            }
            StyledCheckBox { 
                text: root.tr("map.filter.tactical_lines", "Mostrar Linhas Táticas")
                checked: root.showTacticalLines
                onCheckedChanged: root.showTacticalLines = checked
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
        property real lastCursorSyncTime: 0
        
        function hitTestAt(sx, sy) {
            var wp = screenToWorld(sx, sy);
            
            // Check tactical symbols first (they are usually smaller/on top)
            for (var k = root.tacticalSymbols.length - 1; k >= 0; k--) {
                var ts = root.tacticalSymbols[k];
                var distTS = Math.sqrt(Math.pow(wp.x - ts.x, 2) + Math.pow(wp.y - ts.y, 2));
                if (distTS <= (30 * (ts.scale || 1.0)) / root.getZoomFactor()) {
                    return ts;
                }
            }
            
            // Check drawings in reverse order (top to bottom)
            for (var i = root.drawings.length - 1; i >= 0; i--) {
                var d = root.drawings[i];
                var hit = false;
                var baseThickness = d.thickness || 3;
                var threshold = Math.max(baseThickness * 2, 20) / root.getZoomFactor();
                
                if (d.type === "polygon") {
                    hit = isPointInPolygon(wp.x, wp.y, d.points);
                } else if (d.type === "brush" || d.type === "route" || d.type === "defensive_line") {
                    if (d.points.length === 1) {
                        var distPt = Math.sqrt(Math.pow(wp.x - d.points[0].x, 2) + Math.pow(wp.y - d.points[0].y, 2));
                        if (distPt <= threshold) { hit = true; }
                    } else {
                        for (var j = 0; j < d.points.length - 1; j++) {
                            var dist = distanceToSegment(wp.x, wp.y, d.points[j].x, d.points[j].y, d.points[j+1].x, d.points[j+1].y);
                            if (dist <= threshold) {
                                hit = true; break;
                            }
                        }
                    }
                } else if (d.type === "arrow" || d.type === "artillery") {
                    var dist2 = distanceToSegment(wp.x, wp.y, d.start.x, d.start.y, d.end.x, d.end.y);
                    if (dist2 <= threshold) {
                        hit = true;
                    }
                } else if (d.type === "parabola") {
                    var sWp = apiToWorld(d.start.x, d.start.y);
                    var eWp = apiToWorld(d.end.x, d.end.y);
                    var pDist = distanceToParabola(wp.x, wp.y, sWp.x, sWp.y, eWp.x, eWp.y);
                    if (pDist <= threshold) {
                        hit = true;
                    }
                }
                
                if (hit) return d;
            }
            return null;
        }

        function eraseAt(sx, sy) {
            var wp = screenToWorld(sx, sy);
            var removed = false;
            var newDrawings = [];
            
            for (var i = 0; i < root.drawings.length; i++) {
                var d = root.drawings[i];
                if (d.locked) {
                    newDrawings.push(d);
                    continue;
                }
                var hit = false;
                var baseThickness = d.thickness || 3;
                var threshold = Math.max(baseThickness * 2, 20) / root.getZoomFactor();
                
                if (d.type === "polygon") {
                    hit = isPointInPolygon(wp.x, wp.y, d.points);
                } else if (d.type === "brush" || d.type === "route") {
                    if (d.points.length === 1) {
                        var distPtErase = Math.sqrt(Math.pow(wp.x - d.points[0].x, 2) + Math.pow(wp.y - d.points[0].y, 2));
                        if (distPtErase <= threshold) { hit = true; }
                    } else {
                        for (var j = 0; j < d.points.length - 1; j++) {
                            var dist = distanceToSegment(wp.x, wp.y, d.points[j].x, d.points[j].y, d.points[j+1].x, d.points[j+1].y);
                            if (dist <= threshold) {
                                hit = true; break;
                            }
                        }
                    }
                } else if (d.type === "arrow" || d.type === "artillery") {
                    var dist2 = distanceToSegment(wp.x, wp.y, d.start.x, d.start.y, d.end.x, d.end.y);
                    if (dist2 <= threshold) {
                        hit = true;
                    }
                } else if (d.type === "parabola") {
                    var sWp = apiToWorld(d.start.x, d.start.y);
                    var eWp = apiToWorld(d.end.x, d.end.y);
                    var pDist = distanceToParabola(wp.x, wp.y, sWp.x, sWp.y, eWp.x, eWp.y);
                    if (pDist <= threshold) {
                        hit = true;
                    }
                } else if (d.type === "vehicle") {
                    var distVeh = Math.sqrt(Math.pow(wp.x - d.x, 2) + Math.pow(wp.y - d.y, 2));
                    if (distVeh <= (35 * (d.scale || 1.0)) / root.getZoomFactor()) {
                        hit = true;
                    }
                }
                
                if (hit) {
                    if (typeof mapSessionController !== 'undefined') {
                        mapSessionController.pushEvent("remove_drawing", d.id || d._id || d.eventId, "{}");
                    }
                    removed = true;
                } else {
                    newDrawings.push(d);
                }
            }
            
            for (var k = 0; k < root.tacticalSymbols.length; k++) {
                var ts = root.tacticalSymbols[k];
                if (ts.locked) continue;
                var distTS = Math.sqrt(Math.pow(wp.x - ts.x, 2) + Math.pow(wp.y - ts.y, 2));
                if (distTS <= (30 * (ts.scale || 1.0)) / root.getZoomFactor()) {
                    if (typeof mapSessionController !== 'undefined') {
                        mapSessionController.pushEvent("remove_tactical_symbol", ts.id, "{}");
                    }
                    removed = true;
                }
            }
            
            if (removed) {
                // root.drawings = newDrawings; // Managed by SyncManager via onMapUpdated
                            if (typeof mapSessionController !== 'undefined') {
                                if (newDrawings.length > 0) {
                                    var lastAdded = newDrawings[newDrawings.length - 1];
                                    mapSessionController.pushEvent("add_drawing", "draw_" + Date.now(), JSON.stringify(lastAdded));
                                } else {
                                    mapSessionController.pushEvent("clear_all", "all", "{}");
                                }
                            }
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
                
                if (root.activeLineStyle === "symbol") {
                    var symColor = root.activeColor;
                    var symIcon = root.activeSymbol;
                    var syms = SymbolData.getSymbols();
                    for (var s = 0; s < syms.length; s++) {
                        if (syms[s].id === root.activeSymbol) {
                            symIcon = syms[s].icon;
                            break;
                        }
                    }
                    var ts = {
                        id: "ts_" + Date.now(),
                        type: "tactical_symbol",
                        symbolId: root.activeSymbol,
                        icon: symIcon,
                        x: wp.x,
                        y: wp.y,
                        rotation: 0,
                        scale: 1.0,
                        color: symColor,
                        locked: root.activeLocked,
                        createdBy: cUserBrush,
                        createdAt: Date.now(),
                        updatedAt: Date.now()
                    };
                    if (typeof mapSessionController !== 'undefined') {
                        mapSessionController.pushEvent("add_tactical_symbol", ts.id, JSON.stringify(ts));
                    }
                    root.currentDrawing = null;
                } else {
                    var expiresAt = root.activeExpiration > 0 ? (Date.now() + root.activeExpiration * 1000) : null;
                    var cUserId = typeof chatController !== "undefined" ? chatController.currentUserId : "";
                    root.currentDrawing = { 
                        type: "brush", 
                        color: root.activeColor, 
                        thickness: root.activeThickness, 
                        opacity: root.activeOpacity, 
                        lineStyle: root.activeLineStyle, 
                        arrowPosition: root.activeArrowPosition,
                        arrowPlacement: root.activeArrowPlacement,
                        highlight: root.activeHighlight, 
                        locked: root.activeLocked, 
                        expiresAt: expiresAt, 
                        points: [wp], 
                        user: cUserBrush,
                        createdBy: cUserId,
                        createdAt: Date.now(),
                        updatedAt: Date.now()
                    };
                }
            } else if (root.activeTool === "arrow") {
                var wp2 = screenToWorld(mouse.x, mouse.y);
                var nearestNode2 = findNearestNode(wp2, 15);
                if (nearestNode2) wp2 = nearestNode2;
                var cUserArrow = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                var cUserArrowId = typeof chatController !== "undefined" ? chatController.currentUserId : "";
                root.currentDrawing = { 
                    type: "arrow", color: root.activeColor, thickness: root.activeThickness, 
                    start: wp2, end: wp2, user: cUserArrow, createdBy: cUserArrowId, createdAt: Date.now(), updatedAt: Date.now() 
                };
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
                if (!didPan) {
                    var hitP = hitTestAt(mouse.x, mouse.y);
                    if (hitP) {
                        root.inspectedDrawingId = hitP.id || hitP._id || hitP.eventId || "";
                        root.inspectedDrawing = hitP;
                        root.inspectMode = true;
                        
                        // Switch active tool to the drawing's tool so the proper settings menu loads
                        var dType = hitP.type || "brush";
                        if (dType === "defensive_line" || dType === "minefield" || dType === "checkpoint" || dType === "line") dType = "brush";
                        if (dType !== "brush" && dType !== "polygon" && dType !== "route" && dType !== "vehicle" && dType !== "arrow" && dType !== "text") dType = "brush";
                        
                        root.activeTool = dType;
                        root.showToolSettings = true;
                        
                        if (toolSettingsLoader.item && typeof toolSettingsLoader.item.setCurrentTab === 'function') {
                            toolSettingsLoader.item.setCurrentTab("info");
                        }
                    } else {
                        root.inspectedDrawingId = "";
                        root.inspectedDrawing = null;
                        root.inspectMode = false;
                    }
                }
            } else if (root.activeTool === "brush") {
                if (!didPan) {
                    var hitB = hitTestAt(mouse.x, mouse.y);
                    if (hitB) {
                        root.currentDrawing = null; // Discard the point created in onPressed!
                        root.inspectedDrawingId = hitB.id || hitB._id || hitB.eventId || "";
                        root.inspectedDrawing = hitB;
                        root.inspectMode = true;
                        root.showToolSettings = true;
                        if (toolSettingsLoader.item && typeof toolSettingsLoader.item.setCurrentTab === 'function') {
                            toolSettingsLoader.item.setCurrentTab("info");
                        }
                        return; // Don't draw a dot if we hit something
                    } else {
                        root.inspectedDrawingId = "";
                        root.inspectedDrawing = null;
                        root.inspectMode = false;
                    }
                }
                
                // If we didn't hit anything, continue drawing brush
                if (!didPan) {
                    var wpB = screenToWorld(mouse.x, mouse.y);
                    var nearestNodeB = findNearestNode(wpB, 15);
                    if (nearestNodeB) wpB = nearestNodeB;
                    
                    if (!root.currentDrawing || root.currentDrawing.type !== "brush") {
                        var cUserBrush = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                        var cUserBrushId = typeof chatController !== "undefined" ? chatController.currentUserId : "";
                        root.currentDrawing = { 
                            type: "brush", 
                            color: root.activeColor, 
                            thickness: root.activeThickness, 
                            opacity: root.activeOpacity, 
                            lineStyle: root.activeLineStyle, 
                            arrowPosition: root.activeArrowPosition, 
                            arrowPlacement: root.activeArrowPlacement,
                            highlight: root.activeHighlight,
                            locked: root.activeLocked,
                            points: [wpB], 
                            user: cUserBrush,
                            createdBy: cUserBrushId,
                            createdAt: Date.now(),
                            updatedAt: Date.now()
                        };
                    } else {
                        var b = Object.assign({}, root.currentDrawing);
                        b.points = b.points.slice();
                        b.points.push(wpB);
                        root.currentDrawing = b;
                    }
                }
                if (root.activeTool === "brush" && !root.skipBrushNameDialog) {
                    root.brushNameDialogVisible = true;
                    if (typeof brushNameInput !== "undefined") brushNameInput.forceActiveFocus();
                } else if (root.activeTool === "brush") {
                    var newDrawings = root.drawings.slice();
                    var lastB = Object.assign({}, root.currentDrawing);
                    lastB.id = "draw_" + Date.now();
                    var exp = root.activeExpiration > 0 ? (Date.now() + root.activeExpiration * 1000) : null;
                    if (exp) lastB.expiresAt = exp;
                    newDrawings.push(lastB);
                    if (typeof mapSessionController !== 'undefined') {
                        mapSessionController.pushEvent("add_drawing", lastB.id, JSON.stringify(lastB));
                    }
                    root.currentDrawing = null;
                }
            } else if (root.activeTool === "polygon") {
                cursorShape = Qt.CrossCursor;
                if (!didPan && !root.polygonNameDialogVisible) {
                    var wp = screenToWorld(mouse.x, mouse.y);
                    if (!root.currentDrawing || root.currentDrawing.type !== "polygon") {
                        var cUserPoly = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                        var cUserPolyId = typeof chatController !== "undefined" ? chatController.currentUserId : "";
                        root.currentDrawing = { 
                            type: "polygon", color: root.activeColor, thickness: root.activeThickness, 
                            points: [wp], user: cUserPoly, createdBy: cUserPolyId, createdAt: Date.now(), updatedAt: Date.now() 
                        };
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
                    if (!root.currentDrawing || root.currentDrawing.type !== "route" || root.currentDrawing.points.length === 0) {
                        var cUserRoute = typeof chatController !== "undefined" ? chatController.currentUserName : "Desconhecido";
                        var cUserRouteId = typeof chatController !== "undefined" ? chatController.currentUserId : "";
                        root.currentDrawing = { 
                            type: "route", color: root.activeColor, thickness: root.activeThickness, 
                            points: [wpRoute], user: cUserRoute, createdBy: cUserRouteId, createdAt: Date.now(), updatedAt: Date.now() 
                        };
                    } else {
                        var startPoint = root.currentDrawing.points[0];
                        if (typeof routingController !== "undefined") {
                            var resultStr = routingController.calculateRoute(startPoint.x, startPoint.y, wpRoute.x, wpRoute.y);
                            var result = JSON.parse(resultStr);
                            if (result && result.points && result.points.length > 0) {
                                var route = Object.assign({}, root.currentDrawing);
                                route.points = result.points;
                                route.cost = result.cost;
                                route.time_mins = result.time_mins;
                                root.currentDrawing = route;
                                root.routeNameDialogVisible = true;
                                if (typeof routeNameInput !== "undefined") routeNameInput.forceActiveFocus();
                            } else {
                                console.log("Failed to calculate route:", resultStr);
                                var routeFail = Object.assign({}, root.currentDrawing);
                                routeFail.points = routeFail.points.slice();
                                routeFail.points.push(wpRoute);
                                root.currentDrawing = routeFail;
                            }
                        } else {
                            var routeFallback = Object.assign({}, root.currentDrawing);
                            routeFallback.points = routeFallback.points.slice();
                            routeFallback.points.push(wpRoute);
                            root.currentDrawing = routeFallback;
                        }
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
                    // root.drawings = newDrawings; // Managed by SyncManager via onMapUpdated
                            if (typeof mapSessionController !== 'undefined') {
                                if (newDrawings.length > 0) {
                                    var lastAdded = newDrawings[newDrawings.length - 1];
                                    mapSessionController.pushEvent("add_drawing", "draw_" + Date.now(), JSON.stringify(lastAdded));
                                } else {
                                    mapSessionController.pushEvent("clear_all", "all", "{}");
                                }
                            }
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
                    if (root.activeTool === "brush" && !root.skipBrushNameDialog) {
                        root.brushNameDialogVisible = true;
                        if (typeof brushNameInput !== "undefined") brushNameInput.forceActiveFocus();
                    } else {
                        var newDrawings = root.drawings.slice();
                        newDrawings.push(root.currentDrawing);
                        // root.drawings = newDrawings; // Managed by SyncManager via onMapUpdated
                        if (typeof mapSessionController !== 'undefined') {
                            if (newDrawings.length > 0) {
                                var lastAdded = newDrawings[newDrawings.length - 1];
                                mapSessionController.pushEvent("add_drawing", "draw_" + Date.now(), JSON.stringify(lastAdded));
                            } else {
                                mapSessionController.pushEvent("clear_all", "all", "{}");
                            }
                        }
                        root.currentDrawing = null;
                    }
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
                if (root.activeTool === "brush" && !root.skipBrushNameDialog) {
                    root.brushNameDialogVisible = true;
                    if (typeof brushNameInput !== "undefined") brushNameInput.forceActiveFocus();
                } else {
                    var newDrawings = root.drawings.slice();
                    newDrawings.push(root.currentDrawing);
                    // root.drawings = newDrawings; // Managed by SyncManager via onMapUpdated
                    if (typeof mapSessionController !== 'undefined') {
                        if (newDrawings.length > 0) {
                            var lastAdded = newDrawings[newDrawings.length - 1];
                            mapSessionController.pushEvent("add_drawing", "draw_" + Date.now(), JSON.stringify(lastAdded));
                        } else {
                            mapSessionController.pushEvent("clear_all", "all", "{}");
                        }
                    }
                    root.currentDrawing = null;
                }
            }
        }
        
        onPositionChanged: function(mouse) {
            if (root.activeTool === "artillery" && root.artilleryStep === 1) {
                var wpArt = screenToWorld(mouse.x, mouse.y);
                root.artilleryTarget = wpArt;
            }
            if (isDragging) {
                if (root.activeTool === "pan" || root.activeTool === "polygon" || root.activeTool === "route" || root.activeTool === "vehicle" || root.activeTool === "brush") {
                    var dx = mouse.x - lastX;
                    var dy = mouse.y - lastY;
                    
                    var dist = Math.sqrt(Math.pow(mouse.x - pressX, 2) + Math.pow(mouse.y - pressY, 2));
                    if (dist > 15) {
                        didPan = true;
                    }
                    
                    if (didPan || root.activeTool === "pan") {
                        if (root.activeTool !== "brush") {
                            root.centerX = Math.max(0, Math.min(root.mapWidthAtZoom, root.centerX - dx));
                            root.centerY = Math.max(0, Math.min(root.mapHeightAtZoom, root.centerY - dy));
                            lastX = mouse.x;
                            lastY = mouse.y;
                        }
                    }
                }
                
                if (root.activeTool === "brush" && root.currentDrawing) {
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
                        if (rdist < 20 / root.getZoomFactor()) {
                            foundHover = route;
                            break;
                        }
                    }
                    if (root.logisticsHoveredRoute !== foundHover) {
                        root.logisticsHoveredRoute = foundHover;
                    }
                }
                
                // Hover for drawings
                if (!isDragging) {
                    var foundHoverDrawing = hitTestAt(mouse.x, mouse.y);
                    
                    if (foundHoverDrawing) {
                        var hId = foundHoverDrawing.id || foundHoverDrawing._id || foundHoverDrawing.eventId || "";
                        if (root.hoveredDrawingId !== hId) {
                            console.log("[HOVER] Novo item detectado: " + hId);
                            root.hoveredDrawingId = hId;
                            root.hoveredDrawing = foundHoverDrawing;
                        }
                        drawingHoverTooltip.drawingData = foundHoverDrawing;
                        drawingHoverTooltip.x = mouse.x + 15;
                        drawingHoverTooltip.y = mouse.y + 15;
                        if (root.activeTool === "pan" || root.activeTool === "brush" || root.activeTool === "polygon" || root.activeTool === "route") {
                            cursorShape = Qt.PointingHandCursor;
                        }
                    } else {
                        if (root.hoveredDrawingId !== "") {
                            root.hoveredDrawingId = "";
                            root.hoveredDrawing = null;
                        }
                        drawingHoverTooltip.drawingData = null;
                        if (root.activeTool === "pan") cursorShape = Qt.OpenHandCursor;
                        else if (root.activeTool === "brush") cursorShape = Qt.CrossCursor;
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
    MapToolbar {
        id: drawingToolbar
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        anchors.horizontalCenter: parent.horizontalCenter
        z: 100
        
        activeTool: root.activeTool
        globalToolTip: globalToolTip
        
        onToolSelected: function(toolId) {
            if (root.currentDrawing) root.currentDrawing = null;
            root.activeTool = toolId;
            
            var toolObj = ToolsData.getToolById(toolId);
            if (toolObj && toolObj.hasProperties) {
                root.showToolSettings = true;
            } else {
                root.showToolSettings = false;
            }
            
            if (toolId === "artillery") {
                artilleryModal.visible = true;
            } else {
                artilleryModal.visible = false;
            }
            
            if (toolId === "logistics") {
                root.logisticsModalVisible = true;
                logisticsModal.open();
            } else {
                root.logisticsModalVisible = false;
            }
        }
        
        onToggleSettings: {
            root.showToolSettings = !root.showToolSettings;
        }
    }

    // --- DYNAMIC TOOL SETTINGS MODAL ---
    Loader {
        id: toolSettingsLoader
        property var activeToolObj: null
        
        Connections {
            target: root
            function onActiveToolChanged() {
                toolSettingsLoader.activeToolObj = ToolsData.getToolById(root.activeTool);
                console.log("[DEBUG] toolSettingsLoader onActiveToolChanged:", root.activeTool, "Obj:", toolSettingsLoader.activeToolObj ? toolSettingsLoader.activeToolObj.id : "null", "Visible:", root.showToolSettings);
            }
            function onSkipBrushNameDialogChanged() {
                if (toolSettingsLoader.item && toolSettingsLoader.item.skipBrushNameDialog !== undefined) {
                    toolSettingsLoader.item.skipBrushNameDialog = root.skipBrushNameDialog;
                }
            }
        }
        
        Component.onCompleted: {
            activeToolObj = ToolsData.getToolById(root.activeTool);
            console.log("[DEBUG] toolSettingsLoader completed:", root.activeTool);
        }
        
        onVisibleChanged: {
            console.log("[DEBUG] toolSettingsLoader visible changed to:", visible, "source:", source);
        }
        
        visible: root.showToolSettings && activeToolObj && activeToolObj.settingsComponent
        source: visible ? activeToolObj.settingsComponent : ""

        
        anchors.bottom: drawingToolbar.top
        anchors.bottomMargin: 16
        anchors.horizontalCenter: parent.horizontalCenter
        z: 100
        
        onItemChanged: {
            if (item) {
                if (item.skipBrushNameDialog !== undefined) item.skipBrushNameDialog = root.skipBrushNameDialog;
                if (item.inspectMode !== undefined) item.inspectMode = Qt.binding(function() { return root.inspectMode; });
                if (item.inspectedDrawing !== undefined) item.inspectedDrawing = Qt.binding(function() { return root.inspectedDrawing; });
            }
        }
        
        Connections {
            target: toolSettingsLoader.item
            ignoreUnknownSignals: true
            
            function onActiveColorChanged() {
                if (toolSettingsLoader.item && toolSettingsLoader.item.activeColor !== undefined) {
                    root.activeColor = toolSettingsLoader.item.activeColor;
                }
            }
            function onActiveThicknessChanged() {
                if (toolSettingsLoader.item && toolSettingsLoader.item.activeThickness !== undefined) {
                    root.activeThickness = toolSettingsLoader.item.activeThickness;
                }
            }
            function onActiveOpacityChanged() {
                if (toolSettingsLoader.item && toolSettingsLoader.item.activeOpacity !== undefined) {
                    root.activeOpacity = toolSettingsLoader.item.activeOpacity;
                }
            }
            function onActiveLineStyleChanged() { if (toolSettingsLoader.item && toolSettingsLoader.item.activeLineStyle !== undefined) root.activeLineStyle = toolSettingsLoader.item.activeLineStyle; }
            function onArrowPositionChanged() { if (toolSettingsLoader.item && toolSettingsLoader.item.arrowPosition !== undefined) root.activeArrowPosition = toolSettingsLoader.item.arrowPosition; }
            function onArrowPlacementChanged() { if (toolSettingsLoader.item && toolSettingsLoader.item.arrowPlacement !== undefined) root.activeArrowPlacement = toolSettingsLoader.item.arrowPlacement; }
            function onActiveSymbolChanged() { if (toolSettingsLoader.item && toolSettingsLoader.item.activeSymbol !== undefined) root.activeSymbol = toolSettingsLoader.item.activeSymbol; }
            function onActiveHighlightChanged() { if (toolSettingsLoader.item && toolSettingsLoader.item.activeHighlight !== undefined) root.activeHighlight = toolSettingsLoader.item.activeHighlight; }
            function onActiveExpirationChanged() { if (toolSettingsLoader.item && toolSettingsLoader.item.activeExpiration !== undefined) root.activeExpiration = toolSettingsLoader.item.activeExpiration; }
            function onActiveLockedChanged() { if (toolSettingsLoader.item && toolSettingsLoader.item.activeLocked !== undefined) root.activeLocked = toolSettingsLoader.item.activeLocked; }
            function onResetDescriptionDialog(ask) { root.skipBrushNameDialog = !ask; }
            
            function onColorChanged(c) { root.activeColor = c; }
            function onThicknessChanged(t) { root.activeThickness = t; }
            function onOpacityChanged(o) { root.activeOpacity = o; }
            
            function onClearAllRequested() {
                if (typeof mapSessionController !== 'undefined') {
                    mapSessionController.pushEvent("clear_all", "all", "{}");
                }
                root.currentDrawing = null;
                root.showToolSettings = false;
                root.activeTool = "pan";
            }
            function onFinishDrawing() {
                if (root.activeTool === "polygon" && root.currentDrawing && root.currentDrawing.type === "polygon") {
                    polygonNameDialogVisible = true;
                    polygonNameInput.forceActiveFocus();
                } else if (root.activeTool === "route" && root.currentDrawing && root.currentDrawing.type === "route") {
                    routeNameDialogVisible = true;
                    routeNameInput.forceActiveFocus();
                }
            }
            function onVehicleSelected(img, name) {
                root.activeVehicleImage = img;
                root.activeVehicleName = name;
            }
            function onVehicleCountChanged(c) {
                root.activeVehicleCount = c;
            }
        }
        
        onLoaded: {
            if (item) {
                if (item.activeColor !== undefined) item.activeColor = root.activeColor;
                if (item.activeThickness !== undefined) item.activeThickness = root.activeThickness;
                if (item.activeOpacity !== undefined) item.activeOpacity = root.activeOpacity;
                if (item.activeLineStyle !== undefined) item.activeLineStyle = root.activeLineStyle;
                if (item.activeArrowHead !== undefined) item.activeArrowHead = root.activeArrowHead;
                if (item.activeHighlight !== undefined) item.activeHighlight = root.activeHighlight;
                if (item.activeExpiration !== undefined) item.activeExpiration = root.activeExpiration;
                if (item.activeLocked !== undefined) item.activeLocked = root.activeLocked;
                if (item.activeToolId !== undefined) item.activeToolId = root.activeTool;
                
                if (item.activeVehicleImage !== undefined) item.activeVehicleImage = root.activeVehicleImage;
                if (item.activeVehicleName !== undefined) item.activeVehicleName = root.activeVehicleName;
                if (item.activeVehicleCount !== undefined) item.activeVehicleCount = root.activeVehicleCount;
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
                            // root.drawings = newDrawings; // Managed by SyncManager via onMapUpdated
                            if (typeof mapSessionController !== 'undefined') {
                                if (newDrawings.length > 0) {
                                    var lastAdded = newDrawings[newDrawings.length - 1];
                                    mapSessionController.pushEvent("add_drawing", "draw_" + Date.now(), JSON.stringify(lastAdded));
                                } else {
                                    mapSessionController.pushEvent("clear_all", "all", "{}");
                                }
                            }
                            root.currentDrawing = null;
                            polygonNameInput.text = "";
                            root.polygonNameDialogVisible = false;
                        }
                    }
                }
            }
        }
    }

    // --- BRUSH NAME MODAL ---
    Rectangle {
        id: brushNameModal
        visible: root.brushNameDialogVisible
        anchors.centerIn: parent
        width: 300
        height: 170
        radius: 8
        color: settingsController.surfaceColor
        border.color: settingsController.borderColor
        border.width: 1
        z: 200
        
        MultiEffect {
            source: brushNameModal
            anchors.fill: brushNameModal
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
                text: "Adicionar descrição? (Opcional)"
                color: settingsController.textColor
                font.bold: true
                font.pixelSize: 16
                Layout.fillWidth: true
            }
            
            TextField {
                id: brushNameInput
                Layout.fillWidth: true
                placeholderText: "Ex: Linha de Defesa"
                color: settingsController.textColor
                background: Rectangle {
                    color: settingsController.backgroundColor
                    border.color: settingsController.borderColor
                    border.width: 1
                    radius: 4
                }
                onAccepted: finishBrushBtn.clicked()
            }
            
            StyledCheckBox {
                text: "Não perguntar novamente (nesta sessão)"
                checked: root.skipBrushNameDialog
                onCheckedChanged: root.skipBrushNameDialog = checked
                Layout.fillWidth: true
            }
            
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                
                Button {
                    Layout.fillWidth: true
                    text: "Sem Descrição"
                    onClicked: {
                        brushNameInput.text = "";
                        finishBrushBtn.clicked();
                    }
                }
                
                Button {
                    id: finishBrushBtn
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
                        if (root.currentDrawing && root.currentDrawing.type === "brush") {
                            if (brushNameInput.text.trim() !== "") {
                                root.currentDrawing.label = brushNameInput.text;
                            }
                            var newDrawings = root.drawings.slice();
                            newDrawings.push(root.currentDrawing);
                            if (typeof mapSessionController !== 'undefined') {
                                if (newDrawings.length > 0) {
                                    var lastAdded = newDrawings[newDrawings.length - 1];
                                    mapSessionController.pushEvent("add_drawing", "draw_" + Date.now(), JSON.stringify(lastAdded));
                                } else {
                                    mapSessionController.pushEvent("clear_all", "all", "{}");
                                }
                            }
                            root.currentDrawing = null;
                            brushNameInput.text = "";
                            root.brushNameDialogVisible = false;
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
        height: 270
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
            
            Text {
                text: root.currentDrawing && root.currentDrawing.time_mins ? "Tempo Estimado: ~" + Math.ceil(root.currentDrawing.time_mins) + " minutos" : ""
                color: settingsController.accentColor
                font.pixelSize: 13
                font.bold: true
                visible: root.currentDrawing && root.currentDrawing.time_mins !== undefined
                Layout.alignment: Qt.AlignHCenter
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
                            // root.drawings = newDrawings; // Managed by SyncManager via onMapUpdated
                            if (typeof mapSessionController !== 'undefined') {
                                if (newDrawings.length > 0) {
                                    var lastAdded = newDrawings[newDrawings.length - 1];
                                    mapSessionController.pushEvent("add_drawing", "draw_" + Date.now(), JSON.stringify(lastAdded));
                                } else {
                                    mapSessionController.pushEvent("clear_all", "all", "{}");
                                }
                            }
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
                            // root.drawings = newDrawings; // Managed by SyncManager via onMapUpdated
                            if (typeof mapSessionController !== 'undefined') {
                                if (newDrawings.length > 0) {
                                    var lastAdded = newDrawings[newDrawings.length - 1];
                                    mapSessionController.pushEvent("add_drawing", "draw_" + Date.now(), JSON.stringify(lastAdded));
                                } else {
                                    mapSessionController.pushEvent("clear_all", "all", "{}");
                                }
                            }
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
        property int serverVersion: 0
        property int pendingQueueSize: 0
        property string latestLogType: ""

        
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
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { text: "Ver: " + jsonDebugWindow.serverVersion; color: "#00ff00"; font.bold: true }
                    Text { text: "Queue: " + jsonDebugWindow.pendingQueueSize; color: jsonDebugWindow.pendingQueueSize > 0 ? "#ffaa00" : "#00ff00"; font.bold: true }
                    Text { text: "Last: " + jsonDebugWindow.latestLogType; color: "#aaaaaa"; Layout.fillWidth: true; elide: Text.ElideRight }
                }
                Rectangle { height: 1; Layout.fillWidth: true; color: "#333333" }
                
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

    // --- EVENT SOURCING TIMERS ---
    Item {
        id: autoSaveTimers
        property real lastSentWx: -99999
        property real lastSentWy: -99999
        
        Timer {
            interval: 50
            running: true
            repeat: true
            onTriggered: {
                if (Qt.application.active) {
                    var isHovered = mapMouseArea.containsMouse;
                    var isPressed = mapMouseArea.pressed;
                    if (isHovered || isPressed) {
                        var mx = mapMouseArea.mouseX;
                        var my = mapMouseArea.mouseY;
                        var wp = screenToWorld(mx, my);
                        if (Math.abs(wp.x - parent.lastSentWx) > 0.1 || Math.abs(wp.y - parent.lastSentWy) > 0.1) {
                            parent.lastSentWx = wp.x;
                        parent.lastSentWy = wp.y;
                        var userId = (typeof chatController !== "undefined" && chatController.currentUserId) ? chatController.currentUserId : "";
                        var nick = (typeof chatController !== "undefined" && chatController.currentUserName) ? chatController.currentUserName : "Unknown";
                        var avatar = (typeof chatController !== "undefined" && chatController.currentUserAvatar) ? chatController.currentUserAvatar : "";
                        
                        if (typeof mapSessionController !== "undefined") {
                            var payload = {
                                nick: nick,
                                avatar: avatar,
                                status: { x: wp.x, y: wp.y },
                                tool: root.activeTool
                            };
                            mapSessionController.pushEvent("cursor_move", userId, JSON.stringify(payload));
                            
                            // Optimistically update local state for unified debugging
                            var cursors = root.usersDict;
                            cursors[userId] = payload;
                            root.usersDict = cursors;
                            
                            if (typeof mapSessionController.debugSync !== "undefined" && mapSessionController.debugSync) {
                                // Logs are now appended directly via the onLogAppended signal
                            }
                        }
                    }
                    }
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
            // root.drawings = currentDrawings; // Managed by SyncManager via onMapUpdated
                            if (typeof mapSessionController !== 'undefined') {
                                if (currentDrawings.length > 0) {
                                    var lastAdded = currentDrawings[currentDrawings.length - 1];
                                    mapSessionController.pushEvent("add_drawing", "draw_" + Date.now(), JSON.stringify(lastAdded));
                                } else {
                                    mapSessionController.pushEvent("clear_all", "all", "{}");
                                }
                            }
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
                    // root.drawings = []; // Managed by SyncManager via onMapUpdated
                            if (typeof mapSessionController !== 'undefined') {
                                mapSessionController.pushEvent("clear_all", "all", "{}");
                            }
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
        property var drawingData: null
        opacity: drawingHoverTooltip.drawingData ? 1.0 : 0.0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 150 } }
        
        width: tooltipContent.implicitWidth + 24
        height: tooltipContent.implicitHeight + 20
        color: "#f00f172a" // sleek slate 900
        border.color: "#3b82f6" // blue 500
        border.width: 1
        radius: 8
        z: 9999
        
        function formatExpiration(msTime) {
            if (!msTime) return "";
            var now = Date.now();
            if (msTime <= now) return "Expirado";
            var diff = Math.floor((msTime - now) / 1000);
            var m = Math.floor(diff / 60);
            var s = diff % 60;
            return m + "m " + s + "s";
        }
        
        Column {
            id: tooltipContent
            anchors.centerIn: parent
            spacing: 6
            
            Text {
                text: "👤 " + (drawingHoverTooltip.drawingData ? (drawingHoverTooltip.drawingData.user || "Desconhecido") : "")
                color: "#f8fafc"
                font.pixelSize: 14
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
            }
            
            Rectangle {
                width: parent.width * 0.8
                height: 1
                color: "#334155"
                anchors.horizontalCenter: parent.horizontalCenter
                visible: drawingHoverTooltip.drawingData && drawingHoverTooltip.drawingData.expiresAt
            }
            
            Text {
                text: "⏳ Expira em " + drawingHoverTooltip.formatExpiration(drawingHoverTooltip.drawingData ? drawingHoverTooltip.drawingData.expiresAt : null)
                color: "#fbbf24"
                font.pixelSize: 12
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
                visible: drawingHoverTooltip.drawingData && drawingHoverTooltip.drawingData.expiresAt
            }
        }
    }
}
