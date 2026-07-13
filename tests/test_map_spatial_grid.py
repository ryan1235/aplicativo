import unittest

from controllers.map_spatial_grid import MapSpatialGrid


class MapSpatialGridTests(unittest.TestCase):
    def test_builds_and_filters_by_visible_cells(self):
        grid = MapSpatialGrid(cell_size=64)
        items = [
            {"name": "A", "x": 10, "y": -10},
            {"name": "B", "x": 80, "y": -10},
            {"name": "C", "x": 1000, "y": -1000},
        ]

        grid.build(items)
        visible = grid.get_items_in_viewport(0, 0, 96, 96)

        self.assertEqual([item["name"] for item in visible], ["A", "B"])

    def test_supports_world_coordinates_directly(self):
        grid = MapSpatialGrid(cell_size=128)
        items = [
            {"name": "D", "worldX": 20, "worldY": 40},
            {"name": "E", "worldX": 600, "worldY": 600},
        ]

        grid.build(items)
        visible = grid.get_items_in_viewport(0, 0, 160, 160)

        self.assertEqual([item["name"] for item in visible], ["D"])


if __name__ == "__main__":
    unittest.main()
