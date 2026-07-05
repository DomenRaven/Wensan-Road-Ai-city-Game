#!/usr/bin/env python3
"""验证 parkour 触控 overlay 注入与静态约束。"""
from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings
from app.services.edu_workspace import PARKOUR_TOUCH_FILENAME, apply_edu_workspace_patch
from app.services.workspace import copy_template_to_workspace

OVERLAY: Path = ROOT / "templates" / "_edu" / "parkour_touch_overlay.gd"


def main() -> int:
    text: str = OVERLAY.read_text(encoding="utf-8")
    checks: list[tuple[str, bool]] = [
        ("ScreenTouch 多点", "InputEventScreenTouch" in text),
        ("jump 物理帧释放", "_physics_process" in text and "_jump_release_pending" in text),
        ("skill hold", '"skill"' in text and "action_release(action)" in text),
        ("无 Button", "Button.new()" not in text),
        ("贴底左右布局", "PRESET_BOTTOM_LEFT" in text and "PRESET_BOTTOM_RIGHT" in text),
        ("圆角样式", "set_corner_radius_all" in text),
    ]
    print("=== parkour_touch_overlay.gd 静态检查 ===")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not all(ok for _, ok in checks):
        return 1

    settings = Settings()
    session_id: str = str(uuid.uuid4())
    workspace = copy_template_to_workspace(
        settings.templates_dir,
        settings.workspace_dir,
        "parkour",
        session_id,
    )
    try:
        ok_patch: bool = apply_edu_workspace_patch(
            workspace,
            "parkour",
            settings.templates_dir,
            settings.workspace_dir,
        )
        assert ok_patch
        assert (workspace / "core" / PARKOUR_TOUCH_FILENAME).is_file()
        main_tscn: str = (workspace / "scenes" / "main.tscn").read_text(encoding="utf-8")
        assert "ParkourTouch" in main_tscn
        print("  [PASS] workspace 注入 ParkourTouch")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    print()
    print("=== 人工验收提示 ===")
    print("  B7 重新 launch · 跳过高障碍 · hold 滑铲过低障碍")
    print("  键盘对照：空格跳 · S/↓ hold 滑铲")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
