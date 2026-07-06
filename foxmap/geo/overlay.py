import math
from .utils import Point2D

def _generate_circle_points(center: Point2D, radius: float, num_points: int = 64) -> list[Point2D]:
    """Internal helper to generate points for a circle."""
    points = []
    angle_step = (2 * math.pi) / num_points
    for i in range(num_points):
        angle = i * angle_step
        x = center.x + radius * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        points.append(Point2D(x, y))
    return points

def circle(center: Point2D, radius: float, num_points: int = 64) -> list[Point2D]:
    """
    Generate points forming a circle. 
    Radius should be in the target coordinate space (e.g., world or pixel).
    """
    return _generate_circle_points(center, radius, num_points)

def min_ring(center: Point2D, min_radius: float, num_points: int = 64) -> list[Point2D]:
    """Generate points forming the minimum range ring."""
    return circle(center, min_radius, num_points)

def max_ring(center: Point2D, max_radius: float, num_points: int = 64) -> list[Point2D]:
    """Generate points forming the maximum range ring."""
    return circle(center, max_radius, num_points)

def polygon(points: list[Point2D]) -> list[Point2D]:
    """
    Return the points of a polygon. 
    Can be expanded in the future for triangulation or validation.
    """
    return points

def bounding_box(points: list[Point2D]) -> tuple[Point2D, Point2D]:
    """
    Return the (min_point, max_point) bounding box for a given set of points.
    """
    if not points:
        return Point2D(0.0, 0.0), Point2D(0.0, 0.0)
    
    min_x = min(p.x for p in points)
    min_y = min(p.y for p in points)
    max_x = max(p.x for p in points)
    max_y = max(p.y for p in points)
    
    return Point2D(min_x, min_y), Point2D(max_x, max_y)
