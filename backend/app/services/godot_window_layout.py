from __future__ import annotations

import sys
import time
from typing import TypedDict


class WindowRect(TypedDict):
    x: int
    y: int
    w: int
    h: int


def get_monitor_bottom_half_rect(anchor_x: int, anchor_y: int) -> WindowRect | None:
    """Return bottom half of the monitor nearest *anchor* (Win32 virtual screen coords)."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        MONITOR_DEFAULTTONEAREST: int = 2
        pt = POINT(int(anchor_x), int(anchor_y))
        hmon = user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
        if not hmon:
            return None

        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            return None

        mon = info.rcMonitor
        mon_w: int = int(mon.right - mon.left)
        mon_h: int = int(mon.bottom - mon.top)
        if mon_w <= 0 or mon_h <= 0:
            return None
        half_h: int = mon_h // 2
        return {
            "x": int(mon.left),
            "y": int(mon.top + half_h),
            "w": mon_w,
            "h": half_h,
        }
    except Exception:
        return None


def place_by_pid(
    pid: int,
    rect: WindowRect,
    *,
    timeout_s: float = 5.0,
    interval_s: float = 0.25,
) -> bool:
    """Move a Godot top-level window to *rect* (screen coordinates). Win32 only."""
    if pid <= 0:
        return False
    if sys.platform != "win32":
        return False
    deadline: float = time.monotonic() + max(timeout_s, interval_s)
    while True:
        try:
            hwnd: int | None = _find_game_window_for_pid(pid)
            if hwnd is not None and _set_window_rect(hwnd, rect):
                return True
        except Exception:
            pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval_s)


def _collect_process_tree(root_pid: int) -> set[int]:
    import ctypes
    from ctypes import wintypes

    TH32CS_SNAPPROCESS: int = 0x00000002

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        return {root_pid}

    children: dict[int, list[int]] = {}
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return {root_pid}
        while True:
            pid: int = int(entry.th32ProcessID)
            parent: int = int(entry.th32ParentProcessID)
            children.setdefault(parent, []).append(pid)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snapshot)

    pids: set[int] = {root_pid}
    queue: list[int] = [root_pid]
    while queue:
        current: int = queue.pop(0)
        for child in children.get(current, []):
            if child not in pids:
                pids.add(child)
                queue.append(child)
    return pids


def _score_window(title: str, width: int, height: int) -> int:
    score: int = min(width * height // 1000, 500)
    upper: str = title.upper()
    if "(DEBUG)" in upper:
        score += 200
    if "GAMEFORGE" in upper:
        score += 150
    if "GODOT" in upper:
        score += 120
    if width < 200 or height < 200:
        score -= 300
    return score


def _find_game_window_for_pid(root_pid: int) -> int | None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    pids: set[int] = _collect_process_tree(root_pid)
    best_hwnd: int | None = None
    best_score: int = -1

    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd: int, _lparam: int) -> bool:
        nonlocal best_hwnd, best_score
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindow(hwnd, 4):  # GW_OWNER — skip owned/tool windows
            return True
        proc_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if int(proc_id.value) not in pids:
            return True
        length: int = int(user32.GetWindowTextLengthW(hwnd))
        if length <= 0:
            return True
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title: str = buff.value.strip()
        if not title:
            return True
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width: int = int(rect.right - rect.left)
        height: int = int(rect.bottom - rect.top)
        score: int = _score_window(title, width, height)
        if score > best_score:
            best_score = score
            best_hwnd = int(hwnd)
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return best_hwnd


def _set_window_rect(hwnd: int, rect: WindowRect) -> bool:
    import ctypes

    user32 = ctypes.windll.user32
    SWP_NOZORDER: int = 0x0004
    SWP_SHOWWINDOW: int = 0x0040
    flags: int = SWP_NOZORDER | SWP_SHOWWINDOW
    ok: bool = bool(
        user32.SetWindowPos(
            hwnd,
            0,
            int(rect["x"]),
            int(rect["y"]),
            int(rect["w"]),
            int(rect["h"]),
            flags,
        )
    )
    return ok
