import json
from pathlib import Path
from stockpiler import extract_pinned_tooltips, discover_map_data_file, simplify

save_file = discover_map_data_file()
if not save_file:
    print("No map data save file found")
    exit(1)

tooltips = extract_pinned_tooltips(save_file, strip_enum_prefixes=False)

matched_tooltips = []
for tip in tooltips:
    tip_str = json.dumps(tip, default=str)
    if "Maintenance" in tip_str or "MSupp" in tip_str or "msup" in tip_str.lower() or "tunnel" in tip_str.lower():
        matched_tooltips.append(tip)

print(f"Total tooltips: {len(tooltips)}")
print(f"Matched tooltips: {len(matched_tooltips)}")

with open("C:/Users/ryanl/OneDrive/Desktop/aplicativo/test_dump.json", "w", encoding="utf-8") as f:
    json.dump(matched_tooltips, f, indent=2, ensure_ascii=False)
