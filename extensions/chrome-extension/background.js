// Background service worker for g4f Chrome Extension

chrome.runtime.onInstalled.addListener(() => {
  // Create context menus for selected text
  chrome.contextMenus.create({
    id: "g4f_explain",
    title: "🤖 g4f AI: Explain Selection",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "g4f_summarize",
    title: "📝 g4f AI: Summarize",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "g4f_fix",
    title: "🔧 g4f AI: Fix Grammar / Code",
    contexts: ["selection"]
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  let action = "explain";
  if (info.menuItemId === "g4f_summarize") action = "summarize";
  if (info.menuItemId === "g4f_fix") action = "fix";

  // Store selection & action in storage so popup can load it, or open popup
  chrome.storage.local.set({
    lastSelection: info.selectionText,
    lastAction: action,
    timestamp: Date.now()
  }, () => {
    // Open action popup or trigger notification
    chrome.action.openPopup().catch(() => {
      // In case openPopup is restricted, execute content script notification
      console.log("Context menu action saved to storage.");
    });
  });
});
