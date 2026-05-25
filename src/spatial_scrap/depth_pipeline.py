import os
from typing import Optional

import numpy as np
import trimesh
from PIL import Image

try:
    import imageio
except ImportError:  # pragma: no cover
    imageio = None

try:
    import pymeshlab
except ImportError:  # pragma: no cover
    pymeshlab = None


class DepthMapConverter:
    DEPTH_EXTENSIONS = {".exr", ".png", ".tiff", ".tif", ".jpg", ".jpeg", ".bmp"}

    def __init__(
        self,
        z_scale: float = 1.0,
        downsample: int = 1,
        pixel_size: float = 1.0,
        invert_depth: bool = False,
        smooth_passes: int = 0,
        normalize_z: bool = True,
    ):
        self.z_scale = z_scale
        self.downsample = max(1, downsample)
        self.pixel_size = pixel_size
        self.invert_depth = invert_depth
        self.smooth_passes = max(0, smooth_passes)
        self.normalize_z = normalize_z

    def convert(self, path: str) -> trimesh.Trimesh:
        depth = self._load_depth_image(path)
        mesh = self._depth_to_mesh(depth)
        if self.smooth_passes > 0:
            mesh = self._smooth_mesh(mesh)
        return mesh

    def _load_depth_image(self, path: str) -> np.ndarray:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".exr":
            if imageio is None:
                raise RuntimeError(
                    "imageio is required to load EXR depth maps. Install with `pip install imageio`."
                )
            image = imageio.v2.imread(path)
        else:
            with Image.open(path) as image_file:
                mode = image_file.mode
                image = np.array(image_file, dtype=np.float32)
                if mode in ('I;16', 'I') or mode.startswith('I;16'):
                    image /= 65535.0
                else:
                    image /= 255.0

        if image.ndim == 3:
            depth = image[..., 0]
        elif image.ndim == 4:
            depth = image[..., 0]
        else:
            depth = image.astype(np.float32)

        if depth.dtype.kind in "iu":
            depth = depth.astype(np.float32) / float(np.iinfo(depth.dtype).max)

        if self.invert_depth:
            depth = 1.0 - depth

        depth = np.clip(depth, 0.0, 1.0) * self.z_scale
        return depth

    def _depth_to_mesh(self, depth: np.ndarray) -> trimesh.Trimesh:
        if self.downsample > 1:
            depth = depth[:: self.downsample, :: self.downsample]

        height, width = depth.shape
        yy, xx = np.meshgrid(np.arange(height, dtype=np.float32), np.arange(width, dtype=np.float32), indexing="ij")
        
        max_dim = max(width, height) * self.pixel_size
        scaled_depth = depth * max_dim
        
        vertices = np.column_stack(
            (
                xx.ravel() * self.pixel_size,
                yy.ravel() * self.pixel_size,
                scaled_depth.ravel(),
            )
        )

        if self.normalize_z:
            vertices[:, 2] -= np.min(vertices[:, 2])

        vertices[:, 0] -= (width - 1) * self.pixel_size * 0.5
        vertices[:, 1] -= (height - 1) * self.pixel_size * 0.5

        faces = []
        for y in range(height - 1):
            for x in range(width - 1):
                base = x + y * width
                faces.append([base, base + width, base + width + 1])
                faces.append([base, base + width + 1, base + 1])
        faces = np.array(faces, dtype=np.int64)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.merge_vertices()
        return mesh

    def _smooth_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        if pymeshlab is None:
            return mesh

        ms = pymeshlab.MeshSet()
        ms.add_mesh(pymeshlab.Mesh(mesh.vertices, mesh.faces), "depth_mesh")
        ms.apply_coord_laplacian_smoothing(stepsmoothnum=self.smooth_passes)
        smoothed = ms.current_mesh()
        return trimesh.Trimesh(
            vertices=smoothed.vertex_matrix(),
            faces=smoothed.face_matrix(),
            process=False,
        )

    @classmethod
    def is_depth_file(cls, path: str) -> bool:
        return os.path.splitext(path)[1].lower() in cls.DEPTH_EXTENSIONS
