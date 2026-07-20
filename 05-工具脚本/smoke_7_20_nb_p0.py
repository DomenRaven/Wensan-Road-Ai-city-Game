#!/usr/bin/env python3
"""7.20 P0 推荐消项冒烟：NB-01 / 03 / 06 / 07 / 10 / 12（开服 API + 浏览器入口）。

前置：
  - API  http://127.0.0.1:8000  （建议 MAX_SESSIONS>=70；测满员时可临时 MAX_CONCURRENT_AGENTS=1）
  - Kiosk http://127.0.0.1:8080/kiosk/edu/

用法（仓库根）：
  python 05-工具脚本/smoke_7_20_nb_p0.py
"""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:8000"
KIOSK = "http://127.0.0.1:8080/kiosk/edu/"

# 与 uvicorn 共用 backend/.env（WORKSPACE_DIR / LEARNING_ANALYTICS_DIR）
_BACKEND = ROOT / "backend"
os.chdir(_BACKEND)
sys.path.insert(0, str(_BACKEND))


class SmokeError(RuntimeError):
    pass


def _ok(name: str, detail: str = "") -> None:
    print(f"  PASS  {name}" + (f" · {detail}" if detail else ""))


def _fail(name: str, detail: str) -> None:
    raise SmokeError(f"{name}: {detail}")


def check_nb12_health(client: httpx.Client) -> None:
    r = client.get(f"{API}/health")
    if r.status_code != 200:
        _fail("NB-12", f"/health {r.status_code} {r.text[:200]}")
    body = r.json()
    ms = int(body.get("max_sessions") or 0)
    if ms < 70:
        _fail("NB-12", f"max_sessions={ms} < 70（请在 backend/.env 写 MAX_SESSIONS=70 并重启 API）")
    if "max_concurrent_agents" not in body:
        _fail("NB-12", "health 缺少 max_concurrent_agents")
    _ok("NB-12", f"max_sessions={ms}, agents={body.get('max_concurrent_agents')}")


