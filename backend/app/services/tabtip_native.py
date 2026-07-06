"""Windows TabTip · in-process COM toggle · avoids PowerShell spawn latency."""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from ctypes import POINTER, Structure, byref, c_int, c_uint8, c_uint16, c_uint32, c_void_p, windll
from pathlib import Path
from typing import Any, Callable, Literal, TypeVar

if sys.platform != "win32":
    raise ImportError("tabtip_native only supports Windows")

user32 = windll.user32
ole32 = windll.ole32

CLSCTX_LOCAL_SERVER = 0x4
COINIT_APARTMENTTHREADED = 0x2

CLSID_UIHostNoLaunch = (
    0x4CE576FA,
    0x83DC,
    0x4F88,
    (0x95, 0x1C, 0x9D, 0x07, 0x82, 0xB4, 0xE3, 0x76),
)
IID_ITipInvocation = (
    0x37C994E7,
    0x432B,
    0x4834,
    (0xA2, 0xF7, 0xDC, 0xE1, 0xF1, 0x3B, 0x83, 0x4B),
)

KLF_ACTIVATE = 0x1
WM_INPUTLANGCHANGEREQUEST = 0x0050
INPUTLANGCHANGE_FORWARD = 2

ToggleFn = ctypes.WINFUNCTYPE(None, c_void_p, c_void_p)
ReleaseFn = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)

_com_lock = threading.Lock()
_tabtip_warmed = False
_ime_ready = False
_tabtip_open = False
_thread_local = threading.local()
_com_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tabtip-com")
T = TypeVar("T")


def _run_on_com_thread(fn: Callable[[], T]) -> T:
    return _com_worker.submit(fn).result(timeout=8)


class GUID(Structure):
    _fields_ = [
        ("Data1", c_uint32),
        ("Data2", c_uint16),
        ("Data3", c_uint16),
        ("Data4", c_uint8 * 8),
    ]


class RECT(Structure):
    _fields_ = [
        ("left", c_int),
        ("top", c_int),
        ("right", c_int),
        ("bottom", c_int),
    ]


def _make_guid(parts: tuple[int, int, int, tuple[int, ...]]) -> GUID:
    data1, data2, data3, tail = parts
    return GUID(data1, data2, data3, (c_uint8 * 8)(*tail))


def _ensure_com() -> None:
    if getattr(_thread_local, "ready", False):
        return
    ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
    _thread_local.ready = True


def _tabtip_exe() -> Path:
    common = os.environ.get("CommonProgramFiles", r"C:\Program Files\Common Files")
    return Path(common) / "Microsoft Shared" / "Ink" / "TabTip.exe"


def is_tabtip_visible() -> bool:
    hwnd = user32.FindWindowW("IPTip_Main_Window", None)
    if not hwnd:
        return False
    if not user32.IsWindowVisible(hwnd):
        return False
    rect = RECT()
    if not user32.GetWindowRect(hwnd, byref(rect)):
        return False
    return (rect.bottom - rect.top) > 20 and (rect.right - rect.left) > 20


def _tabtip_process_running() -> bool:
    try:
        completed = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq TabTip.exe", "/NH"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "TabTip.exe" in (completed.stdout or "")


def ensure_tabtip_process() -> bool:
    global _tabtip_warmed
    exe = _tabtip_exe()
    if not exe.is_file():
        return False
    if _tabtip_warmed:
        return True
    if not _tabtip_process_running():
        subprocess.Popen([str(exe)], close_fds=True)
        time.sleep(0.08)
    _tabtip_warmed = True
    return True


def ensure_chinese_ime() -> bool:
    global _ime_ready
    if _ime_ready:
        return True
    ok = switch_foreground_to_chinese()
    _ime_ready = ok
    return ok


def switch_foreground_to_chinese() -> bool:
    hwnd = user32.GetForegroundWindow()
    hkl = user32.LoadKeyboardLayoutW("00000804", KLF_ACTIVATE)
    if not hkl:
        return False
    user32.ActivateKeyboardLayout(hkl, 0)
    return bool(
        user32.PostMessageW(
            hwnd,
            WM_INPUTLANGCHANGEREQUEST,
            INPUTLANGCHANGE_FORWARD,
            hkl,
        )
    )


def _toggle_tabtip() -> tuple[bool, int]:
    _ensure_com()
    clsid = _make_guid(CLSID_UIHostNoLaunch)
    iid = _make_guid(IID_ITipInvocation)
    punk = c_void_p()
    hr = ole32.CoCreateInstance(byref(clsid), None, CLSCTX_LOCAL_SERVER, byref(iid), byref(punk))
    if hr != 0 or not punk.value:
        return False, int(hr)
    vtbl_ptr = ctypes.cast(punk, POINTER(c_void_p)).contents.value
    funcs = ctypes.cast(vtbl_ptr, POINTER(c_void_p))
    toggle = ToggleFn(funcs[3])
    release = ReleaseFn(funcs[2])
    toggle(punk, user32.GetDesktopWindow())
    release(punk)
    return True, 0


def show_if_hidden() -> dict[str, object]:
    global _tabtip_open
    with _com_lock:
        ensure_tabtip_process()
        ensure_chinese_ime()
        if is_tabtip_visible():
            _tabtip_open = True
            return {"ok": True, "action": "show", "already_visible": True}
        if _tabtip_open:
            return {"ok": True, "action": "show", "already_visible": True}
        ok, hr = _toggle_tabtip()
        if ok:
            _tabtip_open = True
        return {
            "ok": ok,
            "action": "show",
            "already_visible": False,
            "toggled": ok,
            "hresult": hr,
        }


def hide_if_visible() -> dict[str, object]:
    global _tabtip_open
    with _com_lock:
        visible = is_tabtip_visible()
        was_open = _tabtip_open or visible
        if not was_open:
            return {"ok": True, "action": "hide", "already_hidden": True, "toggled": False}
        ok, hr = _toggle_tabtip()
        if ok or not is_tabtip_visible():
            _tabtip_open = False
        return {
            "ok": ok,
            "action": "hide",
            "already_hidden": False,
            "toggled": ok,
            "was_tracked_open": was_open,
            "hresult": hr,
        }


KeyboardState = Literal["show", "hide"]


def apply_keyboard_state(state: KeyboardState) -> dict[str, object]:
    if state == "show":
        return _run_on_com_thread(show_if_hidden)
    return _run_on_com_thread(hide_if_visible)


def warm_tabtip() -> dict[str, object]:
    return _run_on_com_thread(_warm_tabtip_impl)


def _warm_tabtip_impl() -> dict[str, object]:
    with _com_lock:
        ok = ensure_tabtip_process()
        ensure_chinese_ime()
        return {"ok": ok, "action": "warm"}
