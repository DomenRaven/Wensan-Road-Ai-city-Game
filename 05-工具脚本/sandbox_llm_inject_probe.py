#!/usr/bin/env python3
"""注入 LLM 沙箱探针：走生产 apply_nl_patch → run_game_agent，拦截 messages 并扫描。

用法（在仓库根或 backend 外均可）:
  python 05-工具脚本/sandbox_llm_inject_probe.py
  python 05-工具脚本/sandbox_llm_inject_probe.py --live   # 真调一轮 LLM（需 Key）

不改盘玩法；会话结束后删除临时 workspace。
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))

import os

os.chdir(BACKEND)

from app.config import get_settings  # noqa: E402
from app.services.creative import game_agent as ga  # noqa: E402
from app.services.creative.llm_patch import apply_nl_patch  # noqa: E402
from app.services.creative.learned_skills import append_session_patch_log  # noqa: E402
from app.services.edu_workspace import apply_edu_workspace_patch  # noqa: E402
from app.services.workspace_guard import (  # noqa: E402
    copy_template_to_workspace,
    remove_workspace,
)

# 不得出现在注入正文里的窄化/负面劫持词（产品文档注释除外）
_BAD_TOKENS: tuple[str, ...] = (
    "脚步",
    "只修玩家",
    "不要假设",
    "故障·强制",
    "禁止空 done",
    "只能改玩家",
    "严禁",
    "反模式",
    "禁止再 enable",
    "禁止只 enable",
    "不要重复无效",
)

_CASES: list[dict[str, Any]] = [
    {
        "id": "pingpong_color_feedback",
        "genre": "pingpong",
        "user_text": "发完大力球，之后球还是红色，颜色没有恢复",
        "feedback": "",
        "seed_recent_writes": True,
        "expect_in_user": ["开放读盘", "近期改动", "core/ball.gd"],
        "expect_not_playability_hijack": True,
    },
    {
        "id": "pingpong_conditional_create",
        "genre": "pingpong",
        "user_text": "每接3个球可以大力扣杀一次，球要很快，有火焰效果",
        "feedback": "",
        "seed_recent_writes": False,
        "expect_in_system": ["开放读盘", "读盘"],
    },
    {
        "id": "shmup_conditional_laser",
        "genre": "shmup",
        "user_text": "激光要每打5下才可以发射一次，并且子弹变成彩虹色",
        "feedback": "",
        "seed_recent_writes": False,
        "expect_in_system": ["开放读盘", "读盘"],
        "expect_in_user": ["施工上下文"],
    },
    {
        "id": "shmup_drop_loot",
        "genre": "shmup",
        "user_text": "敌机掉落激光，捡到后才开启",
        "feedback": "",
        "seed_recent_writes": False,
        "expect_in_user": ["掉落", "player_ship.gd"],
    },
    {
        "id": "platformer_coin_condition",
        "genre": "platformer",
        "user_text": "每吃到5个金币，无敌并加速3秒",
        "feedback": "",
        "seed_recent_writes": False,
        "expect_in_user": ["施工上下文", "level_01.gd"],
    },
    {
        "id": "parkour_white_screen",
        "genre": "parkour",
        "user_text": "白屏了，人看不见",
        "feedback": "",
        "seed_recent_writes": False,
        "expect_in_user": ["可玩性提示", "开放读盘"],
    },
    {
        "id": "survivor_kill_condition",
        "genre": "survivor",
        "user_text": "每击败10个敌人自动释放一次新星",
        "feedback": "",
        "seed_recent_writes": False,
        "expect_in_user": ["施工上下文", "player_survivor.gd"],
    },
    {
        "id": "fighting_combo_condition",
        "genre": "fighting",
        "user_text": "连续格挡3次后获得一次强化升龙",
        "feedback": "",
        "seed_recent_writes": False,
        "expect_in_user": ["施工上下文", "player_fighter.gd"],
    },
    {
        "id": "racing_drift_condition",
        "genre": "racing",
        "user_text": "漂移持续3秒后获得短暂加速",
        "feedback": "",
        "seed_recent_writes": False,
        "expect_in_user": ["施工上下文", "car_topdown.gd"],
    },
]


def _scan_blob(blob: str) -> list[str]:
    hits: list[str] = []
    for tok in _BAD_TOKENS:
        if tok in blob:
            hits.append(tok)
    # system/playbook 主路径不应再堆「禁止…」禁令句（门禁错误另论）
    if re.search(r"禁止空\s*done|禁止只修|禁止再开新技能", blob):
        hits.append("legacy_forbid_phrase")
    return hits


def _seed_recent(root: Path) -> None:
    append_session_patch_log(
        root,
        {
            "ok": True,
            "user_text": "每接3个球大力扣杀",
            "summary": "已实现扣杀与火焰",
            "sandbox_files": ["core/ball.gd", "core/paddle.gd"],
            "gate_passed": True,
        },
    )
    # 会话内植入「扣杀改红、复位未清色」差分（不改 templates）
    ball_path = root / "core" / "ball.gd"
    if not ball_path.is_file():
        raise RuntimeError("seed_recent: 缺少 core/ball.gd")
    body = ball_path.read_text(encoding="utf-8")
    if "func activate_smash" in body:
        # 仍须断言：复位缺颜色恢复
        if "_smash_mode = false" in body and "Color.WHITE" not in body.split(
            "func reset_to_center", 1
        )[-1][:400]:
            return
        return
    body = body.replace(
        "var _ai_paddle: Area2D = null\n",
        "var _ai_paddle: Area2D = null\nvar _smash_mode: bool = false\n",
        1,
    )
    smash_fn = """
