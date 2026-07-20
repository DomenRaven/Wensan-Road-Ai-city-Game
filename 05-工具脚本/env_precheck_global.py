#!/usr/bin/env python3
"""全局环境测试 · 前置 E0–E3 + G1 游客入口。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402

API = "http://127.0.0.1:8000"
KIOSK = "http://127.0.0.1:8080/kiosk/edu/"


def main() -> int:
    get_settings.cache_clear()
    s = get_settings()
    assert s.llm_api_key and len(s.llm_api_key) > 8, "E0 LLM_API_KEY 未配置"
    assert Path(s.godot_path).is_file(), f"E1 Godot 不存在: {s.godot_path}"
    assert s.play_launch_mode == "server", s.play_launch_mode
    assert int(s.max_sessions) >= 70, s.max_sessions
    print("PASS E0 Key")
    print("PASS E1 Godot", s.godot_path)
    print("PASS E2 mode=server max_sessions=", s.max_sessions)

    with httpx.Client(timeout=15.0, trust_env=False) as c:
        h = c.get(f"{API}/health")
        h.raise_for_status()
        body = h.json()
        assert body.get("status") == "ok"
        assert body.get("play_launch_mode") == "server"
        assert int(body.get("max_sessions") or 0) >= 70
        k = c.get(KIOSK)
        k.raise_for_status()
    print("PASS E3 API+Kiosk health")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(KIOSK, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector('[data-act="guest"]', timeout=15000)
        page.click('[data-act="guest"]')
        page.wait_for_timeout(1000)
        browser.close()
    print("PASS G1 guest entry click")
    print("PRECHECK_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
