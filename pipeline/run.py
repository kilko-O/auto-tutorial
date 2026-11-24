"""命令行入口：events.json + 截图目录 -> 教程文档

用法：
    python pipeline/run.py --events samples/events.json --shots samples/shots --out output
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from annotate import crop_and_mark, make_placeholder  # noqa: E402
from frames import build_steps, dedupe_similar_frames, load_events, load_steps, save_steps  # noqa: E402
from render import render_docx, render_html, render_markdown, render_review  # noqa: E402


def clean_page_title(raw: str) -> str:
    """去掉浏览器标题里的站点后缀，如「…~-bilibili」「… - 智慧树」。"""
    t = (raw or "").strip()
    t = re.split(r"\s*~\s*-|\s+-\s+", t, maxsplit=1)[0].strip()
    return t or "操作教程"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="把操作事件流转成图文教程")
    parser.add_argument("--events", help="扩展导出的 events.json（与 --steps 二选一）")
    parser.add_argument("--steps", help="复核页导出的 steps.json，跳过事件合并直接成文")
    parser.add_argument("--shots", required=True, help="截图所在目录")
    parser.add_argument("--out", default="output", help="输出目录，默认 output")
    parser.add_argument("--title", default="", help="教程标题，默认取首个页面标题")
    parser.add_argument("--format", choices=["md", "docx", "html", "both", "all"], default="md")
    parser.add_argument("--window", type=int, default=1500, help="合并窗口（毫秒）")
    parser.add_argument("--no-dedupe", action="store_true", help="关闭相邻重复帧合并")
    parser.add_argument("--crop-w", type=int, default=680, help="裁剪区宽（物理像素）")
    parser.add_argument("--crop-h", type=int, default=400, help="裁剪区高（物理像素）")
    parser.add_argument("--dedupe-threshold", type=float, default=2.0,
                        help="重复帧灰度差阈值，越小越严格")
    args = parser.parse_args(argv)

    if args.steps:
        steps = load_steps(args.steps)
        print(f"读入已编辑步骤 {len(steps)} 个")
    elif args.events:
        events = load_events(args.events)
        steps = build_steps(events, window_ms=args.window)
        if not args.no_dedupe:
            steps = dedupe_similar_frames(steps, args.shots, threshold=args.dedupe_threshold)
        print(f"原始事件 {len(events)} 条 -> 合并为 {len(steps)} 个步骤")
    else:
        parser.error("--events 与 --steps 至少提供一个")

    out_dir = Path(args.out)
    steps_dir = out_dir / "steps"
    steps_dir.mkdir(parents=True, exist_ok=True)
    # 清掉上一轮残留的标注图，避免步骤变少后旧图留在目录里
    for old in steps_dir.glob("*.png"):
        old.unlink()
    shots_dir = Path(args.shots)

    missing = 0
    for step in steps:
        src_name = step.source or step.image
        src = shots_dir / src_name if src_name else None
        if src is None or not src.exists():
            missing += 1
            dst_name = f"{step.index:03d}.png"
            make_placeholder(step, steps_dir / dst_name)
            step.image = dst_name
            continue
        dst_name = f"{step.index:03d}.png"
        crop_and_mark(src, step, steps_dir / dst_name,
                      crop_size=(args.crop_w, args.crop_h))
        step.image = dst_name

    title = args.title or clean_page_title(next((s.title for s in steps if s.title), ""))
    md_path = render_markdown(steps, out_dir / "tutorial.md", title)
    print(f"Markdown：{md_path}")

    if args.format in ("docx", "both", "all"):
        docx_path = render_docx(steps, out_dir / "tutorial.docx", title)
        if docx_path is None:
            print("未安装 python-docx，跳过 Word 导出（pip install python-docx 后可开启）")
        else:
            print(f"Word：{docx_path}")

    if args.format in ("html", "all"):
        html_path = render_html(steps, out_dir / "tutorial.html", title)
        print(f"HTML：{html_path}")

    review_path = render_review(steps, out_dir / "review.html", title)
    print(f"复核页：{review_path}")

    save_steps(steps, out_dir / "steps.json")

    if missing:
        print(f"警告：有 {missing} 个步骤找不到对应截图，已在文档中标记")
    print(f"完成，共 {len(steps)} 步")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
