import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: debugRoot
    z: 5000
    width: 300
    color: "#ee111827"
    border.color: "#f59e0b"
    border.width: 2
    radius: 8

    property var mapView: null
    property bool collapsed: false
    implicitHeight: collapsed ? 44 : 520

    function syncToController() {
        if (typeof mapController === "undefined" || !mapController || !mapView)
            return;
        mapController.mapScale = mapView.debugMapScale;
        mapController.mapOffsetX = mapView.debugMapOffsetX;
        mapController.mapOffsetY = mapView.debugMapOffsetY;
    }

    function calibrationJson() {
        if (!mapView) return "{}";
        return JSON.stringify({
            zoom: mapView.currentZoom,
            zoomMode: mapView.debugZoomMode,
            mapScale: Number(mapView.debugMapScale.toFixed(4)),
            offsetX: Number(mapView.debugMapOffsetX.toFixed(3)),
            offsetY: Number(mapView.debugMapOffsetY.toFixed(3)),
            zoomMultX: Number(mapView.debugZoomMultX.toFixed(4)),
            zoomMultY: Number(mapView.debugZoomMultY.toFixed(4)),
            effectiveScaleX: Number(mapView.mapZoomScaleX.toFixed(4)),
            effectiveScaleY: Number(mapView.mapZoomScaleY.toFixed(4))
        }, null, 2);
    }

    function refreshJson() {
        jsonPreview.text = calibrationJson();
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "Debug Malha"
                color: "#fbbf24"
                font.bold: true
                font.pixelSize: 13
                Layout.fillWidth: true
            }
            Button {
                text: collapsed ? "+" : "−"
                implicitWidth: 28
                implicitHeight: 24
                onClicked: debugRoot.collapsed = !debugRoot.collapsed
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: !collapsed
            spacing: 6

            Text {
                text: "Zoom: " + (mapView ? mapView.currentZoom : "?")
                color: "#e5e7eb"
                font.pixelSize: 11
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 4
                Button {
                    text: "−"
                    implicitWidth: 32
                    onClicked: if (mapView) mapView.currentZoom = Math.max(mapView.minZoom, mapView.currentZoom - 1)
                }
                Slider {
                    id: zoomSlider
                    Layout.fillWidth: true
                    from: mapView ? mapView.minZoom : 0
                    to: mapView ? mapView.maxZoom : 6
                    stepSize: 1
                    value: mapView ? mapView.currentZoom : 2
                    onMoved: if (mapView) mapView.currentZoom = Math.round(value)
                }
                Button {
                    text: "+"
                    implicitWidth: 32
                    onClicked: if (mapView) mapView.currentZoom = Math.min(mapView.maxZoom, mapView.currentZoom + 1)
                }
            }

            ComboBox {
                id: modeCombo
                Layout.fillWidth: true
                model: ["2^z (clássico)", "Manifest (wz/w0)", "Foxlogi resample"]
                currentIndex: {
                    if (!mapView) return 0;
                    if (mapView.debugZoomMode === "manifest") return 1;
                    if (mapView.debugZoomMode === "foxlogi") return 2;
                    return 0;
                }
                onActivated: function(i) {
                    if (!mapView) return;
                    mapView.debugZoomMode = i === 1 ? "manifest" : (i === 2 ? "foxlogi" : "pow2");
                    refreshJson();
                }
            }

            Text { text: "mapScale: " + (mapView ? mapView.debugMapScale.toFixed(3) : "?"); color: "#9ca3af"; font.pixelSize: 10 }
            Slider {
                Layout.fillWidth: true
                from: 0.5; to: 2.0; stepSize: 0.001
                value: mapView ? mapView.debugMapScale : 1.0
                onMoved: { if (mapView) { mapView.debugMapScale = value; syncToController(); refreshJson(); } }
            }

            Text { text: "offsetX: " + (mapView ? mapView.debugMapOffsetX.toFixed(1) : "?"); color: "#9ca3af"; font.pixelSize: 10 }
            Slider {
                Layout.fillWidth: true
                from: -150; to: 150; stepSize: 0.5
                value: mapView ? mapView.debugMapOffsetX : 0
                onMoved: { if (mapView) { mapView.debugMapOffsetX = value; syncToController(); refreshJson(); } }
            }

            Text { text: "offsetY: " + (mapView ? mapView.debugMapOffsetY.toFixed(1) : "?"); color: "#9ca3af"; font.pixelSize: 10 }
            Slider {
                Layout.fillWidth: true
                from: -150; to: 150; stepSize: 0.5
                value: mapView ? mapView.debugMapOffsetY : 0
                onMoved: { if (mapView) { mapView.debugMapOffsetY = value; syncToController(); refreshJson(); } }
            }

            Text { text: "zoomMult X: " + (mapView ? mapView.debugZoomMultX.toFixed(3) : "?"); color: "#9ca3af"; font.pixelSize: 10 }
            Slider {
                Layout.fillWidth: true
                from: 0.5; to: 2.0; stepSize: 0.001
                value: mapView ? mapView.debugZoomMultX : 1.0
                onMoved: { if (mapView) { mapView.debugZoomMultX = value; refreshJson(); } }
            }

            Text { text: "zoomMult Y: " + (mapView ? mapView.debugZoomMultY.toFixed(3) : "?"); color: "#9ca3af"; font.pixelSize: 10 }
            Slider {
                Layout.fillWidth: true
                from: 0.5; to: 2.0; stepSize: 0.001
                value: mapView ? mapView.debugZoomMultY : 1.0
                onMoved: { if (mapView) { mapView.debugZoomMultY = value; refreshJson(); } }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 4
                Button {
                    text: "Reset"
                    Layout.fillWidth: true
                    onClicked: {
                        if (!mapView) return;
                        mapView.debugMapScale = 1.0;
                        mapView.debugMapOffsetX = 0.0;
                        mapView.debugMapOffsetY = 0.0;
                        mapView.debugZoomMultX = 1.0;
                        mapView.debugZoomMultY = 1.0;
                        mapView.debugZoomMode = "pow2";
                        modeCombo.currentIndex = 0;
                        syncToController();
                        refreshJson();
                    }
                }
                Button {
                    text: "Copiar JSON"
                    Layout.fillWidth: true
                    onClicked: {
                        var txt = calibrationJson();
                        jsonPreview.text = txt;
                        if (typeof mapController !== "undefined" && mapController)
                            mapController.copyTextToClipboard(txt);
                    }
                }
            }

            TextArea {
                id: jsonPreview
                Layout.fillWidth: true
                Layout.preferredHeight: 88
                readOnly: true
                wrapMode: TextArea.Wrap
                color: "#a7f3d0"
                font.family: "Consolas"
                font.pixelSize: 9
                background: Rectangle { color: "#0f172a"; radius: 4 }
            }

            Text {
                Layout.fillWidth: true
                text: "Ajuste até alinhar. Copie o JSON e me envie."
                color: "#6b7280"
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
        }
    }

    Connections {
        target: mapView
        function onCurrentZoomChanged() { refreshJson(); if (mapView) zoomSlider.value = mapView.currentZoom; }
        function onDebugZoomModeChanged() { refreshJson(); }
        function onMapZoomScaleXChanged() { refreshJson(); }
    }

    Component.onCompleted: refreshJson()
}
