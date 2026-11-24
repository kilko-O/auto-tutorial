"""步骤列表 -> 文档

默认输出 Markdown；装了 python-docx 时也可以直接出 Word；另支持静态 HTML。
"""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path


def render_markdown(steps, out_path: str | Path, title: str, image_dir: str = "steps") -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"# {title}", ""]
    lines.append(f"> 共 {len(steps)} 个步骤 · 生成于 {datetime.now():%Y-%m-%d %H:%M}")
    lines.append("")

    for step in steps:
        lines.append(f"## {step.index}. {step.action_text}")
        lines.append("")
        if step.image:
            lines.append(f"![步骤 {step.index}]({image_dir}/{step.image})")
        else:
            lines.append("> 缺少对应截图")
        lines.append("")

    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_path


def render_html(steps, out_path: str | Path, title: str, image_dir: str = "steps") -> Path:
    """导出单文件静态 HTML，图片按相对路径引用 steps/ 目录。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cards = []
    for step in steps:
        if step.image:
            media = f'<img src="{escape(f"{image_dir}/{step.image}")}" alt="步骤 {step.index}">'
        else:
            media = '<p class="missing">缺少对应截图</p>'
        cards.append(
            "<section class=\"step\">"
            f"<h2><span class=\"no\">{step.index}</span> {escape(step.action_text)}</h2>"
            f"{media}</section>"
        )

    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
  body {{ margin: 0; background: #f3f4f6; color: #1f2937;
         font-family: "Microsoft YaHei", system-ui, sans-serif; }}
  main {{ max-width: 860px; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ font-size: 28px; margin: 0 0 8px; }}
  .meta {{ color: #6b7280; margin: 0 0 28px; }}
  .step {{ background: #fff; border-radius: 12px; padding: 20px 22px;
          margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .step h2 {{ font-size: 18px; margin: 0 0 14px; display: flex; align-items: center; gap: 10px; }}
  .no {{ display: inline-flex; align-items: center; justify-content: center;
        width: 26px; height: 26px; border-radius: 50%; background: #d93025;
        color: #fff; font-size: 15px; flex: none; }}
  .step img {{ max-width: 100%; border: 1px solid #e5e7eb; border-radius: 8px; }}
  .missing {{ color: #9ca3af; }}
</style>
</head>
<body>
<main>
  <h1>{escape(title)}</h1>
  <p class="meta">共 {len(steps)} 个步骤 · 生成于 {datetime.now():%Y-%m-%d %H:%M}</p>
  {''.join(cards)}
</main>
</body>
</html>"""

    out_path.write_text(doc, encoding="utf-8")
    return out_path


def render_docx(steps, out_path: str | Path, title: str, image_dir: str = "steps") -> Path | None:
    """导出 Word；未安装 python-docx 时返回 None。"""
    try:
        from docx import Document
        from docx.shared import Cm
    except ImportError:
        return None

    out_path = Path(out_path)
    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph(f"共 {len(steps)} 个步骤，生成于 {datetime.now():%Y-%m-%d %H:%M}")

    base = out_path.parent
    for step in steps:
        doc.add_heading(f"{step.index}. {step.action_text}", level=2)
        image_path = base / image_dir / step.image
        if step.image and image_path.exists():
            doc.add_picture(str(image_path), width=Cm(14))
        else:
            doc.add_paragraph("缺少对应截图")

    doc.save(out_path)
    return out_path


