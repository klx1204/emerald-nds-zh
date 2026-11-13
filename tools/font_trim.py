"""裁剪字体：删除游戏用不到的 glyph，腾出空间补中文，保持字体大小接近原版。

B2 的输入界面有固定的字体缓冲区，字体变大（371 KB / 7093 glyph）会死机。
这里只保留：
- ASCII、标点、假名、全角符号、拉丁扩展；
- zh_data 里实际出现的字符；
- 需要补的中文缺字。
其余日文汉字/未用符号删除，再追加中文，最终大小通常小于原版。

    python tools/font_trim.py \
        --font-dir work/fonts/font0clean \
        --data zh_data \
        --chars-file work/zh_chars.txt \
        --ttf ... --ttf-size 12 --shadow right \
        --nitro-font ... --out work/fonts/font0-trim.nftr
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from font_build import add_glyphs  # noqa: E402

GUIDE = 4


def keep_chars(data_dir: Path) -> set[str]:
    chars: set[str] = set()
    for path in data_dir.glob("*/*/*.json"):
        for line in json.loads(path.read_text(encoding="utf-8"))["lines"]:
            chars.update(line)
    return chars


def must_chars() -> set[str]:
    keep = {chr(code) for code in range(0x20, 0x7F)}
    keep |= {chr(code) for code in range(0xA0, 0x100)}
    keep |= {chr(code) for code in range(0x3000, 0x3040)}
    keep |= {chr(code) for code in range(0x3040, 0x3100)}
    keep |= {chr(code) for code in range(0xFF00, 0xFFF0)}
    keep |= set("…—“”‘’·←↑→↓")
    return keep


def trim(font_dir: Path, out_dir: Path, chars: set[str], must: set[str]) -> None:
    font = json.loads((font_dir / "font.json").read_text(encoding="utf-8"))
    font.pop("$schema", None)
    sheet = Image.open(font_dir / "glyphs.png")
    cell_w, cell_h = font["cellWidth"], font["cellHeight"]
    columns = (sheet.width - 1) // (cell_w + 1)

    keep = [g for g in font["glyphs"] if g["char"] in chars or g["char"] in must]
    rows = math.ceil(len(keep) / columns)
    out = Image.new("P", (columns * (cell_w + 1) + 1, rows * (cell_h + 1) + 1), GUIDE)
    out.putpalette(sheet.getpalette())

    index = {g["char"]: i for i, g in enumerate(font["glyphs"])}
    for new_index, glyph in enumerate(keep):
        old = index[glyph["char"]]
        sx = old % columns * (cell_w + 1) + 1
        sy = old // columns * (cell_h + 1) + 1
        dx = new_index % columns * (cell_w + 1) + 1
        dy = new_index // columns * (cell_h + 1) + 1
        out.paste(sheet.crop((sx, sy, sx + cell_w, sy + cell_h)), (dx, dy))

    font["glyphs"] = keep
    out_dir.mkdir(parents=True, exist_ok=True)
    out.save(out_dir / "glyphs.png")
    (out_dir / "font.json").write_text(
        json.dumps(font, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"裁剪：{len(font['glyphs']) + (index.__len__() - len(keep))} -> {len(keep)} glyph")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-dir", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("zh_data"))
    parser.add_argument("--chars-file", type=Path, required=True)
    parser.add_argument("--ttf", type=Path, required=True)
    parser.add_argument("--ttf-size", type=int, required=True)
    parser.add_argument("--shadow", choices=("right", "outline"), default="right")
    parser.add_argument("--y-offset", type=int, default=1)
    parser.add_argument("--nitro-font", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    chars = set(args.chars_file.read_text(encoding="utf-8"))
    chars |= keep_chars(args.data)
    must = must_chars()
    trim(args.font_dir, Path(str(args.out) + ".dir"), chars, must)
    add_glyphs(
        Path(str(args.out) + ".dir"),
        None,
        list(chars),
        "",
        ttf=args.ttf,
        ttf_size=args.ttf_size,
        cjk_only=True,
        shadow=args.shadow,
        y_offset=args.y_offset,
    )
    import subprocess

    subprocess.run(
        [sys.executable, str(args.nitro_font), "pack", str(args.out) + ".dir", str(args.out)],
        check=True,
    )


if __name__ == "__main__":
    main()
