import urllib.request
import json
import math

print("Fetching foxlogi map-items...")
foxlogi_req = urllib.request.urlopen('https://foxlogi.com/api/map-items/', timeout=10)
foxlogi_data = json.loads(foxlogi_req.read().decode())
foxlogi_dict = {item['name']: (item['x'], item['y']) for item in foxlogi_data if 'name' in item}

maps_req = urllib.request.urlopen('https://war-service-live.foxholeservices.com/api/worldconquest/maps')
maps = json.loads(maps_req.read().decode())

SCALE_X = 25.553590845600255
SCALE_Y = -22.32744119202343

origins = {}

for m in maps:
    try:
        req = urllib.request.urlopen(f'https://war-service-live.foxholeservices.com/api/worldconquest/maps/{m}/static')
        data = json.loads(req.read().decode())
        
        matches = []
        for text_item in data.get('mapTextItems', []):
            name = text_item.get('text')
            if name in foxlogi_dict:
                matches.append((name, foxlogi_dict[name][0], foxlogi_dict[name][1], text_item['x'], text_item['y']))
                
        # Calculate origin for each match in this hex
        hex_ox_list = []
        hex_oy_list = []
        for name, gx, gy, lx, ly in matches:
            ox = gx - (lx * SCALE_X)
            oy = gy - (ly * SCALE_Y)
            hex_ox_list.append(ox)
            hex_oy_list.append(oy)
            
        if hex_ox_list:
            hex_ox_list.sort()
            hex_oy_list.sort()
            med_ox = hex_ox_list[len(hex_ox_list)//2]
            med_oy = hex_oy_list[len(hex_oy_list)//2]
            origins[m] = (med_ox, med_oy)
    except Exception:
        pass

print(f"Calculated origins for {len(origins)} hexes.")
print("DeadLandsHex:", origins.get("DeadLandsHex"))
# Dump dict to file for python script to read
with open('origins.json', 'w') as f:
    json.dump(origins, f)
