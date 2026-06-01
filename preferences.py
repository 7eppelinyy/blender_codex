import bpy
from . import ADDON_ID


class CodexPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    api_key: bpy.props.StringProperty(
        name="API 密钥",
        subtype="PASSWORD",
        description="填入你的 API 密钥（OpenAI: sk-… / OpenRouter: sk-or-…）",
    )
    model: bpy.props.EnumProperty(
        name="模型",
        items=[
            # OpenAI 直连
            ("gpt-5.5", "GPT-5.5 (OpenAI)", "OpenAI 最新旗舰"),
            ("gpt-4o", "GPT-4o (OpenAI)", "快速强大"),
            # OpenRouter 路由
            ("openai/gpt-5.5", "GPT-5.5 (OpenRouter)", "OpenRouter 路由"),
            ("openai/gpt-4o", "GPT-4o (OpenRouter)", "OpenRouter 路由"),
            ("anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6 (OpenRouter)", "Anthropic 快速"),
            ("anthropic/claude-opus-4-8", "Claude Opus 4.8 (OpenRouter)", "Anthropic 最强"),
            # DeepSeek
            ("deepseek/deepseek-chat", "DeepSeek-V3 (OpenRouter)", "OpenRouter 路由"),
            ("deepseek-v4-pro", "DeepSeek-V4 Pro", "DeepSeek 直连"),
            ("deepseek-chat", "DeepSeek-V3", "DeepSeek 直连"),
        ],
        default="deepseek-v4-pro",
        description="选择模型（OpenRouter 用户请选带 OpenRouter 后缀的）",
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
        description="兼容 OpenAI 协议的 API 端点（支持代理和镜像站）",
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
        col.prop(self, "proxy")

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
        col.label(text="模型选带 (OpenRouter) 后缀的")
        col.separator()
        col.label(text="DeepSeek：platform.deepseek.com → API Keys")
        col.label(text="API 地址填 https://api.deepseek.com")


def register():
    if not hasattr(bpy.types, CodexPreferences.__name__):
        bpy.utils.register_class(CodexPreferences)


def unregister():
    try:
        bpy.utils.unregister_class(CodexPreferences)
    except Exception as e:
        print(f"[Codex] 注销 preferences 失败: {e}")
