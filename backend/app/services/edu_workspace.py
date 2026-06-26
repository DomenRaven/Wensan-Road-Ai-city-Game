from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

from app.services.workspace_guard import assert_not_under_templates, assert_under_workspace

EDU_BRIDGE_FILENAME: str = "edu_action_bridge.gd"
FIGHTING_TOUCH_FILENAME: str = "fighting_touch_overlay.gd"
GENRE_HOOKS: dict[str, str] = {
    "platformer": "platformer_hooks.gd",
    "shmup": "shmup_hooks.gd",
    "survivor": "survivor_hooks.gd",
    "pingpong": "pingpong_hooks.gd",
    "fighting": "fighting_hooks.gd",
    "parkour": "parkour_hooks.gd",
    "racing": "racing_hooks.gd",
}


def apply_edu_workspace_patch(
    workspace_root: Path,
    genre: str,
    templates_dir: Path,
    workspace_dir: Path,
) -> bool:
    """Copy B7 edu bridge into workspace and patch project.godot / main.tscn. Returns True if applied."""
    hooks_filename: str | None = GENRE_HOOKS.get(genre)
    if hooks_filename is None:
        return False

    edu_dir: Path = templates_dir / "_edu"
    bridge_src: Path = edu_dir / EDU_BRIDGE_FILENAME
    hooks_src: Path = edu_dir / hooks_filename
    if not bridge_src.is_file() or not hooks_src.is_file():
        return False

    resolved_workspace: Path = workspace_root.resolve()
    assert_under_workspace(resolved_workspace, workspace_dir.resolve())
    assert_not_under_templates(resolved_workspace, templates_dir.resolve())

    core_dir: Path = resolved_workspace / "core"
    core_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bridge_src, core_dir / EDU_BRIDGE_FILENAME)
    shutil.copy2(hooks_src, core_dir / hooks_filename)

    if genre == "fighting":
        touch_src: Path = edu_dir / FIGHTING_TOUCH_FILENAME
        if touch_src.is_file():
            shutil.copy2(touch_src, core_dir / FIGHTING_TOUCH_FILENAME)

    project_path: Path = resolved_workspace / "project.godot"
    if project_path.is_file():
        _patch_project_godot_autoload(project_path)

    main_scene: Path = resolved_workspace / "scenes" / "main.tscn"
    if main_scene.is_file():
        _patch_main_tscn_hooks(main_scene, hooks_filename)
        if genre == "fighting":
            _patch_main_tscn_fighting_touch(main_scene)

    return True


def _patch_project_godot_autoload(project_path: Path) -> None:
    text: str = project_path.read_text(encoding="utf-8")
    if "EduActionBridge=" in text:
        return
    marker: str = "[autoload]\n"
    if marker not in text:
        return
    line: str = 'EduActionBridge="*res://core/edu_action_bridge.gd"\n'
    project_path.write_text(text.replace(marker, marker + line, 1), encoding="utf-8")


def _patch_main_tscn_hooks(main_path: Path, hooks_filename: str) -> None:
    text: str = main_path.read_text(encoding="utf-8")
    if 'name="EduHooks"' in text:
        return

    script_path: str = f"res://core/{hooks_filename}"
    load_match = re.search(r"load_steps=(\d+)", text)
    load_steps: int = int(load_match.group(1)) if load_match else 1
    new_load_steps: int = load_steps + 1
    ext_id: str = f"{new_load_steps}_eduhooks"

    text = re.sub(r"load_steps=\d+", f"load_steps={new_load_steps}", text, count=1)

    ext_line: str = f'[ext_resource type="Script" path="{script_path}" id="{ext_id}"]\n'
    insert_pos: int = text.find("\n\n[")
    if insert_pos == -1:
        insert_pos = text.find("\n[node")
    if insert_pos == -1:
        insert_pos = len(text)
    text = text[:insert_pos] + "\n" + ext_line + text[insert_pos:]

    node_block: str = (
        f'\n[node name="EduHooks" type="Node" parent="."]\n'
        f'script = ExtResource("{ext_id}")\n'
    )
    if not text.endswith("\n"):
        text += "\n"
    text += node_block
    main_path.write_text(text, encoding="utf-8")


def _patch_main_tscn_fighting_touch(main_path: Path) -> None:
    text: str = main_path.read_text(encoding="utf-8")
    if 'name="FightingTouch"' in text:
        return
    if '[node name="CanvasLayer"' not in text:
        return

    load_match = re.search(r"load_steps=(\d+)", text)
    load_steps: int = int(load_match.group(1)) if load_match else 1
    new_load_steps: int = load_steps + 1
    ext_id: str = f"{new_load_steps}_fighttouch"
    script_path: str = f"res://core/{FIGHTING_TOUCH_FILENAME}"

    text = re.sub(r"load_steps=\d+", f"load_steps={new_load_steps}", text, count=1)

    ext_line: str = f'[ext_resource type="Script" path="{script_path}" id="{ext_id}"]\n'
    insert_pos: int = text.find("\n\n[")
    if insert_pos == -1:
        insert_pos = text.find("\n[node")
    if insert_pos == -1:
        insert_pos = len(text)
    text = text[:insert_pos] + "\n" + ext_line + text[insert_pos:]

    canvas_idx: int = text.find('[node name="CanvasLayer"')
    if canvas_idx == -1:
        return
    insert_child: int = text.find("\n[node", canvas_idx + 1)
    if insert_child == -1:
        insert_child = len(text)
    touch_block: str = (
        f'\n[node name="FightingTouch" type="Control" parent="CanvasLayer"]\n'
        f"layout_mode = 3\n"
        f"anchors_preset = 15\n"
        f"anchor_right = 1.0\n"
        f"anchor_bottom = 1.0\n"
        f"grow_horizontal = 2\n"
        f"grow_vertical = 2\n"
        f"mouse_filter = 2\n"
        f'script = ExtResource("{ext_id}")\n'
    )
    text = text[:insert_child] + touch_block + text[insert_child:]
    main_path.write_text(text, encoding="utf-8")


EDU_ACTIONS_LOG: str = ".edu_actions.jsonl"


def _edu_actions_log_path(workspace_root: Path) -> Path:
    return workspace_root / EDU_ACTIONS_LOG


def append_edu_action(workspace_root: Path, action_id: str) -> int:
    """Append one action event to workspace .edu_actions.jsonl. Returns t_ms."""
    t_ms: int = int(time.time() * 1000)
    log_path: Path = _edu_actions_log_path(workspace_root)
    payload: dict[str, object] = {"action_id": action_id, "t_ms": t_ms}
    line: str = json.dumps(payload, separators=(",", ":")) + "\n"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line)
    return t_ms


def read_edu_actions(workspace_root: Path, since_ms: int = 0) -> list[dict[str, object]]:
    log_path: Path = _edu_actions_log_path(workspace_root)
    if not log_path.is_file():
        return []
    events: list[dict[str, object]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        stripped: str = line.strip()
        if not stripped:
            continue
        try:
            row: dict[str, object] = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        t_ms: int = int(row.get("t_ms", 0))
        if t_ms > since_ms:
            events.append(row)
    return events
