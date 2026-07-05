import urllib.request
import json
import math

print("Fetching foxlogi map-items...")
foxlogi_req = urllib.request.urlopen('https://foxlogi.com/api/map-items/', timeout=10)
foxlogi_data = json.loads(foxlogi_req.read().decode())
foxlogi_dict = {item['name']: (item['x'], item['y']) for item in foxlogi_data if 'name' in item}

print("Fetching official deadlands...")
deadlands_req = urllib.request.urlopen('https://war-service-live.foxholeservices.com/api/worldconquest/maps/DeadLandsHex/static', timeout=10)
deadlands_data = json.loads(deadlands_req.read().decode())

print("Matching...")
matches = []
for text_item in deadlands_data.get('mapTextItems', []):
    name = text_item['text']
    if name in foxlogi_dict:
        gx, gy = foxlogi_dict[name]
        lx, ly = text_item['x'], text_item['y']
        matches.append({'name': name, 'gx': gx, 'gy': gy, 'lx': lx, 'ly': ly})
        print(f"Match: {name} -> Global({gx}, {gy}) Local({lx}, {ly})")

if len(matches) >= 2:
    m1 = matches[0]
    m2 = matches[1]
    
    # Calculate scale
    dx_g = m2['gx'] - m1['gx']
    dx_l = m2['lx'] - m1['lx']
    scale_x = dx_g / dx_l if dx_l != 0 else 0
    
    dy_g = m2['gy'] - m1['gy']
    dy_l = m2['ly'] - m1['ly']
    scale_y = dy_g / dy_l if dy_l != 0 else 0
    
    print(f"Scale X: {scale_x}, Scale Y: {scale_y}")
    
    # Calculate offset (origin of hex where lx=0, ly=0)
    origin_x = m1['gx'] - (m1['lx'] * scale_x)
    origin_y = m1['gy'] - (m1['ly'] * scale_y)
    print(f"Origin X: {origin_x}, Origin Y: {origin_y}")
