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

TAG_FALLBACK = {
    "input": "输入框",
    "button": "按钮",
    "a": "链接",
    "span": "页面元素",
    "div": "页面元素",
    "li": "列表项",
    "label": "选项",
}


def normalize_label(text: str) -> str:
    """去掉协议书名号、压缩空白、超长截断。"""
    t = str(text or "")
    t = re.sub(r"《[^》]*》", "", t)
    t = re.sub(r"\s+", " ", t).strip()
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
    label: str = ""
    value: str = ""
    image: str = ""
    ts: int = 0
    count: int = 1
    labels: list[str] = field(default_factory=list)

    @property
    def action_text(self) -> str:
        """生成一句步骤说明。"""
        if self.kind == "check":
            verb = CHECK_OFF if self.value == CHECK_OFF else CHECK_ON
            return f"{verb}【{self.label}】" if self.label else f"{verb}页面选项"

        if self.kind == "input":
            if self.label and self.value:
                return f"在【{self.label}】输入「{self.value}」"
            if self.label:
                return f"在【{self.label}】输入内容"
            return "在输入框中输入内容"

        unique = list(dict.fromkeys(x for x in self.labels if x))
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
            "label": self.label,
            "image": self.image,
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

        if steps and _can_merge(steps[-1], event, window_ms):
            last = steps[-1]
            last.count += 1
            last.ts = int(event.get("ts", last.ts))
            if label:
                last.labels.append(label)
            if shot:
                last.image = shot
            # 合并后按"最后一次操作"定位与截图，保证画面与红框一致
            last.x = int(event.get("x", last.x) or 0)
            last.y = int(event.get("y", last.y) or 0)
            last.dpr = float(event.get("dpr", last.dpr) or 1)

            if kind == "check":
                last.kind = "check"
                last.value = value
                last.label = label
            elif kind == "input" and value:
                last.value = value
                last.label = label
            elif label:
                last.label = label
            continue

        steps.append(
            Step(
                kind=kind,
                url=str(event.get("url", "")),
                title=str(event.get("title", "")),
                x=int(event.get("x", 0) or 0),
                y=int(event.get("y", 0) or 0),
                dpr=float(event.get("dpr", 1) or 1),
                label=label,
                value=value if kind in ("check", "input") else "",
                image=shot,
                ts=int(event.get("ts", 0) or 0),
                labels=[label] if label else [],
            )
        )

    for step in steps:
        step.labels = list(dict.fromkeys(x for x in step.labels if x))
        if not step.label and step.labels:
            step.label = step.labels[0]

    for i, step in enumerate(steps, start=1):
        step.index = i
    return steps


def _can_merge(prev: Step, event: dict[str, Any], window_ms: int) -> bool:
    if prev.url != str(event.get("url", "")):
        return False
    gap = int(event.get("ts", 0) or 0) - prev.ts
    if not (0 <= gap <= window_ms):
        return False
    kind = _event_kind(event)
    if prev.kind == kind:
        return True
    # 勾选动作的 click 与 change 是同一次操作，跨类型合并
    return prev.kind == "check" or kind == "check"


def _basename(path: str) -> str:
    return Path(str(path)).name if path else ""


def save_steps(steps: list[Step], path: str | Path) -> None:
    payload = [s.to_dict() for s in steps]
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
