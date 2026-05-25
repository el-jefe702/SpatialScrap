import tempfile
from pathlib import Path
import unittest

import numpy as np
from PIL import Image

from spatial_scrap.depth_pipeline import DepthMapConverter


class DepthPipelineTests(unittest.TestCase):
    def test_convert_png_depth_map(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            depth_path = Path(temp_dir) / "depth_map.png"
            width, height = 64, 64
            depth = np.linspace(0.0, 1.0, num=width * height, dtype=np.float32).reshape((height, width))
            depth_image = (depth * 65535.0).astype(np.uint16)
            Image.fromarray(depth_image, mode="I;16").save(depth_path)

            converter = DepthMapConverter(
                z_scale=1.0,
                downsample=2,
                pixel_size=1.0,
                invert_depth=False,
                smooth_passes=0,
            )
            mesh = converter.convert(str(depth_path))

            self.assertGreater(mesh.vertices.shape[0], 0)
            self.assertGreater(mesh.faces.shape[0], 0)
            self.assertAlmostEqual(mesh.vertices[:, 2].min(), 0.0, places=6)
            self.assertGreater(mesh.vertices[:, 2].max(), 0.0)
            self.assertTrue(DepthMapConverter.is_depth_file(str(depth_path)))


if __name__ == "__main__":
    unittest.main()
