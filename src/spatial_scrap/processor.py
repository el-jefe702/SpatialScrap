import logging
import os
import tempfile
from typing import Optional

import numpy as np
import trimesh

try:
    import pymeshlab
except ImportError:  # pragma: no cover
    pymeshlab = None

from .blender_adapter import BlenderAdapter, BlenderNotFoundError
from .depth_pipeline import DepthMapConverter


logger = logging.getLogger(__name__)


class SpatialScrapProcessor:
    def __init__(
        self,
        blender_executable: Optional[str] = None,
        target_triangles: Optional[int] = None,
        reduction_ratio: float = 0.75,
        bake_relief: bool = True,
        use_blender: bool = True,
        blender_bake_size: int = 2048,
        blender_bake_samples: int = 64,
        depth_z_scale: float = 1.0,
        depth_downsample: int = 1,
        depth_pixel_size: float = 1.0,
        depth_invert: bool = False,
        depth_smooth_passes: int = 0,
        verbose: bool = False,
    ):
        self.blender_executable = blender_executable
        self.target_triangles = target_triangles
        self.reduction_ratio = reduction_ratio
        self.bake_relief = bake_relief
        self.use_blender = use_blender
        self.blender_bake_size = blender_bake_size
        self.blender_bake_samples = blender_bake_samples
        self.depth_z_scale = depth_z_scale
        self.depth_downsample = depth_downsample
        self.depth_pixel_size = depth_pixel_size
        self.depth_invert = depth_invert
        self.depth_smooth_passes = depth_smooth_passes
        self.verbose = verbose

        if self.verbose:
            logging.basicConfig(level=logging.INFO)

    def process(self, input_path: str, output_path: str, progress_callback=None) -> None:
        def report(msg):
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        report("Loading input mesh...")
        mesh = self.load_input(input_path)

        report("Decimating mesh...")
        mesh = self.decimate_mesh(mesh)

        if self.bake_relief:
            report("Baking relief shadow data (this may take a few minutes)...")
            mesh = self.bake_relief_shadows(mesh, input_path, output_path)

        report("Exporting GLB...")
        self.export_glb(mesh, output_path)
        report("Export complete!")

    def load_input(self, path: str) -> trimesh.Trimesh:
        suffix = os.path.splitext(path)[1].lower()
        if DepthMapConverter.is_depth_file(path):
            return self.load_depth_map(path)

        mesh = trimesh.load(path, process=False)
        if not isinstance(mesh, trimesh.Trimesh):
            if isinstance(mesh, trimesh.Scene):
                mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
            else:
                raise ValueError(f"Unsupported mesh input type: {type(mesh)}")
        return mesh

    def load_depth_map(self, path: str) -> trimesh.Trimesh:
        converter = DepthMapConverter(
            z_scale=self.depth_z_scale,
            downsample=self.depth_downsample,
            pixel_size=self.depth_pixel_size,
            invert_depth=self.depth_invert,
            smooth_passes=self.depth_smooth_passes,
        )
        return converter.convert(path)

    def decimate_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        target = self.target_triangles
        if target is None:
            target = max(4, int(mesh.faces.shape[0] * max(0.01, 1.0 - self.reduction_ratio)))

        if pymeshlab is not None:
            try:
                ms = pymeshlab.MeshSet()
                ms.add_mesh(pymeshlab.Mesh(mesh.vertices, mesh.faces), "source")
                ms.meshing_decimation_quadric_edge_collapse(
                    targetfacenum=target,
                    preserveboundary=True,
                    preservenormal=True,
                    preservetopology=True,
                )
                simplified = ms.current_mesh()
                return trimesh.Trimesh(
                    vertices=simplified.vertex_matrix(),
                    faces=simplified.face_matrix(),
                    process=False,
                )
            except Exception as error:  # pragma: no cover
                logger.warning("PyMeshLab decimation failed: %s", error)

        if hasattr(mesh, "simplify_quadratic_decimation"):
            try:
                return mesh.simplify_quadratic_decimation(target)
            except Exception as error:
                logger.warning("Trimesh decimation failed: %s", error)

        logger.info("Skipping decimation: unable to simplify automatically")
        return mesh

    def bake_relief_shadows(
        self, mesh: trimesh.Trimesh, input_path: str, output_path: str
    ) -> trimesh.Trimesh:
        if self.use_blender:
            try:
                blender = BlenderAdapter(self.blender_executable)
                with tempfile.TemporaryDirectory() as temp_dir:
                    source = os.path.join(temp_dir, "source.obj")
                    baked = os.path.join(temp_dir, "baked.glb")
                    mesh.export(source, file_type="obj")
                    blender.bake_relief(
                        source,
                        baked,
                        texture_size=self.blender_bake_size,
                        samples=self.blender_bake_samples,
                    )
                    return trimesh.load(baked, process=False)
            except BlenderNotFoundError as error:
                logger.warning("Blender integration unavailable: %s", error)
            except Exception as error:
                logger.warning("Blender relief bake failed: %s", error)

        return self._apply_vertex_shadow_shading(mesh)

    def _apply_vertex_shadow_shading(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        normals = mesh.vertex_normals
        if normals is None or len(normals) == 0:
            mesh.compute_vertex_normals()
            normals = mesh.vertex_normals

        light_dir = np.array([0.35, 0.35, 0.9], dtype=np.float32)
        light_dir /= np.linalg.norm(light_dir)
        shade = np.clip(np.dot(normals, light_dir), 0.0, 1.0)
        shade = 0.25 + 0.75 * shade

        colors = np.vstack([shade, shade, shade, np.ones_like(shade)]).T
        mesh.visual.vertex_colors = (colors * 255).astype(np.uint8)
        return mesh

    def export_glb(self, mesh: trimesh.Trimesh, output_path: str) -> None:
        try:
            mesh.export(output_path, file_type="glb")
        except Exception as error:
            raise RuntimeError(f"GLB export failed: {error}")
