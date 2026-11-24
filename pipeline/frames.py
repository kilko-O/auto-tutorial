"""事件流 -> 步骤列表

把扩展录下来的原始事件（点击、输入、勾选）合并成"人看得懂的步骤"。

合并规则：
1. 只有 click / input 参与成步骤，其它忽略；
2. 相邻两条事件同属一个页面（url 相同）、间隔 <= window_ms 就合并；
   勾选类动作（复选框/单选）的 click 与 change 是同一次操作，跨类型也合并；
3. 合并后保留最后一条事件的截图与坐标，文字去重后合成"依次点击 A、B"。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

MERGE_WINDOW_MS = 1500
VALID_TYPES = ("click", "input")

CHECK_ON = "勾选"
CHECK_OFF = "取消勾选"
CHECK_VALUES = (CHECK_ON, CHECK_OFF)

LABEL_MAX = 18

# 点到这些通用容器且读不到元素名时，很可能是点在表单/卡片空白处的游离点击
GENERIC_TAGS = {"div", "form", "section", "span", "ul", "ol", "p", "article", "body"}

# 图形验证码：依次点选同一图片上的多个位置，没有可靠的元素名，统一用这个名字
CAPTCHA_LABEL = "验证码图片"
CAPTCHA_TAGS = ("img", "canvas", "video")
CAPTCHA_KEYWORDS = ("验证码", "滑块", "拼图", "验证", "captcha", "slider")


def _looks_like_captcha(step: "Step") -> bool:
    """元素本身是图片/画布，或标签明确提到验证码/滑块，才按验证码处理。"""
    if step.tag in CAPTCHA_TAGS:
        return True
    t = (step.label or "").lower()
    return any(k in t for k in CAPTCHA_KEYWORDS)

# 密码类输入框：成文时把真实值打码，避免教程里泄露口令；其余输入值同样不进教程
PASSWORD_KEYWORDS = ("密码", "password", "pwd", "passwd", "pass")


def _is_password_label(label: str) -> bool:
    t = (label or "").lower()
    return any(k in t for k in PASSWORD_KEYWORDS)


_INPUT_PREFIXES = ("请输入", "请填写", "请选择", "输入", "填写")


def _input_noun(label: str) -> str:
    """从输入框标签里抽关键词：「请输入账号」->「账号」，抽不到用「内容」。"""
    t = str(label or "").strip()
    for p in _INPUT_PREFIXES:
        if t.startswith(p):
            t = t[len(p):].strip()
            break
    return t.strip("：: ") or "内容"

TAG_FALLBACK = {
    "input": "输入框",
    "select": "下拉框",
    "button": "按钮",
    "a": "链接",
    "span": "页面元素",
    "div": "页面元素",
    "li": "列表项",
    "label": "选项",
}


def normalize_label(text: str) -> str:
    """去掉协议书名号、压缩空白、超长截断；纯数字/序号或多段聚合文本视为无效标签。"""
    t = str(text or "")
    t = re.sub(r"《[^》]*》", "", t)
    t = re.sub(r"^\s*\+\d+\s*", "", t)  # 去掉手机号前缀 +86 这类区号
    t = re.sub(r"\s+", " ", t).strip()
    if re.fullmatch(r"[\d\s]+", t):
        return ""
    # 容器把多个输入框/按钮的文字拼在一起（如「+86 发送验证码 请输入验证码」），不是元素名
    if len([s for s in t.split(" ") if s]) >= 2:
        return ""
    if len(t) > LABEL_MAX:
        t = t[:LABEL_MAX].rstrip() + "…"
    return t


def fallback_label(tag: str) -> str:
    return TAG_FALLBACK.get(str(tag or "").lower(), "页面元素")


def _is_check(event: dict[str, Any]) -> bool:
    return str(event.get("value", "")) in CHECK_VALUES


def _event_kind(event: dict[str, Any]) -> str:
    if _is_check(event):
        return "check"
    return str(event.get("type", "click"))


@dataclass
class Step:
    index: int = 0
    kind: str = "click"
    url: str = ""
    title: str = ""
    x: int = 0
    y: int = 0
    dpr: float = 1.0
    w: int = 0
    h: int = 0
    label: str = ""
    value: str = ""
    tag: str = ""
    image: str = ""
    source: str = ""
    ts: int = 0
    count: int = 1
    labels: list[str] = field(default_factory=list)
    text_override: str = ""
    mosaics: list[dict] = field(default_factory=list)
    suspect: bool = False
    # 复核页人工调整后的红框（裁剪图相对物理像素 [x0,y0,x1,y1]）；空表示按元素几何重算
    box: list[int] = field(default_factory=list)

    @property
    def action_text(self) -> str:
        """生成一句步骤说明；人工在确认页改过的文案优先保留。"""
        if self.text_override:
            return self.text_override
        if self.kind == "check":
            verb = CHECK_OFF if self.value == CHECK_OFF else CHECK_ON
            return f"{verb}【{self.label}】" if self.label else f"{verb}页面选项"

        if self.tag == "select":
            option = self.value or self.label
            return f"选择【{option}】" if option else "选择下拉选项"

        if self.kind == "input":
            # 教程里不展示具体输入内容：密码写「输入密码」，其余按标签写「输入账号/学号…」
            noun = "密码" if _is_password_label(self.label) else _input_noun(self.label)
            if self.label:
                return f"在【{self.label}】输入{noun}"
            return "在输入框中输入内容"

        unique = list(dict.fromkeys(x for x in self.labels if x))
        if self.label == CAPTCHA_LABEL:
            return "在验证码图片中依次点击指定文字"
        if len(unique) > 1:
            return "依次点击" + "、".join(f"【{x}】" for x in unique)
        if self.label:
            return f"点击【{self.label}】"
        return "点击页面元素"

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "kind": self.kind,
            "url": self.url,
            "title": self.title,
            "x": self.x,
            "y": self.y,
            "dpr": self.dpr,
            "w": self.w,
            "h": self.h,
            "label": self.label,
            "value": self.value,
            "tag": self.tag,
            "labels": self.labels,
            "source": self.source,
            "image": self.image,
            "mosaics": self.mosaics,
            "suspect": self.suspect,
            "box": self.box,
            "text": self.action_text,
        }


def load_events(path: str | Path) -> list[dict[str, Any]]:
    """读取扩展导出的 events.json。

    兼容两种结构：顶层数组，或 {"events": [...]}。
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("events", [])
    if not isinstance(data, list):
        raise ValueError("events.json 格式不对：应当是数组或含 events 数组的对象")
    return [e for e in data if isinstance(e, dict)]


