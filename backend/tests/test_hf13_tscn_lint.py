"""HF-13：.tscn Godot 4 静态校验 + 写入拦截（防未引用坏场景漏检）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import Settings
from app.services.creative.agent_contracts import lint_tscn_godot4
from app.services.creative.game_agent import _run_action


def _settings(templates: Path, workspace: Path) -> Settings:
    learned = workspace.parent / "learned_skills_test"
    learned.mkdir(parents=True, exist_ok=True)
    ref = workspace.parent / "reference_skills_test"
    ref.mkdir(parents=True, exist_ok=True)
    return Settings(
        templates_dir=templates,
        workspace_dir=workspace,
        learned_skills_dir=learned,
        reference_skills_dir=ref,
        allow_memory_fallback=True,
        llm_api_key="sk-test",
        llm_base_url="https://example.invalid/v1",
        llm_model="test-model",
        llm_timeout_sec=5.0,
        agent_max_rounds=8,
        agent_soft_extra_rounds=0,
        agent_wall_clock_sec=60.0,
    )


def test_lint_tscn_rejects_extents() -> None:
    bad = (
        '[gd_scene load_steps=2 format=3]\n\n'
        '[sub_resource type="RectangleShape2D" id="RectangleShape2D"]\n'
        "extents = Vector2(16, 32)\n\n"
        '[node name="Zone" type="Area2D"]\n'
        'shape = SubResource("RectangleShape2D")\n'
    )
    errs = lint_tscn_godot4(bad)
    assert any("size" in e and "extents" in e for e in errs)


def test_lint_tscn_rejects_subresource_before_define() -> None:
    bad = (
        '[gd_scene load_steps=2 format=3]\n\n'
        '[node name="Zone" type="Area2D"]\n'
        '[node name="CollisionShape2D" type="CollisionShape2D" parent="."]\n'
        'shape = SubResource("RectangleShape2D")\n\n'
        '[sub_resource type="RectangleShape2D" id="RectangleShape2D"]\n'
        "size = Vector2(16, 32)\n"
    )
    errs = lint_tscn_godot4(bad)
    assert any("SubResource" in e and "定义之前" in e for e in errs)


def test_lint_tscn_rejects_unclosed_node_header() -> None:
    bad = (
        '[gd_scene load_steps=2 format=3]\n\n'
        '[node name="Zone" type="Area2D" groups=["boost"]\n'
        'script = ExtResource("1")\n'
    )
    errs = lint_tscn_godot4(bad)
    assert any("闭合" in e for e in errs)


def test_lint_tscn_accepts_godot4_minimal() -> None:
    good = (
        '[gd_scene load_steps=2 format=3]\n\n'
        '[sub_resource type="RectangleShape2D" id="RectangleShape2D"]\n'
        "size = Vector2(16, 32)\n\n"
        '[node name="Zone" type="Area2D"]\n'
        '[node name="CollisionShape2D" type="CollisionShape2D" parent="."]\n'
        'shape = SubResource("RectangleShape2D")\n'
    )
    assert lint_tscn_godot4(good) == []


def test_write_file_blocks_bad_tscn(tmp_path: Path) -> None:
    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    root = workspace / "sess-hf13-tscn"
    (root / "scenes" / "prefabs").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    (root / "config").mkdir(parents=True)
    (root / "config" / "game_config.json").write_text(
        json.dumps({"meta": {"genre": "parkour"}, "tuning": {"enabled_skills": []}}),
        encoding="utf-8",
    )
    settings = _settings(templates, workspace)
    bad = (
        '[gd_scene load_steps=2 format=3]\n\n'
        '[node name="Zone" type="Area2D"]\n'
        '[node name="CollisionShape2D" type="CollisionShape2D" parent="."]\n'
        'shape = SubResource("RectangleShape2D")\n\n'
        '[sub_resource type="RectangleShape2D" id="RectangleShape2D"]\n'
        "extents = Vector2(16, 32)\n"
    )
    with pytest.raises(Exception) as ei:
        _run_action(
            settings,
            root,
            "parkour",
            {
                "tool": "write_file",
                "path": "scenes/prefabs/speed_boost_zone.tscn",
                "content": bad,
            },
            {},
            [],
            user_text="加速光环",
        )
    msg = str(ei.value)
    assert "场景写入前校验失败" in msg
    assert not (root / "scenes" / "prefabs" / "speed_boost_zone.tscn").is_file()
