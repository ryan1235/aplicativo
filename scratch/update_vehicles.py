import json
import os

vehicles_json_path = r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\img\vaiculos\vehicles.json'
vehicles_js_path = r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qml\components\Vehicles.js'

with open(vehicles_json_path, 'r', encoding='utf-8') as f:
    vehicles_data = json.load(f)

new_category = {
    "id": "vehicles",
    "name": "Catálogo de Veículos",
    "items": []
}

for key, val in vehicles_data.items():
    name = val.get("name", key.title())
    faction_str = val.get("faction", "").lower()
    
    faction_code = "n"
    if "warden" in faction_str:
        faction_code = "w"
    elif "colonial" in faction_str:
        faction_code = "c"
        
    item_id = key.lower().replace(" ", "_").replace("'", "")
    
    images = val.get("images", {})
    small_img = images.get("small")
    if small_img:
        image_path = "../vaiculos/" + small_img
    else:
        image_path = "../vaiculos/small/" + key + ".webp"
        
    new_category["items"].append({
        "id": item_id,
        "name": name,
        "image": image_path,
        "faction": faction_code
    })

original_boats_items = [
    { "id": "blacksteele", "name": "Blacksteele", "image": "Blacksteele.png", "faction": "w" },
    { "id": "callahan", "name": "Callahan", "image": "Callahan.png", "faction": "w" },
    { "id": "charon", "name": "Charon Gunboat", "image": "Charon Gunboat.png", "faction": "c" },
    { "id": "conqueror", "name": "Conqueror", "image": "Conqueror.png", "faction": "c" },
    { "id": "longhook", "name": "Longhook", "image": "Longhook.png", "faction": "n" },
    { "id": "lucian", "name": "Lucian", "image": "Lucian.png", "faction": "w" },
    { "id": "mercy", "name": "Mercy", "image": "Mercy.png", "faction": "w" },
    { "id": "nakki", "name": "Nakki", "image": "Nakki.png", "faction": "w" },
    { "id": "poseidon", "name": "Poseidon", "image": "Poseidon.png", "faction": "c" },
    { "id": "rinnspeir", "name": "Rinnspeir", "image": "Rinnspeir Gunship.png", "faction": "w" },
    { "id": "ronan_blackguard", "name": "Ronan B.", "image": "Ronan Blackguard.png", "faction": "w" },
    { "id": "ronan_fathomer", "name": "Ronan F.", "image": "Ronan Fathomer.png", "faction": "w" },
    { "id": "ronan_gunboat", "name": "Ronan G.", "image": "Ronan Gunboat.png", "faction": "w" },
    { "id": "sombre", "name": "Sombre", "image": "Sombre.png", "faction": "c" },
    { "id": "strider", "name": "Strider", "image": "Strider.png", "faction": "c" },
    { "id": "titan", "name": "Titan", "image": "Titan.png", "faction": "c" },
    { "id": "trident", "name": "Trident", "image": "Trident.png", "faction": "c" },
    { "id": "barge", "name": "Barge", "image": "barge.png", "faction": "n" }
]

boats_category = {
    "id": "boats",
    "name": "Catálogo de Embarcações",
    "items": original_boats_items
}

categories = [boats_category, new_category]
data = {"categories": categories}

new_js = ".pragma library\n\nvar data = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n"

with open(vehicles_js_path, 'w', encoding='utf-8') as f:
    f.write(new_js)
