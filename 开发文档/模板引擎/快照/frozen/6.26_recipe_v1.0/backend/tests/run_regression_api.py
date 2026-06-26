"""One-shot API regression for P0-B backend (run: python tests/run_regression_api.py)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import create_app

INTENT_CASES: list[tuple[str, str]] = [
    ("我想玩马里奥", "platformer"),
    ("打飞机", "shmup"),
    ("割草升级", "survivor"),
    ("乒乓球", "pingpong"),
    ("格斗双人", "fighting"),
    ("跑酷", "parkour"),
    ("赛车", "racing"),
]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def main() -> None:
    passed: int = 0
    with TestClient(create_app()) as client:
        _run_checks(client, passed_holder := [0])
        passed = passed_holder[0]
    print(f"\n=== REGRESSION PASSED: {passed} checks ===")


def _run_checks(client: TestClient, passed_holder: list[int]) -> None:
    passed: int = passed_holder[0]

    r = client.get("/health")
    if r.status_code != 200:
        fail(f"GET /health -> {r.status_code}")
    ok("GET /health")
    passed += 1

    r = client.get("/bootstrap")
    if r.status_code != 200:
        fail(f"GET /bootstrap -> {r.status_code}")
    body: dict[str, Any] = r.json()
    if not body.get("ready"):
        print(f"WARN: bootstrap ready=false: {body.get('messages')}")
    ok("GET /bootstrap")
    passed += 1

    for text, expected_genre in INTENT_CASES:
        s = client.post("/sessions")
        if s.status_code != 201:
            fail(f"POST /sessions -> {s.status_code}")
        sid: str = s.json()["session_id"]
        r = client.post(
            "/intent/match-genre",
            json={"text": text, "session_id": sid},
        )
        if r.status_code != 200:
            fail(f"intent '{text}' -> {r.status_code} {r.text}")
        data = r.json()
        if data.get("matched_genre") != expected_genre:
            fail(f"intent '{text}' expected {expected_genre}, got {data.get('matched_genre')}")
        if data.get("llm_patch_required") if "llm_patch_required" in data else False:
            fail("intent response must not require llm_patch")
        ok(f"intent '{text}' -> {expected_genre} (confidence={data.get('confidence')})")
        passed += 1

    r = client.post("/intent/match-genre", json={"text": "", "session_id": "00000000-0000-4000-8000-000000000001"})
    if r.status_code != 400:
        fail(f"empty intent text expected 400, got {r.status_code}")
    ok("intent empty text -> 400")
    passed += 1

    s = client.post("/sessions")
    sid = s.json()["session_id"]
    client.post("/intent/match-genre", json={"text": "马里奥闯关", "session_id": sid})

    r = client.get("/creative/templates/platformer")
    if r.status_code != 200 or r.json().get("genre") != "platformer":
        fail(f"GET creative template -> {r.status_code}")
    ok("GET /creative/templates/platformer")
    passed += 1

    r = client.get("/creative/name-suggestions", params={"genre": "platformer"})
    if r.status_code != 200 or not r.json().get("suggestions"):
        fail("name-suggestions empty or error")
    ok("GET /creative/name-suggestions")
    passed += 1

    r = client.get("/creative/templates/shmup")
    if r.status_code != 200 or r.json().get("genre") != "shmup":
        fail(f"shmup template expected 200, got {r.status_code} {r.text[:120]}")
    ok("GET /creative/templates/shmup")
    passed += 1

    answers = {
        "q_move": "fast",
        "q_jump": "high",
        "q_enemy": "hard",
        "q_lives": "high",
        "q_coin": "high",
    }
    r = client.post(f"/sessions/{sid}/creative/answers", json={"answers": answers})
    if r.status_code != 200:
        fail(f"creative answers -> {r.status_code} {r.text}")
    ok("POST creative/answers")
    passed += 1

    r = client.post(f"/sessions/{sid}/analyze-requirements")
    if r.status_code != 200:
        fail(f"analyze -> {r.status_code} {r.text}")
    analyze = r.json()
    if analyze.get("llm_patch_required") is not False:
        fail("analyze llm_patch_required must be false")
    if len(analyze.get("resolutions", [])) < 3:
        fail(f"analyze resolutions too few: {analyze.get('resolutions')}")
    if "jump" not in analyze.get("code_map_preview", {}):
        fail("code_map_preview missing jump anchor")
    ok(f"POST analyze-requirements ({len(analyze['resolutions'])} resolutions, llm_patch=false)")
    passed += 1

    s2 = client.post("/sessions").json()["session_id"]
    client.post("/intent/match-genre", json={"text": "马里奥", "session_id": s2})
    r = client.post(f"/sessions/{s2}/generate/v2")
    if r.status_code != 400:
        fail(f"generate/v2 without analyze expected 400, got {r.status_code}")
    ok("generate/v2 without analyze -> 400")
    passed += 1

    r = client.post(f"/sessions/{sid}/generate/v2")
    if r.status_code != 200:
        fail(f"generate/v2 -> {r.status_code} {r.text}")
    gen = r.json()
    if not gen.get("ok"):
        fail("generate/v2 ok=false")
    cfg_path = Path(gen["config_path"])
    if not cfg_path.is_file():
        fail(f"config not found: {cfg_path}")
    merged = json.loads(cfg_path.read_text(encoding="utf-8"))
    if merged["tuning"]["player"]["move_speed"] != 240:
        fail(f"move_speed mismatch: {merged['tuning']['player']['move_speed']}")
    if merged["tuning"]["player"]["jump_velocity"] != -440:
        fail(f"jump_velocity mismatch")
    if "templates" in str(cfg_path.resolve()).replace("\\", "/").split("/")[-3:]:
        fail("config written under templates/")
    if "jump" not in gen.get("code_map", {}):
        fail("generate code_map missing jump")
    ok("POST generate/v2 + workspace config merge")
    passed += 1

    s3 = client.post("/sessions").json()["session_id"]
    r = client.post(f"/sessions/{s3}/generate")
    if r.status_code != 400:
        fail(f"v1 generate without recap expected 400, got {r.status_code}")
    ok("v1 /generate without recap -> 400 (legacy path preserved)")
    passed += 1

    passed_holder[0] = passed


if __name__ == "__main__":
    main()
