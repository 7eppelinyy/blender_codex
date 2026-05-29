import json
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


def get_api_config():
    """Read API settings from Blender add-on preferences."""
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


def call_codex(prompt: str, history: list[dict] | None = None) -> tuple[str, str | None]:
    """Send a prompt to the OpenAI API and return (code, error_message).

    Returns:
        (code_str, None) on success, or ("", error_str) on failure.
    """
    api_key, model, max_tokens, temperature, api_base = get_api_config()

    if not api_key:
        return "", "Please set your OpenAI API key in add-on preferences."

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})

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
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
            msg = detail.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        return "", f"HTTP {e.code}: {msg}"
    except urllib.error.URLError as e:
        return "", f"Network error: {e.reason}"
    except Exception as e:
        return "", f"Unexpected error: {e}"

    try:
        code = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        return "", f"Unexpected API response format: {e}"

    code = _strip_markdown_fences(code)
    return code, None


def _strip_markdown_fences(text: str) -> str:
    """Remove ```python ... ``` wrappers if the model outputs them anyway."""
    text = text.strip()
    for prefix in ("```python", "```py", "```"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    if text.endswith("```"):
        text = text[:-3].strip()
    return text
