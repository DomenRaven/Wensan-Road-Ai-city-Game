from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from app.routers.play import ClientViewport, ClientViewportRect, resolve_placement_rect
from app.services.godot_window_layout import get_monitor_bottom_half_rect, place_by_pid


@patch("app.routers.play.get_monitor_fullscreen_rect")
def test_resolve_placement_rect_prefers_win32_monitor(mock_win32: MagicMock) -> None:
    # S-A1：优先 Win32 真实显示器整块边界（多屏 + 横竖屏自适应）
    mock_win32.return_value = {"x": 1920, "y": 0, "w": 1920, "h": 1080}
    rect = resolve_placement_rect(
        "landscape",
        ClientViewport(
            screen_x=2000,
            screen_y=50,
            screen_w=1920,
            screen_h=1080,
            monitor_x=1920,
            monitor_y=0,
            kiosk_rect=ClientViewportRect(x=1960, y=120, w=900, h=800),
        ),
    )
    assert rect == {"x": 1920, "y": 0, "w": 1920, "h": 1080}
    mock_win32.assert_called_once_with(1960 + 450, 120 + 400)


@patch("app.routers.play.get_monitor_fullscreen_rect", return_value=None)
def test_resolve_placement_rect_landscape_fallback_full_display(_mock_win32: MagicMock) -> None:
    rect = resolve_placement_rect(
        "landscape",
        ClientViewport(
            screen_x=100,
            screen_y=50,
            screen_w=1920,
            screen_h=1080,
            monitor_x=0,
            monitor_y=0,
        ),
    )
    # 禁止半屏小窗：铺满整块显示器
    assert rect == {"x": 0, "y": 0, "w": 1920, "h": 1080}


@patch("app.routers.play.get_monitor_fullscreen_rect", return_value=None)
def test_resolve_placement_rect_portrait_full_display(_mock_win32: MagicMock) -> None:
    # 展厅竖屏：按显示器实际宽高铺满，不写死横屏
    rect = resolve_placement_rect(
        "portrait",
        ClientViewport(
            screen_x=200,
            screen_y=100,
            screen_w=1080,
            screen_h=1920,
            monitor_x=0,
            monitor_y=0,
        ),
    )
    assert rect == {"x": 0, "y": 0, "w": 1080, "h": 1920}


@patch("app.routers.play.get_monitor_fullscreen_rect", return_value=None)
def test_resolve_placement_rect_none_without_viewport(_mock_win32: MagicMock) -> None:
    assert resolve_placement_rect("landscape", None) is None
    assert resolve_placement_rect(None, ClientViewport()) is None


@pytest.mark.skipif(sys.platform != "win32", reason="win32 only")
def test_get_monitor_bottom_half_rect_live() -> None:
    rect = get_monitor_bottom_half_rect(400, 300)
    assert rect is not None
    assert rect["w"] > 0
    assert rect["h"] > 0
    assert rect["y"] >= rect["h"]


@pytest.mark.skipif(sys.platform == "win32", reason="non-win32 path returns False")
def test_place_by_pid_non_win32() -> None:
    assert place_by_pid(1234, {"x": 0, "y": 0, "w": 800, "h": 600}, timeout_s=0.01) is False


def test_place_by_pid_invalid_pid() -> None:
    assert place_by_pid(0, {"x": 0, "y": 0, "w": 800, "h": 600}, timeout_s=0.01) is False


@patch("app.services.godot_window_layout.sys.platform", "win32")
@patch("app.services.godot_window_layout.time.sleep")
@patch("app.services.godot_window_layout._set_window_rect", return_value=True)
@patch("app.services.godot_window_layout._find_game_window_for_pid")
def test_place_by_pid_retries_until_window_found(
    mock_find: MagicMock,
    _mock_set: MagicMock,
    _mock_sleep: MagicMock,
) -> None:
    mock_find.side_effect = [None, None, 42]
    assert place_by_pid(999, {"x": 960, "y": 0, "w": 960, "h": 1080}, timeout_s=1.0) is True
    assert mock_find.call_count == 3


@patch("app.services.godot_window_layout.sys.platform", "win32")
@patch("app.services.godot_window_layout.time.sleep")
@patch("app.services.godot_window_layout._set_window_rect", return_value=True)
@patch("app.services.godot_window_layout._find_game_window_for_pid", return_value=42)
def test_place_by_pid_win32_success(
    _mock_find: MagicMock,
    mock_set: MagicMock,
    _mock_sleep: MagicMock,
) -> None:
    assert place_by_pid(999, {"x": 960, "y": 0, "w": 960, "h": 1080}, timeout_s=0.01) is True
    assert mock_set.call_args.kwargs.get("always_on_top") is True


@patch("app.services.godot_window_layout.sys.platform", "win32")
def test_set_window_rect_uses_hwnd_topmost() -> None:
    """Always on Top：SetWindowPos 使用 HWND_TOPMOST=-1，且不含 SWP_NOZORDER。"""
    import ctypes
    from unittest.mock import MagicMock

    from app.services.godot_window_layout import _set_window_rect

    fake_user32 = MagicMock()
    fake_user32.SetWindowPos.return_value = 1
    with patch("ctypes.windll") as windll:
        windll.user32 = fake_user32
        ok = _set_window_rect(42, {"x": 0, "y": 0, "w": 800, "h": 600}, always_on_top=True)
    assert ok is True
    args = fake_user32.SetWindowPos.call_args[0]
    assert args[0] == 42
    assert args[1] == -1  # HWND_TOPMOST
    flags = args[6]
    assert (flags & 0x0004) == 0  # no SWP_NOZORDER


@patch("app.services.godot_window_layout.sys.platform", "win32")
@patch("app.services.godot_window_layout.time.sleep")
@patch("app.services.godot_window_layout._find_game_window_for_pid", return_value=None)
def test_place_by_pid_win32_no_window(
    _mock_find: MagicMock,
    _mock_sleep: MagicMock,
) -> None:
    assert place_by_pid(999, {"x": 960, "y": 0, "w": 960, "h": 1080}, timeout_s=0.01) is False
