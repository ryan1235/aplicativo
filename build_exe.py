from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile


APP_NAME = "GG Coalition"
UPDATER_NAME = "GG Updater"
WEB_INSTALLER_NAME = "GG Coalition Web Setup"

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build_nuitka"
RELEASE_DIR = ROOT / "release"
RELEASE_APP_DIR = RELEASE_DIR / APP_NAME
INSTALLER_BASENAME = "GG-Coalition-Setup"
INNO_APP_ID = "{{D01A6BEF-0E3D-4C4E-93F9-BA13E5D51A64}"

ICON_GIF = ROOT / "img" / "ggimege.gif"
ICON_ICO = ROOT / "img" / "app_icon.ico"
CERTS_DIR = ROOT / "certs"
TEST_CERT_PATH = CERTS_DIR / "GG-Coalition-Test-Code-Signing.cer"
TEST_CERT_SUBJECT = "CN=GG Coalition Test Code Signing"

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
    ("audio", "audio"),
    ("efeitos sonoros", "efeitos sonoros"),
    ("translations", "translations"),
    ("Content", "Content"),
    ("qml", "qml"),
    ("admin", "admin"),
]

DATA_FILES = [
    ("locations.csv", "locations.csv"),
    ("slang_terms.json", "slang_terms.json"),
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


def quote_inno(value: str | Path) -> str:
    return str(value).replace('"', '""')


def app_version() -> str:
    for source in ("app_metadata.py", "qt_controllers.py", "felb_app.py"):
        text = (ROOT / source).read_text(encoding="utf-8-sig")
        match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
        if match:
            return match.group(1)
    return "1.0.0"


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
        "PySide6",
        "pillow",
        "numpy",
        "opencv-python",
    ])


def clean() -> None:
    for path in (DIST_DIR, BUILD_DIR, RELEASE_DIR):
        if path.exists():
            remove_tree(path)

    for pattern in ("*.build", "*.dist", "*.onefile-build"):
        for path in ROOT.glob(pattern):
            if path.is_dir():
                remove_tree(path)


def remove_tree(path: Path) -> None:
    for attempt in range(3):
        try:
            shutil.rmtree(path)
            if not path.exists():
                return
        except PermissionError as exc:
            if attempt < 2:
                time.sleep(0.6)
                continue
            raise SystemExit(
                f"Nao consegui limpar {path}.\n"
                "Feche o GG Coalition, feche o GG Updater e confira se eles nao estao na bandeja do Windows.\n"
                f"Detalhe: {exc}"
            ) from exc
        if attempt < 2:
            time.sleep(0.6)
            continue
        raise SystemExit(
            f"Nao consegui limpar {path}.\n"
            "Apague essa pasta gerada ou feche qualquer build ainda rodando antes de tentar novamente."
        )


