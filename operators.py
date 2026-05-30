import os
import threading
import bpy
from . import codex_client

CODE_HISTORY: list[dict] = []
LAST_CODE: str = ""

_worker: threading.Thread | None = None
_worker_result: tuple[str, str] | None = None

WORKER_CHECK_INTERVAL = 0.3


def _do_request(prompt: str, image_path: str, history: list[dict] | None):
    global _worker_result
    if image_path:
        code, error = codex_client.call_codex_vision(image_path, prompt)
    else:
        code, error = codex_client.call_codex(prompt, history)
    _worker_result = (code or "", error or "")


def _check_worker():
    global _worker, _worker_result, LAST_CODE, CODE_HISTORY

    if _worker is None or _worker.is_alive():
        return WORKER_CHECK_INTERVAL

    result = _worker_result
    _worker = None
    _worker_result = None

    context = bpy.context
    if result is None:
        context.scene.codex_status = "错误：未获取到 API 返回结果。"
        return None

    code, error = result
    if error:
        context.scene.codex_status = f"错误：{error}"
        return None

    LAST_CODE = code
    prompt = context.scene.codex_prompt.strip() or "(图片识别)"
    CODE_HISTORY.append({"role": "user", "content": prompt})
    CODE_HISTORY.append({"role": "assistant", "content": code})
    context.scene.codex_status = f"完成！生成了 {len(code)} 个字符的代码。"
    return None


class CODEX_OT_send_prompt(bpy.types.Operator):
    bl_idname = "codex.send_prompt"
    bl_label = "发送到 AI"
    bl_description = "将文字描述（或图片）发送给 AI 生成 Blender 脚本"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        global _worker, _worker_result
        prompt = context.scene.codex_prompt.strip()
        image_path = context.scene.codex_image_path.strip()

        if not prompt and not image_path:
            context.scene.codex_status = "请输入描述或选择一张参考图片。"
            return {"CANCELLED"}

        if image_path and not os.path.isfile(image_path):
            context.scene.codex_status = f"图片不存在: {image_path}"
            return {"CANCELLED"}

        if _worker is not None and _worker.is_alive():
            context.scene.codex_status = "上一个请求尚未完成，请稍等。"
            return {"CANCELLED"}

        context.scene.codex_status = "正在请求 AI…"
        _worker_result = None

        history = list(CODE_HISTORY[-20:]) if CODE_HISTORY else None
        _worker = threading.Thread(
            target=_do_request,
            args=(prompt, image_path, history),
            daemon=True,
        )
        _worker.start()

        bpy.app.timers.register(_check_worker)
        return {"FINISHED"}


class CODEX_OT_execute_code(bpy.types.Operator):
    bl_idname = "codex.execute_code"
    bl_label = "执行生成脚本"
    bl_description = "在 Blender 中运行生成的脚本"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        global LAST_CODE
        if not LAST_CODE.strip():
            context.scene.codex_status = "尚未生成代码。"
            return {"CANCELLED"}

        context.scene.codex_status = "正在执行…"

        namespace = {"bpy": bpy, "__builtins__": __builtins__}
        try:
            exec(LAST_CODE, namespace)
        except Exception as e:
            context.scene.codex_status = f"执行出错: {e}"
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        context.scene.codex_status = "代码执行完毕！"
        self.report({"INFO"}, "脚本完成。")
        return {"FINISHED"}


class CODEX_OT_clear_history(bpy.types.Operator):
    bl_idname = "codex.clear_history"
    bl_label = "清除历史"
    bl_description = "清除对话历史与生成代码"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        global LAST_CODE, CODE_HISTORY
        LAST_CODE = ""
        CODE_HISTORY.clear()
        context.scene.codex_prompt = ""
        context.scene.codex_image_path = ""
        context.scene.codex_status = ""
        self.report({"INFO"}, "对话已清除。")
        return {"FINISHED"}


class CODEX_OT_copy_code(bpy.types.Operator):
    bl_idname = "codex.copy_code"
    bl_label = "复制代码"
    bl_description = "复制生成的代码到剪贴板"
    bl_options = {"REGISTER"}

    def execute(self, context):
        global LAST_CODE
        if not LAST_CODE:
            return {"CANCELLED"}
        context.window_manager.clipboard = LAST_CODE
        self.report({"INFO"}, "代码已复制。")
        return {"FINISHED"}


class CODEX_OT_clear_image(bpy.types.Operator):
    bl_idname = "codex.clear_image"
    bl_label = "清除图片"
    bl_description = "清除已选择的参考图片"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.scene.codex_image_path = ""
        return {"FINISHED"}


classes = (
    CODEX_OT_send_prompt,
    CODEX_OT_execute_code,
    CODEX_OT_clear_history,
    CODEX_OT_copy_code,
    CODEX_OT_clear_image,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
