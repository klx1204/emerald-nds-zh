"""给 B2 的 NFTR 字体补简体中文字形。

字形取自 pokeemerald-expansion 的 chinese_normal.png / chinese_small.png
（16×16 点阵，按 charmap.txt 的编码排列）。B2 的 cell 尺寸从 font.json 读取
（字体 0 是 12×15，字体 2 是 11×11），源字形按比例缩放到 cell 内。

字体本身的 dump/pack 由 pokebw2 的 tools/data/nitro_font.py 完成：

    python tools/font_build.py \
        --font-dir work/fonts/font0 \
        --expansion /path/to/pokeemerald-expansion \
        --chars-file work/missing_chars.txt \
        --nitro-font /path/to/pokebw2/tools/data/nitro_font.py \
        --out work/fonts/font0-zh.nftr
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

GUIDE = 4  # glyphs.png 里 cell 之间的分隔线颜色索引


def load_charmap(expansion: Path) -> dict[str, int]:
    table: dict[str, int] = {}
    for line in (expansion / "charmap.txt").read_text(encoding="utf-8").splitlines():
        match = re.match(r"'(.+?)'\s*=\s*([0-9A-Fa-f]+)", line)
        if match and len(match.group(1)) == 1:
            table[match.group(1)] = int(match.group(2), 16)
    return table


def glyph_index(code: int) -> int:
    """charmap 编码 -> 字库图里的 tile 下标。"""
    high, low = code >> 8, code & 0xFF
    if high > 0x1B:
        high -= 1
    if high > 0x06:
        high -= 1
    high -= 1
    return (high << 8) | low


def quantize(value: int) -> int:
    """把灰度值压到 2bpp 的 0/1/2。"""
    if value < 64:
        return 0
    if value < 160:
        return 1
    return 2


def add_glyphs(
    font_dir: Path, expansion: Path, chars: list[str], sheet_name: str, replace: bool = True
) -> int:
    font = json.loads((font_dir / "font.json").read_text(encoding="utf-8"))
    font.pop("$schema", None)
    cell_w, cell_h = font["cellWidth"], font["cellHeight"]

    position = {glyph["char"]: i for i, glyph in enumerate(font["glyphs"])}
    wanted = list(dict.fromkeys(chars))
    # 已有码位可能是空的或日文占位字形，所以默认全部重绘
    missing = [ch for ch in wanted if ch not in position]
    if not replace and not missing:
        print("没有缺字")
        return 0

    sheet = Image.open(font_dir / "glyphs.png")
    if sheet.mode != "P":
        raise SystemExit(f"glyphs.png 不是索引 PNG（mode={sheet.mode}）")
    sheet_w, sheet_h = sheet.size
    columns = (sheet_w - 1) // (cell_w + 1)
    rows = (sheet_h - 1) // (cell_h + 1)
    if columns * rows < len(font["glyphs"]):
        raise SystemExit(f"glyphs.png 容量不足：{columns * rows} < {len(font['glyphs'])}")

    needed = len(font["glyphs"]) + len(missing)
    new_rows = max(rows, -(-needed // columns))
    new_h = new_rows * (cell_h + 1) + 1

    out = Image.new("P", (sheet_w, new_h), GUIDE)
    out.putpalette(sheet.getpalette())
    out.paste(sheet, (0, 0))
    out_px = out.load()

    source = Image.open(expansion / "graphics/fonts" / sheet_name)
    if source.size[0] % 16 or source.size[1] % 16:
        raise SystemExit(f"字库图尺寸异常：{source.size}")
    src_columns = source.size[0] // 16
    cmap = load_charmap(expansion)

    # 用字体里已有的全角汉字作为字宽/字距参考
    reference = next(
        (g for g in font["glyphs"] if 0x4E00 <= ord(g["char"]) <= 0x9FFF), None
    )
    left = reference["left"] if reference else 1
    width = reference["width"] if reference else cell_w
    advance = reference["advance"] if reference else cell_w + 1

    written = 0
    for ch in wanted:
        code = cmap.get(ch)
        if code is None:
            continue
        index = glyph_index(code)
        # 源图是索引 PNG：0 是背景，1/2 是笔画深浅。不能转灰度，
        # 否则调色板会把背景变成 255、笔画变成深色，量化后整格反色。
        tile = source.crop(
            (
                (index % src_columns) * 16,
                (index // src_columns) * 16,
                (index % src_columns) * 16 + 16,
                (index // src_columns) * 16 + 16,
            )
        )
        tile = tile.resize((cell_w, cell_h), Image.NEAREST)

        if ch in position:
            slot = position[ch]
        else:
            slot = len(font["glyphs"])
            font["glyphs"].append(
                {"char": ch, "left": left, "width": width, "advance": advance}
            )
            position[ch] = slot
        x0 = slot % columns * (cell_w + 1) + 1
        y0 = slot // columns * (cell_h + 1) + 1
        for y in range(cell_h):
            for x in range(cell_w):
                out_px[x0 + x, y0 + y] = tile.getpixel((x, y)) & 0x03
        written += 1

    out.save(font_dir / "glyphs.png")
    (font_dir / "font.json").write_text(
        json.dumps(font, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        f"补入 {written} 个字形（cell {cell_w}x{cell_h}），"
        f"sheet {sheet_w}x{sheet_h} -> {sheet_w}x{new_h}"
    )
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-dir", type=Path, required=True)
    parser.add_argument("--expansion", type=Path, required=True)
    parser.add_argument("--chars", default="")
    parser.add_argument("--chars-file", type=Path, default=None)
    parser.add_argument("--sheet", default="chinese_normal.png")
    parser.add_argument("--nitro-font", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    chars = list(args.chars)
    if args.chars_file:
        chars += list(args.chars_file.read_text(encoding="utf-8"))
    add_glyphs(args.font_dir, args.expansion, chars, args.sheet)

    nitro = args.nitro_font or Path("tools/vendor/nitro_font.py")
    if not nitro.exists():
        raise SystemExit("找不到 nitro_font.py；用 --nitro-font 指向 pokebw2 的 tools/data/nitro_font.py")
    subprocess.run([sys.executable, str(nitro), "pack", str(args.font_dir), str(args.out)], check=True)


if __name__ == "__main__":
    main()
