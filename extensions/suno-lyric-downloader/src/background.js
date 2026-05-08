chrome.action.setPopup({ popup: 'popup.html' });

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (!changeInfo.url) return;

  let url;
  try {
    url = new URL(changeInfo.url);
  } catch {
    return;
  }

  if (!url.hostname.includes('suno.com')) return;

  const match = url.pathname.match(/^\/song\/([^/]+)/);
  if (!match) return;

  const songId = match[1];
  chrome.tabs.sendMessage(tabId, {
    action: 'URL_CHANGED',
    url: changeInfo.url,
    songId,
  }).catch(() => {});
});
