#!/usr/bin/env python3
"""Headless Godot smoke for seven E2E keep workspaces."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402

IDS = {
    "platformer": "55e85168-4ce2-4bca-b5e4-a83286eba64e",
    "shmup": "17a7b14c-bf07-4e16-b307-ce1e48d00b28",
    "survivor": "b0ff9628-34ee-47dc-91e1-aa356f67c5e6",
    "pingpong": "bde18663-5080-41d9-bfe4-78f382b48b0a",
    "fighting": "f96b46f8-323f-41ba-b8c5-33fb2b2b117d",
    "parkour": "bdd5178a-a2a7-4d2f-a491-d77b2aa00ca7",
    "racing": "b6041d30-d69f-418b-9de4-84b185f5b753",
}


def main() -> int:
    settings = get_settings()
    godot = str(settings.godot_path)
    ws = Path(__file__).resolve().parents[1] / "workspace"
    print("GODOT", godot)
    passed = 0
    for genre, sid in IDS.items():
        root = ws / sid
        if not (root / "project.godot").is_file():
            print(f"[FAIL] {genre} missing project {root}")
            continue
        cmd = [godot, "--path", str(root), "--headless", "--quit-after", "90"]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
            )
        except subprocess.TimeoutExpired:
            print(f"[FAIL] {genre} timeout")
            continue
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        real = [ln for ln in out.splitlines() if re.search(r"\bERROR\b|SCRIPT ERROR", ln)]
        # ignore pure WARNING lines
        real = [ln for ln in real if "WARNING" not in ln]
        ok = len(real) == 0
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {genre} rc={proc.returncode} errors={len(real)}")
        for err in real[:4]:
            print(" ", err)
    print(f"DONE {passed}/{len(IDS)}")
    return 0 if passed == len(IDS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
