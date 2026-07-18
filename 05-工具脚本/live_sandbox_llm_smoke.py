#!/usr/bin/env python3
"""真实 LLM 沙箱联调：platformer + shmup（agent 主路径 + harvest + 检索）。"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))

import os

os.chdir(BACKEND)

from app.config import get_settings  # noqa: E402
from app.services.creative.llm_patch import apply_nl_patch  # noqa: E402
from app.services.creative.learned_skills import (  # noqa: E402
    harvest_session_experience,
    search_learned_skills,
)
from app.services.edu_workspace import apply_edu_workspace_patch  # noqa: E402
from app.services.workspace_guard import (  # noqa: E402
    copy_template_to_workspace,
    remove_workspace,
)

CASES: list[tuple[str, list[str]]] = [
    (
        "platformer",
        [
            "加二段跳并帮我绘制图标",
            "每吃到5个金币进入无敌并加速，有特效和倒计时",
        ],
    ),
    (
        "shmup",
        [
            "飞机技能太少了。多加有趣的技能",
            "没生效，再改一次",
        ],
    ),
]


def main() -> int:
    get_settings.cache_clear()
    settings = get_settings()
    if not settings.llm_api_key.strip():
        print("FAIL: 无 LLM_API_KEY")
        return 2
    print(
        f"LIVE LLM sandbox · model={settings.llm_model} "
        f"base={settings.llm_base_url} learned={settings.learned_skills_dir}"
    )
    passed = 0
    rows: list[dict] = []
    for genre, prompts in CASES:
        sid = str(uuid.uuid4())
        print(f"\n=== {genre} session={sid} ===")
        root = copy_template_to_workspace(
            settings.templates_dir, settings.workspace_dir, genre, sid
        )
        apply_edu_workspace_patch(
            root, genre, settings.templates_dir, settings.workspace_dir
        )
        history: list[dict[str, str]] = []
        providers: list[str] = []
        ok_all = True
        last_text = prompts[0]
        for i, text in enumerate(prompts):
            feedback = ""
            req = text
            if text.startswith("没生效"):
                feedback = text
                req = last_text
            try:
                result = apply_nl_patch(
                    settings,
                    root,
                    settings.templates_dir,
                    genre,
                    req,
                    history=history,
                    feedback=feedback,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  EXC {text}: {exc}")
                ok_all = False
                break
            providers.append(str(result.get("provider")))
            print(
                f"  [{i+1}] provider={result.get('provider')} ok={result.get('ok')} "
                f"applied={result.get('applied_capabilities')} "
                f"files={len(result.get('sandbox_files') or [])} "
                f"agent_rounds={result.get('agent_rounds')}"
            )
            print(f"       msg={(result.get('message') or '')[:120]}")
            if not result.get("ok"):
                ok_all = False
            history.append({"role": "user", "content": text})
            history.append(
                {
                    "role": "assistant",
                    "content": str(result.get("message") or "")[:400],
                }
            )
            if not text.startswith("没生效"):
                last_text = text

        harvest = harvest_session_experience(
            settings.learned_skills_dir,
            session_id=sid,
            genre=genre,
            workspace_root=root,
        )
        print(
            f"  harvest skipped={harvest.get('skipped')} "
            f"created={harvest.get('skills_created')} "
            f"merged={harvest.get('skills_merged')} exp={harvest.get('experience_id')}"
        )
        hits = search_learned_skills(
            settings.learned_skills_dir, prompts[0], genre, k=3
        )
        print(f"  search_hits={len(hits)} titles={[h.get('title') for h in hits]}")

        # 模板未改抽样
        tpl_player = settings.templates_dir / genre / "core"
        tpl_ok = tpl_player.is_dir()
        remove_workspace(settings.workspace_dir, sid)
        row = {
            "genre": genre,
            "ok": ok_all and any(p in ("agent", "llm") for p in providers),
            "providers": providers,
            "harvest": harvest,
            "hits": len(hits),
            "tpl_dir_ok": tpl_ok,
        }
        # 若 agent 全失败但 stub 成功，标为降级
        if ok_all and all(p == "stub" for p in providers):
            row["ok"] = False
            row["note"] = "全部降级 stub，未打到真实 LLM"
        rows.append(row)
        if row["ok"]:
            passed += 1
            print(f"  => PASS")
        else:
            print(f"  => FAIL {row}")

    out = REPO / "workspace" / "live_sandbox_llm_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"passed": passed, "total": len(CASES), "rows": rows}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"\n=== 汇总 {passed}/{len(CASES)} · {out} ===")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
