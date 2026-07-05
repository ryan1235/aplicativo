import urllib.request, json
try:
    map_req = urllib.request.urlopen(urllib.request.Request('https://foxlogi.com/api/map-items/', headers={'User-Agent': 'Mozilla/5.0'}))
    map_items = json.loads(map_req.read().decode())
    loc_map = {m.get('name'): (m.get('x'), m.get('y')) for m in map_items if m.get('name')}
    
    data_req = urllib.request.urlopen(urllib.request.Request(
        'https://felblogi.discloud.app/data',
        data=b'{"mode": "debug"}',
        headers={'Content-Type': 'application/json', 'X-API-Key': 'AIza7m3-iCHSlTbLDavZkAM-6Gv0zRClL30XbRS'},
        method='GET'
    ))
    data = json.loads(data_req.read().decode())
    
    unmatched = set()
    matched = set()
    for item in data.get('data', []):
        wh = item.get('warehouse', {})
        town = wh.get('town', '').strip()
        if town in loc_map:
            matched.add(town)
        else:
            unmatched.add(town)
            
    print("Matched towns:", matched)
    print("Unmatched towns:", unmatched)
except Exception as e:
    print(e)
