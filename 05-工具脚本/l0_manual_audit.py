#!/usr/bin/env python3
"""Automated pre-checks for L0 manual review (H1 + config sanity)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
TEMPLATES: Path = ROOT / "templates"
GODOT: Path = Path(
    r"F:\Godot\Godot_v4.6.3-stable_win64.exe\Godot_v4.6.3-stable_win64_console.exe"
)
ORDER: list[str] = [
    "platformer",
    "tower_defense",
    "shmup",
    "shooter",
    "survivor",
    "fighting",
    "parkour",
    "life_sim",
    "sports_race",
    "pingpong",
    "racing",
]


def run_smoke(genre: str) -> tuple[int, list[str]]:
    project: Path = TEMPLATES / genre
    if not GODOT.exists():
        return -1, [f"Godot not found: {GODOT}"]
    proc: subprocess.CompletedProcess[str] = subprocess.run(
        [str(GODOT), "--path", str(project), "--headless", "--quit-after", "2"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    combined: str = proc.stdout + proc.stderr
    errors: list[str] = [
        line.strip()
        for line in combined.splitlines()
        if "ERROR:" in line and "RemoteException" not in line
    ]
    return len(errors), errors[:8]


def read_config(genre: str) -> dict[str, object]:
    config_path: Path = TEMPLATES / genre / "config" / "game_config.json"
    data: dict[str, object] = json.loads(config_path.read_text(encoding="utf-8"))
    theme: dict[str, object] = data.get("theme", {}) if isinstance(data.get("theme"), dict) else {}
    safety: dict[str, object] = (
        data.get("content_safety", {}) if isinstance(data.get("content_safety"), dict) else {}
    )
    sounds: dict[str, object] = theme.get("sounds", {}) if isinstance(theme.get("sounds"), dict) else {}
    impact: dict[str, object] = sounds.get("impact", {}) if isinstance(sounds.get("impact"), dict) else {}
    interface: dict[str, object] = (
        sounds.get("interface", {}) if isinstance(sounds.get("interface"), dict) else {}
    )
    meta: dict[str, object] = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
    return {
        "display_name": meta.get("display_name", ""),
        "max_keys": safety.get("max_keys", 0),
        "impact_sound_keys": sorted(impact.keys()),
        "interface_sound_keys": sorted(interface.keys()),
        "has_theme_sounds": bool(sounds),
    }


def audit_genre(genre: str) -> dict[str, object]:
    err_count, err_samples = run_smoke(genre)
    cfg: dict[str, object] = read_config(genre)
    h1: str = "PASS" if err_count == 0 else "FAIL"
    h4: str = "PASS" if int(cfg.get("max_keys", 99)) <= 3 else "FAIL"
    audio_junction: Path = TEMPLATES / genre / "assets" / "kenney" / "impact-sounds"
    h5_partial: str = "PASS" if audio_junction.exists() else "WARN"
    return {
        "genre": genre,
        "h1_mcp_errors": h1,
        "error_count": err_count,
        "error_samples": err_samples,
        "h4_max_keys": h4,
        "h5_audio_junction": h5_partial,
        **cfg,
    }


def main() -> int:
    results: list[dict[str, object]] = [audit_genre(g) for g in ORDER]
    out: Path = ROOT / "开发文档" / "模板引擎" / "评审记录" / "_audit_autocheck_latest.json"
    payload: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "godot": str(GODOT),
        "results": results,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": sum(1 for r in results if r["h1_mcp_errors"] == "PASS"), "total": len(results), "out": str(out)}, ensure_ascii=False))
    for r in results:
        mark: str = "OK" if r["h1_mcp_errors"] == "PASS" else "FAIL"
        print(f"  {mark} {r['genre']:14} errors={r['error_count']} keys={r['max_keys']} sounds={r['has_theme_sounds']}")
    return 0 if all(r["h1_mcp_errors"] == "PASS" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
