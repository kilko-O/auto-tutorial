"""处理链自测：模拟扩展的真实产出（events.json + auto-tutorial/001_xxx.png）跑一遍

运行：python tools/pipeline_selftest.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.run import main as run_main  # noqa: E402


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="auto-tutorial-"))
    shots_dir = tmp / "shots"
    shots_dir.mkdir()

    src_shots = ROOT / "samples" / "shots"
    if not src_shots.exists():
        print("先运行 python tools/make_demo.py 生成演示截图")
        return 1

    # 按扩展的命名规则改名：auto-tutorial/001_<时间戳>.png
    mapping = {}
    for i, src in enumerate(sorted(src_shots.glob("*.png")), start=1):
        new_name = f"{i:03d}_17000000000{i}.png"
        shutil.copyfile(src, shots_dir / new_name)
        mapping[src.name] = f"auto-tutorial/{new_name}"

    # 按扩展的导出格式组装 events.json
    raw = json.loads((ROOT / "samples" / "events.json").read_text(encoding="utf-8"))
    events = []
    for ev in raw:
        ev = dict(ev)
        ev["shot"] = mapping.get(Path(ev.get("shot", "")).name, "")
        events.append(ev)

    events_path = tmp / "events.json"
    events_path.write_text(
        json.dumps(
            {"version": 1, "exported_at": "2026-01-01T00:00:00Z", "download_dir": "auto-tutorial", "events": events},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    out_dir = tmp / "out"
    code = run_main(
        [
            "--events",
            str(events_path),
            "--shots",
            str(shots_dir),
            "--out",
            str(out_dir),
            "--title",
            "自测教程",
        ]
    )
    if code != 0:
        print("处理链返回非 0")
        return 1

    steps = json.loads((out_dir / "steps.json").read_text(encoding="utf-8"))
    images = sorted((out_dir / "steps").glob("*.png"))
    md = (out_dir / "tutorial.md").read_text(encoding="utf-8")

    problems = []
    if len(steps) != 3:
        problems.append(f"步骤数应为 3，实际 {len(steps)}")
    if len(images) != 3:
        problems.append(f"标注图应为 3 张，实际 {len(images)}")
    if "自测教程" not in md:
        problems.append("Markdown 标题没写进去")
    if "依次点击" not in md:
        problems.append("合并步骤的文字不对")

    shutil.rmtree(tmp, ignore_errors=True)

    if problems:
        print("FAIL")
        for p in problems:
            print(" -", p)
        return 1

    print("PASS：扩展格式的 events.json -> 3 步骤 + 3 张标注图 + Markdown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
