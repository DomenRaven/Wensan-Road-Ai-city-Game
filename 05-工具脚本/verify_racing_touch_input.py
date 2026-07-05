#!/usr/bin/env python3
"""验证 racing 触控 overlay 注入与静态约束。"""
from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings
from app.services.edu_workspace import RACING_TOUCH_FILENAME, apply_edu_workspace_patch
from app.services.workspace import copy_template_to_workspace

OVERLAY: Path = ROOT / "templates" / "_edu" / "racing_touch_overlay.gd"


def main() -> int:
    text: str = OVERLAY.read_text(encoding="utf-8")
    checks: list[tuple[str, bool]] = [
        ("ScreenTouch 多点", "InputEventScreenTouch" in text),
        ("底部三键", '"steer_left"' in text and '"steer_right"' in text and '"skill"' in text),
        ("贴底布局", "PRESET_BOTTOM_LEFT" in text and "PRESET_BOTTOM_RIGHT" in text),
        ("非全屏半屏", "PRESET_LEFT_WIDE" not in text and "PRESET_RIGHT_WIDE" not in text),
        ("圆角胶囊", "set_corner_radius_all" in text),
        ("无 Button", "Button.new()" not in text),
        ("失焦释放", "NOTIFICATION_WM_WINDOW_FOCUS_OUT" in text),
    ]
    print("=== racing_touch_overlay.gd 静态检查 ===")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not all(ok for _, ok in checks):
        return 1

    settings = Settings()
    session_id: str = str(uuid.uuid4())
    workspace = copy_template_to_workspace(
        settings.templates_dir,
        settings.workspace_dir,
        "racing",
        session_id,
    )
    try:
        ok_patch: bool = apply_edu_workspace_patch(
            workspace,
            "racing",
            settings.templates_dir,
            settings.workspace_dir,
        )
        assert ok_patch
        assert (workspace / "core" / RACING_TOUCH_FILENAME).is_file()
        main_tscn: str = (workspace / "scenes" / "main.tscn").read_text(encoding="utf-8")
        assert "RacingTouch" in main_tscn
        assert 'parent="GameHost/GameViewport/CanvasLayer"' in main_tscn
        print("  [PASS] workspace 注入 RacingTouch（SubViewport CanvasLayer）")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    print()
    print("=== 人工验收提示 ===")
    print("  重启后端 + B7 重新 launch")
    print("  底部三键：左 ← · 左旁 → · 右 加速（hold）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
