# g4f Google Chrome AI Assistant Extension

A complete, ready-to-load Manifest V3 Chrome extension connecting to your local `g4f` API server.

## Features
- ⚡ **Direct connection to local g4f server** (Default: `http://127.0.0.1:1337`).
- 🤖 **Multi-Model support** (GPT-4o, Gemini 2.0 Flash, DeepSeek-R1, Claude 3.5 Sonnet, etc.).
- 🌐 **Auto Page Context:** Grabs selected text automatically from any active webpage.
- 🖱️ **Right-click Context Menus:** Highlight text on any website -> Right-click -> "Explain", "Summarize", or "Fix Grammar".
- 📋 **One-click Copy:** Instantly copy formatted AI responses.

---

## How to Install and Load in Google Chrome / Brave / Edge

1. **Start the local g4f API Server:**
   Open terminal in your `chatbot` folder and run:
   ```powershell
   python -m g4f --port 1337
   ```

2. **Open Extensions in Chrome:**
   - In your browser address bar, navigate to: `chrome://extensions/`
   - Enable **Developer mode** toggle in the top-right corner.

3. **Load Unpacked Extension:**
   - Click the **Load unpacked** button in the top-left corner.
   - Select this folder:
     `c:\Users\HP\Desktop\chatbot\extensions\chrome-extension`

4. **Done!**
   - Click the extension icon in Chrome's toolbar to open the assistant.
   - Or highlight text on any webpage and right-click to send directly to g4f AI.
