import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SteamProfile:
    steam_id: str | None = None
    persona_name: str | None = None
    account_name: str | None = None
    steam_path: Path | None = None
    avatar_path: Path | None = None


def find_steam_path() -> Path | None:
    try:
        import winreg

        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(root, r"Software\Valve\Steam") as key:
                    value, _ = winreg.QueryValueEx(key, "SteamPath")
                    if value:
                        path = Path(value.replace("/", "\\"))
                        if path.exists():
                            return path
            except OSError:
                continue
    except Exception:
        pass

    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Steam",
        Path(os.environ.get("PROGRAMFILES", "")) / "Steam",
        Path.home() / "AppData" / "Local" / "Steam",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def parse_loginusers_vdf(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8", errors="ignore")
    users: dict[str, dict[str, str]] = {}
    current_id: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        id_match = re.fullmatch(r'"(\d{15,20})"', line)
        kv_match = re.fullmatch(r'"([^"]+)"\s+"([^"]*)"', line)

        if id_match:
            current_id = id_match.group(1)
            users[current_id] = {}
        elif kv_match and current_id:
            users[current_id][kv_match.group(1)] = kv_match.group(2)

    return users


def find_avatar_path(steam_path: Path, steam_id: str) -> Path | None:
    avatar_cache = steam_path / "config" / "avatarcache"
    if not avatar_cache.exists():
        return None

    patterns = (
        f"{steam_id}*.png",
        f"{steam_id}*.jpg",
        f"{steam_id}*.jpeg",
        f"*{steam_id}*.png",
        f"*{steam_id}*.jpg",
        f"*{steam_id}*.jpeg",
    )
    for pattern in patterns:
        matches = sorted(avatar_cache.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
        if matches:
            return matches[0]
    return None


def get_local_steam_profile() -> SteamProfile:
    steam_path = find_steam_path()
    if not steam_path:
        return SteamProfile()

    users = parse_loginusers_vdf(steam_path / "config" / "loginusers.vdf")
    if not users:
        return SteamProfile(steam_path=steam_path)

    def user_sort(item: tuple[str, dict[str, str]]) -> tuple[int, int]:
        _, data = item
        return (int(data.get("MostRecent", "0") == "1"), int(data.get("Timestamp", "0") or 0))

    steam_id, data = max(users.items(), key=user_sort)
    return SteamProfile(
        steam_id=steam_id,
        persona_name=data.get("PersonaName"),
        account_name=data.get("AccountName"),
        steam_path=steam_path,
        avatar_path=find_avatar_path(steam_path, steam_id),
    )
