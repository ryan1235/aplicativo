import urllib.request
import json
import math

print("Fetching foxlogi map-items...")
foxlogi_req = urllib.request.urlopen('https://foxlogi.com/api/map-items/', timeout=10)
foxlogi_data = json.loads(foxlogi_req.read().decode())
foxlogi_dict = {item['name']: (item['x'], item['y']) for item in foxlogi_data if 'name' in item}

maps_req = urllib.request.urlopen('https://war-service-live.foxholeservices.com/api/worldconquest/maps')
maps = json.loads(maps_req.read().decode())

dx_pairs = []
dy_pairs = []

for m in maps:
    try:
        req = urllib.request.urlopen(f'https://war-service-live.foxholeservices.com/api/worldconquest/maps/{m}/static')
        data = json.loads(req.read().decode())
        
        matches = []
        for text_item in data.get('mapTextItems', []):
            name = text_item.get('text')
            if name in foxlogi_dict:
                matches.append((name, foxlogi_dict[name][0], foxlogi_dict[name][1], text_item['x'], text_item['y']))
                
        # Get pairwise distances inside the same hex
        for i in range(len(matches)):
            for j in range(i+1, len(matches)):
                name1, gx1, gy1, lx1, ly1 = matches[i]
                name2, gx2, gy2, lx2, ly2 = matches[j]
                
                dgx = gx2 - gx1
                dlx = lx2 - lx1
                if abs(dlx) > 0.1:
                    dx_pairs.append(dgx / dlx)
                    
                dgy = gy2 - gy1
                dly = ly2 - ly1
                if abs(dly) > 0.1:
                    dy_pairs.append(dgy / dly)
                    
    except Exception:
        pass

dx_pairs.sort()
dy_pairs.sort()

# Use median to ignore outliers (like wrong town matches)
if dx_pairs and dy_pairs:
    med_scale_x = dx_pairs[len(dx_pairs)//2]
    med_scale_y = dy_pairs[len(dy_pairs)//2]
    print(f"Global Median SCALE_X: {med_scale_x}")
    print(f"Global Median SCALE_Y: {med_scale_y}")
else:
    print("Not enough pairs")
