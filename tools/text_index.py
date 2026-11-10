"""导出 ROM 文本库的索引，用于对比原版黑2、上游 patched ROM 与黑2汉化版。

    python tools/text_index.py --rom black2.nds --out build/index_black2.json

输出每个文本文件的下标、消息数、总字符数和前几条预览，不写 ROM 内容。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import ndspy.narc
import ndspy.rom

from b2text import parse_file

ARCHIVES = ("a/0/0/2", "a/0/0/3")


def index_rom(rom_path: Path) -> dict:
    rom = ndspy.rom.NintendoDSRom.fromFile(str(rom_path))
    result = {"rom": rom_path.name, "archives": {}}
    for archive in ARCHIVES:
        try:
            data = rom.getFileByName(archive)
        except KeyError:
            result["archives"][archive] = {"error": "missing"}
            continue
        narc = ndspy.narc.NARC(data)
        files = []
        for i, member in enumerate(narc.files):
            try:
                parsed = parse_file(bytes(member))
            except Exception as exc:  # 记录异常文件，不中断索引
                files.append({"index": i, "error": f"{type(exc).__name__}: {exc}"})
                continue
            preview = []
            for message in parsed.messages[:3]:
                preview.append(message[:80])
            files.append(
                {
                    "index": i,
                    "messages": len(parsed.messages),
                    "chars": sum(len(m) for m in parsed.messages),
                    "preview": preview,
                }
            )
        result["archives"][archive] = {"count": len(narc.files), "files": files}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    index = index_rom(args.rom)
    args.out.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    for archive, info in index["archives"].items():
        if "error" in info:
            print(f"{archive}: {info['error']}")
        else:
            print(f"{archive}: {info['count']} 个文件")


if __name__ == "__main__":
    main()
