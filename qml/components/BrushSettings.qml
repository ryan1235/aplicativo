import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import QtQuick.Dialogs
import Qt.labs.platform 1.1 as Platform
import "MapToolsData.js" as ToolsData
import "LineStylesData.js" as LineData
import "TacticalSymbolsData.js" as SymbolData

Item {
    id: root
    width: 320
    height: 480
    
    property string activeToolId: "brush"
    property var activeTool: ToolsData.getToolById("brush")
    
    // Properties that will be persisted
    property int currentTab: 0
    property string activeColor: "#ef4444"
    property int activeThickness: 4
    property real activeOpacity: 1.0
    property string activeLineStyle: "solid"
    property string arrowPosition: "end"
    property string arrowPlacement: "center"
    property bool activeHighlight: false
    property int activeExpiration: 0
    property bool activeLocked: false
    property string activeSymbol: "defense"
    property var customColors: []
    property bool skipBrushNameDialog: false
    
    signal resetDescriptionDialog(bool ask)
    
    property string symbolSearchQuery: ""
    property string symbolActiveCategory: "Todos"
    
    property bool inspectMode: false
    property var inspectedDrawing: null
    property bool isOwner: inspectedDrawing ? (inspectedDrawing.createdBy === (typeof chatController !== "undefined" ? chatController.currentUserId : "")) : false
    
    onInspectedDrawingChanged: {
        if (inspectMode && inspectedDrawing && isOwner) {
            // Temporarily block updates to avoid sending update events while syncing
            var prevMode = inspectMode;
            inspectMode = false;
            
            if (inspectedDrawing.color) activeColor = inspectedDrawing.color;
            if (inspectedDrawing.thickness) activeThickness = inspectedDrawing.thickness;
            if (inspectedDrawing.opacity) activeOpacity = inspectedDrawing.opacity;
            if (inspectedDrawing.lineStyle) activeLineStyle = inspectedDrawing.lineStyle;
            if (inspectedDrawing.arrowPosition) arrowPosition = inspectedDrawing.arrowPosition;
            if (inspectedDrawing.arrowPlacement) arrowPlacement = inspectedDrawing.arrowPlacement;
            
            if (inspectedDrawing.locked !== undefined) activeLocked = inspectedDrawing.locked;
            if (inspectedDrawing.expiresAt) {
                var diff = (inspectedDrawing.expiresAt - Date.now()) / 1000;
                activeExpiration = diff > 0 ? diff : 0;
            } else {
                activeExpiration = 0;
            }
            
            inspectMode = prevMode;
        }
    }
    
    function setCurrentTab(tabName) {
        if (tabName === "info") currentTab = 0;
        else if (tabName === "appearance") currentTab = 1;
        else if (tabName === "specials") currentTab = 2;
    }
    
    Component.onCompleted: {
        if (typeof settingsController !== 'undefined') {
            var tab = settingsController.value("tactical_map", "currentTab");
            if (tab !== undefined && tab !== null) currentTab = parseInt(tab);
            else currentTab = 1; // Default to Aparência
            
            if (!inspectMode && currentTab === 0) currentTab = 1;
            if (inspectMode) currentTab = 0;
            
            var c = settingsController.value("tactical_map", "activeColor");
            if (c) activeColor = c;
            
            var th = settingsController.value("tactical_map", "activeThickness");
            if (th !== undefined && th !== null) activeThickness = parseInt(th);
            
            var op = settingsController.value("tactical_map", "activeOpacity");
            if (op !== undefined && op !== null) activeOpacity = parseFloat(op);
            
            var ls = settingsController.value("tactical_map", "activeLineStyle");
            if (ls) activeLineStyle = ls;
            
            var apos = settingsController.value("tactical_map", "arrowPosition");
            if (apos) arrowPosition = apos;
            
            var aplace = settingsController.value("tactical_map", "arrowPlacement");
            if (aplace) arrowPlacement = aplace;
            
            var sym = settingsController.value("tactical_map", "activeSymbol");
            if (sym) activeSymbol = sym;
            
            var cust = settingsController.value("tactical_map", "customColors");
            if (cust) {
                try {
                    customColors = JSON.parse(cust);
                } catch(e) {}
            }
        }
        
        loadSymbols();
    }
    
    onCurrentTabChanged: saveSetting("currentTab", currentTab)
    onActiveColorChanged: { saveSetting("activeColor", activeColor); updateInspectedDrawing("color", activeColor); }
    onActiveThicknessChanged: { saveSetting("activeThickness", activeThickness); updateInspectedDrawing("thickness", activeThickness); }
    onActiveOpacityChanged: { saveSetting("activeOpacity", activeOpacity); updateInspectedDrawing("opacity", activeOpacity); }
    onActiveLineStyleChanged: { saveSetting("activeLineStyle", activeLineStyle); updateInspectedDrawing("lineStyle", activeLineStyle); }
    onArrowPositionChanged: { saveSetting("arrowPosition", arrowPosition); updateInspectedDrawing("arrowPosition", arrowPosition); }
    onArrowPlacementChanged: { saveSetting("arrowPlacement", arrowPlacement); updateInspectedDrawing("arrowPlacement", arrowPlacement); }
    onActiveExpirationChanged: { updateInspectedDrawing("expiresAt", activeExpiration > 0 ? (Date.now() + activeExpiration * 1000) : null); }
    onActiveLockedChanged: { updateInspectedDrawing("locked", activeLocked); }
    onActiveSymbolChanged: saveSetting("activeSymbol", activeSymbol)
    onCustomColorsChanged: saveSetting("customColors", JSON.stringify(customColors))
    
    function updateInspectedDrawing(key, val) {
        if (!inspectMode || !inspectedDrawing || !isOwner) return;
        var modified = false;
        if (inspectedDrawing[key] !== val) {
            inspectedDrawing[key] = val;
            modified = true;
        }
        if (modified && typeof mapSessionController !== 'undefined') {
            inspectedDrawing.updatedAt = Date.now();
            mapSessionController.pushEvent("update_drawing", inspectedDrawing.id || inspectedDrawing._id || inspectedDrawing.eventId, JSON.stringify(inspectedDrawing));
        }
    }
    
    function saveSetting(key, val) {
        if (typeof settingsController !== 'undefined') {
            settingsController.setValue("tactical_map", key, val);
        }
    }

    ListModel {
        id: symbolsListModel
    }

    MouseArea { anchors.fill: parent }

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: 12
        color: Qt.rgba(settingsController.surfaceColor.r, settingsController.surfaceColor.g, settingsController.surfaceColor.b, 0.95)
        border.color: Qt.rgba(settingsController.borderColor.r, settingsController.borderColor.g, settingsController.borderColor.b, 0.5)
        border.width: 1
    }

    MultiEffect {
        source: bg
        anchors.fill: bg
        shadowEnabled: true
        shadowOpacity: 0.5
        shadowBlur: 1.5
        shadowVerticalOffset: 4
        shadowColor: "black"
        blurEnabled: true
        blur: 0.8
    }

    ColorDialog {
        id: colorDialog
        title: "Cor Personalizada"
        onAccepted: {
            var c = colorDialog.selectedColor.toString();
            root.activeColor = c;
            var cc = root.customColors.slice();
            if (cc.indexOf(c) === -1) {
                cc.push(c);
                if (cc.length > 8) cc.shift();
                root.customColors = cc;
            }
        }
    }

    // Toggle Switch Component Inline
    Component {
        id: customSwitchComponent
        Rectangle {
            property bool checked: false
            property string labelText: ""
            property string iconText: ""
            
            width: parent.width
            height: 36
            radius: 6
            color: "transparent"
            border.color: settingsController.borderColor || "#444"
            border.width: 1
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8
                Text { text: iconText; font.pixelSize: 14; Layout.alignment: Qt.AlignVCenter }
                Text { text: labelText; color: settingsController.textColor || "white"; font.pixelSize: 12; Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter }
                
                Rectangle {
                    width: 40; height: 20; radius: 10
                    color: checked ? (settingsController.accentColor || "#3b82f6") : "#4b5563"
                    Behavior on color { ColorAnimation { duration: 150 } }
                    
                    Rectangle {
                        width: 16; height: 16; radius: 8
                        color: "white"
                        x: checked ? 22 : 2
                        anchors.verticalCenter: parent.verticalCenter
                        Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutQuad } }
                        
                        MultiEffect {
                            source: parent
                            anchors.fill: parent
                            shadowEnabled: true
                            shadowOpacity: 0.3
                            shadowBlur: 0.5
                        }
                    }
                }
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: checked = !checked
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        // Header / Navigation
        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            
            Repeater {
                model: {
                    var tabs = [];
                    if (root.inspectMode) {
                        tabs.push({ icon: "ℹ", label: "Informações", tabIdx: 0 });
                    }
                    if (!root.inspectMode || root.isOwner) {
                        tabs.push({ icon: "🎨", label: "Aparência", tabIdx: 1 });
                        tabs.push({ icon: "⚙", label: "Especiais", tabIdx: 2 });
                    }
                    return tabs;
                }
                delegate: Rectangle {
                    Layout.fillWidth: true
                    height: 32
                    radius: 6
                    color: root.currentTab === modelData.tabIdx ? (settingsController.accentColor || "#3b82f6") : "transparent"
                    border.color: root.currentTab === modelData.tabIdx ? "transparent" : (settingsController.borderColor || "#444")
                    border.width: 1
                    
                    Row {
                        anchors.centerIn: parent
                        spacing: 4
                        Text { text: modelData.icon; color: root.currentTab === modelData.tabIdx ? "white" : (settingsController.textColor || "white"); font.pixelSize: 12 }
                        Text { text: modelData.label; color: root.currentTab === modelData.tabIdx ? "white" : (settingsController.textColor || "white"); font.pixelSize: 11; font.bold: root.currentTab === modelData.tabIdx; visible: root.width > 280 }
                    }
                    
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.currentTab = modelData.tabIdx
                    }
                }
            }
        }
        
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: settingsController.borderColor || "#444"
        }

        // Content Area
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            // Tab 0: INFORMAÇÕES
            ScrollView {
                id: infoScroll
                anchors.fill: parent
                visible: root.currentTab === 0 && root.inspectMode
                OpacityAnimator on opacity { from: 0; to: 1; duration: 200; running: root.currentTab === 0 && root.inspectMode }
                contentWidth: width
                
                ColumnLayout {
                    width: infoScroll.width
                    spacing: 16
                    
                    Text { text: "INFORMAÇÕES"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.5 }
                    
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: infoContentCol.implicitHeight + 32
                        radius: 8
                        color: Qt.rgba(0,0,0,0.3)
                        border.color: settingsController.borderColor || "#444"
                        border.width: 1
                        
                        ColumnLayout {
                            id: infoContentCol
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 16
                            spacing: 12
                            
                            RowLayout {
                                spacing: 12
                                Rectangle {
                                    width: 32; height: 32; radius: 16
                                    color: settingsController.accentColor || "#3b82f6"
                                    Text {
                                        anchors.centerIn: parent
                                        text: "👤"
                                        font.pixelSize: 16
                                    }
                                }
                                ColumnLayout {
                                    spacing: 2
                                    Text {
                                        text: root.inspectedDrawing && root.inspectedDrawing.user ? root.inspectedDrawing.user : "Desconhecido"
                                        color: "white"
                                        font.bold: true
                                        font.pixelSize: 15
                                        Layout.fillWidth: true
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        text: "Criador do Traçado"
                                        color: settingsController.mutedTextColor || "#888"
                                        font.pixelSize: 11
                                    }
                                }
                            }
                            
                            Rectangle { Layout.fillWidth: true; height: 1; color: Qt.rgba(1,1,1,0.1) }
                            
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Criado em:"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 12 }
                                Item { Layout.fillWidth: true } // Spacer
                                Text { 
                                    text: {
                                        if (root.inspectedDrawing && root.inspectedDrawing.createdAt) {
                                            var d = new Date(root.inspectedDrawing.createdAt);
                                            return d.toLocaleDateString() + " " + d.toLocaleTimeString();
                                        }
                                        return "--/--/---- --:--";
                                    }
                                    color: "white"; font.pixelSize: 12; font.family: "monospace"
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignRight
                                }
                            }
                            
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "⏳ Expira em:"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 12 }
                                Item { Layout.fillWidth: true } // Spacer
                                Text { 
                                    id: expirationText
                                    color: timeStr === "Expirado" ? "#ef4444" : "white"
                                    font.pixelSize: 12; font.bold: true; font.family: "monospace"
                                    property string timeStr: "Nunca expira"
                                    text: timeStr
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignRight
                                    
                                    Timer {
                                        interval: 1000; running: root.currentTab === 0 && root.inspectedDrawing; repeat: true
                                        onTriggered: {
                                            if (!root.inspectedDrawing || !root.inspectedDrawing.expiresAt) {
                                                expirationText.timeStr = "Nunca expira";
                                            } else {
                                                var diff = root.inspectedDrawing.expiresAt - Date.now();
                                                if (diff <= 0) {
                                                    expirationText.timeStr = "Expirado";
                                                } else {
                                                    var h = Math.floor(diff / 3600000);
                                                    var m = Math.floor((diff % 3600000) / 60000);
                                                    var s = Math.floor((diff % 60000) / 1000);
                                                    var res = "";
                                                    if (h > 0) res += h + "h ";
                                                    if (m > 0 || h > 0) res += m + "m ";
                                                    res += s + "s";
                                                    expirationText.timeStr = res;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "🔒 Status:"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 12 }
                                Item { Layout.fillWidth: true } // Spacer
                                Text { 
                                    text: root.inspectedDrawing && root.inspectedDrawing.locked ? "Travado" : "Livre"
                                    color: root.inspectedDrawing && root.inspectedDrawing.locked ? "#f59e0b" : "#10b981"
                                    font.pixelSize: 12; font.bold: true
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignRight
                                }
                            }
                        }
                    }
                    
                    // Owner actions
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        visible: root.isOwner
                        
                        Text { text: "AÇÕES DO CRIADOR"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.5; Layout.topMargin: 8 }
                        
                        Rectangle {
                            Layout.fillWidth: true
                            height: 40
                            radius: 8
                            color: confirmMode ? "#7f1d1d" : Qt.rgba(0.937, 0.267, 0.267, 0.1) // #ef4444 with opacity
                            border.color: confirmMode ? "#ef4444" : "#dc2626"
                            border.width: 1
                            property bool confirmMode: false
                            
                            Text {
                                anchors.centerIn: parent
                                text: parent.confirmMode ? "Tem certeza? (Clique novamente)" : "🗑 Remover Traçado"
                                color: "#ef4444"
                                font.pixelSize: 13
                                font.bold: true
                            }
                            
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (!parent.confirmMode) {
                                        parent.confirmMode = true;
                                    } else {
                                        if (inspectedDrawing && typeof mapSessionController !== 'undefined') {
                                            var dId = inspectedDrawing.id || inspectedDrawing._id || inspectedDrawing.eventId;
                                            mapSessionController.pushEvent("remove_drawing", dId, "{}");
                                            
                                            // Chamar removeDrawingLocally com try-catch para não quebrar a execução
                                            try {
                                                if (typeof removeDrawingLocally === 'function') {
                                                    removeDrawingLocally(dId);
                                                }
                                            } catch (e) {
                                                console.error("Erro ao chamar removeDrawingLocally:", e);
                                            }
                                        }
                                        inspectMode = false;
                                        inspectedDrawing = null;
                                        if (typeof showToolSettings !== 'undefined') showToolSettings = false;
                                    }
                                }
                                onExited: parent.confirmMode = false
                            }
                        }
                    }
                }
            }
            
            // Tab 1: APARÊNCIA
            ScrollView {
                anchors.fill: parent
                visible: root.currentTab === 1
                OpacityAnimator on opacity { from: 0; to: 1; duration: 200; running: root.currentTab === 1 }
                
                Column {
                    width: parent.width
                    spacing: 12
                    
                    // Cor
                    Column {
                        width: parent.width
                        spacing: 4
                        Text { text: "Cor"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 11 }
                        Flow {
                            width: parent.width
                            spacing: 8
                            
                            Repeater {
                                model: {
                                    var baseColors = ["#ef4444", "#3b82f6", "#22c55e", "#eab308", "#f97316", "#a855f7", "#ffffff", "#000000", "#06b6d4", "#ec4899", "#78350f"];
                                    return baseColors.concat(root.customColors);
                                }
                                delegate: Rectangle {
                                    width: 28; height: 28; radius: 14; color: modelData
                                    border.color: root.activeColor === modelData ? (settingsController.accentColor || "white") : "transparent"
                                    border.width: 2
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.activeColor = modelData
                                        cursorShape: Qt.PointingHandCursor
                                    }
                                }
                            }
                            
                            Rectangle {
                                width: 28; height: 28; radius: 14; color: "transparent"
                                border.color: settingsController.borderColor || "#888"
                                border.width: 1
                                Text { anchors.centerIn: parent; text: "+"; color: settingsController.textColor || "white"; font.pixelSize: 18 }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: colorDialog.open()
                                    cursorShape: Qt.PointingHandCursor
                                }
                            }
                        }
                    }
                    
                    // Tipo de Linha
                    Column {
                        width: parent.width
                        spacing: 4
                        Text { text: "Tipo de Linha"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 11 }
                        Flow {
                            width: parent.width
                            spacing: 8
                            Repeater {
                                model: LineData.getStyles()
                                delegate: Rectangle {
                                    width: parent.width / 2 - 4
                                    height: 36
                                    radius: 4
                                    color: root.activeLineStyle === modelData.val ? (settingsController.accentColor || "#3b82f6") : "transparent"
                                    border.color: settingsController.borderColor || "#444"
                                    border.width: 1
                                    
                                    Column {
                                        anchors.centerIn: parent
                                        Canvas {
                                            id: previewCanvas
                                            width: 100
                                            height: 12
                                            onPaint: {
                                                var ctx = getContext("2d");
                                                ctx.clearRect(0, 0, width, height);
                                                ctx.strokeStyle = root.activeColor;
                                                ctx.fillStyle = root.activeColor;
                                                ctx.lineWidth = Math.min(4, Math.max(1, root.activeThickness / 3));
                                                
                                                var style = modelData.val;
                                                var cx = width / 2;
                                                var cy = height / 2;
                                                
                                                ctx.beginPath();
                                                ctx.moveTo(10, cy);
                                                
                                                if (style === "dashed") { ctx.setLineDash([6, 6]); ctx.lineTo(width - 10, cy); ctx.stroke(); }
                                                else if (style === "dotted") { ctx.setLineDash([2, 4]); ctx.lineTo(width - 10, cy); ctx.stroke(); }
                                                else if (style === "advance") { ctx.lineTo(width - 15, cy); ctx.stroke(); ctx.beginPath(); ctx.moveTo(width - 15, cy - 4); ctx.lineTo(width - 5, cy); ctx.lineTo(width - 15, cy + 4); ctx.fill(); }
                                                else if (style === "retreat") { ctx.moveTo(25, cy); ctx.lineTo(width - 10, cy); ctx.stroke(); ctx.beginPath(); ctx.moveTo(25, cy - 4); ctx.lineTo(15, cy); ctx.lineTo(25, cy + 4); ctx.fill(); }
                                                else if (style === "double_movement") { ctx.moveTo(25, cy); ctx.lineTo(width - 25, cy); ctx.stroke(); ctx.beginPath(); ctx.moveTo(25, cy - 4); ctx.lineTo(15, cy); ctx.lineTo(25, cy + 4); ctx.fill(); ctx.beginPath(); ctx.moveTo(width - 25, cy - 4); ctx.lineTo(width - 15, cy); ctx.lineTo(width - 25, cy + 4); ctx.fill(); }
                                                else if (style === "defensive_line" || style === "barricade") {
                                                    ctx.lineTo(width - 10, cy); ctx.stroke();
                                                    var spacing = style === "barricade" ? 8 : 25;
                                                    for(var x = 20; x < width - 15; x += spacing) {
                                                        ctx.beginPath(); ctx.moveTo(x-4, cy); ctx.lineTo(x+4, cy); ctx.lineTo(x, cy-6); ctx.fill();
                                                    }
                                                }
                                                else if (style === "minefield") {
                                                    ctx.lineTo(width - 10, cy); ctx.stroke();
                                                    for(var x = 20; x < width - 15; x += 25) {
                                                        ctx.beginPath(); ctx.moveTo(x-3, cy-3); ctx.lineTo(x+3, cy+3); ctx.stroke();
                                                        ctx.beginPath(); ctx.moveTo(x-3, cy+3); ctx.lineTo(x+3, cy-3); ctx.stroke();
                                                    }
                                                }
                                                else if (style === "checkpoint") {
                                                    ctx.lineTo(width - 10, cy); ctx.stroke();
                                                    for(var x = 20; x < width - 15; x += 25) {
                                                        ctx.fillRect(x-3, cy-3, 6, 6);
                                                    }
                                                }
                                                else if (style === "barrier") {
                                                    ctx.lineTo(width - 10, cy); ctx.stroke();
                                                    for(var x = 15; x < width - 10; x += 8) {
                                                        ctx.beginPath(); ctx.moveTo(x, cy-4); ctx.lineTo(x, cy+4); ctx.stroke();
                                                    }
                                                }
                                                else { ctx.lineTo(width - 10, cy); ctx.stroke(); }
                                            }
                                            Connections {
                                                target: root
                                                function onActiveColorChanged() { previewCanvas.requestPaint(); }
                                                function onActiveThicknessChanged() { previewCanvas.requestPaint(); }
                                            }
                                        }
                                        Text { text: modelData.label; color: root.activeLineStyle === modelData.val ? "white" : (settingsController.textColor || "white"); font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter; width: parent.width }
                                    }
                                    
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.activeLineStyle = modelData.val
                                        cursorShape: Qt.PointingHandCursor
                                    }
                                }
                            }
                        }
                    }
                    
                    // Espessura
                    Column {
                        width: parent.width
                        spacing: 4
                        Text { text: "Espessura"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 11 }
                        Slider {
                            width: parent.width
                            from: 1; to: 30; value: root.activeThickness; stepSize: 1
                            onValueChanged: root.activeThickness = value
                        }
                    }
                    
                    // Opacidade
                    Column {
                        width: parent.width
                        spacing: 4
                        Text { text: "Opacidade"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 11 }
                        Slider {
                            width: parent.width
                            from: 0.1; to: 1.0; value: root.activeOpacity; stepSize: 0.1
                            onValueChanged: root.activeOpacity = value
                        }
                    }
                }
            }
            
            // Tab 1: ESPECIAIS
            ScrollView {
                anchors.fill: parent
                visible: root.currentTab === 2
                OpacityAnimator on opacity { from: 0; to: 1; duration: 200; running: root.currentTab === 2 }
                
                Column {
                    width: parent.width
                    spacing: 16
                    
                    Column {
                        width: parent.width
                        spacing: 8
                        Text { text: "Configuração de Setas"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 11; font.bold: true }
                        
                        Text { text: "Posicionamento Local"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 10 }
                        RowLayout {
                            width: parent.width
                            CheckBox { text: "Acima"; checked: root.arrowPlacement === "above" || root.arrowPlacement === "above_below"; onClicked: togglePlacement("above") }
                            CheckBox { text: "Centro"; checked: root.arrowPlacement === "center"; onClicked: togglePlacement("center") }
                            CheckBox { text: "Abaixo"; checked: root.arrowPlacement === "below" || root.arrowPlacement === "above_below"; onClicked: togglePlacement("below") }
                        }
                        
                        Text { text: "Repetição"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 10 }
                        Flow {
                            width: parent.width
                            RadioButton { text: "Nenhuma"; checked: root.arrowPosition === "none"; onClicked: root.arrowPosition = "none" }
                            RadioButton { text: "Início"; checked: root.arrowPosition === "start"; onClicked: root.arrowPosition = "start" }
                            RadioButton { text: "Final"; checked: root.arrowPosition === "end"; onClicked: root.arrowPosition = "end" }
                            RadioButton { text: "Ambos"; checked: root.arrowPosition === "both"; onClicked: root.arrowPosition = "both" }
                            RadioButton { text: "Repetir (Fluxo)"; checked: root.arrowPosition === "repeat"; onClicked: root.arrowPosition = "repeat" }
                        }
                    }
                    
                    Rectangle { width: parent.width; height: 1; color: settingsController.borderColor || "#444" }
                    
                    Column {
                        width: parent.width
                        spacing: 8
                        Text { text: "Atributos Adicionais"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 11; font.bold: true }
                        
                        Loader {
                            sourceComponent: customSwitchComponent
                            width: parent.width
                            onLoaded: {
                                item.iconText = "🖍"
                                item.labelText = "Marca-Texto"
                                item.checked = Qt.binding(function() { return root.activeHighlight; })
                                item.checkedChanged.connect(function() { root.activeHighlight = item.checked; })
                            }
                        }
                        
                        Loader {
                            sourceComponent: customSwitchComponent
                            width: parent.width
                            onLoaded: {
                                item.iconText = "🔒"
                                item.labelText = "Travar Desenho"
                                item.checked = Qt.binding(function() { return root.activeLocked; })
                                item.checkedChanged.connect(function() { root.activeLocked = item.checked; })
                            }
                        }
                        
                        Loader {
                            sourceComponent: customSwitchComponent
                            width: parent.width
                            onLoaded: {
                                item.iconText = "💬"
                                item.labelText = "Perguntar Descrição"
                                item.checked = Qt.binding(function() { return !root.skipBrushNameDialog; })
                                item.checkedChanged.connect(function() { 
                                    root.resetDescriptionDialog(item.checked);
                                })
                            }
                        }
                    }
                    
                    Rectangle { width: parent.width; height: 1; color: settingsController.borderColor || "#444" }
                    
                    Column {
                        width: parent.width
                        spacing: 8
                        Text { text: "⏳ Expiração Automática"; color: settingsController.mutedTextColor || "#888"; font.pixelSize: 11; font.bold: true }
                        
                        RowLayout {
                            width: parent.width
                            spacing: 4
                            Repeater {
                                model: [{val: 0, lbl: "Nunca"}, {val: 30, lbl: "30s"}, {val: 60, lbl: "1m"}, {val: 300, lbl: "5m"}, {val: 600, lbl: "10m"}]
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    height: 32; radius: 6
                                    color: root.activeExpiration === modelData.val ? (settingsController.accentColor || "#3b82f6") : "transparent"
                                    border.color: settingsController.borderColor || "#444"; border.width: 1
                                    Text { anchors.centerIn: parent; text: modelData.lbl; color: "white"; font.pixelSize: 11; font.bold: root.activeExpiration === modelData.val }
                                    MouseArea { anchors.fill: parent; onClicked: root.activeExpiration = modelData.val; cursorShape: Qt.PointingHandCursor }
                                }
                            }
                        }
                        
                        Text {
                            text: "Este desenho será removido automaticamente."
                            color: "#eab308"
                            font.pixelSize: 10
                            font.italic: true
                            visible: root.activeExpiration > 0
                        }
                    }
                }
            }
        }
    }
    
    function togglePlacement(p) {
        if (p === "center") {
            root.arrowPlacement = "center";
            return;
        }
        if (root.arrowPlacement === "center") root.arrowPlacement = p;
        else if (p === "above" && root.arrowPlacement === "below") root.arrowPlacement = "above_below";
        else if (p === "below" && root.arrowPlacement === "above") root.arrowPlacement = "above_below";
        else if (p === "above" && root.arrowPlacement === "above_below") root.arrowPlacement = "below";
        else if (p === "below" && root.arrowPlacement === "above_below") root.arrowPlacement = "above";
        else if (p === root.arrowPlacement) root.arrowPlacement = "center";
    }
    
    function loadSymbols() {
        filterSymbols();
    }
    
    function filterSymbols() {
        symbolsListModel.clear();
        var allSyms = SymbolData.getSymbols();
        var q = root.symbolSearchQuery;
        var cat = root.symbolActiveCategory;
        for(var i=0; i<allSyms.length; i++) {
            var matchCat = (cat === "Todos" || allSyms[i].category === cat);
            var matchQuery = (q === "" || allSyms[i].label.toLowerCase().indexOf(q) !== -1 || allSyms[i].id.toLowerCase().indexOf(q) !== -1);
            if (matchCat && matchQuery) {
                symbolsListModel.append({
                    symId: allSyms[i].id,
                    symIcon: allSyms[i].icon,
                    symFallback: allSyms[i].fallbackIcon || "?",
                    symLabel: allSyms[i].label
                });
            }
        }
    }
}
