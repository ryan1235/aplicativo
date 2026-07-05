import os
import urllib.request
import urllib.error
import concurrent.futures
import threading

BASE_URL = "https://foxlogi.com/map-tiles/patch-64/{z}/{x}/{y}.webp"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "map-tiles", "patch-64")

MAX_ZOOM = 7 # Download up to zoom 7
MAX_WORKERS = 10

downloaded_count = 0
error_count = 0
lock = threading.Lock()

def download_tile(z, x, y):
    global downloaded_count, error_count
    
    url = BASE_URL.format(z=z, x=x, y=y)
    
    # Create the directory structure for this tile
    tile_dir = os.path.join(OUTPUT_DIR, str(z), str(x))
    os.makedirs(tile_dir, exist_ok=True)
    
    file_path = os.path.join(tile_dir, f"{y}.webp")
    
    # Skip if already downloaded
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return
        
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            with open(file_path, 'wb') as f:
                f.write(response.read())
                
        with lock:
            downloaded_count += 1
            if downloaded_count % 50 == 0:
                print(f"[{z}/{x}/{y}] Downloaded {downloaded_count} new tiles...")
                
    except urllib.error.HTTPError as e:
        if e.code != 404:
            with lock:
                error_count += 1
    except Exception as e:
        with lock:
            error_count += 1

def main():
    print(f"Starting map tiles download to {OUTPUT_DIR}")
    print("This might take a while depending on the max zoom level.")
    
    tasks = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for z in range(MAX_ZOOM + 1):
            max_coord = 2 ** z
            for x in range(max_coord):
                for y in range(max_coord):
                    tasks.append(executor.submit(download_tile, z, x, y))
                    
        # Wait for all tasks to complete
        concurrent.futures.wait(tasks)
        
    print(f"Download complete! Downloaded {downloaded_count} new tiles. Errors/404s ignored: {error_count}")

if __name__ == "__main__":
    main()
