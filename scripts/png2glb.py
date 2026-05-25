#!/usr/bin/env python
import argparse
import os
import numpy as np
import trimesh
from PIL import Image
from pathlib import Path

def convert_depth_to_glb(input_path: str, output_path: str, z_scale: float = 0.15, pixel_size: float = 1.0, invert: bool = False, downsample: int = 1):
    """
    Reads a 2D PNG depth map and extrudes it into a 3D mesh exported as a GLB file.
    """
    # 1. Load the depth map PNG [cite: 94]
    if not Path(input_path).exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
        
    img = Image.open(input_path)
    
    if downsample > 1:
        img = img.resize((img.width // downsample, img.height // downsample), Image.Resampling.LANCZOS)

    if img.mode == 'I;16' or img.mode == 'I' or img.mode.startswith('I;16'):
        depth_data = np.array(img, dtype=np.float32)
        max_val = 65535.0
    else:
        img = img.convert('L')
        depth_data = np.array(img, dtype=np.float32)
        max_val = 255.0

    # 2. Handle depth inversion if white represents far instead of near [cite: 76]
    if invert:
        depth_data = max_val - depth_data

    # Normalize depth data to a 0.0 - 1.0 range
    depth_data = depth_data / max_val
    
    height, width = depth_data.shape

    # 3. Generate X and Y coordinates mapping to the image grid
    x, y = np.meshgrid(np.arange(width) * pixel_size, np.arange(height) * pixel_size)
    
    # 4. Apply the Z-scale to calculate exact relief depth [cite: 76, 80]
    # We invert Y so the 3D model renders right-side up relative to image coordinates
    # Scale Z proportionally to the max dimension so a z_scale like 0.15 is visible.
    max_dim = max(width, height) * pixel_size
    z = depth_data * (z_scale * max_dim)
    vertices = np.column_stack((x.flatten(), -y.flatten(), z.flatten()))

    # 5. Triangulate the grid to create mesh faces
    idx = np.arange(height * width).reshape(height, width)
    
    # Define corners for each pixel block
    top_left = idx[:-1, :-1].flatten()
    top_right = idx[:-1, 1:].flatten()
    bottom_left = idx[1:, :-1].flatten()
    bottom_right = idx[1:, 1:].flatten()

    # Form two triangles per pixel square
    faces1 = np.column_stack((top_left, top_right, bottom_left))
    faces2 = np.column_stack((top_right, bottom_right, bottom_left))
    faces = np.vstack((faces1, faces2))

    # 6. Construct the Trimesh object without auto-processing to preserve exact vertices [cite: 82]
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    # 7. Export the optimized mesh as a .glb file [cite: 76, 78]
    mesh.export(output_path)
    print(f"Successfully wrote conversion to {output_path}")
    print(f"Mesh Structure - Vertices: {len(vertices)}, Faces: {len(faces)}")

def main():
    parser = argparse.ArgumentParser(description='Convert depth PNG to mesh and export GLB')
    parser.add_argument('input', help='input depth PNG path')
    parser.add_argument('output', help='output GLB path')
    parser.add_argument('--scale', type=float, default=0.15, help='Z scale (depth units)')
    parser.add_argument('--pixel-size', type=float, default=1.0, help='XY plane scale per pixel')
    parser.add_argument('--invert', action='store_true', help='Invert depth (white->far)')
    parser.add_argument('--downsample', type=int, default=1, help='Downsample factor (e.g. 2 for half size)')
    
    args = parser.parse_args()

    try:
        convert_depth_to_glb(
            input_path=args.input, 
            output_path=args.output, 
            z_scale=args.scale, 
            pixel_size=args.pixel_size,
            invert=args.invert,
            downsample=args.downsample
        )
    except Exception as e:
        print(f"Conversion failed: {e}")
        raise

if __name__ == '__main__':
    main()