// 采集端：录制开关、事件登记、延迟截屏、导出事件流
//
// 关键设计：
// 1. 事件一到达就登记（ts 用真实时间），截图与事件解耦，避免"防抖只留下最后一条"的丢事件问题；
// 2. 截图按批次进行：一批事件共用一个 shot 文件名，截图失败时该批事件 shot 留空，pipeline 会告警；
// 3. 结束录制时自动把整段事件流写成 events.json 下载到 auto-tutorial/ 目录，直接喂给 pipeline。

const DOWNLOAD_DIR = "auto-tutorial";
// Chrome 限制每秒最多 2 次 captureVisibleTab，700ms 防抖留出余量
const CAPTURE_DELAY_MS = 700;
const STORAGE_KEY = "events";

let recording = false;
let events = []; // 本次录制全部事件
let batch = []; // 尚未分配截图的事件
let seq = 0;
let lastWindowId = null;
let captureTimer = null;
let persistTimer = null;

init();

async function init() {
  const data = await chrome.storage.local.get(["recording", STORAGE_KEY]);
  recording = !!data.recording;
  events = Array.isArray(data[STORAGE_KEY]) ? data[STORAGE_KEY] : [];
  seq = events.reduce((max, e) => Math.max(max, Number(e.seq) || 0), 0);
  setBadge();
}

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
      // 页面没有 content script，忽略
    }
  }
}

chrome.action.onClicked.addListener(async () => {
  if (recording) {
    await stopRecording();
  } else {
    await startRecording();
  }
});

async function startRecording() {
  recording = true;
  events = [];
  batch = [];
  seq = 0;
  clearTimers();
  await chrome.storage.local.set({ recording: true, [STORAGE_KEY]: [] });
  setBadge();
  await broadcastState();
}

async function stopRecording() {
  recording = false;
  clearTimers();
  if (batch.length) await flushBatch(true);
  await persistNow();
  await chrome.storage.local.set({ recording: false });
  setBadge();
  await broadcastState();
  await exportEvents();
}

function clearTimers() {
  if (captureTimer) {
    clearTimeout(captureTimer);
    captureTimer = null;
  }
  if (persistTimer) {
    clearTimeout(persistTimer);
    persistTimer = null;
  }
}

async function persistNow() {
  await chrome.storage.local.set({ [STORAGE_KEY]: events });
}

function schedulePersist() {
  if (persistTimer) return;
  persistTimer = setTimeout(() => {
    persistTimer = null;
    persistNow().catch(() => {});
  }, 200);
}

function scheduleCapture(windowId) {
  lastWindowId = windowId ?? lastWindowId;
  if (captureTimer) clearTimeout(captureTimer);
  captureTimer = setTimeout(() => {
    captureTimer = null;
    flushBatch().catch(() => {});
  }, CAPTURE_DELAY_MS);
}

async function flushBatch(force = false) {
  if (!force && !recording) return;
  if (!batch.length) return;

  const targets = batch;
  batch = [];
  const windowId = lastWindowId;

  try {
    const dataUrl = await chrome.tabs.captureVisibleTab(windowId, { format: "png" });
    const stamp = Date.now();
    const name = `${DOWNLOAD_DIR}/${String(targets[0].seq).padStart(3, "0")}_${stamp}.png`;
    await chrome.downloads.download({ url: dataUrl, filename: name, saveAs: false });
    for (const ev of targets) ev.shot = name;
    await persistNow();
  } catch (e) {
    // 截图失败不影响事件本身，shot 留空，pipeline 会报"缺少截图"
    console.warn("[auto-tutorial] capture failed:", e);
    schedulePersist();
  }
}

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (!msg || !msg.kind) return;

  if (msg.kind === "get-events") {
    console.log(JSON.stringify(events, null, 2));
    return;
  }

  if (msg.kind === "export-events") {
    exportEvents();
    return;
  }

  if (msg.kind !== "ui-event") return;
  if (!recording || !sender.tab) return;

  seq += 1;
  const record = {
    seq,
    ts: Date.now(),
    type: msg.type || "click",
    url: msg.url || "",
    title: msg.title || "",
    vw: msg.vw || 0,
    vh: msg.vh || 0,
    dpr: msg.dpr || 1,
    x: msg.x || 0,
    y: msg.y || 0,
    tag: msg.tag || "",
    label: msg.label || "",
    value: msg.value || "",
    shot: "",
  };

  events.push(record);
  batch.push(record);
  schedulePersist();
  scheduleCapture(sender.tab.windowId);
});

async function exportEvents() {
  const payload = {
    version: 1,
    exported_at: new Date().toISOString(),
    download_dir: DOWNLOAD_DIR,
    events,
  };
  const json = JSON.stringify(payload, null, 2);
  const url = "data:application/json;charset=utf-8," + encodeURIComponent(json);

  try {
    await chrome.downloads.download({
      url,
      filename: `${DOWNLOAD_DIR}/events.json`,
      saveAs: false,
      conflictAction: "overwrite",
    });
    console.log(`[auto-tutorial] 已导出 ${events.length} 条事件`);
  } catch (e) {
    console.warn("[auto-tutorial] 导出失败：", e);
  }
}
