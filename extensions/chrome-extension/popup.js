// popup.js - g4f AI & Vision Assistant Chrome Extension Logic

const DEFAULT_SERVER = "http://127.0.0.1:1337";

let serverUrl = DEFAULT_SERVER;
let attachedImageData = null;

const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const modelSelect = document.getElementById("modelSelect");
const promptInput = document.getElementById("promptInput");
const sendBtn = document.getElementById("sendBtn");
const responseCard = document.getElementById("responseCard");
const responseContent = document.getElementById("responseContent");
const copyBtn = document.getElementById("copyBtn");
const serverLabel = document.getElementById("serverLabel");
const imageFileInput = document.getElementById("imageFileInput");
const imagePreviewContainer = document.getElementById("imagePreviewContainer");
const imagePreview = document.getElementById("imagePreview");
const imagePreviewName = document.getElementById("imagePreviewName");
const removeImgBtn = document.getElementById("removeImgBtn");
const webSearchToggle = document.getElementById("webSearchToggle");

// Markdown formatter
function formatMarkdown(text) {
  let formatted = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, function(match, lang, code) {
    const cleanCode = code.trim();
    return `<pre><code>${cleanCode.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`;
  });
  formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
  formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  formatted = formatted.replace(/\n/g, '<br/>');
  return formatted;
}

// Load stored settings and selection
document.addEventListener("DOMContentLoaded", async () => {
  chrome.storage.local.get(["serverUrl", "defaultModel", "lastSelection", "lastAction"], async (data) => {
    if (data.serverUrl) {
      serverUrl = data.serverUrl.replace(/\/+$/, "");
    }
    serverLabel.innerText = `Server: ${serverUrl.replace(/^https?:\/\//, '')}`;

    if (data.defaultModel) {
      modelSelect.value = data.defaultModel;
    }

    if (data.webSearchEnabled !== undefined && webSearchToggle) {
      webSearchToggle.checked = Boolean(data.webSearchEnabled);
    }

    if (data.lastSelection) {
      promptInput.value = data.lastSelection;
      chrome.storage.local.remove(["lastSelection"]);
    } else {
      try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.id) {
          const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: () => window.getSelection().toString()
          });
          if (results && results[0] && results[0].result) {
            promptInput.value = results[0].result;
          }
        }
      } catch (e) {
        console.log("Could not auto-grab selection:", e);
      }
    }

    checkServerStatus();
  });

  if (webSearchToggle) {
    webSearchToggle.addEventListener("change", () => {
      chrome.storage.local.set({ webSearchEnabled: webSearchToggle.checked });
    });
  }
});

// Image attachment handling
imageFileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(event) {
    attachedImageData = event.target.result;
    imagePreview.src = attachedImageData;
    imagePreviewName.innerText = file.name;
    imagePreviewContainer.style.display = "flex";
  };
  reader.readAsDataURL(file);
});

removeImgBtn.addEventListener("click", () => {
  attachedImageData = null;
  imageFileInput.value = "";
  imagePreviewContainer.style.display = "none";
});

// Quick action buttons
document.querySelectorAll(".pill").forEach(btn => {
  btn.addEventListener("click", () => {
    const actionPrefix = btn.getAttribute("data-prompt");
    const current = promptInput.value.trim();
    if (current && !current.startsWith(actionPrefix)) {
      promptInput.value = `${actionPrefix}\n\n${current}`;
    } else {
      promptInput.value = actionPrefix;
    }
    promptInput.focus();
  });
});

// Check Server Connection
async function checkServerStatus() {
  try {
    statusDot.className = "status-dot";
    statusText.innerText = "Checking...";
    
    const res = await fetch(`${serverUrl}/v1/models`, { method: "GET" });
    if (res.ok) {
      statusDot.className = "status-dot online";
      statusText.innerText = "Online";
    } else {
      statusDot.className = "status-dot online";
      statusText.innerText = "Connected";
    }
  } catch (err) {
    statusDot.className = "status-dot offline";
    statusText.innerText = "Offline";
  }
}

