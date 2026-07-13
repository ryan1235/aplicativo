import math
from typing import Any


class MapSpatialGrid:
    """Spatial hash for map items based on world-space coordinates."""

    def __init__(self, cell_size: float = 1024.0) -> None:
        self.cell_size = float(cell_size)
        self._cells: dict[tuple[int, int], list[Any]] = {}
        self._items: list[Any] = []

    def build(
        self,
        items: list[Any] | None,
        map_scale: float = 1.0,
        map_offset_x: float = 0.0,
        map_offset_y: float = 0.0,
    ) -> "MapSpatialGrid":
        self._cells = {}
        self._items = []

        for item in items or []:
            coords = self._extract_world_coordinates(item)
            if coords is None:
                continue

            world_x, world_y = coords
            if self._uses_explicit_world_coordinates(item):
                world_x = float(world_x)
                world_y = float(world_y)
            else:
                world_x = float(world_x) * 80.0
                world_y = -float(world_y) * 80.0 - 4024.0

            cell_x = int(math.floor(world_x / self.cell_size))
            cell_y = int(math.floor(world_y / self.cell_size))
            self._cells.setdefault((cell_x, cell_y), []).append(item)
            self._items.append(item)

        return self

    def get_items_in_viewport(self, left: float, top: float, right: float, bottom: float) -> list[Any]:
        if right < left:
            left, right = right, left
        if bottom < top:
            top, bottom = bottom, top

        cell_left = int(math.floor(left / self.cell_size))
        cell_right = int(math.floor(right / self.cell_size))
        cell_top = int(math.floor(top / self.cell_size))
        cell_bottom = int(math.floor(bottom / self.cell_size))

        visible_items: list[Any] = []
        seen: set[int] = set()
        for cell_x in range(cell_left, cell_right + 1):
            for cell_y in range(cell_top, cell_bottom + 1):
                for item in self._cells.get((cell_x, cell_y), []):
                    item_id = id(item)
                    if item_id in seen:
                        continue
                    seen.add(item_id)
                    visible_items.append(item)
        return visible_items

    def _extract_world_coordinates(self, item: Any) -> tuple[float, float] | None:
        if not isinstance(item, dict):
            return None

        if self._uses_explicit_world_coordinates(item):
            world_x = item.get("worldX", item.get("world_x"))
            world_y = item.get("worldY", item.get("world_y"))
            try:
                return float(world_x), float(world_y)
            except (TypeError, ValueError):
                return None

        x_value = item.get("x")
        y_value = item.get("y")
        try:
            return float(x_value), float(y_value)
        except (TypeError, ValueError):
            return None

    def _uses_explicit_world_coordinates(self, item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        return ("worldX" in item or "world_x" in item) and ("worldY" in item or "world_y" in item)
