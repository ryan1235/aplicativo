import os

file_path = r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qml\components\MapView.qml'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace mapTextItemsModel delegate bindings
old_text_bindings = """                x: worldPxX - width / 2
                y: worldPxY - height / 2
                
                width: labelText.implicitWidth
                height: labelText.implicitHeight
                
                property bool inBounds: true"""

new_text_bindings = """                x: worldPxX - width / 2
                y: worldPxY - height / 2
                
                width: itemLoader.item ? itemLoader.item.implicitWidth : 0
                height: itemLoader.item ? itemLoader.item.implicitHeight : 0
                
                property bool inBounds: true"""

content = content.replace(old_text_bindings, new_text_bindings)

# Replace mapTextItemsModel visibility and Text
old_text_delegate = """                visible: {
                    if (!inBounds) return false;
                    
                    if (modelData.mapMarkerType === "Hex") return root.showHexNames && root.currentZoom >= 0;
                    if (modelData.mapMarkerType === "Major") return root.showMajorCities && root.currentZoom >= 4;
                    if (modelData.mapMarkerType === "Minor") return root.showMinorCities && root.currentZoom >= 5;
                    return true;
                }
                
                property bool isMajor: modelData.mapMarkerType === "Major"
                property bool isHex: modelData.mapMarkerType === "Hex"
                
                Text {
                    id: labelText
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
                }"""

new_text_delegate = """                property bool shouldShow: {
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
                }"""

content = content.replace(old_text_delegate, new_text_delegate)

# Replace mapItemsModel visibility
old_map_items_vis = """                // Hide if out of bounds or zoom too low
                visible: {
                    if (!inBounds) return false;
                    if (hasStock) return true;
                    if (root.currentZoom < 5) return false;
                    if (isResource) return root.showResources;
                    return root.showIcons;
                }
                
                // Set appropriate icon size
                width: hasStock ? 30 : 24
                height: hasStock ? 30 : 24
                
                Image {"""

new_map_items_vis = """                property bool shouldShow: {
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
                
                Loader {
                    anchors.fill: parent
                    active: shouldShow
                    sourceComponent: Item {
                        anchors.fill: parent
                        
                Image {"""

content = content.replace(old_map_items_vis, new_map_items_vis)

# Insert closing braces for the Loader at the end of the delegate
old_end_of_delegate = """                            }
                        }
                    }
                }
            }
        }
    }

    // --- MAP FILTERS UI ---"""

new_end_of_delegate = """                            }
                        }
                    }
                }
                    }
                }
            }
        }
    }

    // --- MAP FILTERS UI ---"""

content = content.replace(old_end_of_delegate, new_end_of_delegate)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done optimizing MapView.qml')
