import os

file_path = r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qml\components\MapView.qml'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Restore Map Filters properties
old_filters = '''    // Map Filters
    property bool showHexNames: true
    property bool showStockFilter: true'''

new_filters = '''    // Map Filters
    property bool showHexNames: true
    property bool showMajorCities: false
    property bool showMinorCities: false
    property bool showResources: false
    property bool showIcons: false
    property bool showStockFilter: true'''

content = content.replace(old_filters, new_filters)

# 2. Restore mapTextItemsModel shouldShow
old_text_should = '''                property bool shouldShow: {
                    if (!inBounds) return false;
                    
                    if (modelData.mapMarkerType === "Hex") return root.showHexNames && root.currentZoom >= 0;
                    return false;
                }'''

new_text_should = '''                property bool shouldShow: {
                    if (!inBounds) return false;
                    
                    if (modelData.mapMarkerType === "Hex") return root.showHexNames && root.currentZoom >= 0;
                    if (modelData.mapMarkerType === "Major") return root.showMajorCities && root.currentZoom >= 4;
                    if (modelData.mapMarkerType === "Minor") return root.showMinorCities && root.currentZoom >= 5;
                    return true;
                }'''

content = content.replace(old_text_should, new_text_should)


# 3. Restore mapItemsModel isResource and shouldShow
old_items_vis = '''                property bool hasStock: root.showStockFilter && modelData.stock !== undefined
                
                property bool shouldShow: {
                    if (!inBounds) return false;
                    return hasStock;
                }'''

new_items_vis = '''                property bool isResource: {
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
                }'''

content = content.replace(old_items_vis, new_items_vis)

# 4. Restore Filter UI
old_ui = '''            StyledCheckBox { 
                text: root.tr("map.filter.hex", "Regiões (Hex)")
                checked: root.showHexNames
                onCheckedChanged: root.showHexNames = checked
            }
            StyledCheckBox { 
                text: root.tr("map.filter.stock", "Depósitos com Estoque")
                checked: root.showStockFilter
                onCheckedChanged: root.showStockFilter = checked
            }'''

new_ui = '''            StyledCheckBox { 
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
            }'''

content = content.replace(old_ui, new_ui)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Restore done!')
