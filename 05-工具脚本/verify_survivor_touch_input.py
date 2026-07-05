#!/usr/bin/env python3
"""验证 survivor 触控 overlay 注入与静态约束。"""
from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings
from app.services.edu_workspace import SURVIVOR_TOUCH_FILENAME, apply_edu_workspace_patch
from app.services.workspace import copy_template_to_workspace

OVERLAY: Path = ROOT / "templates" / "_edu" / "survivor_touch_overlay.gd"


def main() -> int:
    text: str = OVERLAY.read_text(encoding="utf-8")
    checks: list[tuple[str, bool]] = [
        ("ScreenTouch 多点", "InputEventScreenTouch" in text),
        ("摇杆 move_*", '"move_left"' in text and "Input.action_press(action, strength)" in text),
        ("无瞄准 UI", "瞄准" not in text and "AimZone" not in text),
        ("左下摇杆布局", "PRESET_BOTTOM_LEFT" in text and "JOY_SIZE" in text),
        ("升级选卡隐藏", "LevelUpUI" in text),
        ("圆角样式", "set_corner_radius_all" in text),
    ]
    print("=== survivor_touch_overlay.gd 静态检查 ===")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not all(ok for _, ok in checks):
        return 1

    settings = Settings()
    session_id: str = str(uuid.uuid4())
    workspace = copy_template_to_workspace(
        settings.templates_dir,
        settings.workspace_dir,
        "survivor",
        session_id,
    )
    try:
        ok_patch: bool = apply_edu_workspace_patch(
            workspace,
            "survivor",
            settings.templates_dir,
            settings.workspace_dir,
        )
        assert ok_patch
        assert (workspace / "core" / SURVIVOR_TOUCH_FILENAME).is_file()
        main_tscn: str = (workspace / "scenes" / "main.tscn").read_text(encoding="utf-8")
        assert "SurvivorTouch" in main_tscn
        print("  [PASS] workspace 注入 SurvivorTouch")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    print()
    print("=== 人工验收提示 ===")
    print("  B7 重新 launch · 左下摇杆移动 · 右侧瞄准射击 ≥1 分钟")
    print("  升级选卡界面可点 · 演示钮仍可用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
