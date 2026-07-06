from .engine import GeoEngine
from .utils import Point2D

class ArtilleryRenderer:
    """
    Responsible for converting artillery spatial requirements (meters)
    into Map World Coordinates using GeoEngine.
    """
    def __init__(self, engine: GeoEngine = None):
        self.engine = engine or GeoEngine()

    def meters_to_world_units(self, meters: float) -> float:
        """
        Converts a physical distance in meters to map World Units.
        Uses the engine's configured world_to_meters_factor.
        """
        if self.engine.world_to_meters_factor == 0:
            return 0.0
        return meters / self.engine.world_to_meters_factor

    def calculate_dispersion_meters(self, distance_meters: float, min_range: float, max_range: float,
                                    min_dispersion: float, max_dispersion: float) -> float:
        """
        Calculates the dispersion radius at a specific distance using linear interpolation.
        """
        if max_range <= min_range:
            return max_dispersion
        
        # Clamp distance between min and max range
        clamped_dist = max(min_range, min(distance_meters, max_range))
        
        # Interpolate
        fraction = (clamped_dist - min_range) / (max_range - min_range)
        dispersion = min_dispersion + fraction * (max_dispersion - min_dispersion)
        return dispersion

    def get_overlay_data(self, weapon_info: dict, distance_meters: float) -> dict:
        """
        Returns all overlay radii in World Units for rendering.
        """
        if not weapon_info:
            return {}

        rng = weapon_info.get("range", {})
        min_r = rng.get("minimum", 0)
        max_r = rng.get("maximum", 0)

        disp = weapon_info.get("dispersion", {})
        min_d = disp.get("minimum", 0)
        max_d = disp.get("maximum", 0)

        current_dispersion_meters = self.calculate_dispersion_meters(distance_meters, min_r, max_r, min_d, max_d)

        return {
            "minRangeRadiusWU": self.meters_to_world_units(min_r),
            "maxRangeRadiusWU": self.meters_to_world_units(max_r),
            "dispersionRadiusWU": self.meters_to_world_units(current_dispersion_meters),
            "currentDispersionMeters": current_dispersion_meters,
            "minRangeMeters": min_r,
            "maxRangeMeters": max_r
        }
