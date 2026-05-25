"""Convert Bob's domain depth image to GLB using the Python API (no Blender).

Usage: python scripts/convert_bobs_domain.py
"""
from pathlib import Path
from spatial_scrap.processor import SpatialScrapProcessor

input_path = Path('examples') / 'bobs domain.png'
output_path = Path('examples') / 'bobs_domain_out.glb'

proc = SpatialScrapProcessor(use_blender=False, target_triangles=None, reduction_ratio=0.8, bake_relief=False, depth_z_scale=0.15, depth_downsample=2, depth_pixel_size=1.0, depth_invert=False, depth_smooth_passes=1, verbose=True)
try:
	proc.process(str(input_path), str(output_path))
	print(f"Wrote conversion to {output_path}")
except Exception as e:
	print(f"Conversion failed: {e}")
	raise
