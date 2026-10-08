const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

/**
 * In-memory diff document content provider for side-by-side reviews
 */
class G4FDiffContentProvider {
    constructor() {
        this._documents = new Map();
        this._onDidChange = new vscode.EventEmitter();
        this.onDidChange = this._onDidChange.event;
    }

    provideTextDocumentContent(uri) {
        return this._documents.get(uri.toString()) || "";
    }

    setDocumentContent(uri, content) {
        this._documents.set(uri.toString(), content);
        this._onDidChange.fire(uri);
    }
}

const diffContentProvider = new G4FDiffContentProvider();

/**
 * g4f API Client
 */
async function queryG4F(messages, model, customBaseUrl) {
    const config = vscode.workspace.getConfiguration('g4f');
    const baseUrl = (customBaseUrl || config.get('serverUrl') || "http://127.0.0.1:1337").replace(/\/+$/, "");
    const selectedModel = model || config.get('model') || "gpt-4o";

    const payload = {
        model: selectedModel,
        messages: messages
    };

    const response = await fetch(`${baseUrl}/v1/chat/completions`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const errText = await response.text();
        throw new Error(`g4f Server error (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.choices && data.choices[0] && data.choices[0].message
        ? data.choices[0].message.content
        : JSON.stringify(data, null, 2);
}

/**
 * g4f Image Generation Client
 */
async function generateG4FImage(promptText, model, customBaseUrl) {
    const config = vscode.workspace.getConfiguration('g4f');
    const baseUrl = (customBaseUrl || config.get('serverUrl') || "http://127.0.0.1:1337").replace(/\/+$/, "");
    const selectedModel = model === 'flux' || model === 'dall-e-3' || model === 'sdxl-turbo' ? model : "flux";

    const payload = {
        prompt: promptText,
        model: selectedModel
    };

    const response = await fetch(`${baseUrl}/v1/images/generations`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const errText = await response.text();
        throw new Error(`g4f Image Server error (${response.status}): ${errText}`);
    }

    const data = await response.json();
    if (data.data && data.data[0] && data.data[0].url) {
        return {
            url: data.data[0].url,
            revised_prompt: data.data[0].revised_prompt || promptText
        };
    }
    throw new Error("No image URL returned by g4f server.");
}

/**
 * Sidebar Webview View Provider (Interactive Chat & Codebase Modifier)
 */
class G4FChatViewProvider {
    static viewType = 'g4f.chatView';

    constructor(context) {
        this._context = context;
        this._view = undefined;
        this._history = [];

        // Track active editor changes to keep chat informed
        vscode.window.onDidChangeActiveTextEditor((editor) => {
            if (this._view && editor) {
                const relPath = vscode.workspace.asRelativePath(editor.document.uri);
                this._view.webview.postMessage({
                    type: 'activeEditorChanged',
                    filePath: relPath,
                    languageId: editor.document.languageId
                });
            }
        });
    }

    resolveWebviewView(webviewView, context, token) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._context.extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview();

        // Send current active file info
        const activeEditor = vscode.window.activeTextEditor;
        if (activeEditor) {
            webviewView.webview.postMessage({
                type: 'activeEditorChanged',
                filePath: vscode.workspace.asRelativePath(activeEditor.document.uri),
                languageId: activeEditor.document.languageId
            });
        }

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'sendMessage':
                    await this._handleUserMessage(data.text, data.model, data.includeCode, data.scanWorkspace, data.autoApply);
                    break;
                case 'generateImage':
                    await this._handleGenerateImage(data.prompt, data.model);
                    break;
                case 'saveImage':
                    await this._saveImageToWorkspace(data.imageUrl, data.suggestedName);
                    break;
                case 'insertCode':
                    this._insertCodeIntoEditor(data.code);
                    break;
                case 'applyFileEdit':
                    await this._applyFileChanges(data.filePath, data.code);
                    break;
                case 'applyAllEdits':
                    await this._applyAllChanges(data.edits);
                    break;
                case 'reviewDiff':
                    await this._openDiffViewer(data.filePath, data.code);
                    break;
                case 'clearHistory':
                    this._history = [];
                    break;
            }
        });
    }

    async _scanWorkspaceCodebase() {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            return "No workspace folder is currently open.";
        }

        const files = await vscode.workspace.findFiles(
            '**/*',
            '{**/node_modules/**,**/.git/**,**/venv/**,**/__pycache__/**,**/dist/**,**/build/**,**/.next/**,**/*.png,**/*.jpg,**/*.jpeg,**/*.ico,**/*.gif,**/*.exe,**/*.dll,**/*.pyc,**/*.zip,**/*.tar,**/*.gz,**/*.pdf,**/*.woff,**/*.woff2,**/*.ttf,**/*.eot,**/*.mp4,**/*.mp3}',
            40
        );

        let codebaseSummary = `=== WORKSPACE CODEBASE CONTEXT (${files.length} key files scanned) ===\n\n`;

        for (const fileUri of files) {
            const relPath = vscode.workspace.asRelativePath(fileUri);
            try {
                const doc = await vscode.workspace.openTextDocument(fileUri);
                const text = doc.getText();
                const lines = text.split('\n');
                const truncated = lines.length > 120 
                    ? lines.slice(0, 120).join('\n') + `\n... [Truncated ${lines.length - 120} more lines] ...`
                    : text;

                codebaseSummary += `--- File: ${relPath} ---\n\`\`\`\n${truncated}\n\`\`\`\n\n`;
            } catch (err) {
                codebaseSummary += `--- File: ${relPath} (binary/unreadable) ---\n\n`;
            }
        }

        return codebaseSummary;
    }

    _isImageGenerationPrompt(text, model) {
        if (model === 'flux' || model === 'dall-e-3' || model === 'sdxl-turbo') {
            return true;
        }
        let clean = text.trim();
        const templatePrefixes = [
            /^Refactor and optimize this code for readability and performance:\s*/i,
            /^Find and fix bugs, security flaws, and edge cases in this code:\s*/i,
            /^Explain this code clearly step-by-step:\s*/i,
            /^Implement the following logic and apply changes directly to codebase:\s*/i,
            /^Design and implement a complete OpenCV Preprocessing.*?:?\s*/i,
            /^Generate a Python Validation Engine.*?:?\s*/i,
            /^Scaffold a complete FastAPI Monitoring Microservice.*?:?\s*/i,
            /^Write comprehensive unit tests for this code:\s*/i,
            /^Summarize this content in bullet points:\s*/i
        ];
        for (const pref of templatePrefixes) {
            clean = clean.replace(pref, '').trim();
        }

        if (clean.startsWith('/image') || clean.startsWith('/img')) {
            return true;
        }

        clean = clean.replace(/^(?:to\s+)?(?:please\s+)?(?:can\s+you\s+)?/i, '').trim();

        // Check if user explicitly asked for code / python script / pipeline
        const explicitCodeWords = ["python script", "write code", "write a script", "write a python", "create a script", "scaffold", "implement pipeline", "fastapi service", "diffusers pipeline", "sam pipeline", "controlnet pipeline", "code implementation"];
        if (explicitCodeWords.some(w => clean.toLowerCase().includes(w))) {
            return false;
        }

        if (/\b(?:image|picture|photo|illustration|drawing|map|diagram|wallpaper|portrait|sketch|art|poster)\s+(?:of|showing|depicting|with|for)\b/i.test(clean)) {
            return true;
        }

        if (/^(?:generate|create|draw|paint|make|render|produce|show me|give me|i want)\s+(?:an?\s+)?(?:image|picture|photo|illustration|drawing|map|diagram|wallpaper|art|poster|sketch|render|portrait|logo)\b/i.test(clean)) {
            return true;
        }

        const directDrawRegex = /^(?:draw|paint|illustrate|render)\s+(?:an?\s+)?([a-zA-Z0-9\s_-]+)/i;
        if (directDrawRegex.test(clean) && !clean.includes("code") && !clean.includes("function") && !clean.includes("class") && !clean.includes("pipeline") && !clean.includes("script")) {
            return true;
        }
        return false;
    }

    _optimizeImagePrompt(prompt) {
        const pLower = prompt.toLowerCase();
        if (pLower.includes("map of") || pLower.startsWith("map") || pLower.includes("nepal")) {
            const match = prompt.match(/map of\s+([a-zA-Z\s_-]+)/i);
            const location = match ? match[1].trim() : prompt;
            return `2D flat geographic and political map of ${location}, accurate national boundary outline, borders, provinces, capital Kathmandu, topography, clear 2D cartography vector illustration, white background, no landscape scenery, no mountains, no buildings`;
        }
        if (pLower.includes("diagram") || pLower.includes("flowchart") || pLower.includes("architecture")) {
            return `Clean 2D technical diagram and schematic architecture infographic of ${prompt}, vector illustration, clear layout, professional white background`;
        }
        return prompt;
    }

    async _handleGenerateImage(promptText, model) {
        if (!this._view) return;

        let cleanPrompt = promptText.replace(/^\/(?:image|img)\s*/i, '').trim();
        cleanPrompt = cleanPrompt.replace(/^(?:to\s+)?(?:generate|create|draw|paint|make|render|produce|show me|give me|i want)\s+(?:an?\s+)?(?:image|picture|photo|illustration|drawing|map|diagram|wallpaper|art|poster|sketch|render|portrait|logo)?\s*(?:of|showing|depicting|with|for)?\s*/i, '').trim();
        cleanPrompt = cleanPrompt.replace(/^(?:image|picture|photo|illustration|drawing|map|diagram)\s+(?:of|showing|depicting|with|for)\s*/i, '').trim();
        cleanPrompt = cleanPrompt.replace(/^(?:draw|paint|illustrate|render)\s+(?:an?\s+)?/i, '').trim();
        if (!cleanPrompt) cleanPrompt = promptText;

        const optimizedPrompt = this._optimizeImagePrompt(cleanPrompt);

        this._view.webview.postMessage({
            type: 'addMessage',
            message: { role: 'user', content: `🎨 Generate Image: "${cleanPrompt}"` }
        });
        this._view.webview.postMessage({ type: 'setLoading', loading: true, loadingText: "🎨 Generating image with Flux AI..." });

        try {
            const imgResult = await generateG4FImage(optimizedPrompt, model);
            this._view.webview.postMessage({
                type: 'addImageMessage',
                imageUrl: imgResult.url,
                prompt: cleanPrompt,
                revisedPrompt: imgResult.revised_prompt
            });
        } catch (err) {
            this._view.webview.postMessage({
                type: 'addMessage',
                message: { role: 'error', content: `⚠️ Image Generation Error: ${err.message}` }
            });
        } finally {
            this._view.webview.postMessage({ type: 'setLoading', loading: false });
        }
    }

    async _saveImageToWorkspace(imageUrl, suggestedName) {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showErrorMessage("Please open a workspace folder to save generated images.");
            return;
        }

        try {
            const imagesDir = vscode.Uri.joinPath(workspaceFolders[0].uri, "images");
            if (!fs.existsSync(imagesDir.fsPath)) {
                fs.mkdirSync(imagesDir.fsPath, { recursive: true });
            }

            const cleanBase = (suggestedName || "generated_image")
                .toLowerCase()
                .replace(/[^a-z0-9_-]+/g, "_")
                .substring(0, 35)
                .replace(/^_+|_+$/g, '') || "ai_image";

            const fileName = `${cleanBase}_${Date.now().toString().slice(-4)}.jpg`;
            const targetUri = vscode.Uri.joinPath(imagesDir, fileName);

            const response = await fetch(imageUrl);
            const arrayBuffer = await response.arrayBuffer();
            const buffer = Buffer.from(arrayBuffer);

            fs.writeFileSync(targetUri.fsPath, buffer);
            const relPath = vscode.workspace.asRelativePath(targetUri);
            vscode.window.showInformationMessage(`✅ Image saved to: ${relPath}`);
            await vscode.commands.executeCommand('vscode.open', targetUri);
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to save image: ${error.message}`);
        }
    }

    async _handleUserMessage(promptText, model, includeCode, scanWorkspace, autoApply) {
        if (!this._view) return;

        // Auto-detect image generation request
        if (this._isImageGenerationPrompt(promptText, model)) {
            await this._handleGenerateImage(promptText, model);
            return;
        }

        let activeCode = "";
        let activeFileContext = "";
        const editor = vscode.window.activeTextEditor;

        if (editor) {
            const relPath = vscode.workspace.asRelativePath(editor.document.uri);
            activeFileContext = `Active file in editor: \`${relPath}\` (${editor.document.languageId})\n`;
            
            if (includeCode) {
                if (!editor.selection.isEmpty) {
                    activeCode = editor.document.getText(editor.selection);
                } else {
                    const fullDocText = editor.document.getText();
                    if (fullDocText.length < 5000) {
                        activeCode = fullDocText;
                    }
                }
            }
        }

        let fullUserPrompt = promptText;
        if (activeCode) {
            fullUserPrompt = `${promptText}\n\n[Active File Context: ${activeFileContext.trim()}]\n\`\`\`\n${activeCode}\n\`\`\``;
        } else if (activeFileContext) {
            fullUserPrompt = `${promptText}\n\n[Active File Context: ${activeFileContext.trim()}]`;
        }

        if (scanWorkspace) {
            this._view.webview.postMessage({
                type: 'addMessage',
                message: { role: 'user', content: `🔍 Scanning workspace files... [${promptText}]` }
            });
            this._view.webview.postMessage({ type: 'setLoading', loading: true, loadingText: "Scanning workspace..." });

            const workspaceContext = await this._scanWorkspaceCodebase();
            fullUserPrompt = `${promptText}\n\n${workspaceContext}`;
        } else {
            this._view.webview.postMessage({
                type: 'addMessage',
                message: { role: 'user', content: promptText, codeSnippet: activeCode }
            });
            this._view.webview.postMessage({ type: 'setLoading', loading: true, loadingText: "Generating response..." });
        }

        this._history.push({ role: "user", content: fullUserPrompt });

        try {
            const systemMessage = {
                role: "system",
                content: `You are an expert AI autonomous software engineer, codebase modifier, and Senior Computer Vision & Diffusion System Architect (specializing in PyTorch, Diffusers, OpenCV, SAM / SAM 2, ControlNet, Inpainting, Real-ESRGAN, YOLO, and FastAPI).
When the user asks you to implement features, fix bugs, refactor, or build vision & diffusion generation/editing systems:
1. Provide the complete, direct, production-grade implementation (never use placeholders or incomplete snippets).
2. For Image Generation, Editing & Object Inpainting Systems, follow the multi-stage deterministic + diffusion pipeline:
   [User Image/Prompt] -> [Preprocessing (OpenCV/Pillow)] -> [Segmentation & Object Isolation (SAM/SAM 2/YOLO)] -> [Conditioning & Edge/Depth/Pose Maps (ControlNet)] -> [Diffusion Inpainting / Img2Img (SDXL/Flux/Diffusers)] -> [Identity/Background Preservation (IP-Adapter/Mask Blending)] -> [Super Resolution (Real-ESRGAN)] -> [Validation & Quality Check (SSIM/PSNR)].
3. For every modified or new file, ALWAYS designate the target file path in the markdown code fence or header:
   \`\`\`language:relative/path/to/file.ext
   or
   ### File: relative/path/to/file.ext
   \`\`\`language
   <complete modified code>
   \`\`\`
4. Output clean, complete, working code ready for direct application to the user's workspace files.
5. If multiple files need changes, create a separate code block for each file with its target path.`
            };

            const messages = [
                systemMessage,
                ...this._history
            ];

            const reply = await queryG4F(messages, model);

            this._history.push({ role: "assistant", content: reply });

            this._view.webview.postMessage({
                type: 'addMessage',
                message: { role: 'assistant', content: reply, autoApply: Boolean(autoApply) }
            });
        } catch (err) {
            this._view.webview.postMessage({
                type: 'addMessage',
                message: { role: 'error', content: "⚠️ Error: " + err.message + "\nMake sure g4f is running on port 1337 ('python -m g4f --port 1337')." }
            });
        } finally {
            this._view.webview.postMessage({ type: 'setLoading', loading: false });
        }
    }

    _resolveTargetUri(filePath) {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (filePath) {
            // Clean up any leading/trailing quotes or markdown artifacts
            const cleanPath = filePath.trim().replace(/^['"`]+|['"`]+$/g, '');
            if (path.isAbsolute(cleanPath)) {
                return vscode.Uri.file(cleanPath);
            }
            if (workspaceFolders && workspaceFolders.length > 0) {
                return vscode.Uri.joinPath(workspaceFolders[0].uri, cleanPath);
            }
        }
        if (vscode.window.activeTextEditor) {
            return vscode.window.activeTextEditor.document.uri;
        }
        if (workspaceFolders && workspaceFolders.length > 0 && filePath) {
            return vscode.Uri.joinPath(workspaceFolders[0].uri, filePath);
        }
        return null;
    }

    async _applyFileChanges(filePath, newContent) {
        try {
            const targetUri = this._resolveTargetUri(filePath);
            if (!targetUri) {
                vscode.window.showErrorMessage("No target file or active editor found to apply changes.");
                return false;
            }

            const targetFsPath = targetUri.fsPath;
            const targetDir = path.dirname(targetFsPath);

            // Ensure folder exists
            if (!fs.existsSync(targetDir)) {
                fs.mkdirSync(targetDir, { recursive: true });
            }

            // If file doesn't exist yet, create it
            if (!fs.existsSync(targetFsPath)) {
                fs.writeFileSync(targetFsPath, newContent, 'utf8');
                const doc = await vscode.workspace.openTextDocument(targetUri);
                await vscode.window.showTextDocument(doc, { preview: false });
                vscode.window.showInformationMessage(`✅ Created and applied changes to: ${vscode.workspace.asRelativePath(targetUri)}`);
                if (this._view) {
                    this._view.webview.postMessage({ type: 'fileAppliedSuccess', filePath: vscode.workspace.asRelativePath(targetUri) });
                }
                return true;
            }

            // Open doc and apply workspace edit
            const doc = await vscode.workspace.openTextDocument(targetUri);
            const editor = await vscode.window.showTextDocument(doc, { preview: false });

            const fullRange = new vscode.Range(
                doc.positionAt(0),
                doc.positionAt(doc.getText().length)
            );

            const edit = new vscode.WorkspaceEdit();
            edit.replace(targetUri, fullRange, newContent);
            const applied = await vscode.workspace.applyEdit(edit);
            
            if (applied) {
                await doc.save();
                const displayPath = vscode.workspace.asRelativePath(targetUri);
                vscode.window.showInformationMessage(`⚡ Successfully applied changes to: ${displayPath}`);
                if (this._view) {
                    this._view.webview.postMessage({ type: 'fileAppliedSuccess', filePath: displayPath });
                }
                return true;
            } else {
                vscode.window.showErrorMessage(`Failed to apply changes to ${vscode.workspace.asRelativePath(targetUri)}`);
                return false;
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Error applying code: ${error.message}`);
            return false;
        }
    }

    async _applyAllChanges(edits) {
        if (!edits || !Array.isArray(edits) || edits.length === 0) {
            vscode.window.showWarningMessage("No file edits detected to apply.");
            return;
        }

        let successCount = 0;
        for (const item of edits) {
            const ok = await this._applyFileChanges(item.filePath, item.code);
            if (ok) successCount++;
        }

        if (successCount > 0) {
            vscode.window.showInformationMessage(`🚀 Codex/Claude Auto-Apply: Applied ${successCount}/${edits.length} file change(s) across codebase!`);
        }
    }

    async _openDiffViewer(filePath, newContent) {
        try {
            const targetUri = this._resolveTargetUri(filePath);
            if (!targetUri) {
                vscode.window.showErrorMessage("No target file found for diff review.");
                return;
            }

            const fileName = path.basename(targetUri.fsPath);
            const previewUri = vscode.Uri.parse(`g4f-diff://preview/${encodeURIComponent(fileName)}?t=${Date.now()}`);
            diffContentProvider.setDocumentContent(previewUri, newContent);

            const title = `${fileName} (Original ↔ AI Suggestion)`;
            await vscode.commands.executeCommand('vscode.diff', targetUri, previewUri, title);

            // Ask user if they'd like to apply directly from notification
            const choice = await vscode.window.showInformationMessage(
                `Reviewing changes for ${fileName}. Apply these changes to your codebase?`,
                "⚡ Apply Changes",
                "Cancel"
            );

            if (choice === "⚡ Apply Changes") {
                await this._applyFileChanges(filePath, newContent);
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Error opening diff: ${error.message}`);
        }
    }

    _insertCodeIntoEditor(code) {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage("No active code editor found.");
            return;
        }

        editor.edit(editBuilder => {
            if (!editor.selection.isEmpty) {
                editBuilder.replace(editor.selection, code);
            } else {
                editBuilder.insert(editor.selection.active, code);
            }
        });
    }

    sendQuickPrompt(action) {
        if (!this._view) return;
        this._view.show?.(true);

        let prompt = "";
        switch (action) {
            case 'explain':
                prompt = "Explain this code clearly step-by-step:";
                break;
            case 'refactor':
                prompt = "Refactor and optimize this code for readability and performance. Implement the changes in full:";
                break;
            case 'fix':
                prompt = "Find bugs, security flaws, or edge cases in this code and implement the complete fix:";
                break;
            case 'tests':
                prompt = "Write comprehensive unit tests for this code:";
                break;
            default:
                prompt = action;
        }

        this._handleUserMessage(prompt, undefined, true);
    }

    clear() {
        this._history = [];
        if (this._view) {
            this._view.webview.postMessage({ type: 'clearChat' });
        }
    }

    _getHtmlForWebview() {
        const htmlPath = path.join(this._context.extensionPath, 'media', 'chat.html');
        if (fs.existsSync(htmlPath)) {
            return fs.readFileSync(htmlPath, 'utf8');
        }
        return `<!DOCTYPE html><html><body><h3>g4f Chat</h3><p>chat.html not found.</p></body></html>`;
    }
}

/**
 * Extension Activation
 */
function activate(context) {
    console.log('g4f AI Assistant is now active with Codex-style codebase modifications.');

    // Register Diff Content Provider
    context.subscriptions.push(
        vscode.workspace.registerTextDocumentContentProvider('g4f-diff', diffContentProvider)
    );

    const provider = new G4FChatViewProvider(context);

    // Register Webview View
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(G4FChatViewProvider.viewType, provider)
    );

    // 1. Ask AI command
    const askCmd = vscode.commands.registerCommand('g4f.askAI', async () => {
        const prompt = await vscode.window.showInputBox({
            prompt: "Ask g4f AI a question or instruct code modifications",
            placeHolder: "e.g., Implement dark mode, refactor authentication, fix null pointer..."
        });

        if (!prompt) return;

        vscode.commands.executeCommand('g4f.chatView.focus');
        provider._handleUserMessage(prompt, undefined, true);
    });

    // 2. Explain Code command
    const explainCmd = vscode.commands.registerCommand('g4f.explainCode', () => {
        vscode.commands.executeCommand('g4f.chatView.focus');
        provider.sendQuickPrompt('explain');
    });

    // 3. Refactor Code command
    const refactorCmd = vscode.commands.registerCommand('g4f.refactorCode', () => {
        vscode.commands.executeCommand('g4f.chatView.focus');
        provider.sendQuickPrompt('refactor');
    });

    // 4. Fix Bugs command
    const fixCmd = vscode.commands.registerCommand('g4f.fixBugs', () => {
        vscode.commands.executeCommand('g4f.chatView.focus');
        provider.sendQuickPrompt('fix');
    });

    // 5. Open Chat View
    const openChatCmd = vscode.commands.registerCommand('g4f.openChat', () => {
        vscode.commands.executeCommand('g4f.chatView.focus');
    });

    // 6. Clear Chat
    const clearChatCmd = vscode.commands.registerCommand('g4f.clearChat', () => {
        provider.clear();
    });

    context.subscriptions.push(askCmd, explainCmd, refactorCmd, fixCmd, openChatCmd, clearChatCmd);
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
