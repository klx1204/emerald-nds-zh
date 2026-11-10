"""把 Hoenn 文本的英文原文与中文 pokeemerald-expansion 的现成译文做精确匹配。

不翻译、不生成新文本：只有规范化后完全相同的句子才替换，其余保留英文。

    python tools/match_zh.py \
        --english /path/to/pokeemerald \
        --chinese /path/to/pokeemerald-expansion \
        --data zh_data/hoenn \
        --out zh_data/hoenn_zh
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LABEL = re.compile(r"^([A-Za-z_]\w*)::?\s*(?:@.*)?$")
STRING = re.compile(r'\.string\s+"(.*)"')
PLACEHOLDER = re.compile(r"\{([^}]*)\}")


def parse_labels(root: Path) -> dict[str, str]:
    """提取 .inc/.c/.h 里 Label: 后面连续的 .string 文本。"""
    out: dict[str, str] = {}
    files = []
    for pattern in ("data/**/*.inc", "src/**/*.c", "src/**/*.h"):
        files += list(root.glob(pattern))
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").split("\n")
        except (UnicodeDecodeError, OSError):
            continue
        label = None
        buffer = ""
        for line in lines:
            match = LABEL.match(line.strip())
            if match:
                if label and buffer:
                    out.setdefault(label, buffer)
                label = match.group(1)
                buffer = ""
                continue
            if label is None:
                continue
            string = STRING.search(line)
            if string:
                buffer += string.group(1)
                if "$" in buffer:
                    out.setdefault(label, buffer)
                    label, buffer = None, ""
            elif line.strip() and ".string" not in line and not buffer:
                label = None
        if label and buffer:
            out.setdefault(label, buffer)
    return out


def normalize(text: str) -> str:
    text = PLACEHOLDER.sub("", text)
    text = text.replace("\\n", "").replace("\\l", "").replace("\\p", "")
    text = text.replace('\\"', '"').replace("\\", "")
    if text.endswith("$"):
        text = text[:-1]
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("é", "e").replace("É", "E")
    text = re.sub(r"\s+", "", text)
    return text.lower()


def to_b2(text: str) -> str:
    """把 GBA 文本转换成 B2 的文本格式。"""
    text = text.replace("\\p", "{be01}\\n").replace("\\l", "{be00}\\n")
    text = text.replace("$", "")
    replacements = {
        "{PLAYER}": "{0100:0}",
        "{RIVAL}": "{0100:4}",
        "{STR_VAR_1}": "{0100:1}",
        "{STR_VAR_2}": "{0100:2}",
        "{STR_VAR_3}": "{0100:3}",
        "{KUN}": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("'", "’")
    # 中文译文里不应再出现 GBA 的转义
    text = text.replace("\\c", "")
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--english", type=Path, required=True)
    parser.add_argument("--chinese", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("zh_data/hoenn"))
    parser.add_argument("--out", type=Path, default=Path("zh_data/hoenn_zh"))
    args = parser.parse_args()

    english = parse_labels(args.english)
    chinese = parse_labels(args.chinese)
    common = sorted(set(english) & set(chinese))
    table: dict[str, str] = {}
    for label in common:
        key = normalize(english[label])
        if key:
            table.setdefault(key, chinese[label])
    print(f"英文标签 {len(english)}，中文标签 {len(chinese)}，共同 {len(common)}，匹配表 {len(table)}")

    total = matched = 0
    unmatched: list[str] = []
    for path in sorted(args.data.rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        lines = data["lines"]
        hits = []
        for i, line in enumerate(lines):
            total += 1
            key = normalize(line)
            zh = table.get(key)
            if zh is None:
                hits.append(False)
                unmatched.append(line)
                continue
            converted = to_b2(zh)
            # 译文里的占位符必须是原文占位符的子集，否则控制码会错位
            source_codes = set(PLACEHOLDER.findall(line))
            target_codes = set(PLACEHOLDER.findall(converted))
            if not target_codes.issubset(source_codes):
                hits.append(False)
                unmatched.append(line)
                continue
            lines[i] = converted
            hits.append(True)
            matched += 1
        data["lines"] = lines
        data["matched"] = hits
        target = args.out / path.relative_to(args.data)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"总行数 {total}，命中 {matched}（{matched / total * 100:.1f}%），未命中 {total - matched}")
    Path("build").mkdir(exist_ok=True)
    Path("build/unmatched_hoenn.txt").write_text("\n".join(unmatched), encoding="utf-8")


if __name__ == "__main__":
    main()
