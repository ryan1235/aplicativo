import urllib.request
import json
import math

print("Fetching foxlogi map-items...")
foxlogi_req = urllib.request.urlopen('https://foxlogi.com/api/map-items/', timeout=10)
foxlogi_data = json.loads(foxlogi_req.read().decode())
foxlogi_dict = {item['name']: (item['x'], item['y']) for item in foxlogi_data if 'name' in item}

print("Fetching maps...")
maps_req = urllib.request.urlopen('https://war-service-live.foxholeservices.com/api/worldconquest/maps')
maps = json.loads(maps_req.read().decode())

SCALE_X = 22.524858778047548
SCALE_Y = -16.45235496658322

missing_origins = []

for m in maps:
    try:
        req = urllib.request.urlopen(f'https://war-service-live.foxholeservices.com/api/worldconquest/maps/{m}/static')
        data = json.loads(req.read().decode())
        
        origin_x, origin_y = None, None
        
        for text_item in data.get('mapTextItems', []):
            name = text_item['text']
            if name in foxlogi_dict:
                gx, gy = foxlogi_dict[name]
                lx, ly = text_item['x'], text_item['y']
                origin_x = gx - (lx * SCALE_X)
                origin_y = gy - (ly * SCALE_Y)
                break
                
        if origin_x is None:
            missing_origins.append(m)
    except Exception as e:
        print(f"Error {m}: {e}")

print(f"Missing origins for {len(missing_origins)} hexes out of {len(maps)}: {missing_origins}")
