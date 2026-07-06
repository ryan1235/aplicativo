import math
from dataclasses import dataclass

@dataclass
class Point2D:
    x: float
    y: float

def distance(p1: Point2D, p2: Point2D) -> float:
    """Calculate the Euclidean distance between two points."""
    return math.hypot(p2.x - p1.x, p2.y - p1.y)

def bearing(p1: Point2D, p2: Point2D) -> float:
    """
    Calculate the bearing (azimuth) from p1 to p2 in degrees.
    North is 0 degrees, clockwise.
    """
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    angle = math.degrees(math.atan2(dx, -dy))
    return (angle + 360) % 360

def angle_between(p1: Point2D, p2: Point2D) -> float:
    """Calculate the mathematical angle between two points in degrees."""
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return math.degrees(math.atan2(dy, dx))

def midpoint(p1: Point2D, p2: Point2D) -> Point2D:
    """Calculate the midpoint between two points."""
    return Point2D((p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0)

def interpolate(p1: Point2D, p2: Point2D, fraction: float) -> Point2D:
    """Interpolate between p1 and p2 by a given fraction (0.0 to 1.0)."""
    return Point2D(
        p1.x + (p2.x - p1.x) * fraction,
        p1.y + (p2.y - p1.y) * fraction
    )
