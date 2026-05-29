import bpy
from . import codex_client

CODE_HISTORY: list[dict] = []
LAST_CODE: str = ""


class CODEX_OT_send_prompt(bpy.types.Operator):
    bl_idname = "codex.send_prompt"
    bl_label = "Send to Codex"
    bl_description = "Generate Blender Python code from your description"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        global LAST_CODE, CODE_HISTORY
        prompt = context.scene.codex_prompt.strip()

        if not prompt:
            context.scene.codex_status = "Please enter a description first."
            return {"CANCELLED"}

        context.scene.codex_status = "Thinking… (this may take a few seconds)"
        self.report({"INFO"}, f"Sending: {prompt[:60]}…")

        code, error = codex_client.call_codex(prompt, CODE_HISTORY[-20:] if CODE_HISTORY else None)

        if error:
            context.scene.codex_status = f"Error: {error}"
            self.report({"ERROR"}, error)
            return {"CANCELLED"}

        LAST_CODE = code
        CODE_HISTORY.append({"role": "user", "content": prompt})
        CODE_HISTORY.append({"role": "assistant", "content": code})

        context.scene.codex_status = f"Done! Generated {len(code)} characters of code."
        self.report({"INFO"}, "Code generated successfully.")
        return {"FINISHED"}


class CODEX_OT_execute_code(bpy.types.Operator):
    bl_idname = "codex.execute_code"
    bl_label = "Execute Generated Code"
    bl_description = "Run the generated script in Blender"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        global LAST_CODE
        if not LAST_CODE.strip():
            context.scene.codex_status = "No code to execute. Generate code first."
            return {"CANCELLED"}

        context.scene.codex_status = "Executing…"

        namespace = {"bpy": bpy, "__builtins__": __builtins__}
        try:
            exec(LAST_CODE, namespace)
        except Exception as e:
            context.scene.codex_status = f"Execution error: {e}"
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        context.scene.codex_status = "Code executed successfully!"
        self.report({"INFO"}, "Script finished.")
        return {"FINISHED"}


class CODEX_OT_clear_history(bpy.types.Operator):
    bl_idname = "codex.clear_history"
    bl_label = "Clear History"
    bl_description = "Clear conversation history and generated code"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        global LAST_CODE, CODE_HISTORY
        LAST_CODE = ""
        CODE_HISTORY.clear()
        context.scene.codex_prompt = ""
        context.scene.codex_status = ""
        self.report({"INFO"}, "Conversation cleared.")
        return {"FINISHED"}


class CODEX_OT_copy_code(bpy.types.Operator):
    bl_idname = "codex.copy_code"
    bl_label = "Copy Code to Clipboard"
    bl_description = "Copy generated code to clipboard"
    bl_options = {"REGISTER"}

    def execute(self, context):
        global LAST_CODE
        if not LAST_CODE:
            return {"CANCELLED"}
        context.window_manager.clipboard = LAST_CODE
        self.report({"INFO"}, "Code copied to clipboard.")
        return {"FINISHED"}


classes = (
    CODEX_OT_send_prompt,
    CODEX_OT_execute_code,
    CODEX_OT_clear_history,
    CODEX_OT_copy_code,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
