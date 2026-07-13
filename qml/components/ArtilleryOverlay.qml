import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import QtQuick.Effects

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
    property real mapZoomScaleX: Math.pow(2, currentZoom - 6)
    property real mapZoomScaleY: Math.pow(2, currentZoom - 6)
    
    // Map viewport center to calculate relative canvas coordinates
    property real centerX: 0
    property real centerY: 0
    
    // External override properties for saved batteries
    property bool isDynamic: true
    property var externalMathRes: null
    property var externalRadii: null
    property string externalIcon: ""

    function apiToWorld(ax, ay) {
        var wX = ax * 80.0;
        var wY = -ay * 80.0 - 4024.0;
        return {x: wX, y: wY};
    }

    function worldToCanvas(wx, wy) {
        var cx = (wx * mapZoomScaleX) + (width / 2) - centerX;
        var cy = (wy * mapZoomScaleY) + (height / 2) - centerY;
        return {x: cx, y: cy};
    }

    // QML Item-based Rendering (Hardware Accelerated, no Canvas bugs)
    Item {
        id: innerItem
        anchors.fill: parent
        visible: overlayRoot.isActive && (typeof artilleryController !== "undefined" && artilleryController ? artilleryController.weaponInfo !== null : externalIcon !== "")

        property var cP: {
            var _t = centerX + centerY + mapZoomScaleX + mapZoomScaleY + width + height;
            return worldToCanvas(cannonX, cannonY);
        }
        
        property real cAPI_x: cannonX / 80.0
        property real cAPI_y: -(cannonY + 4024.0) / 80.0
        property real tAPI_x: targetX / 80.0
        property real tAPI_y: -(targetY + 4024.0) / 80.0

        property real windDir: typeof artilleryController !== "undefined" && artilleryController ? artilleryController.windDirection : 0
        property int windTier: typeof artilleryController !== "undefined" && artilleryController ? artilleryController.windTier : 0
        
        property var dynamicMathRes: {
            var _trigger = cAPI_x + cAPI_y + tAPI_x + tAPI_y + windDir + windTier;
            if (mapController && isDynamic) {
                return mapController.calculateArtillery(cAPI_x, cAPI_y, tAPI_x, tAPI_y, windDir, windTier);
            }
            return null;
        }
        property var mathRes: isDynamic ? dynamicMathRes : externalMathRes
        
        property var aimWorld: mathRes && mathRes.aim_x !== undefined && mathRes.aim_y !== undefined ? apiToWorld(mathRes.aim_x, mathRes.aim_y) : null
        property var tP: {
            var _t = centerX + centerY + mapZoomScaleX + mapZoomScaleY + width + height;
            return aimWorld ? worldToCanvas(aimWorld.x, aimWorld.y) : worldToCanvas(targetX, targetY);
        }
        
        property real dist_meters: mathRes ? (mathRes.distance_meters || 0) : 0
        property var radii: {
            var _trigger = dist_meters;
            if (isDynamic) {
                return (typeof artilleryController !== "undefined" && artilleryController) ? artilleryController.getOverlayData(dist_meters) : null;
            }
            return externalRadii;
        }
        
        property real radiusCompensator: 1.515
        property real minR: radii && radii.min_range ? radii.min_range * radiusCompensator * mapZoomScaleX : 0
        property real maxR: radii && radii.max_range ? radii.max_range * radiusCompensator * mapZoomScaleX : 0
        property real dispR: radii && radii.dispersion ? radii.dispersion * radiusCompensator * mapZoomScaleX : 0

        // Min Range Ring (Redesign: distinct color, softer)
        Shape {
            x: innerItem.cP.x - innerItem.minR
            y: innerItem.cP.y - innerItem.minR
            width: innerItem.minR * 2
            height: innerItem.minR * 2
            visible: currentZoom > 1 && (typeof artilleryController !== "undefined" && artilleryController ? artilleryController.showRange : true) && innerItem.minR > 0
            
            ShapePath {
                fillColor: "transparent"
                strokeColor: "#f43f5e" // Rose 500 for min range
                strokeWidth: 2
                strokeStyle: ShapePath.DashLine
                dashPattern: [8, 12]
                
                PathAngleArc {
                    centerX: innerItem.minR; centerY: innerItem.minR
                    radiusX: innerItem.minR; radiusY: innerItem.minR
                    startAngle: 0; sweepAngle: 360
                }
            }
        }

        // Max Range Ring (Redesign: thicker, more visible)
        Shape {
            x: innerItem.cP.x - innerItem.maxR
            y: innerItem.cP.y - innerItem.maxR
            width: innerItem.maxR * 2
            height: innerItem.maxR * 2
            visible: currentZoom > 1 && (typeof artilleryController !== "undefined" && artilleryController ? artilleryController.showRange : true) && innerItem.maxR > 0
            
            ShapePath {
                fillColor: Qt.rgba(234/255, 179/255, 8/255, 0.05) // Subtle fill
                strokeColor: "#eab308" // Yellow 500
                strokeWidth: 3 // Thicker
                strokeStyle: ShapePath.DashLine
                dashPattern: [12, 8]
                
                PathAngleArc {
                    centerX: innerItem.maxR; centerY: innerItem.maxR
                    radiusX: innerItem.maxR; radiusY: innerItem.maxR
                    startAngle: 0; sweepAngle: 360
                }
            }
        }

        // Dispersion Ring (at target)
        Shape {
            x: innerItem.tP.x - innerItem.dispR
            y: innerItem.tP.y - innerItem.dispR
            width: innerItem.dispR * 2
            height: innerItem.dispR * 2
            visible: currentZoom > 1 && (typeof artilleryController !== "undefined" && artilleryController ? artilleryController.showDispersion : true) && innerItem.dispR > 0
            
            Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
            Behavior on y { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
            Behavior on width { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
            Behavior on height { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }

            ShapePath {
                fillColor: Qt.rgba(239/255, 68/255, 68/255, 0.15) // Soft Red fill
                strokeColor: "#ef4444" // Red 500
                strokeWidth: 2
                strokeStyle: ShapePath.DashLine
                dashPattern: [6, 4]
                
                PathAngleArc {
                    centerX: innerItem.dispR; centerY: innerItem.dispR
                    radiusX: innerItem.dispR; radiusY: innerItem.dispR
                    startAngle: 0; sweepAngle: 360
                }
            }
        }

        // Connecting Line (Redesign: better styling)
        Shape {
            visible: currentZoom > 1 && (targetX !== cannonX || targetY !== cannonY) && (typeof artilleryController !== "undefined" && artilleryController ? artilleryController.showLine : true)
            ShapePath {
                fillColor: "transparent"
                strokeColor: Qt.rgba(255/255, 255/255, 255/255, 0.75)
                strokeWidth: 2
                strokeStyle: ShapePath.DashLine
                dashPattern: [10, 6]
                startX: innerItem.cP.x
                startY: innerItem.cP.y
                PathLine { x: innerItem.tP.x; y: innerItem.tP.y }
            }
        }

        // Cannon Indicator (Redesign: small drop shadow for modern look)
        Item {
            x: innerItem.cP.x - width/2
            y: innerItem.cP.y - height/2
            width: 64
            height: 64
            visible: (cannonX !== 0 || cannonY !== 0)
            
            Image {
                id: cannonPreview
                anchors.fill: parent
                visible: false // MultiEffect draws it instead
                source: isDynamic 
                    ? (typeof artilleryController !== "undefined" && artilleryController && artilleryController.weaponInfo && artilleryController.weaponInfo.icon 
                        ? "../../" + artilleryController.weaponInfo.icon 
                        : "")
                    : externalIcon
                fillMode: Image.PreserveAspectFit
                rotation: (targetX !== cannonX || targetY !== cannonY) ? (Math.atan2(innerItem.tP.y - innerItem.cP.y, innerItem.tP.x - innerItem.cP.x) * 180 / Math.PI) - 90 : 0
                
                Behavior on rotation { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
            }
            
            MultiEffect {
                source: cannonPreview
                anchors.fill: parent
                shadowEnabled: true
                shadowColor: "black"
                shadowOpacity: 0.5
                shadowBlur: 0.8
                shadowVerticalOffset: 2
            }

            Rectangle {
                anchors.centerIn: parent
                width: 14
                height: 14
                radius: 7
                color: "#3b82f6"
                border.color: "white"
                border.width: 2
                visible: cannonPreview.source == "" || cannonPreview.status === Image.Error
            }
        }

        // Target Indicator (Redesign: Modern Crosshair)
        Item {
            id: targetMarker
            x: innerItem.tP.x - width/2
            y: innerItem.tP.y - height/2
            width: 24
            height: 24
            visible: currentZoom > 1 && (targetX !== cannonX || targetY !== cannonY)
            
            Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
            Behavior on y { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }

            // Outer ring
            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: "transparent"
                border.color: "#ef4444"
                border.width: 2
                opacity: 0.8
            }
            
            // Center dot
            Rectangle {
                anchors.centerIn: parent
                width: 6
                height: 6
                radius: 3
                color: "#ef4444"
            }
            
            // Crosshair lines
            Rectangle { anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; width: 2; height: 6; color: "#ef4444" }
            Rectangle { anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; width: 2; height: 6; color: "#ef4444" }
            Rectangle { anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; width: 6; height: 2; color: "#ef4444" }
            Rectangle { anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right; width: 6; height: 2; color: "#ef4444" }
        }

        // Tooltip (Azimuth & Distance) - Redesign
        Item {
            id: tooltipContainer
            x: innerItem.tP.x + 20
            y: innerItem.tP.y - height/2
            width: tooltipLayout.implicitWidth + 24
            height: tooltipLayout.implicitHeight + 16
            visible: currentZoom > 1 && (targetX !== cannonX || targetY !== cannonY) && (typeof artilleryController !== "undefined" && artilleryController ? artilleryController.showDistances : true)

            Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
            Behavior on y { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }

            Rectangle {
                id: tooltipBg
                anchors.fill: parent
                color: Qt.rgba(15/255, 23/255, 42/255, 0.85) // Slate 900 Glass
                border.color: Qt.rgba(255/255, 255/255, 255/255, 0.25)
                border.width: 1
                radius: 8
            }
            
            MultiEffect {
                source: tooltipBg
                anchors.fill: parent
                shadowEnabled: true
                shadowColor: "black"
                shadowOpacity: 0.6
                shadowBlur: 1.0
                shadowVerticalOffset: 3
            }

            Row {
                id: tooltipLayout
                anchors.centerIn: parent
                spacing: 16

                Column {
                    spacing: 2
                    Text { text: "AZIMUTE"; color: "#94a3b8"; font.bold: true; font.pixelSize: 9; font.letterSpacing: 1.5; font.family: "Inter, sans-serif" }
                    Row {
                        spacing: 4
                        Text { text: "🧭"; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
                        Text {
                            text: innerItem.mathRes && innerItem.mathRes.bearing !== undefined ? Math.round(innerItem.mathRes.bearing) + "°" : "0°"
                            color: "#fcd34d" // Amber 300
                            font.bold: true
                            font.pixelSize: 16
                            font.family: "Inter, sans-serif"
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }

                Rectangle { width: 1; height: 30; color: Qt.rgba(255/255, 255/255, 255/255, 0.2); anchors.verticalCenter: parent.verticalCenter }

                Column {
                    spacing: 2
                    Text { text: "DISTÂNCIA"; color: "#94a3b8"; font.bold: true; font.pixelSize: 9; font.letterSpacing: 1.5; font.family: "Inter, sans-serif" }
                    Row {
                        spacing: 4
                        Text { text: "📏"; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
                        Text {
                            text: innerItem.mathRes && innerItem.mathRes.distance_meters !== undefined ? Math.round(innerItem.mathRes.distance_meters) + "m" : "0m"
                            color: "#6ee7b7" // Emerald 300
                            font.bold: true
                            font.pixelSize: 16
                            font.family: "Inter, sans-serif"
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }
        }
    }
}