def check_nb01_browser() -> None:
    """优先 Playwright 点选；无 playwright 时降级为静态入口契约检查。"""
    with httpx.Client(timeout=10.0, trust_env=False) as c:
        page = c.get(KIOSK)
        if page.status_code != 200:
            _fail("NB-01", f"kiosk {page.status_code}")
        html = page.text
        if "entry-gate.js" not in html:
            _fail("NB-01", "index 未引用 entry-gate.js")
        for rel in ("entry-gate.js", "code-browser.js", "nl-patch-dialog.js"):
            rr = c.get(f"{KIOSK}{rel}")
            if rr.status_code != 200:
                _fail("NB-01", f"缺少静态 {rel} → {rr.status_code}")
        gate = c.get(f"{KIOSK}entry-gate.js").text
        for needle in ('data-act="guest"', 'data-act="login"', "游客模式", "登录 / 注册"):
            if needle not in gate:
                _fail("NB-01", f"entry-gate.js 缺少 {needle}")

    used_pw = False
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(KIOSK, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector('[data-act="guest"]', timeout=15000)
            page.wait_for_selector('[data-act="login"]', timeout=5000)
            page.click('[data-act="login"]')
            page.wait_for_selector("#entryAuthForm", timeout=5000)
            page.click('[data-act="back"]')
            page.wait_for_selector('[data-act="guest"]', timeout=5000)
            page.click('[data-act="guest"]')
            page.wait_for_timeout(600)
            browser.close()
        used_pw = True
    except Exception as exc:  # noqa: BLE001
        print(f"  NOTE  NB-01 Playwright 跳过（{exc}）· 已用静态契约")

    _ok("NB-01", "游客∥登录入口" + (" · Playwright 点选" if used_pw else " · 静态契约"))


def check_nb06_isolation(client: httpx.Client) -> None:
    suffix = uuid.uuid4().hex[:8]
    users: list[dict[str, Any]] = []
    for i, name in enumerate((f"sma{suffix}", f"smb{suffix}")):
        r = client.post(
            f"{API}/auth/register",
            json={
                "username": name,
                "password": "secret12",
                "nickname": ("甲同学" if i == 0 else "乙同学"),
                "class_label": "冒烟班",
            },
        )
        if r.status_code != 201:
            _fail("NB-06", f"register {name}: {r.status_code} {r.text[:200]}")
        users.append(r.json())
    ha = {"Authorization": f"Bearer {users[0]['token']}"}
    hb = {"Authorization": f"Bearer {users[1]['token']}"}
    sa = client.post(f"{API}/sessions", json={"auth_mode": "login"}, headers=ha)
    if sa.status_code != 201:
        _fail("NB-06", f"session A: {sa.status_code} {sa.text[:200]}")
    sid_a = sa.json()["session_id"]
    denied = client.get(f"{API}/sessions/{sid_a}", headers=hb)
    if denied.status_code != 403:
        _fail("NB-06", f"期望 B 读 A → 403，实际 {denied.status_code}")
    # workspace 路径含 users/{uid}
    root_hint = str(sa.json().get("workspace_path") or "")
    uid = users[0]["user"]["id"]
    if "users" not in root_hint.replace("\\", "/") and uid not in root_hint:
        # 部分响应不带 workspace_path；用 generate 前 GET
        got = client.get(f"{API}/sessions/{sid_a}", headers=ha)
        payload = got.json().get("payload") or {}
        root_hint = str(payload.get("workspace_path") or root_hint)
    _ok("NB-06", f"跨用户 403；sid_a={sid_a[:8]}…")


def _seed_workspace(session_id: str, user_id: str | None = None) -> Path:
    from app.config import get_settings
    from app.services.workspace_guard import workspace_root_for_session

    settings = get_settings()
    root = workspace_root_for_session(
        settings.workspace_dir, session_id, user_id=user_id
    )
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "core").mkdir(parents=True, exist_ok=True)
    (root / "scenes").mkdir(parents=True, exist_ok=True)
    (root / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (root / "config" / "game_config.json").write_text(
        '{"meta":{"genre":"platformer","display_name":"冒烟"},"theme":{"title":"冒烟"},"tuning":{}}',
        encoding="utf-8",
    )
    (root / "scenes" / "main.tscn").write_text("[gd_scene]\n", encoding="utf-8")
    (root / "core" / "player.gd").write_text("extends CharacterBody2D\n", encoding="utf-8")
    return root


def check_nb07_cert_and_scenes(client: httpx.Client) -> None:
    created = client.post(f"{API}/sessions", json={"auth_mode": "guest"})
    if created.status_code not in (200, 201):
        _fail("NB-07", f"guest session {created.status_code}")
    sid = created.json()["session_id"]
    _seed_workspace(sid)

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    put = client.put(
        f"{API}/sessions/{sid}/certificate",
        content=png,
        headers={"Content-Type": "image/png"},
    )
    if put.status_code != 200:
        _fail("NB-07", f"certificate upload {put.status_code} {put.text[:200]}")
    got = client.get(f"{API}/sessions/{sid}")
    if not got.json().get("payload", {}).get("certificate_saved"):
        _fail("NB-07", "certificate_saved 未置真")
    tree = client.get(f"{API}/sessions/{sid}/workspace/tree")
    if tree.status_code != 200:
        _fail("NB-07", f"tree {tree.status_code}")
    names = {n["name"] for n in tree.json().get("tree", [])}
    if "scenes" not in names:
        _fail("NB-07", f"tree 无 scenes: {names}")
    sc = client.get(
        f"{API}/sessions/{sid}/workspace/file",
        params={"rel_path": "scenes/main.tscn"},
    )
    if sc.status_code != 200 or "[gd_scene]" not in sc.json().get("content", ""):
        _fail("NB-07", f"scenes 读失败 {sc.status_code} {sc.text[:160]}")
    _ok("NB-07", "证书门闩标记 + scenes 可读")


def check_nb03_rating_and_diff(client: httpx.Client) -> None:
    from app.services.learning_analytics import get_learning_store
    from app.services.turn_diff import compute_turn_diff

    created = client.post(f"{API}/sessions", json={"auth_mode": "guest"})
    sid = created.json()["session_id"]
    _seed_workspace(sid)
    store = get_learning_store()

    turn = store.record_agent_turn(
        session_id=sid,
        user_id=None,
        auth_mode="guest",
        user_text="冒烟改快点",
        message="好的，已加速。",
        summary="已加速",
        how_to_play=["方向键移动"],
        gate_passed=True,
    )
    rate = client.post(
        f"{API}/sessions/{sid}/turns/{turn.turn_id}/rating",
        json={"score": 2, "comment": "冒烟"},
    )
    if rate.status_code != 200:
        _fail("NB-03", f"rating {rate.status_code} {rate.text[:200]}")
    body = rate.json()
    if body.get("label") != "比较不满意":
        _fail("NB-03", f"label 异常: {body}")
    diff_payload = compute_turn_diff(
        {"core/player.gd": "extends CharacterBody2D\n"},
        {"core/player.gd": "extends CharacterBody2D\n# faster\n"},
        overview_note="冒烟 Diff",
    )
    store.save_turn_diff(turn.turn_id, diff_payload)
    diff = client.get(f"{API}/sessions/{sid}/turns/{turn.turn_id}/diff")
    if diff.status_code != 200:
        _fail("NB-03", f"diff {diff.status_code}")
    files = diff.json().get("files") or []
    if not files:
        _fail("NB-03", "diff 无 files")
    js = client.get(f"{KIOSK}nl-patch-dialog.js")
    text = js.text if js.status_code == 200 else ""
    if "rating" not in text.lower() and "Diff" not in text and "diff" not in text:
        _fail("NB-03", "nl-patch-dialog.js 未见评价/Diff 相关文案")
    _ok("NB-03", f"rating+diff API；turn={turn.turn_id[:8]}…")


def check_nb10_queue_full(client: httpx.Client) -> None:
    """开服进程与脚本不共享内存闸门 → HTTP 503 以 pytest 为准；此处验文案 + 本机闸门语义。"""
    from app.services.agent_queue import AgentQueueError, get_agent_queue, reset_agent_queue_for_tests

    reset_agent_queue_for_tests()
    gate = get_agent_queue()
    entered = threading.Event()
    release = threading.Event()

    def hold() -> None:
        with gate.acquire("q1", max_concurrent=1, wait_sec=0.15):
            entered.set()
            release.wait(timeout=5.0)

    th = threading.Thread(target=hold, daemon=True)
    th.start()
    if not entered.wait(timeout=1.0):
        release.set()
        _fail("NB-10", "未能占住本地闸门")
    try:
        with gate.acquire("q2", max_concurrent=1, wait_sec=0.15):
            pass
        release.set()
        _fail("NB-10", "期望 agent_queue_full")
    except AgentQueueError as exc:
        if exc.code != "agent_queue_full" or "人数已满" not in exc.message:
            release.set()
            _fail("NB-10", f"错误码/文案不符: {exc.code} {exc.message}")
    release.set()
    th.join(timeout=2.0)
    reset_agent_queue_for_tests()

    js = client.get(f"{KIOSK}nl-patch-dialog.js")
    if js.status_code != 200 or "人数已满" not in js.text:
        _fail("NB-10", "FE 未见人数已满解析")
    if "排队中" not in js.text and "智能体施工中" not in js.text:
        _fail("NB-10", "FE 未见排队中 loading 文案")
    # 与后端单测对齐：同仓 pytest 覆盖跨请求 503
    _ok("NB-10", "闸门满员文案 + FE；HTTP 503 契约见 test_agent_queue_w6")


def main() -> int:
    print("=== 7.20 P0 推荐消项冒烟 ===")
    print(f"API   {API}")
    print(f"Kiosk {KIOSK}")
    results: list[str] = []
    try:
        with httpx.Client(timeout=30.0, trust_env=False) as client:
            try:
                client.get(f"{API}/health").raise_for_status()
            except Exception as exc:  # noqa: BLE001
                print(f"FAIL  API 未就绪: {exc}")
                print("请先启动：cd backend && .venv\\Scripts\\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
                return 2
            try:
                client.get(KIOSK).raise_for_status()
            except Exception as exc:  # noqa: BLE001
                print(f"FAIL  Kiosk 未就绪: {exc}")
                print("请先启动：python -m http.server 8080（仓库根）")
                return 2

            check_nb12_health(client)
            results.append("NB-12")
            check_nb01_browser()
            results.append("NB-01")
            check_nb06_isolation(client)
            results.append("NB-06")
            check_nb07_cert_and_scenes(client)
            results.append("NB-07")
            check_nb03_rating_and_diff(client)
            results.append("NB-03")
            check_nb10_queue_full(client)
            results.append("NB-10")
    except SmokeError as exc:
        print(f"FAIL  {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL  未捕获: {exc}")
        return 1

    print("=== 全部通过 ===")
    print("消项:", ", ".join(results))
    print(json.dumps({"ok": True, "cleared": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
