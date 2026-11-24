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
            "--format",
            "all",
        ]
    )
    if code != 0:
        print("处理链返回非 0")
        return 1

    steps = json.loads((out_dir / "steps.json").read_text(encoding="utf-8"))
    images = sorted((out_dir / "steps").glob("*.png"))
    md = (out_dir / "tutorial.md").read_text(encoding="utf-8")
    html_path = out_dir / "tutorial.html"
    html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
    review_path = out_dir / "review.html"
    review = review_path.read_text(encoding="utf-8") if review_path.exists() else ""

    problems = []
    if len(steps) != 5:
        problems.append(f"步骤数应为 5，实际 {len(steps)}")
    if len(images) != 5:
        problems.append(f"标注图应为 5 张，实际 {len(images)}")
    if "自测教程" not in md:
        problems.append("Markdown 标题没写进去")
    if not html_path.exists() or "自测教程" not in html:
        problems.append("HTML 导出缺失或标题没写进去")
    if not review_path.exists() or "steps-data" not in review:
        problems.append("复核页 review.html 缺失或未嵌入步骤数据")
    if "cv" not in review or "mosaics" not in review:
        problems.append("复核页缺少手动马赛克工具")
    if 'data-act="up"' not in review or 'data-act="down"' not in review:
        problems.append("复核页缺少步骤上移/下移按钮")
    if "grip" not in review or "draggable" not in review:
        problems.append("复核页缺少拖拽排序手柄")
    if "buildToc" not in review or 'id="toc"' not in review:
        problems.append("复核页缺少步骤缩略导航")
    if "boxState" not in review:
        problems.append("复核页缺少可拖动/缩放的红框覆盖层")
    for word in ("登录", "学号", "选课", "提交", "计算机学院"):
        if word not in md:
            problems.append(f"步骤文字缺少【{word}】")
    if "选择【计算机学院】" not in md:
        problems.append("下拉选择文案未写成「选择【选项】」")

    # 输入类内容必须不泄露具体填写值
    from pipeline.frames import build_steps  # noqa: E402
    mask_step = build_steps(
        [{
            "type": "input", "url": "u", "label": "请输入密码", "value": "secret123",
            "x": 1, "y": 1, "w": 100, "h": 30, "dpr": 1, "ts": 1,
        }]
    )[0]
    if "secret123" in mask_step.action_text:
        problems.append("密码明文出现在步骤文字里")
    if mask_step.value != "••••••":
        problems.append("中间结果里的密码未打码")

    acct_step = build_steps(
        [{
            "type": "input", "url": "u", "label": "请输入账号", "value": "13700001111",
            "x": 1, "y": 1, "w": 100, "h": 30, "dpr": 1, "ts": 1,
        }]
    )[0]
    if "13700001111" in acct_step.action_text:
        problems.append("账号明文出现在步骤文字里")
    if acct_step.value:
        problems.append("账号具体值残留在中间结果里")
    if "20230001" in md:
        problems.append("演示账号值残存在教程 Markdown 里")

    # 同一输入框的两次输入（防抖批次 + 失焦 change）合并为一步
    dup_input = build_steps([
        {"type": "input", "url": "u", "label": "学号", "value": "a",
         "x": 360, "y": 260, "w": 320, "h": 48, "dpr": 1, "ts": 1},
        {"type": "input", "url": "u", "label": "学号", "value": "b",
         "x": 360, "y": 260, "w": 320, "h": 48, "dpr": 1, "ts": 500},
    ])
    if len(dup_input) != 1:
        problems.append("同一输入框的两次输入未合并为一步")

    # 下拉框文案：选择【所选选项】，且选项值保留
    sel = build_steps([
        {"type": "input", "url": "u", "tag": "select", "label": "学院",
         "value": "计算机学院", "x": 1, "y": 1, "w": 100, "h": 30, "dpr": 1, "ts": 1},
    ])[0]
    if "选择【计算机学院】" not in sel.action_text:
        problems.append("下拉选择文案模板不对")
    if sel.value != "计算机学院":
        problems.append("下拉选项文字未保留")

    # 复核二次读入：steps.json -> Step 列表，步骤数与文案保留
    from pipeline.frames import load_steps, steps_from_dicts, Step  # noqa: E402
    rt_steps = load_steps(out_dir / "steps.json")
    if len(rt_steps) != 5:
        problems.append(f"复核二次读入应为 5 步，实际 {len(rt_steps)}")
    elif rt_steps[0].action_text != steps[0]["text"]:
        problems.append("复核二次读入后步骤文案丢失")

    # 马赛克区域 / 红框坐标 / 疑似标记随 steps.json 保存并读回
    ms = Step(label="测试", mosaics=[{"x": 10, "y": 20, "w": 80, "h": 30}],
              box=[1, 2, 3, 4], suspect=True)
    rt = steps_from_dicts([ms.to_dict()])[0]
    if rt.mosaics != ms.mosaics:
        problems.append("马赛克区域未随 steps.json 保存/读回")
    if rt.box != [1, 2, 3, 4]:
        problems.append("红框坐标未随 steps.json 保存/读回")
    if not rt.suspect:
        problems.append("疑似游离点击标记未随 steps.json 保存/读回")

    # 缺图占位图可正常生成
    from pipeline.annotate import make_placeholder  # noqa: E402
    ph = tmp / "ph.png"
    make_placeholder(Step(index=9, label="缺图"), ph)
    if not ph.exists() or ph.stat().st_size < 1000:
        problems.append("缺图占位图生成失败")

    # 重复帧去重：同控件同图合并为一步
    from pipeline.frames import Step, dedupe_similar_frames  # noqa: E402
    dup = dedupe_similar_frames(
        [
            Step(label="提交", x=100, y=100, w=120, h=40, dpr=1, source="001.png", image="001.png"),
            Step(label="提交", x=100, y=100, w=120, h=40, dpr=1, source="001.png", image="001.png"),
        ],
        src_shots,
    )
    if len(dup) != 1:
        problems.append("同控件重复帧未合并")

    shutil.rmtree(tmp, ignore_errors=True)

    if problems:
        print("FAIL")
        for p in problems:
            print(" -", p)
        return 1

    print("PASS：5 步骤 + 5 张标注图，Markdown / HTML / 复核页 / 下拉文案 / 红框回写校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
