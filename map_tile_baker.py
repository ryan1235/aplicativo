"""Geração de tiles do mapa com ícones e nomes colados (baking) para o app desktop."""

from __future__ import annotations

import json
import math
import re
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app_paths import resource_dir

VENDOR_DIR = resource_dir() / "vendor"
if VENDOR_DIR.exists() and str(VENDOR_DIR) not in sys.path:
    # Keep the active environment's packages ahead of bundled fallbacks.  In
    # particular, Pillow needs the compiled PIL._imaging extension installed
    # in the virtual environment; the source-only vendor copy cannot provide it.
    sys.path.append(str(VENDOR_DIR))

from PIL import Image, ImageChops, ImageDraw, ImageFont  # noqa: E402

TILE_SIZE = 256
ICON_MIN_ZOOM = 5   # zoom mínimo no QML para exibir ícones
ICON_MAX_ZOOM = 7
ICON_SIZE = 24
# Só cola ícones no zoom máximo — nos demais o app usa tiles do foxlogi + QML.
ICON_BAKE_ZOOMS: tuple[int, ...] = (7,)

LABEL_HEX_MIN_ZOOM = 0
LABEL_MAJOR_MIN_ZOOM = 4
LABEL_MINOR_MIN_ZOOM = 5
LABEL_MAX_ZOOM = 7
# Nomes colados só no zoom máximo; demais níveis usam QML.
LABEL_BAKE_ZOOMS: tuple[int, ...] = (7,)

MAP_SCALE = 1.0
MAP_OFFSET_X = 0.0
MAP_OFFSET_Y = 0.0

SCALE_X = 25.553590845600255
SCALE_Y = -22.32744119202343

BASE_TILE_URL = "https://foxlogi.com/map-tiles/patch-64/{z}/{x}/{y}.webp"
MAP_ITEMS_URL = "https://foxlogi.com/api/map-items/"
MAPS_URL = "https://war-service-live.foxholeservices.com/api/worldconquest/maps"
STATIC_MAP_URL = "https://war-service-live.foxholeservices.com/api/worldconquest/maps/{map_id}/static"

USER_AGENT = "Mozilla/5.0 (GG-Coalition Map Tile Baker)"
BAKE_VERSION = 4

ProgressCallback = Callable[[str, int, int], None]
OnStageComplete = Callable[[], None]

# Centro aproximado do mapa para priorizar tiles visíveis primeiro.
DEFAULT_VIEWPORT_CENTER_X = 128.0
DEFAULT_VIEWPORT_CENTER_Y = -130.0
DEFAULT_VIEW_WIDTH = 1920
DEFAULT_VIEW_HEIGHT = 1080

DEPOSIT_TYPES: frozenset[int] = frozenset({33, 52, 51, 88, 12})
# Campos e minas ficam no QML (filtro "Recursos") — são centenas de ícones dispensáveis no bake.
RESOURCE_TYPES: frozenset[int] = frozenset({20, 21, 22, 23, 32, 38, 40, 61, 62})

