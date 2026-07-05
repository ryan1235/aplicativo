import urllib.request
import json
import math

print("Fetching foxlogi map-items...")
foxlogi_req = urllib.request.urlopen('https://foxlogi.com/api/map-items/', timeout=10)
foxlogi_data = json.loads(foxlogi_req.read().decode())
foxlogi_dict = {item['name']: (item['x'], item['y']) for item in foxlogi_data if 'name' in item}

SCALE_X = 22.524858778047548
SCALE_Y = -16.45235496658322

m = "DeadLandsHex"
req = urllib.request.urlopen(f'https://war-service-live.foxholeservices.com/api/worldconquest/maps/{m}/static')
data = json.loads(req.read().decode())

# Step 1: Rough calibration
rough_origin_x, rough_origin_y = None, None
rough_name = None
for text_item in data.get('mapTextItems', []):
    name = text_item.get('text')
    if name in foxlogi_dict:
        gx, gy = foxlogi_dict[name]
        lx, ly = text_item.get('x', 0), text_item.get('y', 0)
        rough_origin_x = gx - (lx * SCALE_X)
        rough_origin_y = gy - (ly * SCALE_Y)
        rough_name = name
        break

print(f"Rough Origin for {m} (using {rough_name}): {rough_origin_x}, {rough_origin_y}")

# Step 2: Precise calibration
# Find the mapItem closest to the foxlogi town
gx, gy = foxlogi_dict[rough_name]
closest_item = None
min_dist = 999999

for item in data.get('mapItems', []):
    lx, ly = item.get('x', 0), item.get('y', 0)
    # Convert local to rough global
    rough_gx = rough_origin_x + (lx * SCALE_X)
    rough_gy = rough_origin_y + (ly * SCALE_Y)
    
    dist = math.hypot(rough_gx - gx, rough_gy - gy)
    if dist < min_dist:
        min_dist = dist
        closest_item = item

if closest_item:
    print(f"Closest Icon Distance: {min_dist} pixels")
    exact_origin_x = gx - (closest_item['x'] * SCALE_X)
    exact_origin_y = gy - (closest_item['y'] * SCALE_Y)
    print(f"Exact Origin for {m}: {exact_origin_x}, {exact_origin_y}")
    print(f"Offset difference: {exact_origin_x - rough_origin_x}, {exact_origin_y - rough_origin_y}")
