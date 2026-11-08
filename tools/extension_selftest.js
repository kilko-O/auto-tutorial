// 扩展逻辑自测：用假的 chrome API 驱动 background.js
// 目的：在没有浏览器的情况下验证"事件登记不丢、截图按批次分配、结束时导出 events.json"
// 运行：node tools/extension_selftest.js

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const BG = fs.readFileSync(path.join(ROOT, "extension", "background.js"), "utf8");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const storage = {};
const downloads = [];
const actionListeners = [];
const messageListeners = [];

globalThis.chrome = {
  storage: {
    local: {
      get: async (keys) => {
        const out = {};
        for (const k of Array.isArray(keys) ? keys : [keys]) {
          if (k in storage) out[k] = storage[k];
        }
        return out;
      },
      set: async (obj) => Object.assign(storage, obj),
    },
  },
  action: {
    setBadgeText: () => {},
    setBadgeBackgroundColor: () => {},
    onClicked: { addListener: (fn) => actionListeners.push(fn) },
  },
  tabs: {
    query: async () => [],
    sendMessage: async () => {},
    captureVisibleTab: async () => "data:image/png;base64,AAAA",
  },
  downloads: {
    download: async (opts) => {
      downloads.push(opts);
      return downloads.length;
    },
  },
  runtime: { onMessage: { addListener: (fn) => messageListeners.push(fn) } },
};

vm.runInThisContext(BG, { filename: "background.js" });

const sender = { tab: { id: 1, windowId: 9 } };

function emit(type, label, x, y) {
  for (const fn of messageListeners) {
    fn(
      { kind: "ui-event", type, url: "https://jw.example.edu/login", title: "登录",
        vw: 1440, vh: 900, dpr: 1, x, y, tag: "button", label, value: type === "input" ? "20230001" : "" },
      sender
    );
  }
}

(async () => {
  await sleep(60); // 等 init 结束

  // 开始录制
  await actionListeners[0]();
  await sleep(30);

  // 三次操作，前两次间隔很近（同一批截图），第三次单独一批
  emit("click", "登录", 265, 444);
  await sleep(100);
  emit("input", "学号", 360, 260);
  await sleep(900); // 等第一批截图
  emit("click", "提交", 265, 746);
  await sleep(900);

  // 结束录制 -> 触发导出
  await actionListeners[0]();
  await sleep(200);

  const events = storage.events || [];
  const pngDownloads = downloads.filter((d) => d.filename.endsWith(".png"));
  const jsonDownload = downloads.find((d) => d.filename.endsWith("events.json"));

  const problems = [];
  if (events.length !== 3) problems.push(`事件数应为 3，实际 ${events.length}`);
  if (pngDownloads.length !== 2) problems.push(`截图批次数应为 2，实际 ${pngDownloads.length}`);
  if (events.some((e) => !e.shot)) problems.push("有事件没分到截图");
  if (events[0].shot !== events[1].shot) problems.push("前两条事件应共用一张截图");
  if (!jsonDownload) problems.push("没有导出 events.json");

  if (jsonDownload) {
    const raw = decodeURIComponent(jsonDownload.url.split(",").slice(1).join(","));
    const payload = JSON.parse(raw);
    if (!Array.isArray(payload.events) || payload.events.length !== 3) {
      problems.push("导出的 events.json 内容不对");
    }
    if (payload.events[0].ts >= payload.events[2].ts) problems.push("事件时间戳顺序不对");
  }

  if (problems.length) {
    console.log("FAIL");
    problems.forEach((p) => console.log(" -", p));
    process.exit(1);
  }
  console.log("PASS：3 条事件 / 2 批截图 / 1 份导出，时间戳递增");
})();
