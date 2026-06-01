import bpy
from . import ADDON_ID


# ═══════════════════════════════════════════════════════════════
# 模型 → 默认 API 地址映射
# ═══════════════════════════════════════════════════════════════
_MODEL_DEFAULT_URL = {
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

# 提供商类别
def _get_provider(model_id: str) -> str:
    if "/" in model_id or "openrouter" in model_id:
        return "openrouter"
    if model_id.startswith("deepseek-"):
        return "deepseek"
    return "openai"


def _on_model_update(self, context):
    """切换模型时自动切换 API 地址并恢复对应密钥"""
    import json

    model_id = self.model
    old_provider = _get_provider(self._last_model)
    new_provider = _get_provider(model_id)

    # ── 1. 保存当前密钥到旧提供商槽位 ──
    if old_provider and self.api_key.strip():
        try:
            keys = json.loads(self._saved_keys or '{}')
        except json.JSONDecodeError:
            keys = {}
        keys[old_provider] = self.api_key
        self._saved_keys = json.dumps(keys, ensure_ascii=False)

    # ── 2. 保存当前 URL 到旧提供商槽位 ──
    if old_provider and self.api_base.strip():
        try:
            urls = json.loads(self._saved_urls or '{}')
        except json.JSONDecodeError:
            urls = {}
        urls[old_provider] = self.api_base
        self._saved_urls = json.dumps(urls, ensure_ascii=False)

    # ── 3. 切换 URL ──
    try:
        urls = json.loads(self._saved_urls or '{}')
    except json.JSONDecodeError:
        urls = {}
    saved_url = urls.get(new_provider)
    if saved_url:
        self.api_base = saved_url
    else:
        default_url = _MODEL_DEFAULT_URL.get(model_id)
        if default_url:
            self.api_base = default_url

    # ── 4. 恢复新提供商的密钥 ──
    try:
        keys = json.loads(self._saved_keys or '{}')
    except json.JSONDecodeError:
        keys = {}
    saved_key = keys.get(new_provider)
    if saved_key:
        self.api_key = saved_key

    # ── 5. 记录切换 ──
    self._last_model = model_id


class CodexPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    # ─── 用户可见的设置 ───────────────────────────────
    api_key: bpy.props.StringProperty(
        name="API 密钥",
        subtype="PASSWORD",
        description="填入你的 API 密钥（切换提供商会自动恢复之前填的key）",
    )
    model: bpy.props.EnumProperty(
        name="模型",
        items=[
            # OpenAI 直连
            ("gpt-5.5", "GPT-5.5 (OpenAI)", "OpenAI 最新旗舰 → api.openai.com"),
            ("gpt-4o", "GPT-4o (OpenAI)", "快速强大 → api.openai.com"),
            # OpenRouter 路由
            ("openai/gpt-5.5", "GPT-5.5 (OpenRouter)", "OpenRouter → openrouter.ai"),
            ("openai/gpt-4o", "GPT-4o (OpenRouter)", "OpenRouter → openrouter.ai"),
            ("anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6 (OpenRouter)", "Anthropic 快速 → openrouter.ai"),
            ("anthropic/claude-opus-4-8", "Claude Opus 4.8 (OpenRouter)", "Anthropic 最强 → openrouter.ai"),
            # DeepSeek
            ("deepseek/deepseek-chat", "DeepSeek-V3 (OpenRouter)", "OpenRouter → openrouter.ai"),
            ("deepseek-v4-pro", "DeepSeek-V4 Pro", "DeepSeek 直连 → api.deepseek.com"),
            ("deepseek-chat", "DeepSeek-V3", "DeepSeek 直连 → api.deepseek.com"),
        ],
        default="deepseek-v4-pro",
        description="选择模型 — API 地址和密钥会自动切换",
        update=_on_model_update,
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
        description="兼容 OpenAI 协议的 API 端点（切换模型时自动更新）",
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

    # ─── 内部存储（Hidden 表示不显示在 UI，但会存盘）───
    _last_model: bpy.props.StringProperty(
        default="deepseek-v4-pro",
        options={'HIDDEN'},
    )
    _saved_keys: bpy.props.StringProperty(
        default='{}',
        options={'HIDDEN'},
        description="JSON dict: provider → api_key",
    )
    _saved_urls: bpy.props.StringProperty(
        default='{}',
        options={'HIDDEN'},
        description="JSON dict: provider → api_base",
    )

    # ─── UI ──────────────────────────────────────────
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

        # 显示当前提供商
        provider = _get_provider(self.model)
        names = {"openai": "OpenAI 直连", "openrouter": "OpenRouter", "deepseek": "DeepSeek 直连"}
        layout.label(text=f"当前提供商: {names.get(provider, '未知')}", icon="URL")

        layout.separator()
        box = layout.box()
        box.label(text="设置指南", icon="INFO")
        col = box.column(align=True)
        col.label(text="切换模型时 API 地址和密钥会自动切换")
        col.label(text="每个提供商的密钥会分别记住")
        col.separator()
        col.label(text="OpenAI：platform.openai.com → API Keys")
        col.label(text="OpenRouter：openrouter.ai → API Keys")
        col.label(text="DeepSeek：platform.deepseek.com → API Keys")


def register():
    if not hasattr(bpy.types, CodexPreferences.__name__):
        bpy.utils.register_class(CodexPreferences)


def unregister():
    try:
        bpy.utils.unregister_class(CodexPreferences)
    except Exception as e:
        print(f"[Codex] 注销 preferences 失败: {e}")
