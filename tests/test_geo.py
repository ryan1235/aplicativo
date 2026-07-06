import math
import unittest

from foxmap.geo.utils import Point2D, distance, bearing, angle_between, midpoint, interpolate
from foxmap.geo.engine import GeoEngine
from foxmap.geo.artillery import ArtilleryCalculator
from foxmap.geo.weapons import WeaponRange, StormCannon, Rocket, WeaponRangeStatus
from foxmap.geo.overlay import circle, min_ring, max_ring, bounding_box

class TestGeo(unittest.TestCase):

    def test_utils_distance(self):
        p1 = Point2D(0, 0)
        p2 = Point2D(3, 4)
        self.assertTrue(math.isclose(distance(p1, p2), 5.0))

    def test_utils_bearing(self):
        p1 = Point2D(0, 0)
        self.assertEqual(bearing(p1, Point2D(0, -1)), 0.0)
        self.assertEqual(bearing(p1, Point2D(1, 0)), 90.0)
        self.assertEqual(bearing(p1, Point2D(-1, 0)), 270.0)
        self.assertEqual(bearing(p1, Point2D(0, 1)), 180.0)

    def test_utils_angle_between(self):
        p1 = Point2D(0, 0)
        self.assertEqual(angle_between(p1, Point2D(1, 1)), 45.0)

    def test_utils_midpoint(self):
        self.assertEqual(midpoint(Point2D(0, 0), Point2D(2, 4)), Point2D(1, 2))

    def test_utils_interpolate(self):
        self.assertEqual(interpolate(Point2D(0, 0), Point2D(10, 10), 0.5), Point2D(5, 5))

    def test_engine_conversions(self):
        engine = GeoEngine(scale=2.0, offset_x=10.0, offset_y=10.0, tile_size=256.0)
        world_pt = Point2D(10.0, 10.0)
        
        # World -> Pixel
        pixel_pt = engine.world_to_pixel(world_pt)
        self.assertEqual(pixel_pt, Point2D(40.0, 40.0))
        
        # Pixel -> World
        self.assertEqual(engine.pixel_to_world(pixel_pt), world_pt)
        
        # Pixel -> Tile
        tile_pt = engine.pixel_to_tile(Point2D(256.0, 512.0))
        self.assertEqual(tile_pt, Point2D(1.0, 2.0))
        
        # Tile -> Pixel
        self.assertEqual(engine.tile_to_pixel(tile_pt), Point2D(256.0, 512.0))

    def test_engine_hex_conversions(self):
        engine = GeoEngine(hex_size_meters=2000.0, world_to_meters_factor=38.624867)
        world_pt = Point2D(40.0855, 0)
        hex_pt = engine.world_to_hex(world_pt)
        self.assertTrue(math.isclose(hex_pt.x, 0.774, abs_tol=0.01))
        
        world_back = engine.hex_to_world(hex_pt)
        self.assertTrue(math.isclose(world_back.x, world_pt.x, abs_tol=0.01))

    def test_artillery_calculator(self):
        calc = ArtilleryCalculator()
        cannon = (100.22, -80.55)
        target = (120.15, -115.33)
        solution = calc.calculate(cannon, target)
        
        self.assertTrue(math.isclose(solution.distance_meters, 1548.3, abs_tol=1.0))
        self.assertTrue(math.isclose(solution.distance_kilometers, 1.548, abs_tol=0.01))
        self.assertTrue(math.isclose(solution.distance_hexes, 0.774, abs_tol=0.01))
        self.assertTrue(math.isclose(solution.bearing, 29.8, abs_tol=1.0))
        self.assertTrue(math.isclose(solution.dx, 19.93, abs_tol=0.01))
        self.assertTrue(math.isclose(solution.dy, -34.78, abs_tol=0.01))

    def test_weapon_ranges(self):
        weapon = StormCannon()
        cannon_pt = Point2D(100.22, -80.55)
        target_pt = Point2D(120.15, -115.33)
        
        self.assertFalse(weapon.target_in_range(cannon_pt, target_pt))
        self.assertEqual(weapon.target_out_of_range(cannon_pt, target_pt), WeaponRangeStatus.OUT_OF_RANGE_MAX)
        self.assertEqual(weapon.remaining_distance(cannon_pt, target_pt), 0.0)
        
        target_near = Point2D(100.22, -90.55)
        self.assertFalse(weapon.target_in_range(cannon_pt, target_near))
        self.assertEqual(weapon.target_out_of_range(cannon_pt, target_near), WeaponRangeStatus.OUT_OF_RANGE_MIN)

    def test_overlay_points(self):
        c = circle(Point2D(0, 0), 10.0, 4)
        self.assertTrue(math.isclose(c[0].x, 10.0))
        self.assertTrue(math.isclose(c[0].y, 0.0))
        
        bbox = bounding_box(c)
        self.assertTrue(math.isclose(bbox[0].x, -10.0, abs_tol=0.001))
        self.assertTrue(math.isclose(bbox[1].x, 10.0, abs_tol=0.001))

if __name__ == '__main__':
    unittest.main()
