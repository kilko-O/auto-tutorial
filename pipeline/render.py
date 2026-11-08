"""步骤列表 -> 文档

默认输出 Markdown；装了 python-docx 时也可以直接出 Word。
"""

from __future__ import annotations

from datetime import datetime
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


def render_docx(steps, out_path: str | Path, title: str, image_dir: str = "steps") -> Path | None:
    """导出 Word；未安装 python-docx 时返回 None。"""
    try:
        from docx import Document
        from docx.shared import Cm
    except ImportError:
        return None

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph(f"共 {len(steps)} 个步骤，生成于 {datetime.now():%Y-%m-%d %H:%M}")

    base = out_path.parent
    for step in steps:
        doc.add_heading(f"{step.index}. {step.action_text}", level=2)
        if step.image:
            image_path = base / image_dir / step.image
            if image_path.exists():
                doc.add_picture(str(image_path), width=Cm(14))
        else:
            doc.add_paragraph("缺少对应截图")

    doc.save(out_path)
    return out_path
