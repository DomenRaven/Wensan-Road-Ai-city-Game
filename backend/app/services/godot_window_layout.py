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


def get_monitor_fullscreen_rect(anchor_x: int, anchor_y: int) -> WindowRect | None:
    """Return the FULL bounds of the monitor nearest *anchor* (S-A1 · 铺满整块显示器).

    读真实显示器几何（含横/竖屏自适应），不写死分辨率。Win32 only。
    """
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
        return {
            "x": int(mon.left),
            "y": int(mon.top),
            "w": mon_w,
            "h": mon_h,
        }
    except Exception:
        return None


def place_by_pid(
    pid: int,
    rect: WindowRect,
    *,
    timeout_s: float = 5.0,
    interval_s: float = 0.25,
    borderless: bool = False,
    always_on_top: bool = True,
) -> bool:
    """Move a Godot top-level window to *rect* (screen coordinates). Win32 only.

    *borderless* True 时先去掉标题栏/边框，再铺满 *rect*（S-A1 全屏体验）。
    *always_on_top* True（默认）→ HWND_TOPMOST，始终在所有应用最上层。
    """
    if pid <= 0:
        return False
    if sys.platform != "win32":
        return False
    deadline: float = time.monotonic() + max(timeout_s, interval_s)
    while True:
        try:
            hwnd: int | None = _find_game_window_for_pid(pid)
            if hwnd is not None:
                if borderless:
                    _make_window_borderless(hwnd)
                if _set_window_rect(hwnd, rect, always_on_top=always_on_top):
                    return True
        except Exception:
            pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval_s)


def _make_window_borderless(hwnd: int) -> None:
    """去掉标题栏与可调边框，让 Godot 窗口可真正铺满显示器。失败静默。"""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        GWL_STYLE: int = -16
        WS_CAPTION: int = 0x00C00000
        WS_THICKFRAME: int = 0x00040000
        WS_MINIMIZEBOX: int = 0x00020000
        WS_MAXIMIZEBOX: int = 0x00010000
        WS_SYSMENU: int = 0x00080000
        get_style = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
        set_style = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
        style: int = int(get_style(hwnd, GWL_STYLE))
        new_style: int = style & ~(
            WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU
        )
        if new_style != style:
            set_style(hwnd, GWL_STYLE, new_style)
            SWP_NOMOVE: int = 0x0002
            SWP_NOSIZE: int = 0x0001
            SWP_NOZORDER: int = 0x0004
            SWP_FRAMECHANGED: int = 0x0020
            user32.SetWindowPos(
                hwnd,
                0,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
            )
    except Exception:
        pass


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


def _set_window_rect(
    hwnd: int,
    rect: WindowRect,
    *,
    always_on_top: bool = True,
) -> bool:
    """铺满 rect；默认 HWND_TOPMOST（去掉会阻碍置顶的 SWP_NOZORDER）。"""
    import ctypes

    user32 = ctypes.windll.user32
    SWP_SHOWWINDOW: int = 0x0040
    SWP_FRAMECHANGED: int = 0x0020
    HWND_TOPMOST: int = -1
    HWND_NOTOPMOST: int = -2
    flags: int = SWP_SHOWWINDOW | SWP_FRAMECHANGED
    insert_after: int = HWND_TOPMOST if always_on_top else HWND_NOTOPMOST
    try:
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    except Exception:
        pass
    ok: bool = bool(
        user32.SetWindowPos(
            hwnd,
            insert_after,
            int(rect["x"]),
            int(rect["y"]),
            int(rect["w"]),
            int(rect["h"]),
            flags,
        )
    )
    return ok
