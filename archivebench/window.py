"""Size only the dedicated console launched by the Windows shortcuts."""

import ctypes
from ctypes import wintypes


def centered_bounds(left, top, right, bottom):
    width, height = int((right - left) * 0.8), int((bottom - top) * 0.8)
    return left + (right - left - width) // 2, top + (bottom - top - height) // 2, width, height


def fit_console_window():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel.GetConsoleWindow.restype = wintypes.HWND
    user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user.MonitorFromWindow.restype = wintypes.HANDLE

    class MonitorInfo(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("monitor", wintypes.RECT),
            ("work", wintypes.RECT),
            ("flags", wintypes.DWORD),
        ]

    user.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    user.MoveWindow.argtypes = [
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.BOOL,
    ]
    window = kernel.GetConsoleWindow()
    if not window:
        return
    info = MonitorInfo()
    info.size = ctypes.sizeof(info)
    if user.GetMonitorInfoW(user.MonitorFromWindow(window, 2), ctypes.byref(info)):
        area = info.work
        user.MoveWindow(
            window, *centered_bounds(area.left, area.top, area.right, area.bottom), True
        )
