#!/usr/bin/env python3
"""7.19 · HF-13 · 七品类真·LLM 端到端（每品类 3 任务）· 并发探针。

相对 7.18 校准（施工规范 §5.2）：
  - 有 Key：provider==agent 且 agent_rounds>=1；禁 express / agent_rounds=0 业务成功
  - 验收看 gate_passed（非仅 result.ok）；partial/rolled_back 记入报告
  - 每案落盘：原话、rounds、工具序列、写盘 diff、gate、dry-run、messages
  - 报告目录：reports/live_three_tasks/<stamp>/
  - templates/{genre}/core 前后 hash 不变

任务模型（每品类）：
  T1 加一个简单功能（可 enable catalog，须经 Agent 循环）
  T2 加两个简单功能
  T3 创造性全新功能（须会话 core/scenes/sandbox 代码落地）

用法：
  python 05-工具脚本/e2e_7_19_live_three_tasks.py --only platformer shmup --workers 2
  python 05-工具脚本/e2e_7_19_live_three_tasks.py --keep
  python 05-工具脚本/e2e_7_19_live_three_tasks.py --no-dry
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

_CAPTURE_TLS = threading.local()
_REAL_LLM_TURN: Any = None
_LLM_PATCHED = False
_LLM_PATCH_LOCK = threading.Lock()

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.config import get_settings  # noqa: E402
from app.services.creative import game_agent as ga  # noqa: E402
from app.services.creative.agent_contracts import dry_run_godot  # noqa: E402
from app.services.creative.llm_patch import apply_nl_patch  # noqa: E402
from app.services.edu_workspace import apply_edu_workspace_patch  # noqa: E402
from app.services.workspace_guard import (  # noqa: E402
    copy_template_to_workspace,
    remove_workspace,
)

# 每品类：T1 单加 · T2 双加 · T3 新造机制
TASKS: dict[str, list[dict[str, Any]]] = {
    "platformer": [
        {"kind": "add1", "text": "开启二段跳", "expect": ["double_jump"]},
        {"kind": "add2", "text": "开启二段跳和下砸", "expect": ["double_jump", "ground_pound"]},
        {
            "kind": "create",
            "text": "在关卡里加一个会上下移动的弹跳板，角色踩上去会被高高弹起",
        },
    ],
    "shmup": [
        {"kind": "add1", "text": "开启激光", "expect": ["laser_beam"]},
        {"kind": "add2", "text": "开启激光和清屏炸弹", "expect": ["laser_beam", "bomb"]},
        {
            "kind": "create",
            "text": "让敌机被击落时有小概率掉落一颗爱心，飞机捡到爱心回一点血",
        },
    ],
    "survivor": [
        {"kind": "add1", "text": "开启吸经验", "expect": ["magnet"]},
        {"kind": "add2", "text": "开启吸经验和环形爆发", "expect": ["magnet", "nova"]},
        {
            "kind": "create",
            "text": "每存活30秒就在场上刷一个金色宝箱，玩家碰到它时全屏敌人减速3秒",
        },
    ],
    "pingpong": [
        {"kind": "add1", "text": "开启大力扣杀", "expect": ["power_smash"]},
        {"kind": "add2", "text": "开启大力扣杀和旋转球", "expect": ["power_smash", "curve_ball"]},
        {
            "kind": "create",
            "text": "连续接住5个球后，我的球拍变长一次并持续8秒",
        },
    ],
    "fighting": [
        {"kind": "add1", "text": "开启格挡", "expect": ["block_parry"]},
        {"kind": "add2", "text": "开启格挡和上勾拳", "expect": ["block_parry", "special_uppercut"]},
        {
            "kind": "create",
            "text": "给角色加一个蓄力重拳，按住蓄满后放开，一拳把对手击退很远",
        },
    ],
    "parkour": [
        {"kind": "add1", "text": "开启二段跳", "expect": ["double_jump"]},
        {"kind": "add2", "text": "开启二段跳和滑铲", "expect": ["double_jump", "slide"]},
        {
            "kind": "create",
            "text": "跑道上每隔一段距离出现一个加速光环，穿过它冲刺速度提升持续2秒",
        },
    ],
    "racing": [
        {"kind": "add1", "text": "开启氮气", "expect": ["boost"]},
        {"kind": "add2", "text": "开启氮气和漂移", "expect": ["boost", "drift_snap"]},
        {
            "kind": "create",
            "text": "赛道上随机刷出香蕉皮，赛车压到会打滑失控1秒",
        },
    ],
}


def _hash_frozen_core(core_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not core_dir.is_dir():
        return out
    for p in sorted(core_dir.rglob("*.gd")):
        rel = p.relative_to(core_dir).as_posix()
        if any(
            x in rel
            for x in (
                "edu_action_bridge",
                "ai_sandbox_bridge",
                "window_chrome",
                "_hooks",
                "touch_overlay",
            )
        ):
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _session_core_hash(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    core = root / "core"
    if not core.is_dir():
        return out
    for p in sorted(core.rglob("*")):
        if p.is_file():
            out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _snapshot_text_files(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in {".gd", ".tscn", ".json"}:
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith("."):
            continue
        out[rel] = p.read_text(encoding="utf-8", errors="replace")
    return out


def _workspace_diffs(before: dict[str, str], after: dict[str, str]) -> dict[str, str]:
    diffs: dict[str, str] = {}
    for rel in sorted(set(before) | set(after)):
        old = before.get(rel, "")
        new = after.get(rel, "")
        if old == new:
            continue
        diffs[rel] = "".join(
            difflib.unified_diff(
                old.splitlines(keepends=True),
                new.splitlines(keepends=True),
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
            )
        )
    return diffs


def _enabled_skills(root: Path) -> list[str]:
    cfg = root / "config" / "game_config.json"
    if not cfg.is_file():
        return []
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
        t = data.get("tuning") if isinstance(data, dict) else {}
        raw = t.get("enabled_skills") if isinstance(t, dict) else []
        return [str(x) for x in raw] if isinstance(raw, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _tool_sequence_from_replies(llm_replies: list[Any]) -> list[str]:
    seq: list[str] = []
    for reply in llm_replies:
        if not isinstance(reply, dict):
            continue
        actions = reply.get("actions")
        if not isinstance(actions, list):
            continue
        for a in actions:
            if isinstance(a, dict):
                tool = str(a.get("tool") or "").strip()
                if tool:
                    seq.append(tool)
    return seq


def _ensure_llm_capture_patch() -> None:
    """全局只装一次；按线程分流到各自 captured（支持并发品类）。"""
    global _REAL_LLM_TURN, _LLM_PATCHED
    with _LLM_PATCH_LOCK:
        if _LLM_PATCHED:
            return
        _REAL_LLM_TURN = ga._llm_turn

        def _threaded_intercept(
            settings_inner: Any, messages: list[dict[str, str]]
        ) -> dict[str, Any]:
            bucket = getattr(_CAPTURE_TLS, "captured", None)
            if isinstance(bucket, dict):
                bucket.setdefault("turns", []).append(
                    [
                        {
                            "role": m.get("role"),
                            "chars": len(str(m.get("content") or "")),
                            "content": str(m.get("content") or ""),
                        }
                        for m in messages
                    ]
                )
            assert _REAL_LLM_TURN is not None
            parsed = _REAL_LLM_TURN(settings_inner, messages)
            if isinstance(bucket, dict):
                bucket.setdefault("llm_replies", []).append(parsed)
            return parsed

        ga._llm_turn = _threaded_intercept  # type: ignore[assignment]
        _LLM_PATCHED = True


def _apply_with_capture(
    settings: Any,
    root: Path,
    genre: str,
    text: str,
    history: list[dict[str, str]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """生产入口 apply_nl_patch，并拦截 _llm_turn 以保留全轮轨迹。"""
    _ensure_llm_capture_patch()
    captured: dict[str, Any] = {"turns": [], "llm_replies": []}
    _CAPTURE_TLS.captured = captured
    try:
        result = apply_nl_patch(
            settings, root, settings.templates_dir, genre, text, history=history
        )
    finally:
        _CAPTURE_TLS.captured = None
    return result, captured


def _accept_task(
    kind: str,
    expect: list[str],
    result: dict[str, Any],
    before_core: dict[str, str],
    after_core: dict[str, str],
    before_skills: list[str],
    after_skills: list[str],
    sandbox_count_delta: int,
    dry: dict[str, Any] | None,
) -> list[str]:
    """返回验收失败原因列表；空 = 通过。"""
    fails: list[str] = []
    if result.get("provider") != "agent":
        fails.append(f"provider={result.get('provider')}（应为 agent，禁 stub/伪降级）")
    if bool(result.get("express")):
        fails.append("express=True（HF-13 禁 catalog express）")
    rounds = result.get("agent_rounds")
    try:
        rounds_n = int(rounds) if rounds is not None else 0
    except (TypeError, ValueError):
        rounds_n = 0
    if rounds_n < 1:
        fails.append(f"agent_rounds={rounds}（有 Key 须 >=1，禁 rounds=0 业务成功）")
    if not result.get("gate_passed"):
        fails.append(
            f"gate_passed=False（partial={result.get('partial')} "
            f"rolled_back={result.get('rolled_back')}）"
        )

    changes = result.get("changes") or []
    sandbox = result.get("sandbox_files") or []
    applied = result.get("applied_capabilities") or []
    landing = bool(changes or sandbox or applied)
    if not landing and not (set(after_skills) - set(before_skills)):
        fails.append("无落地产物（changes/sandbox/applied/skills 均空）")

    core_changed = before_core != after_core
    skills_added = set(after_skills) - set(before_skills)
    disk_visible = core_changed or bool(skills_added) or sandbox_count_delta > 0
    if not disk_visible:
        fails.append("磁盘无实际变化（core 未改 + enabled_skills 未增 + 无新沙箱文件）")

    if kind in ("add1", "add2"):
        missing = [s for s in expect if s not in after_skills]
        if missing:
            fails.append(
                f"目标技能未全部启用：缺 {missing}（当前 enabled={after_skills}）"
            )
    elif kind == "create":
        if not core_changed and sandbox_count_delta <= 0:
            fails.append("新功能：会话 core/scenes/ai_sandbox 无代码落地（疑似口头/仅 catalog 顶替）")

    if dry is not None:
        if dry.get("skipped"):
            fails.append(f"dry-run 跳过（{dry.get('reason')}）：无法在游戏内验收")
        elif not dry.get("ok"):
            errs = dry.get("errors") or []
            fails.append("游戏加载失败: " + "; ".join(str(e)[:120] for e in errs[:3]))
    return fails


def _safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)[:80]


def _run_genre(
    genre: str,
    do_dry: bool,
    keep: bool,
    report_dir: Path,
) -> dict[str, Any]:
    settings = get_settings()
    session_id = str(uuid.uuid4())
    root = copy_template_to_workspace(
        settings.templates_dir, settings.workspace_dir, genre, session_id
    )
    edu_ok = apply_edu_workspace_patch(
        root, genre, settings.templates_dir, settings.workspace_dir
    )
    tpl_before = _hash_frozen_core(settings.templates_dir / genre / "core")
    genre_dir = report_dir / "cases" / genre
    genre_dir.mkdir(parents=True, exist_ok=True)
    (genre_dir / "diffs").mkdir(exist_ok=True)
    (genre_dir / "messages").mkdir(exist_ok=True)

    row: dict[str, Any] = {
        "genre": genre,
        "session_id": session_id,
        "workspace": str(root),
        "edu_ok": edu_ok,
        "tasks": [],
        "ok": True,
        "errors": [],
        "template_core_hash_before": {
            k: v[:16] for k, v in sorted(tpl_before.items())
        },
    }
    if not edu_ok:
        row["ok"] = False
        row["errors"].append("edu patch failed")
        return row
    if not (root / "core" / "ai_sandbox_bridge.gd").is_file():
        row["ok"] = False
        row["errors"].append("AiSandboxBridge missing")
        return row

    history: list[dict[str, str]] = []
    for task in TASKS[genre]:
        kind, text = task["kind"], task["text"]
        before_core = _session_core_hash(root)
        before_skills = _enabled_skills(root)
        before_text = _snapshot_text_files(root)
        before_sandbox = (
            len(list((root / "core" / "ai_sandbox").rglob("*")))
            if (root / "core" / "ai_sandbox").is_dir()
            else 0
        )

        t0 = time.time()
        try:
            result, captured = _apply_with_capture(
                settings, root, genre, text, history
            )
        except Exception as exc:  # noqa: BLE001
            row["ok"] = False
            row["errors"].append(f"{kind}:{text}:EXC:{exc}")
            row["tasks"].append(
                {
                    "kind": kind,
                    "text": text,
                    "exception": str(exc)[:300],
                    "accepted": False,
                }
            )
            break
        elapsed = round(time.time() - t0, 1)

        after_core = _session_core_hash(root)
        after_skills = _enabled_skills(root)
        after_text = _snapshot_text_files(root)
        after_sandbox = (
            len(list((root / "core" / "ai_sandbox").rglob("*")))
            if (root / "core" / "ai_sandbox").is_dir()
            else 0
        )
        diffs = _workspace_diffs(before_text, after_text)
        tool_seq = _tool_sequence_from_replies(captured.get("llm_replies") or [])

        dry: dict[str, Any] | None = None
        if do_dry:
            dry = dry_run_godot(root, settings.godot_path, timeout_sec=40.0)

        fails = _accept_task(
            kind,
            task.get("expect") or [],
            result,
            before_core,
            after_core,
            before_skills,
            after_skills,
            after_sandbox - before_sandbox,
            dry,
        )
        accepted = not fails
        if not accepted:
            row["ok"] = False

        case_id = f"{genre}_{kind}"
        for rel, patch_text in diffs.items():
            patch_path = genre_dir / "diffs" / f"{case_id}__{_safe_name(rel)}.patch"
            patch_path.write_text(patch_text, encoding="utf-8")

        turns_path = genre_dir / "messages" / f"{case_id}_turns.json"
        turns_path.write_text(
            json.dumps(captured.get("turns") or [], ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        replies_path = genre_dir / "messages" / f"{case_id}_replies.json"
        replies_path.write_text(
            json.dumps(captured.get("llm_replies") or [], ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )

        task_row: dict[str, Any] = {
            "kind": kind,
            "text": text,
            "provider": result.get("provider"),
            "ok": result.get("ok"),
            "gate_passed": bool(result.get("gate_passed")),
            "partial": bool(result.get("partial")),
            "rolled_back": bool(result.get("rolled_back")),
            "express": bool(result.get("express")),
            "agent_rounds": result.get("agent_rounds"),
            "elapsed_s": elapsed,
            "understanding": result.get("understanding"),
            "goals": result.get("goals") or [],
            "changes": [c.get("path") for c in (result.get("changes") or [])],
            "sandbox_files": result.get("sandbox_files") or [],
            "attempted_paths": result.get("attempted_paths") or [],
            "applied": result.get("applied_capabilities") or [],
            "how_to_play": result.get("how_to_play") or [],
            "verify_gaps": result.get("verify_gaps") or [],
            "skills_added": sorted(set(after_skills) - set(before_skills)),
            "core_changed": before_core != after_core,
            "sandbox_delta": after_sandbox - before_sandbox,
            "tool_sequence": tool_seq,
            "diff_files": [
                f"cases/{genre}/diffs/{case_id}__{_safe_name(rel)}.patch"
                for rel in diffs
            ],
            "messages_turns": f"cases/{genre}/messages/{case_id}_turns.json",
            "messages_replies": f"cases/{genre}/messages/{case_id}_replies.json",
            "agent_dry_run": result.get("dry_run") or {},
            "probe_dry_run": dry,
            "message": str(result.get("message") or "")[:300],
            "accepted": accepted,
            "accept_fails": fails,
        }
        row["tasks"].append(task_row)
        (genre_dir / f"{case_id}.json").write_text(
            json.dumps(task_row, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        history.append({"role": "user", "content": text})
        history.append(
            {"role": "assistant", "content": str(result.get("message") or "")[:400]}
        )

    tpl_after = _hash_frozen_core(settings.templates_dir / genre / "core")
    row["template_core_unchanged"] = tpl_before == tpl_after
    if tpl_before != tpl_after:
        row["ok"] = False
        row["errors"].append("templates core mutated (FORBIDDEN)")

    if row["ok"] and not keep:
        try:
            remove_workspace(settings.workspace_dir, session_id)
            row["workspace_removed"] = True
        except Exception as exc:  # noqa: BLE001
            row["errors"].append(f"cleanup:{exc}")
    else:
        row["workspace_removed"] = False

    (genre_dir / "genre_summary.json").write_text(
        json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", default=[], help="只跑指定品类")
    parser.add_argument("--keep", action="store_true", help="保留 workspace")
    parser.add_argument("--no-dry", action="store_true", help="跳过 Godot dry-run")
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="并发品类数（HF-13 建议 2～4，默认 2）",
    )
    parser.add_argument("--json-out", type=str, default="")
    parser.add_argument(
        "--stamp",
        type=str,
        default="",
        help="报告时间戳目录名；默认本地时间 YYYYMMDD-HHMMSS",
    )
    args = parser.parse_args()

    get_settings.cache_clear()
    settings = get_settings()
    if not settings.llm_api_key.strip():
        print("FATAL: 无 LLM_API_KEY，无法做真·LLM 端到端。")
        return 2

    stamp = args.stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    report_dir = REPO / "reports" / "live_three_tasks" / stamp
    report_dir.mkdir(parents=True, exist_ok=True)

    genres = args.only or list(TASKS.keys())
    do_dry = not args.no_dry
    print(
        f"=== 7.19 HF-13 E2E live · genres={genres} · dry={do_dry} "
        f"· workers={args.workers} · report={report_dir} ==="
    )
    print(
        f"settings: agent_max_rounds={settings.agent_max_rounds} "
        f"soft_extra={settings.agent_soft_extra_rounds} "
        f"wall={settings.agent_wall_clock_sec}s"
    )

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = {
            ex.submit(_run_genre, g, do_dry, args.keep, report_dir): g for g in genres
        }
        for fut in as_completed(futs):
            g = futs[fut]
            try:
                row = fut.result()
            except Exception as exc:  # noqa: BLE001
                row = {
                    "genre": g,
                    "ok": False,
                    "errors": [f"RUNNER:{exc}"],
                    "tasks": [],
                }
            results.append(row)
            status = "PASS" if row.get("ok") else "FAIL"
            print(f"\n[{status}] {g}")
            for t in row.get("tasks", []):
                ts = "OK " if t.get("accepted") else "XX "
                tools = ",".join((t.get("tool_sequence") or [])[:8])
                print(
                    f"  {ts}{t['kind']:6} p={t.get('provider')} "
                    f"rounds={t.get('agent_rounds')} gate={t.get('gate_passed')} "
                    f"express={t.get('express')} rb={t.get('rolled_back')} "
                    f"skills+={t.get('skills_added')} core±={t.get('core_changed')} "
                    f"sbx±={t.get('sandbox_delta')} {t.get('elapsed_s')}s"
                )
                if tools:
                    print(f"      tools: {tools}")
                if t.get("accept_fails"):
                    print("      fails:", "; ".join(t["accept_fails"]))
            if row.get("errors"):
                print("  errors:", "; ".join(row["errors"]))

    results.sort(
        key=lambda r: list(TASKS.keys()).index(r["genre"]) if r["genre"] in TASKS else 99
    )
    passed = sum(1 for r in results if r.get("ok"))
    task_total = sum(len(r.get("tasks", [])) for r in results)
    task_pass = sum(
        1 for r in results for t in r.get("tasks", []) if t.get("accepted")
    )
    report = {
        "stamp": stamp,
        "hf": "HF-13",
        "passed_genres": passed,
        "total_genres": len(results),
        "passed_tasks": task_pass,
        "total_tasks": task_total,
        "settings": {
            "agent_max_rounds": settings.agent_max_rounds,
            "agent_soft_extra_rounds": settings.agent_soft_extra_rounds,
            "agent_wall_clock_sec": settings.agent_wall_clock_sec,
            "llm_model": getattr(settings, "llm_model", ""),
        },
        "results": results,
    }
    out_path = Path(args.json_out) if args.json_out else report_dir / "summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"\n=== 汇总 品类 {passed}/{len(results)} · 任务 {task_pass}/{task_total} "
        f"· 报告 {out_path} ==="
    )
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
