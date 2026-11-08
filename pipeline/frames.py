"""事件流 -> 步骤列表

把扩展录下来的原始事件（点击、输入）合并成"人看得懂的步骤"。

合并规则：
1. 只有 click / input 参与成步骤，其它忽略；
2. 相邻两条事件同属一个页面（url 相同）、同类型、间隔 <= window_ms，合并成一步；
3. 合并后保留最后一条事件的截图，文字合成"依次点击 A、B"。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

MERGE_WINDOW_MS = 1500
VALID_TYPES = ("click", "input")


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
        if self.kind == "input":
            if self.label and self.value:
                return f"在【{self.label}】输入「{self.value}」"
            if self.label:
                return f"在【{self.label}】输入内容"
            return "在输入框中输入内容"

        if self.count > 1:
            names = "、".join(f"【{x}】" for x in self.labels if x)
            return f"依次点击{names}" if names else "依次点击页面上的多个位置"

        if self.label:
            return f"点击【{self.label}】"
        return "点击页面上的位置"

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
        if steps and _can_merge(steps[-1], event, window_ms):
            last = steps[-1]
            last.count += 1
            last.ts = int(event.get("ts", last.ts))
            if event.get("label"):
                last.labels.append(str(event["label"]))
            if shot:
                last.image = shot
            # 合并后按"最后一次操作"定位与截图，保证画面与红框一致
            last.x = int(event.get("x", last.x) or 0)
            last.y = int(event.get("y", last.y) or 0)
            last.dpr = float(event.get("dpr", last.dpr) or 1)
            if event.get("label"):
                last.label = str(event["label"])
            if event.get("type") == "input" and event.get("value"):
                last.value = str(event["value"])
            continue

        steps.append(
            Step(
                kind=str(event.get("type")),
                url=str(event.get("url", "")),
                title=str(event.get("title", "")),
                x=int(event.get("x", 0) or 0),
                y=int(event.get("y", 0) or 0),
                dpr=float(event.get("dpr", 1) or 1),
                label=str(event.get("label", "") or ""),
                value=str(event.get("value", "") or ""),
                image=shot,
                ts=int(event.get("ts", 0) or 0),
                labels=[str(event["label"])] if event.get("label") else [],
            )
        )

    for i, step in enumerate(steps, start=1):
        step.index = i
    return steps


def _can_merge(prev: Step, event: dict[str, Any], window_ms: int) -> bool:
    if prev.url != str(event.get("url", "")):
        return False
    if prev.kind != str(event.get("type")):
        return False
    gap = int(event.get("ts", 0) or 0) - prev.ts
    return 0 <= gap <= window_ms


def _basename(path: str) -> str:
    return Path(str(path)).name if path else ""


def save_steps(steps: list[Step], path: str | Path) -> None:
    payload = [s.to_dict() for s in steps]
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
