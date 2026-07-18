#!/usr/bin/env python3
"""七品类 AI 沙箱对话端到端：copy → edu → nl-patch → 没生效 → harvest → 销毁。

用法（仓库根或 backend）：
  python 05-工具脚本/e2e_seven_genres_sandbox.py
  python 05-工具脚本/e2e_seven_genres_sandbox.py --live   # 若有 LLM_API_KEY 则走真实模型

断言：
- templates/** 冻结 hash 不变
- stub 路径下会话非 ai_sandbox core 也不变；live agent 允许改会话 core
- release 等价：先 harvest 入库，再删 workspace；Skill Store 有记录
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402
from app.services.creative.learned_skills import (  # noqa: E402
    harvest_session_experience,
    search_learned_skills,
)
from app.services.creative.llm_patch import apply_nl_patch  # noqa: E402
from app.services.edu_workspace import apply_edu_workspace_patch  # noqa: E402
from app.services.workspace_guard import (  # noqa: E402
    copy_template_to_workspace,
    remove_workspace,
)

SEVEN: tuple[str, ...] = (
    "platformer",
    "shmup",
    "survivor",
    "pingpong",
    "fighting",
    "parkour",
    "racing",
)

# 每品类：先测 catalog 快车道点名技能，再测一条微调/组合
PROMPTS: dict[str, list[str]] = {
    "platformer": [
        "开启二段跳",
        "加下砸",
    ],
    "shmup": ["开启激光", "开启清屏炸弹"],
    "survivor": ["开启磁铁", "开启环形爆发"],
    "pingpong": ["开启大力扣杀", "开启旋转球"],
    "fighting": ["开启格挡", "开启上勾拳"],
    "parkour": ["开启二段跳", "开启滑铲"],
    "racing": ["开启氮气", "开启漂移"],
}


def _hash_tree(core_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not core_dir.is_dir():
        return out
    for p in sorted(core_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(core_dir).as_posix()
        if rel.startswith("ai_sandbox/"):
            continue
        if rel.startswith("edu_") or "overlay" in rel or "hooks" in rel:
            # edu 注入文件允许存在；只校验模板冻结脚本未改
            if "ai_sandbox_bridge" in rel:
                continue
        # 冻结：原模板 core 下非 edu 注入的 .gd
        if p.suffix == ".gd" and not any(
            x in rel
            for x in (
                "edu_action_bridge",
                "ai_sandbox_bridge",
                "window_chrome",
                "_hooks",
                "touch_overlay",
            )
        ):
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _run_genre(genre: str, live: bool) -> dict[str, Any]:
    settings = get_settings()
    if not live:
        settings = settings.model_copy(update={"llm_api_key": ""})

    session_id = str(uuid.uuid4())
    root = copy_template_to_workspace(
        settings.templates_dir, settings.workspace_dir, genre, session_id
    )
    edu_ok = apply_edu_workspace_patch(
        root, genre, settings.templates_dir, settings.workspace_dir
    )
    # 模板冻结：始终校验 templates/{genre}/core 不变
    template_before = _hash_tree(settings.templates_dir / genre / "core")
    # stub 降级仍不应改会话非沙箱 core；live agent 允许改会话副本
    session_before = _hash_tree(root / "core")
    row: dict[str, Any] = {
        "genre": genre,
        "session_id": session_id,
        "workspace": str(root),
        "edu_ok": edu_ok,
        "provider": None,
        "ok": True,
        "errors": [],
        "rounds": [],
        "sandbox_files": [],
        "applied": [],
        "how_to_play": [],
        "core_unchanged": True,
        "templates_unchanged": True,
        "harvest": {},
        "skill_hits_after": 0,
        "bridge_present": (root / "core" / "ai_sandbox_bridge.gd").is_file(),
        "autoload_ok": "AiSandboxBridge="
        in (root / "project.godot").read_text(encoding="utf-8"),
    }
    if not edu_ok:
        row["ok"] = False
        row["errors"].append("edu patch failed")
        return row
    if not row["bridge_present"] or not row["autoload_ok"]:
        row["ok"] = False
        row["errors"].append("AiSandboxBridge missing")

    history: list[dict[str, str]] = []
    last_message = ""
    for prompt in PROMPTS.get(genre, ["跳得更高一点"]):
        try:
            result = apply_nl_patch(
                settings,
                root,
                settings.templates_dir,
                genre,
                prompt,
                history=history,
            )
        except Exception as exc:  # noqa: BLE001
            row["ok"] = False
            row["errors"].append(f"nl-patch:{prompt}:{exc}")
            break
        row["provider"] = result.get("provider")
        round_info = {
            "text": prompt,
            "ok": result.get("ok"),
            "provider": result.get("provider"),
            "express": bool(result.get("express")),
            "applied": result.get("applied_capabilities", []),
            "changes": [c.get("path") for c in result.get("changes", [])],
            "sandbox": result.get("sandbox_files", []),
            "how": result.get("how_to_play", []),
            "gaps": result.get("verify_gaps", []),
            "message": str(result.get("message") or "")[:120],
        }
        row["rounds"].append(round_info)
        if not result.get("ok"):
            row["ok"] = False
            row["errors"].append(f"patch failed: {prompt}")
        history.append({"role": "user", "content": prompt})
        last_message = str(result.get("message") or "")
        history.append({"role": "assistant", "content": last_message[:400]})
        row["sandbox_files"] = result.get("sandbox_files", [])
        row["applied"] = list(
            dict.fromkeys(row["applied"] + list(result.get("applied_capabilities") or []))
        )
        row["how_to_play"] = list(
            dict.fromkeys(row["how_to_play"] + list(result.get("how_to_play") or []))
        )

    # 反馈轮（stub 必测；live catalog 快车道默认跳过，避免 7×多轮 LLM 拖死）
    if history and (not live or getattr(_run_genre, "_force_feedback", False)):
        try:
            fb = apply_nl_patch(
                settings,
                root,
                settings.templates_dir,
                genre,
                PROMPTS[genre][0],
                history=history,
                feedback="没生效，再改一次",
            )
            row["rounds"].append(
                {
                    "text": "feedback:没生效",
                    "ok": fb.get("ok"),
                    "provider": fb.get("provider"),
                    "applied": fb.get("applied_capabilities", []),
                    "gaps": fb.get("verify_gaps", []),
                }
            )
            if not fb.get("ok"):
                row["ok"] = False
                row["errors"].append("feedback patch failed")
        except Exception as exc:  # noqa: BLE001
            row["ok"] = False
            row["errors"].append(f"feedback:{exc}")
    elif live:
        row["rounds"].append(
            {
                "text": "feedback:skipped_on_live_catalog",
                "ok": True,
                "provider": "skip",
                "applied": [],
                "gaps": [],
            }
        )

    template_after = _hash_tree(settings.templates_dir / genre / "core")
    if template_before != template_after:
        row["ok"] = False
        row["templates_unchanged"] = False
        row["errors"].append("templates core mutated (forbidden)")

    session_after = _hash_tree(root / "core")
    if not live and session_before != session_after:
        row["ok"] = False
        row["core_unchanged"] = False
        row["errors"].append("session frozen core mutated under stub")
    elif live and session_before != session_after:
        # agent 允许改会话副本；仅标记，不算失败
        row["core_unchanged"] = False

    # 至少应有一次成功改动；catalog 快车道可能只改 config/桥，不强制 ai_sandbox 目录
    if not row["rounds"] or not any(r.get("ok") for r in row["rounds"]):
        row["ok"] = False
        row["errors"].append("no successful round")
    has_sandbox = (root / "core" / "ai_sandbox").is_dir()
    has_catalog = bool(row.get("applied"))
    if not has_sandbox and not has_catalog:
        row["ok"] = False
        row["errors"].append("no ai_sandbox dir and no catalog applied")
    row["has_sandbox"] = has_sandbox

    # 模拟 release：先 harvest 再销毁
    try:
        harvest = harvest_session_experience(
            settings.learned_skills_dir,
            session_id,
            root,
            genre,
        )
        row["harvest"] = {
            "skipped": harvest.get("skipped"),
            "experience_id": harvest.get("experience_id"),
            "skills_created": harvest.get("skills_created"),
            "skills_merged": harvest.get("skills_merged"),
        }
        if not harvest.get("skipped"):
            if not (
                harvest.get("skills_created")
                or harvest.get("skills_merged")
                or harvest.get("experience_id")
            ):
                row["ok"] = False
                row["errors"].append("harvest produced nothing")
        # catalog 快车道仅开预制技能时允许跳过入库
        elif live and not row.get("applied"):
            row["ok"] = False
            row["errors"].append("live harvest skipped without catalog applied")
        hits = search_learned_skills(
            settings.learned_skills_dir,
            PROMPTS[genre][0],
            genre,
            k=5,
        )
        row["skill_hits_after"] = len(hits)
    except Exception as exc:  # noqa: BLE001
        row["ok"] = False
        row["errors"].append(f"harvest:{exc}")

    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="使用 .env 中的真实 LLM")
    parser.add_argument("--keep", action="store_true", help="保留 workspace 不删除")
    parser.add_argument(
        "--json-out",
        type=str,
        default="",
        help="写出 JSON 报告路径",
    )
    args = parser.parse_args()
    # Settings 读相对路径 .env：切到 backend 目录保证读到 LLM_API_KEY
    import os

    os.chdir(BACKEND)
    get_settings.cache_clear()
    settings = get_settings()
    live = bool(args.live and settings.llm_api_key.strip())
    if args.live and not live:
        print("WARN: --live 但无 LLM_API_KEY，回退 stub")

    results: list[dict[str, Any]] = []
    print(f"=== E2E 七品类 sandbox 对话 · live={live} ===")
    for genre in SEVEN:
        print(f"\n--- {genre} ---")
        row = _run_genre(genre, live=live)
        results.append(row)
        status = "PASS" if row["ok"] else "FAIL"
        print(
            f"[{status}] edu={row['edu_ok']} provider={row['provider']} "
            f"applied={row['applied']} sandbox={len(row['sandbox_files'])} "
            f"tpl_ok={row['templates_unchanged']} "
            f"harvest={row.get('harvest')} skills={row.get('skill_hits_after')}"
        )
        if row["errors"]:
            print("  errors:", "; ".join(row["errors"]))
        if not args.keep:
            try:
                # harvest 已在 _run_genre 完成；此处销毁 workspace（release 后半段）
                remove_workspace(settings.workspace_dir, row["session_id"])
                row["workspace_removed"] = True
            except Exception as exc:  # noqa: BLE001
                print(f"  cleanup warn: {exc}")
                row["workspace_removed"] = False

    # 新会话检索：任取一品类历史话术应能命中 Skill Store
    cross_hits = search_learned_skills(
        settings.learned_skills_dir, "多加有趣的技能 二段跳 炸弹", "platformer", k=5
    )
    print(f"\nSkill Store 检索抽测 hits={len(cross_hits)}")

    passed = sum(1 for r in results if r["ok"])
    report = {
        "live": live,
        "passed": passed,
        "total": len(results),
        "skill_store_hits": len(cross_hits),
        "results": results,
    }
    out_path = (
        Path(args.json_out)
        if args.json_out and Path(args.json_out).is_absolute()
        else (REPO / args.json_out if args.json_out else REPO / "workspace" / "e2e_seven_genres_report.json")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n=== 汇总 {passed}/{len(results)} PASS · 报告 {out_path} ===")
    # 保留 workspace 路径列表供 Godot 抽测：--keep 时打印
    if args.keep:
        for r in results:
            print(f"KEEP {r['genre']}: {r['workspace']}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
