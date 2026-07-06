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

class ArtilleryCalculator:
    """
    Calculates distance, bearing, and angle between a cannon and a target.
    Utilizes GeoEngine for map projection math.
    """
    def __init__(self, engine: GeoEngine = None):
        self.engine = engine or GeoEngine()

    def calculate(self, cannon_pos: tuple[float, float], target_pos: tuple[float, float]) -> ArtillerySolution:
        """
        Calculates artillery firing solution.
        Input coordinates are expected as (x, y) tuples in World coordinates.
        """
        cannon_pt = Point2D(*cannon_pos)
        target_pt = Point2D(*target_pos)

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
            dy=dy
        )
