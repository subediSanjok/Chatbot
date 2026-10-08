"""
Codex & Claude Code Autonomous Codebase Assistant
A desktop & standalone AI developer assistant with:
- Multi-model selection (claude-3.5-sonnet, gpt-4o, deepseek-r1, gemini-2.0-flash)
- Autonomous codebase modifications (Apply to File, Apply All Changes)
- Built-in visual side-by-side diff review
- Full @workspace file scanning and context ingestion
- Hybrid Computer Vision & Monitoring Pipeline templates
"""

import os
import sys
import json
import urllib.request
import urllib.error
import urllib.parse
import threading
import difflib
import re
import io
import webbrowser
import html
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

from g4f.image.fibo_engine import FiboEngine, FIBO_FULL_SCHEMA

SERVER_URL = "http://127.0.0.1:1337/v1/chat/completions"


SYSTEM_PROMPT = """You are an expert AI autonomous software engineer, codebase modifier, and Senior Computer Vision & Diffusion System Architect (specializing in PyTorch, Diffusers, OpenCV, SAM / SAM 2, ControlNet, Inpainting, Real-ESRGAN, YOLO, and FastAPI).
When the user asks you to implement features, fix bugs, refactor, or build vision & diffusion generation/editing systems:
1. Provide the complete, direct, production-grade implementation (never use placeholders or incomplete snippets).
2. For Image Generation, Editing & Object Inpainting Systems, follow the multi-stage deterministic + diffusion pipeline:
   [User Image/Prompt] -> [Preprocessing (OpenCV/Pillow)] -> [Segmentation & Object Isolation (SAM/SAM 2/YOLO)] -> [Conditioning & Edge/Depth/Pose Maps (ControlNet)] -> [Diffusion Inpainting / Img2Img (SDXL/Flux/Diffusers)] -> [Identity/Background Preservation (IP-Adapter/Mask Blending)] -> [Super Resolution (Real-ESRGAN)] -> [Validation & Quality Check (SSIM/PSNR)].
3. For every modified or new file, ALWAYS designate the target relative file path clearly in the code block header or right before it:
   ```language:relative/path/to/file.ext
   or
   ### File: relative/path/to/file.ext
   ```language
   <complete modified code>
   ```
4. Output clean, complete, working code ready for direct application to workspace files.
5. If multiple files need changes, create a separate code block for each file with its target path."""

# ---------------------------------------------------------------------------
# Web scraping & search utilities
# ---------------------------------------------------------------------------

