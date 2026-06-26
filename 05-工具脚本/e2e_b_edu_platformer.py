#!/usr/bin/env python3
"""E2E-B-EDU-001 · B 链教育版 platformer 全链路验收（6.24 P0-15）."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parents[1]
DEFAULT_API: str = "http://127.0.0.1:8000"

CREATIVE_ANSWERS: dict[str, str | list[str]] = {
    "q_move": "fast",
    "q_jump": "high",
    "q_enemy": "hard",
    "q_skill": ["double_jump"],
}

EXPECTED_TUNING: dict[str, Any] = {
    "move_speed": 240,
    "jump_velocity": -440,
    "patrol_speed": 65,
    "enabled_skills": ["double_jump"],
}


def api_call(
    base: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any] | str]:
    url: str = f"{base}{path}"
    data: bytes | None = None
    headers: dict[str, str] = {}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            raw: str = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw_err: str = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw_err)
        except json.JSONDecodeError:
            return exc.code, raw_err


def assert_ok(name: str, condition: bool, detail: str = "") -> None:
    status: str = "PASS" if condition else "FAIL"
    msg: str = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def run_e2e_b_edu(base: str, display_name: str = "星星大冒险") -> dict[str, Any]:
    results: dict[str, Any] = {"case_id": "E2E-B-EDU-001", "assertions": {}}

    st, bootstrap = api_call(base, "GET", "/bootstrap")
    bootstrap_ok: bool = st == 200
    assert_ok("E0_bootstrap", bootstrap_ok, str(bootstrap)[:120])

    st, created = api_call(base, "POST", "/sessions")
    assert_ok("E1_create_session", st == 201, str(created))
    session_id: str = str(created["session_id"])  # type: ignore[index]
    results["session_id"] = session_id

    st, intent = api_call(
        base,
        "POST",
        "/intent/match-genre",
        {"text": "我想玩马里奥闯关", "session_id": session_id},
    )
    assert_ok(
        "E2_match_genre",
        st == 200 and intent.get("matched_genre") == "platformer",  # type: ignore[union-attr]
        str(intent),
    )

    st, _ = api_call(
        base,
        "POST",
        f"/sessions/{session_id}/wizard/S0",
        {"data": {"display_name": display_name}},
    )
    assert_ok("E3_display_name", st == 200, display_name)

    st, tpl = api_call(base, "GET", "/creative/templates/platformer")
    assert_ok(
        "E4_creative_template",
        st == 200 and tpl.get("genre") == "platformer",  # type: ignore[union-attr]
        str(tpl)[:120],
    )

    st, answers_resp = api_call(
        base,
        "POST",
        f"/sessions/{session_id}/creative/answers",
        {"answers": CREATIVE_ANSWERS},
    )
    assert_ok("E5_creative_answers", st == 200, str(answers_resp)[:120])

    st, analyze = api_call(base, "POST", f"/sessions/{session_id}/analyze-requirements")
    assert_ok(
        "E6_analyze",
        st == 200
        and analyze.get("llm_patch_required") is False  # type: ignore[union-attr]
        and len(analyze.get("resolutions", [])) >= 3,  # type: ignore[union-attr]
        str(analyze)[:200],
    )
    assert_ok(
        "E6_code_map_preview",
        "jump" in analyze.get("code_map_preview", {}),  # type: ignore[union-attr]
        str(list(analyze.get("code_map_preview", {}).keys())),  # type: ignore[union-attr]
    )

    st, gen = api_call(base, "POST", f"/sessions/{session_id}/generate/v2")
    assert_ok("E7_generate_v2", st == 200 and gen.get("ok") is True, str(gen))  # type: ignore[union-attr]
    results["generate"] = gen

    workspace_root: Path = ROOT / "workspace" / session_id
    config_path: Path = workspace_root / "config" / "game_config.json"
    bridge_path: Path = workspace_root / "core" / "edu_action_bridge.gd"
    hooks_path: Path = workspace_root / "core" / "platformer_hooks.gd"
    project_path: Path = workspace_root / "project.godot"

    assert_ok("E8_config_exists", config_path.is_file(), str(config_path))
    assert_ok("E9_edu_bridge_file", bridge_path.is_file(), str(bridge_path))
    assert_ok("E9_hooks_file", hooks_path.is_file(), str(hooks_path))

    config: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
    tuning: dict[str, Any] = config.get("tuning", {})
    player: dict[str, Any] = tuning.get("player", {})
    enemy: dict[str, Any] = tuning.get("enemy", {})
    skills: list[str] = list(tuning.get("enabled_skills", []))

    assert_ok(
        "E10_move_speed",
        player.get("move_speed") == EXPECTED_TUNING["move_speed"],
        str(player.get("move_speed")),
    )
    assert_ok(
        "E10_jump_velocity",
        player.get("jump_velocity") == EXPECTED_TUNING["jump_velocity"],
        str(player.get("jump_velocity")),
    )
    assert_ok(
        "E10_enemy_patrol",
        enemy.get("patrol_speed") == EXPECTED_TUNING["patrol_speed"],
        str(enemy.get("patrol_speed")),
    )
    assert_ok(
        "E10_enabled_skills",
        "double_jump" in skills,
        str(skills),
    )
    assert_ok(
        "E10_display_name",
        config.get("meta", {}).get("display_name") == display_name,
        str(config.get("meta", {})),
    )

    st, session = api_call(base, "GET", f"/sessions/{session_id}")
    edu_applied: bool = bool(session.get("payload", {}).get("edu_bridge_applied"))  # type: ignore[union-attr]
    assert_ok("E11_edu_bridge_applied", edu_applied, str(session.get("payload", {}))[:200])  # type: ignore[union-attr]

    project_text: str = project_path.read_text(encoding="utf-8") if project_path.is_file() else ""
    assert_ok(
        "E12_autoload",
        "EduActionBridge=" in project_text,
        "EduActionBridge autoload present" if "EduActionBridge=" in project_text else "project.godot missing EduActionBridge autoload",
    )

    code_map: dict[str, Any] = gen.get("code_map", {})  # type: ignore[union-attr]
    assert_ok("E13_code_map", "jump" in code_map, str(list(code_map.keys())))

    st, launch = api_call(base, "POST", f"/sessions/{session_id}/play/launch")
    project_launch: str = str(launch.get("project_path", ""))  # type: ignore[union-attr]
    assert_ok(
        "E14_launch_workspace",
        st == 200 and launch.get("ok") is True and "workspace" in project_launch,  # type: ignore[union-attr]
        project_launch,
    )

    st, actions = api_call(base, "GET", f"/sessions/{session_id}/play/actions?since=0")
    assert_ok(
        "E15_play_actions",
        st == 200 and isinstance(actions.get("actions"), list),  # type: ignore[union-attr]
        str(actions),
    )

    results["workspace_path"] = str(workspace_root)
    results["assertions"] = {
        "E0": bootstrap_ok,
        "E1": bool(session_id),
        "E2": intent.get("matched_genre") == "platformer",  # type: ignore[union-attr]
        "E3": True,
        "E4": tpl.get("genre") == "platformer",  # type: ignore[union-attr]
        "E5": answers_resp.get("ok") is True,  # type: ignore[union-attr]
        "E6": analyze.get("llm_patch_required") is False,  # type: ignore[union-attr]
        "E7": gen.get("ok") is True,  # type: ignore[union-attr]
        "E8": config_path.is_file(),
        "E9": bridge_path.is_file() and hooks_path.is_file(),
        "E10": (
            player.get("move_speed") == EXPECTED_TUNING["move_speed"]
            and player.get("jump_velocity") == EXPECTED_TUNING["jump_velocity"]
            and enemy.get("patrol_speed") == EXPECTED_TUNING["patrol_speed"]
            and "double_jump" in skills
        ),
        "E11": edu_applied,
        "E12": "EduActionBridge=" in project_text,
        "E13": "jump" in code_map,
        "E14": "workspace" in project_launch,
        "E15": isinstance(actions.get("actions"), list),  # type: ignore[union-attr]
        "E16": "mcp run_project — 见 P0-16 单独验证",
    }
    auto_keys: list[str] = [k for k in results["assertions"] if k != "E16"]
    results["pass"] = all(results["assertions"][k] is True for k in auto_keys)
    return results


def main() -> int:
    base: str = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_API
    print(f"E2E-B-EDU-001 @ {base}")
    try:
        summary = run_e2e_b_edu(base)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary.get("pass") else 1
    except AssertionError as exc:
        print(f"E2E 失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
