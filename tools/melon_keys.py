"""测试用：激活 melonDS 并向它发送按键，避免按键落到终端。

    python tools/melon_keys.py a 0.2 right 0.4 ...
"""

from __future__ import annotations

import sys
import time

import Quartz
from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication

from keys import KEYS

BUNDLE = "net.kuribo64.melonDS"


def activate() -> None:
    apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(BUNDLE)
    if not apps:
        raise SystemExit("melonDS 没有在运行")
    apps[0].activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
    time.sleep(0.4)


def press(name: str, seconds: float = 0.15) -> None:
    code = KEYS[name]
    down = Quartz.CGEventCreateKeyboardEvent(None, code, True)
    up = Quartz.CGEventCreateKeyboardEvent(None, code, False)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    time.sleep(seconds)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
    time.sleep(0.12)


def main() -> None:
    activate()
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
