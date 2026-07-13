import json
import os
import tempfile
import unittest

from controllers.map_controller import build_local_tile_url_cache


class MapControllerLocalTilesTests(unittest.TestCase):
    def test_builds_file_urls_from_tile_index(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.makedirs(os.path.join(tmp_dir, "6"), exist_ok=True)
            tile_path = os.path.join(tmp_dir, "6", "18_0.webp")
            with open(tile_path, "wb") as handle:
                handle.write(b"fake-image")

            with open(os.path.join(tmp_dir, "tile_index.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "6": {
                            "18_0": {
                                "path": "6/18_0.webp",
                                "x": 18,
                                "y": 0,
                            }
                        }
                    },
                    handle,
                )

            cache = build_local_tile_url_cache(tmp_dir)

            self.assertEqual(
                cache[(6, 18, 0)],
                f"file:///{tile_path.replace(chr(92), '/')}",
            )


if __name__ == "__main__":
    unittest.main()
