# Blender Codex AI Assistant

Natural language to Blender Python scripting — powered by OpenAI's GPT models.

![Blender Version](https://img.shields.io/badge/Blender-4.0%2B-orange)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **Natural Language Input** — Describe what you want to create, Codex writes the Python for you
- **One-Click Execution** — Generated code runs directly inside Blender with a single click
- **Conversation History** — Multi-turn context so you can iterate and refine
- **Clipboard Copy** — Copy generated scripts for manual editing
- **Custom API Endpoint** — Supports OpenAI-compatible proxies and mirrors
- **Zero Dependencies** — Uses only Python stdlib (`urllib`), works with Blender's bundled Python

## Installation

1. Download the latest release `.zip` from [Releases](https://github.com/yourname/blender-codex/releases)
2. In Blender: **Edit → Preferences → Add-ons → Install…**
3. Select the downloaded `.zip` file
4. Enable **"Codex AI Assistant"** in the add-on list

### Manual Install (Development)

```bash
# Clone directly into Blender's add-ons folder
cd "%APPDATA%/Blender Foundation/Blender/<version>/scripts/addons/"
git clone https://github.com/yourname/blender-codex.git
```

Then restart Blender and enable the add-on.

## Setup

1. Go to **Edit → Preferences → Add-ons → Codex AI Assistant → Preferences**
2. Enter your [OpenAI API key](https://platform.openai.com/api-keys)
3. Choose your preferred model (GPT-4o recommended)
4. Optionally set a custom API base for proxies

## Usage

1. In the 3D Viewport, open the sidebar (**N** key)
2. Click the **Codex** tab
3. Type a description like:
   - *"Create a spiral staircase with 20 steps"*
   - *"Add a cube, subdivide it, and apply a displacement modifier"*
   - *"Create a metallic red material and assign it to the selected object"*
   - *"Set up a three-point lighting rig"*
   - *"Generate a particle system that emits glowing spheres"*
4. Click **"Send to Codex"**
5. Review the generated code, then click **"Execute"**

## Supported Models

| Model | Best For |
|-------|----------|
| **GPT-4o** | Fast, capable, recommended default |
| **GPT-4 Turbo** | Complex multi-step scripts |
| **o3-mini** | Quick simple tasks, lower cost |
| **GPT-4.1** | Latest, strongest reasoning |

## Privacy

- Your prompts are sent to OpenAI's API for processing
- No data is stored by this add-on beyond your current session
- Conversation history is held in memory only and cleared on reload

## License

MIT — see [LICENSE](LICENSE)

## Contributing

Issues and PRs welcome! Please open an issue first to discuss what you'd like to change.
