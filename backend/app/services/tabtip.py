from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def show_windows_touch_keyboard(provider: str = "auto") -> dict[str, object]:
    """Invoke touch keyboard helper on Windows kiosk hosts."""
    if platform.system() != "Windows":
        return {"ok": False, "reason": "non_windows"}

    script = _repo_root() / "05-工具脚本" / "show_touch_keyboard.ps1"
    legacy = _repo_root() / "05-工具脚本" / "show_tabtip.ps1"
    if not script.is_file() and legacy.is_file():
        script = legacy

    if not script.is_file():
        return {"ok": False, "reason": "script_missing", "path": str(script)}

    mode = provider if provider in {"auto", "tabtip", "sogou_hand"} else "auto"

    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-Provider",
                mode,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "reason": "invoke_failed", "detail": str(exc)}

    stdout = (completed.stdout or "").strip()
    meta: dict[str, str] = {}
    if stdout:
        for line in stdout.splitlines():
            for part in line.split(";"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    meta[key.strip()] = value.strip()

    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "provider": meta.get("provider", mode),
        "ime": meta.get("ime"),
        "sogou": meta.get("sogou"),
        "stderr": (completed.stderr or "").strip()[:240],
    }