def render_review(steps, out_path: str | Path, title: str, image_dir: str = "steps") -> Path:
    """生成人工复核页：展示成品标注图，可删步、改文案、手动框选马赛克，导出 steps.json。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = [s.to_dict() for s in steps]
    embedded = json.dumps(payload, ensure_ascii=False, indent=2).replace("<", "\\u003c")

    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>复核 · {escape(title)}</title>
<style>
  body {{ margin: 0; background: #f3f4f6; color: #1f2937;
         font-family: "Microsoft YaHei", system-ui, sans-serif; }}
  main {{ max-width: 920px; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ font-size: 28px; margin: 0 0 8px; }}
  .meta {{ color: #6b7280; margin: 0 0 20px; }}
  .toolbar {{ display: flex; align-items: center; gap: 14px; margin-bottom: 24px;
             flex-wrap: wrap; }}
  button {{ background: #d93025; color: #fff; border: 0; border-radius: 8px;
           padding: 10px 18px; font-size: 15px; cursor: pointer; }}
  button:hover {{ background: #b3261e; }}
  .tip {{ color: #6b7280; font-size: 13px; }}
  .card {{ background: #fff; border-radius: 12px; padding: 18px 20px; margin-bottom: 18px;
          box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .card.removed {{ opacity: .38; }}
  .head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }}
  .no {{ display: inline-flex; align-items: center; justify-content: center;
        width: 26px; height: 26px; border-radius: 50%; background: #d93025;
        color: #fff; font-size: 15px; flex: none; }}
  .text {{ flex: 1; border: 1px solid #d1d5db; border-radius: 8px; padding: 8px 10px;
          font-size: 15px; }}
  .del {{ display: inline-flex; align-items: center; gap: 6px; color: #6b7280;
         font-size: 13px; white-space: nowrap; }}
  .moves {{ display: inline-flex; gap: 4px; flex: none; }}
  .grip {{ cursor: grab; color: #9ca3af; padding: 0 4px; flex: none; user-select: none; }}
  .grip:active {{ cursor: grabbing; }}
  .card.dragging {{ opacity: .5; }}
  .card.drop-before {{ box-shadow: inset 0 3px 0 #d93025, 0 1px 3px rgba(0,0,0,.08); }}
  .card.drop-after {{ box-shadow: inset 0 -3px 0 #d93025, 0 1px 3px rgba(0,0,0,.08); }}
  .card.suspect {{ border-left: 4px solid #f59e0b; background: #fffbeb; }}
  .sbadge {{ background: #f59e0b; color: #fff; font-size: 12px; border-radius: 6px;
            padding: 3px 8px; white-space: nowrap; }}
  .moves button {{ background: #374151; padding: 4px 10px; font-size: 13px;
                  border-radius: 6px; }}
  .moves button:hover {{ background: #1f2937; }}
  .hint {{ margin: 10px 0 0; color: #9ca3af; font-size: 12px; }}

  .viewer {{ margin-top: 10px; }}
  .mbar {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }}
  .mbar button {{ background: #374151; padding: 5px 12px; font-size: 13px; border-radius: 6px; }}
  .mbar button:hover {{ background: #1f2937; }}
  .mbar button.boxedit.active {{ background: #d93025; }}
  .mcount {{ color: #374151; font-size: 13px; }}
  .mtip {{ color: #9ca3af; font-size: 12px; }}
  .cv {{ width: 100%; display: block; border: 1px solid #e5e7eb; border-radius: 8px;
        cursor: crosshair; }}

  #toc {{ position: sticky; top: 0; z-index: 20; background: #f3f4f6;
          display: flex; gap: 8px; flex-wrap: wrap; padding: 10px 0; }}
  .chip {{ position: relative; width: 64px; border: 1px solid #e5e7eb; border-radius: 8px;
           overflow: hidden; background: #fff; cursor: pointer; }}
  .chip img {{ width: 100%; height: 42px; object-fit: cover; display: block; }}
  .chip .ph {{ width: 100%; height: 42px; display: flex; align-items: center;
              justify-content: center; color: #9ca3af; font-size: 12px; }}
  .chip .n {{ position: absolute; left: 2px; top: 2px; background: #d93025; color: #fff;
              font-size: 11px; border-radius: 50%; width: 18px; height: 18px;
              text-align: center; line-height: 18px; }}
  .chip.suspect {{ border-color: #f59e0b; }}
  .chip .cdot {{ position: absolute; right: 3px; bottom: 3px; width: 8px; height: 8px;
                border-radius: 50%; background: #374151; }}
</style>
</head>
<body>
<main>
  <h1>复核 · {escape(title)}</h1>
  <p class="meta">共 {len(steps)} 个步骤 · 删除多余步骤、修改说明文字；需要隐藏的内容在图上拖框打码，导出 steps.json 后二次成文</p>
  <div class="toolbar">
    <button id="export" type="button">导出修改后的 steps.json</button>
    <span class="tip">导出后重新运行：python pipeline/run.py --steps steps.json --shots 截图目录 --out output</span>
  </div>
  <nav id="toc"></nav>
  <div id="cards"></div>
</main>
<script id="steps-data" type="application/json">{embedded}</script>
<script>
const data = JSON.parse(document.getElementById('steps-data').textContent);
const box = document.getElementById('cards');
const IMG = "{escape(image_dir)}";
let dragCard = null;

data.forEach((s, i) => {{
  const card = document.createElement('article');
  card.className = 'card' + (s.suspect ? ' suspect' : '');
  card.dataset.idx = i;
  const hasImage = Boolean(s.image);

  const viewer = hasImage
    ? '<div class="viewer">' +
        '<div class="mbar">' +
          '<button type="button" data-act="boxedit">✥ 调整红框</button>' +
          '<button type="button" data-act="undo">撤销马赛克</button>' +
          '<button type="button" data-act="clear">清空马赛克</button>' +
          '<span class="mcount">马赛克 0 块</span>' +
          '<span class="mtip">拖红框移动 · 右下角白点缩放 · 空白处拖框打码</span>' +
        '</div>' +
        '<canvas class="cv"></canvas>' +
      '</div>'
    : '<p class="hint">缺少对应截图</p>';

  card.innerHTML =
    '<div class="head">' +
      '<span class="grip" draggable="true" title="拖动调整顺序">⠿</span>' +
      '<span class="moves">' +
        '<button type="button" data-act="up" title="上移">↑</button>' +
        '<button type="button" data-act="down" title="下移">↓</button>' +
      '</span>' +
      '<span class="no">' + (i + 1) + '</span>' +
      (s.suspect ? '<span class="sbadge">疑似游离点击，请检查</span>' : '') +
      '<input class="text" type="text" value="' + escapeHtml(s.text) + '">' +
      '<label class="del"><input type="checkbox" class="rm"> 删除此步</label>' +
    '</div>' +
    viewer +
    '<p class="hint">类型：' + escapeHtml(s.kind) + ' · 元素：' + escapeHtml(s.label || '—') + '</p>';

  card.querySelector('.rm').addEventListener('change', (ev) => {{
    card.classList.toggle('removed', ev.target.checked);
  }});
  card.querySelector('[data-act="up"]').addEventListener('click', () => {{
    const prev = card.previousElementSibling;
    if (prev) {{ box.insertBefore(card, prev); refreshNumbers(); }}
  }});
  card.querySelector('[data-act="down"]').addEventListener('click', () => {{
    const next = card.nextElementSibling;
    if (next) {{ box.insertBefore(next, card); refreshNumbers(); }}
  }});

  card.addEventListener('dragstart', (ev) => {{
    dragCard = card;
    card.classList.add('dragging');
    ev.dataTransfer.effectAllowed = 'move';
    try {{ ev.dataTransfer.setData('text/plain', card.dataset.idx); }} catch (_) {{}}
  }});
  card.addEventListener('dragover', (ev) => {{
    ev.preventDefault();
    ev.dataTransfer.dropEffect = 'move';
    const r = card.getBoundingClientRect();
    const after = (ev.clientY - r.top) > r.height / 2;
    card.classList.toggle('drop-before', !after);
    card.classList.toggle('drop-after', after);
  }});
  card.addEventListener('dragleave', () => {{
    card.classList.remove('drop-before', 'drop-after');
  }});
  card.addEventListener('drop', (ev) => {{
    ev.preventDefault();
    clearMarks();
    if (!dragCard || dragCard === card) return;
    const r = card.getBoundingClientRect();
    const after = (ev.clientY - r.top) > r.height / 2;
    box.insertBefore(dragCard, after ? card.nextSibling : card);
    refreshNumbers();
  }});
  card.addEventListener('dragend', () => {{
    dragCard = null;
    card.classList.remove('dragging');
    clearMarks();
  }});
  box.appendChild(card);
  if (hasImage) initMosaic(card, s);
}});
buildToc();

function refreshNumbers() {{
  [...box.querySelectorAll('.card')].forEach((c, i) => {{
    c.querySelector('.no').textContent = i + 1;
  }});
  buildToc();
}}

function buildToc() {{
  const toc = document.getElementById('toc');
  toc.innerHTML = '';
  [...box.querySelectorAll('.card')].forEach((card, i) => {{
    const s = data[Number(card.dataset.idx)];
    const chip = document.createElement('div');
    chip.className = 'chip' + (s.suspect ? ' suspect' : '');
    const media = s.image
      ? `<img src="${{IMG}}/${{s.image}}" alt="">`
      : '<div class="ph">缺图</div>';
    const dot = (card._mosaics && card._mosaics.length) ? '<span class="cdot"></span>' : '';
    chip.innerHTML = media + `<span class="n">${{i + 1}}</span>` + dot;
    chip.addEventListener('click', () => card.scrollIntoView({{ behavior: 'smooth', block: 'center' }}));
    toc.appendChild(chip);
  }});
}}

function clearMarks() {{
  box.querySelectorAll('.drop-before, .drop-after')
    .forEach((c) => c.classList.remove('drop-before', 'drop-after'));
}}

function initMosaic(card, s) {{
  const cv = card.querySelector('.cv');
  const ctx = cv.getContext('2d');
  const mosaics = (s.mosaics || []).map((m) => ({{
    x: Number(m.x) || 0, y: Number(m.y) || 0,
    w: Number(m.w) || 0, h: Number(m.h) || 0,
  }}));
  const boxState = (Array.isArray(s.box) && s.box.length === 4)
    ? s.box.map(Number) : null;
  card._mosaics = mosaics;
  card._box = boxState;

  const img = new Image();
  let ready = false, mode = null;
  let startX = 0, startY = 0, cur = null;
  let grabOff = {{ x: 0, y: 0 }};
  let boxFlash = false;

  function paint() {{
    if (!ready) return;
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.drawImage(img, 0, 0);
    for (const m of mosaics) {{
      ctx.save();
      ctx.filter = 'blur(8px)';
      ctx.drawImage(img, m.x, m.y, m.w, m.h, m.x, m.y, m.w, m.h);
      ctx.restore();
    }}
    if (boxState) {{
      const [x0, y0, x1, y1] = boxState;
      ctx.strokeStyle = boxFlash ? '#f59e0b' : '#d93025';
      ctx.lineWidth = 3;
      ctx.setLineDash(boxFlash ? [9, 6] : []);
      ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
      ctx.setLineDash([]);
      // 右下角缩放手柄：白底红框 + 红心圆点，提高辨识度
      const hs = 15;
      ctx.fillStyle = '#fff';
      ctx.fillRect(x1 - hs / 2, y1 - hs / 2, hs, hs);
      ctx.strokeStyle = '#d93025';
      ctx.lineWidth = 2;
      ctx.strokeRect(x1 - hs / 2, y1 - hs / 2, hs, hs);
      ctx.fillStyle = '#d93025';
      ctx.beginPath();
      ctx.arc(x1, y1, 3.5, 0, Math.PI * 2);
      ctx.fill();
    }}
  }}
  function count() {{
    card.querySelector('.mcount').textContent = '马赛克 ' + mosaics.length + ' 块';
  }}

  img.onload = () => {{
    ready = true;
    cv.width = img.naturalWidth;
    cv.height = img.naturalHeight;
    paint();
    count();
  }};
  img.src = IMG + '/' + s.image;

  function toNatural(ev) {{
    const r = cv.getBoundingClientRect();
    return {{
      x: (ev.clientX - r.left) * cv.width / r.width,
      y: (ev.clientY - r.top) * cv.height / r.height,
    }};
  }}

  // 悬停光标：手柄处缩放、框内移动、其余位置打码
  cv.addEventListener('pointermove', (ev) => {{
    if (mode) return;
    const p = toNatural(ev);
    if (!boxState) {{ cv.style.cursor = 'crosshair'; return; }}
    const [x0, y0, x1, y1] = boxState;
    if (Math.abs(p.x - x1) <= 13 && Math.abs(p.y - y1) <= 13) {{
      cv.style.cursor = 'nwse-resize';
    }} else if (p.x >= x0 && p.x <= x1 && p.y >= y0 && p.y <= y1) {{
      cv.style.cursor = 'move';
    }} else {{
      cv.style.cursor = 'crosshair';
    }}
  }});

  cv.addEventListener('pointerdown', (ev) => {{
    ev.preventDefault();
    try {{ cv.setPointerCapture(ev.pointerId); }} catch (_) {{}}
    const p = toNatural(ev);
    if (boxState) {{
      const [x0, y0, x1, y1] = boxState;
      if (Math.abs(p.x - x1) <= 12 && Math.abs(p.y - y1) <= 12) {{
        mode = 'resize';
      }} else if (p.x >= x0 && p.x <= x1 && p.y >= y0 && p.y <= y1) {{
        mode = 'move';
        grabOff = {{ x: p.x - x0, y: p.y - y0 }};
      }}
    }}
    if (!mode) {{
      mode = 'mosaic';
      startX = p.x; startY = p.y;
      cur = {{ x: p.x, y: p.y, w: 0, h: 0 }};
    }}
  }});
  cv.addEventListener('pointermove', (ev) => {{
    if (!mode) return;
    const p = toNatural(ev);
    if (mode === 'resize' && boxState) {{
      boxState[2] = Math.max(boxState[0] + 24, Math.min(cv.width, p.x));
      boxState[3] = Math.max(boxState[1] + 16, Math.min(cv.height, p.y));
      paint();
      return;
    }}
    if (mode === 'move' && boxState) {{
      const bw = boxState[2] - boxState[0], bh = boxState[3] - boxState[1];
      boxState[0] = Math.max(0, Math.min(cv.width - bw, p.x - grabOff.x));
      boxState[1] = Math.max(0, Math.min(cv.height - bh, p.y - grabOff.y));
      paint();
      return;
    }}
    if (mode === 'mosaic' && cur) {{
      cur.x = Math.min(startX, p.x);
      cur.y = Math.min(startY, p.y);
      cur.w = Math.abs(p.x - startX);
      cur.h = Math.abs(p.y - startY);
      paint();
      ctx.strokeStyle = '#d93025';
      ctx.lineWidth = 2;
      ctx.strokeRect(cur.x, cur.y, cur.w, cur.h);
    }}
  }});
  const endDrag = () => {{
    if (mode === 'mosaic' && cur && cur.w >= 8 && cur.h >= 8) mosaics.push({{ ...cur }});
    cur = null;
    mode = null;
    paint();
    count();
  }};
  cv.addEventListener('pointerup', endDrag);
  cv.addEventListener('pointercancel', endDrag);

  const boxBtn = card.querySelector('[data-act="boxedit"]');
  boxBtn.addEventListener('click', () => {{
    if (!boxState) return;
    boxFlash = true;
    boxBtn.classList.add('active');
    paint();
    setTimeout(() => {{
      boxFlash = false;
      boxBtn.classList.remove('active');
      paint();
    }}, 1600);
  }});

  card.querySelector('[data-act="undo"]').addEventListener('click', () => {{
    mosaics.pop();
    paint();
    count();
  }});
  card.querySelector('[data-act="clear"]').addEventListener('click', () => {{
    mosaics.length = 0;
    paint();
    count();
  }});
}}

function escapeHtml(t) {{
  return String(t ?? '').replace(/[&<>"']/g, (c) => (
    {{'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}}[c]
  ));
}}

document.getElementById('export').addEventListener('click', () => {{
  const kept = [];
  document.querySelectorAll('.card').forEach((card) => {{
    if (card.classList.contains('removed')) return;
    const s = data[Number(card.dataset.idx)];
    s.text = card.querySelector('.text').value.trim() || s.text;
    if (card._mosaics) {{
      s.mosaics = card._mosaics.map((m) => ({{
        x: Math.round(m.x), y: Math.round(m.y),
        w: Math.round(m.w), h: Math.round(m.h),
      }}));
    }}
    if (card._box) {{
      s.box = card._box.map(Math.round);
    }}
    kept.push(s);
  }});
  kept.forEach((s, i) => {{ s.index = i + 1; }});
  const blob = new Blob([JSON.stringify(kept, null, 2)], {{type: 'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'steps.json';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
}});
</script>
</body>
</html>"""

    out_path.write_text(doc, encoding="utf-8")
    return out_path
