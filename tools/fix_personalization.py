import os
import json
import re

# 1. Update Translations
translations = {
    'pt': {
        "map.stock.title": "Visual do estoque",
        "map.stock.updated": "Atualizado",
        "map.stock.priority": "PRIORIDADE",
        "map.stock.supplies": "SUPRIMENTOS",
        "map.stock.common_logi": "LOGI COMUM",
        "map.stock.vehicles": "VEÍCULOS",
        "map.stock.others": "OUTROS",
        "map.filter.title": "Filtros do Mapa",
        "map.filter.hex": "Regiões (Hex)",
        "map.filter.major": "Cidades Principais",
        "map.filter.minor": "Sub-regiões (Vilas)",
        "map.filter.resources": "Recursos (Campos/Minas)",
        "map.filter.icons": "Estruturas Gerais",
        "map.filter.stock": "Depósitos com Estoque"
    },
    'en': {
        "map.stock.title": "Stock View",
        "map.stock.updated": "Updated",
        "map.stock.priority": "PRIORITY",
        "map.stock.supplies": "SUPPLIES",
        "map.stock.common_logi": "COMMON LOGI",
        "map.stock.vehicles": "VEHICLES",
        "map.stock.others": "OTHERS",
        "map.filter.title": "Map Filters",
        "map.filter.hex": "Regions (Hex)",
        "map.filter.major": "Major Cities",
        "map.filter.minor": "Sub-regions (Towns)",
        "map.filter.resources": "Resources (Fields/Mines)",
        "map.filter.icons": "General Structures",
        "map.filter.stock": "Stocked Depots"
    },
    'es': {
        "map.stock.title": "Vista de Inventario",
        "map.stock.updated": "Actualizado",
        "map.stock.priority": "PRIORIDAD",
        "map.stock.supplies": "SUMINISTROS",
        "map.stock.common_logi": "LOGI COMÚN",
        "map.stock.vehicles": "VEHÍCULOS",
        "map.stock.others": "OTROS",
        "map.filter.title": "Filtros de Mapa",
        "map.filter.hex": "Regiones (Hex)",
        "map.filter.major": "Ciudades Principales",
        "map.filter.minor": "Subregiones (Villas)",
        "map.filter.resources": "Recursos (Campos/Minas)",
        "map.filter.icons": "Estructuras Generales",
        "map.filter.stock": "Depósitos con Stock"
    },
    'fr': {
        "map.stock.title": "Vue du Stock",
        "map.stock.updated": "Mis à jour",
        "map.stock.priority": "PRIORITÉ",
        "map.stock.supplies": "FOURNITURES",
        "map.stock.common_logi": "LOGI COMMUN",
        "map.stock.vehicles": "VÉHICULES",
        "map.stock.others": "AUTRES",
        "map.filter.title": "Filtres de Carte",
        "map.filter.hex": "Régions (Hex)",
        "map.filter.major": "Villes Principales",
        "map.filter.minor": "Sous-régions (Villes)",
        "map.filter.resources": "Ressources (Champs/Mines)",
        "map.filter.icons": "Structures Générales",
        "map.filter.stock": "Dépôts avec Stock"
    }
}

base_path = r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\translations'
for lang, trans_dict in translations.items():
    file_path = os.path.join(base_path, lang, 'translation.json')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # update the data with our dict
        for k, v in trans_dict.items():
            data[k] = v
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Updated {lang}/translation.json")

