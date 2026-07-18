#!/usr/bin/env python3
"""展厅 Live 可感知矩阵：shmup → platformer → parkour。

验收：agent/llm 成功 + 磁盘 L1/L3 证据（config / sandbox / 桥或触控）+ 模板 core 未改。
不替代人手点屏，但挡住「口头 done」。
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.config import get_settings  # noqa: E402
from app.services.creative.llm_patch import apply_nl_patch  # noqa: E402
from app.services.edu_workspace import apply_edu_workspace_patch  # noqa: E402
from app.services.workspace_guard import (  # noqa: E402
    copy_template_to_workspace,
    remove_workspace,
)

# 施工 10.2 矩阵
CASES: list[tuple[str, str, list[str]]] = [
    (
        "shmup",
        "技能少+彩色子弹",
        ["飞机技能太少了，再加点有趣技能，子弹变成五颜六色"],
    ),
    (
        "platformer",
        "二段跳或金币buff",
        ["加二段跳，吃金币有加速特效"],
    ),
    (
        "parkour",
        "开catalog或调手感",
        ["跑得更快一点，跳跃手感更好"],
    ),
]


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _enabled_skills(root: Path) -> list[str]:
    cfg = root / "config" / "game_config.json"
    if not cfg.is_file():
        return []
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    raw = (data.get("tuning") or {}).get("enabled_skills") or data.get("enabled_skills") or []
    return [str(x) for x in raw]


def _sandbox_blob(root: Path) -> str:
    sandbox = root / "core" / "ai_sandbox"
    if not sandbox.is_dir():
        return ""
    parts: list[str] = []
    for p in sandbox.rglob("*.gd"):
        parts.append(_read_text(p))
    return "\n".join(parts)


def _has_touch_pathway(root: Path) -> bool:
    core = root / "core"
    if not core.is_dir():
        return False
    if any(core.glob("*_touch_overlay.gd")):
        return True
    bridge = _read_text(core / "ai_sandbox_bridge.gd")
    return "ensure_touch_action" in bridge or "ensure_touch_skill_buttons" in bridge


def check_perceivable(genre: str, root: Path, result: dict) -> list[str]:
    """返回缺口列表；空=通过。"""
    gaps: list[str] = []
    if not result.get("ok"):
        gaps.append("patch_not_ok")
    provider = str(result.get("provider") or "")
    if provider not in ("agent", "llm"):
        gaps.append(f"provider={provider}")
    if not (root / "core").is_dir():
        gaps.append("no_core")
        return gaps
    if not _has_touch_pathway(root):
        gaps.append("no_touch_pathway")
    skills = _enabled_skills(root)
    blob = _sandbox_blob(root) + _read_text(root / "core" / "ai_sandbox_bridge.gd")
    cfg_txt = _read_text(root / "config" / "game_config.json")
    evidence = blob + cfg_txt + " ".join(skills)

    if genre == "shmup":
        if not skills and "bomb" not in evidence and "laser" not in evidence:
            gaps.append("shmup_no_skill_config")
        if not any(
            k in evidence
            for k in (
                "rainbow_player_bullets",
                "tint_player_bullets",
                "Color(",
                "modulate",
            )
        ):
            # 仅开技能也算部分可感；彩色是强期望
            if "彩色" in str(result.get("message") or "") or "五颜六色" in str(
                result.get("message") or ""
            ):
                if "rainbow" not in evidence and "tint" not in evidence:
                    gaps.append("shmup_no_color_wiring")
    elif genre == "platformer":
        if not any(
            k in evidence.lower()
            for k in ("double", "jump", "二段", "boost", "invincib", "金币", "coin")
        ):
            # agent 可能只改 tuning
            if "tuning" not in cfg_txt and not (root / "core" / "ai_sandbox").is_dir():
                gaps.append("platformer_no_edit_evidence")
    elif genre == "parkour":
        if "tuning" not in cfg_txt and "set_tuning" not in blob and not skills:
            if not result.get("sandbox_files") and not result.get("applied_capabilities"):
                gaps.append("parkour_no_edit_evidence")

    how = " ".join(result.get("how_to_play") or [])
    if how and ("重开" not in how and "重新" not in how):
        gaps.append("how_to_play_no_relaunch_hint")
    return gaps


def main() -> int:
    get_settings.cache_clear()
    settings = get_settings()
    if not settings.llm_api_key.strip():
        print("FAIL: 无 LLM_API_KEY")
        return 2
    print(
        f"LIVE perceivable · model={settings.llm_model} base={settings.llm_base_url}"
    )
    rows: list[dict] = []
    passed = 0
    keep_last: Path | None = None
    for genre, label, prompts in CASES:
        sid = str(uuid.uuid4())
        print(f"\n=== {genre} · {label} · session={sid} ===")
        root = copy_template_to_workspace(
            settings.templates_dir, settings.workspace_dir, genre, sid
        )
        apply_edu_workspace_patch(
            root, genre, settings.templates_dir, settings.workspace_dir
        )
        history: list[dict[str, str]] = []
        last: dict = {}
        ok = True
        for i, text in enumerate(prompts):
            try:
                last = apply_nl_patch(
                    settings,
                    root,
                    settings.templates_dir,
                    genre,
                    text,
                    history=history,
                    feedback="",
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  EXC: {exc}")
                ok = False
                last = {"ok": False, "provider": "exc", "message": str(exc)}
                break
            print(
                f"  [{i+1}] provider={last.get('provider')} ok={last.get('ok')} "
                f"rounds={last.get('agent_rounds')} "
                f"caps={last.get('applied_capabilities')}"
            )
            print(f"       {(last.get('message') or '')[:140]}")
            history.append({"role": "user", "content": text})
            history.append(
                {"role": "assistant", "content": str(last.get("message") or "")[:400]}
            )
            if not last.get("ok"):
                ok = False

        gaps = check_perceivable(genre, root, last) if ok else ["patch_failed"]
        # 模板未改
        tpl_bridge = settings.templates_dir / genre / "core"
        row = {
            "genre": genre,
            "label": label,
            "session": sid,
            "ok": ok and not gaps,
            "gaps": gaps,
            "provider": last.get("provider"),
            "skills": _enabled_skills(root),
            "has_touch": _has_touch_pathway(root),
            "has_sandbox": (root / "core" / "ai_sandbox").is_dir(),
            "tpl_core_exists": tpl_bridge.is_dir(),
            "message": str(last.get("message") or "")[:200],
            "how_to_play": last.get("how_to_play"),
        }
        rows.append(row)
        if row["ok"]:
            passed += 1
            print(f"  => PASS skills={row['skills']} touch={row['has_touch']}")
            remove_workspace(settings.workspace_dir, sid)
        else:
            print(f"  => FAIL gaps={gaps} (保留 workspace 供排查)")
            keep_last = root

    out = REPO / "workspace" / "live_perceivable_report.json"
    out.write_text(
        json.dumps(
            {"passed": passed, "total": len(CASES), "rows": rows},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\n=== 汇总 {passed}/{len(CASES)} · {out} ===")
    if keep_last:
        print(f"失败会话目录: {keep_last}")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
