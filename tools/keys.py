"""测试用：给 melonDS 发送长按按键（需要 macOS 辅助功能权限）。

    python tools/keys.py right 0.5 a

参数是若干组 "按键 秒数"，最后可以给单个按键。键名见 KEYS。
"""

from __future__ import annotations

import sys
import time

import Quartz

KEYS = {
    "up": 126,
    "down": 125,
    "left": 123,
    "right": 124,
    "a": 7,  # X
    "b": 6,  # Z
    "d": 2,  # melonDS 的 A 键（本机配置）
    "start": 36,
    "select": 48,
    "l": 12,
    "r": 13,
}


def press(name: str, seconds: float = 0.15) -> None:
    code = KEYS[name]
    down = Quartz.CGEventCreateKeyboardEvent(None, code, True)
    up = Quartz.CGEventCreateKeyboardEvent(None, code, False)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    time.sleep(seconds)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
    time.sleep(0.1)


def main() -> None:
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        name = args[i]
        seconds = 0.15
        if i + 1 < len(args):
            try:
                seconds = float(args[i + 1])
                i += 1
            except ValueError:
                pass
        press(name, seconds)
        i += 1


if __name__ == "__main__":
    main()