def ensure_icon() -> Path | None:
    if not ICON_GIF.exists():
        return ICON_ICO if ICON_ICO.exists() else None

    if ICON_ICO.exists() and ICON_ICO.stat().st_mtime >= ICON_GIF.stat().st_mtime:
        return ICON_ICO

    try:
        from PIL import Image

        image = Image.open(ICON_GIF).convert("RGBA")
        bbox = image.getbbox()
        if bbox:
            image = image.crop(bbox)
        image.thumbnail((256, 256), Image.LANCZOS)
        canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        canvas.alpha_composite(image, ((256 - image.width) // 2, (256 - image.height) // 2))
        canvas.save(
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


def standalone_output_dir(script_name: str) -> Path:
    return DIST_DIR / f"{Path(script_name).stem}.dist"


def standalone_build_dir(script_name: str) -> Path:
    return DIST_DIR / f"{Path(script_name).stem}.build"


def standalone_onefile_build_dir(script_name: str) -> Path:
    return DIST_DIR / f"{Path(script_name).stem}.onefile-build"


def clean_nuitka_target(script_name: str) -> None:
    for path in (
        standalone_build_dir(script_name),
        standalone_output_dir(script_name),
        standalone_onefile_build_dir(script_name),
    ):
        if path.exists():
            remove_tree(path)


def standalone_exe_path(script_name: str, output_name: str) -> Path:
    return standalone_output_dir(script_name) / output_name


def onefile_exe_path(output_name: str) -> Path:
    return DIST_DIR / output_name


def build_app() -> Path:
    clean_nuitka_target("felb_app.py")
    icon_path = ensure_icon()
    output = standalone_exe_path("felb_app.py", f"{APP_NAME}.exe")

    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--windows-console-mode=disable",
        f"--file-version={app_version()}",
        f"--product-version={app_version()}",
        f"--product-name={APP_NAME}",
        f"--file-description={APP_NAME} - Aplicativo",
        "--copyright=GG Coalition",
        "--include-package=PySide6",
        "--include-package=pygvas",
        "--include-package=pydantic",
        "--include-package=pydantic_core",
        "--include-package=typing_extensions",
        "--include-package=PIL",
        "--include-package=numpy",
        "--include-package=cv2",
        "--enable-plugin=pyside6",
        "--include-qt-plugins=qml",
        f"--output-dir={DIST_DIR}",
        f"--output-filename={output.name}",
        *( [f"--windows-icon-from-ico={icon_path}"] if icon_path else [] ),
        *nuitka_data_args(),
        str(ROOT / "felb_app.py"),
    ]

    run(command)
    if not output.exists():
        raise SystemExit(f"Build finalizou, mas o executavel nao foi encontrado em: {output}")
    return output


def build_updater() -> Path:
    clean_nuitka_target("updater.py")
    icon_path = ensure_icon()
    output = standalone_exe_path("updater.py", f"{UPDATER_NAME}.exe")

    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--windows-console-mode=disable",
        f"--file-version={app_version()}",
        f"--product-version={app_version()}",
        f"--product-name={UPDATER_NAME}",
        f"--file-description={UPDATER_NAME} - Atualizador",
        "--copyright=GG Coalition",
        *( [f"--windows-icon-from-ico={icon_path}"] if icon_path else [] ),
        "--enable-plugin=pyside6",
        "--include-qt-plugins=qml",
        f"--output-dir={DIST_DIR}",
        f"--output-filename={output.name}",
        str(ROOT / "updater.py"),
    ]

    run(command)
    if not output.exists():
        raise SystemExit(f"Build do updater finalizou, mas o executavel nao foi encontrado em: {output}")
    return output


def build_web_installer() -> Path:
    clean_nuitka_target("web_installer.py")
    icon_path = ensure_icon()
    gif_path = ICON_GIF if ICON_GIF.exists() else None
    RELEASE_DIR.mkdir(exist_ok=True)
    output = RELEASE_DIR / f"{WEB_INSTALLER_NAME}.exe"
    work_dir = BUILD_DIR / "pyinstaller-web"
    stale_release_dir = RELEASE_DIR / WEB_INSTALLER_NAME
    if stale_release_dir.exists():
        remove_tree(stale_release_dir)
    stale_zip = RELEASE_DIR / "GG-Coalition-Web-Setup-Standalone.zip"
    if stale_zip.exists():
        stale_zip.unlink()
    if output.exists():
        output.unlink()

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconsole",
        "--noconfirm",
        "--clean",
        "--name",
        WEB_INSTALLER_NAME,
        *( [f"--icon={icon_path}"] if icon_path else [] ),
        *( [f"--add-data={icon_path};img"] if icon_path else [] ),
        *( [f"--add-data={gif_path};img"] if gif_path else [] ),
        "--distpath",
        str(RELEASE_DIR),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(work_dir),
        str(ROOT / "web_installer.py"),
    ]

    run(command)
    if not output.exists():
        raise SystemExit(f"Build do instalador online finalizou, mas o executavel nao foi encontrado em: {output}")

    dist_dir = DIST_DIR / WEB_INSTALLER_NAME
    if dist_dir.exists():
        remove_tree(dist_dir)
    DIST_DIR.mkdir(exist_ok=True)
    dist_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output, dist_dir / output.name)
    return output


def merge_updater_into_app_dist(updater_exe: Path) -> None:
    app_dist = standalone_output_dir("felb_app.py")
    updater_dist = standalone_output_dir("updater.py")
    if not app_dist.exists() or not updater_dist.exists():
        return
    for source in updater_dist.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(updater_dist)
        destination = app_dist / relative
        if destination.exists() and destination.name.lower() != f"{UPDATER_NAME}.exe".lower():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    if not (app_dist / updater_exe.name).exists():
        shutil.copy2(updater_exe, app_dist / updater_exe.name)


