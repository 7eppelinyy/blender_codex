import bpy
from . import ADDON_ID


class CodexPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    api_key: bpy.props.StringProperty(
        name="API Key",
        subtype="PASSWORD",
        description="API key (OpenAI: sk-… / DeepSeek: sk-…)",
    )
    model: bpy.props.EnumProperty(
        name="Model",
        items=[
            ("gpt-4o", "GPT-4o", "Fast, capable, recommended"),
            ("gpt-4-turbo", "GPT-4 Turbo", "Strong reasoning"),
            ("o3-mini", "o3-mini", "Lightweight reasoning model"),
            ("gpt-4.1", "GPT-4.1", "Latest flagship"),
            ("deepseek-chat", "DeepSeek-V3", "Fast, cost-effective"),
            ("deepseek-reasoner", "DeepSeek-R1", "Deep reasoning model"),
            ("deepseek-v4-pro", "DeepSeek-V4 Pro", "Latest flagship, strongest"),
        ],
        default="deepseek-v4-pro",
        description="Model used for code generation",
    )
    max_tokens: bpy.props.IntProperty(
        name="Max Tokens",
        default=4096,
        min=256,
        max=16384,
        description="Maximum response length in tokens (set higher for complex scenes)",
    )
    temperature: bpy.props.FloatProperty(
        name="Temperature",
        default=0.3,
        min=0.0,
        max=2.0,
        step=0.1,
        precision=2,
        description="Higher = more creative, lower = more deterministic",
    )
    api_base: bpy.props.StringProperty(
        name="API Base",
        default="https://api.openai.com/v1",
        description="OpenAI-compatible API endpoint (supports proxies and mirrors)",
    )
    enable_search: bpy.props.BoolProperty(
        name="Enable Web Search",
        default=False,
        description="Search the web and inject results into the prompt before sending to AI",
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        col = layout.column(heading="API Key")
        col.prop(self, "api_key", text="")
        col.prop(self, "api_base")

        layout.separator()
        layout.prop(self, "model")
        layout.prop(self, "max_tokens", slider=True)
        layout.prop(self, "temperature", slider=True)
        layout.prop(self, "enable_search")

        layout.separator()
        box = layout.box()
        box.label(text="Setup Guide", icon="INFO")
        col = box.column(align=True)
        col.label(text="OpenAI: platform.openai.com → API Keys")
        col.label(text="DeepSeek: platform.deepseek.com → API Keys")
        col.label(text="Set API Base to https://api.deepseek.com")
        col.label(text="Then paste your key above")


def register():
    if not hasattr(bpy.types, CodexPreferences.__name__):
        bpy.utils.register_class(CodexPreferences)


def unregister():
    try:
        bpy.utils.unregister_class(CodexPreferences)
    except Exception as e:
        print(f"[Codex] 注销 preferences 失败: {e}")
