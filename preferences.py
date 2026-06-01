import bpy
from . import ADDON_ID


# ═══════════════════════════════════════════════════════════════
# 模型 → 默认 API 地址映射
# ═══════════════════════════════════════════════════════════════
MODEL_DEFAULT_URL = {
    # OpenAI 直连
    "gpt-5.5": "https://api.openai.com/v1",
    "gpt-4o": "https://api.openai.com/v1",
    # OpenRouter 路由
    "openai/gpt-5.5": "https://openrouter.ai/api/v1",
    "openai/gpt-4o": "https://openrouter.ai/api/v1",
    "anthropic/claude-sonnet-4-6": "https://openrouter.ai/api/v1",
    "anthropic/claude-opus-4-8": "https://openrouter.ai/api/v1",
    "deepseek/deepseek-chat": "https://openrouter.ai/api/v1",
    # DeepSeek 直连
    "deepseek-v4-pro": "https://api.deepseek.com",
    "deepseek-chat": "https://api.deepseek.com",
}


def get_provider(model_id: str) -> str:
    """根据模型 ID 判断提供商"""
    if "/" in model_id:
        return "openrouter"
    if model_id.startswith("deepseek-"):
        return "deepseek"
    return "openai"


class CodexPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    api_key: bpy.props.StringProperty(
        name="API 密钥",
        subtype="PASSWORD",
        description="填入你的 API 密钥",
    )
    model: bpy.props.EnumProperty(
        name="模型",
        items=[
            # OpenAI 直连
            ("gpt-5.5", "GPT-5.5 (OpenAI)", "→ api.openai.com"),
            ("gpt-4o", "GPT-4o (OpenAI)", "→ api.openai.com"),
            # OpenRouter 路由
            ("openai/gpt-5.5", "GPT-5.5 (OpenRouter)", "→ openrouter.ai"),
            ("openai/gpt-4o", "GPT-4o (OpenRouter)", "→ openrouter.ai"),
            ("anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6 (OpenRouter)", "→ openrouter.ai"),
            ("anthropic/claude-opus-4-8", "Claude Opus 4.8 (OpenRouter)", "→ openrouter.ai"),
            # DeepSeek
            ("deepseek/deepseek-chat", "DeepSeek-V3 (OpenRouter)", "→ openrouter.ai"),
            ("deepseek-v4-pro", "DeepSeek-V4 Pro", "→ api.deepseek.com"),
            ("deepseek-chat", "DeepSeek-V3", "→ api.deepseek.com"),
        ],
        default="deepseek-v4-pro",
        description="选择模型",
    )
    max_tokens: bpy.props.IntProperty(
        name="最大 Token 数",
        default=4096,
        min=256,
        max=16384,
        description="AI 回复的最大长度（复杂场景建议 4096 以上）",
    )
    temperature: bpy.props.FloatProperty(
        name="温度",
        default=0.3,
        min=0.0,
        max=2.0,
        step=0.1,
        precision=2,
        description="越高越有创意，越低越稳定可靠",
    )
    api_base: bpy.props.StringProperty(
        name="API 地址",
        default="https://api.openai.com/v1",
        description="切换模型后点一下旁边的「自动匹配 URL」按钮即可",
    )
    proxy: bpy.props.StringProperty(
        name="代理地址",
        default="",
        description="HTTP 代理，格式 http://127.0.0.1:7890（留空则使用系统代理）",
    )
    enable_search: bpy.props.BoolProperty(
        name="启用联网搜索",
        default=False,
        description="发送请求前先联网搜索，将结果注入提示词",
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        col = layout.column(heading="API 密钥")
        col.prop(self, "api_key", text="")
        col.prop(self, "api_base")

        # 自动匹配 URL 按钮
        row = col.row(align=True)
        row.prop(self, "proxy")
        default_url = MODEL_DEFAULT_URL.get(self.model)
        if default_url and self.api_base != default_url:
            op = row.operator("codex.auto_url", text="", icon="FILE_REFRESH")
            op.target_url = default_url

        layout.separator()
        layout.prop(self, "model")
        layout.prop(self, "max_tokens", slider=True)
        layout.prop(self, "temperature", slider=True)
        layout.prop(self, "enable_search")

        layout.separator()
        box = layout.box()
        box.label(text="设置指南", icon="INFO")
        col = box.column(align=True)
        col.label(text="OpenAI：platform.openai.com → API Keys")
        col.label(text="API 地址填 https://api.openai.com/v1")
        col.separator()
        col.label(text="OpenRouter：openrouter.ai → API Keys")
        col.label(text="API 地址填 https://openrouter.ai/api/v1")
        col.separator()
        col.label(text="DeepSeek：platform.deepseek.com → API Keys")
        col.label(text="API 地址填 https://api.deepseek.com")


class CODEX_OT_auto_url(bpy.types.Operator):
    """一键匹配当前模型对应的 API 地址"""
    bl_idname = "codex.auto_url"
    bl_label = "自动匹配 URL"
    bl_options = {"INTERNAL"}

    target_url: bpy.props.StringProperty()

    def execute(self, context):
        prefs = context.preferences.addons[ADDON_ID].preferences
        prefs.api_base = self.target_url
        self.report({"INFO"}, f"已切换到 {self.target_url}")
        return {"FINISHED"}


def register():
    if not hasattr(bpy.types, CodexPreferences.__name__):
        bpy.utils.register_class(CodexPreferences)
    if not hasattr(bpy.types, CODEX_OT_auto_url.__name__):
        bpy.utils.register_class(CODEX_OT_auto_url)


def unregister():
    try:
        bpy.utils.unregister_class(CODEX_OT_auto_url)
    except Exception as e:
        print(f"[Codex] 注销 auto_url 失败: {e}")
    try:
        bpy.utils.unregister_class(CodexPreferences)
    except Exception as e:
        print(f"[Codex] 注销 preferences 失败: {e}")
