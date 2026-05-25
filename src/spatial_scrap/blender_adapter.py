import os
import shutil
import subprocess
import tempfile
import textwrap


class BlenderNotFoundError(RuntimeError):
    pass


class BlenderAdapter:
    def __init__(self, blender_executable: str | None = None):
        self.executable = blender_executable or self._find_blender_executable()

    def _find_blender_executable(self) -> str:
        blender_path = shutil.which("blender")
        if blender_path:
            return blender_path

        raise BlenderNotFoundError(
            "Blender executable not found on PATH. Set --blender /path/to/blender if installed."
        )

    def bake_relief(
        self,
        source_path: str,
        output_path: str,
        texture_size: int = 2048,
        samples: int = 64,
    ) -> None:
        script = textwrap.dedent(
            """
            import bpy
            import sys
            import os

            argv = sys.argv
            if "--" not in argv:
                raise RuntimeError("Blender script requires source and output paths after '--'.")

            args = argv[argv.index("--") + 1 :]
            source_path = args[0]
            output_path = args[1]
            texture_size = int(args[2])
            samples = int(args[3])

            bpy.ops.wm.read_factory_settings(use_empty=True)

            bpy.ops.import_scene.obj(filepath=source_path)
            obj = None
            for candidate in bpy.context.selected_objects:
                if candidate.type == "MESH":
                    obj = candidate
                    break
            if obj is None:
                raise RuntimeError("Imported OBJ did not contain a mesh.")

            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.shade_smooth()

            if not obj.data.uv_layers:
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
                bpy.ops.object.mode_set(mode="OBJECT")

            material = bpy.data.materials.new(name="BakeReliefMaterial")
            material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            nodes.clear()

            texture_node = nodes.new(type="ShaderNodeTexImage")
            baked_image = bpy.data.images.new(
                name="BakedRelief", width=texture_size, height=texture_size
            )
            texture_node.image = baked_image
            texture_node.select = True
            nodes.active = texture_node

            diffuse_node = nodes.new(type="ShaderNodeBsdfDiffuse")
            output_node = nodes.new(type="ShaderNodeOutputMaterial")
            links.new(diffuse_node.outputs["BSDF"], output_node.inputs["Surface"])

            obj.data.materials.clear()
            obj.data.materials.append(material)

            scene = bpy.context.scene
            scene.render.engine = "CYCLES"
            scene.cycles.samples = samples
            scene.cycles.use_denoising = False
            scene.render.tile_x = 256
            scene.render.tile_y = 256
            scene.render.image_settings.color_mode = "RGB"
            scene.render.image_settings.color_depth = "8"
            scene.render.image_settings.file_format = "PNG"

            light_data = bpy.data.lights.new(name="ReliefSun", type="SUN")
            light_data.energy = 4.0
            light_object = bpy.data.objects.new(name="ReliefSun", object_data=light_data)
            bpy.context.collection.objects.link(light_object)
            light_object.rotation_euler = (0.7854, 0.0, 0.7854)

            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            bpy.ops.object.bake(
                type="DIFFUSE",
                use_clear=True,
                use_selected_to_active=False,
                use_split_materials=False,
                use_pass_direct=True,
                use_pass_indirect=True,
                use_pass_color=True,
            )

            bpy.ops.export_scene.gltf(
                filepath=output_path,
                export_format="GLB",
                export_apply=True,
                export_materials="EXPORT",
                export_texture_dir="",
                export_selected=False,
            )
            """
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as fh:
            fh.write(script)
            script_path = fh.name

        try:
            subprocess.check_call(
                [
                    self.executable,
                    "--background",
                    "--python",
                    script_path,
                    "--",
                    source_path,
                    output_path,
                    str(texture_size),
                    str(samples),
                ],
                cwd=os.path.dirname(source_path) or None,
            )
        finally:
            try:
                os.remove(script_path)
            except OSError:
                pass
