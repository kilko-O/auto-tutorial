// 采集端：录制开关、事件接收、延迟截屏、落盘
// 说明：截图走 chrome.downloads 存到下载目录的 auto-tutorial/ 子目录；
// 事件流存 chrome.storage.local，供 pipeline 读取。

const DOWNLOAD_DIR = "auto-tutorial";
const CAPTURE_DELAY_MS = 400;
const STORAGE_KEY = "events";

let recording = false;
let seq = 0;
let pendingTimer = null;

chrome.storage.local.get("recording", (data) => {
  recording = !!data.recording;
  setBadge();
});

function setBadge() {
  chrome.action.setBadgeText({ text: recording ? "REC" : "" });
  chrome.action.setBadgeBackgroundColor({ color: "#d93025" });
}

async function broadcastState() {
  const tabs = await chrome.tabs.query({});
  for (const tab of tabs) {
    if (!tab.id) continue;
    try {
      await chrome.tabs.sendMessage(tab.id, { kind: "recording-state", recording });
    } catch (e) {
      // 部分页面没有 content script，忽略即可
    }
  }
}

chrome.action.onClicked.addListener(async () => {
  recording = !recording;
  if (recording) {
    seq = 0;
    await chrome.storage.local.set({ recording: true, events: [] });
  } else {
    await chrome.storage.local.set({ recording: false });
    if (pendingTimer) {
      clearTimeout(pendingTimer);
      pendingTimer = null;
    }
  }
  setBadge();
  await broadcastState();
});

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (!msg || msg.kind !== "ui-event" || !recording) return;
  if (!sender.tab) return;

  // 防抖：400ms 内的连续操作只截一张图，事件全部保留
  if (pendingTimer) clearTimeout(pendingTimer);
  pendingTimer = setTimeout(() => {
    pendingTimer = null;
    capture(sender.tab.id, sender.tab.windowId, msg);
  }, CAPTURE_DELAY_MS);
});

async function capture(tabId, windowId, msg) {
  if (!recording) return;
  try {
    const dataUrl = await chrome.tabs.captureVisibleTab(windowId, { format: "png" });
    seq += 1;
    const stamp = Date.now();
    const filename = `${DOWNLOAD_DIR}/${String(seq).padStart(3, "0")}_${stamp}.png`;

    await chrome.downloads.download({ url: dataUrl, filename, saveAs: false });

    const record = { ...msg, seq, shot: filename, ts: stamp };
    const { events = [] } = await chrome.storage.local.get(STORAGE_KEY);
    events.push(record);
    await chrome.storage.local.set({ events });
  } catch (e) {
    console.warn("[auto-tutorial] capture failed:", e);
  }
}

// 供调试：在扩展的「检查视图」控制台里可读取
chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.kind === "get-events") {
    chrome.storage.local.get(STORAGE_KEY).then((d) => {
      console.log(JSON.stringify(d.events || [], null, 2));
    });
  }
});