def build_steps(events: Iterable[dict[str, Any]], window_ms: int = MERGE_WINDOW_MS) -> list[Step]:
    """把事件合并为步骤列表。"""
    ordered = sorted((e for e in events if e.get("type") in VALID_TYPES), key=lambda e: e.get("ts", 0))

    steps: list[Step] = []
    for event in ordered:
        shot = _basename(event.get("shot", ""))
        kind = _event_kind(event)
        raw_label = normalize_label(event.get("label", ""))
        label = raw_label or fallback_label(event.get("tag", ""))
        value = str(event.get("value", "") or "")

        if steps and _can_merge(steps[-1], event, label, window_ms):
            last = steps[-1]
            last.count += 1
            last.ts = int(event.get("ts", last.ts))
            if raw_label:
                last.labels.append(raw_label)
            if shot:
                last.image = shot
            # 合并后按"最后一次操作"定位与截图；
            # 几何（坐标+宽高）作为整体保留：只有新事件读到了完整有效矩形才覆盖，
            # 避免隐藏复选框这类 0×0 / 缺坐标事件把上一条可见元素的框冲偏
            new_x = int(event.get("x", last.x) or 0)
            new_y = int(event.get("y", last.y) or 0)
            new_w = int(event.get("w", last.w) or 0)
            new_h = int(event.get("h", last.h) or 0)
            if new_x > 0 and new_y > 0 and new_w >= 10 and new_h >= 10:
                last.x, last.y, last.w, last.h = new_x, new_y, new_w, new_h
            last.dpr = float(event.get("dpr", last.dpr) or 1)

            if kind == "check":
                last.kind = "check"
                last.value = value
                if raw_label:
                    last.label = raw_label
            elif kind == "input":
                last.kind = "input"
                if value:
                    last.value = value
                if raw_label:
                    last.label = raw_label
            elif raw_label:
                last.label = raw_label
            continue

        steps.append(
            Step(
                kind=kind,
                url=str(event.get("url", "")),
                title=str(event.get("title", "")),
                x=int(event.get("x", 0) or 0),
                y=int(event.get("y", 0) or 0),
                dpr=float(event.get("dpr", 1) or 1),
                w=int(event.get("w", 0) or 0),
                h=int(event.get("h", 0) or 0),
                label=label,
                value=value if kind in ("check", "input") else "",
                tag=str(event.get("tag", "") or ""),
                image=shot,
                source=shot,
                ts=int(event.get("ts", 0) or 0),
                labels=[raw_label] if raw_label else [],
            )
        )

    for step in steps:
        step.labels = list(dict.fromkeys(x for x in step.labels if x))
        if not step.label and step.labels:
            step.label = step.labels[0]
        # 同一图片区域上的多次连续点选，按图形验证码处理（图片/画布元素或标签含验证码关键词）
        if step.kind == "click" and step.count >= 2 and _looks_like_captcha(step):
            step.label = CAPTCHA_LABEL
        # 输入类步骤不留具体填写值：密码打码，其余清空；
        # 下拉选项本身就是教程要展示的选择结果，保留选项文字
        if step.kind == "input" and step.tag != "select":
            step.value = "••••••" if _is_password_label(step.label) else ""
        # 通用容器 + 读不到元素名 + 退回经验大框：疑似点在空白处的游离点击，复核页标黄
        step.suspect = (
            step.tag in GENERIC_TAGS
            and step.label == fallback_label(step.tag)
            and step.w >= 180
            and step.h >= 80
        )

    for i, step in enumerate(steps, start=1):
        step.index = i
    return steps


