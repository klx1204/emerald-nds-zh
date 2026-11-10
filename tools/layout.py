"""按 B2 字体宽度重排中文文本。

对话框约 208px（16 个全角字），道具/图鉴说明约 176px（13-14 字）。
保留 {be00}/{be01} 分页/滚动控制码；只处理含中文的行，英文行不动。
B2 原生自动换行界面（如 0043 地点介绍）放进白名单，不重排。

    python tools/layout.py --data zh_data
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CONTROL = re.compile(r"\{[^}]*\}|\\x\{[0-9a-fA-F]+\}")
CJK = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")

# 自动换行/滚动文本，交给游戏自己处理
WHITELIST = {
    "hoenn_zh/2/0043.json",  # 地点介绍
    "b2/2/0043.json",
}

NARROW = {"hoenn_zh/2/0063.json", "hoenn_zh/2/0442.json", "hoenn_zh/2/0443.json"}


def char_width(ch: str) -> int:
    if ch in "\n":
        return 0
    code = ord(ch)
    if 0x2E80 <= code <= 0x9FFF or 0xFF00 <= code <= 0xFFEF or 0x3000 <= code <= 0x303F:
        return 13
    return 6


def wrap(text: str, limit: int) -> str:
    """按显示宽度折行，保留控制码；已有 \\n 先去掉再重排。"""
    # 分页/滚动控制码作为硬边界
    parts = re.split(r"(\{be00\}|\{be01\})", text)
    out: list[str] = []
    for part in parts:
        if part in ("{be00}", "{be01}"):
            # 翻页/滚动之后必须换行，否则两段文字会挤在同一行
            out.append(part + "\\n")
            continue
        # 去掉原有换行，再按宽度重排
        clean = part.replace("\\n", "")
        line: list[str] = []
        width = 0
        i = 0
        while i < len(clean):
            match = CONTROL.match(clean, i)
            if match:
                token = match.group(0)
                line.append(token)
                i = match.end()
                continue
            ch = clean[i]
            w = char_width(ch)
            if width + w > limit and line and not CJK.match(ch):
                out.append("".join(line) + "\\n")
                line, width = [], 0
            elif width + w > limit and line:
                out.append("".join(line) + "\\n")
                line, width = [], 0
            line.append(ch)
            width += w
            i += 1
        out.append("".join(line))
    return "".join(out)


def display_width(text: str) -> int:
    text = text.replace("\\n", "").replace("{be00}", "").replace("{be01}", "")
    return sum(char_width(ch) for ch in CONTROL.sub("", text))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("zh_data"))
    args = parser.parse_args()

    report = []
    for path in sorted(args.data.glob("*/*/*.json")):
        rel = str(path.relative_to(args.data))
        if rel in WHITELIST:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        limit = 100 if rel in NARROW else 120
        changed = 0
        for i, line in enumerate(data["lines"]):
            if not CJK.search(line):
                continue
            new = wrap(line, limit)
            if new != line:
                data["lines"][i] = new
                changed += 1
            for seg in re.split(r"\\n|\{be00\}|\{be01\}", new):
                w = display_width(seg)
                if w > limit:
                    report.append((rel, i, w, limit, seg[:60]))
        if changed:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{rel}: 重排 {changed} 行")

    Path("build").mkdir(exist_ok=True)
    with open("build/report_layout.txt", "w", encoding="utf-8") as f:
        f.write(f"白名单外超宽行：{len(report)}\n\n")
        for row in report:
            f.write("\t".join(map(str, row)) + "\n")
    print(f"白名单外超宽行：{len(report)}（报告 build/report_layout.txt）")


if __name__ == "__main__":
    main()
