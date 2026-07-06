import urllib.request
import json

try:
    print("Fetching Map Items...")
    req = urllib.request.Request("https://foxlogi.com/api/map-items/", headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    data = json.loads(response.read().decode())
    
    unique_data = []
    seen_names = set()
    for item in data:
        name = item.get("name")
        if name:
            if name in seen_names: continue
            seen_names.add(name)
        unique_data.append(item)
    
    _map_items = unique_data
    print(f"Loaded {_map_items.__len__()} unique map items.")

    print("Fetching Test Data...")
    req = urllib.request.Request(
        "https://felblogi.discloud.app/data",
        data=b'{"mode": "debug"}',
        headers={'Content-Type': 'application/json', 'X-API-Key': 'AIza7m3-iCHSlTbLDavZkAM-6Gv0zRClL30XbRS'},
        method='GET'
    )
    response = urllib.request.urlopen(req)
    raw_data = json.loads(response.read().decode())
    
    loc_map = {}
    for m_item in _map_items:
        name = m_item.get("name")
        if name:
            loc_map[name] = (m_item.get("x", 0), m_item.get("y", 0))

    warehouses = {}
    for item in raw_data.get("data", []):
        wh = item.get("warehouse", {})
        wh_name = item.get("WarehouseName", "Unknown")
        town_name = wh.get("town", "").strip()
        
        real_coords = loc_map.get(town_name)
        if wh_name not in warehouses:
            if real_coords:
                final_x, final_y = real_coords
                print(f"MATCH: {wh_name} -> {town_name} -> {final_x}, {final_y}")
            else:
                final_x = wh.get("x", 0) * 150
                final_y = -wh.get("y", 0) * 150
                print(f"FALLBACK: {wh_name} -> {town_name} -> {final_x}, {final_y}")
                
            warehouses[wh_name] = {
                "name": wh_name,
                "x": final_x,
                "y": final_y,
                "items": []
            }
except Exception as e:
    print("Error:", e)
