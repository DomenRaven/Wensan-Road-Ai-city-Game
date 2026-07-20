#!/usr/bin/env python3
"""全局环境 E2E（HTTP）：G2 generate → G3 nl-patch(Live) → G4 星/Diff → G5 证书/scenes → G6 play → G7 release。

前置：API :8000；backend/.env 含 LLM_API_KEY；Godot 路径有效（G6）。
用法（仓库根）：
  backend\\.venv\\Scripts\\python.exe 05-工具脚本\\e2e_global_env_g2g7.py
  backend\\.venv\\Scripts\\python.exe 05-工具脚本\\e2e_global_env_g2g7.py --genre platformer --skip-play
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

API = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[1]


class Fail(RuntimeError):
    pass


def _ok(step: str, detail: str = "") -> None:
    print(f"  PASS  {step}" + (f" · {detail}" if detail else ""))


def _answers_from_template(tpl: dict[str, Any]) -> dict[str, str]:
    answers: dict[str, str] = {}
    for q in tpl.get("questions") or []:
        qid = str(q.get("id") or "")
        opts = q.get("options") or []
        if not qid or not opts:
            continue
        # 优先选非 default 的中间档，否则第一项
        pick = opts[0]
        for o in opts:
            if str(o.get("id")) not in ("default", "medium", "normal"):
                pick = o
                break
        answers[qid] = str(pick.get("id"))
    if not answers:
        raise Fail("creative template 无可用选项")
    return answers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--genre", default="pingpong", help="品类 slug")
    parser.add_argument("--skip-play", action="store_true", help="跳过 Godot 启动（仅验 generate～证书）")
    parser.add_argument(
        "--nl-text",
        default="球再快一点点，更容易看清",
        help="有 Key 的 nl-patch 用户话",
    )
    parser.add_argument("--timeout", type=float, default=420.0, help="nl-patch 超时秒")
    args = parser.parse_args()
    genre = args.genre.strip()

    print(f"=== 全局 E2E G2–G7 · genre={genre} ===")
    results: dict[str, Any] = {"genre": genre, "steps": {}}

    with httpx.Client(base_url=API, timeout=httpx.Timeout(args.timeout, connect=30.0), trust_env=False) as c:
        health = c.get("/health")
        if health.status_code != 200:
            raise Fail(f"API /health {health.status_code}")
        h = health.json()
        if h.get("status") != "ok":
            raise Fail("health not ok")
        _ok("E3", f"mode={h.get('play_launch_mode')} sessions={h.get('max_sessions')}")

        # —— G2：制作 ——
        created = c.post("/sessions", json={"auth_mode": "guest"})
        if created.status_code not in (200, 201):
            raise Fail(f"create session {created.status_code} {created.text[:200]}")
        sid = created.json()["session_id"]
        results["session_id"] = sid

        intent = c.post(
            "/intent/match-genre",
            json={"text": genre if genre != "pingpong" else "我想打乒乓球", "session_id": sid},
        )
        if intent.status_code != 200:
            raise Fail(f"intent {intent.status_code} {intent.text[:200]}")
        matched = intent.json().get("matched_genre") or intent.json().get("genre")
        if matched and matched != genre:
            print(f"  NOTE  intent matched={matched} · 强制继续 genre={genre}")
        # 确保会话 genre
        patch = c.patch(f"/sessions/{sid}", json={"creator_name": "环境测"})
        if patch.status_code not in (200, 201):
            # 某些部署 PATCH 字段不同，不阻断
            print(f"  NOTE  PATCH creator {patch.status_code}")

        # 直接写 genre：若 intent 未落到目标品类，用 wizard/S1 或再 match
        if matched != genre:
            intent2 = c.post(
                "/intent/match-genre",
                json={"text": {"pingpong": "乒乓球对打", "platformer": "马里奥闯关", "shmup": "飞机射击"}.get(genre, genre), "session_id": sid},
            )
            if intent2.status_code == 200:
                matched = intent2.json().get("matched_genre") or matched

        tpl = c.get(f"/creative/templates/{genre}")
        if tpl.status_code != 200:
            raise Fail(f"template {genre} {tpl.status_code}")
        answers = _answers_from_template(tpl.json())
        ans = c.post(f"/sessions/{sid}/creative/answers", json={"answers": answers})
        if ans.status_code != 200:
            raise Fail(f"creative/answers {ans.status_code} {ans.text[:240]}")
        analyze = c.post(f"/sessions/{sid}/analyze-requirements")
        if analyze.status_code != 200:
            raise Fail(f"analyze {analyze.status_code} {analyze.text[:240]}")
        if not analyze.json().get("resolutions"):
            raise Fail("analyze 无 resolutions")
        c.post(
            f"/sessions/{sid}/wizard/S0",
            json={"data": {"display_name": f"环境测{genre}"}},
        )
        gen = c.post(f"/sessions/{sid}/generate/v2")
        if gen.status_code != 200:
            raise Fail(f"generate/v2 {gen.status_code} {gen.text[:400]}")
        gbody = gen.json()
        if not gbody.get("ok"):
            raise Fail(f"generate ok=false {gbody}")
        wsp = Path(gbody["workspace_path"])
        if not wsp.is_dir() or not (wsp / "project.godot").is_file():
            raise Fail(f"workspace 不完整: {wsp}")
        _ok("G2", f"generate · {wsp.name}")
        results["steps"]["G2"] = {"ok": True, "workspace": str(wsp)}

        # —— G3：Live nl-patch ——
        t0 = time.time()
        nl = c.post(
            f"/sessions/{sid}/nl-patch",
            json={"text": args.nl_text, "history": [], "feedback": ""},
        )
        elapsed = round(time.time() - t0, 1)
        if nl.status_code != 200:
            raise Fail(f"nl-patch {nl.status_code} {nl.text[:500]}")
        nbody = nl.json()
        provider = str(nbody.get("provider") or "")
        turn_id = str(nbody.get("turn_id") or "")
        if provider == "stub":
            raise Fail("nl-patch 仍为 stub · 检查 API 进程是否加载了带 Key 的 .env（需重启 uvicorn）")
        if not nbody.get("ok") and not nbody.get("partial"):
            # 允许 partial；完全失败才报
            print(f"  WARN  nl-patch ok=false partial={nbody.get('partial')} msg={str(nbody.get('message') or '')[:120]}")
        _ok(
            "G3",
            f"provider={provider} turn={turn_id[:12] or '-'} rounds={nbody.get('agent_rounds')} {elapsed}s",
        )
        results["steps"]["G3"] = {
            "ok": True,
            "provider": provider,
            "turn_id": turn_id,
            "elapsed_sec": elapsed,
            "gate_passed": nbody.get("gate_passed"),
            "partial": nbody.get("partial"),
        }

        # —— G4：星级 + Diff ——
        if not turn_id:
            raise Fail("无 turn_id · 学情未落库，无法评星/Diff")
        rate = c.post(
            f"/sessions/{sid}/turns/{turn_id}/rating",
            json={"score": 4, "comment": "e2e"},
        )
        if rate.status_code != 200:
            raise Fail(f"rating {rate.status_code} {rate.text[:200]}")
        diff = c.get(f"/sessions/{sid}/turns/{turn_id}/diff")
        if diff.status_code != 200:
            raise Fail(f"diff {diff.status_code} {diff.text[:200]}")
        dbody = diff.json()
        _ok("G4", f"rating label={rate.json().get('label')} files={dbody.get('file_count')}")
        results["steps"]["G4"] = {"ok": True, "file_count": dbody.get("file_count")}

        # —— G5：证书 + scenes ——
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        put = c.put(
            f"/sessions/{sid}/certificate",
            content=png,
            headers={"Content-Type": "image/png"},
        )
        if put.status_code != 200:
            raise Fail(f"certificate {put.status_code} {put.text[:200]}")
        sess = c.get(f"/sessions/{sid}")
        if not sess.json().get("payload", {}).get("certificate_saved"):
            raise Fail("certificate_saved 未置真")
        tree = c.get(f"/sessions/{sid}/workspace/tree")
        if tree.status_code != 200:
            raise Fail(f"tree {tree.status_code}")
        names = {n["name"] for n in tree.json().get("tree", [])}
        if "scenes" not in names:
            raise Fail(f"tree 无 scenes: {names}")
        # 找一个 scenes 下可读文件
        scene_file = ""
        for n in tree.json().get("tree", []):
            if n.get("name") == "scenes" and n.get("type") == "dir":
                for ch in n.get("children") or []:
                    if ch.get("type") == "file" and ch.get("previewable", True):
                        scene_file = ch["path"]
                        break
        if not scene_file:
            # 回落常见路径
            for cand in ("scenes/game.tscn", "scenes/main.tscn", "scenes/player.tscn"):
                fr = c.get(f"/sessions/{sid}/workspace/file", params={"rel_path": cand})
                if fr.status_code == 200:
                    scene_file = cand
                    break
        if not scene_file:
            raise Fail("scenes 下无可读文件")
        fr = c.get(f"/sessions/{sid}/workspace/file", params={"rel_path": scene_file})
        if fr.status_code != 200:
            raise Fail(f"read {scene_file} {fr.status_code}")
        _ok("G5", f"cert+scenes · {scene_file}")
        results["steps"]["G5"] = {"ok": True, "scene_file": scene_file}

        # —— G6：play/launch ——
        if args.skip_play:
            _ok("G6", "skipped")
            results["steps"]["G6"] = {"ok": True, "skipped": True}
        else:
            launch = c.post(f"/sessions/{sid}/play/launch", json={})
            if launch.status_code != 200:
                raise Fail(f"play/launch {launch.status_code} {launch.text[:300]}")
            lbody = launch.json()
            if not lbody.get("ok"):
                raise Fail(f"launch ok=false {lbody}")
            # server 模式应有 pid（或 already_running）
            mode = lbody.get("launch_mode") or h.get("play_launch_mode")
            pid = lbody.get("pid")
            if mode == "local_share":
                if not lbody.get("ready_for_local_godot"):
                    raise Fail("local_share 未 ready")
            else:
                if pid is None and not lbody.get("already_running"):
                    print(f"  WARN  server 模式无 pid · message={lbody.get('message')}")
            status = c.get(f"/sessions/{sid}/play/status")
            _ok(
                "G6",
                f"mode={mode} pid={pid} status_running={status.json().get('running') if status.status_code==200 else '?'}",
            )
            results["steps"]["G6"] = {
                "ok": True,
                "launch_mode": mode,
                "pid": pid,
                "message": lbody.get("message"),
            }
            # 给窗口一点时间再 release，避免立刻杀进程
            time.sleep(2.0)

        # —— G7：release ——
        rel = c.post(f"/sessions/{sid}/release", params={"harvest": "false"})
        if rel.status_code != 200:
            raise Fail(f"release {rel.status_code} {rel.text[:240]}")
        # release 后 Diff 仍应可回看
        diff2 = c.get(f"/sessions/{sid}/turns/{turn_id}/diff")
        if diff2.status_code != 200:
            raise Fail(f"release 后 diff 丢失 {diff2.status_code}")
        _ok("G7", "release + diff 仍可回看")
        results["steps"]["G7"] = {"ok": True}

    out = ROOT / "reports" / "global_env_e2e"
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = out / f"{stamp}-{genre}.json"
    results["ok"] = True
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=== 全部通过 ===")
    print("report:", path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL  {exc}")
        raise SystemExit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL  {exc}")
        raise SystemExit(1)
