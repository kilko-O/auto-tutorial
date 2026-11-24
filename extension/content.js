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

// 容器把多个输入框/按钮的文字拼在一起（如「+86 发送验证码 请输入验证码」），不算元素名
function isAggregated(text) {
  const t = String(text || "");
  if (!t) return false;
  if (t.split(" ").filter(Boolean).length >= 2) return true;
  return /请输入|请设置|请填写/.test(t) && t.length > 6;
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

// 输入框本身往往只有一行文字高（~20px），向上找单行包装容器（一整行 ~44px）；
// 太高的祖先包了账号+密码多行，不能用，高度上限 64px。
function fieldBox(el) {
  const field = el && el.closest ? el.closest("input, textarea, select") : null;
  if (!field) return rectOf(el);
  let cur = field;
  let best = rectOf(field);
  for (let i = 0; i < 3 && cur.parentElement; i++) {
    const r = rectOf(cur.parentElement);
    if (r && r.h >= 28 && r.h <= 64 && (!best || r.w >= best.w)) best = r;
    cur = cur.parentElement;
  }
  return best || rectOf(field);
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
    if (t && !isAggregated(t)) return t;
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
    const raw = e.target;
    const target = actionable(raw);
    const rawRect = /^(INPUT|TEXTAREA|SELECT)$/.test(raw.tagName || "")
      ? fieldBox(raw)
      : rectOf(raw);
    const actRect = target === raw ? null : rectOf(target);
    let r;
    if (rawRect && actRect) {
      // 祖先容器比原始元素大太多（外面套了大卡片/弹窗），保留更小的原始元素框
      r = actRect.w * actRect.h <= 3 * rawRect.w * rawRect.h ? actRect : rawRect;
    } else {
      r = actRect || rawRect || {
        x: Math.round(e.clientX),
        y: Math.round(e.clientY),
        w: 0,
        h: 0,
      };
    }
    const tagName = target && target.tagName ? target.tagName.toLowerCase() : "";
    // 点到了大容器空白处（表单/卡片背景）：不用整个容器的大框，退回点击位置的固定小框
    const GENERIC = new Set(["div", "form", "section", "span", "ul", "ol", "p", "article"]);
    let box = r;
    if (GENERIC.has(tagName) && r && r.h > 80) {
      box = { x: Math.round(e.clientX), y: Math.round(e.clientY), w: 210, h: 96 };
    }
    send("click", {
      x: box.x,
      y: box.y,
      w: box.w,
      h: box.h,
      tag: tagName,
      label: labelOf(target),
    });
  },
  true
);

// input 在打字过程中持续触发，400ms 防抖后上报一次，避免每个按键都生成一条事件；
// 失焦时的 change 再补一条，处理链会把同一输入框的两次输入合并为一步。
const INPUT_DEBOUNCE_MS = 400;
const inputTimers = new WeakMap();

document.addEventListener(
  "input",
  (e) => {
    if (!recording) return;
    const el = e.target;
    if (!el || !el.tagName) return;
    if (!/^(INPUT|TEXTAREA)$/.test(el.tagName)) return;
    if (el.type === "checkbox" || el.type === "radio" || el.type === "hidden") return;

    clearTimeout(inputTimers.get(el));
    inputTimers.set(
      el,
      setTimeout(() => {
        if (!recording) return;
        const r = fieldBox(el) || {};
        send("input", {
          x: r.x ?? 0,
          y: r.y ?? 0,
          w: r.w ?? 0,
          h: r.h ?? 0,
          tag: el.tagName.toLowerCase(),
          label: labelOf(el),
          value: String(el.value || "").replace(/\s+/g, " ").trim().slice(0, 30),
        });
      }, INPUT_DEBOUNCE_MS)
    );
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

    const r = fieldBox(el) || {};
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
