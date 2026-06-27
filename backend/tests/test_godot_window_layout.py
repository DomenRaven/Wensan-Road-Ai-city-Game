from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from app.routers.play import ClientViewport, ClientViewportRect, resolve_placement_rect
from app.services.godot_window_layout import get_monitor_bottom_half_rect, place_by_pid


def test_resolve_placement_rect_from_godot_zone() -> None:
    rect = resolve_placement_rect(
        "landscape",
        ClientViewport(
            screen_x=100,
            screen_y=50,
            screen_w=1920,
            screen_h=1080,
            godot_zone_rect=ClientViewportRect(x=1060, y=114, w=860, h=900),
        ),
    )
    assert rect == {"x": 1060, "y": 114, "w": 860, "h": 900}


def test_resolve_placement_rect_ignores_device_pixel_ratio() -> None:
    rect = resolve_placement_rect(
        "landscape",
        ClientViewport(
            devicePixelRatio=1.5,
            godot_zone_rect=ClientViewportRect(x=960, y=80, w=960, h=1000),
        ),
    )
    assert rect == {"x": 960, "y": 80, "w": 960, "h": 1000}


def test_resolve_placement_rect_landscape_fallback() -> None:
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
    assert rect == {"x": 960, "y": 0, "w": 960, "h": 1080}


@patch("app.routers.play.get_monitor_bottom_half_rect")
def test_resolve_placement_rect_portrait_uses_win32_monitor(mock_win32: MagicMock) -> None:
    mock_win32.return_value = {"x": 0, "y": 533, "w": 1707, "h": 533}
    rect = resolve_placement_rect(
        "portrait",
        ClientViewport(
            screen_x=200,
            screen_y=100,
            screen_w=1920,
            screen_h=1080,
            kiosk_rect=ClientViewportRect(x=200, y=120, w=900, h=800),
            godot_zone_rect=ClientViewportRect(x=200, y=700, w=900, h=400),
        ),
    )
    assert rect == {"x": 0, "y": 533, "w": 1707, "h": 533}
    mock_win32.assert_called_once_with(200 + 450, 120 + 160)


@patch("app.routers.play.get_monitor_bottom_half_rect", return_value=None)
def test_resolve_placement_rect_portrait_fallback_when_win32_fails(_mock_win32: MagicMock) -> None:
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
    assert rect == {"x": 0, "y": 960, "w": 1080, "h": 960}


def test_resolve_placement_rect_none_without_viewport() -> None:
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
    _mock_set: MagicMock,
    _mock_sleep: MagicMock,
) -> None:
    assert place_by_pid(999, {"x": 960, "y": 0, "w": 960, "h": 1080}, timeout_s=0.01) is True


@patch("app.services.godot_window_layout.sys.platform", "win32")
@patch("app.services.godot_window_layout.time.sleep")
@patch("app.services.godot_window_layout._find_game_window_for_pid", return_value=None)
def test_place_by_pid_win32_no_window(
    _mock_find: MagicMock,
    _mock_sleep: MagicMock,
) -> None:
    assert place_by_pid(999, {"x": 960, "y": 0, "w": 960, "h": 1080}, timeout_s=0.01) is False
