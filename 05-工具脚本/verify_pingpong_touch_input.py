#!/usr/bin/env python3
"""验证 pingpong 触控 overlay 注入与静态约束。"""
from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings
from app.services.edu_workspace import PINGPONG_TOUCH_FILENAME, apply_edu_workspace_patch
from app.services.workspace import copy_template_to_workspace

OVERLAY: Path = ROOT / "templates" / "_edu" / "pingpong_touch_overlay.gd"


def main() -> int:
    text: str = OVERLAY.read_text(encoding="utf-8")
    checks: list[tuple[str, bool]] = [
        ("ScreenTouch 拖动", "InputEventScreenTouch" in text),
        ("ScreenDrag 跟随", "InputEventScreenDrag" in text),
        ("直接设 position.y", "paddle.position.y" in text),
        ("拖动时禁用 paddle 输入", "set_input_enabled" in text),
        ("无 action_press 注入", "action_press" not in text),
        ("无 warp_mouse 注入", "warp_mouse" not in text),
        ("无 Button", "Button.new()" not in text),
        ("无虚拟键 UI", "PanelContainer.new()" not in text and "Label.new()" not in text),
        ("透明 DragPad", "DragPad" in text),
    ]
    print("=== pingpong_touch_overlay.gd 静态检查 ===")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not all(ok for _, ok in checks):
        return 1

    settings = Settings()
    session_id: str = str(uuid.uuid4())
    workspace = copy_template_to_workspace(
        settings.templates_dir,
        settings.workspace_dir,
        "pingpong",
        session_id,
    )
    try:
        ok_patch: bool = apply_edu_workspace_patch(
            workspace,
            "pingpong",
            settings.templates_dir,
            settings.workspace_dir,
        )
        assert ok_patch
        assert (workspace / "core" / PINGPONG_TOUCH_FILENAME).is_file()
        main_tscn: str = (workspace / "scenes" / "main.tscn").read_text(encoding="utf-8")
        assert "PingpongTouch" in main_tscn
        print("  [PASS] workspace 注入 PingpongTouch")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    print()
    print("=== 人工验收提示 ===")
    print("  B7 重新 launch · 全屏拖动 · 球拍 Y 与触点即时对齐")
    print("  无 action/warp 注入 · 击球音效不应被截断")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
