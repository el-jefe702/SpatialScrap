import argparse
import sys
from .processor import SpatialScrapProcessor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Decimate CNC meshes or depth maps, bake relief shadows, and export GLB for spatial computing."
    )
    parser.add_argument("input_path", help="Path to the source mesh or depth map")
    parser.add_argument("output_path", help="Path to the generated GLB file")
    parser.add_argument(
        "--target-triangles",
        type=int,
        default=None,
        help="Target triangle count after decimation",
    )
    parser.add_argument(
        "--reduction-ratio",
        type=float,
        default=0.75,
        help="Decimation reduction ratio (0.0-1.0, where 0.75 keeps 25%% of triangles)",
    )
    parser.add_argument(
        "--depth-scale",
        type=float,
        default=1.0,
        help="Scale factor for 16-bit depth map heights",
    )
    parser.add_argument(
        "--depth-downsample",
        type=int,
        default=1,
        help="Downsample the depth map before mesh conversion",
    )
    parser.add_argument(
        "--depth-pixel-size",
        type=float,
        default=1.0,
        help="Distance between depth map samples in XY units",
    )
    parser.add_argument(
        "--depth-invert",
        action="store_true",
        help="Invert depth values when building the mesh",
    )
    parser.add_argument(
        "--depth-smooth-passes",
        type=int,
        default=0,
        help="Laplacian smoothing passes for depth-mesh conversion",
    )
    parser.add_argument(
        "--bake",
        action="store_true",
        help="Bake relief shadow data into the mesh",
    )
    parser.add_argument(
        "--no-blender",
        action="store_true",
        help="Disable Blender-driven baking/export. Blender API is preferred by default if available.",
    )
    parser.add_argument(
        "--blender",
        default=None,
        help="Explicit Blender executable path when using Blender API",
    )
    parser.add_argument(
        "--blender-bake-size",
        type=int,
        default=2048,
        help="Texture resolution for Blender relief bake",
    )
    parser.add_argument(
        "--blender-bake-samples",
        type=int,
        default=64,
        help="Cycle sample count for Blender relief bake",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    processor = SpatialScrapProcessor(
        blender_executable=args.blender,
        target_triangles=args.target_triangles,
        reduction_ratio=args.reduction_ratio,
        bake_relief=args.bake,
        use_blender=not args.no_blender,
        blender_bake_size=args.blender_bake_size,
        blender_bake_samples=args.blender_bake_samples,
        depth_z_scale=args.depth_scale,
        depth_downsample=args.depth_downsample,
        depth_pixel_size=args.depth_pixel_size,
        depth_invert=args.depth_invert,
        depth_smooth_passes=args.depth_smooth_passes,
        verbose=args.verbose,
    )

    processor.process(args.input_path, args.output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
