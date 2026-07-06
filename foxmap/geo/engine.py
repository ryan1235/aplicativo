from dataclasses import dataclass
from .utils import Point2D, distance

@dataclass
class GeoEngine:
    """
    Core engine for Foxhole geospatial math conversions.
    All properties are configurable to adapt to different map extractions.
    """
    scale: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    hex_size_meters: float = 2000.0  # From point to point
    tile_size: float = 256.0
    max_zoom: int = 5
    world_to_meters_factor: float = 88  # Calibrated based on 511m distance

    def world_to_pixel(self, world_pt: Point2D) -> Point2D:
        """Convert a world coordinate to a pixel coordinate on the base zoom level map."""
        px = (world_pt.x + self.offset_x) * self.scale
        py = (world_pt.y + self.offset_y) * self.scale
        return Point2D(px, py)

    def pixel_to_world(self, pixel_pt: Point2D) -> Point2D:
        """Convert a pixel coordinate back to a world coordinate."""
        wx = (pixel_pt.x / self.scale) - self.offset_x
        wy = (pixel_pt.y / self.scale) - self.offset_y
        return Point2D(wx, wy)

    def pixel_to_tile(self, pixel_pt: Point2D) -> Point2D:
        """Convert a pixel coordinate to a tile index coordinate (float)."""
        tx = pixel_pt.x / self.tile_size
        ty = pixel_pt.y / self.tile_size
        return Point2D(tx, ty)

    def tile_to_pixel(self, tile_pt: Point2D) -> Point2D:
        """Convert a tile index coordinate back to a pixel coordinate."""
        px = tile_pt.x * self.tile_size
        py = tile_pt.y * self.tile_size
        return Point2D(px, py)

    def world_to_tile(self, world_pt: Point2D) -> Point2D:
        """Convert a world coordinate to a tile index coordinate."""
        return self.pixel_to_tile(self.world_to_pixel(world_pt))

    def tile_to_world(self, tile_pt: Point2D) -> Point2D:
        """Convert a tile index coordinate back to a world coordinate."""
        return self.pixel_to_world(self.tile_to_pixel(tile_pt))

    def world_to_screen(self, world_pt: Point2D, view_offset: Point2D, zoom: float) -> Point2D:
        """
        Convert a world coordinate to a screen coordinate given a camera view offset and zoom.
        """
        px_pt = self.world_to_pixel(world_pt)
        sx = (px_pt.x - view_offset.x) * zoom
        sy = (px_pt.y - view_offset.y) * zoom
        return Point2D(sx, sy)

    def screen_to_world(self, screen_pt: Point2D, view_offset: Point2D, zoom: float) -> Point2D:
        """
        Convert a screen coordinate to a world coordinate given a camera view offset and zoom.
        """
        px = (screen_pt.x / zoom) + view_offset.x
        py = (screen_pt.y / zoom) + view_offset.y
        return self.pixel_to_world(Point2D(px, py))

    def world_to_hex(self, world_pt: Point2D) -> Point2D:
        """
        Approximation of converting a world point to a hex-grid coordinate.
        Assumes flat-topped or pointy-topped orientation mapped linearly for simplicity,
        or just scaling by hex size in world units.
        """
        hex_size_wu = self.hex_size_meters / self.world_to_meters_factor
        hx = world_pt.x / hex_size_wu
        hy = world_pt.y / hex_size_wu
        return Point2D(hx, hy)

    def hex_to_world(self, hex_pt: Point2D) -> Point2D:
        """Convert a hex-grid coordinate back to world coordinates."""
        hex_size_wu = self.hex_size_meters / self.world_to_meters_factor
        wx = hex_pt.x * hex_size_wu
        wy = hex_pt.y * hex_size_wu
        return Point2D(wx, wy)

    def distance_world(self, p1: Point2D, p2: Point2D) -> float:
        """Calculate distance between two points in world units."""
        return distance(p1, p2)

    def distance_pixels(self, p1: Point2D, p2: Point2D) -> float:
        """Calculate distance between two points in pixels."""
        px1 = self.world_to_pixel(p1)
        px2 = self.world_to_pixel(p2)
        return distance(px1, px2)

    def distance_meters(self, p1: Point2D, p2: Point2D) -> float:
        """Calculate distance between two points in meters."""
        return self.distance_world(p1, p2) * self.world_to_meters_factor

    def distance_hex(self, p1: Point2D, p2: Point2D) -> float:
        """Calculate distance between two points in hexes."""
        return self.distance_meters(p1, p2) / self.hex_size_meters
