#!/usr/bin/env python3
"""端到端可用性 / 鲁棒性回归（HTTP）。

覆盖：游客/登录主流程、业务 404 不毁盘、bootstrap 不误删、登录 Diff 跨 sid、
会话 takeover 行为、GET 探活 403 不 silently 成功。

前置：API :8000（建议 Redis）；仓库根执行：
  backend\\.venv\\Scripts\\python.exe 05-工具脚本\\e2e_usability_robustness.py
  backend\\.venv\\Scripts\\python.exe 05-工具脚本\\e2e_usability_robustness.py --with-nl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

API = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[1]


class Fail(RuntimeError):
    pass


def _ok(step: str, detail: str = "") -> None:
    print(f"  PASS  {step}" + (f" · {detail}" if detail else ""))


def _fail(step: str, detail: str) -> None:
    raise Fail(f"{step}: {detail}")


def _answers(c: httpx.Client, genre: str) -> dict[str, str]:
    tpl = c.get(f"/creative/templates/{genre}")
    if tpl.status_code != 200:
        raise Fail(f"creative template {genre} → {tpl.status_code}")
    answers: dict[str, str] = {}
    for q in tpl.json().get("questions") or []:
        qid = str(q.get("id") or "")
        opts = q.get("options") or []
        if qid and opts:
            answers[qid] = str(opts[0].get("id"))
    if not answers:
        raise Fail("creative template empty")
    return answers


def _workspace_exists(path: str) -> bool:
    p = Path(path)
    return p.is_dir() and (p / "project.godot").is_file()


def _seed_turn_diff(*, session_id: str, user_id: str, genre: str) -> str:
    """向 data/learning_analytics 写入一笔可 HTTP 读取的 turn+diff。"""
    import sqlite3

    la = ROOT / "data" / "learning_analytics"
    db = la / "learning.db"
    blobs = la / "blobs"
    if not db.is_file():
        raise Fail(f"learning.db missing: {db}")
    turn_id = f"trn_{uuid.uuid4().hex[:16]}"
    play_id = str(uuid.uuid4())
    now = time.time()
    diff_payload = {
        "rolled_back": False,
        "file_count": 1,
        "overview_note": "鲁棒性注入 Diff",
        "files": [
            {
                "path": "core/a.gd",
                "change_type": "added",
                "diff_text": "--- /dev/null\n+++ b/core/a.gd\n@@ -0,0 +1 @@\n+extends Node\n",
                "after_text": "extends Node\n",
                "note": "测试",
            }
        ],
    }
    rel = f"{turn_id}/diff.json"
    blob_path = blobs / rel
    blob_path.parent.mkdir(parents=True, exist_ok=True)
    blob_path.write_text(json.dumps(diff_payload, ensure_ascii=False), encoding="utf-8")
    con = sqlite3.connect(str(db))
    try:
        con.execute(
            "INSERT OR REPLACE INTO play_sessions "
            "(id, session_id, user_id, guest_key, genre, display_name, creator_name, "
            "auth_mode, workspace_key, created_at, ended_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
            (
                play_id,
                session_id,
                user_id,
                "",
                genre,
                "鲁棒性测试",
                "鲁棒",
                "login",
                "",
                now,
            ),
        )
        con.execute(
            "INSERT INTO agent_turns "
            "(id, play_session_id, session_id, user_id, turn_index, user_text, "
            "agent_reply_full, agent_summary, how_to_play_json, provider, "
            "gate_passed, partial, rolled_back, outcome, goals_json, "
            "sandbox_files_json, truncated, created_at) "
            "VALUES (?,?,?,?,0,?,?,?,?, 'e2e',1,0,0,'success','[]','[]',0,?)",
            (
                turn_id,
                play_id,
                session_id,
                user_id,
                "测试回合",
                "已记录",
                "测",
                "[]",
                now,
            ),
        )
        con.execute(
            "INSERT OR REPLACE INTO agent_turn_diffs "
            "(turn_id, rolled_back, file_count, overview_note, blob_relpath, created_at) "
            "VALUES (?,0,1,?,?,?)",
            (turn_id, "鲁棒性注入 Diff", rel, now),
        )
        con.commit()
    finally:
        con.close()
    return turn_id


def _generate(c: httpx.Client, sid: str, genre: str, headers: dict[str, str] | None = None) -> str:
    hdrs = headers or {}
    intent_text = {
        "shmup": "飞机射击",
        "platformer": "马里奥闯关",
        "pingpong": "乒乓球对打",
    }.get(genre, genre)
    c.post(
        "/intent/match-genre",
        headers=hdrs,
        json={"text": intent_text, "session_id": sid},
    )
    c.patch(f"/sessions/{sid}", headers=hdrs, json={"creator_name": "鲁棒测"})
    answers = _answers(c, genre)
    ans = c.post(
        f"/sessions/{sid}/creative/answers",
        headers=hdrs,
        json={"answers": answers},
    )
    if ans.status_code != 200:
        raise Fail(f"creative/answers {ans.status_code} {ans.text[:200]}")
    c.post(f"/sessions/{sid}/analyze-requirements", headers=hdrs)
    c.post(
        f"/sessions/{sid}/wizard/S0",
        headers=hdrs,
        json={"data": {"display_name": "鲁棒性测试"}},
    )
    gen = c.post(
        f"/sessions/{sid}/generate/v2",
        headers=hdrs,
        json={"meta": {"genre": genre, "display_name": "鲁棒性测试"}, "creative_answers": answers},
        timeout=120.0,
    )
    if gen.status_code != 200:
        raise Fail(f"generate {gen.status_code} {gen.text[:240]}")
    body = gen.json()
    wp = str(body.get("workspace_path") or "")
    if not wp or not _workspace_exists(wp):
        raise Fail(f"workspace missing after generate: {wp!r}")
    return wp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--genre", default="shmup")
    parser.add_argument(
        "--with-nl",
        action="store_true",
        help="跑一轮 nl-patch（需 LLM_API_KEY；较慢）",
    )
    parser.add_argument("--timeout", type=float, default=420.0)
    args = parser.parse_args()
    genre = args.genre.strip()

    print(f"=== 可用性/鲁棒性 E2E · genre={genre} ===")
    report: dict[str, Any] = {"genre": genre, "steps": {}, "ts": time.time()}

    with httpx.Client(
        base_url=API,
        timeout=httpx.Timeout(args.timeout, connect=30.0),
        trust_env=False,
    ) as c:
        # —— E0 健康 ——
        h = c.get("/health")
        if h.status_code != 200:
            _fail("E0", f"health {h.status_code}")
        hj = h.json()
        backend = str(hj.get("session_backend") or "")
        _ok("E0", f"session_backend={backend} play={hj.get('play_launch_mode')}")
        report["session_backend"] = backend
        if backend != "redis":
            print("  WARN  session_backend!=redis · 展厅请启 Redis，避免 memory 冷启动风险")

        # —— U1 游客：制作 → 树/文件 → 业务 404 不毁盘 ——
        g = c.post("/sessions", json={"auth_mode": "guest"})
        if g.status_code not in (200, 201):
            _fail("U1-create", g.text[:200])
        sid = g.json()["session_id"]
        wp = _generate(c, sid, genre)
        tree = c.get(f"/sessions/{sid}/workspace/tree")
        if tree.status_code != 200:
            _fail("U1-tree", tree.text[:200])
        names = {n["name"] for n in tree.json().get("tree") or []}
        if "config" not in names or "core" not in names:
            _fail("U1-tree", f"missing folders {names}")
        cfg = c.get(
            f"/sessions/{sid}/workspace/file",
            params={"rel_path": "config/game_config.json"},
        )
        if cfg.status_code != 200:
            _fail("U1-file", cfg.text[:200])
        # 业务 404：不存在的 turn / rating —— 会话与盘仍在
        bad_turn = c.get(f"/sessions/{sid}/turns/trn_does_not_exist/diff")
        if bad_turn.status_code != 404:
            _fail("U1-turn404", f"expected 404 got {bad_turn.status_code}")
        bad_rate = c.get(f"/sessions/{sid}/turns/trn_does_not_exist/rating")
        if bad_rate.status_code != 404:
            _fail("U1-rating404", f"expected 404 got {bad_rate.status_code}")
        still = c.get(f"/sessions/{sid}")
        if still.status_code != 200:
            _fail("U1-session-alive", "session vanished after business 404")
        if not _workspace_exists(wp):
            _fail("U1-disk-alive", "workspace deleted after business 404")
        _ok("U1", "guest generate + tree + business 404 safe")

        # —— U2 GET /bootstrap 不删活跃 workspace ——
        boot1 = c.get("/bootstrap")
        if boot1.status_code != 200:
            _fail("U2", boot1.text[:200])
        boot2 = c.get("/bootstrap")
        if boot2.status_code != 200:
            _fail("U2", "second bootstrap failed")
        removed = boot2.json().get("orphan_workspaces_removed") or []
        if sid in removed:
            _fail("U2", "active session workspace listed as orphan-removed")
        if not _workspace_exists(wp):
            _fail("U2", "workspace wiped by GET /bootstrap")
        _ok("U2", "GET /bootstrap non-destructive for active sid")

        # —— U3 登录：隔离路径 + Diff + 跨 sid 读本人 turn ——
        uname = f"rb_{uuid.uuid4().hex[:8]}"
        reg = c.post(
            "/auth/register",
            json={
                "username": uname,
                "password": "secret12",
                "nickname": "鲁棒",
            },
        )
        if reg.status_code != 201:
            _fail("U3-reg", reg.text[:200])
        token = reg.json()["token"]
        uid = reg.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}
        s1 = c.post("/sessions", json={"auth_mode": "login"}, headers=headers)
        if s1.status_code not in (200, 201):
            _fail("U3-session", s1.text[:200])
        sid1 = s1.json()["session_id"]
        if s1.json().get("user_id") != uid:
            _fail("U3-session", "user_id mismatch")
        wp1 = _generate(c, sid1, genre, headers=headers)
        if "users" not in Path(wp1).parts or uid not in Path(wp1).parts:
            _fail("U3-path", f"login workspace not isolated: {wp1}")
        # 无 Token 读登录会话 → 403
        denied = c.get(f"/sessions/{sid1}")
        if denied.status_code != 403:
            _fail("U3-403", f"expected 403 got {denied.status_code}")
        # 记一笔 turn + diff（不依赖 LLM；直写学情库，与 API 同 data/learning_analytics）
        turn_id = _seed_turn_diff(session_id=sid1, user_id=uid, genre=genre)
        d1 = c.get(f"/sessions/{sid1}/turns/{turn_id}/diff", headers=headers)
        if d1.status_code != 200:
            _fail("U3-diff", d1.text[:200])
        # 再 create → takeover 旧 sid（删盘）；跨新 sid 仍可读本人 Diff
        s2 = c.post("/sessions", json={"auth_mode": "login"}, headers=headers)
        if s2.status_code not in (200, 201):
            _fail("U3-recreate", s2.text[:200])
        sid2 = s2.json()["session_id"]
        if sid2 == sid1:
            _fail("U3-recreate", "expected new session id")
        taken = s2.json().get("taken_over_session_id")
        if taken != sid1:
            print(f"  WARN  taken_over={taken!r} (expected {sid1[:8]}…)")
        d2 = c.get(f"/sessions/{sid2}/turns/{turn_id}/diff", headers=headers)
        if d2.status_code != 200:
            _fail("U3-cross-diff", d2.text[:200])
        _ok("U3", f"login isolate + cross-sid diff turn={turn_id[:12]}…")

        # —— U4 游客 release 后门闩 ——
        gone = c.get(f"/sessions/{sid}")
        # sid 游客仍在（未 release）
        if gone.status_code != 200:
            _fail("U4-pre", "guest session missing before release")
        rel = c.post(f"/sessions/{sid}/release?harvest=false")
        if rel.status_code != 200:
            _fail("U4-release", rel.text[:200])
        if c.get(f"/sessions/{sid}").status_code != 404:
            _fail("U4-release", "session still listed")
        if _workspace_exists(wp):
            _fail("U4-release", "workspace still on disk after release")
        _ok("U4", "guest release clears session+workspace")

        # —— U5 可选 Live nl-patch ——
        if args.with_nl:
            s3 = c.post("/sessions", json={"auth_mode": "login"}, headers=headers)
            sid3 = s3.json()["session_id"]
            wp3 = _generate(c, sid3, genre, headers=headers)
            nl = c.post(
                f"/sessions/{sid3}/nl-patch",
                headers=headers,
                json={"text": "敌人稍微慢一点", "history": [], "feedback": ""},
                timeout=args.timeout,
            )
            if nl.status_code != 200:
                _fail("U5-nl", nl.text[:300])
            nj = nl.json()
            tid = str(nj.get("turn_id") or "")
            if not tid:
                print("  WARN  nl-patch 无 turn_id（学情落库失败？）")
            else:
                df = c.get(f"/sessions/{sid3}/turns/{tid}/diff", headers=headers)
                if df.status_code != 200:
                    _fail("U5-diff", df.text[:200])
            if not _workspace_exists(wp3):
                _fail("U5-disk", "workspace gone after nl-patch")
            tree3 = c.get(f"/sessions/{sid3}/workspace/tree", headers=headers)
            if tree3.status_code != 200:
                _fail("U5-tree", tree3.text[:200])
            _ok("U5", f"nl-patch ok={nj.get('ok')} turn={tid[:12] if tid else '-'}")
            c.post(f"/sessions/{sid3}/release?harvest=false", headers=headers)
        else:
            _ok("U5", "skipped (--with-nl to enable)")

        # —— U6 play/status 在无 Godot 时不毁盘 ——
        s4 = c.post("/sessions", json={"auth_mode": "guest"})
        sid4 = s4.json()["session_id"]
        wp4 = _generate(c, sid4, genre)
        st = c.get(f"/sessions/{sid4}/play/status")
        if st.status_code != 200:
            _fail("U6", st.text[:200])
        if not _workspace_exists(wp4):
            _fail("U6", "status wiped workspace")
        c.post(f"/sessions/{sid4}/release?harvest=false")
        _ok("U6", "play/status safe")

    report["ok"] = True
    out = ROOT / "reports" / "usability_robustness"
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = out / f"e2e_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"=== ALL PASS · report {path} ===")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except httpx.HTTPError as exc:
        print(f"FAIL  HTTP {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
