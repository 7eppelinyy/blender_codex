import os
import time
import threading
import bpy
from . import codex_client
from .codex_client import _fix_api_compat

CODE_HISTORY: list[dict] = []
LAST_CODE: str = ""

TEXT_NAME = "codex_output.py"

_worker: threading.Thread | None = None
_worker_result: tuple[str, str] | None = None
_request_start_time: float = 0

WORKER_CHECK_INTERVAL = 0.3
API_TIMEOUT_ESTIMATE = 48.0


def _write_to_text_editor(code: str):
    """Create or update the code text block in Blender's Text Editor."""
    try:
        text = bpy.data.texts.get(TEXT_NAME)
        if text is None:
            text = bpy.data.texts.new(TEXT_NAME)
        text.clear()
        text.write(code)
    except Exception:
        pass


def _do_request(prompt: str, image_path: str, history: list[dict] | None):
    global _worker_result
    if image_path:
        code, error = codex_client.call_codex_vision(image_path, prompt)
    else:
        code, error = codex_client.call_codex(prompt, history)
    _worker_result = (code or "", error or "")


def _tag_redraw_all():
    """Request redraw of all 3D View areas so the panel progress bar updates."""
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except Exception:
        pass


def _check_worker():
    global _worker, _worker_result, LAST_CODE, CODE_HISTORY

    if _worker is not None and _worker.is_alive():
        try:
            elapsed = time.time() - _request_start_time
            progress = min(elapsed / API_TIMEOUT_ESTIMATE, 0.92)
            scene = bpy.context.scene
            scene.codex_progress = progress
            scene.codex_elapsed = int(elapsed)
            _tag_redraw_all()
        except Exception:
            pass
        return WORKER_CHECK_INTERVAL

    result = _worker_result
    _worker = None
    _worker_result = None

    try:
        scene = bpy.context.scene
        scene.codex_loading = False

        if result is None:
            scene.codex_status = "错误：未获取到 API 返回结果。"
            _tag_redraw_all()
            return None

        code, error = result
        if error:
            scene.codex_status = f"错误：{error}"
            scene.codex_progress = 0.0
            _tag_redraw_all()
            return None

        # 代码生成后立即修正，不等到执行
        if isinstance(code, str) and code:
            import re
            _before = code
            code = code.replace("'Specular'", "'Specular IOR Level'")
            code = code.replace('"Specular"', '"Specular IOR Level"')
            code = re.sub(
                r'^.*(addon_utils\.enable|bpy\.ops\.preferences\.addon_enable).*$',
                r'# [Codex] removed addon_enable call',
                code, flags=re.MULTILINE,
            )
            code = re.sub(
                r'^.*bpy\.ops\.mesh\.primitive_teapot_add.*$',
                r'# [Codex] removed (requires addon)',
                code, flags=re.MULTILINE,
            )
            code = re.sub(
                r'^.*bpy\.ops\.curve\.tree_add.*$',
                r'# [Codex] removed (requires addon)',
                code, flags=re.MULTILINE,
            )
            if code != _before:
                print("[Codex] code patched on arrival", flush=True)
        else:
            print(f"[Codex] WARNING: code is {type(code).__name__}, skipping patch", flush=True)

        LAST_CODE = code
        scene.codex_progress = 1.0
        prompt = scene.codex_prompt.strip() or "(图片识别)"
        CODE_HISTORY.append({"role": "user", "content": prompt})
        CODE_HISTORY.append({"role": "assistant", "content": code})
        _write_to_text_editor(code)
        scene.codex_status = f"完成！生成了 {len(code)} 个字符的代码。"
    except Exception as _e:
        import traceback
        traceback.print_exc()
        print(f"[Codex] _check_worker exception: {_e}", flush=True)
    finally:
        _tag_redraw_all()

    return None


