import os
import re

file_path = r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qml\components\MapView.qml'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove hexControlData and updateHexControl
start_hex_ctrl = content.find('    // Faction Territory Data')
end_hex_ctrl = content.find('    function tr(key, fallback)')
if start_hex_ctrl != -1 and end_hex_ctrl != -1:
    content = content[:start_hex_ctrl] + content[end_hex_ctrl:]

# 2. Remove Map Filters properties
old_filters = '''    // Map Filters
    property bool showTerritoryControl: false
    property bool showHexNames: true
    property bool showMajorCities: true
    property bool showMinorCities: false
    property bool showResources: true
    property bool showIcons: true
    property bool showStockFilter: true'''

new_filters = '''    // Map Filters
    property bool showHexNames: true
    property bool showStockFilter: true'''

if old_filters in content:
    content = content.replace(old_filters, new_filters)
else:
    print("Warning: old_filters not found")

# 3. Remove Territory Control Overlay Repeater
overlay_pattern = r'        // --- Territory Control Overlay ---.*?(?=        Repeater \{\s*model: typeof mapController !== "undefined" && mapController \? mapController\.testItemsModel)'
content, count = re.subn(overlay_pattern, '', content, flags=re.DOTALL)
if count == 0:
    print("Warning: territory overlay not found")

# 4. mapTextItemsModel shouldShow
old_text_should = '''                property bool shouldShow: {
                    if (!inBounds) return false;
                    
                    if (modelData.mapMarkerType === "Hex") return root.showHexNames && root.currentZoom >= 0;
                    if (modelData.mapMarkerType === "Major") return root.showMajorCities && root.currentZoom >= 4;
                    if (modelData.mapMarkerType === "Minor") return root.showMinorCities && root.currentZoom >= 5;
                    return true;
                }'''

new_text_should = '''                property bool shouldShow: {
                    if (!inBounds) return false;
                    
                    if (modelData.mapMarkerType === "Hex") return root.showHexNames && root.currentZoom >= 0;
                    return false;
                }'''

if old_text_should in content:
    content = content.replace(old_text_should, new_text_should)
else:
    print("Warning: old_text_should not found")


# 5. mapItemsModel isResource and shouldShow
old_items_vis = '''                property bool isResource: {
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

new_items_vis = '''                property bool hasStock: root.showStockFilter && modelData.stock !== undefined
                
                property bool shouldShow: {
                    if (!inBounds) return false;
                    return hasStock;
                }'''

if old_items_vis in content:
    content = content.replace(old_items_vis, new_items_vis)
else:
    print("Warning: old_items_vis not found")

# 6. Filter UI
old_ui = '''            StyledCheckBox { 
                text: root.tr("map.filter.territory", "Zonas de Controle")
                checked: root.showTerritoryControl
                onCheckedChanged: root.showTerritoryControl = checked
            }
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
                text: root.tr("map.filter.icons", "Estruturas Gerais")
                checked: root.showIcons
                onCheckedChanged: root.showIcons = checked
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
                text: root.tr("map.filter.stock", "Depósitos com Estoque")
                checked: root.showStockFilter
                onCheckedChanged: root.showStockFilter = checked
            }'''

if old_ui in content:
    content = content.replace(old_ui, new_ui)
else:
    print("Warning: old_ui not found")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Cleanup done!')
