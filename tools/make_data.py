"""建立三套 ROM 的文本索引，并生成中文构建所需的文本数据。

输入：
- 原版 Black 2（美版，干净 dump）
- 上游 patched ROM（Emerald NDS）
- 黑2汉化版 ROM（日版基底，中文文本）

输出：
- build/index.json：每个文本文件的分类与行数
- zh_data/b2/<archive>/<index>.json：从黑2汉化版迁移的文本（仅行数可对齐的文件）
- zh_data/hoenn/<archive>/<index>.json：Hoenn 文本的英文原文（等待匹配中文）

用法：
    python tools/make_data.py \
        --black2 path/to/black2.nds \
        --patched path/to/patched.nds \
        --chinese path/to/black2-cn.nds \
        --out zh_data
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import ndspy.narc
import ndspy.rom

from b2text import MessageFile, parse_file

ARCHIVES = ("a/0/0/2", "a/0/0/3")


def read_archive(rom_path: Path, archive: str) -> list[MessageFile | None]:
    rom = ndspy.rom.NintendoDSRom.fromFile(str(rom_path))
    narc = ndspy.narc.NARC(rom.getFileByName(archive))
    files: list[MessageFile | None] = []
    for member in narc.files:
        try:
            files.append(parse_file(bytes(member)))
        except Exception:
            files.append(None)
    return files


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--black2", type=Path, required=True)
    parser.add_argument("--patched", type=Path, required=True)
    parser.add_argument("--chinese", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("zh_data"))
    args = parser.parse_args()

    index: dict = {"archives": {}}
    stats: dict[str, dict[str, int]] = {}

    for archive in ARCHIVES:
        original = read_archive(args.black2, archive)
        patched = read_archive(args.patched, archive)
        chinese = read_archive(args.chinese, archive)
        short = archive.rsplit("/", 1)[-1]
        entries = []
        count = {"b2": 0, "hoenn": 0, "new": 0, "special": 0, "b2_migrated": 0}

        for i, current in enumerate(patched):
            entry: dict = {"index": i}
            if current is None:
                entry["class"] = "special"
                count["special"] += 1
                entries.append(entry)
                continue
            entry["messages"] = len(current.messages)

            if i < len(original) and original[i] is not None:
                same = original[i].messages == current.messages
            else:
                same = False

            if i >= len(original):
                entry["class"] = "new"
                count["new"] += 1
                write_json(
                    args.out / "hoenn" / short / f"{i:04d}.json",
                    {"index": i, "source": "patched", "lines": current.messages},
                )
            elif same:
                entry["class"] = "b2"
                count["b2"] += 1
                # 黑2汉化版在同一索引、行数一致时，按行号迁移
                zh = chinese[i] if i < len(chinese) else None
                if zh is not None and len(zh.messages) == len(current.messages):
                    entry["b2_migrated"] = True
                    count["b2_migrated"] += 1
                    write_json(
                        args.out / "b2" / short / f"{i:04d}.json",
                        {
                            "index": i,
                            "source": "black2-cn",
                            "lines": zh.messages,
                        },
                    )
            else:
                entry["class"] = "hoenn"
                count["hoenn"] += 1
                write_json(
                    args.out / "hoenn" / short / f"{i:04d}.json",
                    {"index": i, "source": "patched", "lines": current.messages},
                )
            entries.append(entry)

        index["archives"][archive] = entries
        stats[archive] = count
        print(f"{archive}: {count}")

    write_json(Path("build/index.json"), index)
    print("index -> build/index.json")


if __name__ == "__main__":
    main()
