#!/usr/bin/env python3
"""E2E-B-001 · platformer L1 个性化链路验收脚本（线 B · B6 准备）."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parents[1]
DEFAULT_API: str = "http://127.0.0.1:8000"


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
        with urllib.request.urlopen(request, timeout=30) as resp:
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


def run_e2e_b001(base: str) -> dict[str, Any]:
    results: dict[str, Any] = {"case_id": "E2E-B-001", "assertions": {}}

    status, created = api_call(base, "POST", "/sessions")
    assert_ok("create_session", status == 201, str(created))
    session_id: str = str(created["session_id"])  # type: ignore[index]
    results["session_id"] = session_id

    steps: list[tuple[str, dict[str, Any]]] = [
        ("S0", {"display_name": "小明的星星冒险"}),
        ("S1", {"genre": "platformer"}),
        ("S2", {"play_variant_id": "default"}),
        ("S3", {"style_pack": "default", "mood_keywords": ["冒险"]}),
        ("S4", {"character": {"name": "小明", "color": "#ff6b6b"}}),
        ("S5", {"props": ["star", "coin"]}),
        ("S6", {"feel_id": "challenge"}),
        ("S7", {"enabled_skills": ["double_jump"]}),
    ]
    for step_id, data in steps:
        st, payload = api_call(base, "POST", f"/sessions/{session_id}/wizard/{step_id}", {"data": data})
        assert_ok(f"wizard_{step_id}", st == 200, str(payload)[:200])

    st, recap = api_call(base, "POST", f"/sessions/{session_id}/recap")
    assert_ok("recap_confirm", st == 200, str(recap.get("display_name", "")))  # type: ignore[union-attr]

    st, gen = api_call(base, "POST", f"/sessions/{session_id}/generate")
    assert_ok("generate", st == 200 and gen.get("ok") is True, str(gen))  # type: ignore[union-attr]
    results["generate"] = gen

    config_path: Path = ROOT / "workspace" / session_id / "config" / "game_config.json"
    assert_ok("A1_filesystem", config_path.is_file(), str(config_path))
    config: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))

    assert_ok("A2_display_name", config.get("meta", {}).get("display_name") == "小明的星星冒险")
    assert_ok("A3_theme_title", config.get("theme", {}).get("title") == "小明的星星冒险")
    skills: list[str] = config.get("tuning", {}).get("enabled_skills", [])
    assert_ok("A4_enabled_skills", "double_jump" in skills, str(skills))

    base_template: dict[str, Any] = json.loads(
        (ROOT / "templates" / "platformer" / "config" / "game_config.json").read_text(encoding="utf-8")
    )
    balanced_speed: float = float(base_template["tuning"]["player"]["move_speed"])
    challenge_speed: float = float(config["tuning"]["player"]["move_speed"])
    assert_ok(
        "A5_tuning_delta",
        challenge_speed > balanced_speed,
        f"move_speed {challenge_speed} vs base {balanced_speed}",
    )

    st, launch = api_call(base, "POST", f"/sessions/{session_id}/play/launch")
    project_path: str = str(launch.get("project_path", ""))  # type: ignore[union-attr]
    assert_ok(
        "A6_launch_workspace",
        st == 200 and launch.get("ok") is True and "workspace" in project_path,  # type: ignore[union-attr]
        project_path,
    )

    results["assertions"] = {
        "A1": config_path.is_file(),
        "A2": config.get("meta", {}).get("display_name") == "小明的星星冒险",
        "A3": config.get("theme", {}).get("title") == "小明的星星冒险",
        "A4": "double_jump" in skills,
        "A5": challenge_speed > balanced_speed,
        "A6": "workspace" in project_path,
        "A7": "manual_play — 标题/HUD/双跳/手感需人工 120s",
        "A8": "mcp run_project — 可选 MCP 验证",
    }
    results["pass"] = all(v is True for k, v in results["assertions"].items() if k.startswith("A") and k != "A7" and k != "A8")
    return results


def main() -> int:
    base: str = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_API
    print(f"E2E-B-001 @ {base}")
    try:
        summary = run_e2e_b001(base)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary.get("pass") else 1
    except AssertionError as exc:
        print(f"E2E 失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
