#!/usr/bin/env python3
"""CLI para geração de tiles com ícones e nomes (usa map_tile_baker)."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from map_tile_baker import MapTileBaker  # noqa: E402


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera tiles do mapa (ícones + nomes).")
    parser.add_argument("--full", action="store_true", help="Força regeneração completa.")
    parser.add_argument("--icons-only", action="store_true", help="Gera apenas tiles com ícones.")
    parser.add_argument("--labels-only", action="store_true", help="Gera apenas overlay de nomes.")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "img" / "map-tiles", help="Diretório de cache.")
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    baker = MapTileBaker(args.cache_dir, ROOT)

    def progress(stage: str, current: int, total: int) -> None:
        if total > 0 and (current % 25 == 0 or current == total):
            log(f"  [{stage}] {current}/{total}")

    start = time.time()
    if args.labels_only:
        ok, err = baker.generate_labels(progress=progress, workers=args.workers, full=args.full)
        log(f"Labels: {ok} OK, {err} erros.")
    elif args.icons_only:
        ok, err = baker.generate_icons(progress=progress, workers=args.workers, full=args.full)
        log(f"Ícones: {ok} OK, {err} erros.")
    else:
        baker.generate_all(progress=progress, workers=args.workers, force_full=args.full)

    log(f"Concluído em {time.time() - start:.1f}s.")
    log(f"Ícones: {baker.icons_dir}")
    log(f"Nomes:  {baker.labels_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
