import json
import base64
import urllib.request
import urllib.error
import ssl
from textwrap import dedent

SYSTEM_PROMPT = dedent("""\
You are a Blender Python scripting engine. Your ONLY output must be valid, runnable Python code for Blender's `bpy` API.

Rules:
- Output ONLY raw Python code. No markdown fences, no explanations, no commentary.
- Code must be complete and self-contained — import bpy if needed, define variables before use.
- If the user asks for something impossible, output a Python comment explaining why.
- Use `import bpy` at the top of every script.
- Prefer `bpy.ops` operators for modeling tasks, `bpy.data` / `bpy.context` for data access.
- Always include a final `print("Done.")` at the end so Blender confirms execution.
- Keep code concise and readable.
""")

VISION_PROMPT = dedent("""\
You are a Blender Python scripting engine. Analyze the provided image and generate valid Blender Python code to recreate the object, shape, or scene shown.

Rules:
- Output ONLY raw Python code. No markdown fences, no explanations, no commentary.
- Identify the main object in the image and model it using Blender's `bpy` API.
- Include materials, colors, and lighting if visible.
- Code must be complete and self-contained — import bpy if needed.
- Always include a final `print("Done.")` at the end.
- Keep code concise and readable.
""")


def get_api_config():
    prefs = None
    try:
        import bpy
        prefs = bpy.context.preferences.addons[__package__].preferences
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
    """Send messages to API, return (content, error)."""
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
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
            msg = detail.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        return "", f"HTTP {e.code}: {msg}"
    except urllib.error.URLError as e:
        return "", f"网络错误: {e.reason}"
    except Exception as e:
        return "", f"未知错误: {e}"

    try:
        code = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        return "", f"API 返回格式异常: {e}"

    code = _strip_markdown_fences(code)
    return code, None


def call_codex(prompt: str, history: list[dict] | None = None) -> tuple[str, str | None]:
    """Send a text-only prompt."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})
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
