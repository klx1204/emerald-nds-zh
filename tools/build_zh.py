"""把 zh_data 里的文本和字体写进上游 patched ROM，生成中文 ROM。

    python tools/build_zh.py \
        --patched work/patched.nds \
        --data zh_data \
        --font0 work/fonts/font0-zh.nftr \
        --font2 work/fonts/font2-zh.nftr \
        --out work/zh.nds

替换范围：
- zh_data/b2/<archive>/<index>.json       从黑2汉化版迁移的 UI 文本
- zh_data/hoenn_zh/<archive>/<index>.json Hoenn 文本（命中的中文 + 未命中的英文）
- 字体 a/0/2/3 的第 0、2 个字体
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import ndspy.narc
import ndspy.rom

from b2text import build_file, parse_file
from patch_rom import patch

ARCHIVES = {"a/0/0/2": "2", "a/0/0/3": "3"}


def apply_text(narc: ndspy.narc.NARC, archive: str, data: Path) -> tuple[int, int, int]:
    short = ARCHIVES[archive]
    replaced = skipped = 0
    for i, member in enumerate(narc.files):
        source = None
        for folder in ("b2", "hoenn_zh"):
            candidate = data / folder / short / f"{i:04d}.json"
            if candidate.exists():
                source = candidate
                break
        if source is None:
            continue
        try:
            current = parse_file(bytes(member))
        except Exception:
            skipped += 1
            continue
        lines = json.loads(source.read_text(encoding="utf-8"))["lines"]
        if len(lines) != len(current.messages):
            print(f"跳过 {archive}[{i}]：行数 {len(lines)} != {len(current.messages)}")
            skipped += 1
            continue
        narc.files[i] = build_file(lines, current.pad)
        replaced += 1
    return replaced, skipped, len(narc.files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patched", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("zh_data"))
    parser.add_argument("--font0", type=Path, required=True)
    parser.add_argument("--font2", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rom = ndspy.rom.NintendoDSRom.fromFile(str(args.patched))
    replacements: dict[str, bytes] = {}

    for archive in ARCHIVES:
        narc = ndspy.narc.NARC(rom.getFileByName(archive))
        replaced, skipped, total = apply_text(narc, archive, args.data)
        replacements[archive] = narc.save()
        print(f"{archive}: 替换 {replaced}/{total}，跳过 {skipped}")

    fonts = ndspy.narc.NARC(rom.getFileByName("a/0/2/3"))
    fonts.files[0] = args.font0.read_bytes()
    if args.font2 is not None:
        fonts.files[2] = args.font2.read_bytes()
    replacements["a/0/2/3"] = fonts.save()
    print(f"字体: 0{' + 2' if args.font2 else ''}")

    # 保持原 ROM 大小，只改 FAT 指针
    patch(args.patched, args.out, replacements)


if __name__ == "__main__":
    main()
