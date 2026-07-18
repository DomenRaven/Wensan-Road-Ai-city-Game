#!/usr/bin/env python3
"""7.18 · 七品类真·LLM 端到端（每品类 3 任务）· 并行 · 临时工作区自由创作。

任务模型（每品类）：
  T1 加一个简单功能（catalog 单开）
  T2 加两个简单功能（catalog 双开）
  T3 一个创造新功能（前所未有机制，需 LLM 现场写会话 core/scenes）

验收（尽量模拟人类体感）：
  - provider == 'agent'（有 Key 只走智能体，不许 stub 伪降级）
  - ok == True（done 门禁通过：声称⊆磁盘、无幻想 API、含重开+触屏）
  - 落地证据：sandbox_files/changes/applied 至少其一；且磁盘可见（enabled_skills/新文件/会话 core 改动）
  - Godot headless dry-run 无 SCRIPT/parse ERROR（游戏能加载起来 = 可玩前提）
  - templates/{genre}/core 冻结 hash 不变（禁改源）

用法：
  python 05-工具脚本/e2e_7_18_live_three_tasks.py            # 全部并行
  python 05-工具脚本/e2e_7_18_live_three_tasks.py --only shmup platformer
  python 05-工具脚本/e2e_7_18_live_three_tasks.py --keep      # 失败/成功都保留 workspace
  python 05-工具脚本/e2e_7_18_live_three_tasks.py --no-dry    # 跳过 Godot dry-run（仅代码级）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
# Settings 读相对 .env：切到 backend 才能拿到 LLM_API_KEY
os.chdir(BACKEND)

from app.config import get_settings  # noqa: E402
from app.services.creative.agent_contracts import dry_run_godot  # noqa: E402
from app.services.creative.llm_patch import apply_nl_patch  # noqa: E402
from app.services.edu_workspace import apply_edu_workspace_patch  # noqa: E402
from app.services.workspace_guard import (  # noqa: E402
    copy_template_to_workspace,
    remove_workspace,
)

# 每品类：T1 单加 · T2 双加 · T3 新造机制（前所未有）
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
    """templates/{genre}/core 冻结校验：非 edu 注入的 .gd。"""
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
    if not result.get("ok"):
        fails.append("ok=False（门禁未过）")

    changes = result.get("changes") or []
    sandbox = result.get("sandbox_files") or []
    applied = result.get("applied_capabilities") or []
    landing = bool(changes or sandbox or applied)
    if not landing:
        fails.append("无落地产物（changes/sandbox/applied 均空）")

    # 磁盘可见证据
    core_changed = before_core != after_core
    skills_added = set(after_skills) - set(before_skills)
    disk_visible = core_changed or bool(skills_added) or sandbox_count_delta > 0
    if not disk_visible:
        fails.append("磁盘无实际变化（core 未改 + enabled_skills 未增 + 无新沙箱文件）")

    if kind in ("add1", "add2"):
        # 任务累积在同一工作区：按「目标技能是否全部已启用」判定
        missing = [s for s in expect if s not in after_skills]
        if missing:
            fails.append(
                f"目标技能未全部启用：缺 {missing}（当前 enabled={after_skills}）"
            )
    elif kind == "create":
        # 新造机制：必须有会话 core/scenes 或 ai_sandbox 实际代码，不能只靠 catalog
        if not core_changed and sandbox_count_delta <= 0:
            fails.append("新功能：会话 core/scenes/ai_sandbox 无代码落地（疑似口头/仅 catalog 顶替）")

    if dry is not None:
        if dry.get("skipped"):
            fails.append(f"dry-run 跳过（{dry.get('reason')}）：无法在游戏内验收")
        elif not dry.get("ok"):
            errs = dry.get("errors") or []
            fails.append("游戏加载失败: " + "; ".join(str(e)[:120] for e in errs[:3]))
    return fails


def _run_genre(genre: str, do_dry: bool, keep: bool) -> dict[str, Any]:
    settings = get_settings()
    session_id = str(uuid.uuid4())
    root = copy_template_to_workspace(
        settings.templates_dir, settings.workspace_dir, genre, session_id
    )
    edu_ok = apply_edu_workspace_patch(
        root, genre, settings.templates_dir, settings.workspace_dir
    )
    tpl_before = _hash_frozen_core(settings.templates_dir / genre / "core")

    row: dict[str, Any] = {
        "genre": genre,
        "session_id": session_id,
        "workspace": str(root),
        "edu_ok": edu_ok,
        "tasks": [],
        "ok": True,
        "errors": [],
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
        before_sandbox = len(list((root / "core" / "ai_sandbox").rglob("*"))) if (
            root / "core" / "ai_sandbox"
        ).is_dir() else 0

        t0 = time.time()
        try:
            result = apply_nl_patch(
                settings, root, settings.templates_dir, genre, text, history=history
            )
        except Exception as exc:  # noqa: BLE001
            row["ok"] = False
            row["errors"].append(f"{kind}:{text}:EXC:{exc}")
            row["tasks"].append(
                {"kind": kind, "text": text, "exception": str(exc)[:300], "accepted": False}
            )
            break
        elapsed = round(time.time() - t0, 1)

        after_core = _session_core_hash(root)
        after_skills = _enabled_skills(root)
        after_sandbox = len(list((root / "core" / "ai_sandbox").rglob("*"))) if (
            root / "core" / "ai_sandbox"
        ).is_dir() else 0

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

        row["tasks"].append(
            {
                "kind": kind,
                "text": text,
                "provider": result.get("provider"),
                "ok": result.get("ok"),
                "express": bool(result.get("express")),
                "elapsed_s": elapsed,
                "changes": [c.get("path") for c in (result.get("changes") or [])],
                "sandbox_files": result.get("sandbox_files") or [],
                "applied": result.get("applied_capabilities") or [],
                "how_to_play": result.get("how_to_play") or [],
                "verify_gaps": result.get("verify_gaps") or [],
                "skills_added": sorted(set(after_skills) - set(before_skills)),
                "core_changed": before_core != after_core,
                "sandbox_delta": after_sandbox - before_sandbox,
                "dry_run": dry,
                "message": str(result.get("message") or "")[:200],
                "accepted": accepted,
                "accept_fails": fails,
            }
        )

        history.append({"role": "user", "content": text})
        history.append(
            {"role": "assistant", "content": str(result.get("message") or "")[:400]}
        )

    tpl_after = _hash_frozen_core(settings.templates_dir / genre / "core")
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
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", default=[], help="只跑指定品类")
    parser.add_argument("--keep", action="store_true", help="保留 workspace")
    parser.add_argument("--no-dry", action="store_true", help="跳过 Godot dry-run")
    parser.add_argument("--workers", type=int, default=7)
    parser.add_argument("--json-out", type=str, default="")
    args = parser.parse_args()

    get_settings.cache_clear()
    settings = get_settings()
    if not settings.llm_api_key.strip():
        print("FATAL: 无 LLM_API_KEY，无法做真·LLM 端到端。")
        return 2

    genres = args.only or list(TASKS.keys())
    do_dry = not args.no_dry
    print(f"=== 7.18 E2E live · genres={genres} · dry={do_dry} · workers={args.workers} ===")

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {
            ex.submit(_run_genre, g, do_dry, args.keep): g for g in genres
        }
        for fut in as_completed(futs):
            g = futs[fut]
            try:
                row = fut.result()
            except Exception as exc:  # noqa: BLE001
                row = {"genre": g, "ok": False, "errors": [f"RUNNER:{exc}"], "tasks": []}
            results.append(row)
            status = "PASS" if row.get("ok") else "FAIL"
            print(f"\n[{status}] {g}")
            for t in row.get("tasks", []):
                ts = "OK " if t.get("accepted") else "XX "
                print(
                    f"  {ts}{t['kind']:6} p={t.get('provider')} "
                    f"skills+={t.get('skills_added')} core±={t.get('core_changed')} "
                    f"sbx±={t.get('sandbox_delta')} {t.get('elapsed_s')}s"
                )
                if t.get("accept_fails"):
                    print("      fails:", "; ".join(t["accept_fails"]))
            if row.get("errors"):
                print("  errors:", "; ".join(row["errors"]))

    results.sort(key=lambda r: list(TASKS.keys()).index(r["genre"]) if r["genre"] in TASKS else 99)
    passed = sum(1 for r in results if r.get("ok"))
    task_total = sum(len(r.get("tasks", [])) for r in results)
    task_pass = sum(
        1 for r in results for t in r.get("tasks", []) if t.get("accepted")
    )
    report = {
        "passed_genres": passed,
        "total_genres": len(results),
        "passed_tasks": task_pass,
        "total_tasks": task_total,
        "results": results,
    }
    out_path = (
        Path(args.json_out)
        if args.json_out
        else REPO / "workspace" / "e2e_7_18_live_report.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"\n=== 汇总 品类 {passed}/{len(results)} · 任务 {task_pass}/{task_total} · 报告 {out_path} ==="
    )
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
