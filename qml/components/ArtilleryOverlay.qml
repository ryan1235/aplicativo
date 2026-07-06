import QtQuick
import QtQuick.Controls

Item {
    id: overlayRoot
    anchors.fill: parent

    // Injected properties from MapView
    property real cannonX: 0
    property real cannonY: 0
    property real targetX: 0
    property real targetY: 0
    property bool isActive: false
    property var mapController: null
    property real currentZoom: 0
    property real mapScale: 1
    property real mapOffsetX: 0
    property real mapOffsetY: 0
    
    // Map viewport center to calculate relative canvas coordinates
    property real centerX: 0
    property real centerY: 0

    function apiToWorld(ax, ay) {
        var wX = (ax * mapScale) + mapOffsetX;
        var wY = (-ay * mapScale) + mapOffsetY;
        return {x: wX, y: wY};
    }

    function worldToCanvas(wx, wy) {
        var cx = (wx * Math.pow(2, currentZoom)) - (centerX - width / 2);
        var cy = (wy * Math.pow(2, currentZoom)) - (centerY - height / 2);
        return {x: cx, y: cy};
    }

    function apiToCanvas(ax, ay) {
        var w = apiToWorld(ax, ay);
        return worldToCanvas(w.x, w.y);
    }

    // QML Item-based Rendering (Hardware Accelerated, no Canvas bugs)
    Item {
        anchors.fill: parent
        visible: overlayRoot.isActive && typeof artilleryController !== "undefined" && artilleryController.weaponInfo !== null

        property var cP: apiToCanvas(cannonX, cannonY)
        property var tP: apiToCanvas(targetX, targetY)
        property var mathRes: mapController ? mapController.calculateArtillery(cannonX, cannonY, targetX, targetY) : null
        property real dist_meters: mathRes ? (mathRes.distance_meters || 0) : 0
        property var radii: artilleryController.getOverlayData(dist_meters)
        
        property real zoomFactor: Math.pow(2, currentZoom)
        
        // Fator de compensação solicitado pelo usuário para alinhar o anel visual com o mapa
        property real radiusCompensator: 1.515

        // Radii from python are in API coordinates. Multiply by mapScale, zoomFactor, and compensator.
        property real minR: radii && radii.minRangeRadiusWU ? (radii.minRangeRadiusWU * mapScale * zoomFactor * radiusCompensator) : 0
        property real maxR: radii && radii.maxRangeRadiusWU ? (radii.maxRangeRadiusWU * mapScale * zoomFactor * radiusCompensator) : 0
        property real dispR: radii && radii.dispersionRadiusWU ? (radii.dispersionRadiusWU * mapScale * zoomFactor * radiusCompensator) : 0

        // Min Range Ring
        Rectangle {
            x: parent.cP.x - parent.minR
            y: parent.cP.y - parent.minR
            width: parent.minR * 2
            height: parent.minR * 2
            radius: parent.minR
            color: "transparent"
            border.color: "white"
            border.width: 1
            opacity: 0.3
            visible: artilleryController.showRange && parent.minR > 0
        }

        // Max Range Ring
        Rectangle {
            x: parent.cP.x - parent.maxR
            y: parent.cP.y - parent.maxR
            width: parent.maxR * 2
            height: parent.maxR * 2
            radius: parent.maxR
            color: "transparent"
            border.color: "white"
            border.width: 1
            opacity: 0.3
            visible: artilleryController.showRange && parent.maxR > 0
        }

        // Connecting Line
        Rectangle {
            property real dist: Math.sqrt(Math.pow(parent.tP.x - parent.cP.x, 2) + Math.pow(parent.tP.y - parent.cP.y, 2))
            x: parent.cP.x
            y: parent.cP.y - height/2
            width: dist
            height: 2
            color: artilleryController.showLine ? "white" : "transparent"
            opacity: 0.5
            transformOrigin: Item.Left
            rotation: Math.atan2(parent.tP.y - parent.cP.y, parent.tP.x - parent.cP.x) * 180 / Math.PI
            visible: (targetX !== cannonX || targetY !== cannonY) && dist > 0
        }

        // Dispersion Ring (at target)
        Rectangle {
            x: parent.tP.x - parent.dispR
            y: parent.tP.y - parent.dispR
            width: parent.dispR * 2
            height: parent.dispR * 2
            radius: parent.dispR
            color: "#19ef4444"
            border.color: "#99ef4444"
            border.width: 1
            visible: artilleryController.showDispersion && parent.dispR > 0
        }

        // Cannon Indicator
        Rectangle {
            width: 12
            height: 12
            radius: 6
            color: "#3b82f6"
            x: parent.cP.x - 6
            y: parent.cP.y - 6
            visible: cannonX !== 0 || cannonY !== 0
        }

        // Target Indicator
        Rectangle {
            width: 8
            height: 8
            radius: 4
            color: "#ef4444"
            x: parent.tP.x - 4
            y: parent.tP.y - 4
            visible: targetX !== cannonX || targetY !== cannonY
        }

        // Info Text (Azimuth and Distance)
        Rectangle {
            x: parent.tP.x + 10
            y: parent.tP.y - 10
            width: infoText.implicitWidth + 10
            height: infoText.implicitHeight + 6
            color: "#cc0f172a" // Dark slate
            border.color: "#33ffffff"
            border.width: 1
            radius: 4
            visible: (targetX !== cannonX || targetY !== cannonY) && parent.mathRes !== null
            
            Text {
                id: infoText
                anchors.centerIn: parent
                color: "white"
                font.pixelSize: 12
                font.bold: true
                text: {
                    if (!parent.parent.mathRes) return "";
                    var azm = parent.parent.mathRes.bearing || 0;
                    var dist = parent.parent.mathRes.distance_meters || 0;
                    return "AZM: " + Math.round(azm) + "° | DIST: " + Math.round(dist) + "m";
                }
            }
        }
    }
}