ICON_MAP: dict[int, str] = {
    5: "MapIconTownBaseTier1.webp",
    6: "MapIconTownBaseTier2.webp",
    7: "MapIconTownBaseTier3.webp",
    8: "MapIconTownBaseTier1.webp",
    9: "MapIconTownBaseTier2.webp",
    10: "MapIconTownBaseTier3.webp",
    11: "MapIconHospital.webp",
    16: "MapIconManufacturing.webp",
    17: "MapIconManufacturing.webp",
    18: "Shipyard.webp",
    19: "MapIconTechCenter.webp",
    20: "MapIconSalvageColor.webp",
    21: "MapIconComponentsColor.webp",
    22: "MapIconFuel.webp",
    23: "MapIconSulfurColor.webp",
    27: "MapIconsKeep.webp",
    28: "MapIconObservationTower.webp",
    29: "MapIconRelicBase.webp",
    31: "MapIconSulfurMineColor.webp",
    32: "MapIconSulfurMineColor.webp",
    34: "MapIconFactory.webp",
    35: "MapIconSafehouse.webp",
    36: "MapIconFactory.webp",
    37: "MapIconRocketSite.webp",
    38: "MapIconSalvageMineColor.webp",
    39: "MapIconConstructionYard.webp",
    40: "MapIconComponentMineColor.webp",
    41: "MapIconFacilityMineOilRig.webp",
    42: "MapIconRocketTarget.webp",
    43: "MapIconMortarHouse.webp",
    45: "MapIconRelicBase.webp",
    46: "MapIconRelicBase.webp",
    47: "MapIconRelicBase.webp",
    48: "MapIconStormcannon.webp",
    49: "MapIconIntelcenter.webp",
    50: "MapIconBorderBase.webp",
    53: "MapIconCoastalGun.webp",
    54: "MapIconFactory.webp",
    55: "MapIconBorderBase.webp",
    56: "MapIconTownBaseTier1.webp",
    57: "MapIconTownBaseTier2.webp",
    58: "MapIconTownBaseTier3.webp",
    59: "MapIconStormcannon.webp",
    60: "MapIconIntelcenter.webp",
    61: "MapIconCoalFieldColor.webp",
    62: "MapIconOilFieldColor.webp",
    70: "MapIconRocketTarget.webp",
    71: "MapIconRocketGroundZero.webp",
    75: "unknown.webp",
    84: "MapIconMaintenanceTunnel.webp",
    85: "MapIconTrainBridge.webp",
    86: "Shipyard.webp",
    87: "MapIconFacilityMineOilRig.webp",
}

TEAM_COLORS: dict[int, tuple[int, int, int]] = {
    1: (59, 130, 246),
    2: (34, 197, 94),
}

TileKey = tuple[int, int, int]


@dataclass(frozen=True)
class Structure:
    id: int
    name: str
    team: int
    type: int
    x: float
    y: float

    def to_state_entry(self) -> dict[str, Any]:
        return {
            "team": self.team,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "name": self.name,
        }

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> Structure:
        return cls(
            id=int(item["id"]),
            name=str(item.get("name", "")),
            team=int(item.get("team", 0)),
            type=int(item["type"]),
            x=float(item["x"]),
            y=float(item["y"]),
        )

    @classmethod
    def from_state(cls, sid: str, entry: dict[str, Any]) -> Structure:
        return cls(
            id=int(sid),
            name=str(entry.get("name", "")),
            team=int(entry.get("team", 0)),
            type=int(entry.get("type", 0)),
            x=float(entry["x"]),
            y=float(entry["y"]),
        )


@dataclass(frozen=True)
class MapLabel:
    text: str
    x: float
    y: float
    marker_type: str

    def visible_at_zoom(self, zoom: int) -> bool:
        if self.marker_type == "Hex":
            return zoom >= LABEL_HEX_MIN_ZOOM
        if self.marker_type == "Major":
            return zoom >= LABEL_MAJOR_MIN_ZOOM
        if self.marker_type == "Minor":
            return zoom >= LABEL_MINOR_MIN_ZOOM
        return True

    def font_size(self, zoom: int) -> int:
        if self.marker_type == "Hex":
            if zoom <= 2:
                return 11
            if zoom >= 5:
                return 36
            return 18
        if self.marker_type == "Major":
            return 22 if zoom >= 6 else 14
        return 15 if zoom >= 6 else 10


