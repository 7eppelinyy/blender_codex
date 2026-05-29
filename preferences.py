import bpy


class CodexPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    api_key: bpy.props.StringProperty(
        name="API Key",
        subtype="PASSWORD",
        description="OpenAI API key (sk-…)",
    )
    model: bpy.props.EnumProperty(
        name="Model",
        items=[
            ("gpt-4o", "GPT-4o", "Fast, capable, recommended"),
            ("gpt-4-turbo", "GPT-4 Turbo", "Strong reasoning"),
            ("o3-mini", "o3-mini", "Lightweight reasoning model"),
            ("gpt-4.1", "GPT-4.1", "Latest flagship"),
        ],
        default="gpt-4o",
        description="Model used for code generation",
    )
    max_tokens: bpy.props.IntProperty(
        name="Max Tokens",
        default=2048,
        min=256,
        max=16384,
        description="Maximum response length in tokens",
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

        layout.separator()
        box = layout.box()
        box.label(text="How to get an API key", icon="INFO")
        col = box.column(align=True)
        col.label(text="1. Visit platform.openai.com")
        col.label(text="2. Create an account or sign in")
        col.label(text="3. Go to API Keys → Create new secret key")
        col.label(text="4. Copy the key (starts with sk-)")
        col.label(text="5. Paste it above")


def register():
    bpy.utils.register_class(CodexPreferences)


def unregister():
    bpy.utils.unregister_class(CodexPreferences)
