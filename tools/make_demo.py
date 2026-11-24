"""生成演示样例库：多套假页面 + 事件流

跑完在 samples/ 下生成：
  samples/events.json + samples/shots/   （默认 login 流程，兼容旧自测路径）
  samples/<flow>/events.json + shots/    （register / publish 等流程）

用法：
  python tools/make_demo.py              # 生成全部流程
  python tools/make_demo.py --flow register
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.annotate import font  # noqa: E402

SAMPLES = ROOT / "samples"
W, H = 1440, 900


def _base(title: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 64), fill=(238, 240, 244))
    d.text((32, 20), title, font=font(22), fill=(40, 44, 52))
    return img, d


def _field(d, x, y, w, label, text, placeholder: bool = False):
    d.text((x, y - 36), label, font=font(20), fill=(60, 64, 72))
    d.rectangle((x, y, x + w, y + 48), outline=(200, 205, 214), width=2)
    d.text(
        (x + 14, y + 14), text, font=font(18),
        fill=(150, 155, 165) if placeholder else (60, 64, 72),
    )


def _select(d, x, y, w, label, value):
    d.text((x, y - 36), label, font=font(20), fill=(60, 64, 72))
    d.rectangle((x, y, x + w, y + 48), outline=(200, 205, 214), width=2)
    d.text((x + 14, y + 14), value, font=font(18), fill=(60, 64, 72))
    d.polygon([(x + w - 28, y + 16), (x + w - 12, y + 16), (x + w - 20, y + 26)],
              fill=(120, 125, 135))


def _button(d, x, y, w, text, fill=(36, 110, 240)):
    d.rectangle((x, y, x + w, y + 48), fill=fill)
    tw = d.textlength(text, font=font(22))
    d.text((x + (w - tw) / 2, y + 12), text, font=font(22), fill=(255, 255, 255))


# ---------- 流程一：登录 + 选课（默认，兼容旧自测） ----------

def login_page() -> Image.Image:
    img, d = _base("教务管理系统")
    _field(d, 200, 236, 320, "学号", "请输入学号", placeholder=True)
    _select(d, 600, 236, 320, "学院", "计算机学院")
    _field(d, 200, 342, 320, "密码", "请输入密码", placeholder=True)
    _button(d, 200, 420, 130, "登录")
    d.rectangle((200, 540, 330, 590), fill=(246, 247, 250))
    d.text((232, 552), "选课", font=font(22), fill=(40, 44, 52))
    _button(d, 200, 720, 130, "提交", fill=(30, 160, 90))
    return img


LOGIN_URL = "https://jw.example.edu/login"
LOGIN_EVENTS = [
    {"type": "input", "url": LOGIN_URL, "title": "教务系统 - 登录",
     "x": 360, "y": 260, "w": 320, "h": 48, "dpr": 1, "tag": "input",
     "label": "学号", "value": "20230001", "shot": "001.png", "ts": 2000},
    {"type": "input", "url": LOGIN_URL, "title": "教务系统 - 登录",
     "x": 760, "y": 260, "w": 320, "h": 48, "dpr": 1, "tag": "select",
     "label": "学院", "value": "计算机学院", "shot": "002.png", "ts": 3500},
    {"type": "click", "url": LOGIN_URL, "title": "教务系统 - 登录",
     "x": 265, "y": 444, "w": 130, "h": 48, "dpr": 1, "tag": "button",
     "label": "登录", "shot": "003.png", "ts": 5000},
    {"type": "click", "url": "https://jw.example.edu/select", "title": "教务系统 - 选课",
     "x": 265, "y": 565, "w": 130, "h": 50, "dpr": 1, "tag": "div",
     "label": "选课", "shot": "004.png", "ts": 9000},
    {"type": "click", "url": "https://jw.example.edu/select", "title": "教务系统 - 选课",
     "x": 265, "y": 746, "w": 130, "h": 52, "dpr": 1, "tag": "button",
     "label": "提交", "shot": "005.png", "ts": 9600},
]

# ---------- 流程二：注册 ----------

def register_page() -> Image.Image:
    img, d = _base("智慧树 - 注册")
    _field(d, 200, 200, 320, "手机号", "请输入手机号", placeholder=True)
    _field(d, 200, 290, 320, "密码", "请设置密码", placeholder=True)
    _field(d, 200, 380, 220, "验证码", "请输入验证码", placeholder=True)
    _button(d, 460, 380, 120, "发送验证码", fill=(107, 114, 128))
    _button(d, 200, 470, 160, "下一步")
    return img


REGISTER_URL = "https://online.zhihuishu.example/register"
REGISTER_EVENTS = [
    {"type": "input", "url": REGISTER_URL, "title": "注册",
     "x": 360, "y": 224, "w": 320, "h": 48, "dpr": 1, "tag": "input",
     "label": "手机号", "value": "13700001111", "shot": "001.png", "ts": 2000},
    {"type": "input", "url": REGISTER_URL, "title": "注册",
     "x": 360, "y": 314, "w": 320, "h": 48, "dpr": 1, "tag": "input",
     "label": "密码", "value": "secret123", "shot": "002.png", "ts": 3600},
    {"type": "input", "url": REGISTER_URL, "title": "注册",
     "x": 310, "y": 404, "w": 220, "h": 48, "dpr": 1, "tag": "input",
     "label": "验证码", "value": "8866", "shot": "003.png", "ts": 5200},
    {"type": "click", "url": REGISTER_URL, "title": "注册",
     "x": 280, "y": 494, "w": 160, "h": 48, "dpr": 1, "tag": "button",
     "label": "下一步", "shot": "004.png", "ts": 6800},
]

# ---------- 流程三：发布活动（标题 + 类别下拉 + 提交） ----------

def publish_page() -> Image.Image:
    img, d = _base("后台 - 发布活动")
    _field(d, 200, 200, 520, "活动标题", "请输入活动标题", placeholder=True)
    _select(d, 200, 290, 320, "活动类别", "文体活动")
    _button(d, 200, 380, 130, "发布", fill=(30, 160, 90))
    return img


PUBLISH_URL = "https://admin.example.com/activity/new"
PUBLISH_EVENTS = [
    {"type": "input", "url": PUBLISH_URL, "title": "发布活动",
     "x": 460, "y": 224, "w": 520, "h": 48, "dpr": 1, "tag": "input",
     "label": "活动标题", "value": "秋季篮球赛", "shot": "001.png", "ts": 2000},
    {"type": "input", "url": PUBLISH_URL, "title": "发布活动",
     "x": 360, "y": 314, "w": 320, "h": 48, "dpr": 1, "tag": "select",
     "label": "活动类别", "value": "文体活动", "shot": "002.png", "ts": 3600},
    {"type": "click", "url": PUBLISH_URL, "title": "发布活动",
     "x": 265, "y": 404, "w": 130, "h": 48, "dpr": 1, "tag": "button",
     "label": "发布", "shot": "003.png", "ts": 5200},
]

FLOWS = {
    "login": {"page": login_page, "events": LOGIN_EVENTS},
    "register": {"page": register_page, "events": REGISTER_EVENTS},
    "publish": {"page": publish_page, "events": PUBLISH_EVENTS},
}


def write_flow(name: str) -> None:
    flow = FLOWS[name]
    fdir = SAMPLES / name
    shots = fdir / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    page = flow["page"]()
    for i, _ in enumerate(flow["events"], start=1):
        page.save(shots / f"{i:03d}.png")
    (fdir / "events.json").write_text(
        json.dumps(flow["events"], ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="生成演示样例库")
    ap.add_argument("--flow", default="", help="只生成指定流程：login / register / publish")
    args = ap.parse_args()

    names = [args.flow] if args.flow else list(FLOWS)
    for name in names:
        if name not in FLOWS:
            print(f"未知流程：{name}，可选 {', '.join(FLOWS)}")
            return 1
        write_flow(name)
        print(f"已生成 samples/{name}/（{len(FLOWS[name]['events'])} 步）")

    # 兼容旧自测路径：samples/events.json + samples/shots/ 放默认 login 流程
    if not args.flow or args.flow == "login":
        shutil.rmtree(SAMPLES / "shots", ignore_errors=True)
        shutil.copytree(SAMPLES / "login" / "shots", SAMPLES / "shots")
        shutil.copy(SAMPLES / "login" / "events.json", SAMPLES / "events.json")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
