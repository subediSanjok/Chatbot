# 🌐 Chrome AI Assistant Extension

**Developer:** **Sanjok Subedi**  
**Repository:** [subediSanjok/Chatbot](https://github.com/subediSanjok/Chatbot)

---

## Overview

A Manifest V3 Google Chrome extension engineered by **Sanjok Subedi** connecting your browser directly to the local Chatbot API server.

## Features
- ⚡ **Direct Server Integration**: Communicates with the local server at `http://127.0.0.1:1337`.
- 🤖 **Multi-Model Access**: Toggle between models including GPT-4o, Claude 3.5 Sonnet, DeepSeek-R1, and Gemini 2.0.
- 🌐 **Instant Page Context**: Automatically extract selected text from any active web tab.
- 🖱️ **Context Menus**: Right-click highlighted content to explain, summarize, or fix text instantly.
- 📋 **Clipboard Sync**: One-click copying for formatted responses and code snippets.

## Installation
1. Start the local server:
   ```powershell
   python -m g4f --port 1337
   ```
2. Navigate to `chrome://extensions/` in Chrome/Brave/Edge.
3. Turn on **Developer mode** (top-right).
4. Click **Load unpacked** and select this directory (`extensions/chrome-extension`).

---

**Developed & Maintained by Sanjok Subedi**
