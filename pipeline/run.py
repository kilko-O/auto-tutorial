"""命令行入口：events.json + 截图目录 -> 教程文档

用法：
    python pipeline/run.py --events samples/events.json --shots samples/shots --out output
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from annotate import crop_and_mark  # noqa: E402
from frames import build_steps, load_events, save_steps  # noqa: E402
from render import render_docx, render_markdown  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="把操作事件流转成图文教程")
    parser.add_argument("--events", required=True, help="扩展导出的 events.json")
    parser.add_argument("--shots", required=True, help="截图所在目录")
    parser.add_argument("--out", default="output", help="输出目录，默认 output")
    parser.add_argument("--title", default="", help="教程标题，默认取首个页面标题")
    parser.add_argument("--format", choices=["md", "docx", "both"], default="md")
    parser.add_argument("--window", type=int, default=1500, help="合并窗口（毫秒）")
    args = parser.parse_args(argv)

    events = load_events(args.events)
    steps = build_steps(events, window_ms=args.window)
    print(f"原始事件 {len(events)} 条 -> 合并为 {len(steps)} 个步骤")

    out_dir = Path(args.out)
    steps_dir = out_dir / "steps"
    steps_dir.mkdir(parents=True, exist_ok=True)
    shots_dir = Path(args.shots)

    missing = 0
    for step in steps:
        src = shots_dir / step.image if step.image else None
        if src is None or not src.exists():
            missing += 1
            step.image = ""
            continue
        dst_name = f"{step.index:03d}.png"
        crop_and_mark(src, step, steps_dir / dst_name)
        step.image = dst_name

    title = args.title or next((s.title for s in steps if s.title), "操作教程")
    md_path = render_markdown(steps, out_dir / "tutorial.md", title)
    print(f"Markdown：{md_path}")

    if args.format in ("docx", "both"):
        docx_path = render_docx(steps, out_dir / "tutorial.docx", title)
        if docx_path is None:
            print("未安装 python-docx，跳过 Word 导出（pip install python-docx 后可开启）")
        else:
            print(f"Word：{docx_path}")

    save_steps(steps, out_dir / "steps.json")

    if missing:
        print(f"警告：有 {missing} 个步骤找不到对应截图，已在文档中标记")
    print(f"完成，共 {len(steps)} 步")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
