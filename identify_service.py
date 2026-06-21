from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent

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
        except ImportError:  # pragma: no cover - controller reports unavailable detection.
            _np = None
        else:
            _np = numpy_module
    return _np


def _load_cv2():
    global _cv2
    if _cv2 is _UNLOADED:
        try:
            import cv2 as cv2_module
        except ImportError:  # pragma: no cover - controller reports unavailable detection.
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
class DetectionTemplate:
    path: Path | None
    name: str
    color: Any
    gray: Any


DETECTION_TEMPLATE_MAX_SIDE = 128


def _clip_rect(x: int, y: int, width: int, height: int, max_width: int, max_height: int) -> tuple[int, int, int, int]:
    x = max(0, min(x, max_width - 1))
    y = max(0, min(y, max_height - 1))
    width = max(1, min(width, max_width - x))
    height = max(1, min(height, max_height - y))
    return x, y, width, height


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


def prepare_detection_template_path(path: Path) -> tuple[DetectionTemplate | None, str]:
    image_module, _image_enhance_module, _image_grab_module = _load_pillow()
    if image_module is None:
        return None, "Pillow is required to load the reference image."
    try:
        image = image_module.open(path).convert("RGBA")
    except Exception as exc:
        return None, f"Could not open image: {exc}"
    template, status = prepare_detection_template(image, name=path.name, path=path)
    return template, status


def prepare_detection_template(image, *, name: str = "selected image", path: Path | None = None) -> tuple[DetectionTemplate | None, str]:
    image_module, _image_enhance_module, _image_grab_module = _load_pillow()
    np_module = _load_numpy()
    cv2_module = _load_cv2()
    if image_module is None or np_module is None or cv2_module is None:
        return None, "Pillow, numpy and opencv-python are required for detection."
    try:
        rgba = image.convert("RGBA")
        background = image_module.new("RGBA", rgba.size, (0, 0, 0, 255))
        composed = image_module.alpha_composite(background, rgba)
        width, height = composed.size
        max_side = max(width, height)
        if max_side > DETECTION_TEMPLATE_MAX_SIDE:
            scale = DETECTION_TEMPLATE_MAX_SIDE / float(max_side)
            composed = composed.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                image_module.Resampling.LANCZOS,
            )
        color = np_module.array(composed.convert("RGB"), dtype=np_module.uint8)
        gray = np_module.array(composed.convert("L"), dtype=np_module.uint8)
        if color.shape[0] < 8 or color.shape[1] < 8:
            return None, "Reference image is too small for reliable detection."
        return DetectionTemplate(path=path, name=name, color=color, gray=gray), "Reference ready for live detection."
    except Exception as exc:
        return None, f"Could not prepare reference image: {exc}"


