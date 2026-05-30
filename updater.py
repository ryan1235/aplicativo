from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile


SKIP_NAMES = {"felb_settings.json", "__pycache__"}


def wait_for_process(pid: int, timeout: float = 20.0) -> None:
    if pid <= 0:
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.25)


def copy_tree(source: Path, target: Path) -> None:
    for item in source.iterdir():
        if item.name in SKIP_NAMES:
            continue
        destination = target / item.name
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            copy_tree(item, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)


def extract_zip(zip_path: Path) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="gg_coalition_update_"))
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(temp_dir)

    entries = [item for item in temp_dir.iterdir()]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return temp_dir


def launch_app(launch: Path, target: Path) -> None:
    if launch.suffix.lower() == ".py":
        subprocess.Popen([sys.executable, str(launch)], cwd=str(target), close_fds=True)
    else:
        subprocess.Popen([str(launch)], cwd=str(target), close_fds=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--launch", required=True)
    parser.add_argument("--pid", type=int, default=0)
    args = parser.parse_args()

    zip_path = Path(args.zip)
    target = Path(args.target)
    launch = Path(args.launch)

    wait_for_process(args.pid)
    source = extract_zip(zip_path)
    copy_tree(source, target)
    launch_app(launch, target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
