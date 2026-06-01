chrome.action.setPopup({ popup: 'popup.html' });

function notifySongChange(tabId, rawUrl) {
  let url;
  try {
    url = new URL(rawUrl);
  } catch {
    return;
  }
  if (!url.hostname.includes('suno.com')) return;
  const match = url.pathname.match(/^\/song\/([^/]+)/);
  if (!match) return;
  chrome.tabs.sendMessage(tabId, {
    action: 'URL_CHANGED',
    url: rawUrl,
    songId: match[1],
  }).catch(() => {});
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.url) notifySongChange(tabId, changeInfo.url);
});

// SPA pushState/replaceState는 onUpdated를 통해 전달되지만,
// content script에서 직접 보낸 URL_NAVIGATE 메시지도 수신하여 이중 보호
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.action === 'URL_NAVIGATE' && sender.tab?.id) {
    notifySongChange(sender.tab.id, msg.url);
  }
});
