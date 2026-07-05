import urllib.request
import json
import csv

foxlogi_req = urllib.request.urlopen('https://foxlogi.com/api/map-items/', timeout=10)
foxlogi_data = json.loads(foxlogi_req.read().decode())
foxlogi_dict = {item['name']: (item['x'], item['y']) for item in foxlogi_data if 'name' in item}

reader = csv.DictReader(open('locations.csv', encoding='utf-8'))
points = []
for row in reader:
    name = row['Loc']
    if name in foxlogi_dict:
        gx, gy = foxlogi_dict[name]
        world_x, world_y = float(row['X']), float(row['Y'])
        points.append((world_x, world_y, gx, gy))

# Linear regression for X: gx = A * world_x + B
# Linear regression for Y: gy = C * world_y + D

n = len(points)
sum_wx = sum(p[0] for p in points)
sum_wy = sum(p[1] for p in points)
sum_gx = sum(p[2] for p in points)
sum_gy = sum(p[3] for p in points)

sum_wx2 = sum(p[0]**2 for p in points)
sum_wy2 = sum(p[1]**2 for p in points)
sum_wxgx = sum(p[0]*p[2] for p in points)
sum_wygy = sum(p[1]*p[3] for p in points)

A = (n * sum_wxgx - sum_wx * sum_gx) / (n * sum_wx2 - sum_wx**2)
B = (sum_gx - A * sum_wx) / n

C = (n * sum_wygy - sum_wy * sum_gy) / (n * sum_wy2 - sum_wy**2)
D = (sum_gy - C * sum_wy) / n

print(f"Foxlogi_X = {A} * World_X + {B}")
print(f"Foxlogi_Y = {C} * World_Y + {D}")

# Test the fit
max_err = 0
for wx, wy, gx, gy in points:
    calc_gx = A * wx + B
    calc_gy = C * wy + D
    err = max(abs(calc_gx - gx), abs(calc_gy - gy))
    max_err = max(max_err, err)

print(f"Max Error: {max_err} pixels")
