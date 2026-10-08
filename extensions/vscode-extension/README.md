# 💻 VS Code AI Assistant Extension

**Developer:** **Sanjok Subedi**  
**Repository:** [subediSanjok/Chatbot](https://github.com/subediSanjok/Chatbot)

---

## Overview

A native VS Code extension built by **Sanjok Subedi** providing copilot assistance, codebase modification, and diff inspection powered by your local Chatbot AI server.

## Features
- ⚡ **Local LLM Gateway**: Connects to `http://127.0.0.1:1337/v1` without external telemetry.
- 🚀 **Automated Codebase Modification**:
  - **Apply to File**: Writes generated patches directly to targeted workspace files.
  - **Side-by-Side Diff Review**: Review edits side-by-side using VS Code's native diff editor before applying.
  - **Batch Multi-File Patching**: Apply architectural changes across multiple project files simultaneously.
- 📁 **@workspace Scanning**: Context-aware scanning of repository structure for high-precision code completions.
- ⌨️ **Global Shortcut**: Press `Ctrl+Alt+G` (or `Cmd+Alt+G` on macOS) to invoke the AI assistant.
- 🎨 **Embedded Chat Webview**: Live chat panel supporting markdown rendering, syntax highlighting, and inline insertion.

## Installation
1. Start the local server:
   ```powershell
   python -m g4f --port 1337
   ```
2. In VS Code, open this folder (`extensions/vscode-extension`) and press **F5** to run in an Extension Development Host window.
3. Or install permanently by copying this folder to:
   `%USERPROFILE%\.vscode\extensions\g4f-vscode-assistant`

---

**Developed & Maintained by Sanjok Subedi**
