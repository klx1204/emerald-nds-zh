"""按中文词边界重排对话（jieba 分词 + 避头点 + 每页 2 行）。

    python tools/layout2.py --data zh_data
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import jieba

from layout import CONTROL, PUNCT, WHITELIST, char_width, fix_leading_punct, paginate

for word in (
    "宝可梦", "宝可梦中心", "宝可梦图鉴", "宝可梦训练家", "宝可梦联盟",
    "宝可梦商店", "宝可梦导航", "宝可方块", "训练家", "精灵球",
    "对战金字塔", "对战开拓区", "对战塔", "对战房间", "道馆", "道馆馆主",
    "四天王", "冠军", "劲敌", "博士", "宝可梦博士", "宝可梦研究员",
):
    jieba.add_word(word)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    while i < len(text):
        match = CONTROL.match(text, i)
        if match:
            tokens.append(match.group(0))
            i = match.end()
            continue
        j = i
        while j < len(text) and not CONTROL.match(text, j):
            j += 1
        for word in jieba.lcut(text[i:j]):
            if word and all(ch in PUNCT for ch in word) and tokens:
                tokens[-1] += word
            elif word:
                tokens.append(word)
        i = j
    return tokens


def wrap(text: str, limit: int) -> str:
    parts = re.split(r"(\{be01\}|\{be00\})", text)
    out: list[str] = []
    for part in parts:
        if part == "{be01}":
            out.append("{be01}\\n")
            continue
        if part == "{be00}":
            out.append("\\n")
            continue
        clean = part.replace("\\n", "")
        line: list[str] = []
        width = 0
        for token in tokenize(clean):
            w = sum(char_width(ch) for ch in token)
            if width + w > limit and line:
                # 标点不能放行首，附到当前行末尾
                if token and all(ch in PUNCT for ch in token):
                    line.append(token)
                    width += w
                    continue
                out.append("".join(line) + "\\n")
                line, width = [], 0
            line.append(token)
            width += w
        out.append("".join(line))
    return "".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("zh_data"))
    args = parser.parse_args()

    for path in sorted(args.data.glob("*/*/*.json")):
        rel = str(path.relative_to(args.data))
        if rel in WHITELIST:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = 0
        for i, line in enumerate(data["lines"]):
            if not re.search(r"[\u4e00-\u9fff]", line):
                continue
            limit = 128 if "0063" in rel or "0442" in rel or "0443" in rel else 150
            new = fix_leading_punct(paginate(wrap(line, limit)))
            if new != line:
                data["lines"][i] = new
                changed += 1
        if changed:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{rel}: {changed}")


if __name__ == "__main__":
    main()
