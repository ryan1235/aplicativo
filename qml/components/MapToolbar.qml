import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import "MapToolsData.js" as ToolsData

Item {
    id: root
    width: toolbarRow.implicitWidth + 32
    height: 50
    
    property string activeTool: "pan"
    signal toolSelected(string toolId)
    signal toggleSettings()

    // No longer depends on globalToolTip, it brings its own modern tooltip
    property Item globalToolTip: null
    
    Rectangle {
        id: toolbarBg
        anchors.fill: parent
        radius: 25
        color: Qt.rgba(settingsController.surfaceColor.r, settingsController.surfaceColor.g, settingsController.surfaceColor.b, 0.85)
        border.color: Qt.rgba(settingsController.borderColor.r, settingsController.borderColor.g, settingsController.borderColor.b, 0.5)
        border.width: 1
    }

    MultiEffect {
        source: toolbarBg
        anchors.fill: toolbarBg
        shadowEnabled: true
        shadowOpacity: 0.5
        shadowBlur: 1.5
        shadowVerticalOffset: 4
        shadowColor: "black"
        blurEnabled: true
        blur: 0.8
    }

    Row {
        id: toolbarRow
        anchors.centerIn: parent
        spacing: 8

        Repeater {
            model: {
                var groups = [];
                var lastGroup = -1;
                var displayList = [];
                for(var i=0; i<ToolsData.tools.length; i++) {
                    var t = ToolsData.tools[i];
                    if (t.isImplemented) {
                        if (lastGroup !== -1 && t.group !== lastGroup) {
                            displayList.push({ isSeparator: true });
                        }
                        displayList.push({ isSeparator: false, tool: t });
                        lastGroup = t.group;
                    }
                }
                return displayList;
            }

            delegate: Item {
                width: modelData.isSeparator ? 9 : 36
                height: 36
                
                // Separator
                Rectangle {
                    visible: modelData.isSeparator
                    width: 1
                    height: 24
                    anchors.centerIn: parent
                    color: Qt.rgba(settingsController.borderColor.r, settingsController.borderColor.g, settingsController.borderColor.b, 0.5)
                }

                // Tool Button
                Rectangle {
                    visible: !modelData.isSeparator
                    width: 36
                    height: 36
                    radius: 18
                    color: (root.activeTool === (modelData.tool ? modelData.tool.id : "")) ? (settingsController.accentColor || "#3b82f6") : (mouseArea.containsMouse ? (settingsController.hoverColor || Qt.rgba(1,1,1,0.1)) : "transparent")
                    border.color: (root.activeTool === (modelData.tool ? modelData.tool.id : "")) ? (settingsController.accentColor || "#3b82f6") : "transparent"
                    border.width: 1
                    
                    scale: mouseArea.containsMouse ? ((root.activeTool === (modelData.tool ? modelData.tool.id : "")) ? 1.10 : 1.05) : ((root.activeTool === (modelData.tool ? modelData.tool.id : "")) ? 1.10 : 1.0)
                    Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutQuad } }
                    Behavior on color { ColorAnimation { duration: 150 } }

                    MultiEffect {
                        source: parent
                        anchors.fill: parent
                        shadowEnabled: root.activeTool === (modelData.tool ? modelData.tool.id : "")
                        shadowColor: settingsController.accentColor || "#3b82f6"
                        shadowBlur: 1.0
                        shadowOpacity: 0.8
                        visible: root.activeTool === (modelData.tool ? modelData.tool.id : "")
                    }

                    Text {
                        anchors.centerIn: parent
                        text: modelData.tool ? modelData.tool.icon : ""
                        font.pixelSize: 18
                        color: (root.activeTool === (modelData.tool ? modelData.tool.id : "")) ? "white" : (settingsController.textColor || "white")
                    }

                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        
                        onClicked: {
                            if (!modelData.tool) return;
                            if (root.activeTool === modelData.tool.id && modelData.tool.hasProperties) {
                                root.toggleSettings();
                            } else {
                                root.toolSelected(modelData.tool.id);
                            }
                        }

                        Timer {
                            id: hoverTimer
                            interval: 300
                            onTriggered: {
                                if (mouseArea.containsMouse && modelData.tool) {
                                    // Center tooltip relative to the button instead of mouse cursor
                                    var btnCenterPt = mapToItem(root, parent.width / 2, parent.height / 2);
                                    
                                    var activeLang = "en";
                                    if (typeof i18nController !== "undefined" && i18nController.currentLanguage) {
                                        activeLang = i18nController.currentLanguage;
                                    } else {
                                        if (typeof i18nController !== "undefined") {
                                            var trTest = i18nController.t("tool.pan.name");
                                            if (trTest === "Mover") activeLang = "pt";
                                        }
                                    }
                                    
                                    var activeName = modelData.tool.names ? (modelData.tool.names[activeLang] || modelData.tool.names.pt) : modelData.tool.translationKey;
                                    var activeDesc = modelData.tool.desc ? (modelData.tool.desc[activeLang] || modelData.tool.desc.pt) : "";
                                    
                                    var text = "<b>" + activeName + "</b> (" + modelData.tool.shortcut + ")<br>";
                                    
                                    if (modelData.tool.names) {
                                        text += "<br>🇧🇷 " + (modelData.tool.names.pt || "");
                                        text += "<br>🇺🇸 " + (modelData.tool.names.en || "");
                                        text += "<br>🇪🇸 " + (modelData.tool.names.es || "");
                                        text += "<br>🇫🇷 " + (modelData.tool.names.fr || "");
                                    }
                                    
                                    if (activeDesc) {
                                        text += "<br><br>" + activeDesc;
                                    }

                                    modernTooltip.text = text;
                                    modernTooltip.x = btnCenterPt.x - (modernTooltip.width / 2);
                                    modernTooltip.y = btnCenterPt.y - (parent.height / 2) - modernTooltip.height - 15;
                                    modernTooltip.visible = true;
                                }
                            }
                        }

                        onContainsMouseChanged: {
                            if (containsMouse) hoverTimer.start();
                            else {
                                hoverTimer.stop();
                                modernTooltip.visible = false;
                            }
                        }
                    }
                }
            }
        }
    }

    // Modern self-contained Tooltip
    Item {
        id: modernTooltip
        visible: false
        z: 1000
        width: tooltipContent.width + 24
        height: tooltipContent.height + 24
        
        property alias text: tooltipContent.text
        
        Behavior on opacity { NumberAnimation { duration: 150 } }
        opacity: visible ? 1.0 : 0.0

        Rectangle {
            id: tooltipBg
            anchors.fill: parent
            radius: 12
            color: Qt.rgba(settingsController.surfaceColor.r, settingsController.surfaceColor.g, settingsController.surfaceColor.b, 0.95)
            border.color: Qt.rgba(settingsController.borderColor.r, settingsController.borderColor.g, settingsController.borderColor.b, 0.8)
            border.width: 1
        }
        
        MultiEffect {
            source: tooltipBg
            anchors.fill: tooltipBg
            shadowEnabled: true
            shadowOpacity: 0.6
            shadowBlur: 1.5
            shadowVerticalOffset: 4
            shadowColor: "black"
            blurEnabled: true
            blur: 0.5
        }
        
        Text {
            id: tooltipContent
            anchors.centerIn: parent
            color: settingsController.textColor || "white"
            font.pixelSize: 12
            textFormat: Text.RichText
            lineHeight: 1.2
        }
    }
}
