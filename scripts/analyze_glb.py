"""Simple GLB analyzer: scans workspace for .glb files and reports structure metrics.

Usage: python scripts/analyze_glb.py
"""
import os
import sys
import json
import struct
from glob import glob

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def read_glb_json(path: str):
    with open(path, "rb") as f:
        header = f.read(12)
        if len(header) < 12:
            raise RuntimeError("Not a valid GLB (header too short)")
        magic, version, length = struct.unpack("<4sII", header)
        if magic != b"glTF":
            raise RuntimeError("Not a GLB file (missing 'glTF' magic)")
        # Read first chunk (JSON)
        chunk_header = f.read(8)
        if len(chunk_header) < 8:
            raise RuntimeError("Missing GLB chunk header")
        chunk_length, chunk_type = struct.unpack("<II", chunk_header)
        chunk_type_bytes = struct.pack("<I", chunk_type)
        # chunk type for JSON is 0x4E4F534A ('JSON')
        json_bytes = f.read(chunk_length)
        try:
            text = json_bytes.decode("utf-8")
            data = json.loads(text)
            return data, version
        except Exception as e:
            raise RuntimeError(f"Failed to parse GLB JSON chunk: {e}")


def analyze_gltf(data: dict):
    out = {}
    out["meshes"] = len(data.get("meshes", []))
    out["nodes"] = len(data.get("nodes", []))
    out["scenes"] = len(data.get("scenes", []))
    out["materials"] = len(data.get("materials", []))
    out["images"] = len(data.get("images", []))
    out["textures"] = len(data.get("textures", []))
    out["bufferViews"] = len(data.get("bufferViews", []))
    out["accessors"] = len(data.get("accessors", []))
    out["buffers"] = len(data.get("buffers", []))

    accessors = data.get("accessors", [])

    def accessor_count(idx):
        if idx is None:
            return 0
        try:
            return int(accessors[idx].get("count", 0))
        except Exception:
            return 0

    total_primitives = 0
    total_triangles = 0
    total_vertices = 0
    for mesh in data.get("meshes", []):
        for prim in mesh.get("primitives", []):
            total_primitives += 1
            mode = prim.get("mode", 4)
            # Only handle triangle primitives (mode 4)
            if mode != 4:
                continue
            idx = prim.get("indices")
            if idx is not None:
                tri_count = accessor_count(idx) // 3
                total_triangles += tri_count
            else:
                pos_idx = None
                attrs = prim.get("attributes", {})
                for k, v in attrs.items():
                    if k.upper() == "POSITION":
                        pos_idx = v
                        break
                if pos_idx is not None:
                    vert_count = accessor_count(pos_idx)
                    total_triangles += vert_count // 3
                    total_vertices += vert_count
    out["primitives"] = total_primitives
    out["triangles_est"] = total_triangles
    out["vertices_est"] = total_vertices

    # Sum declared buffer byteLengths if present
    buffers = data.get("buffers", [])
    out["declared_buffer_bytes"] = sum(int(b.get("byteLength", 0)) for b in buffers)
    return out


def main():
    pattern = os.path.join(WORKSPACE_ROOT, "**", "*.glb")
    files = glob(pattern, recursive=True)
    if not files:
        print("No .glb files found in workspace.")
        return 0

    results = []
    for fpath in sorted(files):
        rel = os.path.relpath(fpath, WORKSPACE_ROOT)
        size = os.path.getsize(fpath)
        try:
            data, version = read_glb_json(fpath)
            stats = analyze_gltf(data)
            stats["version"] = version
            stats["file_size_bytes"] = size
            stats["path"] = rel
            results.append(stats)
        except Exception as e:
            print(f"Failed to analyze {rel}: {e}")

    # Print summary
    for s in results:
        print("---")
        print(f"File: {s['path']}")
        print(f"Size: {s['file_size_bytes']} bytes")
        print(f"glTF version: {s.get('version')}")
        print(f"Meshes: {s.get('meshes')}, Nodes: {s.get('nodes')}, Scenes: {s.get('scenes')}")
        print(f"Materials: {s.get('materials')}, Images: {s.get('images')}, Textures: {s.get('textures')}")
        print(f"Primitives: {s.get('primitives')}, Estimated triangles: {s.get('triangles_est')}")
        print(f"Estimated vertices (from POSITION): {s.get('vertices_est')}")
        print(f"Declared buffer bytes: {s.get('declared_buffer_bytes')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
