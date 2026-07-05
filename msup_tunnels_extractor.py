import json
import threading
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app_paths import extracted_dir
from stockpiler import extract_pinned_tooltips, discover_map_data_file

MSUP_TUNNELS_FILE = extracted_dir() / "msup_tunnels.json"

def _debug_log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [MSuppTunnels] {msg}", flush=True)

def extract_msup_tunnels(path: Path) -> list[dict[str, Any]]:
    try:
        data = extract_pinned_tooltips(path, strip_enum_prefixes=True)
    except Exception as exc:
        _debug_log(f"Error extracting tooltips: {exc}")
        return []

    tunnels = []
    for tip in data:
        if not isinstance(tip, dict):
            continue
        if tip.get("CodeName") == "MaintenanceTunnel":
            map_id = tip.get("MapId", "Unknown")
            coords = tip.get("NormalizedMapCoords") or {}
            x = coords.get("x", 0.0)
            y = coords.get("y", 0.0)
            last_updated = tip.get("LastUpdated", "")

            msupp_count = 0
            recent_details = tip.get("RecentMapItemDetails") or {}
            stockpile_info = recent_details.get("StockpileInfo") or {}
            items = stockpile_info.get("Items") or []
            for item in items:
                if isinstance(item, dict) and item.get("CodeName") == "MaintenanceSupplies":
                    msupp_count = item.get("Quantity", 0)
                    break
            
            tunnels.append({
                "map_id": map_id,
                "x": x,
                "y": y,
                "msupps": msupp_count,
                "last_updated": last_updated
            })
    return tunnels

def extract_and_save(path: Path, callback: Callable[[list[dict[str, Any]]], None] | None = None) -> bool:
    _debug_log(f"Extracting msup tunnels from {path.name}")
    tunnels = extract_msup_tunnels(path)
    
    tunnels_json = json.dumps(tunnels, sort_keys=True)
    current_hash = hashlib.sha256(tunnels_json.encode('utf-8')).hexdigest()
    
    try:
        if MSUP_TUNNELS_FILE.exists():
            with open(MSUP_TUNNELS_FILE, "r", encoding="utf-8") as f:
                old_tunnels = json.load(f)
            old_hash = hashlib.sha256(json.dumps(old_tunnels, sort_keys=True).encode('utf-8')).hexdigest()
            if old_hash == current_hash:
                _debug_log("Tunnels unchanged.")
                # We can still trigger callback if needed, but usually we skip if unchanged
                return False
    except Exception:
        pass

    try:
        MSUP_TUNNELS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MSUP_TUNNELS_FILE, "w", encoding="utf-8") as f:
            json.dump(tunnels, f, indent=2, ensure_ascii=False)
        _debug_log(f"Saved {len(tunnels)} tunnels to {MSUP_TUNNELS_FILE.name}")
        if callback:
            callback(tunnels)
        return True
    except Exception as exc:
        _debug_log(f"Failed to save {MSUP_TUNNELS_FILE.name}: {exc}")
        return False

class MsupTunnelsWatcher:
    def __init__(
        self,
        interval: float = 0.5,
        discovery_interval: float = 5.0,
        status_callback: Callable[[str], None] | None = None,
        tunnels_callback: Callable[[list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self.interval = interval
        self.discovery_interval = max(interval, discovery_interval)
        self.status_callback = status_callback
        self.tunnels_callback = tunnels_callback
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self._cached_candidate_file: Path | None = None
        self._last_discovery_at = 0.0

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self.stop_event.set()
        thread = self.thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=max(0.0, timeout))
        if thread and not thread.is_alive():
            self.thread = None

    def _status(self, message: str) -> None:
        _debug_log(message)
        if self.status_callback:
            self.status_callback(message)

    def _run(self) -> None:
        self._status("running")
        watched_path: Path | None = None
        watched_stat: tuple[int, int] | None = None

        while not self.stop_event.is_set():
            now = time.monotonic()
            candidate = self._candidate_file()
            if candidate is None:
                if self.stop_event.wait(self.interval):
                    break
                continue

            try:
                resolved = candidate.resolve()
                stat = resolved.stat()
            except OSError:
                if self.stop_event.wait(self.interval):
                    break
                continue

            current_stat = (stat.st_mtime_ns, stat.st_size)
            is_new = watched_path is None or resolved != watched_path

            if is_new or current_stat != watched_stat:
                watched_path = resolved
                watched_stat = current_stat
                self._status(f"Reload detected: {resolved.name}")
                extract_and_save(resolved, self.tunnels_callback)

            if self.stop_event.wait(self.interval):
                break

    def _candidate_file(self) -> Path | None:
        now = time.monotonic()
        if self._cached_candidate_file is not None and now - self._last_discovery_at < self.discovery_interval:
            return self._cached_candidate_file
        discovered = discover_map_data_file()
        if discovered:
            self._cached_candidate_file = discovered
            self._last_discovery_at = now
            return discovered
        self._cached_candidate_file = None
        self._last_discovery_at = now
        return None

def main():
    candidate = discover_map_data_file()
    if candidate:
        extract_and_save(candidate)
    else:
        print("No Foxhole save found!")

if __name__ == "__main__":
    main()
