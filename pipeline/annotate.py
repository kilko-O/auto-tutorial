"""截图裁剪 + 标注

给定一张整屏截图和一个步骤，裁出点击附近的区域，并画红框与序号。
坐标换算：截图是物理像素，事件坐标是 CSS 像素，必须乘 devicePixelRatio。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CROP_W, CROP_H = 760, 440          # 输出裁剪区大小（物理像素）
FOCUS_W, FOCUS_H = 210, 96         # 红框大小，元素尺寸未知时的经验值
RED = (214, 48, 49)
BADGE_R = 17

_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "msyhbd.ttc",
    "msyh.ttc",
    "arialbd.ttf",
)


def font(size: int) -> ImageFont.ImageFont:
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def crop_and_mark(shot_path: str | Path, step, out_path: str | Path, crop_size=None) -> Path:
    """裁出焦点区域并标注，返回输出文件路径。"""
    shot_path = Path(shot_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(shot_path).convert("RGB")
    width, height = img.size

    dpr = step.dpr if step.dpr and step.dpr > 0 else 1.0
    cx = int(round(step.x * dpr))
    cy = int(round(step.y * dpr))
    cx = max(0, min(width - 1, cx))
    cy = max(0, min(height - 1, cy))

    cw, ch = crop_size or (CROP_W, CROP_H)
    cw = min(cw, width)
    ch = min(ch, height)

    left = max(0, min(width - cw, cx - cw // 2))
    top = max(0, min(height - ch, cy - ch // 2))
    cropped = img.crop((left, top, left + cw, top + ch)).convert("RGBA")

    px, py = cx - left, cy - top
    box = (
        max(2, px - FOCUS_W // 2),
        max(2, py - FOCUS_H // 2),
        min(cw - 2, px + FOCUS_W // 2),
        min(ch - 2, py + FOCUS_H // 2),
    )

    # 框外压暗，突出焦点
    dim = Image.new("RGBA", cropped.size, (0, 0, 0, 0))
    dim_draw = ImageDraw.Draw(dim)
    for rect in (
        (0, 0, cw, box[1]),
        (0, box[3], cw, ch),
        (0, box[1], box[0], box[3]),
        (box[2], box[1], cw, box[3]),
    ):
        dim_draw.rectangle(rect, fill=(0, 0, 0, 55))
    cropped = Image.alpha_composite(cropped, dim)

    draw = ImageDraw.Draw(cropped)
    draw.rectangle(box, outline=RED, width=3)

    # 序号圆圈，放在框的左上角
    bx = max(BADGE_R + 4, box[0] - 6)
    by = max(BADGE_R + 4, box[1] - 6)
    draw.ellipse(
        (bx - BADGE_R, by - BADGE_R, bx + BADGE_R, by + BADGE_R),
        fill=RED,
        outline=(255, 255, 255),
        width=2,
    )
    label = str(step.index)
    text_font = font(20)
    tw = draw.textlength(label, font=text_font)
    draw.text((bx - tw / 2, by - 12), label, font=text_font, fill=(255, 255, 255))

    cropped.convert("RGB").save(out_path, format="PNG", optimize=True)
    return out_path
