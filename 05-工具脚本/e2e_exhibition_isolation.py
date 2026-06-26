#!/usr/bin/env python3
"""E2E-EXHIBITION-ISOLATION · 展陈 P0 窗14 · 3 用户 workspace 隔离验收."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parents[1]
DEFAULT_API: str = "http://127.0.0.1:8000"
CASE_ID: str = "E2E-EXHIBITION-ISOLATION"
DISPLAY_A: str = "展陈隔离用户A_7f3a"
DISPLAY_C: str = "展陈隔离用户C_9b2e"


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


def snapshot_template_hashes() -> dict[str, str]:
    """记录 templates/ 内关键文件哈希，用于断言 generate 零写入。"""
    hashes: dict[str, str] = {}
    templates_root: Path = ROOT / "templates"
    if not templates_root.is_dir():
        return hashes
    for path in templates_root.rglob("game_config.json"):
        if path.is_file():
            rel: str = path.relative_to(ROOT).as_posix()
            hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in templates_root.rglob("project.godot"):
        if path.is_file():
            rel = path.relative_to(ROOT).as_posix()
            hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def assert_templates_unchanged(before: dict[str, str]) -> None:
    after: dict[str, str] = snapshot_template_hashes()
    changed: list[str] = [
        rel for rel, digest in before.items() if after.get(rel) != digest
    ]
    assert_ok(
        "templates_zero_write_runtime",
        not changed,
        ", ".join(changed) if changed else f"{len(before)} template files unchanged",
    )


def warn_templates_git_clean() -> None:
    """展前门禁：git diff templates/ 应为空（仅告警，不阻断开发机脏工作区）。"""
    proc = subprocess.run(
        ["git", "diff", "--name-only", "templates/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    changed: str = proc.stdout.strip()
    if changed:
        print(f"  [WARN] templates git diff 非空（展前须清零）: {changed.replace(chr(10), ', ')}")
    else:
        print("  [INFO] templates git diff 为空 · 展前门禁 OK")


def platformer_generate(base: str, session_id: str, display_name: str) -> dict[str, Any]:
    steps: list[tuple[str, dict[str, Any]]] = [
        ("S0", {"display_name": display_name}),
        ("S1", {"genre": "platformer"}),
        ("S2", {"play_variant_id": "default"}),
        ("S3", {"style_pack": "default", "mood_keywords": ["冒险"]}),
        ("S4", {"character": {"name": "测试", "color": "#ff6b6b"}}),
        ("S5", {"props": ["star", "coin"]}),
        ("S6", {"feel_id": "challenge"}),
        ("S7", {"enabled_skills": ["double_jump"]}),
    ]
    for step_id, data in steps:
        st, payload = api_call(
            base,
            "POST",
            f"/sessions/{session_id}/wizard/{step_id}",
            {"data": data},
        )
        assert_ok(f"wizard_{step_id}", st == 200, str(payload)[:160])

    st, recap = api_call(base, "POST", f"/sessions/{session_id}/recap")
    assert_ok("recap", st == 200, str(recap)[:120])

    st, gen = api_call(base, "POST", f"/sessions/{session_id}/generate")
    assert_ok("generate", st == 200 and gen.get("ok") is True, str(gen)[:200])  # type: ignore[union-attr]
    return gen if isinstance(gen, dict) else {}  # type: ignore[return-value]


def read_workspace_config(session_id: str) -> dict[str, Any]:
    path: Path = ROOT / "workspace" / session_id / "config" / "game_config.json"
    assert_ok("workspace_config_exists", path.is_file(), str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def run_isolation_e2e(base: str) -> dict[str, Any]:
    results: dict[str, Any] = {"case_id": CASE_ID, "assertions": {}}
    print(f"\n=== {CASE_ID} · 展陈隔离 ===\n")

    template_hashes_before: dict[str, str] = snapshot_template_hashes()
    warn_templates_git_clean()

    st, boot = api_call(base, "GET", "/bootstrap")
    assert_ok("bootstrap_ready", st == 200 and boot.get("ready") is True, str(boot)[:120])  # type: ignore[union-attr]

    # --- 用户 A：platformer generate + 独特 display_name ---
    st, created_a = api_call(base, "POST", "/sessions")
    assert_ok("user_a_create", st == 201, str(created_a))
    sid_a: str = str(created_a["session_id"])  # type: ignore[index]
    results["session_a"] = sid_a
    print(f"  用户 A session: {sid_a[:8]}…")

    platformer_generate(base, sid_a, DISPLAY_A)
    cfg_a = read_workspace_config(sid_a)
    assert_ok(
        "user_a_display_name",
        cfg_a.get("meta", {}).get("display_name") == DISPLAY_A,
        str(cfg_a.get("meta", {})),
    )
    skills_a: list[str] = cfg_a.get("tuning", {}).get("enabled_skills", [])
    assert_ok("user_a_tuning", "double_jump" in skills_a, str(skills_a))

    ws_a: Path = ROOT / "workspace" / sid_a
    assert_ok("user_a_workspace_path", ws_a.is_dir() and "workspace" in str(ws_a), str(ws_a))

    # --- release A ---
    st, released = api_call(base, "POST", f"/sessions/{sid_a}/release")
    assert_ok(
        "user_a_release",
        st == 200 and released.get("deleted") is True and released.get("workspace_removed") is True,  # type: ignore[union-attr]
        str(released),
    )
    assert_ok("user_a_workspace_gone", not ws_a.exists(), str(ws_a))

    st, _gone = api_call(base, "GET", f"/sessions/{sid_a}")
    assert_ok("user_a_session_gone", st == 404, str(_gone)[:80])

    # --- bootstrap 孤儿清理：无活跃 session 的目录应被删 ---
    orphan_id: str = str(uuid.uuid4())
    orphan_dir: Path = ROOT / "workspace" / orphan_id
    orphan_dir.mkdir(parents=True, exist_ok=True)
    (orphan_dir / ".orphan_marker").write_text("simulated crash", encoding="utf-8")
    st, refresh = api_call(base, "POST", "/bootstrap/refresh")
    removed: list[str] = refresh.get("orphan_workspaces_removed", []) if isinstance(refresh, dict) else []  # type: ignore[union-attr]
    assert_ok(
        "bootstrap_orphan_cleanup",
        st == 200 and orphan_id in removed and not orphan_dir.exists(),
        f"removed={removed}",
    )

    # --- 用户 B：新 session 不得读到 A 的 meta/display_name/tuning ---
    st, created_b = api_call(base, "POST", "/sessions")
    assert_ok("user_b_create", st == 201, str(created_b))
    sid_b: str = str(created_b["session_id"])  # type: ignore[index]
    results["session_b"] = sid_b
    assert_ok("user_b_distinct_id", sid_b != sid_a, f"{sid_b} vs {sid_a}")
    print(f"  用户 B session: {sid_b[:8]}…")

    st, session_b = api_call(base, "GET", f"/sessions/{sid_b}")
    assert_ok("user_b_session_record", st == 200, str(session_b)[:120])
    assert_ok(
        "user_b_no_a_display_name",
        session_b.get("display_name", "") != DISPLAY_A,  # type: ignore[union-attr]
        str(session_b.get("display_name", "")),  # type: ignore[union-attr]
    )

    st, cfg_b_api = api_call(base, "GET", f"/sessions/{sid_b}/workspace/game-config")
    assert_ok("user_b_no_workspace_yet", st == 404, str(cfg_b_api)[:120])

    st, cfg_a_leak = api_call(base, "GET", f"/sessions/{sid_a}/workspace/game-config")
    assert_ok("user_a_config_inaccessible", st == 404, str(cfg_a_leak)[:80])

    ws_b_before: Path = ROOT / "workspace" / sid_b
    assert_ok("user_b_no_workspace_dir", not ws_b_before.exists(), str(ws_b_before))

    # --- 用户 C：第三位用户 generate 后路径隔离 ---
    st, created_c = api_call(base, "POST", "/sessions")
    assert_ok("user_c_create", st == 201, str(created_c))
    sid_c: str = str(created_c["session_id"])  # type: ignore[index]
    results["session_c"] = sid_c
    print(f"  用户 C session: {sid_c[:8]}…")

    platformer_generate(base, sid_c, DISPLAY_C)
    cfg_c = read_workspace_config(sid_c)
    assert_ok(
        "user_c_own_display_name",
        cfg_c.get("meta", {}).get("display_name") == DISPLAY_C,
        str(cfg_c.get("meta", {})),
    )
    assert_ok(
        "user_c_not_a_display_name",
        cfg_c.get("meta", {}).get("display_name") != DISPLAY_A,
        DISPLAY_A,
    )

    ws_c: Path = ROOT / "workspace" / sid_c
    assert_ok("user_c_workspace_isolated", ws_c.is_dir() and not ws_a.exists(), str(ws_c))
    assert_ok(
        "workspace_paths_distinct",
        sid_a != sid_b != sid_c and ws_c != ws_b_before,
        f"A={sid_a[:8]} B={sid_b[:8]} C={sid_c[:8]}",
    )

    # 清理 C（模拟 release）
    st, _ = api_call(base, "POST", f"/sessions/{sid_c}/release")
    assert_ok("user_c_release", st == 200, str(_))
    st, _ = api_call(base, "POST", f"/sessions/{sid_b}/release")
    assert_ok("user_b_release", st == 200, str(_))

    assert_templates_unchanged(template_hashes_before)

    results["assertions"] = {
        "templates_zero_write_runtime": True,
        "user_a_generate_release": True,
        "bootstrap_orphan_cleanup": True,
        "user_b_no_leak": True,
        "user_c_path_isolation": True,
    }
    print(f"\n=== {CASE_ID} · ALL PASS ===\n")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=CASE_ID)
    parser.add_argument("api_base", nargs="?", default=DEFAULT_API)
    args = parser.parse_args()
    try:
        run_isolation_e2e(args.api_base.rstrip("/"))
        return 0
    except AssertionError as exc:
        print(f"\n=== {CASE_ID} · FAILED ===\n{exc}\n", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"API unreachable: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
