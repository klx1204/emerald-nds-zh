"""宝可梦 黑2/白2 文本库（a/0/0/2、a/0/0/3）的读取与打包。

格式与 pokebw2 的 tools/text/text_data.py 一致：

- 文件头 16 字节：u16 段数、u16 条数、u32 段大小、u32 未知、u32 段偏移（固定 16）。
- 段：u32 大小、每条 8 字节的条目表（u32 偏移、u16 字符数、u16 属性）、字符数据。
- 每条消息是 UTF-16 码位，用 key = 0x7C89 + 0x2983 * 下标 起手、每字符循环左移 3 位加密。
- 0xFFFF 结束，0xFFFE 换行，0xF000 起是控制码；0xF100 开头表示 9-bit 压缩文本。

本模块只依赖标准库和 ndspy。
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

LINE_END = 0xFFFF
NEWLINE = 0xFFFE
CONTROL = 0xF000
COMPRESSED = 0xF100

BASE_KEY = 0x7C89
KEY_STEP = 0x2983


def decrypt(chars: list[int]) -> list[int]:
    """文本按最后一位（0xFFFF）异或起手，反向每字符循环右移 3 位。"""
    chars = list(chars)
    if not chars:
        return chars
    key = chars[-1] ^ LINE_END
    for i in reversed(range(len(chars))):
        chars[i] ^= key
        key = ((key >> 3) | (key << 13)) & 0xFFFF
    return chars


def encrypt(chars: list[int], index: int) -> list[int]:
    key = (BASE_KEY + KEY_STEP * index) & 0xFFFF
    out = []
    for c in chars:
        out.append(c ^ key)
        key = ((key << 3) | (key >> 13)) & 0xFFFF
    return out


def decompress(chars: list[int]) -> list[int]:
    """解压 9-bit 文本；美版游戏没有压缩文本，但留作兼容。"""
    if not chars or chars[0] != COMPRESSED:
        return chars
    bits = count = 0
    out: list[int] = []
    for word in chars[1:]:
        bits |= word << count
        count += 16
        while count >= 9:
            c = bits & 0x1FF
            if c == 0x1FF:
                return out + [LINE_END]
            out.append(c)
            bits >>= 9
            count -= 9
    return out + [LINE_END]


def compress(chars: list[int]) -> list[int]:
    """把消息压成 9-bit 文本；中文码位超过 0x1FF，不能压缩。"""
    bits = count = 0
    words = [COMPRESSED]
    for c in chars + [0x1FF]:
        if c > 0x1FF:
            raise ValueError(f"字符 {c:#x} 超出 9-bit 压缩范围")
        bits |= c << count
        count += 9
        while count >= 16:
            words.append(bits & 0xFFFF)
            bits >>= 16
            count -= 16
    if count:
        if count <= 8:
            words.append((bits | (0xFFFF << count)) & 0xFFFF)
        else:
            words += [bits & 0xFFFF, LINE_END]
    return words


def _printable(c: int) -> bool:
    if c < 0x20 or 0xD800 <= c < 0xE000:
        return False
    if 0xE000 <= c < 0xF900:
        return False
    if c >= CONTROL:
        return False
    return chr(c).isprintable()


def format_message(chars: list[int], compressed: bool = False) -> str:
    """把一条消息的码位写成可编辑文本；控制码写成 {kind:args}。"""
    out = ["\\c"] if compressed else []
    i = 0
    while i < len(chars):
        c = chars[i]
        if c == CONTROL and i + 2 < len(chars) and i + 3 + chars[i + 2] <= len(chars):
            kind, count = chars[i + 1], chars[i + 2]
            args = chars[i + 3:i + 3 + count]
            out.append(f"{{{kind:04x}" + (":" + ",".join(map(str, args)) if count else "") + "}")
            i += 3 + count
            continue
        if c == NEWLINE:
            out.append("\\n")
        elif _printable(c):
            ch = chr(c)
            out.append({"\\": "\\\\", "{": "\\{", "}": "\\}"}.get(ch, ch))
        else:
            out.append(f"\\x{{{c:04x}}}")
        i += 1
    return "".join(out)


def parse_message(text: str) -> tuple[list[int], bool]:
    """parse_message 的逆操作。"""
    compressed = text.startswith("\\c")
    if compressed:
        text = text[2:]
    chars: list[int] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            nxt = text[i + 1]
            if nxt == "n":
                chars.append(NEWLINE)
                i += 2
            elif nxt == "x":
                end = text.index("}", i)
                chars.append(int(text[i + 3:end], 16))
                i = end + 1
            elif nxt in "\\{}":
                chars.append(ord(nxt))
                i += 2
            else:
                raise ValueError(f"未知转义 \\{nxt}: {text!r}")
        elif ch == "{":
            end = text.index("}", i)
            kind, _, args = text[i + 1:end].partition(":")
            values = [int(a) for a in args.split(",")] if args else []
            chars += [CONTROL, int(kind, 16), len(values), *values]
            i = end + 1
        else:
            chars.append(ord(ch))
            i += 1
    return chars, compressed


@dataclass
class MessageFile:
    """一个文本文件：消息列表（可编辑格式）+ 末尾填充字节。"""

    messages: list[str]
    pad: int = 0


def parse_file(data: bytes) -> MessageFile:
    # 日版/汉化版可能是双段文件（日文 + 英文），这里只读第一段；
    # 我们构建的是美版 patched ROM，写回时始终用单段。
    _num_sections, num_lines = struct.unpack_from("<HH", data, 0)
    section = struct.unpack_from("<I", data, 12)[0]
    messages: list[str] = []
    for i in range(num_lines):
        offset, length, attribute = struct.unpack_from("<IHH", data, section + 4 + 8 * i)
        if attribute:
            raise ValueError(f"消息 {i} 带属性 {attribute}")
        raw = struct.unpack_from(f"<{length}H", data, section + offset)
        chars = decrypt(list(raw))
        compressed = bool(chars) and chars[0] == COMPRESSED
        if compressed:
            chars = decompress(chars)
        if not chars or chars[-1] != LINE_END:
            raise ValueError(f"消息 {i} 没有结束符")
        messages.append(format_message(chars[:-1], compressed))
    used = 4 + 8 * num_lines + 2 * sum(
        struct.unpack_from("<H", data, section + 6 + 8 * i)[0] for i in range(num_lines)
    )
    pad = data[section + used] if section + used < len(data) else 0
    return MessageFile(messages, pad)


def build_file(messages: list[str], pad: int = 0) -> bytes:
    """把可编辑文本行打包回一个文本文件。"""
    encoded = []
    for i, message in enumerate(messages):
        chars, compressed = parse_message(message)
        chars = compress(chars) if compressed else chars + [LINE_END]
        encoded.append(encrypt(chars, i))
    table_size = 4 + 8 * len(messages)
    offset = table_size
    table = bytearray()
    body = bytearray()
    for chars in encoded:
        table += struct.pack("<IHH", offset, len(chars), 0)
        body += struct.pack(f"<{len(chars)}H", *chars)
        offset += 2 * len(chars)
    size = (table_size + len(body) + 3) & ~3
    section = struct.pack("<I", size) + bytes(table) + bytes(body)
    section += bytes([pad & 0xFF]) * (size - len(section))
    header = struct.pack("<HHIII", 1, len(messages), size, 0, 16)
    return header + section
