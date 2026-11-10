"""在不改变 ROM 大小的前提下替换 NitroFS 文件（只改 FAT 指针）。

    python tools/patch_rom.py --rom patched.nds --out zh.nds \
        --file a/0/0/2=work/narc/system.narc \
        --file a/0/0/3=work/narc/script.narc \
        --file a/0/2/3=work/narc/fonts.narc

新文件比原文件小时原地覆盖；更大时写到 ROM 有效数据末尾，并更新 FAT。
ARM9/overlay、反盗版补丁和 512 MB 大小都保持不变，兼容模拟器和实机。
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

import ndspy.rom


def patch(rom_path: Path, out_path: Path, files: dict[str, bytes]) -> None:
    data = bytearray(rom_path.read_bytes())
    rom = ndspy.rom.NintendoDSRom.fromFile(str(rom_path))
    fat_offset, fat_size = struct.unpack_from("<II", data, 0x48)

    # DS 的 FAT 项是 start / end 偏移，不是 start / size
    used_end = 0
    for i in range(fat_size // 8):
        start, end = struct.unpack_from("<II", data, fat_offset + 8 * i)
        if end > start:
            used_end = max(used_end, end)
    used_end = (used_end + 3) & ~3

    for name, blob in files.items():
        file_id = rom.filenames.idOf(name)
        start, old_end = struct.unpack_from("<II", data, fat_offset + 8 * file_id)
        size = old_end - start
        if len(blob) <= size:
            # 保留 FAT 里的原 end：HoennB2 给部分文件预留了空间，
            # 缩小范围可能影响后续读取。
            data[start:start + len(blob)] = blob
            print(f"{name}: 原地 {start:#x}（{len(blob)} / {size} 字节）")
        else:
            if used_end + len(blob) > len(data):
                raise SystemExit(f"{name}: ROM 空间不足（需要到 {used_end + len(blob):#x}）")
            data[used_end:used_end + len(blob)] = blob
            struct.pack_into("<II", data, fat_offset + 8 * file_id, used_end, used_end + len(blob))
            print(f"{name}: 追加 {used_end:#x}（{len(blob)} 字节）")
            used_end = (used_end + len(blob) + 3) & ~3

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    print(f"写入 {out_path}（{len(data)} 字节）")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--file", action="append", default=[], metavar="PATH=FILE")
    args = parser.parse_args()

    files: dict[str, bytes] = {}
    for item in args.file:
        name, _, path = item.partition("=")
        if not path:
            raise SystemExit(f"--file 需要 PATH=FILE：{item}")
        files[name] = Path(path).read_bytes()
    patch(args.rom, args.out, files)


if __name__ == "__main__":
    main()
