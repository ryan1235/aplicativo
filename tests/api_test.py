import urllib.request
import json

maps_req = urllib.request.urlopen('https://war-service-live.foxholeservices.com/api/worldconquest/maps')
maps = json.loads(maps_req.read().decode())
print(f"Total maps: {len(maps)}, Sample: {maps[:3]}")

static_req = urllib.request.urlopen('https://war-service-live.foxholeservices.com/api/worldconquest/maps/DeadLandsHex/static')
deadlands = json.loads(static_req.read().decode())
print(f"Keys in static: {list(deadlands.keys())}")
print(f"Sample mapTextItem: {deadlands.get('mapTextItems', [])[:2]}")
