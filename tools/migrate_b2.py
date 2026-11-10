"""把黑2汉化版的现成中文迁移到 HoennB2 的文本文件。

用原版黑2与黑2汉化版的同索引文件建立“英文行 -> 中文行”映射，
再按文本匹配 patched 的每一行。这样 HoennB2 重排过行号也能命中；
映射里没有的行（HoennB2 改写/新增）保持现状。

    python tools/migrate_b2.py \
        --black2 orig.nds --patched patched.nds --chinese black2-cn.nds \
        --data zh_data
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import ndspy.narc
import ndspy.rom

from b2text import parse_file

CJK = re.compile(r"[\u4e00-\u9fff]")
ARCHIVE = "a/0/0/2"
SHORT = "2"


def read_archive(path: Path) -> list[list[str] | None]:
    rom = ndspy.rom.NintendoDSRom.fromFile(str(path))
    narc = ndspy.narc.NARC(rom.getFileByName(ARCHIVE))
    out: list[list[str] | None] = []
    for member in narc.files:
        try:
            out.append(parse_file(bytes(member)).messages)
        except Exception:
            out.append(None)
    return out


def build_map(original: list[str], chinese: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for en, zh in zip(original, chinese):
        if en and zh and CJK.search(zh) and not CJK.search(en):
            mapping.setdefault(en, zh)
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--black2", type=Path, required=True)
    parser.add_argument("--patched", type=Path, required=True)
    parser.add_argument("--chinese", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("zh_data"))
    parser.add_argument("--force", default="", help="行号即 ID 的表，按行强行替换：63,442,443,382,383")
    args = parser.parse_args()
    force = {int(x) for x in args.force.split(",") if x.strip()}

    original = read_archive(args.black2)
    chinese = read_archive(args.chinese)
    patched = read_archive(args.patched)

    report = []
    for path in sorted((args.data / "hoenn_zh" / SHORT).glob("*.json")):
        index = int(path.stem)
        if index >= len(patched) or patched[index] is None:
            continue
        if index >= len(original) or index >= len(chinese):
            continue
        if original[index] is None or chinese[index] is None:
            continue
        mapping = build_map(original[index], chinese[index])
        current = json.loads(path.read_text(encoding="utf-8"))
        lines = current["lines"]
        hit = 0

        # 行号即 ID 的表（道具/图鉴/训练家/职业）：行数一致时按行替换
        if index in force and len(chinese[index]) == len(lines):
            for i, line in enumerate(lines):
                zh = chinese[index][i]
                if zh and CJK.search(zh) and not CJK.search(line):
                    lines[i] = zh
                    hit += 1
        elif mapping:
            for i, line in enumerate(lines):
                zh = mapping.get(line)
                if zh and zh != line:
                    lines[i] = zh
                    hit += 1
        if hit:
            path.write_text(json.dumps(current, ensure_ascii=False, indent=1), encoding="utf-8")
            report.append((index, hit, len(lines), len(mapping)))
            print(f"{index:04d}: {hit}/{len(lines)}（映射 {len(mapping)}）")

    Path("build").mkdir(exist_ok=True)
    with open("build/report_migrate.txt", "w", encoding="utf-8") as f:
        f.write("索引\t替换\t总行数\t映射条目\n")
        for row in report:
            f.write("\t".join(map(str, row)) + "\n")
        f.write(f"\n合计替换 {sum(r[1] for r in report)} 行，涉及 {len(report)} 个文件\n")
    print(f"合计替换 {sum(r[1] for r in report)} 行，涉及 {len(report)} 个文件")


if __name__ == "__main__":
    main()