def detect_stockpile_item_regions(image, *, limit: int = 180) -> tuple[list[dict[str, int]], str]:
    np_module = _load_numpy()
    cv2_module = _load_cv2()
    if np_module is None or cv2_module is None:
        return [], "numpy and opencv-python are required for stockpile selection."

    try:
        rgb = np_module.array(image.convert("RGB"), dtype=np_module.uint8)
    except Exception as exc:
        return [], f"Could not read screen image: {exc}"

    screen_h, screen_w = rgb.shape[:2]
    if screen_w < 300 or screen_h < 220:
        return [], "Screen capture is too small."

    gray = cv2_module.cvtColor(rgb, cv2_module.COLOR_RGB2GRAY)
    hsv = cv2_module.cvtColor(rgb, cv2_module.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1]
    r = rgb[:, :, 0].astype(np_module.int16)
    g = rgb[:, :, 1].astype(np_module.int16)
    b = rgb[:, :, 2].astype(np_module.int16)
    neutral = (np_module.abs(r - g) < 18) & (np_module.abs(g - b) < 18) & (np_module.abs(r - b) < 18)
    qty_mask = ((gray >= 52) & (gray <= 155) & ((saturation < 42) | neutral)).astype(np_module.uint8) * 255
    qty_mask[:70, :] = 0
    qty_mask[:, : int(screen_w * 0.18)] = 0
    qty_mask = cv2_module.morphologyEx(qty_mask, cv2_module.MORPH_OPEN, np_module.ones((3, 3), np_module.uint8))
    qty_mask = cv2_module.morphologyEx(qty_mask, cv2_module.MORPH_CLOSE, np_module.ones((5, 5), np_module.uint8))

    qty_contours, _hierarchy = cv2_module.findContours(qty_mask, cv2_module.RETR_EXTERNAL, cv2_module.CHAIN_APPROX_SIMPLE)
    candidates: list[dict[str, int]] = []
    for contour in qty_contours:
        qx, qy, qw, qh = cv2_module.boundingRect(contour)
        if qx < int(screen_w * 0.18) or qy < 70:
            continue
        if qw < 24 or qw > 72 or qh < 18 or qh > 40:
            continue
        aspect = qw / float(qh)
        if aspect < 0.9 or aspect > 2.7:
            continue
        fill_ratio = float((qty_mask[qy : qy + qh, qx : qx + qw] > 0).mean())
        if fill_ratio < 0.52:
            continue

        icon_size = int(max(24, min(44, round(qh * 1.22))))
        margin = max(4, int(qh * 0.18))
        crop_x = qx - icon_size - margin
        crop_y = qy + (qh // 2) - (icon_size // 2)
        if crop_x < 0 or crop_y < 0:
            continue
        crop_x, crop_y, crop_w, crop_h = _clip_rect(crop_x, crop_y, icon_size, icon_size, screen_w, screen_h)
        icon_gray = gray[crop_y : crop_y + crop_h, crop_x : crop_x + crop_w]
        icon_saturation = saturation[crop_y : crop_y + crop_h, crop_x : crop_x + crop_w]
        if icon_gray.size == 0:
            continue
        foreground = (((icon_gray > 58) | (icon_saturation > 45)).astype(np_module.uint8)) * 255
        foreground = cv2_module.morphologyEx(foreground, cv2_module.MORPH_OPEN, np_module.ones((2, 2), np_module.uint8))
        foreground_contours, _foreground_hierarchy = cv2_module.findContours(foreground, cv2_module.RETR_EXTERNAL, cv2_module.CHAIN_APPROX_SIMPLE)
        if foreground_contours:
            fx, fy, fw, fh = cv2_module.boundingRect(max(foreground_contours, key=cv2_module.contourArea))
            if fw >= 8 and fh >= 8:
                pad = 2
                crop_x, crop_y, crop_w, crop_h = _clip_rect(
                    crop_x + fx - pad,
                    crop_y + fy - pad,
                    fw + (pad * 2),
                    fh + (pad * 2),
                    screen_w,
                    screen_h,
                )
                icon_gray = gray[crop_y : crop_y + crop_h, crop_x : crop_x + crop_w]
        bright_ratio = float((icon_gray > 48).mean())
        contrast = float(icon_gray.std())
        if bright_ratio < 0.025 or contrast < 7.0:
            continue

        local_x, local_y, local_w, local_h = _clip_rect(crop_x - 8, min(crop_y, qy) - 8, (qx + qw + 8) - (crop_x - 8), max(crop_y + crop_h, qy + qh) - (min(crop_y, qy) - 8), screen_w, screen_h)
        local_gray = gray[local_y : local_y + local_h, local_x : local_x + local_w]
        if local_gray.size == 0 or float((local_gray < 72).mean()) < 0.35:
            continue

        select_padding = max(2, min(5, int(crop_w * 0.08)))
        select_x = max(0, crop_x - select_padding)
        select_y = max(0, crop_y - select_padding)
        select_right = min(screen_w, crop_x + crop_w + select_padding)
        select_bottom = min(screen_h, crop_y + crop_h + select_padding)
        candidates.append(
            {
                "qtyX": qx,
                "qtyY": qy,
                "qtyW": qw,
                "qtyH": qh,
                "selectX": select_x,
                "selectY": select_y,
                "selectW": max(1, select_right - select_x),
                "selectH": max(1, select_bottom - select_y),
                "cropX": crop_x,
                "cropY": crop_y,
                "cropW": crop_w,
                "cropH": crop_h,
            }
        )

    if len(candidates) < 4:
        return [], "Could not find stockpile item quantity boxes."

    remaining = set(range(len(candidates)))
    clusters: list[list[int]] = []
    while remaining:
        seed = remaining.pop()
        cluster = [seed]
        queue = [seed]
        while queue:
            current = queue.pop()
            current_center = (
                candidates[current]["qtyX"] + (candidates[current]["qtyW"] // 2),
                candidates[current]["qtyY"] + (candidates[current]["qtyH"] // 2),
            )
            linked = []
            for other in remaining:
                other_center = (
                    candidates[other]["qtyX"] + (candidates[other]["qtyW"] // 2),
                    candidates[other]["qtyY"] + (candidates[other]["qtyH"] // 2),
                )
                if abs(current_center[0] - other_center[0]) <= 132 and abs(current_center[1] - other_center[1]) <= 58:
                    linked.append(other)
            for other in linked:
                remaining.remove(other)
                queue.append(other)
                cluster.append(other)
        clusters.append(cluster)

    best_cluster: list[int] | None = None
    best_score = -1.0
    for cluster in clusters:
        if len(cluster) < 6:
            continue
        xs = [candidates[index]["qtyX"] for index in cluster]
        ys = [candidates[index]["qtyY"] for index in cluster]
        rights = [candidates[index]["qtyX"] + candidates[index]["qtyW"] for index in cluster]
        bottoms = [candidates[index]["qtyY"] + candidates[index]["qtyH"] for index in cluster]
        bx, by = min(xs), min(ys)
        br, bb = max(rights), max(bottoms)
        bw, bh = br - bx, bb - by
        if bw < 160 or bh < 85:
            continue
        row_count = len({round(candidates[index]["qtyY"] / 18) for index in cluster})
        col_count = len({round(candidates[index]["qtyX"] / 28) for index in cluster})
        if row_count < 2 or col_count < 2:
            continue
        ex, ey, ew, eh = _clip_rect(bx - 90, by - 54, bw + 118, bh + 72, screen_w, screen_h)
        cluster_gray = gray[ey : ey + eh, ex : ex + ew]
        dark_ratio = float((cluster_gray < 72).mean()) if cluster_gray.size else 0.0
        if dark_ratio < 0.34:
            continue
        center_bonus = 1.12 if (ex + (ew / 2)) > screen_w * 0.28 else 0.75
        compactness = len(cluster) / max(1.0, (bw * bh) / 10000.0)
        score = (len(cluster) * 12.0) + (row_count * 4.0) + (col_count * 3.0) + (dark_ratio * 35.0) + compactness
        score *= center_bonus
        if score > best_score:
            best_score = score
            best_cluster = cluster

    if not best_cluster:
        return [], "Could not isolate the stockpile item grid."

    raw_regions: list[dict[str, int]] = []
    seen: list[tuple[int, int]] = []
    for index in best_cluster:
        candidate = candidates[index]
        center = (
            candidate["cropX"] + (candidate["cropW"] // 2),
            candidate["cropY"] + (candidate["cropH"] // 2),
        )
        if any(abs(center[0] - old_x) < 18 and abs(center[1] - old_y) < 18 for old_x, old_y in seen):
            continue
        seen.append(center)
        raw_regions.append({key: int(candidate[key]) for key in ("selectX", "selectY", "selectW", "selectH", "cropX", "cropY", "cropW", "cropH")})

    if not raw_regions:
        return [], "Stockpile grid found, but no item slots were detected."

    detected_sizes = sorted(max(item["cropW"], item["cropH"]) for item in raw_regions)
    median_size = detected_sizes[len(detected_sizes) // 2]
    lower_typical_size = detected_sizes[max(0, int(len(detected_sizes) * 0.35) - 1)]
    standard_size = int(round((median_size * 0.65) + (lower_typical_size * 0.35)))
    standard_size = max(24, min(38, standard_size))
    regions: list[dict[str, int]] = []
    for item in raw_regions:
        center_x = item["cropX"] + (item["cropW"] // 2)
        center_y = item["cropY"] + (item["cropH"] // 2)
        crop_x, crop_y, crop_w, crop_h = _clip_rect(
            center_x - (standard_size // 2),
            center_y - (standard_size // 2),
            standard_size,
            standard_size,
            screen_w,
            screen_h,
        )
        select_padding = 1
        select_x, select_y, select_w, select_h = _clip_rect(
            crop_x - select_padding,
            crop_y - select_padding,
            crop_w + (select_padding * 2),
            crop_h + (select_padding * 2),
            screen_w,
            screen_h,
        )
        regions.append(
            {
                "selectX": select_x,
                "selectY": select_y,
                "selectW": select_w,
                "selectH": select_h,
                "cropX": crop_x,
                "cropY": crop_y,
                "cropW": crop_w,
                "cropH": crop_h,
            }
        )
    regions.sort(key=lambda item: (item["selectY"], item["selectX"]))
    return regions[:limit], f"Select an item. {len(regions[:limit])} candidates found."


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
