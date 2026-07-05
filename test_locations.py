import urllib.request
import json
import csv

foxlogi_req = urllib.request.urlopen('https://foxlogi.com/api/map-items/', timeout=10)
foxlogi_data = json.loads(foxlogi_req.read().decode())
foxlogi_dict = {item['name']: (item['x'], item['y']) for item in foxlogi_data if 'name' in item}

reader = csv.DictReader(open('locations.csv', encoding='utf-8'))
matches = 0
for row in reader:
    name = row['Loc']
    if name in foxlogi_dict:
        gx, gy = foxlogi_dict[name]
        world_x, world_y = float(row['X']), float(row['Y'])
        print(f"{name}: Foxlogi({gx}, {gy})  World({world_x}, {world_y})")
        matches += 1
        if matches > 5:
            break