class CODEX_OT_send_prompt(bpy.types.Operator):
    bl_idname = "codex.send_prompt"
    bl_label = "发送到 AI"
    bl_description = "将文字描述（或图片）发送给 AI 生成 Blender 脚本"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        global _worker, _worker_result, _request_start_time
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
        context.scene.codex_progress = 0.0
        context.scene.codex_elapsed = 0
        context.scene.codex_loading = True
        _worker_result = None
        _request_start_time = time.time()

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

        # ═══════════════════════════════════════════════════════════
        # 内联代码修正（Blender 4.2 兼容性）—— 不用任何 import，
        # 纯 str.replace()，绝不会静默失败。
        # ═══════════════════════════════════════════════════════════
        import re
        code = LAST_CODE

        # 1. 废弃 socket 名 → 4.2 新版名称
        #    用最暴力的方式：替换所有带引号的 'Specular' 字符串，
        #    不管它出现在 inputs['Specular']、列表里、还是任何地方。
        #    同时也处理带空格的变体 [ 'Specular' ]。
        code = code.replace("'Specular'", "'Specular IOR Level'")
        code = code.replace('"Specular"', '"Specular IOR Level"')
        code = re.sub(r"\[\s*'Specular'\s*\]", "['Specular IOR Level']", code)
        code = re.sub(r'\[\s*"Specular"\s*\]', '["Specular IOR Level"]', code)

        # 2. 注释掉 addon_enable 调用
        code = re.sub(
            r'^.*(addon_utils\.enable|bpy\.ops\.preferences\.addon_enable).*$',
            r'# [Codex] removed addon enable call',
            code, flags=re.MULTILINE,
        )

        # 3. 注释掉需扩展的操作符
        for banned in (
            'bpy\\.ops\\.mesh\\.primitive_teapot_add',
            'bpy\\.ops\\.curve\\.tree_add',
        ):
            code = re.sub(
                rf'^.*{banned}.*$',
                r'# [Codex] removed (requires addon)',
                code, flags=re.MULTILINE,
            )

        if code != LAST_CODE:
            print("[Codex] inline patch applied!", flush=True)

        # 最终检查：代码里还剩 'Specular' 吗？
        if "'Specular'" in code or '"Specular"' in code:
            import re as _re
            for _i, _line in enumerate(code.split('\n'), 1):
                if _re.search(r"""['"]Specular['"]""", _line) and 'IOR Level' not in _line:
                    print(f"[Codex] WARNING: residual 'Specular' at line {_i}: {_line.strip()}", flush=True)

        LAST_CODE = code

        _write_to_text_editor(LAST_CODE)

        # 先检查语法，给出精确的错误位置
        try:
            compile(LAST_CODE, "<AI脚本>", "exec")
        except SyntaxError as e:
            context.scene.codex_status = f"语法错误: 第 {e.lineno} 行 — {e.msg}"
            self.report({"ERROR"}, f"第 {e.lineno} 行: {e.msg}")
            return {"CANCELLED"}

        namespace = {"bpy": bpy, "__builtins__": __builtins__}
        try:
            exec(LAST_CODE, namespace)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[Codex] EXEC ERROR:\n{tb}", flush=True)
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


class CODEX_OT_open_text(bpy.types.Operator):
    bl_idname = "codex.open_text"
    bl_label = "在文本编辑器中查看"
    bl_description = "在 Blender 文本编辑器中打开生成的代码"
    bl_options = {"REGISTER"}

    def execute(self, context):
        text = bpy.data.texts.get(TEXT_NAME)
        if text is None:
            context.scene.codex_status = "尚未生成代码。"
            return {"CANCELLED"}

        for area in context.screen.areas:
            if area.type == "TEXT_EDITOR":
                area.spaces.active.text = text
                return {"FINISHED"}

        self.report({"INFO"}, f"代码已保存到 '{TEXT_NAME}'，请手动打开文本编辑器查看。")
        return {"FINISHED"}


classes = (
    CODEX_OT_send_prompt,
    CODEX_OT_execute_code,
    CODEX_OT_clear_history,
    CODEX_OT_copy_code,
    CODEX_OT_clear_image,
    CODEX_OT_open_text,
)


def register():
    for cls in classes:
        if not hasattr(bpy.types, cls.__name__):
            bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[Codex] 注销 {cls.__name__} 失败: {e}")