func activate_smash() -> void:
	_smash_mode = true
	if _visual:
		_visual.color = Color(1.0, 0.2, 0.2, 1.0)
	if _sprite:
		_sprite.modulate = Color(1.0, 0.35, 0.2, 1.0)


"""
    body = body.replace(
        "func reset_to_center(center: Vector2) -> void:",
        smash_fn + "func reset_to_center(center: Vector2) -> void:",
        1,
    )
    # 复位清模式但不清颜色（探针目标 bug）
    if "func reset_to_center(center: Vector2) -> void:\n" in body:
        body = body.replace(
            "func reset_to_center(center: Vector2) -> void:\n",
            "func reset_to_center(center: Vector2) -> void:\n\t_smash_mode = false\n",
            1,
        )
    ball_path.write_text(body, encoding="utf-8")
    # HF-12：seed 后立即断言夹具成立
    seeded = ball_path.read_text(encoding="utf-8")
    if "func activate_smash" not in seeded:
        raise RuntimeError("seed_recent: activate_smash 未写入")
    reset_body = seeded.split("func reset_to_center", 1)[-1][:500]
    if "_smash_mode = false" not in reset_body:
        raise RuntimeError("seed_recent: reset 未清 _smash_mode")
    if "color = Color.WHITE" in reset_body or "modulate = Color.WHITE" in reset_body:
        raise RuntimeError("seed_recent: reset 不应已有颜色恢复（探针目标是缺恢复）")


def _git_meta(repo: Path) -> dict[str, Any]:
    meta: dict[str, Any] = {"revision": "", "dirty": False}
    try:
        rev = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo), text=True
        ).strip()
        meta["revision"] = rev
        st = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=str(repo), text=True
        )
        meta["dirty"] = bool(st.strip())
    except (OSError, subprocess.CalledProcessError):
        pass
    return meta


def _hash_templates_core(templates: Path, genre: str) -> str:
    core = templates / genre / "core"
    h = hashlib.sha256()
    if not core.is_dir():
        return ""
    for p in sorted(core.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(core).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def _snapshot_workspace_text(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in {".gd", ".tscn", ".json"}:
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith("."):
            continue
        out[rel] = p.read_text(encoding="utf-8", errors="replace")
    return out


def _workspace_diffs(
    before: dict[str, str],
    after: dict[str, str],
) -> dict[str, str]:
    diffs: dict[str, str] = {}
    for rel in sorted(set(before) | set(after)):
        old = before.get(rel, "")
        new = after.get(rel, "")
        if old == new:
            continue
        patch = "".join(
            difflib.unified_diff(
                old.splitlines(keepends=True),
                new.splitlines(keepends=True),
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
            )
        )
        diffs[rel] = patch
    return diffs


def _capture_run(
    settings: Any,
    root: Path,
    genre: str,
    user_text: str,
    feedback: str,
    *,
    live: bool,
) -> dict[str, Any]:
    captured: dict[str, Any] = {"turns": [], "live": live}
    real_llm = ga._llm_turn

    def _intercept(settings_inner: Any, messages: list[dict[str, str]]) -> dict[str, Any]:
        captured["turns"].append(
            [
                {
                    "role": m.get("role"),
                    "chars": len(str(m.get("content") or "")),
                    "content": str(m.get("content") or ""),
                }
                for m in messages
            ]
        )
        if live:
            try:
                parsed = real_llm(settings_inner, messages)
                captured.setdefault("llm_replies", []).append(parsed)
                return parsed
            except Exception as exc:  # noqa: BLE001
                captured["live_error"] = str(exc)
                raise
        # 离线沙箱：立刻 done，只验注入
        return {
            "understanding": "沙箱探针：仅验证注入内容",
            "goals": ["检查提示词正向"],
            "thought": "probe",
            "actions": [
                {
                    "tool": "done",
                    "summary": "沙箱探针结束（未改盘）",
                    "how_to_play": ["重开后点屏试玩"],
                }
            ],
        }

    ga._llm_turn = _intercept  # type: ignore[assignment]
    try:
        out = apply_nl_patch(
            settings,
            root,
            settings.templates_dir,
            genre,
            user_text,
            history=[],
            feedback=feedback,
        )
        captured["agent_result"] = {
            "ok": out.get("ok"),
            "partial": out.get("partial"),
            "provider": out.get("provider"),
            "message": (out.get("message") or "")[:400],
            "intent": (out.get("intent_route") or {}).get("intent"),
            "sandbox_files": out.get("sandbox_files") or [],
            "understanding": out.get("understanding"),
            "goals": out.get("goals"),
            "agent_rounds": out.get("agent_rounds"),
            "gate_passed": out.get("gate_passed"),
            "dry_run": out.get("dry_run") or {},
            "attempted_paths": out.get("attempted_paths") or [],
            "rolled_back": bool(out.get("rolled_back")),
            "verify_gaps": out.get("verify_gaps") or [],
        }
    finally:
        ga._llm_turn = real_llm  # type: ignore[assignment]
    return captured


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM 注入沙箱探针")
    parser.add_argument(
        "--live",
        action="store_true",
        help="首轮真调 LLM（需真实 LLM_API_KEY）；默认纯拦截不联网",
    )
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="只跑指定 case id（可多次）；默认全部",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="保留临时 workspace 与报告目录",
    )
    args = parser.parse_args()

    get_settings.cache_clear()
    settings = get_settings()
    if args.live and not settings.llm_api_key.strip():
        print("FAIL: --live 需要 LLM_API_KEY")
        return 2

    cases = _CASES
    if args.case:
        wanted = set(args.case)
        cases = [c for c in _CASES if c["id"] in wanted]
        if not cases:
            print(f"FAIL: 无匹配 case：{args.case}")
            return 2

    report_root = REPO / "reports" / "inject_probe"
    report_root.mkdir(parents=True, exist_ok=True)
    mode = "live" if args.live else "offline"
    run_id = uuid.uuid4().hex[:8]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    report_dir = report_root / f"{stamp}-{mode}-{run_id}"
    (report_dir / "cases").mkdir(parents=True)
    (report_dir / "messages").mkdir(parents=True)
    (report_dir / "diffs").mkdir(parents=True)
    rows: list[dict[str, Any]] = []
    failed = 0
    git_meta = _git_meta(REPO)

    print(
        f"LLM inject probe · mode={mode} · cases={len(cases)} · "
        f"model={settings.llm_model} · report={report_dir}"
    )

    for case in cases:
        sid = str(uuid.uuid4())
        genre = str(case["genre"])
        print(f"\n=== {case['id']} · {genre} · session={sid} ===")
        tpl_hash_before = _hash_templates_core(settings.templates_dir, genre)
        root = copy_template_to_workspace(
            settings.templates_dir, settings.workspace_dir, genre, sid
        )
        apply_edu_workspace_patch(
            root, genre, settings.templates_dir, settings.workspace_dir
        )
        if case.get("seed_recent_writes"):
            _seed_recent(root)
        workspace_before = _snapshot_workspace_text(root)

        # pydantic Settings：无 Key 时注入探针假 Key（拦截器默认不联网）
        probe_settings = settings
        if not settings.llm_api_key.strip() or not args.live:
            probe_settings = settings.model_copy(
                update={"llm_api_key": settings.llm_api_key.strip() or "sk-inject-probe"}
            )

        try:
            cap = _capture_run(
                probe_settings,
                root,
                genre,
                str(case["user_text"]),
                str(case.get("feedback") or ""),
                live=bool(args.live),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  EXC: {exc}")
            failed += 1
            rows.append({"id": case["id"], "ok": False, "error": str(exc)})
            if not args.keep:
                remove_workspace(settings.workspace_dir, sid)
            continue

        turns = cap.get("turns") or []
        if not turns:
            print("  FAIL: 未捕获到任何 LLM messages")
            failed += 1
            rows.append({"id": case["id"], "ok": False, "error": "no_messages"})
            if not args.keep:
                remove_workspace(settings.workspace_dir, sid)
            continue

        # HF-12：扫描所有轮次
        all_system: list[str] = []
        all_user: list[str] = []
        for turn in turns:
            for m in turn:
                if m.get("role") == "system":
                    all_system.append(str(m.get("content") or ""))
                elif m.get("role") == "user":
                    all_user.append(str(m.get("content") or ""))
        system = all_system[0] if all_system else ""
        user = all_user[0] if all_user else ""
        blob = "\n\n".join(all_system + all_user)
        bad = _scan_blob(blob)
        missing: list[str] = []
        for needle in case.get("expect_in_user") or []:
            if needle not in user and needle not in "\n".join(all_user):
                missing.append(f"user缺少:{needle}")
        for needle in case.get("expect_in_system") or []:
            if needle not in system and needle not in "\n".join(all_system):
                missing.append(f"system缺少:{needle}")
        if case.get("expect_not_playability_hijack"):
            if "可玩性提示" in user and "球还是红色" in case["user_text"]:
                missing.append("颜色反馈被标成可玩性危急（不应）")
            if "只修" in user or "只能改玩家" in user:
                missing.append("出现玩家可见性劫持")
        # 品类隔离：pingpong/racing 等不应出现 platformer 专属 capability 行
        if genre in ("pingpong", "racing", "fighting", "survivor"):
            if re.search(
                r"double_jump\s*·\s*二段跳|ground_pound\s*·\s*下砸|coin_streak_buff\s*·",
                blob,
            ):
                missing.append("跨品类 catalog 串味")
        # 高信号树：关键文件应在首轮 user
        must_core = {
            "pingpong": ["ball.gd", "paddle.gd", "game.tscn"],
            "shmup": ["player_ship.gd"],
            "platformer": ["player_platformer.gd", "level_01.gd"],
            "parkour": ["player_runner.gd"],
            "survivor": ["player_survivor.gd"],
            "fighting": ["player_fighter.gd"],
            "racing": ["car_topdown.gd"],
        }
        for name in must_core.get(genre) or []:
            if name not in user:
                missing.append(f"树摘要缺:{name}")
        # 单次请求内 Reference 索引不重复；不同轮次会重复携带同一 system/user。
        if any(
            "\n".join(str(m.get("content") or "") for m in turn).count(
                "【Reference Skills 索引】"
            )
            > 1
            for turn in turns
        ):
            missing.append("Reference 疑似重复注入")
        ar = cap.get("agent_result") or {}
        if args.live:
            replies = cap.get("llm_replies") or []
            tool_names: list[str] = []
            for r in replies:
                for a in r.get("actions") or []:
                    if isinstance(a, dict):
                        tool_names.append(str(a.get("tool") or ""))
            if "read_file" not in tool_names and "diagnose_workspace" not in tool_names:
                missing.append("live未读盘")
            if "replace_text" not in tool_names and any(
                t == "write_file" for t in tool_names
            ):
                # 大文件整写视为风险；确定性加固工具可替代 replace_text
                if "ensure_player_visibility" not in tool_names:
                    missing.append("live未用replace_text")
            if ar.get("gate_passed") is not True:
                missing.append("live gate_passed!=true")
            if ar.get("partial"):
                missing.append("live partial=true")
            files = ar.get("sandbox_files") or []
            if files:
                print(f"  live_wrote={files}")
            else:
                print(f"  live_tools={tool_names[:16]}")

        workspace_after = _snapshot_workspace_text(root)
        diffs = _workspace_diffs(workspace_before, workspace_after)
        changed_paths = sorted(diffs)
        for rel, patch_text in diffs.items():
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "__", rel)
            (report_dir / "diffs" / f"{case['id']}__{safe_name}.patch").write_text(
                patch_text, encoding="utf-8"
            )
        tpl_hash_after = _hash_templates_core(settings.templates_dir, genre)
        if tpl_hash_before != tpl_hash_after:
            missing.append("templates/core hash 被改动")

        ok = not bad and not missing
        print(
            f"  system={len(system)}c user={len(user)}c turns={len(turns)} "
            f"bad={bad or '[]'} missing={missing or '[]'} "
            f"agent={ar}"
        )
        if cap.get("live_error"):
            print(f"  live_error: {cap['live_error']}")
        if not ok:
            failed += 1

        dump_path = report_dir / "cases" / f"{case['id']}.json"
        dump_path.write_text(
            json.dumps(
                {
                    "case": case,
                    "ok": ok,
                    "bad_tokens": bad,
                    "missing": missing,
                    "agent_result": ar,
                    "live_error": cap.get("live_error"),
                    "llm_replies": cap.get("llm_replies"),
                    "system_chars": len(system),
                    "user_chars": len(user),
                    "llm_turns_captured": len(turns),
                    "template_hash_before": tpl_hash_before,
                    "template_hash_after": tpl_hash_after,
                    "changed_paths": changed_paths,
                    "diff_files": [
                        f"diffs/{case['id']}__{re.sub(r'[^A-Za-z0-9_.-]+', '__', rel)}.patch"
                        for rel in changed_paths
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (report_dir / "messages" / f"{case['id']}_system.md").write_text(
            system, encoding="utf-8"
        )
        (report_dir / "messages" / f"{case['id']}_user.md").write_text(
            user, encoding="utf-8"
        )
        (report_dir / "messages" / f"{case['id']}_turns.json").write_text(
            json.dumps(turns, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        rows.append(
            {
                "id": case["id"],
                "ok": ok,
                "bad_tokens": bad,
                "missing": missing,
                "dump": str(dump_path),
                "gate_passed": ar.get("gate_passed"),
                "partial": ar.get("partial"),
                "dry_run": ar.get("dry_run") or {},
                "changed_paths": changed_paths,
            }
        )
        if not args.keep:
            remove_workspace(settings.workspace_dir, sid)

    summary_path = report_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "mode": mode,
                "timestamp": stamp,
                "run_id": run_id,
                "git": git_meta,
                "model": settings.llm_model,
                "failed": failed,
                "total": len(cases),
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n=== done failed={failed}/{len(cases)} report={summary_path} ===")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
