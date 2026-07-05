#!/usr/bin/env python3
"""验证 platformer 触控 overlay 注入，并打印方向+跳跃同时按验收说明。"""
from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings
from app.services.edu_workspace import PLATFORMER_TOUCH_FILENAME, apply_edu_workspace_patch
from app.services.workspace import copy_template_to_workspace

OVERLAY: Path = ROOT / "templates" / "_edu" / "platformer_touch_overlay.gd"


def main() -> int:
    text: str = OVERLAY.read_text(encoding="utf-8")
    checks: list[tuple[str, bool]] = [
        ("ScreenTouch 多点", "InputEventScreenTouch" in text),
        ("跳跃 physics 帧释放", "_physics_process" in text and "_jump_release_pending" in text),
        ("方向 hold", 'action != "jump"' in text and "action_press(action)" in text),
        ("无 Button 单键互斥", "Button.new()" not in text),
    ]
    print("=== platformer_touch_overlay.gd 静态检查 ===")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not all(ok for _, ok in checks):
        return 1

    settings = Settings()
    session_id: str = str(uuid.uuid4())
    workspace = copy_template_to_workspace(
        settings.templates_dir,
        settings.workspace_dir,
        "platformer",
        session_id,
    )
    try:
        ok_patch: bool = apply_edu_workspace_patch(
            workspace,
            "platformer",
            settings.templates_dir,
            settings.workspace_dir,
        )
        assert ok_patch
        assert (workspace / "core" / PLATFORMER_TOUCH_FILENAME).is_file()
        main_tscn: str = (workspace / "scenes" / "main.tscn").read_text(encoding="utf-8")
        assert "PlatformerTouch" in main_tscn
        print("  [PASS] workspace 注入 PlatformerTouch")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    print()
    print("=== 方向 + 跳跃 同时按 · 验收说明 ===")
    print("  鼠标：单键无法同时按住方向再点跳（硬件限制），不代表触屏有问题。")
    print("  键盘对照：按住 D/→ 再按空格，应能跳过管道（默认 jump_velocity=-400）。")
    print("  触屏实机：一指按住 →，另一指点 跳，应能斜跳过管道。")
    print("  若键盘也跳不过：检查 B3 创作是否选了「跳跃低一点」（-360）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
