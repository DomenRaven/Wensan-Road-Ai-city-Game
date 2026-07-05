#!/usr/bin/env python3
"""验证 fighting 触控 overlay 注入与静态约束。"""
from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings
from app.services.edu_workspace import FIGHTING_TOUCH_FILENAME, apply_edu_workspace_patch
from app.services.workspace import copy_template_to_workspace

OVERLAY: Path = ROOT / "templates" / "_edu" / "fighting_touch_overlay.gd"


def main() -> int:
    text: str = OVERLAY.read_text(encoding="utf-8")
    checks: list[tuple[str, bool]] = [
        ("ScreenTouch 多点", "InputEventScreenTouch" in text),
        ("P1 六键 action", all(
            action in text
            for action in (
                "p1_left",
                "p1_right",
                "p1_light",
                "p1_heavy",
                "p1_block",
                "p1_ultimate",
            )
        )),
        ("P2 六键 action", all(
            action in text
            for action in (
                "p2_left",
                "p2_right",
                "p2_light",
                "p2_heavy",
                "p2_block",
                "p2_ultimate",
            )
        )),
        ("PvP 双套布局", "PvpPad" in text and "_is_pvp_mode" in text),
        ("PvP 紧凑尺寸", "BTN_SIZE_PVP" in text),
        ("tap 物理帧释放", "_physics_process" in text and "_tap_release_pending" in text),
        ("贴底布局", "PRESET_BOTTOM_LEFT" in text and "PRESET_BOTTOM_RIGHT" in text),
        ("非固定 y 坐标", "292" not in text),
        ("圆角胶囊", "set_corner_radius_all" in text),
        ("无 Button", "Button.new()" not in text),
        ("BattleHUD 显隐", "BattleHUD" in text),
        ("失焦释放", "NOTIFICATION_WM_WINDOW_FOCUS_OUT" in text),
    ]
    print("=== fighting_touch_overlay.gd 静态检查 ===")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not all(ok for _, ok in checks):
        return 1

    settings = Settings()
    session_id: str = str(uuid.uuid4())
    workspace = copy_template_to_workspace(
        settings.templates_dir,
        settings.workspace_dir,
        "fighting",
        session_id,
    )
    try:
        ok_patch: bool = apply_edu_workspace_patch(
            workspace,
            "fighting",
            settings.templates_dir,
            settings.workspace_dir,
        )
        assert ok_patch
        assert (workspace / "core" / FIGHTING_TOUCH_FILENAME).is_file()
        main_tscn: str = (workspace / "scenes" / "main.tscn").read_text(encoding="utf-8")
        assert "FightingTouch" in main_tscn
        assert 'parent="CanvasLayer"' in main_tscn
        print("  [PASS] workspace 注入 FightingTouch（根级 CanvasLayer）")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    hooks_text: str = (ROOT / "templates" / "_edu" / "fighting_hooks.gd").read_text(encoding="utf-8")
    mute_ok: bool = "set_bus_mute" in hooks_text and "_mute_exhibition_audio" in hooks_text
    print(f"  [{'PASS' if mute_ok else 'FAIL'}] fighting_hooks 展厅静音")
    if not mute_ok:
        return 1

    print()
    print("=== 人工验收提示 ===")
    print("  重启后端 + B7 重新 launch")
    print("  PvE：无键盘打完 1 局 · 六键贴底 · 无音效")
    print("  PvP：屏下左右各一套紧凑六键 · 双指可同时操作")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