def _same_field(prev: Step, event: dict[str, Any]) -> bool:
    """点击的包装容器和随后输入的框是同一行（矩形相交、中心接近）。"""
    nx = int(event.get("x", 0) or 0)
    ny = int(event.get("y", 0) or 0)
    nw = int(event.get("w", 0) or 0)
    nh = int(event.get("h", 0) or 0)
    if nx <= 0 or ny <= 0 or nw < 10 or nh < 10 or prev.w < 10 or prev.h < 10:
        return False
    if abs(nx - prev.x) > 30 or abs(ny - prev.y) > 30:
        return False
    # 一边是大容器、一边是单行输入框（高度/宽度差太多），不是同一行
    if min(prev.h, nh) > 0 and max(prev.h, nh) / min(prev.h, nh) > 1.6:
        return False
    if min(prev.w, nw) > 0 and max(prev.w, nw) / min(prev.w, nw) > 1.6:
        return False
    return abs(nx - prev.x) <= (nw + prev.w) / 2 and abs(ny - prev.y) <= (nh + prev.h) / 2


def _same_widget(prev: Step, event: dict[str, Any]) -> bool:
    """两次点击落在同一个控件上（矩形几乎重合），如图形验证码依次点选。"""
    if prev.w < 10 or prev.h < 10:
        return False
    nx = int(event.get("x", 0) or 0)
    ny = int(event.get("y", 0) or 0)
    nw = int(event.get("w", 0) or 0)
    nh = int(event.get("h", 0) or 0)
    if nx <= 0 or ny <= 0 or nw < 10 or nh < 10:
        return False
    return (
        abs(nx - prev.x) <= 15
        and abs(ny - prev.y) <= 15
        and abs(nw - prev.w) <= 15
        and abs(nh - prev.h) <= 15
    )


def _can_merge(prev: Step, event: dict[str, Any], label: str, window_ms: int) -> bool:
    if prev.url != str(event.get("url", "")):
        return False
    gap = int(event.get("ts", 0) or 0) - prev.ts
    kind = _event_kind(event)
    # 勾选动作的 click 与 change 是同一次操作，跨类型合并
    if prev.kind == "check" or kind == "check":
        return True
    # 点进输入框、随后在同一个框里输入，即使间隔稍长也合成一步
    if prev.kind == "click" and kind == "input":
        if (label and prev.label == label) or _same_field(prev, event):
            return True
    # 同一输入框的多次输入（打字防抖批次 + 失焦 change）合并为一步
    if prev.kind == "input" and kind == "input":
        if (label and prev.label == label) or _same_field(prev, event):
            return True
    # 同一控件上的连续点击（图形验证码依次点选），或点在同一输入框的包装/内框上，合成一步
    if prev.kind == "click" and kind == "click" and 0 <= gap <= window_ms * 2:
        return _same_widget(prev, event) or _same_field(prev, event)
    return False


