import gradio as gr
from pathlib import Path
import tempfile
from spatial_scrap.processor import SpatialScrapProcessor

def process_file(input_file, target_triangles, reduction_ratio, use_blender, bake_relief, depth_scale, depth_downsample, depth_pixel_size, depth_invert, depth_smooth_passes, progress=gr.Progress(track_tqdm=True)):
    if input_file is None:
        return None
    
    # Gradio passes a temporary filepath as a string if we use type="filepath" in gr.File
    # In newer Gradio, gr.File returns a NamedString object if type isn't specified, but we'll use input_file directly if it's a path
    input_path = input_file.name if hasattr(input_file, 'name') else input_file
    
    out_dir = Path(tempfile.gettempdir())
    out_path = out_dir / "output.glb"
    
    def on_progress(msg):
        progress(0, desc=msg)

    try:
        proc = SpatialScrapProcessor(
            target_triangles=int(target_triangles) if target_triangles > 0 else None,
            reduction_ratio=float(reduction_ratio),
            use_blender=bool(use_blender),
            bake_relief=bool(bake_relief),
            depth_z_scale=float(depth_scale),
            depth_downsample=int(depth_downsample),
            depth_pixel_size=float(depth_pixel_size),
            depth_invert=bool(depth_invert),
            depth_smooth_passes=int(depth_smooth_passes),
            verbose=True
        )
        proc.process(str(input_path), str(out_path), progress_callback=on_progress)
        return str(out_path)
    except Exception as e:
        raise gr.Error(f"Processing failed: {str(e)}")

css_code = Path("custom.css").read_text() if Path("custom.css").exists() else ""

with gr.Blocks(title="SpatialScrap", css=css_code) as demo:
    with gr.Column(elem_id="top-slice"):
        gr.Image("Logo.png", interactive=False, show_label=False, container=False, elem_id="logo-img")
        gr.Markdown(
            "<div id='top-slice-text'>\n\n"
            "# SpatialScrap\n"
            "### by SLCreations, LLC\n"
            "Upload a 16-bit depth map (PNG/EXR) or a high-poly dense mesh (OBJ/STL/PLY) to decimate and bake relief shadows into a lightweight `.glb` optimized for spatial computing.\n\n"
            "</div>"
        )
    
    with gr.Row():
        with gr.Column():
            with gr.Group():
                input_file = gr.File(label="Upload Source File")
                
                with gr.Accordion("Decimation Options", open=False):
                    target_triangles = gr.Number(value=0, label="Target Triangles (0 = use reduction ratio instead)", precision=0)
                    reduction_ratio = gr.Slider(minimum=0.01, maximum=1.0, value=0.75, step=0.01, label="Reduction Ratio (e.g. 0.75 keeps 25% of faces)")
                
                with gr.Accordion("Depth Map Parsing Options", open=False):
                    depth_scale = gr.Slider(minimum=0.01, maximum=1.0, value=0.15, step=0.01, label="Depth Scale Extrusion")
                    depth_downsample = gr.Slider(minimum=1, maximum=8, step=1, value=1, label="Downsample Scale (1 = original size)")
                    depth_pixel_size = gr.Number(value=1.0, label="XY Plane Scale Per Pixel")
                    depth_smooth_passes = gr.Slider(minimum=0, maximum=5, step=1, value=1, label="Laplacian Smoothing Passes")
                    depth_invert = gr.Checkbox(value=False, label="Invert Depth (White -> Far)")
                
                with gr.Accordion("Relief Shadow Baking", open=False):
                    use_blender = gr.Checkbox(value=True, label="Enable Blender Engine")
                    bake_relief = gr.Checkbox(value=False, label="Bake High-Res Shadows to Decimated Mesh (Requires Blender)")
                    gr.Markdown("*Note: Baking shadows without a dedicated GPU will fallback to CPU rendering and may take several minutes per file.*")
                    
                process_btn = gr.Button("Generate GLB", variant="primary")
            
            gr.Examples(
                examples=[
                    ["examples/bella.png"],
                    ["examples/bobs.png"]
                ],
                inputs=[input_file],
                label="Try an example file"
            )
            
        with gr.Column():
            output_model = gr.Model3D(label="Output Model Viewer", clear_color=[0,0,0,0])

    process_btn.click(
        fn=process_file,
        inputs=[
            input_file, target_triangles, reduction_ratio, use_blender, bake_relief,
            depth_scale, depth_downsample, depth_pixel_size, depth_invert, depth_smooth_passes
        ],
        outputs=[output_model]
    )

if __name__ == "__main__":
    demo.launch(inbrowser=True, theme=gr.themes.Soft(primary_hue="blue", secondary_hue="indigo"))
