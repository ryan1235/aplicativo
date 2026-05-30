from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request


GITHUB_API = "https://api.github.com/repos/{repo}/releases/latest"


@dataclass
class UpdateInfo:
    version: str
    name: str
    body: str
    asset_name: str
    asset_url: str


def normalize_version(value: str) -> tuple[int, ...]:
    cleaned = value.strip().lower().removeprefix("v")
    parts = []
    for part in cleaned.split("."):
        number = ""
        for char in part:
            if char.isdigit():
                number += char
            else:
                break
        parts.append(int(number or "0"))
    return tuple(parts or [0])


def is_newer_version(latest: str, current: str) -> bool:
    latest_parts = normalize_version(latest)
    current_parts = normalize_version(current)
    length = max(len(latest_parts), len(current_parts))
    latest_parts = latest_parts + (0,) * (length - len(latest_parts))
    current_parts = current_parts + (0,) * (length - len(current_parts))
    return latest_parts > current_parts


def check_latest_release(repo: str, current_version: str, timeout: int = 8) -> UpdateInfo | None:
    if not repo or "/" not in repo:
        return None
    request = urllib.request.Request(
        GITHUB_API.format(repo=repo),
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "GG-Coalition-Updater",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        release = json.loads(response.read().decode("utf-8"))

    tag = str(release.get("tag_name") or "")
    if not tag or not is_newer_version(tag, current_version):
        return None

    assets = release.get("assets") or []
    zip_assets = [
        asset for asset in assets
        if str(asset.get("name") or "").lower().endswith(".zip") and asset.get("browser_download_url")
    ]
    if not zip_assets:
        return None
    asset = zip_assets[0]
    return UpdateInfo(
        version=tag,
        name=str(release.get("name") or tag),
        body=str(release.get("body") or ""),
        asset_name=str(asset.get("name") or "update.zip"),
        asset_url=str(asset.get("browser_download_url")),
    )


def download_update(update: UpdateInfo, timeout: int = 60) -> Path:
    target = Path(tempfile.gettempdir()) / update.asset_name
    request = urllib.request.Request(update.asset_url, headers={"User-Agent": "GG-Coalition-Updater"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        target.write_bytes(response.read())
    return target


def launch_updater(zip_path: Path, app_dir: Path, launch_target: Path) -> None:
    updater_exe = app_dir / "GG Updater.exe"
    updater_py = app_dir / "updater.py"
    args = [
        "--zip",
        str(zip_path),
        "--target",
        str(app_dir),
        "--launch",
        str(launch_target),
        "--pid",
        str(os_getpid()),
    ]
    if updater_exe.exists():
        command = [str(updater_exe), *args]
    else:
        command = [sys.executable, str(updater_py), *args]
    subprocess.Popen(command, cwd=str(app_dir), close_fds=True)


def os_getpid() -> int:
    import os

    return os.getpid()
