import os
import sys
from pathlib import Path

def get_save_dir():
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Foxhole" / "Saved" / "SaveGames"
    return Path.home() / "AppData" / "Local" / "Foxhole" / "Saved" / "SaveGames"

save_dir = get_save_dir()
print(f"Save dir: {save_dir}")
if save_dir.exists():
    for f in save_dir.glob("*.sav"):
        print(f)
