import urllib.request
import json

req = urllib.request.Request(
    'https://felblogi.discloud.app/data',
    data=b'{"mode": "debug"}',
    headers={'Content-Type': 'application/json', 'X-API-Key': 'AIza7m3-iCHSlTbLDavZkAM-6Gv0zRClL30XbRS'},
    method='GET'
)
try:
    with urllib.request.urlopen(req) as res:
        print(res.read().decode())
except Exception as e:
    print(e)
