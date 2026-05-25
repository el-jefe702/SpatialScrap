#!/usr/bin/env python
import argparse
import numpy as np
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Convert depth PNG to mesh and export GLB')
    parser.add_argument('input', help='input depth PNG path')
    parser.add_argument('output', help='output GLB path')
    parser.add_argument('--scale', type=float, default=1.0, help='Z scale (depth units)')
    parser.add_argument('--reduction', type=float, default=0.9, help='Fraction of triangles to remove (0-1)')
    parser.add_argument('--invert', action='store_true', help='Invert depth (white->far)')
    args = parser.parse_args()

    try:
        from PIL import Image
    except Exception as e:
        print('Pillow not available:', e)
        raise

    img = Image.open(args.input).convert('L')
    depth = np.array(img).astype(np.float32) / 255.0
    if args.invert:
        depth = 1.0 - depth

    h, w = depth.shape
    # build XY grid centered
    xs = (np.linspace(-0.5, 0.5, w)).astype(np.float32)
    ys = (np.linspace(0.5, -0.5, h)).astype(np.float32)  # flip Y so image top = +y
    xv, yv = np.meshgrid(xs, ys)
    zv = depth * args.scale

    verts = np.stack([xv, yv, zv], axis=-1).reshape(-1, 3)

    # build faces
    faces = []
    def idx(i, j):
        return i * w + j
    for i in range(h - 1):
        for j in range(w - 1):
            a = idx(i, j)
            b = idx(i, j + 1)
            c = idx(i + 1, j)
            d = idx(i + 1, j + 1)
            faces.append([a, c, b])
            faces.append([b, c, d])
    faces = np.array(faces, dtype=np.int64)

    # create mesh and try decimation with Open3D if available
    mesh = None
    try:
        import open3d as o3d
        print('Using Open3D for mesh processing')
        o3d_mesh = o3d.geometry.TriangleMesh()
        o3d_mesh.vertices = o3d.utility.Vector3dVector(verts)
        o3d_mesh.triangles = o3d.utility.Vector3iVector(faces)
        o3d_mesh.compute_vertex_normals()
        target_triangles = max(4, int(len(faces) * (1.0 - args.reduction)))
        print(f'Current triangles: {len(faces)}, target: {target_triangles}')
        dec = o3d_mesh.simplify_quadric_decimation(target_triangles)
        verts = np.asarray(dec.vertices)
        faces = np.asarray(dec.triangles)
        mesh = None
        try:
            import trimesh
            mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
        except Exception:
            pass
    except Exception as e:
        print('Open3D not available or failed:', e)

    if mesh is None:
        try:
            import trimesh
            print('Using Trimesh fallback')
            mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
            # attempt trimesh simplification if available
            target_faces = max(4, int(len(mesh.faces) * (1.0 - args.reduction)))
            if hasattr(mesh, 'simplify_quadratic_decimation'):
                try:
                    mesh = mesh.simplify_quadratic_decimation(target_faces)
                except Exception as e:
                    print('Trimesh decimation failed:', e)
        except Exception as e:
            print('Trimesh not available:', e)
            raise

    # export GLB
    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)
    try:
        mesh.export(outp.as_posix(), file_type='glb')
    except Exception as e:
        print('GLB export via trimesh failed:', e)
        # try pygltflib
        try:
            from pygltflib import GLTF2
            print('pygltflib fallback not implemented')
            raise
        except Exception as e2:
            print('No GLB exporter available:', e2)
            raise

    print('Exported', outp.as_posix())

if __name__ == '__main__':
    main()
