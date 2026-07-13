#!/usr/bin/env python3
"""
Memory profiler for FELB app — tracks RSS memory usage over time.
Run alongside the app to capture memory consumption metrics.
"""
import os
import sys
import psutil
import time
import json
from datetime import datetime

def get_app_process():
    """Find the main app process by name."""
    for proc in psutil.process_iter(['pid', 'name']):
        if 'felb_app' in proc.info['name'].lower() or 'python' in proc.info['name'].lower():
            try:
                if proc.memory_info().rss > 50_000_000:  # > 50MB likely the app
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    return None

def profile(duration_secs=120, interval_secs=2):
    """Profile memory usage."""
    print(f"[*] Searching for FELB app process...")
    time.sleep(1)
    
    proc = get_app_process()
    if not proc:
        print("[!] Could not find app process. Make sure felb_app.py is running.")
        return
    
    print(f"[+] Found process: {proc.info['name']} (PID: {proc.pid})")
    print(f"[*] Recording for {duration_secs} seconds, interval: {interval_secs}s\n")
    
    samples = []
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration_secs:
            try:
                mem_info = proc.memory_info()
                mem_mb = mem_info.rss / 1_000_000
                timestamp = datetime.now().isoformat()
                
                samples.append({
                    "time": timestamp,
                    "memory_mb": round(mem_mb, 2),
                    "vms_mb": round(mem_info.vms / 1_000_000, 2)
                })
                
                elapsed = int(time.time() - start_time)
                print(f"[{elapsed:3d}s] Memory: {mem_mb:7.1f} MB | VMS: {mem_info.vms/1_000_000:7.1f} MB")
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                print("[!] Process died or access denied.")
                break
            
            time.sleep(interval_secs)
    
    except KeyboardInterrupt:
        print("\n[*] Interrupted by user.")
    
    # Analysis
    if samples:
        mems = [s['memory_mb'] for s in samples]
        print(f"\n=== SUMMARY ===")
        print(f"Peak Memory: {max(mems):.1f} MB")
        print(f"Min Memory: {min(mems):.1f} MB")
        print(f"Average Memory: {sum(mems)/len(mems):.1f} MB")
        print(f"Samples: {len(samples)}")
        
        # Save to JSON
        filename = f"memory_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(samples, f, indent=2)
        print(f"[+] Saved to {filename}")

if __name__ == '__main__':
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    profile(duration_secs=duration)
