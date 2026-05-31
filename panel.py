import bpy
from .operators import (
    CODEX_OT_send_prompt,
    CODEX_OT_execute_code,
    CODEX_OT_clear_history,
    CODEX_OT_copy_code,
    CODEX_OT_clear_image,
    CODEX_OT_open_text,
    CODE_HISTORY,
    LAST_CODE,
)


class CODEX_PT_main(bpy.types.Panel):
    bl_label = "Codex AI Assistant"
    bl_idname = "CODEX_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Codex"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # --- Image input ---
        box = layout.box()
        box.label(text="参考图片（可选）", icon="IMAGE_DATA")
        row = box.row(align=True)
        row.prop(scene, "codex_image_path", text="")
        if scene.codex_image_path:
            row.operator(CODEX_OT_clear_image.bl_idname, text="", icon="X")
            box.label(text=f"已选: {scene.codex_image_path}", icon="FILE_IMAGE")

        layout.separator()

        # --- Prompt input ---
        col = layout.column(align=True)
        col.label(text="描述你想创建的内容：", icon="TEXT")
        col.prop(scene, "codex_prompt", text="")
        col.operator(CODEX_OT_send_prompt.bl_idname, icon="EXPORT")

        # --- Generated code ---
        layout.separator()
        row = layout.row()
        row.label(text="生成的脚本", icon="SCRIPT")
        if LAST_CODE:
            row.operator(CODEX_OT_copy_code.bl_idname, text="", icon="COPYDOWN")
            row.operator(CODEX_OT_open_text.bl_idname, text="", icon="TEXT")

        box = layout.box()
        col = box.column(align=True)
        if LAST_CODE:
            lines = LAST_CODE.strip().split("\n")
            display = "\n".join(lines[:40])
            if len(lines) > 40:
                display += f"\n\n…（还有 {len(lines) - 40} 行）"
            for line in display.split("\n"):
                col.label(text=line[:100] or " ")
        else:
            col.label(text="AI 生成的代码将显示在这里。", icon="INFO")

        # --- Execute / Clear ---
        layout.separator()
        row = layout.row(align=True)
        row.operator(CODEX_OT_execute_code.bl_idname, icon="PLAY")
        row.operator(CODEX_OT_clear_history.bl_idname, icon="TRASH")

        # --- Progress / Status ---
        if scene.codex_loading:
            layout.separator()
            box = layout.box()
            box.label(text=f"请求中… 已等待 {scene.codex_elapsed} 秒", icon="SORTTIME")
            col = box.column(align=True)
            col.progress(factor=scene.codex_progress, type="BAR")
            if scene.codex_status:
                col.label(text=scene.codex_status, icon="INFO")

        if scene.codex_status and not scene.codex_loading:
            layout.separator()
            box = layout.box()
            icon = "ERROR" if any(w in scene.codex_status for w in ("Error", "出错", "失败")) else "INFO"
            box.label(text=scene.codex_status, icon=icon)


_scene_props = (
    "codex_prompt", "codex_status", "codex_image_path",
    "codex_progress", "codex_loading", "codex_elapsed",
)


def register():
    if not hasattr(bpy.types.Scene, "codex_prompt"):
        bpy.types.Scene.codex_prompt = bpy.props.StringProperty(
            name="Prompt",
            description="用自然语言描述要创建什么",
            default="",
        )
    if not hasattr(bpy.types.Scene, "codex_status"):
        bpy.types.Scene.codex_status = bpy.props.StringProperty(
            name="Status",
            description="最近一次操作状态",
            default="",
        )
    if not hasattr(bpy.types.Scene, "codex_image_path"):
        bpy.types.Scene.codex_image_path = bpy.props.StringProperty(
            name="图片路径",
            description="可选的参考图片，AI 会识别后建模",
            default="",
            subtype="FILE_PATH",
        )
    if not hasattr(bpy.types.Scene, "codex_progress"):
        bpy.types.Scene.codex_progress = bpy.props.FloatProperty(
            name="进度",
            default=0.0,
            min=0.0,
            max=1.0,
            subtype="FACTOR",
        )
    if not hasattr(bpy.types.Scene, "codex_loading"):
        bpy.types.Scene.codex_loading = bpy.props.BoolProperty(
            name="加载中",
            default=False,
        )
    if not hasattr(bpy.types.Scene, "codex_elapsed"):
        bpy.types.Scene.codex_elapsed = bpy.props.IntProperty(
            name="已过秒数",
            default=0,
        )
    if not hasattr(bpy.types, CODEX_PT_main.__name__):
        bpy.utils.register_class(CODEX_PT_main)


def unregister():
    try:
        bpy.utils.unregister_class(CODEX_PT_main)
    except Exception as e:
        print(f"[Codex] 注销 panel 失败: {e}")
    for prop in _scene_props:
        if hasattr(bpy.types.Scene, prop):
            try:
                delattr(bpy.types.Scene, prop)
            except Exception as e:
                print(f"[Codex] 删除属性 {prop} 失败: {e}")
