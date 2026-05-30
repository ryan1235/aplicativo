from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


APP_NAME = "GG Coalition"
UPDATER_NAME = "GG Updater"

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build_nuitka"
RELEASE_DIR = ROOT / "release"

ICON_GIF = ROOT / "img" / "ggimege.gif"
ICON_ICO = ROOT / "img" / "app_icon.ico"

LOCAL_DEPS = ROOT / "deps"

PACKAGE_PATHS = [
    LOCAL_DEPS,
    Path.home() / "AppData" / "Roaming" / "Python" / "Python314" / "site-packages",
    Path.home() / "AppData" / "Local" / "Python" / "pythoncore-3.14-64" / "Lib" / "site-packages",
]


for package_path in PACKAGE_PATHS:
    if package_path.exists():
        sys.path.insert(0, str(package_path))


DATA_DIRS = [
    ("img", "img"),
    ("translations", "translations"),
    ("Textures", "Textures"),
]

DATA_FILES = [
    ("locations.csv", "locations.csv"),
    ("update64.db", "update64.db"),
    ("requirements-python.txt", "requirements-python.txt"),
    ("README.md", "README.md"),
]


def command_env() -> dict[str, str]:
    env = os.environ.copy()

    paths = [str(path) for path in PACKAGE_PATHS if path.exists()]

    if env.get("PYTHONPATH"):
        paths.append(env["PYTHONPATH"])

    env["PYTHONPATH"] = ";".join(paths)
    return env


def run(command: list[str]) -> None:
    print(" ".join(command), flush=True)
    subprocess.check_call(command, cwd=ROOT, env=command_env())


def has_nuitka() -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "nuitka", "--version"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=command_env(),
    )
    return result.returncode == 0


def install_build_deps() -> None:
    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

    run([
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--target",
        str(LOCAL_DEPS),
        "nuitka",
        "ordered-set",
        "zstandard",
        "customtkinter",
        "pillow",
        "pystray",
    ])


def clean() -> None:
    for path in (DIST_DIR, BUILD_DIR, RELEASE_DIR):
        if path.exists():
            shutil.rmtree(path)

    for pattern in ("*.build", "*.dist", "*.onefile-build"):
        for path in ROOT.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)


def ensure_icon() -> Path | None:
    if ICON_ICO.exists():
        return ICON_ICO

    if not ICON_GIF.exists():
        return None

    try:
        from PIL import Image

        image = Image.open(ICON_GIF).convert("RGBA")
        image.save(
            ICON_ICO,
            format="ICO",
            sizes=[
                (256, 256),
                (128, 128),
                (64, 64),
                (32, 32),
                (16, 16),
            ],
        )

        return ICON_ICO

    except Exception as exc:
        print(f"Nao foi possivel gerar icone .ico: {exc}", flush=True)
        return None


def nuitka_data_args() -> list[str]:
    args: list[str] = []

    for source, target in DATA_DIRS:
        source_path = ROOT / source
        if source_path.exists():
            args.append(f"--include-data-dir={source_path}={target}")

    for source, target in DATA_FILES:
        source_path = ROOT / source
        if source_path.exists():
            args.append(f"--include-data-file={source_path}={target}")

    return args


def build_app() -> Path:
    icon_path = ensure_icon()
    output = DIST_DIR / f"{APP_NAME}.exe"

    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        "--assume-yes-for-downloads",
        "--windows-console-mode=disable",
        "--enable-plugin=tk-inter",
        "--include-package=customtkinter",
        "--include-package=pystray",
        "--include-package=PIL",
        "--include-module=PIL.Image",
        "--include-module=PIL.ImageTk",
        f"--output-dir={DIST_DIR}",
        f"--output-filename={output.name}",
        *( [f"--windows-icon-from-ico={icon_path}"] if icon_path else [] ),
        *nuitka_data_args(),
        str(ROOT / "felb_app.py"),
    ]

    run(command)
    return output


def build_updater() -> Path:
    output = DIST_DIR / f"{UPDATER_NAME}.exe"

    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        "--assume-yes-for-downloads",
        "--windows-console-mode=disable",
        f"--output-dir={DIST_DIR}",
        f"--output-filename={output.name}",
        str(ROOT / "updater.py"),
    ]

    run(command)
    return output


def make_zip(files: list[Path]) -> Path:
    RELEASE_DIR.mkdir(exist_ok=True)

    zip_path = RELEASE_DIR / f"{APP_NAME.replace(' ', '-')}.zip"

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, file.name)

    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GG Coalition with Nuitka.")

    parser.add_argument(
        "--install",
        action="store_true",
        help="Install/upgrade Nuitka and runtime dependencies first.",
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove old build output before building.",
    )

    parser.add_argument(
        "--zip",
        action="store_true",
        help="Create release zip after building.",
    )

    parser.add_argument(
        "--skip-updater",
        action="store_true",
        help="Build only the main app executable.",
    )

    args = parser.parse_args()

    if args.clean:
        clean()

    if args.install:
        install_build_deps()

    if not has_nuitka():
        raise SystemExit(
            "Nuitka nao esta instalado. Rode: py build_exe.py --install --clean --zip"
        )

    outputs = [build_app()]

    if not args.skip_updater:
        outputs.append(build_updater())

    print(f"\nEXE criado em: {outputs[0]}")

    if len(outputs) > 1:
        print(f"Updater criado em: {outputs[1]}")

    if args.zip:
        zip_path = make_zip(outputs)
        print(f"ZIP para GitHub Release: {zip_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())