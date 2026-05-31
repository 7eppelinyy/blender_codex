import os
import atexit
import shutil
import pathlib

bl_info = {
    "name": "Codex AI 建模助手",
    "author": "Zeppelin",
    "version": (1, 3, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Codex",
    "description": "AI 驱动的 Blender 建模助手，支持文字描述和图片识别转 3D",
    "category": "3D View",
    "support": "COMMUNITY",
    "tracker_url": "https://github.com/7eppelinyy/blender_codex/issues",
}

ADDON_ID = __package__

import bpy
from . import preferences
from . import operators
from . import panel

modules = (preferences, operators, panel)


def _fix_userpref_once():
    """Complete the failed atomic rename of userpref.blend@ -> userpref.blend.

    MS Store sandbox sometimes prevents Blender from renaming the temp
    file to the final name.  This timer fires once, 2 s after
    registration, and copies the @ file to the real name if needed.
    """
    try:
        config_dir = pathlib.Path(bpy.utils.user_resource('CONFIG'))
        temp_pref = config_dir / "userpref.blend@"
        final_pref = config_dir / "userpref.blend"

        if not temp_pref.exists():
            return None

        if final_pref.exists():
            if temp_pref.stat().st_mtime > final_pref.stat().st_mtime:
                shutil.copy2(str(temp_pref), str(final_pref))
        else:
            shutil.copy2(str(temp_pref), str(final_pref))

        try:
            temp_pref.unlink(missing_ok=True)
        except Exception:
            pass

        print("[Codex] 偏好设置已从临时文件恢复")
    except Exception as e:
        print(f"[Codex] 偏好修复失败: {e}")

    return None


def _persist_preferences():
    """Save user preferences and schedule MS Store workaround."""
    try:
        bpy.ops.wm.save_userpref()
    except Exception:
        pass
    bpy.app.timers.register(_fix_userpref_once, first_interval=2.0)


def _make_atexit_handler(config_dir: str):
    """Factory: capture config_dir while bpy is alive for atexit handler."""
    def _atexit_fix():
        temp_pref = os.path.join(config_dir, "userpref.blend@")
        final_pref = os.path.join(config_dir, "userpref.blend")
        if os.path.isfile(temp_pref):
            try:
                shutil.copy2(temp_pref, final_pref)
                try:
                    os.remove(temp_pref)
                except Exception:
                    pass
            except Exception:
                pass
    return _atexit_fix


def register():
    registered = []
    for mod in modules:
        try:
            mod.register()
            registered.append(mod)
        except Exception as e:
            print(f"[Codex] 注册模块 {mod.__name__} 失败: {e}")
            for m in reversed(registered):
                try:
                    m.unregister()
                except Exception as ue:
                    print(f"[Codex] 回滚注销 {m.__name__} 失败: {ue}")
            raise RuntimeError(
                f"[Codex] 插件注册失败于 {mod.__name__}"
            ) from e

    _persist_preferences()
    config_dir = bpy.utils.user_resource('CONFIG')
    atexit.register(_make_atexit_handler(config_dir))


def unregister():
    for mod in reversed(modules):
        try:
            mod.unregister()
        except Exception as e:
            print(f"[Codex] 注销模块 {mod.__name__} 失败: {e}")
