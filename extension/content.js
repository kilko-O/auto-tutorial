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

function clean(text) {
  return String(text == null ? "" : text)
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 40);
}

// 取元素的"人话名字"：优先无障碍标签、占位符，其次关联的 <label>，最后才是可见文字。
// 注意：输入框的 value 是用户输入的内容，不能当名字用。
function labelOf(el) {
  if (!el || !el.getAttribute) return "";

  const attr =
    el.getAttribute("aria-label") ||
    el.getAttribute("placeholder") ||
    el.getAttribute("title") ||
    el.getAttribute("alt");
  if (attr) return clean(attr);

  if (el.id) {
    try {
      const bound = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (bound && bound.innerText) return clean(bound.innerText);
    } catch (e) {
      // CSS.escape 在极老版本不存在，忽略
    }
  }

  const wrapper = typeof el.closest === "function" ? el.closest("label") : null;
  if (wrapper && wrapper.innerText) return clean(wrapper.innerText);

  if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT") {
    return clean(el.name || el.type || "");
  }

  return clean(el.innerText || el.textContent);
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
    // 扩展重载后会有短暂失效，忽略
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

// change 在输入框失焦 / 选择项改动时触发，正好对应"完成这一步操作"的时刻
document.addEventListener(
  "change",
  (e) => {
    if (!recording) return;
    const el = e.target;
    if (!el) return;

    const rect = typeof el.getBoundingClientRect === "function" ? el.getBoundingClientRect() : null;
    let value = "";
    if (el.type === "checkbox" || el.type === "radio") {
      value = el.checked ? "勾选" : "取消勾选";
    } else if (el.tagName === "SELECT") {
      const opt = el.options && el.options[el.selectedIndex];
      value = opt ? opt.text : String(el.value || "");
    } else {
      value = String(el.value || "");
    }

    send("input", {
      x: rect ? Math.round(rect.left + rect.width / 2) : 0,
      y: rect ? Math.round(rect.top + rect.height / 2) : 0,
      tag: el.tagName ? el.tagName.toLowerCase() : "",
      label: labelOf(el),
      value: value.replace(/\s+/g, " ").trim().slice(0, 30),
    });
  },
  true
);