def _basename(path: str) -> str:
    return Path(str(path)).name if path else ""


def save_steps(steps: list[Step], path: str | Path) -> None:
    payload = [s.to_dict() for s in steps]
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def steps_from_dicts(payload: list[dict[str, Any]]) -> list[Step]:
    """从 steps.json（可能经过确认页编辑）重建步骤列表，并重新编号。"""
    steps: list[Step] = []
    for d in payload:
        if not isinstance(d, dict):
            continue
        steps.append(
            Step(
                index=int(d.get("index", 0) or 0),
                kind=str(d.get("kind", "click") or "click"),
                url=str(d.get("url", "") or ""),
                title=str(d.get("title", "") or ""),
                x=int(d.get("x", 0) or 0),
                y=int(d.get("y", 0) or 0),
                dpr=float(d.get("dpr", 1) or 1),
                w=int(d.get("w", 0) or 0),
                h=int(d.get("h", 0) or 0),
                label=str(d.get("label", "") or ""),
                value=str(d.get("value", "") or ""),
                tag=str(d.get("tag", "") or ""),
                image=str(d.get("image", "") or ""),
                source=str(d.get("source", "") or d.get("image", "") or ""),
                labels=list(d.get("labels") or []),
                text_override=str(d.get("text", "") or ""),
                mosaics=list(d.get("mosaics") or []),
                suspect=bool(d.get("suspect", False)),
                box=[int(v) for v in (d.get("box") or [])][:4],
            )
        )
    for i, step in enumerate(steps, start=1):
        step.index = i
    return steps


def load_steps(path: str | Path) -> list[Step]:
    """读取已保存的 steps.json，兼容数组或含 steps 字段的对象。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("steps", data.get("events", []))
    if not isinstance(data, list):
        raise ValueError("steps.json 格式不对：应当是数组或含 steps 数组的对象")
    return steps_from_dicts(data)


# 画面差异去重：相邻两步截图平均灰度差小于阈值时视为重复帧
DEDUPE_THRESHOLD = 2.0
_DEDUPE_THUMB = 64


def _frame_diff(a: Path, b: Path) -> float:
    """两张缩略灰度图的平均绝对差（0–255）；读不到时返回 255（不视为重复）。"""
    try:
        from PIL import Image

        ia = Image.open(a).convert("L").resize((_DEDUPE_THUMB, _DEDUPE_THUMB))
        ib = Image.open(b).convert("L").resize((_DEDUPE_THUMB, _DEDUPE_THUMB))
        pa, pb = list(ia.getdata()), list(ib.getdata())
        return sum(abs(x - y) for x, y in zip(pa, pb)) / len(pa)
    except Exception:
        return 255.0


def _same_target(a: Step, b: Step) -> bool:
    """两步是否指向同一控件：矩形几乎重合，或标签相同。"""
    if a.label and b.label and a.label == b.label:
        return True
    if a.w < 10 or a.h < 10 or b.w < 10 or b.h < 10:
        return False
    return (
        abs(a.x - b.x) <= 15
        and abs(a.y - b.y) <= 15
        and abs(a.w - b.w) <= 15
        and abs(a.h - b.h) <= 15
    )


def dedupe_similar_frames(
    steps: list[Step], shots_dir: str | Path, threshold: float = DEDUPE_THRESHOLD
) -> list[Step]:
    """相邻步骤截图几乎无变化、且指向同一控件时合并为一步，去掉重复帧。"""
    shots_dir = Path(shots_dir)
    kept: list[Step] = []
    for step in steps:
        if kept and step.source:
            prev = kept[-1]
            if prev.source and _same_target(prev, step):
                diff = _frame_diff(shots_dir / prev.source, shots_dir / step.source)
                if diff < threshold:
                    prev.count += step.count
                    for lb in step.labels:
                        if lb and lb not in prev.labels:
                            prev.labels.append(lb)
                    continue
        kept.append(step)
    for i, step in enumerate(kept, start=1):
        step.index = i
    return kept
