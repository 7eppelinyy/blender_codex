bl_info = {
    "name": "Codex AI Assistant",
    "author": "Zeppelin",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Codex",
    "description": "Natural language to Blender Python scripting via OpenAI Codex / GPT",
    "category": "3D View",
    "support": "COMMUNITY",
    "tracker_url": "https://github.com/yourname/blender-codex/issues",
}

import bpy
from . import preferences
from . import operators
from . import panel

modules = (preferences, operators, panel)


def register():
    for mod in modules:
        mod.register()


def unregister():
    for mod in reversed(modules):
        mod.unregister()
