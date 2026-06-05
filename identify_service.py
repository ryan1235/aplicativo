from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ICONS_DIR = BASE_DIR / "Content" / "Textures" / "UI" / "ItemIcons"
DEFAULT_MODS_DIR = BASE_DIR / "mods"

try:
    import numpy as np
except ImportError:  # pragma: no cover - similarity falls back to PIL data.
    np = None

try:
    import cv2
except ImportError:  # pragma: no cover - numpy fallback is still useful.
    cv2 = None

try:
    from PIL import Image, ImageEnhance, ImageGrab
except ImportError:  # pragma: no cover - controller reports unavailable features.
    Image = None
    ImageEnhance = None
    ImageGrab = None


@dataclass(frozen=True)
class IconTemplate:
    name: str
    path: Path
    gray: Any
    color: Any


@dataclass(frozen=True)
class IdentifyMatch:
    name: str
    path: Path
    score: float


def dependencies_status() -> str:
    missing = []
    if Image is None:
        missing.append("pillow")
    if np is None:
        missing.append("numpy")
    if cv2 is None:
        missing.append("opencv-python")
    return "OK" if not missing else "Missing: " + ", ".join(missing)


def index_icon_templates(
    icons_dir: Path = DEFAULT_ICONS_DIR,
    mods_dir: Path = DEFAULT_MODS_DIR,
) -> tuple[list[IconTemplate], str]:
    if Image is None:
        return [], "Pillow is required to index icons."
    if not icons_dir.exists():
        return [], f"Icons directory missing: {icons_dir}"

    templates: list[IconTemplate] = []
    for path in icons_dir.rglob("*.png"):
        template = prepare_icon_template(path, path.stem)
        if template is not None:
            templates.append(template)

    if mods_dir.exists():
        for path in mods_dir.rglob("*.png"):
            stem = path.stem
            if "_" not in stem:
                continue
            template = prepare_icon_template(path, stem.split("_", 1)[0])
            if template is not None:
                templates.append(template)

    unique = len({item.name for item in templates})
    return templates, f"Indexed {len(templates)} templates ({unique} unique items)"


def prepare_icon_template(path: Path, name: str | None = None) -> IconTemplate | None:
    gray, color = prepare_image_path(path)
    if gray is None:
        return None
    return IconTemplate(name=name or path.stem, path=path, gray=gray, color=color)


def prepare_image_path(path: Path) -> tuple[Any | None, Any | None]:
    if Image is None:
        return None, None
    try:
        image = Image.open(path).convert("RGBA")
    except Exception:
        return None, None
    return prepare_image(image)


def prepare_image(image) -> tuple[Any | None, Any | None]:
    if Image is None:
        return None, None
    try:
        rgba = image.convert("RGBA")
        black = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
        composed = Image.alpha_composite(black, rgba).resize((32, 32), Image.Resampling.LANCZOS)
        if ImageEnhance is not None:
            composed = ImageEnhance.Sharpness(composed).enhance(2.0)
        gray_image = composed.convert("L")
        rgb_image = composed.convert("RGB")
        if np is None:
            return gray_image, None
        return np.array(gray_image, dtype=np.uint8), np.array(rgb_image, dtype=np.uint8)
    except Exception:
        return None, None


def scan_image_path(
    path: Path,
    templates: list[IconTemplate],
    *,
    mode: str = "Hybrid",
    limit: int = 25,
) -> tuple[list[IdentifyMatch], str]:
    if Image is None:
        return [], "Pillow is required to scan images."
    try:
        image = Image.open(path).convert("RGBA")
    except Exception as exc:
        return [], f"Could not open image: {exc}"
    return scan_image(image, templates, mode=mode, limit=limit)


def scan_image(
    image,
    templates: list[IconTemplate],
    *,
    mode: str = "Hybrid",
    limit: int = 25,
) -> tuple[list[IdentifyMatch], str]:
    target_gray, target_color = prepare_image(image)
    if target_gray is None:
        return [], "No target image selected."
    if not templates:
        return [], "No indexed icon templates."

    normalized_mode = mode.strip().lower()
    scores: list[IdentifyMatch] = []
    for template in templates:
        gray_score = gray_similarity(target_gray, template.gray)
        if normalized_mode == "gray" or np is None or target_color is None or template.color is None:
            score = gray_score
        else:
            color_score = color_similarity(target_color, template.color)
            score = color_score if normalized_mode == "color" else (gray_score * 0.65) + (color_score * 0.35)
        scores.append(IdentifyMatch(name=template.name, path=template.path, score=score))

    scores.sort(key=lambda item: item.score, reverse=True)
    return scores[:limit], f"Found {min(limit, len(scores))} ranked matches"


def gray_similarity(a, b) -> float:
    if cv2 is not None and np is not None:
        result = cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED)
        return float(result[0][0])
    if np is not None:
        diff = np.abs(a.astype(np.int16) - b.astype(np.int16))
        mae = float(diff.mean()) / 255.0
        return max(0.0, 1.0 - mae)
    a_data = list(a.getdata())
    b_data = list(b.getdata())
    if not a_data or len(a_data) != len(b_data):
        return 0.0
    total = sum(abs(int(av) - int(bv)) for av, bv in zip(a_data, b_data))
    mae = (total / len(a_data)) / 255.0
    return max(0.0, 1.0 - mae)


def color_similarity(a_rgb, b_rgb) -> float:
    if np is None or a_rgb is None or b_rgb is None:
        return 0.0
    diff = np.abs(a_rgb.astype(np.int16) - b_rgb.astype(np.int16))
    mae = float(diff.mean()) / 255.0
    return max(0.0, 1.0 - mae)


def grab_clipboard_image():
    if ImageGrab is None:
        return None, "Clipboard capture requires Pillow ImageGrab."
    try:
        grabbed = ImageGrab.grabclipboard()
    except Exception as exc:
        return None, f"Clipboard read failed: {exc}"
    if grabbed is None:
        return None, "Clipboard does not contain an image."
    if isinstance(grabbed, list):
        candidates = [Path(item) for item in grabbed if isinstance(item, str)]
        first_image = next((path for path in candidates if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}), None)
        if first_image and first_image.exists() and Image is not None:
            try:
                return Image.open(first_image).convert("RGBA"), f"Loaded clipboard file: {first_image.name}"
            except Exception as exc:
                return None, f"Could not open clipboard file: {exc}"
        return None, "Clipboard does not contain a supported image file."
    if hasattr(grabbed, "convert"):
        return grabbed.convert("RGBA"), "Loaded clipboard image."
    return None, "Clipboard data is not a supported image."


def grab_screen_image():
    if ImageGrab is None:
        return None, "Screen capture requires Pillow ImageGrab."
    try:
        return ImageGrab.grab().convert("RGBA"), "Captured full screen. Crop item icons externally for best accuracy."
    except Exception as exc:
        return None, f"Screen capture failed: {exc}"
