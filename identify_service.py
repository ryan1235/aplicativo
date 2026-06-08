from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ICONS_DIR = BASE_DIR / "Content" / "Textures" / "UI" / "ItemIcons"
DEFAULT_MODS_DIR = BASE_DIR / "mods"

_UNLOADED = object()
_np: Any = _UNLOADED
_cv2: Any = _UNLOADED
_image: Any = _UNLOADED
_image_enhance: Any = _UNLOADED
_image_grab: Any = _UNLOADED


def _load_numpy():
    global _np
    if _np is _UNLOADED:
        try:
            import numpy as numpy_module
        except ImportError:  # pragma: no cover - similarity falls back to PIL data.
            _np = None
        else:
            _np = numpy_module
    return _np


def _load_cv2():
    global _cv2
    if _cv2 is _UNLOADED:
        try:
            import cv2 as cv2_module
        except ImportError:  # pragma: no cover - numpy fallback is still useful.
            _cv2 = None
        else:
            _cv2 = cv2_module
    return _cv2


def _load_pillow():
    global _image, _image_enhance, _image_grab
    if _image is _UNLOADED:
        try:
            from PIL import Image as image_module
            from PIL import ImageEnhance as image_enhance_module
            from PIL import ImageGrab as image_grab_module
        except ImportError:  # pragma: no cover - controller reports unavailable features.
            _image = None
            _image_enhance = None
            _image_grab = None
        else:
            _image = image_module
            _image_enhance = image_enhance_module
            _image_grab = image_grab_module
    return _image, _image_enhance, _image_grab


def monitor_dependencies() -> tuple[Any, Any, Any]:
    """Return numpy, cv2 and ImageGrab, loading them only for monitoring."""
    _image_module, _image_enhance_module, image_grab = _load_pillow()
    return _load_numpy(), _load_cv2(), image_grab


def monitor_dependencies_available() -> bool:
    np_module, cv2_module, image_grab = monitor_dependencies()
    return bool(np_module is not None and cv2_module is not None and image_grab is not None)


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
    image_module, _image_enhance_module, _image_grab_module = _load_pillow()
    np_module = _load_numpy()
    cv2_module = _load_cv2()
    missing = []
    if image_module is None:
        missing.append("pillow")
    if np_module is None:
        missing.append("numpy")
    if cv2_module is None:
        missing.append("opencv-python")
    return "OK" if not missing else "Missing: " + ", ".join(missing)


def index_icon_templates(
    icons_dir: Path = DEFAULT_ICONS_DIR,
    mods_dir: Path = DEFAULT_MODS_DIR,
) -> tuple[list[IconTemplate], str]:
    image_module, _image_enhance_module, _image_grab_module = _load_pillow()
    if image_module is None:
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
    image_module, _image_enhance_module, _image_grab_module = _load_pillow()
    if image_module is None:
        return None, None
    try:
        image = image_module.open(path).convert("RGBA")
    except Exception:
        return None, None
    return prepare_image(image)


def prepare_image(image) -> tuple[Any | None, Any | None]:
    image_module, image_enhance_module, _image_grab_module = _load_pillow()
    if image_module is None:
        return None, None
    np_module = _load_numpy()
    try:
        rgba = image.convert("RGBA")
        black = image_module.new("RGBA", rgba.size, (0, 0, 0, 255))
        composed = image_module.alpha_composite(black, rgba).resize((32, 32), image_module.Resampling.LANCZOS)
        if image_enhance_module is not None:
            composed = image_enhance_module.Sharpness(composed).enhance(2.0)
        gray_image = composed.convert("L")
        rgb_image = composed.convert("RGB")
        if np_module is None:
            return gray_image, None
        return np_module.array(gray_image, dtype=np_module.uint8), np_module.array(rgb_image, dtype=np_module.uint8)
    except Exception:
        return None, None


def scan_image_path(
    path: Path,
    templates: list[IconTemplate],
    *,
    mode: str = "Hybrid",
    limit: int = 25,
) -> tuple[list[IdentifyMatch], str]:
    image_module, _image_enhance_module, _image_grab_module = _load_pillow()
    if image_module is None:
        return [], "Pillow is required to scan images."
    try:
        image = image_module.open(path).convert("RGBA")
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
        np_module = _load_numpy()
        if normalized_mode == "gray" or np_module is None or target_color is None or template.color is None:
            score = gray_score
        else:
            color_score = color_similarity(target_color, template.color)
            score = color_score if normalized_mode == "color" else (gray_score * 0.65) + (color_score * 0.35)
        scores.append(IdentifyMatch(name=template.name, path=template.path, score=score))

    scores.sort(key=lambda item: item.score, reverse=True)
    return scores[:limit], f"Found {min(limit, len(scores))} ranked matches"


def gray_similarity(a, b) -> float:
    np_module = _load_numpy()
    cv2_module = _load_cv2()
    if cv2_module is not None and np_module is not None:
        result = cv2_module.matchTemplate(a, b, cv2_module.TM_CCOEFF_NORMED)
        return float(result[0][0])
    if np_module is not None:
        diff = np_module.abs(a.astype(np_module.int16) - b.astype(np_module.int16))
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
    np_module = _load_numpy()
    if np_module is None or a_rgb is None or b_rgb is None:
        return 0.0
    diff = np_module.abs(a_rgb.astype(np_module.int16) - b_rgb.astype(np_module.int16))
    mae = float(diff.mean()) / 255.0
    return max(0.0, 1.0 - mae)


def grab_clipboard_image():
    image_module, _image_enhance_module, image_grab = _load_pillow()
    if image_grab is None:
        return None, "Clipboard capture requires Pillow ImageGrab."
    try:
        grabbed = image_grab.grabclipboard()
    except Exception as exc:
        return None, f"Clipboard read failed: {exc}"
    if grabbed is None:
        return None, "Clipboard does not contain an image."
    if isinstance(grabbed, list):
        candidates = [Path(item) for item in grabbed if isinstance(item, str)]
        first_image = next((path for path in candidates if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}), None)
        if first_image and first_image.exists() and image_module is not None:
            try:
                return image_module.open(first_image).convert("RGBA"), f"Loaded clipboard file: {first_image.name}"
            except Exception as exc:
                return None, f"Could not open clipboard file: {exc}"
        return None, "Clipboard does not contain a supported image file."
    if hasattr(grabbed, "convert"):
        return grabbed.convert("RGBA"), "Loaded clipboard image."
    return None, "Clipboard data is not a supported image."


def grab_screen_image():
    _image_module, _image_enhance_module, image_grab = _load_pillow()
    if image_grab is None:
        return None, "Screen capture requires Pillow ImageGrab."
    try:
        return image_grab.grab().convert("RGBA"), "Captured full screen. Crop item icons externally for best accuracy."
    except Exception as exc:
        return None, f"Screen capture failed: {exc}"
