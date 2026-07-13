#!/usr/bin/env python3
"""
Simple memory monitor — attach to any running Python process by name.
Usage: python simple_memory_monitor.py [duration_seconds] [interval_seconds]
"""
import subprocess
import time
import sys

def monitor_process(duration=120, interval=2):
    """Monitor Python process memory using tasklist."""
    print(f"[*] Monitoring Python processes for {duration} seconds...")
    print("[*] Columns: Time(s) | RSS(MB)\n")
    
    start = time.time()
    max_mem = 0
    min_mem = float('inf')
    
    try:
        while time.time() - start < duration:
            # Use tasklist to get memory info
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                capture_output=True,
                text=True
            )
            
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                # Parse: "python.exe","PID","Session","Num","Mem(K)" where Mem is in format "375.128 K"
                for line in lines[1:]:
                    parts = line.split(',')
                    if len(parts) >= 5:
                        mem_str = parts[4].strip().strip('"').replace(' K', '').replace(',', '.')
                        try:
                            mem_kb = float(mem_str)
                            mem_mb = mem_kb / 1024
                        except ValueError:
                            continue
                        
                        elapsed = int(time.time() - start)
                        print(f"[{elapsed:3d}s] {mem_mb:7.1f} MB")
                        
                        max_mem = max(max_mem, mem_mb)
                        min_mem = min(min_mem, mem_mb)
                        break
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n[*] Stopped by user")
    
    if max_mem > 0:
        print(f"\n=== SUMMARY ===")
        print(f"Peak: {max_mem:.1f} MB")
        print(f"Min:  {min_mem:.1f} MB")
        print(f"Delta: {max_mem - min_mem:.1f} MB")

if __name__ == '__main__':
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    monitor_process(duration, interval)