# 2. Update MapView.qml
qml_path = r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qml\components\MapView.qml'
with open(qml_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make the stock Hover Card use theme colors
content = content.replace('color: "#181A1F"', 'color: settingsController.surfaceColor')
content = content.replace('border.color: "#333840"', 'border.color: settingsController.borderColor')
content = content.replace('color: "#2a2e35"', 'color: settingsController.backgroundColor')
content = content.replace('color: "#FFFFFF"', 'color: settingsController.textColor')
content = content.replace('color: "#BBBBBB"', 'color: settingsController.mutedTextColor')
content = content.replace('color: "#888888"', 'color: settingsController.mutedTextColor')
content = content.replace('color: Qt.rgba(1, 1, 1, 0.1)', 'color: settingsController.borderColor')

# Fix the category logic in getItemsByCategory
old_get_items = '''                    function getItemsByCategory(catName) {
                        if (!currentWarehouse || !currentWarehouse.items) return [];
                        var res = [];
                        for (var i = 0; i < currentWarehouse.items.length; i++) {
                            var item = currentWarehouse.items[i];
                            // Match categories (or map multiple API categories to the UI category)
                            if (catName === "PRIORIDADE" && item.category === "Priority") {
                                res.push(item);
                            } else if (catName === "SUPRIMENTOS" && (item.category === "Supplies" || item.category === "Medical" || item.category === "Utility")) {
                                res.push(item);
                            } else if (catName === "LOGI COMUM" && (item.category === "Small Arms" || item.category === "Heavy Arms" || item.category === "Heavy Ammo")) {
                                res.push(item);
                            } else if (catName === "VEÍCULOS" && item.category === "Vehicles") {
                                res.push(item);
                            } else if (catName === "OUTROS" && item.category !== "Priority" && item.category !== "Supplies" && item.category !== "Medical" && item.category !== "Utility" && item.category !== "Small Arms" && item.category !== "Heavy Arms" && item.category !== "Heavy Ammo" && item.category !== "Vehicles") {
                                res.push(item);
                            }
                        }
                        return res;
                    }'''

new_get_items = '''                    function getItemsByCategory(catKey) {
                        if (!currentWarehouse || !currentWarehouse.items) return [];
                        var res = [];
                        for (var i = 0; i < currentWarehouse.items.length; i++) {
                            var item = currentWarehouse.items[i];
                            // Match categories (or map multiple API categories to the UI category)
                            if (catKey === "Priority" && item.category === "Priority") {
                                res.push(item);
                            } else if (catKey === "Supplies" && (item.category === "Supplies" || item.category === "Medical" || item.category === "Utility")) {
                                res.push(item);
                            } else if (catKey === "CommonLogi" && (item.category === "Small Arms" || item.category === "Heavy Arms" || item.category === "Heavy Ammo")) {
                                res.push(item);
                            } else if (catKey === "Vehicles" && item.category === "Vehicles") {
                                res.push(item);
                            } else if (catKey === "Others" && item.category !== "Priority" && item.category !== "Supplies" && item.category !== "Medical" && item.category !== "Utility" && item.category !== "Small Arms" && item.category !== "Heavy Arms" && item.category !== "Heavy Ammo" && item.category !== "Vehicles") {
                                res.push(item);
                            }
                        }
                        return res;
                    }'''

content = content.replace(old_get_items, new_get_items)

# Update texts to use tr()
old_title_text = 'text: "Visual do estoque"'
new_title_text = 'text: root.tr("map.stock.title", "Visual do estoque")'
content = content.replace(old_title_text, new_title_text)

old_updated_text = 'text: "Atualizado: " + modelData.name + " - " + (stockHoverCard.currentWarehouse ? stockHoverCard.currentWarehouse.last_update : "")'
new_updated_text = 'text: root.tr("map.stock.updated", "Atualizado") + ": " + modelData.name + " - " + (stockHoverCard.currentWarehouse ? stockHoverCard.currentWarehouse.last_update : "")'
content = content.replace(old_updated_text, new_updated_text)

# Update repeater array
old_repeater_model = 'model: ["PRIORIDADE", "SUPRIMENTOS", "LOGI COMUM", "VEÍCULOS", "OUTROS"]'
new_repeater_model = '''model: [
                                { key: "Priority", label: root.tr("map.stock.priority", "PRIORIDADE") },
                                { key: "Supplies", label: root.tr("map.stock.supplies", "SUPRIMENTOS") },
                                { key: "CommonLogi", label: root.tr("map.stock.common_logi", "LOGI COMUM") },
                                { key: "Vehicles", label: root.tr("map.stock.vehicles", "VEÍCULOS") },
                                { key: "Others", label: root.tr("map.stock.others", "OUTROS") }
                            ]'''
content = content.replace(old_repeater_model, new_repeater_model)

# Update category delegate usage
old_cat_items = 'property var catItems: stockHoverCard.getItemsByCategory(modelData)'
new_cat_items = 'property var catItems: stockHoverCard.getItemsByCategory(modelData.key)'
content = content.replace(old_cat_items, new_cat_items)

old_cat_text = 'text: modelData\\n                                    color: settingsController.mutedTextColor'
# I'll just regex replace text: modelData -> text: modelData.label
content = re.sub(r'text:\s*modelData(\s+)color:\s*settingsController.mutedTextColor', r'text: modelData.label\1color: settingsController.mutedTextColor', content)

# Fix filter ui colors
old_filter_ui = '''    component StyledCheckBox: CheckBox {
        id: control
        contentItem: Text {
            text: control.text
            color: "#e0e0e0"
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
            color: control.down ? "#1a1e24" : (control.hovered ? "#333840" : "#2a2e35")
            border.color: control.checked ? "#3b82f6" : "#4a515c"
            border.width: control.checked ? 0 : 1

            Rectangle {
                width: 10
                height: 10
                x: 4
                y: 4
                radius: 2
                color: "#3b82f6"
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
            color: filterButton.hovered ? "#333840" : "#2a2e33"
            border.color: "#4a515c"
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
            color: "white"
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
            color: "#1c2025"
            border.color: "#383f47"'''

new_filter_ui = '''    component StyledCheckBox: CheckBox {
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
            border.color: settingsController.borderColor'''

content = content.replace(old_filter_ui, new_filter_ui)

with open(qml_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('UI customization and translation done!')