def prepare_release_folder(app_dist: Path) -> Path:
    if not app_dist.exists():
        raise SystemExit(f"Pasta standalone nao encontrada: {app_dist}")
    required = [app_dist / f"{APP_NAME}.exe"]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise SystemExit("Pasta standalone incompleta. Faltando: " + ", ".join(str(path) for path in missing))
    RELEASE_DIR.mkdir(exist_ok=True)
    if RELEASE_APP_DIR.exists():
        remove_tree(RELEASE_APP_DIR)
    shutil.copytree(app_dist, RELEASE_APP_DIR)
    return RELEASE_APP_DIR


def make_zip(package_dir: Path) -> Path:
    RELEASE_DIR.mkdir(exist_ok=True)
    required = [package_dir / f"{APP_NAME}.exe", package_dir / f"{UPDATER_NAME}.exe"]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise SystemExit("Nao vou criar ZIP de update incompleto. Faltando: " + ", ".join(str(path) for path in missing))
    files = [file for file in package_dir.rglob("*") if file.is_file()]
    if not files:
        raise SystemExit(f"Nao vou criar ZIP vazio. Pasta sem arquivos: {package_dir}")

    zip_path = RELEASE_DIR / f"{APP_NAME.replace(' ', '-')}.zip"

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, file.relative_to(package_dir))

    return zip_path


def sign_release_folder(package_dir: Path, cert_subject: str, timestamp_url: str, no_timestamp: bool) -> None:
    script = ROOT / "tools" / "sign_release.ps1"
    if not script.exists():
        raise SystemExit(f"Script de assinatura nao encontrado: {script}")

    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-PackageDir",
        str(package_dir),
        "-CertSubject",
        cert_subject,
    ]
    if no_timestamp:
        command.append("-NoTimestamp")
    else:
        command.extend(["-TimestampServer", timestamp_url])
    command.append("-Verify")
    run(command)


def ensure_test_certificate(trust_current_user: bool) -> None:
    script = ROOT / "tools" / "create_test_codesign_cert.ps1"
    if not script.exists():
        raise SystemExit(f"Script de certificado nao encontrado: {script}")
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]
    if trust_current_user:
        command.append("-TrustForCurrentUser")
    run(command)


def copy_public_certificate(package_dir: Path) -> None:
    if TEST_CERT_PATH.exists():
        shutil.copy2(TEST_CERT_PATH, package_dir / TEST_CERT_PATH.name)


