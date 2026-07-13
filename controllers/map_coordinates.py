"""Conversão unificada API foxlogi <-> pixels do mapa (malha local ou tiles remotos)."""

from __future__ import annotations

from typing import Any, Callable


def zoom_scale_x(z: int, local_manifest: dict[str, Any] | None, level_width: Callable[[int], float]) -> float:
    if local_manifest is not None:
        w0 = level_width(0)
        wz = level_width(z)
        if w0 > 0:
            return wz / w0
    return float(1 << z)


def zoom_scale_y(z: int, local_manifest: dict[str, Any] | None, level_height: Callable[[int], float]) -> float:
    if local_manifest is not None:
        h0 = level_height(0)
        hz = level_height(z)
        if h0 > 0:
            return hz / h0
    return float(1 << z)


def api_to_world(api_x: float, api_y: float, map_scale: float, offset_x: float, offset_y: float) -> tuple[float, float]:
    return (
        api_x * map_scale + offset_x,
        -api_y * map_scale + offset_y,
    )


def world_to_api(world_x: float, world_y: float, map_scale: float, offset_x: float, offset_y: float) -> tuple[float, float]:
    if map_scale == 0:
        return world_x, world_y
    return (
        (world_x - offset_x) / map_scale,
        -(world_y - offset_y) / map_scale,
    )


def api_to_map_pixels(
    api_x: float,
    api_y: float,
    zoom: int,
    map_scale: float,
    offset_x: float,
    offset_y: float,
    scale_x: float,
    scale_y: float,
) -> tuple[float, float]:
    wx, wy = api_to_world(api_x, api_y, map_scale, offset_x, offset_y)
    return wx * scale_x, wy * scale_y


def map_pixels_to_api(
    px: float,
    py: float,
    zoom: int,
    map_scale: float,
    offset_x: float,
    offset_y: float,
    scale_x: float,
    scale_y: float,
) -> tuple[float, float]:
    if scale_x == 0 or scale_y == 0 or map_scale == 0:
        return px, py
    wx = px / scale_x
    wy = py / scale_y
    return world_to_api(wx, wy, map_scale, offset_x, offset_y)