// System prompt tailored for Hybrid Computer Vision & Diffusion Pipeline Architecture
const CV_ARCHITECT_SYSTEM_PROMPT = `You are an expert AI System Architect and Senior Computer Vision & Diffusion Engineer (specializing in PyTorch, Diffusers, OpenCV, SAM / SAM 2, ControlNet, Inpainting, Real-ESRGAN, YOLO, and FastAPI).
When asked to design, scaffold, or generate vision & diffusion generation/editing systems:
1. Emphasize multi-stage deterministic + diffusion pipelines: (Image/Prompt -> Preprocessing -> SAM/YOLO Segmentation -> ControlNet Conditioning -> Diffusion Inpainting / Img2Img -> Super-Resolution -> Quality Check).
2. Produce production-grade, modular Python and frontend code for precise object addition, object removal, background preservation, and high-accuracy visual generation.
3. Structure validation logic with confidence scores and alert thresholds.`;

// Detect image generation requests
function isImagePrompt(text, model) {
  if (model === "flux" || model === "dall-e-3" || model === "sdxl-turbo") {
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

  if (clean.startsWith("/image") || clean.startsWith("/img")) {
    return true;
  }

  clean = clean.replace(/^(?:to\s+)?(?:please\s+)?(?:can\s+you\s+)?/i, '').trim();

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

function optimizeImagePrompt(prompt) {
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

// Generate image via /v1/images/generations
async function generateImage(promptText, model) {
  let cleanPrompt = promptText.replace(/^\/(?:image|img)\s*/i, '').trim();
  cleanPrompt = cleanPrompt.replace(/^(?:to\s+)?(?:generate|create|draw|paint|make|render|produce|show me|give me|i want)\s+(?:an?\s+)?(?:image|picture|photo|illustration|drawing|map|diagram|wallpaper|art|poster|sketch|render|portrait|logo)?\s*(?:of|showing|depicting|with|for)?\s*/i, '').trim();
  cleanPrompt = cleanPrompt.replace(/^(?:image|picture|photo|illustration|drawing|map|diagram)\s+(?:of|showing|depicting|with|for)\s*/i, '').trim();
  cleanPrompt = cleanPrompt.replace(/^(?:draw|paint|illustrate|render)\s+(?:an?\s+)?/i, '').trim();
  if (!cleanPrompt) cleanPrompt = promptText;

  const optimizedPrompt = optimizeImagePrompt(cleanPrompt);

  responseContent.innerHTML = `<em>🎨 Generating AI image with Flux for: "${cleanPrompt}"...</em>`;

  const selectedModel = (model === "flux" || model === "dall-e-3") ? model : "flux";
  let imageUrl = "";
  let revisedPrompt = cleanPrompt;

  try {
    const response = await fetch(`${serverUrl}/v1/images/generations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer secret"
      },
      body: JSON.stringify({
        prompt: optimizedPrompt,
        model: selectedModel
      })
    });

    if (response.ok) {
      const data = await response.json();
      if (data.data && data.data[0] && data.data[0].url) {
        imageUrl = data.data[0].url;
        revisedPrompt = data.data[0].revised_prompt || cleanPrompt;
      }
    } else {
      console.warn("Server image generation returned status", response.status, "using direct Flux fallback");
    }
  } catch (backendErr) {
    console.warn("Backend error, using direct Flux fallback:", backendErr);
  }

  // Resilient fallback: If server hit upstream rate limit (429/500), load direct Flux image
  if (!imageUrl) {
    const encoded = encodeURIComponent(optimizedPrompt);
    imageUrl = `https://gen.pollinations.ai/image/${encoded}?model=flux&nologo=true`;
  }

  responseContent.innerHTML = `
    <div class="image-result-card">
      <div><strong>Prompt:</strong> <em>${cleanPrompt}</em></div>
      <img class="image-result-preview" src="${imageUrl}" alt="${cleanPrompt}" />
      <div class="img-actions-row">
        <a href="${imageUrl}" target="_blank" download class="img-action-btn" style="background:#065f46; color:#a7f3d0; font-weight:600;">💾 Open / Download</a>
        <button class="img-action-btn" id="btnCopyImgUrl" data-url="${imageUrl}">📋 Copy Image URL</button>
        <button class="img-action-btn" id="btnCopyImgMd" data-url="${imageUrl}" data-prompt="${cleanPrompt}">📝 Copy Markdown</button>
      </div>
    </div>
  `;

  document.getElementById("btnCopyImgUrl")?.addEventListener("click", function() {
    navigator.clipboard.writeText(this.getAttribute("data-url"));
    this.innerText = "✅ Copied URL!";
    setTimeout(() => this.innerText = "📋 Copy Image URL", 2000);
  });

  document.getElementById("btnCopyImgMd")?.addEventListener("click", function() {
    const url = this.getAttribute("data-url");
    const p = this.getAttribute("data-prompt");
    navigator.clipboard.writeText(`![${p}](${url})`);
    this.innerText = "✅ Copied Markdown!";
    setTimeout(() => this.innerText = "📝 Copy Markdown", 2000);
  });
}

// Send Request
sendBtn.addEventListener("click", async () => {
  const text = promptInput.value.trim();
  if (!text && !attachedImageData) return;

  const model = modelSelect.value;

  sendBtn.disabled = true;
  sendBtn.innerText = "⏳ Processing...";
  responseCard.style.display = "flex";

  // Check if image generation request
  if (!attachedImageData && isImagePrompt(text, model)) {
    try {
      await generateImage(text, model);
    } catch (err) {
      responseContent.innerHTML = `<span style="color:#f87171;">⚠️ Image Generation Failed: ${err.message}</span><br/><small style="color:#94a3b8;">Ensure server is running on port 1337 ('python -m g4f --port 1337')</small>`;
      checkServerStatus();
    } finally {
      sendBtn.disabled = false;
      sendBtn.innerText = "⚡ Generate";
    }
    return;
  }

  const hasUrl = /https?:\/\/[^\s]+/i.test(text);
  const isWebSearch = (webSearchToggle && webSearchToggle.checked) || hasUrl;

  const isCvTask = /cv|opencv|diffuser|yolo|sam|controlnet|real-esrgan|inpainting|segmentation/i.test(text);
  const systemPrompt = isCvTask
    ? CV_ARCHITECT_SYSTEM_PROMPT
    : "You are a helpful, versatile AI assistant. When the user provides a link or asks questions requiring live or current information, use the web search / scraped results provided to give a direct, comprehensive, and accurate answer with citations.";

  responseContent.innerHTML = isWebSearch
    ? "<em>🌐 Searching the web / analyzing link and generating response...</em>"
    : "<em>Analyzing and generating response...</em>";

  let userContent = text;
  if (attachedImageData) {
    userContent = [
      { type: "text", text: text || "Analyze this image and extract all OCR, objects, and validation metadata." },
      { type: "image_url", image_url: { url: attachedImageData } }
    ];
  }

  try {
    const payload = {
      model: model,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userContent }
      ],
      stream: false
    };

    if (isWebSearch) {
      payload.web_search = true;
    }

    const response = await fetch(`${serverUrl}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer secret"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Server returned ${response.status}: ${errText}`);
    }

    const data = await response.json();
    const reply = data.choices && data.choices[0] && data.choices[0].message
      ? data.choices[0].message.content
      : JSON.stringify(data, null, 2);

    responseContent.innerHTML = formatMarkdown(reply);
  } catch (err) {
    responseContent.innerHTML = `<span style="color:#f87171;">⚠️ Request Failed: ${err.message}</span><br/><small style="color:#94a3b8;">Ensure server is running on port 1337 ('python -m g4f --port 1337')</small>`;
    checkServerStatus();
  } finally {
    sendBtn.disabled = false;
    sendBtn.innerText = "⚡ Generate";
  }
});

// Copy response button
copyBtn.addEventListener("click", () => {
  const text = responseContent.innerText;
  if (text) {
    navigator.clipboard.writeText(text).then(() => {
      copyBtn.innerText = "✅ Copied!";
      setTimeout(() => copyBtn.innerText = "📋 Copy", 2000);
    });
  }
});
