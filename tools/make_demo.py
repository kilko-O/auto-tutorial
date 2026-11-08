"""生成演示数据：一张假教务系统页面 + 4 条事件

跑完会在 samples/ 下生成 events.json 和 shots/001..004.png，
用来在没有扩展的情况下验证 pipeline 能否出文档。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.annotate import font  # noqa: E402

SAMPLES = ROOT / "samples"
SHOTS = SAMPLES / "shots"
W, H = 1440, 900


def draw_page() -> Image.Image:
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)

    # 顶栏
    d.rectangle((0, 0, W, 64), fill=(238, 240, 244))
    d.text((32, 20), "教务管理系统", font=font(22), fill=(40, 44, 52))

    # 表单区
    d.text((200, 200), "学号", font=font(20), fill=(60, 64, 72))
    d.rectangle((200, 236, 520, 284), outline=(200, 205, 214), width=2)
    d.text((214, 248), "请输入学号", font=font(18), fill=(150, 155, 165))

    d.text((200, 306), "密码", font=font(20), fill=(60, 64, 72))
    d.rectangle((200, 342, 520, 390), outline=(200, 205, 214), width=2)
    d.text((214, 354), "请输入密码", font=font(18), fill=(150, 155, 165))

    # 按钮
    d.rectangle((200, 420, 330, 468), fill=(36, 110, 240))
    d.text((238, 432), "登录", font=font(22), fill=(255, 255, 255))

    # 菜单
    d.rectangle((200, 540, 330, 590), fill=(246, 247, 250))
    d.text((232, 552), "选课", font=font(22), fill=(40, 44, 52))

    # 底部按钮
    d.rectangle((200, 720, 330, 772), fill=(30, 160, 90))
    d.text((238, 734), "提交", font=font(22), fill=(255, 255, 255))

    return img


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)

    shots = ["001", "002", "003", "004"]
    for name in shots:
        draw_page().save(SHOTS / f"{name}.png")

    url = "https://jw.example.edu/login"
    events = [
        {"type": "click", "url": url, "title": "教务系统 - 登录",
         "x": 265, "y": 444, "dpr": 1, "tag": "button", "label": "登录",
         "shot": "001.png", "ts": 1000},
        {"type": "input", "url": url, "title": "教务系统 - 登录",
         "x": 360, "y": 260, "dpr": 1, "tag": "input", "label": "学号", "value": "20230001",
         "shot": "002.png", "ts": 9000},
        {"type": "click", "url": "https://jw.example.edu/select", "title": "教务系统 - 选课",
         "x": 265, "y": 565, "dpr": 1, "tag": "div", "label": "选课",
         "shot": "003.png", "ts": 17000},
        {"type": "click", "url": "https://jw.example.edu/select", "title": "教务系统 - 选课",
         "x": 265, "y": 746, "dpr": 1, "tag": "button", "label": "提交",
         "shot": "004.png", "ts": 17600},
    ]

    (SAMPLES / "events.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"已生成 {SAMPLES / 'events.json'} 与 {len(shots)} 张截图")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
