import urllib.request
import re

req = urllib.request.Request('https://foxlogi.com/assets/index-DoLxoVOn.js', headers={'User-Agent': 'Mozilla/5.0'})
js_code = urllib.request.urlopen(req).read().decode('utf-8')

# Search for transformation functions or scale constants
matches = re.finditer(r'([A-Za-z0-9_]+)\s*[:=]\s*function\([^)]*\)\s*\{[^}]*x[*\-+][^}]*y[*\-+][^}]*\}', js_code)
found = False
for m in matches:
    print("Found potential function:", m.group(0)[:200])
    found = True

# Search for explicit Foxhole Hex scale values, usually involving 256 or L.CRS
crs_matches = re.findall(r'L\.CRS[^\;\}]+', js_code)
for m in crs_matches:
    print("CRS Match:", m[:200])

if not found:
    print("No simple matches. Printing any string with 'scale' and 'transform'")
    for line in js_code.split(';'):
        if 'scale' in line.lower() and 'x' in line.lower() and 'y' in line.lower():
            if len(line) < 300:
                print("Line:", line)
