#!/usr/bin/env python3
"""
Baixa tiles originais do mapa Foxhole (foxlogi) e opcionalmente aplica baking
de ícones de estruturas estáticas via tools/bake_map_tiles.py.

Uso:
  python download_tiles.py              # apenas download dos tiles crus
  python download_tiles.py --bake       # download + baking completo
  python download_tiles.py --bake-only  # apenas baking (tiles crus já existentes)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_URL = "https://foxlogi.com/map-tiles/patch-64/{z}/{x}/{y}.webp"
RAW_DIR = ROOT / "img" / "map-tiles" / "raw" / "patch-64"
OUTPUT_DIR = ROOT / "img" / "map-tiles" / "patch-64"
BAKE_SCRIPT = ROOT / "tools" / "bake_map_tiles.py"

MAX_ZOOM = 7
MAX_WORKERS = 10
LOW_ZOOM_COPY_MAX = 4  # zooms sem baking: cópia direta do raw para output

downloaded_count = 0
error_count = 0
lock = threading.Lock()


def download_tile(z: int, x: int, y: int) -> None:
    global downloaded_count, error_count

    url = BASE_URL.format(z=z, x=x, y=y)
    tile_dir = RAW_DIR / str(z) / str(x)
    tile_dir.mkdir(parents=True, exist_ok=True)
    file_path = tile_dir / f"{y}.webp"

    if file_path.exists() and file_path.stat().st_size > 0:
        return

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            file_path.write_bytes(response.read())

        with lock:
            downloaded_count += 1
            if downloaded_count % 50 == 0:
                print(f"[{z}/{x}/{y}] Baixados {downloaded_count} tiles novos...")

    except urllib.error.HTTPError as e:
        if e.code != 404:
            with lock:
                error_count += 1
    except Exception:
        with lock:
            error_count += 1


def copy_low_zoom_tiles() -> None:
    """Copia tiles de zoom baixo (sem ícones colados) para o diretório de saída."""
    copied = 0
    for z in range(LOW_ZOOM_COPY_MAX + 1):
        src_z = RAW_DIR / str(z)
        if not src_z.exists():
            continue
        for x_dir in src_z.iterdir():
            if not x_dir.is_dir():
                continue
            for tile_file in x_dir.iterdir():
                if tile_file.suffix != ".webp":
                    continue
                rel = tile_file.relative_to(RAW_DIR)
                dest = OUTPUT_DIR / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists() or dest.stat().st_size == 0:
                    shutil.copy2(tile_file, dest)
                    copied += 1
    if copied:
        print(f"Copiados {copied} tiles de zoom 0–{LOW_ZOOM_COPY_MAX} para {OUTPUT_DIR}")


def run_bake(full: bool = True) -> int:
    cmd = [sys.executable, str(BAKE_SCRIPT)]
    if full:
        cmd.append("--full")
    print(f"Executando: {' '.join(cmd)}")
    return subprocess.call(cmd)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download e baking de tiles do mapa.")
    parser.add_argument("--bake", action="store_true", help="Após download, executa baking completo.")
    parser.add_argument("--bake-only", action="store_true", help="Pula download; executa apenas baking.")
    parser.add_argument("--max-zoom", type=int, default=MAX_ZOOM, help=f"Zoom máximo (padrão: {MAX_ZOOM}).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.bake_only:
        return run_bake(full=True)

    print(f"Baixando tiles originais para {RAW_DIR}")
    print("Isso pode demorar dependendo do zoom máximo.")

    tasks = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for z in range(args.max_zoom + 1):
            max_coord = 2 ** z
            for x in range(max_coord):
                for y in range(max_coord):
                    tasks.append(executor.submit(download_tile, z, x, y))
        wait(tasks)

    print(f"Download concluído! {downloaded_count} tiles novos. Erros/404 ignorados: {error_count}")

    copy_low_zoom_tiles()

    if args.bake:
        return run_bake(full=True)

    print("Dica: execute com --bake para colar ícones de estruturas nos tiles.")
    print(f"  python {Path(__file__).name} --bake")
    print(f"  python tools/bake_map_tiles.py        # atualização incremental")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
