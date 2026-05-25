from pathlib import Path
import os
from spatial_scrap.depth_pipeline import DepthMapConverter
import trimesh

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
input_path = Path(WORKSPACE_ROOT) / 'examples' / 'bobs domain.png'
output_path = Path(WORKSPACE_ROOT) / 'examples' / 'bobs_domain_debug_out.glb'

def main():
	conv = DepthMapConverter(z_scale=0.15, downsample=2, pixel_size=1.0, invert_depth=False, smooth_passes=0)
	mesh = conv.convert(str(input_path))
	print('mesh type', type(mesh))
	print('vertices', mesh.vertices.shape)
	print('faces', mesh.faces.shape)
	mesh.export(str(output_path))
	print('wrote', output_path)


if __name__ == '__main__':
	main()
