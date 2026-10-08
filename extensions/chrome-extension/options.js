// options.js - Settings logic

document.addEventListener("DOMContentLoaded", () => {
  chrome.storage.local.get(["serverUrl", "defaultModel"], (data) => {
    if (data.serverUrl) {
      document.getElementById("serverUrl").value = data.serverUrl;
    } else {
      document.getElementById("serverUrl").value = "http://127.0.0.1:1337";
    }
    if (data.defaultModel) {
      document.getElementById("defaultModel").value = data.defaultModel;
    }
  });
});

document.getElementById("saveBtn").addEventListener("click", () => {
  const serverUrl = document.getElementById("serverUrl").value.trim() || "http://127.0.0.1:1337";
  const defaultModel = document.getElementById("defaultModel").value;

  chrome.storage.local.set({ serverUrl, defaultModel }, () => {
    const status = document.getElementById("statusMsg");
    status.innerText = "Settings saved successfully!";
    setTimeout(() => status.innerText = "", 2500);
  });
});
