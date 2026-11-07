from __future__ import annotations

import ctypes
from ctypes import wintypes


WINDOW_TITLE = "KPS Overlay"
WM_CLOSE = 0x0010


def close_overlays() -> int:
    user32 = ctypes.windll.user32
    matches: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def visit_window(hwnd: int, _lparam: int) -> bool:
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        if buffer.value == WINDOW_TITLE:
            matches.append(hwnd)
        return True

    user32.EnumWindows(visit_window, 0)
    for hwnd in matches:
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    return len(matches)


def main() -> int:
    closed = close_overlays()
    if closed == 0:
        ctypes.windll.user32.MessageBoxW(None, "没有找到正在运行的 KPS Overlay。", "退出 KPS Overlay", 0x40)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
