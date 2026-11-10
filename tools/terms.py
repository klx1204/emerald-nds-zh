"""用现成中文名称/说明替换 B2 文本里的名称表。

数据来源：pokemon-dataset-zh（物种、招式、特性、道具）。
只做“整行就是名称”的替换，不会误伤剧情台词；未命中的保留英文。

    python tools/terms.py --dataset /path/to/pokemon-dataset-zh --data zh_data
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CJK = re.compile(r"[\u4e00-\u9fff]")


def norm(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"^(a|an)\s+", "", name)
    return re.sub(r"[^a-z0-9]", "", name)


def singular(name: str) -> str:
    if name.endswith("ies"):
        return name[:-3] + "y"
    if name.endswith("ses"):
        return name[:-2]
    if name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name


def load_dataset(dataset: Path) -> dict[str, dict[str, str]]:
    tables: dict[str, dict[str, str]] = {"species": {}, "moves": {}, "abilities": {}, "items": {}}

    for path in (dataset / "data/pokemon").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("name_en"):
            tables["species"][norm(data["name_en"])] = data["name_zh"]

    for key, filename in (("moves", "move_list.json"), ("abilities", "ability_list.json")):
        data = json.loads((dataset / "data" / filename).read_text(encoding="utf-8"))
        for entry in data:
            if entry.get("name_en"):
                tables[key][norm(entry["name_en"])] = entry["name_zh"]

    items_data = json.loads((dataset / "data/item_list.json").read_text(encoding="utf-8"))

    def walk(node) -> None:
        if isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, dict):
            if node.get("type") == "item" and node.get("name_en"):
                tables["items"][norm(node["name_en"])] = node
            for value in node.values():
                walk(value)

    walk(items_data)
    return tables


def replace_lines(lines: list[str], table: dict, *, strip_prefix: bool = False) -> int:
    hit = 0
    for i, line in enumerate(lines):
        if CJK.search(line):
            continue
        key = norm(line)
        target = table.get(key) or table.get(singular(key))
        if target is None and strip_prefix:
            match = re.match(r"^(.*?)([A-Za-z][A-Za-z' .-]*)$", line)
            if match:
                key = norm(match.group(2))
                target = table.get(key) or table.get(singular(key))
                if target is not None:
                    lines[i] = match.group(1) + target["name_zh"]
                    hit += 1
                    continue
        if target is not None:
            lines[i] = target["name_zh"] if isinstance(target, dict) else target
            hit += 1
    return hit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("zh_data"))
    args = parser.parse_args()

    tables = load_dataset(args.dataset)
    for key, table in tables.items():
        print(f"{key}: {len(table)} 条")

    report = []
    files = sorted(args.data.glob("*/*/*.json"))
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        lines = data["lines"]
        best = (0, None)
        for key, table in tables.items():
            probe = list(lines)
            hit = replace_lines(probe, table, strip_prefix=(key == "items"))
            if hit > best[0]:
                best = (hit, key, probe)
        if best[0] >= 3 and best[1] is not None:
            hit, key, replaced = best
            data["lines"] = replaced
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            report.append((str(path.relative_to(args.data)), key, hit, len(lines)))
            print(f"{path.relative_to(args.data)}: {key} {hit}/{len(lines)}")

    Path("build").mkdir(exist_ok=True)
    with open("build/report_names.txt", "w", encoding="utf-8") as f:
        f.write("文件\t类别\t命中\t总行数\n")
        for row in report:
            f.write("\t".join(map(str, row)) + "\n")
        f.write("\n合计\n")
        for key in tables:
            total = sum(r[2] for r in report if r[1] == key)
            f.write(f"{key}: {total}\n")
    print("报告 -> build/report_names.txt")


if __name__ == "__main__":
    main()
