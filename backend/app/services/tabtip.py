from __future__ import annotations

import platform
import subprocess
from pathlib import Path

if platform.system() == "Windows":
    try:
        from app.services import tabtip_native
    except ImportError:
        tabtip_native = None  # type: ignore[assignment,misc]
else:
    tabtip_native = None  # type: ignore[assignment,misc]

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _run_powershell_show(provider: str) -> dict[str, object]:
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
        "path": "powershell",
    }


def show_windows_touch_keyboard(provider: str = "auto") -> dict[str, object]:
    """Show touch keyboard · fast in-process TabTip on Windows."""
    if platform.system() != "Windows":
        return {"ok": False, "reason": "non_windows"}

    if provider == "sogou_hand":
        return _run_powershell_show(provider)

    if tabtip_native is None:
        return _run_powershell_show(provider)

    try:
        result = tabtip_native.apply_keyboard_state("show")
        result["path"] = "native"
        result["provider"] = "tabtip"
        return result
    except Exception as exc:  # noqa: BLE001 — kiosk fallback must not crash API
        fallback = _run_powershell_show(provider)
        fallback["native_error"] = str(exc)[:120]
        return fallback


def hide_windows_touch_keyboard() -> dict[str, object]:
    """Hide TabTip touch keyboard when visible."""
    if platform.system() != "Windows":
        return {"ok": False, "reason": "non_windows"}

    if tabtip_native is None:
        script = _repo_root() / "05-工具脚本" / "hide_touch_keyboard.ps1"
        if not script.is_file():
            return {"ok": False, "reason": "script_missing"}
        try:
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script),
                ],
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as sub_exc:
            return {"ok": False, "reason": "invoke_failed", "detail": str(sub_exc)}
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "action": "hide",
            "path": "powershell",
        }

    try:
        result = tabtip_native.apply_keyboard_state("hide")
        result["path"] = "native"
        return result
    except Exception as exc:  # noqa: BLE001
        script = _repo_root() / "05-工具脚本" / "hide_touch_keyboard.ps1"
        if not script.is_file():
            return {"ok": False, "reason": "script_missing", "detail": str(exc)}

        try:
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script),
                ],
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as sub_exc:
            return {"ok": False, "reason": "invoke_failed", "detail": str(sub_exc)}

        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "action": "hide",
            "path": "powershell",
            "native_error": str(exc)[:120],
        }


def warm_windows_touch_keyboard() -> dict[str, object]:
    if platform.system() != "Windows":
        return {"ok": False, "reason": "non_windows"}
    if tabtip_native is None:
        return {"ok": False, "reason": "native_unavailable"}
    try:
        result = tabtip_native.warm_tabtip()
        result["path"] = "native"
        return result
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": "warm_failed", "detail": str(exc)[:120]}
