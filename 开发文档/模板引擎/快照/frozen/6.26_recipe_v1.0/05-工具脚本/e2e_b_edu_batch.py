#!/usr/bin/env python3
"""E2E-B-EDU-BATCH · B 链教育版六款品类批量验收（6.24 P1 窗8）."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parents[1]
DEFAULT_API: str = "http://127.0.0.1:8000"
DEFAULT_SLUGS: str = "shmup,survivor,pingpong,fighting,parkour,racing"

SlugCase = dict[str, Any]

SLUG_CASES: dict[str, SlugCase] = {
    "shmup": {
        "case_id": "E2E-B-EDU-002",
        "intent_text": "我想打飞机",
        "display_name": "雷霆小队",
        "creative_answers": {
            "q_speed": "fast",
            "q_fire_rate": "dense",
            "q_spawn": "dense",
            "q_hp": "high",
            "q_enemy_bullet": "fast",
        },
        "code_map_key": "fire",
        "hooks_file": "shmup_hooks.gd",
        "expected_tuning": {
            "player.speed": 390,
            "player.bullet_interval_ms": 140,
            "spawn.interval_ms": 1050,
            "player.max_hp": 4,
            "enemy.bullet_speed": 273,
        },
        "min_resolutions": 4,
    },
    "survivor": {
        "case_id": "E2E-B-EDU-003",
        "intent_text": "割草打怪",
        "display_name": "糖果幸存者",
        "creative_answers": {
            "q_speed": "fast",
            "q_spawn": "dense",
            "q_duration": "intense",
            "q_hp": "high",
            "q_weapon": "fast",
        },
        "code_map_key": "move",
        "hooks_file": "survivor_hooks.gd",
        "expected_tuning": {
            "player.speed": 195,
            "spawn.interval_ms": 2800,
            "session.duration_sec": 126,
            "player.max_hp": 130,
            "weapon.interval_ms": 350,
        },
        "min_resolutions": 4,
    },
    "pingpong": {
        "case_id": "E2E-B-EDU-004",
        "intent_text": "乒乓球",
        "display_name": "弹弹乐",
        "creative_answers": {
            "q_ball": "fast",
            "q_win": "long",
            "q_ai": "strong",
            "q_paddle": "fast",
            "q_angle": "high",
        },
        "code_map_key": "ball_speed",
        "hooks_file": "pingpong_hooks.gd",
        "expected_tuning": {
            "ball.base_speed": 325,
            "rules.points_to_win": 6,
            "ai.speed": 153,
            "paddle.speed": 218,
            "physics.contact_angle_scale": 5.46,
        },
        "min_resolutions": 4,
    },
    "fighting": {
        "case_id": "E2E-B-EDU-005",
        "intent_text": "格斗双人",
        "display_name": "像素拳王",
        "creative_answers": {
            "q_speed": "fast",
            "q_light": "strong",
            "q_ai": "strong",
            "q_heavy": "strong",
        },
        "code_map_key": "player_speed",
        "hooks_file": "fighting_hooks.gd",
        "expected_tuning": {
            "combat.player_speed": 260,
            "combat.light_damage": 6,
            "ai.move_speed_scale": 1.0,
            "combat.heavy_damage": 20,
        },
        "min_resolutions": 4,
    },
    "parkour": {
        "case_id": "E2E-B-EDU-006",
        "intent_text": "跑酷",
        "display_name": "无尽奔跑",
        "creative_answers": {
            "q_run": "fast",
            "q_jump": "high",
            "q_obstacle": "dense",
            "q_gravity": "heavy",
            "q_coin_gap": "dense",
        },
        "code_map_key": "jump",
        "hooks_file": "parkour_hooks.gd",
        "expected_tuning": {
            "runner.speed": 390,
            "jump.velocity": -870,
            "obstacle.min_gap_ms": 1400,
            "physics.gravity": 1950,
            "collectible.min_gap_ms": 1050,
        },
        "min_resolutions": 4,
    },
    "racing": {
        "case_id": "E2E-B-EDU-007",
        "intent_text": "赛车",
        "display_name": "欢乐赛车",
        "creative_answers": {
            "q_speed": "fast",
            "q_turn": "nimble",
            "q_lap": "long",
            "q_time": "long",
            "q_traffic": "dense",
        },
        "code_map_key": "car_speed",
        "hooks_file": "racing_hooks.gd",
        "expected_tuning": {
            "car.max_speed": 1040,
            "car.turn_speed": 390,
            "track.lap_distance_px": 13000,
            "round.duration_sec": 117,
            "spawn.base_delay_ms": 1400,
        },
        "min_resolutions": 4,
    },
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
        with urllib.request.urlopen(request, timeout=120) as resp:
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


def get_tuning_value(tuning: dict[str, Any], dotted: str) -> Any:
    current: Any = tuning
    for part in dotted.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def run_slug_e2e(base: str, slug: str, case: SlugCase) -> dict[str, Any]:
    case_id: str = str(case["case_id"])
    results: dict[str, Any] = {"slug": slug, "case_id": case_id, "assertions": {}}
    print(f"\n=== {case_id} · {slug} ===")

    st, _bootstrap = api_call(base, "GET", "/bootstrap")
    bootstrap_ok: bool = st == 200
    assert_ok(f"{slug}/bootstrap", bootstrap_ok, str(_bootstrap)[:80])

    st, created = api_call(base, "POST", "/sessions")
    assert_ok(f"{slug}/create_session", st == 201, str(created))
    session_id: str = str(created["session_id"])  # type: ignore[index]
    results["session_id"] = session_id

    st, intent = api_call(
        base,
        "POST",
        "/intent/match-genre",
        {"text": case["intent_text"], "session_id": session_id},
    )
    assert_ok(
        f"{slug}/match_genre",
        st == 200 and intent.get("matched_genre") == slug,  # type: ignore[union-attr]
        str(intent),
    )

    display_name: str = str(case["display_name"])
    st, _ = api_call(
        base,
        "POST",
        f"/sessions/{session_id}/wizard/S0",
        {"data": {"display_name": display_name}},
    )
    assert_ok(f"{slug}/display_name", st == 200, display_name)

    st, tpl = api_call(base, "GET", f"/creative/templates/{slug}")
    assert_ok(
        f"{slug}/creative_template",
        st == 200 and tpl.get("genre") == slug,  # type: ignore[union-attr]
        str(tpl)[:120],
    )

    creative_answers: dict[str, Any] = dict(case["creative_answers"])
    st, answers_resp = api_call(
        base,
        "POST",
        f"/sessions/{session_id}/creative/answers",
        {"answers": creative_answers},
    )
    assert_ok(f"{slug}/creative_answers", st == 200, str(answers_resp)[:120])

    st, analyze = api_call(base, "POST", f"/sessions/{session_id}/analyze-requirements")
    min_res: int = int(case["min_resolutions"])
    code_map_key: str = str(case["code_map_key"])
    assert_ok(
        f"{slug}/analyze",
        st == 200
        and analyze.get("llm_patch_required") is False  # type: ignore[union-attr]
        and len(analyze.get("resolutions", [])) >= min_res,  # type: ignore[union-attr]
        str(analyze)[:200],
    )
    assert_ok(
        f"{slug}/code_map_preview",
        code_map_key in analyze.get("code_map_preview", {}),  # type: ignore[union-attr]
        str(list(analyze.get("code_map_preview", {}).keys())),  # type: ignore[union-attr]
    )

    st, gen = api_call(base, "POST", f"/sessions/{session_id}/generate/v2")
    assert_ok(f"{slug}/generate_v2", st == 200 and gen.get("ok") is True, str(gen))  # type: ignore[union-attr]

    workspace_root: Path = ROOT / "workspace" / session_id
    config_path: Path = workspace_root / "config" / "game_config.json"
    bridge_path: Path = workspace_root / "core" / "edu_action_bridge.gd"
    hooks_path: Path = workspace_root / "core" / str(case["hooks_file"])
    project_path: Path = workspace_root / "project.godot"

    assert_ok(f"{slug}/config_exists", config_path.is_file(), str(config_path))
    assert_ok(f"{slug}/edu_bridge_file", bridge_path.is_file(), str(bridge_path))
    assert_ok(f"{slug}/hooks_file", hooks_path.is_file(), str(hooks_path))

    config: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
    tuning: dict[str, Any] = config.get("tuning", {})
    expected: dict[str, Any] = dict(case["expected_tuning"])
    tuning_ok: bool = True
    tuning_details: list[str] = []
    for key, expected_val in expected.items():
        actual: Any = get_tuning_value(tuning, key)
        if key == "enabled_skills":
            ok_val: bool = isinstance(actual, list) and all(
                skill in actual for skill in expected_val  # type: ignore[union-attr]
            )
        else:
            ok_val = actual == expected_val
        if not ok_val:
            tuning_ok = False
            tuning_details.append(f"{key}={actual} (want {expected_val})")
    assert_ok(
        f"{slug}/tuning",
        tuning_ok,
        "; ".join(tuning_details) if tuning_details else "ok",
    )

    st, session = api_call(base, "GET", f"/sessions/{session_id}")
    edu_applied: bool = bool(session.get("payload", {}).get("edu_bridge_applied"))  # type: ignore[union-attr]
    assert_ok(f"{slug}/edu_bridge_applied", edu_applied, str(session.get("payload", {}))[:160])  # type: ignore[union-attr]

    project_text: str = project_path.read_text(encoding="utf-8") if project_path.is_file() else ""
    assert_ok(
        f"{slug}/autoload",
        "EduActionBridge=" in project_text,
        "EduActionBridge autoload present" if "EduActionBridge=" in project_text else "missing",
    )

    code_map: dict[str, Any] = gen.get("code_map", {})  # type: ignore[union-attr]
    assert_ok(f"{slug}/code_map", code_map_key in code_map, str(list(code_map.keys())))

    st, launch = api_call(base, "POST", f"/sessions/{session_id}/play/launch")
    project_launch: str = str(launch.get("project_path", ""))  # type: ignore[union-attr]
    assert_ok(
        f"{slug}/launch_workspace",
        st == 200 and launch.get("ok") is True and "workspace" in project_launch,  # type: ignore[union-attr]
        project_launch,
    )

    st, actions = api_call(base, "GET", f"/sessions/{session_id}/play/actions?since=0")
    assert_ok(
        f"{slug}/play_actions",
        st == 200 and isinstance(actions.get("actions"), list),  # type: ignore[union-attr]
        str(actions),
    )

    results["workspace_path"] = str(workspace_root)
    results["assertions"] = {
        "bootstrap": bootstrap_ok,
        "match_genre": intent.get("matched_genre") == slug,  # type: ignore[union-attr]
        "generate": gen.get("ok") is True,  # type: ignore[union-attr]
        "edu_bridge": bridge_path.is_file() and hooks_path.is_file(),
        "tuning": tuning_ok,
        "edu_bridge_applied": edu_applied,
        "autoload": "EduActionBridge=" in project_text,
        "code_map": code_map_key in code_map,
        "launch": "workspace" in project_launch,
        "play_actions": isinstance(actions.get("actions"), list),  # type: ignore[union-attr]
    }
    results["pass"] = all(results["assertions"].values())
    return results


def cleanup_sessions(base: str) -> None:
    st, listed = api_call(base, "GET", "/sessions")
    if st != 200 or not isinstance(listed, dict):
        return
    for row in listed.get("sessions", []):
        sid: str = str(row.get("session_id", ""))
        if sid:
            api_call(base, "DELETE", f"/sessions/{sid}")


def run_batch(base: str, slugs: list[str]) -> dict[str, Any]:
    cleanup_sessions(base)
    summary: dict[str, Any] = {
        "case_id": "E2E-B-EDU-BATCH",
        "api": base,
        "slugs": slugs,
        "results": [],
    }
    passed: int = 0
    for slug in slugs:
        if slug not in SLUG_CASES:
            raise ValueError(f"未知 slug: {slug} · 可选: {','.join(SLUG_CASES)}")
        result: dict[str, Any] = run_slug_e2e(base, slug, SLUG_CASES[slug])
        summary["results"].append(result)
        if result.get("pass"):
            passed += 1
    summary["passed"] = passed
    summary["total"] = len(slugs)
    summary["pass"] = passed == len(slugs)
    return summary


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="E2E-B-EDU-BATCH 六款品类批量验收")
    parser.add_argument(
        "api",
        nargs="?",
        default=DEFAULT_API,
        help=f"Backend API base URL (default: {DEFAULT_API})",
    )
    parser.add_argument(
        "--api",
        dest="api_flag",
        default=None,
        help="Backend API base URL (overrides positional)",
    )
    parser.add_argument(
        "--slugs",
        default=DEFAULT_SLUGS,
        help=f"Comma-separated slugs (default: {DEFAULT_SLUGS})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    base: str = args.api_flag or args.api
    slugs: list[str] = [s.strip() for s in args.slugs.split(",") if s.strip()]
    print(f"E2E-B-EDU-BATCH @ {base} · slugs={','.join(slugs)}")
    try:
        summary = run_batch(base, slugs)
        print("\n=== SUMMARY ===")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"\n{summary['passed']}/{summary['total']} PASS")
        return 0 if summary.get("pass") else 1
    except (AssertionError, ValueError) as exc:
        print(f"E2E 失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
