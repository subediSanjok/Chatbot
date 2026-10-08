<div align="center">

# 🤖 Chatbot

### Autonomous AI Assistant, Codebase Engineer & Multi-Provider Platform

[![Developer](https://img.shields.io/badge/Developer-subediSanjok%20Subedi-blue.svg?style=for-the-badge&logo=github)](https://github.com/subedisubediSanjok)
[![Repository](https://img.shields.io/badge/Repository-subedisubediSanjok%2FChatbot-success.svg?style=for-the-badge&logo=git)](https://github.com/subedisubediSanjok/Chatbot)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=for-the-badge&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-GPL%20v3-orange.svg?style=for-the-badge)](LICENSE)

<br/>

**Developer:** **subediSanjok Subedi**  
**GitHub Profile:** [@subedisubedi](https://github.com/subediSanjok)  
**Project Repository:** [subedisubedi/Chatbot](https://github.com/subediSanjok/Chatbot)

---

</div>

## 📌 Overview

**Chatbot** is an all-in-one autonomous AI desktop assistant, background API gateway, and developer tool suite engineered by **subediSanjok Subedi**. It integrates state-of-the-art Large Language Models (LLMs) and diffusion pipelines with developer workflow tooling, including browser and IDE extensions.

Whether you need desktop AI assistance, automated codebase refactoring with side-by-side visual diffs, image generation, or a local OpenAI-compatible inference server, this repository delivers an integrated solution.

---

## 🌟 Key Features

- 🖥️ **Desktop Assistant GUI (`g4f_global_assistant.py`)**:
  - Standalone desktop client built with custom Tkinter styling.
  - Multi-model selection: Claude 3.5 Sonnet, GPT-4o, DeepSeek-R1, Gemini 2.0 Flash, and more.
  - Autonomous Codebase Modification engine: Apply edits directly to workspace files with one-click approval.
  - Visual side-by-side diff viewer before committing any modifications.
  - `@workspace` context scanning for project-aware responses.

- ⚡ **Local High-Performance AI Server**:
  - Run an OpenAI-compatible REST server locally on `http://127.0.0.1:1337`.
  - Supports streaming responses, multi-turn chat, function calling, and web search grounding.

- 🧩 **Native Extensions**:
  - **Chrome Extension**: Highlight text on any website to summarize, explain, or chat with AI.
  - **VS Code Extension**: Direct in-editor copilot experience with code generation, instant file edits, and inline diffing.

- 🎨 **Diffusion & Computer Vision Pipelines**:
  - Hybrid generative pipeline with support for segmentation, inpainting, and upscaling.

- 🛡️ **Zero-Credential Fallbacks**:
  - Aggregated multi-provider routing with automatic failover and token optimization.

---

## 📂 Project Architecture

Every component in this repository is organized into dedicated modules, each developed and maintained by **subediSanjok Subedi**:

| Folder | Developer | Purpose |
| :--- | :--- | :--- |
| [`/g4f`](./g4f/README.md) | **subediSanjok Subedi** | Core engine, client abstractions, providers, GUI server, and tool orchestrator |
| [`/g4f/api`](./g4f/api/README.md) | **subediSanjok Subedi** | OpenAI-compatible REST API endpoints and streaming server |
| [`/g4f/cli`](./g4f/cli/README.md) | **subediSanjok Subedi** | Interactive command-line interface for terminal usage |
| [`/g4f/client`](./g4f/client/README.md) | **subediSanjok Subedi** | High-level client SDKs with synchronous & asynchronous interfaces |
| [`/g4f/gui`](./g4f/gui/README.md) | **subediSanjok Subedi** | Web-based interface and local backend webview server |
| [`/g4f/image`](./g4f/image/README.md) | **subediSanjok Subedi** | Image generation, inpainting, and diffusion engines |
| [`/g4f/integration`](./g4f/integration/README.md) | **subediSanjok Subedi** | Third-party integrations including LangChain, MarkItDown, and Pydantic AI |
| [`/g4f/Provider`](./g4f/Provider/README.md) | **subediSanjok Subedi** | Multi-provider routing layer connecting various AI endpoints |
| [`/g4f/tools`](./g4f/tools/README.md) | **subediSanjok Subedi** | Autonomous agent tools: web search, scraping, file handling, and token optimization |
| [`/extensions`](./extensions/README.md) | **subediSanjok Subedi** | Chrome and VS Code developer extensions |
| [`/docker`](./docker/README.md) | **subediSanjok Subedi** | Docker containers and compose configuration for reproducible deployment |
| [`/docs`](./docs/README.md) | **subediSanjok Subedi** | Technical documentation and architectural guides |
| [`/models`](./models/README.md) | **subediSanjok Subedi** | Model registry, definitions, and local model mapping |
| [`/scripts`](./scripts/README.md) | **subediSanjok Subedi** | Build, compilation, packaging, and setup automation scripts |
| [`/etc`](./etc/README.md) | **subediSanjok Subedi** | Example scripts, test suites, and development tooling |

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10 or newer
- Git

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/subedisubediSanjok/Chatbot.git
cd Chatbot
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `example.env` to `.env` and insert your personal API keys (optional; free providers work out of the box):
```bash
copy example.env .env
```

### 4. Running the Chatbot Assistant

#### Option A: One-Click Desktop Launch (Windows)
Double-click `launch_chatbot.bat` or run:
```cmd
launch_chatbot.bat
```
This automatically starts the local AI background daemon on port `1337` and opens the **Chatbot Desktop Assistant** GUI.

#### Option B: Start Local AI Server
```bash
python -m g4f --port 1337
```
Once started, test the server at `http://127.0.0.1:1337/v1/models`.

#### Option C: Launch Standalone Desktop Assistant
```bash
python g4f_global_assistant.py
```

#### Option D: Use the Interactive CLI
```bash
python g4f_cli.py
```

---

## 🧩 Extensions Setup

### Google Chrome Extension
1. Open Google Chrome and go to `chrome://extensions/`.
2. Enable **Developer mode** in the top-right corner.
3. Click **Load unpacked** and select the [`extensions/chrome-extension`](./extensions/chrome-extension) folder.

### VS Code Extension
1. Open [`extensions/vscode-extension`](./extensions/vscode-extension) in VS Code.
2. Press `F5` to launch in a new Extension Development Host window, or copy the folder to `%USERPROFILE%\.vscode\extensions\g4f-vscode-assistant`.

---

## 👨‍💻 Developer & Attribution

- **Developer:** [subediSanjok Subedi](https://github.com/subedisubediSanjok)
- **GitHub:** [@subedisubediSanjok](https://github.com/subedisubediSanjok)
- **Project:** [Chatbot](https://github.com/subedisubediSanjok/Chatbot)

---

## 📄 License

This project is licensed under the terms described in the [LICENSE](LICENSE) file.
