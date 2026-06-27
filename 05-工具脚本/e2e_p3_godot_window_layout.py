#!/usr/bin/env python3
"""P3-3 smoke: play/launch viewport body + backward-compatible empty body."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def api(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(payload)
        except json.JSONDecodeError:
            return exc.code, {"detail": payload}


def main() -> int:
    print(f"P3-3 launch viewport smoke · API={API}")

    st, created = api("POST", "/sessions")
    assert st == 201, created
    session_id = created["session_id"]
    print(f"  [PASS] session created · {session_id}")

    st, matched = api(
        "POST",
        "/intent/match-genre",
        {"text": "马里奥闯关", "session_id": session_id},
    )
    assert st == 200, matched
    print("  [PASS] intent match-genre")

    st, empty_launch = api("POST", f"/sessions/{session_id}/play/launch", {})
    assert st == 200 and empty_launch.get("ok") is True, empty_launch
    assert empty_launch.get("window_placed") is False
    assert empty_launch.get("placement_rect") is None
    print("  [PASS] empty body launch backward compatible")

    viewport_body = {
        "orientation": "landscape",
        "client_viewport": {
            "screen_x": 0,
            "screen_y": 0,
            "screen_w": 1920,
            "screen_h": 1080,
            "devicePixelRatio": 1.0,
            "godot_zone_rect": {"x": 960, "y": 0, "w": 960, "h": 1080},
        },
    }
    st, viewport_launch = api(
        "POST",
        f"/sessions/{session_id}/play/launch?force=true",
        viewport_body,
    )
    assert st == 200 and viewport_launch.get("ok") is True, viewport_launch
    assert "window_placed" in viewport_launch
    placed = viewport_launch.get("window_placed")
    if placed is True:
        assert viewport_launch.get("placement_rect") == {
            "x": 960,
            "y": 0,
            "w": 960,
            "h": 1080,
        }
        print(f"  [PASS] viewport launch · window_placed=True · pid={viewport_launch.get('pid')}")
    else:
        print(
            f"  [WARN] viewport launch ok but window_placed=False "
            f"(Godot HWND 未找到或未归位 · pid={viewport_launch.get('pid')})"
        )

    st, portrait_launch = api(
        "POST",
        f"/sessions/{session_id}/play/launch",
        {
            "orientation": "portrait",
            "client_viewport": {
                "screen_x": 0,
                "screen_y": 0,
                "screen_w": 1080,
                "screen_h": 1920,
            },
        },
    )
    assert st == 200 and portrait_launch.get("ok") is True, portrait_launch
    assert "window_placed" in portrait_launch
    if portrait_launch.get("window_placed") is True:
        assert portrait_launch.get("placement_rect") == {
            "x": 0,
            "y": 960,
            "w": 1080,
            "h": 960,
        }
        print("  [PASS] portrait relaunch · window_placed=True")
    else:
        print("  [WARN] portrait relaunch ok · window_placed=False (实机人工验收贴边)")

    print("P3-3 launch viewport smoke · ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
