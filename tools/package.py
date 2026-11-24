"""把浏览器扩展打成可分发的 zip（Chrome / Edge 均可加载解压目录或 zip）

运行：python tools/package.py
产物：dist/auto-tutorial-extension-<version>.zip
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT_DIR = ROOT / "extension"
DIST_DIR = ROOT / "dist"


def main() -> int:
    manifest_path = EXT_DIR / "manifest.json"
    if not manifest_path.exists():
        print("找不到 extension/manifest.json")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = str(manifest.get("version", "0.0.0"))

    files = sorted(p for p in EXT_DIR.rglob("*") if p.is_file())
    if not files:
        print("extension/ 目录为空")
        return 1

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DIST_DIR / f"auto-tutorial-extension-{version}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for src in files:
            zf.write(src, arcname=src.relative_to(EXT_DIR))

    size_kb = zip_path.stat().st_size / 1024
    print(f"已打包 {len(files)} 个文件 -> {zip_path.relative_to(ROOT)}（{size_kb:.1f} KB）")
    for src in files:
        print("  -", src.relative_to(EXT_DIR))
    return 0


if __name__ == "__main__":
    sys.exit(main())
