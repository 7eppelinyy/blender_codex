import json
import re
import sys
import base64
import urllib.request
import urllib.error
import urllib.parse
from textwrap import dedent

from . import ADDON_ID

SYSTEM_PROMPT = dedent("""\
You are a Blender Python scripting engine. Your ONLY output must be valid, runnable Python code for Blender's `bpy` API.

Rules:
- Output ONLY raw Python code. No markdown fences, no explanations, no commentary.
- Code must be complete and self-contained — import bpy if needed, define variables before use.
- If the user asks for something impossible, output a Python comment explaining why.
- Use `import bpy` at the top of every script.
- Use ONLY ASCII characters. Python does not accept full-width/half-width Unicode punctuation (U+FF00–U+FFEF) like ，。；：（）！？. Every comma must be U+002C, every parenthesis U+0028/U+0029. If you write comments in a non-English language, use English instead.
- NEVER call `addon_utils.enable()` or `bpy.ops.preferences.addon_enable()`.
- NEVER use operators that require third-party or optional addons. The following DO NOT exist in vanilla Blender and MUST NOT be used:
  * bpy.ops.mesh.primitive_teapot_add() — requires "Extra Objects" addon
  * bpy.ops.mesh.primitive_geodesic_dome_add()
  * bpy.ops.mesh.primitive_stepped_cylinder_add()
  * Any other bpy.ops.mesh.primitive_* that is not a standard Blender primitive
- For complex shapes (teapot, dome, etc.), build them from scratch using:
  * bpy.data.meshes.new() + mesh.from_pydata(vertices, edges, faces)
  * bpy.types.Curve + screw modifier for rotational symmetry (ideal for teapot body, cups, vases)
  * Bezier curves for handles, spouts, and decorative elements
  * Standard primitives: bpy.ops.mesh.primitive_cube_add, primitive_uv_sphere_add,
    primitive_cylinder_add, primitive_cone_add, primitive_torus_add,
    primitive_grid_add, primitive_circle_add, primitive_monkey_add, primitive_ico_sphere_add
- If a shape cannot be built with standard primitives and mesh API alone, explain in a comment and build the closest approximation.

Quality requirements:
- ALWAYS clear the default cube before creating anything.
- Use high segment counts for primitives (segments >= 64 for circles/spheres/cylinders).
- Apply `shade_smooth()` on curved objects. Add a BEVEL modifier (segments=3, amount=0.02) and a SUBSURF modifier (levels=2) for smooth, professional results.
- Use Principled BSDF for ALL materials — set base color, roughness (0.3–0.5 unless glossy), metallic where appropriate, and specular.
- Set up proper three-point lighting: one key Area light (200W, warm white), one fill Area light (100W, cool white), one rim/back Area light (150W). Scale lights proportional to scene size.
- Add a ground plane with a subtle material under the subjects.
- Set the World surface to a soft gradient color (use Background node with 0.05–0.15 strength).
- Set up a camera at a flattering angle framing the subject, and set render resolution to 1920x1080 at 100%.
- Use Cycles engine with 128 samples and enable OpenImageDenoise.
- If the user says "render" or "渲染", add `bpy.ops.render.render(write_still=True)` at the end.
- Always include a final `print("Done.")` at the end.
- Keep code concise and readable.
""")

VISION_PROMPT = dedent("""\
You are a Blender Python scripting engine. Analyze the provided image and generate valid Blender Python code to recreate the object, shape, or scene shown.

Rules:
- Output ONLY raw Python code. No markdown fences, no explanations, no commentary.
- Identify the main object in the image and model it using Blender's `bpy` API.
- Code must be complete and self-contained — import bpy if needed.
- Use ONLY ASCII characters. Python does not accept full-width/half-width Unicode punctuation (U+FF00–U+FFEF) like ，。；：（）！？. Every comma must be U+002C, every parenthesis U+0028/U+0029.
- NEVER call `addon_utils.enable()` or `bpy.ops.preferences.addon_enable()`.
- NEVER use operators that require third-party or optional addons (e.g. `bpy.ops.mesh.primitive_teapot_add`). Use only standard Blender primitives + raw mesh API (`from_pydata`, curves + screw modifier, etc.) for complex shapes.

Quality requirements:
- ALWAYS clear the default cube before creating anything.
- Use high segment counts for curved primitives (segments >= 64).
- Apply `shade_smooth()` on curved objects. Add BEVEL (segments=3, amount=0.02) and SUBSURF (levels=2) modifiers for smooth results.
- Match colors from the image using Principled BSDF materials. Set roughness, metallic, and specular appropriately.
- Set up a three-point lighting setup matching the image mood: key Area light (200W), fill Area light (100W), rim/back Area light (150W).
- Add a subtle ground plane or floor.
- Set World surface to a soft dark or neutral background (Background node, strength 0.05–0.15).
- Set up a camera framing the subject at a flattering angle, render resolution 1920x1080 at 100%.
- Use Cycles engine with 128 samples and enable OpenImageDenoise.
- If the user says "render" or "渲染", add `bpy.ops.render.render(write_still=True)` at the end.
- Always include a final `print("Done.")` at the end.
- Keep code concise and readable.
""")


