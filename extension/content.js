// 页面端：监听点击与输入，把事件发给 background

let recording = false;

const BADGE_ID = "__auto_tutorial_rec_badge__";

function renderBadge() {
  let badge = document.getElementById(BADGE_ID);
  if (recording) {
    if (!badge) {
      badge = document.createElement("div");
      badge.id = BADGE_ID;
      badge.style.cssText =
        "position:fixed;top:12px;right:12px;z-index:2147483647;background:rgba(217,48,37,.92);color:#fff;font:13px/1.4 sans-serif;padding:6px 10px;border-radius:6px;pointer-events:none;box-shadow:0 2px 8px rgba(0,0,0,.25)";
      badge.textContent = "● 录制中";
      document.documentElement.appendChild(badge);
    }
  } else if (badge) {
    badge.remove();
  }
}

chrome.storage.local.get("recording", (data) => {
  recording = !!data.recording;
  renderBadge();
  console.log("[auto-tutorial] content.js 已加载：", location.href);
});

chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.kind === "recording-state") {
    recording = !!msg.recording;
    renderBadge();
  }
});

function clean(text) {
  return String(text == null ? "" : text)
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 40);
}

function textOf(el) {
  if (!el) return "";
  return clean(el.innerText || el.textContent || el.value || "");
}

// 点到的常常是按钮里的 span/图标，向上找到真正可点击的容器，框才画得准
function actionable(el) {
  if (!el || !el.closest) return el;
  return (
    el.closest("button, a, label, [role='button'], input, select, textarea, li, td") || el
  );
}

function rectOf(el) {
  if (!el || typeof el.getBoundingClientRect !== "function") return null;
  const r = el.getBoundingClientRect();
  if (!r || !(r.width > 0) || !(r.height > 0)) return null;
  return {
    x: Math.round(r.left + r.width / 2),
    y: Math.round(r.top + r.height / 2),
    w: Math.round(r.width),
    h: Math.round(r.height),
  };
}

// 取元素的"人话名字"：优先无障碍标签、占位符，其次关联的 <label>，
// 再向上找最近的可点击祖先文字。输入框的 value 是用户输入，不能当名字。
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
      if (bound && textOf(bound)) return textOf(bound);
    } catch (e) {
      // 极老浏览器没有 CSS.escape，忽略
    }
  }

  const wrapper = typeof el.closest === "function" ? el.closest("label") : null;
  if (wrapper && textOf(wrapper)) return textOf(wrapper);

  if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT") {
    return clean(el.name || el.type || "");
  }

  let cur = el;
  for (let i = 0; i < 4 && cur && cur !== document.body; i++) {
    const t = textOf(cur);
    if (t) return t;
    cur = cur.parentElement;
  }
  return "";
}

function send(type, payload) {
  try {
    console.log("[auto-tutorial] 上报事件：", type, payload.label || "");
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
    const target = actionable(e.target);
    const r = rectOf(target) || rectOf(e.target) || {
      x: Math.round(e.clientX),
      y: Math.round(e.clientY),
      w: 0,
      h: 0,
    };
    send("click", {
      x: r.x,
      y: r.y,
      w: r.w,
      h: r.h,
      tag: target && target.tagName ? target.tagName.toLowerCase() : "",
      label: labelOf(target),
    });
  },
  true
);

// change 在输入框失焦 / 选择项改动 / 勾选时触发，对应"完成这一步操作"的时刻
document.addEventListener(
  "change",
  (e) => {
    if (!recording) return;
    const el = e.target;
    if (!el) return;

    const r = rectOf(el) || {};
    const isCheck = el.type === "checkbox" || el.type === "radio";

    let type = "input";
    let value = "";
    if (isCheck) {
      type = "click";
      value = el.checked ? "勾选" : "取消勾选";
    } else if (el.tagName === "SELECT") {
      const opt = el.options && el.options[el.selectedIndex];
      value = opt ? opt.text : String(el.value || "");
    } else {
      value = String(el.value || "");
    }

    send(type, {
      x: r.x ?? 0,
      y: r.y ?? 0,
      w: r.w ?? 0,
      h: r.h ?? 0,
      tag: el.tagName ? el.tagName.toLowerCase() : "",
      label: labelOf(el),
      value: value.replace(/\s+/g, " ").trim().slice(0, 30),
    });
  },
  true
);
