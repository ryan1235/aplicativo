from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from typing import Any, Callable


GITHUB_API = "https://api.github.com/repos/{repo}/releases/latest"
GITHUB_TAG_API = "https://api.github.com/repos/{repo}/releases/tags/{tag}"
APP_EXE_NAME = "GG Coalition.exe"
UPDATER_EXE_NAME = "GG Updater.exe"
MIN_UPDATE_ZIP_SIZE = 1024 * 1024
APP_UPDATE_FALLBACK_PT = {
    "update.error_download_failed": "Download da atualizacao falhou: HTTP {status}",
    "update.error_no_trusted_updater": "Nao encontrei um atualizador local confiavel. Se o antivirus bloqueou {updater}, permita o app no Windows Defender ou instale a nova versao manualmente pelo ZIP da release.",
    "update.error_updater_not_found": "Updater nao encontrado: {path}",
    "update.error_zip_not_found": "Arquivo de update nao encontrado: {path}",
    "update.error_zip_too_small": "Arquivo de update muito pequeno ({size} bytes). Provavelmente a release baixou um asset errado ou incompleto.",
    "update.error_zip_invalid": "O arquivo baixado nao e um ZIP valido: {path}",
    "update.error_zip_incomplete": "ZIP de update incompleto. Faltando: {missing}. Envie o arquivo release\\GG-Coalition.zip gerado pelo build.",
}


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
        asset
        for asset in assets
        if str(asset.get("name") or "").lower().endswith(".zip") and asset.get("browser_download_url")
    ]
    if not zip_assets:
        return None
    asset = next(
        (
            item
            for item in zip_assets
            if "gg-coalition" in str(item.get("name") or "").lower()
        ),
        None,
    )
    if asset is None:
        return None
    return UpdateInfo(
        version=tag,
        name=str(release.get("name") or tag),
        body=str(release.get("body") or ""),
        asset_name=str(asset.get("name") or "update.zip"),
        asset_url=str(asset.get("browser_download_url")),
    )


def fetch_release_description(repo: str, version: str, timeout: int = 8) -> str:
    if not repo or "/" not in repo:
        return ""
    tags = [version]
    if not version.lower().startswith("v"):
        tags.insert(0, f"v{version}")
    for tag in tags:
        request = urllib.request.Request(
            GITHUB_TAG_API.format(repo=repo, tag=urllib.parse.quote(tag, safe="")),
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "GG-Coalition-Updater",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                release = json.loads(response.read().decode("utf-8"))
        except Exception:
            continue
        body = str(release.get("body") or "").strip()
        if body:
            return body
    return ""


def _t(translator: Any | None, key: str, **kwargs: Any) -> str:
    if translator is not None and hasattr(translator, "t"):
        return translator.t(key, **kwargs)
    value = APP_UPDATE_FALLBACK_PT.get(key, key)
    if kwargs:
        try:
            return value.format(**kwargs)
        except Exception:
            return value
    return value


def download_update(
    update: UpdateInfo,
    timeout: int = 60,
    progress_callback: Callable[[int, int], None] | None = None,
    translator: Any | None = None,
) -> Path:
    target_dir = Path(tempfile.mkdtemp(prefix="gg_coalition_download_"))
    target = target_dir / safe_asset_name(update.asset_name)
    request = urllib.request.Request(update.asset_url, headers={"User-Agent": "GG-Coalition-Updater"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        if status >= 400:
            raise RuntimeError(_t(translator, "update.error_download_failed", status=status))
        total = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        with target.open("wb") as output:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total)

    validate_update_zip(target, require_updater=True, translator=translator)
    return target


def launch_updater(zip_path: Path, app_dir: Path, launch_target: Path, *, language: str | None = None, translator: Any | None = None) -> None:
    validate_update_zip(zip_path, require_updater=True, translator=translator)
    temp_update_dir = extract_update_package(zip_path, translator=translator)
    updater_exe = temp_update_dir / UPDATER_EXE_NAME
    updater_py = Path(__file__).resolve().with_name("updater.py")
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
    elif updater_py.exists():
        command = [sys.executable, str(updater_py), *args]
    else:
        command = []
    if not command:
        raise RuntimeError(
            _t(translator, "update.error_no_trusted_updater", updater=UPDATER_EXE_NAME)
        )
    executable = Path(command[0])
    if not executable.exists():
        raise RuntimeError(_t(translator, "update.error_updater_not_found", path=executable))
    env = os.environ.copy()
    if language:
        env["GG_COALITION_LANGUAGE"] = language
    subprocess.Popen(command, cwd=str(executable.parent), close_fds=True, env=env)


def extract_update_package(zip_path: Path, *, translator: Any | None = None) -> Path:
    target = Path(tempfile.mkdtemp(prefix="gg_coalition_update_runner_"))
    with zipfile.ZipFile(zip_path, "r") as archive:
        safe_extractall(archive, target, translator=translator)
    entries = [item for item in target.iterdir()]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return target


def validate_update_zip(zip_path: Path, *, require_updater: bool = True, translator: Any | None = None) -> None:
    if not zip_path.exists():
        raise RuntimeError(_t(translator, "update.error_zip_not_found", path=zip_path))
    if zip_path.stat().st_size < MIN_UPDATE_ZIP_SIZE:
        raise RuntimeError(
            _t(translator, "update.error_zip_too_small", size=zip_path.stat().st_size)
        )
    if not zipfile.is_zipfile(zip_path):
        raise RuntimeError(_t(translator, "update.error_zip_invalid", path=zip_path))
    with zipfile.ZipFile(zip_path, "r") as archive:
        validate_zip_member_paths(archive, translator=translator)
        names = {Path(name).name.lower() for name in archive.namelist()}
    required = [APP_EXE_NAME]
    if require_updater:
        required.append(UPDATER_EXE_NAME)
    missing = [name for name in required if name.lower() not in names]
    if missing:
        raise RuntimeError(
            _t(translator, "update.error_zip_incomplete", missing=", ".join(missing))
        )


def validate_zip_member_paths(archive: zipfile.ZipFile, *, translator: Any | None = None) -> None:
    for member in archive.infolist():
        normalized = member.filename.replace("\\", "/")
        path = PurePosixPath(normalized)
        if not normalized or path.is_absolute() or ".." in path.parts:
            raise RuntimeError(_t(translator, "update.error_zip_invalid", path=member.filename))


def safe_extractall(archive: zipfile.ZipFile, target: Path, *, translator: Any | None = None) -> None:
    validate_zip_member_paths(archive, translator=translator)
    target.mkdir(parents=True, exist_ok=True)
    target_root = target.resolve()
    for member in archive.infolist():
        destination = (target / member.filename).resolve()
        try:
            destination.relative_to(target_root)
        except ValueError as exc:
            raise RuntimeError(_t(translator, "update.error_zip_invalid", path=member.filename)) from exc
        archive.extract(member, target)


def safe_asset_name(name: str) -> str:
    cleaned = Path(name or "GG-Coalition.zip").name
    return cleaned if cleaned.lower().endswith(".zip") else "GG-Coalition.zip"


def os_getpid() -> int:
    import os

    return os.getpid()
