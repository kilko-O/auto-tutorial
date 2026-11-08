// 页面端：监听点击与输入，把事件发给 background

let recording = false;

chrome.storage.local.get("recording", (data) => {
  recording = !!data.recording;
});

chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.kind === "recording-state") {
    recording = !!msg.recording;
  }
});

function labelOf(el) {
  if (!el) return "";
  const raw =
    el.innerText ||
    el.value ||
    el.getAttribute("aria-label") ||
    el.getAttribute("placeholder") ||
    el.getAttribute("title") ||
    "";
  return String(raw).replace(/\s+/g, " ").trim().slice(0, 40);
}

function send(type, payload) {
  try {
    chrome.runtime.sendMessage({
      kind: "ui-event",
      type,
      url: location.href,
      title: document.title,
      vw: window.innerWidth,
      vh: window.innerHeight,
      dpr: window.devicePixelRatio,
      ...payload,
    });
  } catch (e) {
    // 扩展被重载后会有短暂失效，忽略
  }
}

document.addEventListener(
  "click",
  (e) => {
    if (!recording) return;
    const el = e.target;
    send("click", {
      x: Math.round(e.clientX),
      y: Math.round(e.clientY),
      tag: el && el.tagName ? el.tagName.toLowerCase() : "",
      label: labelOf(el),
    });
  },
  true
);

document.addEventListener(
  "change",
  (e) => {
    if (!recording) return;
    const el = e.target;
    if (!el) return;
    const rect = typeof el.getBoundingClientRect === "function" ? el.getBoundingClientRect() : null;
    send("input", {
      x: rect ? Math.round(rect.left + rect.width / 2) : 0,
      y: rect ? Math.round(rect.top + rect.height / 2) : 0,
      tag: el.tagName ? el.tagName.toLowerCase() : "",
      label: labelOf(el),
      value: String(el.value || "").slice(0, 30),
    });
  },
  true
);
