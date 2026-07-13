from dataclasses import dataclass
from .utils import Point2D, bearing, angle_between
from .engine import GeoEngine

@dataclass
class ArtillerySolution:
    """Result of an artillery firing calculation."""
    distance_meters: float
    distance_kilometers: float
    distance_hexes: float
    bearing: float
    angle: float
    dx: float
    dy: float
    aim_x: float = 0.0
    aim_y: float = 0.0

class ArtilleryCalculator:
    """
    Calculates distance, bearing, and angle between a cannon and a target.
    Utilizes GeoEngine for map projection math.
    """
    def __init__(self, engine: GeoEngine = None):
        self.engine = engine or GeoEngine()

    def calculate(self, cannon_pos: tuple[float, float], target_pos: tuple[float, float], wind_direction: float = 0.0, wind_tier: int = 0) -> ArtillerySolution:
        """
        Calculates artillery firing solution with optional wind compensation.
        Input coordinates are expected as (x, y) tuples in World coordinates.
        """
        cannon_pt = Point2D(*cannon_pos)
        target_pt = Point2D(*target_pos)

        # Wind compensation: Target = Aim + Wind => Aim = Target - Wind
        # Wind shift is ~5m per tier in the direction of the wind
        if wind_tier > 0:
            shift_meters = wind_tier * 5.0
            shift_wu = shift_meters / self.engine.world_to_meters_factor
            import math
            # Foxhole Azimuth: 0 is North (Up), 90 is East (Right)
            # Wind direction is where the wind is blowing TO.
            # Convert wind azimuth to math radians
            rad = math.radians(wind_direction - 90)
            # Subtract wind shift vector from target to get aim point
            aim_x = target_pt.x - (shift_wu * math.cos(rad))
            aim_y = target_pt.y - (shift_wu * math.sin(rad))
            target_pt = Point2D(aim_x, aim_y)

        # Basic differences in world coordinates
        dx = target_pt.x - cannon_pt.x
        dy = target_pt.y - cannon_pt.y

        # Distances
        dist_meters = self.engine.distance_meters(cannon_pt, target_pt)
        dist_km = dist_meters / 1000.0
        dist_hex = self.engine.distance_hex(cannon_pt, target_pt)

        # Geometry
        azimuth = bearing(cannon_pt, target_pt)
        ang = angle_between(cannon_pt, target_pt)

        return ArtillerySolution(
            distance_meters=dist_meters,
            distance_kilometers=dist_km,
            distance_hexes=dist_hex,
            bearing=azimuth,
            angle=ang,
            dx=dx,
            dy=dy,
            aim_x=target_pt.x,
            aim_y=target_pt.y
        )
