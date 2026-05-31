import bpy
from . import ADDON_ID


class CodexPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    api_key: bpy.props.StringProperty(
        name="API 密钥",
        subtype="PASSWORD",
        description="填入你的 API 密钥（OpenAI: sk-… / DeepSeek: sk-…）",
    )
    model: bpy.props.EnumProperty(
        name="模型",
        items=[
            ("gpt-4o", "GPT-4o", "快速、强大，推荐使用"),
            ("gpt-4-turbo", "GPT-4 Turbo", "推理能力强"),
            ("o3-mini", "o3-mini", "轻量推理模型"),
            ("gpt-4.1", "GPT-4.1", "最新旗舰模型"),
            ("deepseek-chat", "DeepSeek-V3", "快速、高性价比"),
            ("deepseek-reasoner", "DeepSeek-R1", "深度推理模型"),
            ("deepseek-v4-pro", "DeepSeek-V4 Pro", "最新旗舰，综合最强"),
        ],
        default="deepseek-v4-pro",
        description="选择用于生成代码的 AI 模型",
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
        col.label(text="DeepSeek：platform.deepseek.com → API Keys")
        col.label(text="将 API 地址设为 https://api.deepseek.com")
        col.label(text="然后在上方粘贴你的密钥即可")


def register():
    if not hasattr(bpy.types, CodexPreferences.__name__):
        bpy.utils.register_class(CodexPreferences)


def unregister():
    try:
        bpy.utils.unregister_class(CodexPreferences)
    except Exception as e:
        print(f"[Codex] 注销 preferences 失败: {e}")
