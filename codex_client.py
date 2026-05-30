import json
import re
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

    # 直连，跳过系统代理（代理可能干扰 HTTPS 连接）
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)

    last_error = ""
    for attempt in range(3):
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {api_key}")

        try:
            with opener.open(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
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
        except Exception as e:
            import traceback
            traceback.print_exc()
            return "", f"未知错误({type(e).__name__}): {e}"

        if attempt < 2:
            import time
            time.sleep(2)

    return "", f"{last_error}（重试 3 次后仍失败）"

    try:
        code = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        return "", f"API 返回格式异常: {e}"

    code = _strip_markdown_fences(code)
    return code, None


def _search_web(query: str, max_results: int = 5) -> str:
    """Search DuckDuckGo and return formatted results as plain text."""
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": "BlenderCodex/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
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