def scrape_url(url: str, max_chars: int = 8000) -> str:
    """
    Fetch a URL and return its visible text content (strips HTML tags).
    Returns an error string if fetching fails.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            # Detect charset
            charset = "utf-8"
            ct = resp.headers.get_content_charset()
            if ct:
                charset = ct
            text = raw.decode(charset, errors="replace")
    except Exception as e:
        return f"[Error fetching URL: {e}]"

    # Strip <script>, <style>, <head> blocks
    text = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", " ", text)
    # Strip all remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if len(text) > max_chars:
        text = text[:max_chars] + f"\n... [truncated — full page is longer]"

    return text


def duckduckgo_search(query: str, max_results: int = 5) -> str:
    """
    Perform a DuckDuckGo search and return a formatted summary of results.
    """
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.5",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"[Search error: {e}]"

    # Extract result titles + snippets + URLs from DuckDuckGo HTML
    results = []
    # Find result blocks
    blocks = re.findall(
        r'class="result__title"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</div>',
        raw, re.DOTALL
    )
    for href, title, snippet in blocks[:max_results]:
        title_clean = re.sub(r"<[^>]+>", "", title).strip()
        snippet_clean = re.sub(r"<[^>]+>", "", snippet).strip()
        snippet_clean = html.unescape(snippet_clean)
        title_clean = html.unescape(title_clean)
        results.append(f"**{title_clean}**\n{snippet_clean}\nSource: {href}")

    if not results:
        # Fallback: just grab any visible text snippets
        text = re.sub(r"<[^>]+>", " ", raw)
        text = html.unescape(text)
        text = re.sub(r"[ \t]+", " ", text).strip()[:3000]
        return f"Search results for '{query}':\n\n{text}"

    return f"Web search results for '{query}':\n\n" + "\n\n---\n\n".join(results)


def extract_urls(text: str):
    """Find all HTTP/HTTPS URLs in a string."""
    return re.findall(
        r"https?://[^\s\)\]\"'>]{6,}",
        text
    )


def is_search_question(text: str) -> bool:
    """Detect if the message looks like a factual/search question."""
    triggers = [
        r"^(?:what|who|where|when|why|how|which|is|are|does|do|can|tell me about|explain|describe|find|search|look up)",
        r"\?"
    ]
    t = text.strip().lower()
    for pat in triggers:
        if re.search(pat, t, re.IGNORECASE):
            return True
    return False


def get_clipboard_text():
    if pyperclip:
        try:
            return pyperclip.paste()
        except Exception:
            pass
    try:
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        return text
    except Exception:
        return ""

def set_clipboard_text(text):
    if pyperclip:
        try:
            pyperclip.copy(text)
            return
        except Exception:
            pass
    try:
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
    except Exception:
        pass

def scan_workspace_files(folder_path, max_files=40):
    if not os.path.exists(folder_path):
        return "Workspace folder not found."

    ignore_dirs = {
        'node_modules', '.git', 'venv', '__pycache__', 'dist', 'build',
        '.next', '.vscode', '.idea', 'brain', 'generated_media'
    }
    ignore_exts = {
        '.png', '.jpg', '.jpeg', '.ico', '.gif', '.exe', '.dll', '.pyc',
        '.zip', '.tar', '.gz', '.pdf', '.woff', '.woff2', '.ttf', '.mp4', '.mp3'
    }

    scanned_files = []
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in ignore_exts:
                scanned_files.append(os.path.join(root, f))
            if len(scanned_files) >= max_files:
                break
        if len(scanned_files) >= max_files:
            break

    summary = f"=== WORKSPACE CONTEXT ({len(scanned_files)} key files scanned from '{folder_path}') ===\n\n"
    for file_path in scanned_files:
        rel_path = os.path.relpath(file_path, folder_path)
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                lines = content.splitlines()
                truncated = "\n".join(lines[:120]) + (f"\n... [Truncated {len(lines)-120} more lines] ..." if len(lines) > 120 else "")
                summary += f"--- File: {rel_path} ---\n```\n{truncated}\n```\n\n"
        except Exception:
            summary += f"--- File: {rel_path} (unreadable) ---\n\n"

    return summary

def extract_code_blocks(text):
    """
    Extracts code blocks and their associated file paths from AI markdown output.
    """
    edits = []
    pattern = re.compile(r"```([a-zA-Z0-9_\-\.\/\\:]*)\n([\s\S]*?)```")
    for match in pattern.finditer(text):
        header = match.group(1).strip()
        code = match.group(2).strip()
        start_idx = match.start()

        # Check header format `lang:path/to/file`
        file_path = ""
        if ":" in header:
            parts = header.split(":")
            if len(parts) > 1 and parts[1].strip():
                file_path = parts[1].strip()

        # Check preceding text for ### File: path/to/file
        if not file_path:
            preceding = text[max(0, start_idx - 150):start_idx]
            m = re.search(r"(?:###\s*File:|File:|Target\s*file:)\s*[`'\"]?([a-zA-Z0-9_\-\.\/\\~]+)[`'\"]?", preceding, re.IGNORECASE)
            if m:
                file_path = m.group(1).strip()

        edits.append({
            "filePath": file_path,
            "header": header,
            "code": code
        })
    return edits

class DiffViewerWindow:
    def __init__(self, parent, file_path, old_content, new_content, on_apply_callback=None):
        self.win = tk.Toplevel(parent)
        self.win.title(f"Diff Review — {os.path.basename(file_path)}")
        self.win.geometry("850x550")
        self.win.configure(bg="#1e1e2e")

        # Top Bar
        top_bar = tk.Frame(self.win, bg="#181825", padx=10, pady=8)
        top_bar.pack(fill="x")

        tk.Label(
            top_bar,
            text=f"📄 Reviewing Changes for: {file_path}",
            fg="#89b4fa",
            bg="#181825",
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")

        if on_apply_callback:
            tk.Button(
                top_bar,
                text="⚡ Apply This Change",
                command=lambda: [on_apply_callback(), self.win.destroy()],
                bg="#a6e3a1",
                fg="#11111b",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=10
            ).pack(side="right")

        # Diff Text View
        txt_diff = tk.Text(self.win, wrap="none", bg="#11111b", fg="#cdd6f4", font=("Consolas", 10))
        txt_diff.pack(fill="both", expand=True, padx=10, pady=10)

        # Generate Unified Diff
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"Original: {file_path}",
            tofile=f"AI Proposed: {file_path}",
            n=3
        )

        txt_diff.tag_configure("add", foreground="#a6e3a1", background="#1e3a29")
        txt_diff.tag_configure("del", foreground="#f38ba8", background="#3d1f28")
        txt_diff.tag_configure("hdr", foreground="#89b4fa", font=("Consolas", 10, "bold"))

        for line in diff:
            if line.startswith("+") and not line.startswith("+++"):
                txt_diff.insert(tk.END, line, "add")
            elif line.startswith("-") and not line.startswith("---"):
                txt_diff.insert(tk.END, line, "del")
            elif line.startswith("@@") or line.startswith("---") or line.startswith("+++"):
                txt_diff.insert(tk.END, line, "hdr")
            else:
                txt_diff.insert(tk.END, line)

        txt_diff.configure(state="disabled")

class FiboJsonViewerWindow:
    def __init__(self, parent, fibo_data):
        self.win = tk.Toplevel(parent)
        self.win.title("FIBO Structured JSON Schema Blueprint")
        self.win.geometry("780x520")
        self.win.configure(bg="#1e1e2e")

        top_bar = tk.Frame(self.win, bg="#181825", padx=10, pady=8)
        top_bar.pack(fill="x")

        tk.Label(
            top_bar,
            text="📑 FIBO JSON-Native Schema Specification",
            fg="#cba6f7",
            bg="#181825",
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")

        json_str = json.dumps(fibo_data, indent=2)

        def copy_json():
            set_clipboard_text(json_str)
            messagebox.showinfo("Copied", "✅ FIBO JSON Blueprint copied to clipboard!")

        tk.Button(
            top_bar,
            text="📋 Copy JSON Blueprint",
            command=copy_json,
            bg="#89b4fa",
            fg="#11111b",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10
        ).pack(side="right")

        txt_json = tk.Text(self.win, wrap="none", bg="#11111b", fg="#a6e3a1", font=("Consolas", 10))
        txt_json.pack(fill="both", expand=True, padx=10, pady=10)
        txt_json.insert("1.0", json_str)
        txt_json.configure(state="disabled")

class CodexClaudeChatbotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chatbot")
        self.root.geometry("900x650")
        self.root.configure(bg="#181825")

        self.workspace_dir = os.getcwd()
        self.current_edits = []
        self.last_fibo_data = None
        self.fibo_engine = FiboEngine()

        self._build_ui()


    def _build_ui(self):
        # 1. Header Banner
        header = tk.Frame(self.root, bg="#11111b", padx=12, pady=10)
        header.pack(fill="x")

        tk.Label(
            header,
            text="🤖 Chatbot — Autonomous AI Assistant",
            font=("Segoe UI", 13, "bold"),
            fg="#cba6f7",
            bg="#11111b"
        ).pack(side="left")


        self.lbl_status = tk.Label(
            header,
            text="● Server: 127.0.0.1:1337 (Connected)",
            font=("Segoe UI", 9),
            fg="#a6e3a1",
            bg="#11111b"
        )
        self.lbl_status.pack(side="right")

        # 2. Workspace & Model Toolbar
        toolbar = tk.Frame(self.root, bg="#1e1e2e", padx=10, pady=8)
        toolbar.pack(fill="x", padx=10, pady=(8, 0))

        tk.Label(toolbar, text="📁 Workspace:", fg="#a6adc8", bg="#1e1e2e", font=("Segoe UI", 9)).pack(side="left")
        self.lbl_workspace = tk.Label(toolbar, text=self.workspace_dir, fg="#89b4fa", bg="#1e1e2e", font=("Segoe UI", 9, "bold"))
        self.lbl_workspace.pack(side="left", padx=4)

        tk.Button(
            toolbar,
            text="Browse...",
            command=self.choose_workspace,
            bg="#313244",
            fg="#cdd6f4",
            font=("Segoe UI", 8),
            relief="flat"
        ).pack(side="left", padx=4)

        # Model Selector
        tk.Label(toolbar, text="Model:", fg="#a6adc8", bg="#1e1e2e", font=("Segoe UI", 9)).pack(side="left", padx=(16, 4))
        self.model_var = tk.StringVar(value="gpt-4o")
        self.model_combo = ttk.Combobox(
            toolbar,
            textvariable=self.model_var,
            values=["gpt-4o", "claude-3.5-sonnet", "deepseek-r1", "gemini-2.0-flash", "llama-3.3-70b", "flux"],
            width=18,
            state="readonly"
        )
        self.model_combo.pack(side="left")

        # Auto-apply Checkbox
        self.auto_apply_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            toolbar,
            text="⚡ Auto-Apply Code to Files",
            variable=self.auto_apply_var,
            fg="#89b4fa",
            bg="#1e1e2e",
            selectcolor="#11111b",
            activebackground="#1e1e2e",
            activeforeground="#89b4fa",
            font=("Segoe UI", 9, "bold")
        ).pack(side="right")

        # 3. Category & Template Action Pills
        pills_frame = tk.Frame(self.root, bg="#181825", padx=10, pady=4)
        pills_frame.pack(fill="x")

        pills = [
            ("🎨 Nano Banana 2 Image Gen", "/image Generate an image of: ", "#db2777"),
            ("🎯 SAM + Inpainting Pipeline", "Design and implement a complete Python Pipeline with OpenCV + SAM 2 (Segment Anything) + Diffusers SDXL/Flux Inpainting for adding/removing objects with mask preservation for: ", "#7c3aed"),
            ("📐 ControlNet Conditioning", "Implement a PyTorch + Diffusers ControlNet structural conditioning pipeline (Canny Edge + Depth + Pose) preserving exact subject geometry and background for: ", "#9333ea"),
            ("🔍 Real-ESRGAN Super-Res", "Implement a complete Super-Resolution and Quality Validation pipeline using Real-ESRGAN + OpenCV + SSIM quality metrics in Python for: ", "#4f46e5"),
            ("📸 OCR & YOLO Pipeline", "Design and implement a complete OpenCV Preprocessing + PaddleOCR + YOLO + Validation Pipeline in Python for: ", "#0284c7"),
            ("🚀 Implement Feature", "Implement the following logic and apply changes directly to codebase: ", "#2563eb"),
            ("🐛 Fix Bugs", "Find and fix bugs, security flaws, and edge cases in this code: ", "#313244"),
        ]

        for text, prompt, color in pills:
            tk.Button(
                pills_frame,
                text=text,
                command=lambda p=prompt: self.set_prompt_template(p),
                bg=color,
                fg="#ffffff",
                font=("Segoe UI", 8, "bold" if "cv" in text.lower() or "implement" in text.lower() else "normal"),
                relief="flat",
                padx=6,
                pady=2
            ).pack(side="left", padx=2)

        # 4. Bottom Codebase Actions Bar (Packed first with side=bottom to guarantee visibility)
        bottom_bar = tk.Frame(self.root, bg="#181825", padx=10, pady=8)
        bottom_bar.pack(side="bottom", fill="x")

        # Left side controls
        self.btn_send = tk.Button(
            bottom_bar,
            text="⚡ Run / Send Instruction (Ctrl+Enter)",
            command=self.on_send,
            bg="#89b4fa",
            fg="#11111b",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=14,
            pady=5,
            cursor="hand2"
        )
        self.btn_send.pack(side="left")

        tk.Button(
            bottom_bar,
            text="🧹 Clear",
            command=self.clear_all,
            bg="#313244",
            fg="#cdd6f4",
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2"
        ).pack(side="left", padx=6)

        # Right side Codebase Modification buttons
        self.btn_apply_all = tk.Button(
            bottom_bar,
            text="🚀 Apply All Changes to Codebase",
            command=self.apply_all_changes,
            bg="#a6e3a1",
            fg="#11111b",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=12,
            pady=5,
            state="disabled",
            cursor="hand2"
        )
        self.btn_apply_all.pack(side="right")

        self.btn_diff = tk.Button(
            bottom_bar,
            text="🔍 Review Diff",
            command=self.review_diff_first_edit,
            bg="#cba6f7",
            fg="#11111b",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=5,
            state="disabled",
            cursor="hand2"
        )
        self.btn_diff.pack(side="right", padx=6)

        # 5. Main Paned Content Area (Input Prompt & AI Code Output)
        paned = ttk.PanedWindow(self.root, orient="vertical")
        paned.pack(fill="both", expand=True, padx=10, pady=6)

        # Top: Prompt Input Frame
        frame_input = tk.Frame(paned, bg="#181825")
        
        prompt_hdr = tk.Frame(frame_input, bg="#181825")
        prompt_hdr.pack(fill="x", pady=(0, 2))
        tk.Label(prompt_hdr, text="User Instruction / Prompt (Type @workspace to include all workspace files):", fg="#a6adc8", bg="#181825", font=("Segoe UI", 9, "bold")).pack(side="left")

        self.txt_prompt = tk.Text(frame_input, wrap="word", height=4, bg="#1e1e2e", fg="#cdd6f4", font=("Consolas", 10), insertbackground="white")
        self.txt_prompt.pack(fill="both", expand=True, pady=2)
        self.txt_prompt.bind("<Control-Return>", lambda e: [self.on_send(), "break"][1])

        # Action bar right below prompt input
        input_action_bar = tk.Frame(frame_input, bg="#181825", pady=2)
        input_action_bar.pack(fill="x")

        self.btn_input_send = tk.Button(
            input_action_bar,
            text="⚡ Send Instruction",
            command=self.on_send,
            bg="#3b82f6",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2"
        )
        self.btn_input_send.pack(side="right", padx=2)

        tk.Button(
            input_action_bar,
            text="🎨 Generate Image",
            command=lambda: self.set_prompt_template("/image Generate an image of: "),
            bg="#db2777",
            fg="#ffffff",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2"
        ).pack(side="right", padx=4)

        paned.add(frame_input, weight=1)

        # Bottom: AI Response Output Frame
        frame_output = tk.Frame(paned, bg="#181825")
        
        output_hdr = tk.Frame(frame_output, bg="#181825")
        output_hdr.pack(fill="x", pady=(2, 2))
        tk.Label(output_hdr, text="AI Response & Proposed Code Modifications:", fg="#a6adc8", bg="#181825", font=("Segoe UI", 9, "bold")).pack(side="left", padx=2)

        self.lbl_edits_count = tk.Label(output_hdr, text="", fg="#a6e3a1", bg="#181825", font=("Segoe UI", 9, "bold"))
        self.lbl_edits_count.pack(side="right")

        self.txt_output = tk.Text(frame_output, wrap="word", bg="#11111b", fg="#cdd6f4", font=("Consolas", 10), insertbackground="white")
        self.txt_output.pack(fill="both", expand=True, pady=2)
        paned.add(frame_output, weight=3)

    def choose_workspace(self):
        folder = filedialog.askdirectory(initialdir=self.workspace_dir)
        if folder:
            self.workspace_dir = folder
            self.lbl_workspace.config(text=folder)

    def set_prompt_template(self, template):
        current = self.txt_prompt.get("1.0", tk.END).strip()
        if current:
            self.txt_prompt.delete("1.0", tk.END)
            self.txt_prompt.insert("1.0", f"{template}\n{current}")
        else:
            self.txt_prompt.delete("1.0", tk.END)
            self.txt_prompt.insert("1.0", template)
        self.txt_prompt.focus()

    def clear_all(self):
        self.txt_prompt.delete("1.0", tk.END)
        self.txt_output.delete("1.0", tk.END)
        self.current_edits = []
        self.lbl_edits_count.config(text="")
        self.btn_apply_all.config(state="disabled", text="🚀 Apply All Changes to Codebase", bg="#a6e3a1")
        self.btn_diff.config(state="disabled")

    def extract_clean_image_prompt(self, text):
        clean = text.strip()
        template_prefixes = [
            r"^Refactor and optimize this code for readability and performance:\s*",
            r"^Find and fix bugs, security flaws, and edge cases in this code:\s*",
            r"^Explain this code clearly step-by-step:\s*",
            r"^Implement the following logic and apply changes directly to codebase:\s*",
            r"^Design and implement a complete OpenCV Preprocessing.*?:?\s*",
            r"^Generate a Python Validation Engine.*?:?\s*",
            r"^Scaffold a complete FastAPI Monitoring Microservice.*?:?\s*",
            r"^Write comprehensive unit tests for this code:\s*",
            r"^Summarize this content in bullet points:\s*"
        ]
        for pref in template_prefixes:
            clean = re.sub(pref, "", clean, flags=re.IGNORECASE | re.DOTALL).strip()

        clean = re.sub(r"^\/(?:image|img)\s*", "", clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r"^(?:to\s+)?(?:please\s+)?(?:can\s+you\s+)?", "", clean, flags=re.IGNORECASE).strip()
        return clean

    def is_image_request(self, text, model):
        if model in ("flux", "dall-e-3", "sdxl-turbo"):
            return True
        clean = self.extract_clean_image_prompt(text)
        if clean.startswith("/image") or clean.startswith("/img"):
            return True

        # If user explicitly asked for code / python / script / pipeline, don't hijack into image generation
        explicit_code_words = ["python script", "write code", "write a script", "write a python", "create a script", "scaffold", "implement pipeline", "fastapi service", "diffusers pipeline", "sam pipeline", "controlnet pipeline", "code implementation"]
        if any(w in clean.lower() for w in explicit_code_words):
            return False

        # Pattern for image/picture/photo/drawing/map of ...
        if re.search(r"\b(?:image|picture|photo|illustration|drawing|map|diagram|wallpaper|portrait|sketch|art|poster)\s+(?:of|showing|depicting|with|for)\b", clean, re.IGNORECASE):
            return True

        # Pattern for generate/create/draw/paint/make/render/show me/i want ...
        if re.search(r"^(?:generate|create|draw|paint|make|render|produce|show me|give me|i want)\s+(?:an?\s+)?(?:image|picture|photo|illustration|drawing|map|diagram|wallpaper|art|poster|sketch|render|portrait|logo)\b", clean, re.IGNORECASE):
            return True

        direct_draw = re.compile(r"^(?:draw|paint|illustrate|render)\s+(?:an?\s+)?([a-zA-Z0-9\s_-]+)", re.IGNORECASE)
        if direct_draw.search(clean) and not any(w in clean.lower() for w in ["code", "function", "class", "pipeline", "script"]):
            return True

        return False

    def nano_banana_ground_prompt(self, raw_prompt):
        """
        Nano Banana 2 Working Mechanism:
        Uses multimodal reasoning to deconstruct user intent, enforce factual grounding
        (e.g., 2D political boundaries for maps instead of scenery), apply spatial composition,
        and attach strict negative constraints.
        """
        p_lower = raw_prompt.lower()
        if "map of" in p_lower or p_lower.startswith("map") or "nepal" in p_lower:
            match = re.search(r"map of\s+([a-zA-Z\s_-]+)", raw_prompt, re.IGNORECASE)
            location = match.group(1).strip() if match else raw_prompt
            return f"2D flat geographic and political map of {location}, accurate national boundary outline, borders, provinces, capital Kathmandu, topography, clear 2D cartography vector illustration, white background, no landscape scenery, no mountains, no buildings"
        if "diagram" in p_lower or "flowchart" in p_lower or "architecture" in p_lower:
            return f"Clean 2D technical diagram and schematic architecture infographic of {raw_prompt}, vector illustration, clear layout, professional white background"

        # Try fast LLM grounding pass if available
        try:
            grounding_system = (
                "You are Nano Banana 2 Multimodal Grounding Engine. "
                "Convert the user request into an exact, visually grounded, high-fidelity visual generation prompt. "
                "For maps/diagrams: enforce 2D cartographic vectors, clear borders, white background, no scenery photos. "
                "For objects/characters: specify lighting, textures, camera angle, and style. Output ONLY the optimized prompt."
            )
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": grounding_system},
                    {"role": "user", "content": raw_prompt}
                ],
                "stream": False
            }
            req = urllib.request.Request(
                SERVER_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                grounded = data["choices"][0]["message"]["content"].strip()
                if grounded:
                    return grounded
        except Exception:
            pass

        return raw_prompt

    def run_fibo_pipeline(self, prompt: str, task: str = "generate"):
        """
        FIBO JSON-Native Generation & Refinement Pipeline
        """
        self.btn_send.config(state="disabled", text="🎨 FIBO Synthesizing...")
        if hasattr(self, 'btn_input_send'):
            self.btn_input_send.config(state="disabled", text="⏳ FIBO Working...")

        action_title = "Refining Image Blueprint" if task == "refine" else "Generating Image Blueprint"
        self.txt_output.delete("1.0", tk.END)
        self.txt_output.insert("1.0", f"🎨 FIBO Engine: {action_title} for: '{prompt}'...\n")

        def fibo_worker():
            try:
                def update_status(msg):
                    self.txt_output.insert(tk.END, f"{msg}\n")
                self.root.after(0, lambda: update_status("📑 Step 1: Synthesizing structured FIBO JSON schema..."))

                # Execute FIBO engine
                result = self.fibo_engine.generate(
                    prompt=prompt,
                    task=task,
                    existing_json=self.last_fibo_data if task == "refine" else None,
                    model="flux"
                )

                self.last_fibo_data = result.get("structured_json")
                flattened_prompt = result.get("flattened_prompt", prompt)
                img_url = result.get("url") or result.get("image_url", "")
                
                self.root.after(0, lambda: update_status(f"🖼️ Step 2: Synthesized Image: {img_url[:60]}..."))

                # Download image bytes for in-line GUI preview
                img_bytes = None
                if img_url:
                    try:
                        req_img = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                        with urllib.request.urlopen(req_img, timeout=30) as img_resp:
                            img_bytes = img_resp.read()
                    except Exception as dl_err:
                        print("Could not download image preview:", dl_err)

                def on_success():
                    self.txt_output.delete("1.0", tk.END)
                    self.txt_output.insert(tk.END, "🎨 FIBO (Fast Interactive Blueprint Output) Image Generation\n\n", "bold")
                    self.txt_output.insert(tk.END, f"📌 Concept / Edit: {prompt}\n")
                    self.txt_output.insert(tk.END, f"📐 Mode: {'Refine (Disentangled Edit)' if task == 'refine' else 'Initial Blueprint Generation'}\n")
                    self.txt_output.insert(tk.END, f"🔗 Direct Image Link: {img_url}\n\n")


                    if img_bytes and Image and ImageTk:
                        try:
                            pil_img = Image.open(io.BytesIO(img_bytes))
                            pil_img.thumbnail((500, 350), Image.Resampling.LANCZOS)
                            tk_photo = ImageTk.PhotoImage(pil_img)
                            self._rendered_photo = tk_photo

                            card_frame = tk.Frame(self.txt_output, bg="#1e1e2e", padx=12, pady=10, relief="solid", bd=1)

                            lbl_img = tk.Label(card_frame, image=tk_photo, bg="#11111b")
                            lbl_img.pack(pady=4)

                            # Button Row
                            act_row = tk.Frame(card_frame, bg="#1e1e2e", pady=6)
                            act_row.pack(fill="x")

                            def save_img_action():
                                initial_name = "generated_fibo_image.jpg"
                                save_path = filedialog.asksaveasfilename(
                                    initialdir=self.workspace_dir,
                                    initialfile=initial_name,
                                    defaultextension=".jpg",
                                    filetypes=[("JPEG Image", "*.jpg"), ("PNG Image", "*.png"), ("All Files", "*.*")]
                                )
                                if save_path:
                                    with open(save_path, "wb") as f:
                                        f.write(img_bytes)
                                    messagebox.showinfo("Saved", f"✅ Image saved to:\n{save_path}")

                            tk.Button(
                                act_row,
                                text="💾 Save to Project...",
                                command=save_img_action,
                                bg="#065f46",
                                fg="#a7f3d0",
                                font=("Segoe UI", 9, "bold"),
                                relief="flat",
                                padx=8,
                                pady=4,
                                cursor="hand2"
                            ).pack(side="left", padx=3)

                            tk.Button(
                                act_row,
                                text="📋 Copy URL",
                                command=lambda: set_clipboard_text(img_url),
                                bg="#313244",
                                fg="#cdd6f4",
                                font=("Segoe UI", 9),
                                relief="flat",
                                padx=8,
                                pady=4,
                                cursor="hand2"
                            ).pack(side="left", padx=3)

                            tk.Button(
                                act_row,
                                text="🌐 Full Size",
                                command=lambda: webbrowser.open(img_url),
                                bg="#313244",
                                fg="#cdd6f4",
                                font=("Segoe UI", 9),
                                relief="flat",
                                padx=8,
                                pady=4,
                                cursor="hand2"
                            ).pack(side="left", padx=3)

                            if self.last_fibo_data:
                                tk.Button(
                                    act_row,
                                    text="📑 View FIBO JSON Blueprint",
                                    command=lambda: FiboJsonViewerWindow(self.root, self.last_fibo_data),
                                    bg="#cba6f7",
                                    fg="#11111b",
                                    font=("Segoe UI", 9, "bold"),
                                    relief="flat",
                                    padx=8,
                                    pady=4,
                                    cursor="hand2"
                                ).pack(side="right", padx=3)

                            # Interactive FIBO Refinement Panel
                            refine_frame = tk.Frame(card_frame, bg="#181825", padx=8, pady=8, relief="solid", bd=1)
                            refine_frame.pack(fill="x", pady=(8, 0))

                            tk.Label(
                                refine_frame,
                                text="✏️ Refine with FIBO (Disentangled Edit):",
                                bg="#181825",
                                fg="#89b4fa",
                                font=("Segoe UI", 9, "bold")
                            ).pack(anchor="w")

                            refine_input_row = tk.Frame(refine_frame, bg="#181825")
                            refine_input_row.pack(fill="x", pady=(4, 0))

                            txt_refine = tk.Entry(refine_input_row, bg="#11111b", fg="#cdd6f4", insertbackground="#cdd6f4", font=("Segoe UI", 9))
                            txt_refine.insert(0, "e.g. change lighting to golden hour sunset, add sunglasses")
                            txt_refine.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=3)

                            def clear_refine_placeholder(e):
                                if txt_refine.get().startswith("e.g."):
                                    txt_refine.delete(0, tk.END)
                            txt_refine.bind("<FocusIn>", clear_refine_placeholder)

                            def do_refine():
                                ref_text = txt_refine.get().strip()
                                if ref_text and not ref_text.startswith("e.g."):
                                    self.run_fibo_pipeline(ref_text, task="refine")
                                else:
                                    messagebox.showwarning("Empty Edit", "Please enter a modification instruction to refine.")

                            tk.Button(
                                refine_input_row,
                                text="⚡ Apply Refinement",
                                command=do_refine,
                                bg="#f9e2af",
                                fg="#11111b",
                                font=("Segoe UI", 9, "bold"),
                                relief="flat",
                                padx=10,
                                pady=3,
                                cursor="hand2"
                            ).pack(side="right")

                            self.txt_output.window_create(tk.END, window=card_frame)
                            self.txt_output.insert(tk.END, "\n\n")
                        except Exception as render_err:
                            self.txt_output.insert(tk.END, f"(Preview error: {render_err})\n")

                    self.btn_send.config(state="normal", text="⚡ Run / Send Instruction (Ctrl+Enter)")
                    if hasattr(self, 'btn_input_send'):
                        self.btn_input_send.config(state="normal", text="⚡ Send Instruction")

                self.root.after(0, on_success)
            except Exception as e:
                def on_error(err=str(e)):
                    self.txt_output.delete("1.0", tk.END)
                    self.txt_output.insert("1.0", f"⚠️ FIBO Image Generation Error: {err}\n\nMake sure g4f server is running: 'python -m g4f --port 1337'")
                    self.btn_send.config(state="normal", text="⚡ Run / Send Instruction (Ctrl+Enter)")
                    if hasattr(self, 'btn_input_send'):
                        self.btn_input_send.config(state="normal", text="⚡ Send Instruction")
                self.root.after(0, on_error)

        threading.Thread(target=fibo_worker, daemon=True).start()

    def on_send(self):
        user_prompt = self.txt_prompt.get("1.0", tk.END).strip()
        if not user_prompt:
            messagebox.showwarning("Empty Prompt", "Please enter an instruction or prompt.")
            return

        model = self.model_var.get()
        auto_apply = self.auto_apply_var.get()

        # Handle image generation via FIBO Engine
        if self.is_image_request(user_prompt, model):
            clean_prompt = self.extract_clean_image_prompt(user_prompt)
            clean_prompt = re.sub(r"^(?:to\s+)?(?:generate|create|draw|paint|make|render|produce|show me|give me|i want)\s+(?:an?\s+)?(?:image|picture|photo|illustration|drawing|map|diagram|wallpaper|art|poster|sketch|render|portrait|logo)?\s*(?:of|showing|depicting|with|for)?\s*", "", clean_prompt, flags=re.IGNORECASE).strip()
            clean_prompt = re.sub(r"^(?:image|picture|photo|illustration|drawing|map|diagram)\s+(?:of|showing|depicting|with|for)\s*", "", clean_prompt, flags=re.IGNORECASE).strip()
            clean_prompt = re.sub(r"^(?:draw|paint|illustrate|render)\s+(?:an?\s+)?", "", clean_prompt, flags=re.IGNORECASE).strip()
            if not clean_prompt:
                clean_prompt = user_prompt

            self.run_fibo_pipeline(clean_prompt, task="generate")
            return

        # ---------------------------------------------------------------
        # 🌐 URL SCRAPING & WEB SEARCH — Auto-inject live web content
        # ---------------------------------------------------------------
        full_prompt = user_prompt
        web_context_parts = []

        # 1. Detect URLs in the prompt and scrape them
        urls = extract_urls(user_prompt)
        if urls:
            self.txt_output.delete("1.0", tk.END)
            self.txt_output.insert("1.0", f"🌐 Detected {len(urls)} URL(s) — fetching content...\n")
            self.root.update()
            for url in urls[:3]:  # Limit to 3 URLs
                self.txt_output.insert(tk.END, f"  ↳ Scraping: {url}\n")
                self.root.update()
                scraped = scrape_url(url)
                web_context_parts.append(
                    f"=== Content from URL: {url} ===\n{scraped}\n"
                )

        # 2. If it looks like a factual/search question (and no URL provided), do a web search
        elif is_search_question(user_prompt) and "@workspace" not in user_prompt:
            self.txt_output.delete("1.0", tk.END)
            self.txt_output.insert("1.0", f"🔎 Searching the web for: '{user_prompt[:80]}'...\n")
            self.root.update()
            search_results = duckduckgo_search(user_prompt)
            web_context_parts.append(
                f"=== Live Web Search Results ===\n{search_results}\n"
            )

        # 3. Inject web context into the prompt
        if web_context_parts:
            web_block = "\n\n".join(web_context_parts)
            full_prompt = (
                f"{user_prompt}\n\n"
                f"--- LIVE WEB CONTEXT (fetched just now) ---\n"
                f"{web_block}\n"
                f"--- END OF WEB CONTEXT ---\n\n"
                f"Using the above live content, please answer the user's question accurately and in detail."
            )

        # 4. @workspace context injection
        if "@workspace" in user_prompt:
            self.txt_output.delete("1.0", tk.END)
            self.txt_output.insert("1.0", f"🔍 Scanning workspace files from '{self.workspace_dir}'...\n")
            self.root.update()
            workspace_context = scan_workspace_files(self.workspace_dir)
            full_prompt = f"{full_prompt.replace('@workspace', '').strip()}\n\n{workspace_context}"

        self.btn_send.config(state="disabled", text="⏳ Generating...")
        if hasattr(self, 'btn_input_send'):
            self.btn_input_send.config(state="disabled", text="⏳ Generating...")

        if not web_context_parts:
            self.txt_output.delete("1.0", tk.END)
        self.txt_output.insert(tk.END, f"🤖 Generating answer using {model}...\n")

        def worker():
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt}
                ]
            }

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                SERVER_URL,
                data=data,
                headers={"Content-Type": "application/json"}
            )

            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                    answer = resp_json["choices"][0]["message"]["content"]

                # Prepend a note if web context was used
                if web_context_parts and urls:
                    prefix = f"🌐 [Answer based on live content from: {', '.join(urls[:3])}]\n\n"
                elif web_context_parts:
                    prefix = f"🔎 [Answer based on live web search]\n\n"
                else:
                    prefix = ""

                def on_success():
                    self.txt_output.delete("1.0", tk.END)
                    self.txt_output.insert("1.0", prefix + answer)
                    self._process_detected_edits(answer, auto_apply)

                self.root.after(0, on_success)
            except Exception as e:
                def on_error(err=str(e)):
                    self.txt_output.delete("1.0", tk.END)
                    self.txt_output.insert("1.0", f"⚠️ Error: {err}\n\nMake sure g4f server is running: 'python -m g4f --port 1337'")
                    self.btn_send.config(state="normal", text="⚡ Run / Send Instruction (Ctrl+Enter)")
                    if hasattr(self, 'btn_input_send'):
                        self.btn_input_send.config(state="normal", text="⚡ Send Instruction")

                self.root.after(0, on_error)

        threading.Thread(target=worker, daemon=True).start()

    def _process_detected_edits(self, text, auto_apply):
        self.btn_send.config(state="normal", text="⚡ Run / Send Instruction (Ctrl+Enter)")
        if hasattr(self, 'btn_input_send'):
            self.btn_input_send.config(state="normal", text="⚡ Send Instruction")
        self.current_edits = extract_code_blocks(text)

        if self.current_edits:
            file_names = [e["filePath"] if e["filePath"] else "unnamed file" for e in self.current_edits]
            self.lbl_edits_count.config(text=f"✨ {len(self.current_edits)} file modification(s) detected: {', '.join(file_names)}")
            self.btn_apply_all.config(state="normal")
            self.btn_diff.config(state="normal")

            if auto_apply:
                self.apply_all_changes()
        else:
            self.lbl_edits_count.config(text="No file code blocks detected.")
            self.btn_apply_all.config(state="disabled")
            self.btn_diff.config(state="disabled")

    def apply_file_edit(self, file_rel_path, new_code):
        if not file_rel_path:
            file_rel_path = filedialog.asksaveasfilename(initialdir=self.workspace_dir, title="Save generated code as file")
            if not file_rel_path:
                return False
            target_path = file_rel_path
        else:
            target_path = os.path.join(self.workspace_dir, file_rel_path)

        target_dir = os.path.dirname(target_path)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_code)

        return True

    def apply_all_changes(self):
        if not self.current_edits:
            messagebox.showinfo("No Changes", "No file code blocks found to apply.")
            return

        applied = []
        for edit in self.current_edits:
            path_name = edit["filePath"]
            ok = self.apply_file_edit(path_name, edit["code"])
            if ok:
                applied.append(path_name or "New File")

        self.btn_apply_all.config(text="✅ All Changes Applied to Codebase!", bg="#166534")
        messagebox.showinfo(
            "Codebase Modified",
            f"Successfully applied {len(applied)} file changes directly to your workspace:\n\n" + "\n".join(f"• {p}" for p in applied)
        )

    def review_diff_first_edit(self):
        if not self.current_edits:
            return

        edit = self.current_edits[0]
        file_path = edit["filePath"]
        full_path = os.path.join(self.workspace_dir, file_path) if file_path else ""

        old_content = ""
        if full_path and os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                old_content = f.read()

        DiffViewerWindow(
            self.root,
            file_path or "New File",
            old_content,
            edit["code"],
            on_apply_callback=lambda: self.apply_file_edit(file_path, edit["code"])
        )

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = CodexClaudeChatbotGUI()
    app.run()

