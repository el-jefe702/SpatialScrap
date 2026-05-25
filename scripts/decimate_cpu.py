"""Standalone CPU-only decimation sandbox.

Usage (example):
  python scripts/decimate_cpu.py "C:\\Users\\jeff\\Desktop\\highpoly.obj" "C:\\Users\\jeff\\Desktop\\highpoly_decimated.obj" --reduction-ratio 0.9

This script prefers `open3d` for decimation (quadric), and falls back to `trimesh` if open3d is unavailable.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

import numpy as np

try:
    import open3d as o3d
except Exception:  # pragma: no cover - handled at runtime
    o3d = None

import trimesh


def load_mesh(path: str):
    """Load a triangle mesh using Open3D if available, else trimesh."""
    if o3d is not None:
        mesh = o3d.io.read_triangle_mesh(path)
        if mesh is not None and len(np.asarray(mesh.triangles)) > 0:
            return mesh

    # fallback to trimesh
    t = trimesh.load(path, force='mesh')
    if t.is_empty:
        raise RuntimeError(f"Failed to load mesh: {path}")
    return t


def open3d_to_trimesh(mesh_o3d: "o3d.geometry.TriangleMesh") -> trimesh.Trimesh:
    verts = np.asarray(mesh_o3d.vertices)
    faces = np.asarray(mesh_o3d.triangles)
    return trimesh.Trimesh(vertices=verts, faces=faces, process=False)


def trimesh_to_open3d(tmesh: trimesh.Trimesh) -> Optional["o3d.geometry.TriangleMesh"]:
    if o3d is None:
        return None
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(tmesh.vertices)
    mesh.triangles = o3d.utility.Vector3iVector(tmesh.faces)
    return mesh


def decimate_with_open3d(mesh: "o3d.geometry.TriangleMesh", target_triangles: int):
    mesh_s = mesh.simplify_quadric_decimation(target_triangles)
    mesh_s.compute_vertex_normals()
    return mesh_s


def decimate_with_trimesh(tmesh: trimesh.Trimesh, target_triangles: int):
    # Prefer trimesh's quadratic decimation if available
    if hasattr(tmesh, 'simplify_quadratic_decimation'):
        try:
            return tmesh.simplify_quadratic_decimation(target_triangles)
        except Exception:
            # fall through to simple fallback
            pass

    # Simple deterministic fallback: uniformly sample faces to reach the target.
    faces = tmesh.faces
    n_faces = faces.shape[0]
    if target_triangles >= n_faces:
        return tmesh

    # pick evenly spaced face indices to keep a representative subset
    indices = (np.linspace(0, n_faces - 1, num=target_triangles).astype(int))
    sampled = faces[indices]

    # remap vertex indices to a compact vertex list
    unique_vertices, inverse = np.unique(sampled, return_inverse=True)
    verts = tmesh.vertices[unique_vertices]
    new_faces = inverse.reshape(sampled.shape)

    return trimesh.Trimesh(vertices=verts, faces=new_faces, process=False)


def export_mesh(mesh, out_path: str):
    ext = os.path.splitext(out_path)[1].lower()
    if o3d is not None and isinstance(mesh, o3d.geometry.TriangleMesh):
        # prefer open3d write for common formats
        ok = o3d.io.write_triangle_mesh(out_path, mesh, write_triangle_uvs=True)
        if not ok:
            raise RuntimeError(f"Open3D failed to write mesh to {out_path}")
        return

    # if it's a trimesh or we don't have open3d
    if isinstance(mesh, trimesh.Trimesh):
        mesh.export(out_path)
        return

    # try to convert open3d -> trimesh
    if o3d is not None and hasattr(mesh, 'triangles'):
        t = open3d_to_trimesh(mesh)
        t.export(out_path)
        return

    raise RuntimeError("Unsupported mesh object for export")


def main(argv=None):
    parser = argparse.ArgumentParser(description="CPU-only mesh decimation sandbox")
    parser.add_argument('input', help='Path to high-poly mesh')
    parser.add_argument('output', help='Path to write decimated mesh')
    parser.add_argument('--target-triangles', type=int, default=None, help='Target triangle count')
    parser.add_argument('--reduction-ratio', type=float, default=0.75, help='Keep (1-ratio) portion of triangles')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args(argv)

    # Load
    print('Loading', args.input)
    mesh = load_mesh(args.input)

    # Determine current triangle count
    if o3d is not None and isinstance(mesh, o3d.geometry.TriangleMesh):
        curr = int(len(np.asarray(mesh.triangles)))
    elif isinstance(mesh, trimesh.Trimesh):
        curr = int(mesh.faces.shape[0])
    else:
        # try to introspect
        try:
            curr = int(len(mesh.faces))
        except Exception:
            curr = 0

    print('Current triangles:', curr)

    # Compute target
    if args.target_triangles is not None:
        target = args.target_triangles
    else:
        target = max(10, int(curr * max(0.01, 1.0 - args.reduction_ratio)))

    print('Target triangles:', target)

    # Decimate using Open3D if possible
    if o3d is not None and isinstance(mesh, o3d.geometry.TriangleMesh):
        print('Decimating with Open3D...')
        dec = decimate_with_open3d(mesh, target)
    elif isinstance(mesh, trimesh.Trimesh):
        print('Decimating with trimesh...')
        dec = decimate_with_trimesh(mesh, target)
    else:
        # try converting
        if o3d is not None:
            tmesh = open3d_to_trimesh(mesh) if hasattr(mesh, 'triangles') else None
        else:
            tmesh = mesh if isinstance(mesh, trimesh.Trimesh) else None

        if tmesh is not None:
            dec = decimate_with_trimesh(tmesh, target)
        else:
            raise RuntimeError('No decimation path available')

    # Export
    print('Exporting to', args.output)
    export_mesh(dec, args.output)
    print('Done')


if __name__ == '__main__':
    main()
