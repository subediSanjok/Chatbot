# g4f VS Code AI Assistant Extension

A ready-to-load VS Code Extension connecting your editor directly to your local `g4f` API server.

## Features
- ⚡ **Local LLM Server Integration:** Connects to `http://127.0.0.1:1337/v1` (gpt-4o, claude-3.5-sonnet, deepseek-r1, gemini-2.0-flash, etc.).
- 🚀 **Codex & Claude Code Codebase Implementation:** 
  - **⚡ Apply to File:** Directly writes generated code into the target workspace file with a single click.
  - **⚡ Auto-apply to Codebase:** Toggle on to automatically apply all proposed edits across your project files as soon as the model finishes generating.
  - **🔍 Side-by-Side Diff Review:** Inspect code changes side-by-side in VS Code's native diff editor before applying.
  - **🚀 Batch Workspace Application:** Apply multiple file changes across your codebase in one click.
- 📁 **@workspace Scanning:** Scan key workspace files to give the AI full codebase architecture context.
- ⌨️ **Shortcut:** Press `Ctrl+Alt+G` (or `Cmd+Alt+G` on macOS) to ask AI about your selected code.
- 🖱️ **Editor Right-Click Menu:**
  - **g4f AI: Explain Selected Code**
  - **g4f AI: Refactor & Optimize Code**
  - **g4f AI: Find & Fix Bugs**
  - **g4f AI: Ask Anything / Code Helper**
- 🎨 **Side-by-Side Chat Webview:** Real-time AI chat panel with file badges, one-click diff reviews, and code insertion.

---

## How to Install and Run in VS Code

### Option A: Immediate Testing (Run via Debugger)
1. Open this folder in VS Code:
   `c:\Users\HP\Desktop\chatbot\extensions\vscode-extension`
2. Press **`F5`** on your keyboard (or click **Run -> Start Debugging**).
3. A new **Extension Development Host** window will open with the extension loaded and active!

---

### Option B: Permanent Install to your VS Code
To make the extension permanently available across all your VS Code workspaces without compiling:

1. Copy this folder (`extensions/vscode-extension`) to your VS Code extensions directory:
   - **Windows:** `%USERPROFILE%\.vscode\extensions\g4f-vscode-assistant`
   ```powershell
   xcopy /E /I "c:\Users\HP\Desktop\chatbot\extensions\vscode-extension" "%USERPROFILE%\.vscode\extensions\g4f-vscode-assistant"
   ```
2. Restart VS Code. The extension is now permanently installed!

---

## Prerequisite
Ensure your local `g4f` server is running in the background:
```powershell
python -m g4f --port 1337
```