def get_api_config():
    prefs = None
    try:
        import bpy
        prefs = bpy.context.preferences.addons[ADDON_ID].preferences
    except (KeyError, AttributeError, ImportError):
        pass

    if prefs is None:
        return None, None, None, None

    return (
        prefs.api_key,
        prefs.model,
        prefs.max_tokens,
        prefs.temperature,
        prefs.api_base,
    )


def _api_request(messages: list[dict]) -> tuple[str, str | None]:
    """Send messages to API, return (content, error).  Retries on network errors."""
    api_key, model, max_tokens, temperature, api_base = get_api_config()

    if not api_key:
        return "", "请先在偏好设置中填入 API Key。"

    body = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")

    url = f"{api_base.rstrip('/')}/chat/completions"
    print(f"[Codex] 请求: model={model} url={url} key_len={len(api_key)}", flush=True)

    # 直连，跳过系统代理（代理可能干扰 HTTPS 连接）
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)

    last_error = ""
    for attempt in range(3):
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {api_key}")

        try:
            print(f"[Codex] 第 {attempt + 1}/3 次尝试…", flush=True)
            with opener.open(req, timeout=180) as resp:
                print(f"[Codex] HTTP {resp.status}, reading...", flush=True)
                raw = resp.read()
                print(f"[Codex] read {len(raw)} bytes", flush=True)
                data = json.loads(raw.decode("utf-8"))

            print(f"[Codex] choices count: {len(data.get('choices', []))}", flush=True)
            msg = data["choices"][0]["message"]
            print(f"[Codex] msg type: {type(msg).__name__}", flush=True)
            if isinstance(msg, dict):
                for k, v in msg.items():
                    preview = repr(v)[:300] if v else "(empty)"
                    print(f"[Codex]   msg.{k} = {preview}", flush=True)
                print(f"[Codex] msg keys: {list(msg.keys())}", flush=True)
                code = msg.get("content") or msg.get("reasoning_content") or ""
            else:
                code = str(msg)
            print(f"[Codex] chosen code: {repr(code[:200]) if code else '(empty)'}", flush=True)
            code = _strip_markdown_fences(code)
            return code, None
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read().decode("utf-8"))
                msg = detail.get("error", {}).get("message", str(e))
            except Exception:
                msg = str(e)
            return "", f"HTTP {e.code}: {msg}"
        except urllib.error.URLError as e:
            import traceback
            traceback.print_exc()
            last_error = f"网络错误: {e.reason}"
        except OSError as e:
            import traceback
            traceback.print_exc()
            last_error = f"连接失败(errno={e.errno}): {e.strerror or e}"
        except (KeyError, IndexError, TypeError) as e:
            import traceback
            traceback.print_exc()
            return "", f"API 返回格式异常: {e}"
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Codex] 未捕获异常: {type(e).__name__}: {e}", flush=True)
            return "", f"未知错误({type(e).__name__}): {e}"

        if attempt < 2:
            import time
            time.sleep(2)

    return "", f"{last_error}（重试 3 次后仍失败）"


def _search_web(query: str, max_results: int = 5) -> str:
    """Search DuckDuckGo and return formatted results as plain text."""
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": "BlenderCodex/1.0"})
    proxy_handler = urllib.request.ProxyHandler({})
    search_opener = urllib.request.build_opener(proxy_handler)
    try:
        with search_opener.open(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return "（搜索超时或网络错误）"

    # Extract result blocks: each block has a title link and a snippet
    blocks = re.findall(
        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
        r'.*?<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        html, re.DOTALL,
    )
    if not blocks:
        return "（未找到相关搜索结果）"

    lines = []
    for i, (href, title, snippet) in enumerate(blocks[:max_results]):
        href = href.strip()
        title = re.sub(r"<[^>]+>", "", title).strip()
        snippet = re.sub(r"<[^>]+>", "", snippet).strip()
        lines.append(f"[{i + 1}] {title}\n    {snippet}\n    {href}")

    return "\n\n".join(lines)


def _get_search_enabled() -> bool:
    try:
        import bpy
        return bpy.context.preferences.addons[ADDON_ID].preferences.enable_search
    except Exception:
        return False


def call_codex(prompt: str, history: list[dict] | None = None) -> tuple[str, str | None]:
    """Send a text-only prompt."""
    user_content = prompt
    if _get_search_enabled():
        search_results = _search_web(prompt)
        user_content = (
            f"用户请求: {prompt}\n\n"
            f"[联网搜索结果 — 请参考以下信息生成代码]\n{search_results}"
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_content})
    return _api_request(messages)


def call_codex_vision(image_path: str, prompt: str) -> tuple[str, str | None]:
    """Send a prompt with an image for vision-based modeling.

    Reads the image file, encodes as base64, and sends as a
    multi-modal request compatible with GPT-4o / DeepSeek-V4 Pro.
    """
    import mimetypes
    mime, _ = mimetypes.guess_type(image_path)
    if not mime or mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        mime = "image/png"

    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("ascii")

    text = prompt or "请根据这张图片生成 Blender 建模代码。分析图中的物体形状、颜色、材质，并用 bpy 还原。"

    messages = [
        {"role": "system", "content": VISION_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{img_b64}"},
                },
            ],
        },
    ]
    return _api_request(messages)


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    for prefix in ("```python", "```py", "```"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    if text.endswith("```"):
        text = text[:-3].strip()
    return text
