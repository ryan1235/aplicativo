from enum import Enum
from dataclasses import dataclass
from typing import Literal

from .utils import Point2D
from .engine import GeoEngine

class WeaponRangeStatus(Enum):
    IN_RANGE = "in_range"
    OUT_OF_RANGE_MIN = "out_of_range_min"
    OUT_OF_RANGE_MAX = "out_of_range_max"

@dataclass
class WeaponRange:
    """Base class for weapon configurations and range testing."""
    min_range: float
    max_range: float
    engine: GeoEngine = None

    def __post_init__(self):
        if self.engine is None:
            self.engine = GeoEngine()

    def _get_distance(self, cannon_pt: Point2D, target_pt: Point2D) -> float:
        return self.engine.distance_meters(cannon_pt, target_pt)

    def target_in_range(self, cannon_pt: Point2D, target_pt: Point2D) -> bool:
        """Check if target is within the weapon's firing range."""
        dist = self._get_distance(cannon_pt, target_pt)
        return self.min_range <= dist <= self.max_range

    def target_out_of_range(self, cannon_pt: Point2D, target_pt: Point2D) -> WeaponRangeStatus | None:
        """Return the out of range status or None if in range."""
        dist = self._get_distance(cannon_pt, target_pt)
        if dist < self.min_range:
            return WeaponRangeStatus.OUT_OF_RANGE_MIN
        if dist > self.max_range:
            return WeaponRangeStatus.OUT_OF_RANGE_MAX
        return None

    def remaining_distance(self, cannon_pt: Point2D, target_pt: Point2D) -> float:
        """Returns distance left before target is out of max range. 0 if out of range."""
        dist = self._get_distance(cannon_pt, target_pt)
        if dist > self.max_range:
            return 0.0
        return self.max_range - dist

    def distance_to_limit(self, cannon_pt: Point2D, target_pt: Point2D) -> float:
        """
        Returns the absolute distance to the nearest valid range boundary.
        If in range, returns distance to the closest edge (min or max).
        If out of range, returns distance to the edge it crossed.
        """
        dist = self._get_distance(cannon_pt, target_pt)
        if dist < self.min_range:
            return self.min_range - dist
        if dist > self.max_range:
            return dist - self.max_range
        return min(dist - self.min_range, self.max_range - dist)


@dataclass
class StormCannon(WeaponRange):
    """StormCannon specific range profile."""
    min_range: float = 400.0
    max_range: float = 1000.0


@dataclass
class Rocket(WeaponRange):
    """Rocket specific range profile."""
    min_range: float = 100.0
    max_range: float = 250.0