_icon_cache: dict[str, Image.Image] = {}
_font_cache: dict[tuple[bool, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
_cache_lock = threading.Lock()


def api_to_map_pixels(api_x: float, api_y: float, zoom: int) -> tuple[float, float]:
    zoom_factor = 2 ** zoom
    px = (api_x * MAP_SCALE + MAP_OFFSET_X) * zoom_factor
    py = (-api_y * MAP_SCALE + MAP_OFFSET_Y) * zoom_factor
    return px, py


def is_bakeable(item: dict[str, Any]) -> bool:
    stype = int(item.get("type", -1))
    return (
        stype not in DEPOSIT_TYPES
        and stype not in RESOURCE_TYPES
        and stype in ICON_MAP
    )


def fetch_map_items() -> list[dict[str, Any]]:
    req = urllib.request.Request(MAP_ITEMS_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_map_labels(origins_path: Path) -> list[MapLabel]:
    with open(origins_path, encoding="utf-8") as f:
        hex_origins: dict[str, list[float]] = json.load(f)

    req = urllib.request.Request(MAPS_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        maps = json.loads(response.read().decode())

    labels: list[MapLabel] = []

    for map_id in maps:
        origin = hex_origins.get(map_id)
        if not origin:
            continue
        origin_x, origin_y = origin[0], origin[1]

        hex_display = re.sub(r"(?<!^)(?=[A-Z])", " ", map_id.replace("Hex", ""))
        labels.append(MapLabel(hex_display, origin_x + 0.5 * SCALE_X, origin_y + 0.5 * SCALE_Y, "Hex"))

        try:
            static_req = urllib.request.Request(
                STATIC_MAP_URL.format(map_id=map_id),
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(static_req, timeout=20) as static_res:
                data = json.loads(static_res.read().decode())
        except Exception:
            continue

        for text_item in data.get("mapTextItems", []):
            lx = float(text_item.get("x", 0))
            ly = float(text_item.get("y", 0))
            labels.append(
                MapLabel(
                    str(text_item.get("text", "")),
                    origin_x + lx * SCALE_X,
                    origin_y + ly * SCALE_Y,
                    str(text_item.get("mapMarkerType", "Minor")),
                )
            )

    return labels


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    key = (bold, size)
    with _cache_lock:
        if key in _font_cache:
            return _font_cache[key]

    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf") if bold else Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf") if bold else Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            font = ImageFont.truetype(str(path), size=size)
            with _cache_lock:
                _font_cache[key] = font
            return font

    font = ImageFont.load_default()
    with _cache_lock:
        _font_cache[key] = font
    return font


def load_icon(structure_type: int, icons_dir: Path) -> Image.Image | None:
    filename = ICON_MAP.get(structure_type, "unknown.webp")
    with _cache_lock:
        if filename in _icon_cache:
            return _icon_cache[filename].copy()

    path = icons_dir / filename
    if not path.exists():
        path = icons_dir / "unknown.webp"
        if not path.exists():
            return None

    icon = Image.open(path).convert("RGBA")
    if icon.size != (ICON_SIZE, ICON_SIZE):
        icon = icon.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)

    with _cache_lock:
        _icon_cache[filename] = icon.copy()
    return icon


def colorize_icon(icon: Image.Image, team: int) -> Image.Image:
    icon = icon.convert("RGBA")
    if team not in TEAM_COLORS:
        return icon

    color = TEAM_COLORS[team]
    gray = icon.convert("L")
    _, _, _, alpha = icon.split()
    tinted = Image.new("RGBA", icon.size, color)
    tinted.putalpha(gray)
    tinted.putalpha(ImageChops.multiply(gray, alpha))
    return tinted


def download_raw_tile(raw_dir: Path, z: int, x: int, y: int, force: bool = False) -> Image.Image | None:
    rel = Path(str(z)) / str(x) / f"{y}.webp"
    raw_path = raw_dir / rel

    if not force and raw_path.exists() and raw_path.stat().st_size > 0:
        try:
            return Image.open(raw_path).convert("RGBA")
        except Exception:
            pass

    url = BASE_TILE_URL.format(z=z, x=x, y=y)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()
        if not data:
            return None
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(data)
        return Image.open(raw_path).convert("RGBA")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(b"")
            return None
        raise


def tiles_for_rect(px: float, py: float, half_w: float, half_h: float, zoom: int) -> set[TileKey]:
    max_tile = (2 ** zoom) - 1
    left = px - half_w
    right = px + half_w
    top = py - half_h
    bottom = py + half_h
    tiles: set[TileKey] = set()
    tx_min = max(0, int(math.floor(left / TILE_SIZE)))
    tx_max = min(max_tile, int(math.floor(right / TILE_SIZE)))
    ty_min = max(0, int(math.floor(top / TILE_SIZE)))
    ty_max = min(max_tile, int(math.floor(bottom / TILE_SIZE)))
    for tx in range(tx_min, tx_max + 1):
        for ty in range(ty_min, ty_max + 1):
            tiles.add((zoom, tx, ty))
    return tiles


def tiles_for_structure(structure: Structure, zoom: int) -> set[TileKey]:
    px, py = api_to_map_pixels(structure.x, structure.y, zoom)
    half = ICON_SIZE / 2.0
    return tiles_for_rect(px, py, half, half, zoom)


def viewport_tile_keys(
    zoom: int,
    center_api_x: float = DEFAULT_VIEWPORT_CENTER_X,
    center_api_y: float = DEFAULT_VIEWPORT_CENTER_Y,
    view_width: int = DEFAULT_VIEW_WIDTH,
    view_height: int = DEFAULT_VIEW_HEIGHT,
) -> set[TileKey]:
    """Tiles visíveis na região central do mapa (camada prioritária)."""
    cx, cy = api_to_map_pixels(center_api_x, center_api_y, zoom)
    half_w = view_width / 2.0 + TILE_SIZE
    half_h = view_height / 2.0 + TILE_SIZE
    return tiles_for_rect(cx, cy, half_w, half_h, zoom)


def collect_viewport_keys(zooms: tuple[int, ...]) -> set[TileKey]:
    keys: set[TileKey] = set()
    for zoom in zooms:
        keys |= viewport_tile_keys(zoom)
    return keys


def measure_label(draw: ImageDraw.ImageDraw, label: MapLabel, zoom: int) -> tuple[int, int]:
    is_hex = label.marker_type == "Hex"
    is_major = label.marker_type == "Major"
    font = get_font(label.font_size(zoom), bold=is_hex or is_major)
    text = label.text.upper() if is_hex else label.text
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def tiles_for_label(label: MapLabel, zoom: int) -> set[TileKey]:
    if not label.visible_at_zoom(zoom) or not label.text.strip():
        return set()
    px, py = api_to_map_pixels(label.x, label.y, zoom)
    tmp = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(tmp)
    w, h = measure_label(draw, label, zoom)
    return tiles_for_rect(px, py, w / 2.0 + 4, h / 2.0 + 4, zoom)


def draw_outlined_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    width: int = 2,
) -> None:
    x, y = xy
    for ox in range(-width, width + 1):
        for oy in range(-width, width + 1):
            if ox * ox + oy * oy <= width * width:
                draw.text((x + ox, y + oy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def paste_icon(tile: Image.Image, icon: Image.Image, center_px: float, center_py: float, tile_x: int, tile_y: int) -> None:
    local_x = int(round(center_px - tile_x * TILE_SIZE - ICON_SIZE / 2))
    local_y = int(round(center_py - tile_y * TILE_SIZE - ICON_SIZE / 2))
    tile.paste(icon, (local_x, local_y), icon)


def bake_icon_tile(
    raw_dir: Path,
    out_dir: Path,
    icons_dir: Path,
    z: int,
    x: int,
    y: int,
    structures: list[Structure],
    force_download: bool = False,
) -> bool:
    tile_img = download_raw_tile(raw_dir, z, x, y, force=force_download)
    if tile_img is None:
        return False

    if z >= ICON_MIN_ZOOM:
        for structure in structures:
            px, py = api_to_map_pixels(structure.x, structure.y, z)
            icon = load_icon(structure.type, icons_dir)
            if icon is None:
                continue
            paste_icon(tile_img, colorize_icon(icon, structure.team), px, py, x, y)

    out_path = out_dir / str(z) / str(x) / f"{y}.webp"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tile_img.save(out_path, "WEBP", quality=90, method=4)
    return True


def bake_label_tile(
    out_dir: Path,
    z: int,
    x: int,
    y: int,
    labels: list[MapLabel],
) -> bool:
    tile_img = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile_img)
    drew = False

    for label in labels:
        if not label.visible_at_zoom(z):
            continue
        px, py = api_to_map_pixels(label.x, label.y, z)
        is_hex = label.marker_type == "Hex"
        is_major = label.marker_type == "Major"
        font = get_font(label.font_size(z), bold=is_hex or is_major)
        text = label.text.upper() if is_hex else label.text

        tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        w, h = measure_label(tmp, label, z)
        local_x = int(round(px - x * TILE_SIZE - w / 2))
        local_y = int(round(py - y * TILE_SIZE - h / 2))

        if is_hex:
            fill = (255, 255, 255, int(255 * 0.75))
            outline = (0, 0, 0, int(255 * 0.8))
        elif is_major:
            fill = (255, 255, 255, 255)
            outline = (0, 0, 0, int(255 * 0.9))
        else:
            opacity = 0.9 if z >= 5 else 0.6
            fill = (221, 221, 221, int(255 * opacity))
            outline = (0, 0, 0, int(255 * 0.9))

        draw_outlined_text(draw, (local_x, local_y), text, font, fill, outline, width=2 if is_hex else 1)
        drew = True

    if not drew:
        return False

    out_path = out_dir / str(z) / str(x) / f"{y}.webp"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tile_img.save(out_path, "WEBP", quality=90, method=4)
    return True


def run_parallel(
    keys: list[TileKey],
    worker_fn: Callable[[TileKey], bool],
    workers: int,
    stage: str,
    progress: ProgressCallback | None,
) -> tuple[int, int]:
    if not keys:
        return 0, 0

    success = 0
    errors = 0
    total = len(keys)
    done = 0
    lock = threading.Lock()

    def report() -> None:
        if progress:
            progress(stage, done, total)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(worker_fn, key): key for key in keys}
        for future in as_completed(futures):
            try:
                if future.result():
                    success += 1
                else:
                    errors += 1
            except Exception:
                errors += 1
            with lock:
                done += 1
                if done % 10 == 0 or done == total:
                    report()
    report()
    return success, errors


class MapTileBaker:
    def __init__(self, cache_root: Path, resource_root: Path | None = None) -> None:
        self.cache_root = Path(cache_root)
        self.resource_root = Path(resource_root or resource_dir())
        self.raw_dir = self.cache_root / "raw" / "patch-64"
        self.icons_dir = self.cache_root / "patch-64-icons"
        self.labels_dir = self.cache_root / "patch-64-labels"
        self.icons_state = self.cache_root / "icons_bake_state.json"
        self.labels_state = self.cache_root / "labels_bake_state.json"
        self.icons_marker = self.icons_dir / ".bake_complete"
        self.labels_marker = self.labels_dir / ".bake_complete"
        self.icon_assets = self.resource_root / "img" / "iconmap"
        self.origins_path = self.resource_root / "data" / "origins.json"

    def icons_ready(self) -> bool:
        if not self.icons_marker.exists() or not self._has_sample_tile(self.icons_dir):
            return False
        try:
            meta = json.loads(self.icons_marker.read_text(encoding="utf-8"))
            return int(meta.get("version", 0)) >= BAKE_VERSION
        except Exception:
            return False

    def labels_ready(self) -> bool:
        if not self.labels_marker.exists() or not self._has_sample_label_tile():
            return False
        try:
            meta = json.loads(self.labels_marker.read_text(encoding="utf-8"))
            return int(meta.get("version", 0)) >= BAKE_VERSION
        except Exception:
            return False

    @staticmethod
    def _has_sample_tile(tile_dir: Path) -> bool:
        sample = tile_dir / "7" / "63" / "64.webp"
        return sample.exists() and sample.stat().st_size > 0

    def _has_sample_label_tile(self) -> bool:
        for z in (2, 5, 6):
            z_dir = self.labels_dir / str(z)
            if not z_dir.exists():
                continue
            for x_dir in z_dir.iterdir():
                if not x_dir.is_dir():
                    continue
                for tile in x_dir.glob("*.webp"):
                    if tile.stat().st_size > 0:
                        return True
        return False

    def _write_marker(self, path: Path, kind: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "version": BAKE_VERSION,
                    "kind": kind,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _load_icon_state(self) -> dict[str, Any] | None:
        if not self.icons_state.exists():
            return None
        try:
            return json.loads(self.icons_state.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _save_icon_state(self, structures: list[Structure]) -> None:
        payload = {
            "version": BAKE_VERSION,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "structures": {str(s.id): s.to_state_entry() for s in structures},
        }
        self.icons_state.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _structures_from_state(self, state: dict[str, Any] | None) -> dict[int, Structure]:
        if not state:
            return {}
        return {
            int(sid): Structure.from_state(sid, entry)
            for sid, entry in state.get("structures", {}).items()
        }

    def _build_icon_index(self, structures: list[Structure]) -> dict[TileKey, list[Structure]]:
        index: dict[TileKey, list[Structure]] = {}
        for z in ICON_BAKE_ZOOMS:
            for structure in structures:
                for key in tiles_for_structure(structure, z):
                    index.setdefault(key, []).append(structure)
        return index

    def _find_icon_changes(self, old: dict[int, Structure], new: dict[int, Structure]) -> set[TileKey]:
        changed: set[int] = set()
        for sid, structure in new.items():
            prev = old.get(sid)
            if prev is None or prev.team != structure.team:
                changed.add(sid)
        for sid in old:
            if sid not in new:
                changed.add(sid)

        affected: set[TileKey] = set()
        for sid in changed:
            for structure in (new.get(sid), old.get(sid)):
                if structure is None:
                    continue
                for zoom in ICON_BAKE_ZOOMS:
                    affected |= tiles_for_structure(structure, zoom)
        return affected

    def prepare_icon_bake(self, full: bool = False) -> tuple[dict[TileKey, list[Structure]], list[Structure]]:
        api_data = fetch_map_items()
        bakeable = [Structure.from_api(item) for item in api_data if is_bakeable(item)]
        if full or not self._load_icon_state():
            tile_index = self._build_icon_index(bakeable)
        else:
            old_map = self._structures_from_state(self._load_icon_state())
            new_map = {s.id: s for s in bakeable}
            affected = self._find_icon_changes(old_map, new_map)
            full_index = self._build_icon_index(bakeable)
            tile_index = {key: full_index.get(key, []) for key in affected}
        return tile_index, bakeable

    def bake_icon_keys(
        self,
        keys: list[TileKey],
        tile_index: dict[TileKey, list[Structure]],
        progress: ProgressCallback | None = None,
        stage: str = "icons_bake",
        workers: int = 6,
        force_download: bool = True,
    ) -> tuple[int, int]:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.icons_dir.mkdir(parents=True, exist_ok=True)

        def worker(key: TileKey) -> bool:
            z, x, y = key
            return bake_icon_tile(
                self.raw_dir,
                self.icons_dir,
                self.icon_assets,
                z,
                x,
                y,
                tile_index.get(key, []),
                force_download=force_download,
            )

        return run_parallel(keys, worker, workers, stage, progress)

    def finalize_icons(self, bakeable: list[Structure]) -> None:
        self._save_icon_state(bakeable)
        self._write_marker(self.icons_marker, "icons")

    def prepare_label_bake(self) -> tuple[dict[TileKey, list[MapLabel]], list[MapLabel]]:
        if not self.origins_path.exists():
            raise FileNotFoundError(f"origins.json não encontrado em {self.origins_path}")
        labels = fetch_map_labels(self.origins_path)
        return self._build_label_index(labels), labels

    def bake_label_keys(
        self,
        keys: list[TileKey],
        tile_index: dict[TileKey, list[MapLabel]],
        progress: ProgressCallback | None = None,
        stage: str = "labels_bake",
        workers: int = 6,
    ) -> tuple[int, int]:
        self.labels_dir.mkdir(parents=True, exist_ok=True)

        def worker(key: TileKey) -> bool:
            z, x, y = key
            return bake_label_tile(self.labels_dir, z, x, y, tile_index.get(key, []))

        return run_parallel(keys, worker, workers, stage, progress)

    def finalize_labels(self, labels: list[MapLabel]) -> None:
        marker_payload = {
            "version": BAKE_VERSION,
            "label_count": len(labels),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.labels_state.write_text(json.dumps(marker_payload, indent=2), encoding="utf-8")
        self._write_marker(self.labels_marker, "labels")

    def generate_icons(
        self,
        progress: ProgressCallback | None = None,
        workers: int = 6,
        full: bool = False,
        staged: bool = False,
        on_viewport_complete: OnStageComplete | None = None,
    ) -> tuple[int, int]:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.icons_dir.mkdir(parents=True, exist_ok=True)

        if progress:
            progress("icons_fetch", 0, 1)
        api_data = fetch_map_items()
        bakeable = [Structure.from_api(item) for item in api_data if is_bakeable(item)]
        new_map = {s.id: s for s in bakeable}
        old_state = None if full else self._load_icon_state()
        old_map = self._structures_from_state(old_state)

        if full or not old_state:
            tile_index = self._build_icon_index(bakeable)
            keys = list(tile_index.keys())
            force = True
        else:
            affected = self._find_icon_changes(old_map, new_map)
            if not affected:
                self._save_icon_state(bakeable)
                return 0, 0
            full_index = self._build_icon_index(bakeable)
            tile_index = {key: full_index.get(key, []) for key in affected}
            keys = list(tile_index.keys())
            force = True

        viewport_keys = collect_viewport_keys(ICON_BAKE_ZOOMS) if staged else set()
        priority = [k for k in keys if k in viewport_keys] if staged else []
        remainder = [k for k in keys if k not in viewport_keys] if staged else keys

        def worker(key: TileKey) -> bool:
            z, x, y = key
            return bake_icon_tile(
                self.raw_dir,
                self.icons_dir,
                self.icon_assets,
                z,
                x,
                y,
                tile_index[key],
                force_download=force,
            )

        ok = err = 0
        if priority:
            p_ok, p_err = run_parallel(priority, worker, workers, "icons_viewport", progress)
            ok += p_ok
            err += p_err
            if on_viewport_complete:
                on_viewport_complete()

        if remainder:
            r_ok, r_err = run_parallel(remainder, worker, workers, "icons_background", progress)
            ok += r_ok
            err += r_err

        self._save_icon_state(bakeable)
        self._write_marker(self.icons_marker, "icons")
        return ok, err

    def _build_label_index(self, labels: list[MapLabel]) -> dict[TileKey, list[MapLabel]]:
        index: dict[TileKey, list[MapLabel]] = {}
        for zoom in LABEL_BAKE_ZOOMS:
            for label in labels:
                for key in tiles_for_label(label, zoom):
                    index.setdefault(key, []).append(label)
        return index

    def generate_labels(
        self,
        progress: ProgressCallback | None = None,
        workers: int = 6,
        full: bool = False,
        staged: bool = False,
        on_viewport_complete: OnStageComplete | None = None,
    ) -> tuple[int, int]:
        self.labels_dir.mkdir(parents=True, exist_ok=True)

        if not self.origins_path.exists():
            raise FileNotFoundError(f"origins.json não encontrado em {self.origins_path}")

        if progress:
            progress("labels_fetch", 0, 1)
        labels = fetch_map_labels(self.origins_path)

        if full or not self.labels_marker.exists():
            tile_index = self._build_label_index(labels)
        else:
            return 0, 0

        keys = list(tile_index.keys())
        viewport_keys = collect_viewport_keys(LABEL_BAKE_ZOOMS) if staged else set()
        priority = [k for k in keys if k in viewport_keys] if staged else []
        remainder = [k for k in keys if k not in viewport_keys] if staged else keys

        def worker(key: TileKey) -> bool:
            z, x, y = key
            return bake_label_tile(self.labels_dir, z, x, y, tile_index[key])

        ok = err = 0
        if priority:
            p_ok, p_err = run_parallel(priority, worker, workers, "labels_viewport", progress)
            ok += p_ok
            err += p_err
            if on_viewport_complete:
                on_viewport_complete()

        if remainder:
            r_ok, r_err = run_parallel(remainder, worker, workers, "labels_background", progress)
            ok += r_ok
            err += r_err

        marker_payload = {
            "version": BAKE_VERSION,
            "label_count": len(labels),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.labels_state.write_text(json.dumps(marker_payload, indent=2), encoding="utf-8")
        self._write_marker(self.labels_marker, "labels")
        return ok, err

    def generate_all(
        self,
        progress: ProgressCallback | None = None,
        workers: int = 6,
        force_full: bool = False,
        include_labels: bool = False,
    ) -> None:
        needs_icons = force_full or not self.icons_ready()
        needs_labels = include_labels and (force_full or not self.labels_ready())

        if needs_icons:
            self.generate_icons(progress=progress, workers=workers, full=force_full or needs_icons)
        elif progress:
            progress("icons_skip", 1, 1)

        if needs_labels:
            self.generate_labels(progress=progress, workers=workers, full=force_full or needs_labels)
        elif progress:
            progress("labels_skip", 1, 1)

        if progress:
            progress("done", 1, 1)