def write_sha256_manifest(package_dir: Path) -> Path:
    import hashlib

    manifest = package_dir / "SHA256SUMS.txt"
    lines: list[str] = []
    for file in sorted(path for path in package_dir.rglob("*") if path.is_file() and path.name != manifest.name):
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        relative = file.relative_to(package_dir).as_posix()
        lines.append(f"{digest}  {relative}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def write_inno_script(package_dir: Path) -> Path:
    if not package_dir.exists():
        raise SystemExit(f"Pasta do pacote nao encontrada: {package_dir}")
    setup_path = RELEASE_DIR / f"{INSTALLER_BASENAME}.iss"
    version = app_version()
    icon_line = f'SetupIconFile={quote_inno(ICON_ICO)}\n' if ICON_ICO.exists() else ""
    script = f"""#define MyAppName "{APP_NAME}"
#define MyAppVersion "{version}"
#define MyAppPublisher "GG Coalition"
#define MyAppExeName "{APP_NAME}.exe"

[Setup]
AppId={INNO_APP_ID}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
DefaultDirName={{localappdata}}\\Programs\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
DisableProgramGroupPage=yes
OutputDir={quote_inno(RELEASE_DIR)}
OutputBaseFilename={INSTALLER_BASENAME}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
CloseApplicationsFilter={{#MyAppExeName}};GG Updater.exe
RestartApplications=no
UninstallDisplayIcon={{app}}\\{{#MyAppExeName}}
{icon_line}
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Files]
Source: "{quote_inno(package_dir)}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent
"""
    setup_path.write_text(script, encoding="utf-8")
    return setup_path


def find_iscc() -> Path | None:
    from shutil import which

    found = which("ISCC.exe") or which("ISCC")
    if found:
        return Path(found)
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def compile_inno_installer(script_path: Path) -> Path | None:
    iscc = find_iscc()
    if not iscc:
        print(
            "\nInno Setup nao encontrado. Instale o Inno Setup 6 e compile este arquivo:\n"
            f"{script_path}\n",
            flush=True,
        )
        return None
    run([str(iscc), str(script_path)])
    installer = RELEASE_DIR / f"{INSTALLER_BASENAME}.exe"
    if not installer.exists():
        raise SystemExit(f"Compilacao do instalador finalizou, mas o arquivo nao apareceu: {installer}")
    return installer


def sign_single_file(path: Path, cert_subject: str, timestamp_url: str, no_timestamp: bool) -> None:
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
    ]
    timestamp = "" if no_timestamp else f" -TimestampServer '{timestamp_url}'"
    ps = (
        "$cert=Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | "
        f"Where-Object {{$_.Subject -eq '{cert_subject}' -and $_.HasPrivateKey}} | "
        "Sort-Object NotAfter -Descending | Select-Object -First 1; "
        "if(-not $cert){ throw 'Code signing certificate not found' }; "
        f"$r=Set-AuthenticodeSignature -FilePath '{path}' -Certificate $cert -HashAlgorithm SHA256{timestamp}; "
        "Write-Host $r.Status"
    )
    run([*command, ps])


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

    parser.add_argument(
        "--sign",
        action="store_true",
        help="Sign release .exe files with a code signing certificate from CurrentUser\\My.",
    )

    parser.add_argument(
        "--test-cert",
        action="store_true",
        help="Create/reuse the local self-signed test certificate and sign with it.",
    )

    parser.add_argument(
        "--trust-test-cert",
        action="store_true",
        help="Trust the local self-signed test certificate for the current Windows user.",
    )

    parser.add_argument(
        "--cert-subject",
        default=TEST_CERT_SUBJECT,
        help="Certificate subject used by --sign.",
    )

    parser.add_argument(
        "--timestamp-url",
        default="http://timestamp.digicert.com",
        help="Timestamp server used by --sign.",
    )

    parser.add_argument(
        "--no-timestamp",
        action="store_true",
        help="Sign without a timestamp server.",
    )

    parser.add_argument(
        "--installer",
        action="store_true",
        help="Generate an Inno Setup installer that installs or updates the app.",
    )

    parser.add_argument(
        "--web-installer",
        action="store_true",
        help="Build only the online bootstrap installer that downloads the latest GitHub release.",
    )

    args = parser.parse_args()

    if args.clean:
        clean()

    if args.install:
        install_build_deps()

    if args.test_cert:
        ensure_test_certificate(args.trust_test_cert)
        args.sign = True
        args.cert_subject = TEST_CERT_SUBJECT

    if not has_nuitka():
        raise SystemExit(
            "Nuitka nao esta instalado. Rode: py build_exe.py --install --clean --zip"
        )

    if args.web_installer:
        installer = build_web_installer()
        if args.sign:
            sign_single_file(installer, args.cert_subject, args.timestamp_url, args.no_timestamp)
        print(f"\nInstalador online criado em: {installer}")
        return 0

    outputs = [build_app()]

    if not args.skip_updater:
        updater_output = build_updater()
        merge_updater_into_app_dist(updater_output)
        outputs.append(updater_output)

    package_dir = prepare_release_folder(standalone_output_dir("felb_app.py"))

    if args.sign:
        sign_release_folder(package_dir, args.cert_subject, args.timestamp_url, args.no_timestamp)
        if args.cert_subject == TEST_CERT_SUBJECT:
            copy_public_certificate(package_dir)

    manifest = write_sha256_manifest(package_dir)
    installer_path: Path | None = None
    inno_script_path: Path | None = None

    if args.installer:
        inno_script_path = write_inno_script(package_dir)
        installer_path = compile_inno_installer(inno_script_path)
        if installer_path and args.sign:
            sign_single_file(installer_path, args.cert_subject, args.timestamp_url, args.no_timestamp)

    print(f"\nEXE criado em: {outputs[0]}")
    print(f"Pasta pronta para distribuir/testar: {package_dir}")
    print(f"Manifesto SHA256 criado em: {manifest}")
    if inno_script_path:
        print(f"Script do instalador criado em: {inno_script_path}")
    if installer_path:
        print(f"Instalador criado em: {installer_path}")

    if len(outputs) > 1:
        print(f"Updater criado em: {outputs[1]}")

    if args.zip:
        zip_path = make_zip(package_dir)
        print(f"ZIP para GitHub Release: {zip_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
