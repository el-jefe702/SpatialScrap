"""Measure and optionally rescale GLB Z-range.

Usage:
  python scripts/adjust_glb_z.py [--target-height FLOAT] [--inplace]

If --target-height is provided, each GLB's Z range (maxZ - minZ) will be scaled
so that the new range equals target height. By default exports to a new file with
"_scaled" suffix unless --inplace is used.
"""
import os
import sys
from glob import glob
import argparse

import trimesh

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def analyze_and_optionally_scale(path: str, target_height: float = None, inplace: bool = False):
    mesh = trimesh.load(path, process=False)
    # If a scene is returned, concatenate geometries into a single mesh
    if isinstance(mesh, trimesh.Scene):
        if mesh.geometry:
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        else:
            print(f"Skipping {path}: empty scene")
            return None
    if not isinstance(mesh, trimesh.Trimesh):
        print(f"Skipping {path}: not a mesh-like glTF")
        return None
    verts = mesh.vertices
    zmin = float(verts[:, 2].min())
    zmax = float(verts[:, 2].max())
    zrange = zmax - zmin
    info = {
        'path': path,
        'zmin': zmin,
        'zmax': zmax,
        'zrange': zrange,
        'vertex_count': len(verts),
    }
    print(f"{os.path.relpath(path, WORKSPACE_ROOT)}: zmin={zmin:.6f}, zmax={zmax:.6f}, zrange={zrange:.6f}, vertices={info['vertex_count']}")

    if target_height is not None and zrange > 0:
        scale = float(target_height) / zrange
        new_verts = verts.copy()
        # Translate so min z becomes 0, scale, then translate back to original min
        new_verts[:, 2] = (new_verts[:, 2] - zmin) * scale + zmin
        mesh.vertices = new_verts
        if inplace:
            out_path = path
        else:
            base, ext = os.path.splitext(path)
            out_path = f"{base}_scaled{ext}"
        mesh.export(out_path)
        print(f"  -> exported scaled file: {os.path.relpath(out_path, WORKSPACE_ROOT)} (scale factor {scale:.6f})")
        info['scaled'] = True
        info['scale'] = scale
        info['out_path'] = out_path
    return info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target-height', type=float, default=None, help='Desired Z range after scaling')
    parser.add_argument('--inplace', action='store_true', help='Overwrite original files')
    args = parser.parse_args()

    pattern = os.path.join(WORKSPACE_ROOT, 'examples', '*.glb')
    files = sorted(glob(pattern))
    if not files:
        print('No .glb files found in examples/')
        return 1

    results = []
    for f in files:
        try:
            info = analyze_and_optionally_scale(f, args.target_height, args.inplace)
            if info:
                results.append(info)
        except Exception as e:
            print(f"Error processing {f}: {e}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
