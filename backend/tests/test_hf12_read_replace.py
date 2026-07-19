"""HF-12 P0-A：分页 read / search_in_file / replace_text / 结构化 observations。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.agent_workspace import (
    AgentWorkspaceError,
    READ_DEFAULT_LIMIT,
    existing_file_requires_replace,
    read_workspace_file,
    read_workspace_file_page,
    replace_workspace_text,
    search_workspace_file,
    serialize_observations_for_followup,
    sha256_text,
    write_workspace_file,
)


def _mini(tmp_path: Path) -> tuple[Path, Path, Path]:
    templates = tmp_path / "templates"
    workspace = tmp_path / "workspace"
    (templates / "pingpong" / "core").mkdir(parents=True)
    root = workspace / "sess-hf12-p0a"
    (root / "core").mkdir(parents=True)
    return templates, workspace, root


def test_read_file_pagination_15k_to_20k(tmp_path: Path) -> None:
    templates, workspace, root = _mini(tmp_path)
    body = "\n".join(f"# line {i:04d} " + ("x" * 40) for i in range(400))
    assert 15000 <= len(body) <= 25000
    path = "core/big_script.gd"
    write_workspace_file(
        root, workspace, templates, path, "extends Node\n" + body + "\n"
    )
    full = read_workspace_file(root, workspace, templates, path)
    digest = sha256_text(full)

    page1 = read_workspace_file_page(
        root, workspace, templates, path, offset=0, limit=8000
    )
    assert page1["offset"] == 0
    assert page1["returned_chars"] == 8000
    assert page1["eof"] is False
    assert page1["next_offset"] == 8000
    assert page1["sha256"] == digest
    assert page1["total_chars"] == len(full)

    page2 = read_workspace_file_page(
        root,
        workspace,
        templates,
        path,
        offset=int(page1["next_offset"]),
        limit=8000,
    )
    page3_off = page2["next_offset"]
    rebuilt = page1["content"] + page2["content"]
    if page3_off is not None:
        page3 = read_workspace_file_page(
            root, workspace, templates, path, offset=int(page3_off), limit=8000
        )
        rebuilt += page3["content"]
        assert page3["eof"] is True
        assert page3["next_offset"] is None
        assert page3["sha256"] == digest
    else:
        assert page2["eof"] is True
    assert rebuilt == full
    assert page1["sha256"] == page2["sha256"] == digest


def test_search_in_file_hits_and_context(tmp_path: Path) -> None:
    templates, workspace, root = _mini(tmp_path)
    src = (
        "extends Node\n"
        "func reset_to_center() -> void:\n"
        "\tposition = Vector2.ZERO\n"
        "func other() -> void:\n"
        "\tpass\n"
    )
    write_workspace_file(root, workspace, templates, "core/ball.gd", src)
    hit = search_workspace_file(
        root,
        workspace,
        templates,
        "core/ball.gd",
        "reset_to_center",
        max_hits=3,
        context_lines=1,
    )
    assert hit["hit_count"] == 1
    assert hit["hits"][0]["line"] == 2
    assert "reset_to_center" in hit["hits"][0]["context"]
    assert hit["sha256"] == sha256_text(src)


def test_replace_text_unique_success_and_crlf(tmp_path: Path) -> None:
    templates, workspace, root = _mini(tmp_path)
    # 混用 CRLF
    src = "extends Node\r\nfunc a() -> void:\r\n\tpass\r\nfunc b() -> void:\r\n\tpass\r\n"
    write_workspace_file(root, workspace, templates, "core/ball.gd", src)
    before_hash = sha256_text(src)
    result = replace_workspace_text(
        root,
        workspace,
        templates,
        "core/ball.gd",
        "func a() -> void:\r\n\tpass\r\n",
        "func a() -> void:\r\n\tmodulate = Color.WHITE\r\n\tpass\r\n",
        expected_sha256=before_hash,
    )
    assert result["before_sha256"] == before_hash
    assert result["after_sha256"] != before_hash
    assert result["changed_lines"] >= 1
    disk = (root / "core" / "ball.gd").read_bytes().decode("utf-8")
    assert "modulate = Color.WHITE" in disk
    assert "func b() -> void:" in disk
    assert result["after_sha256"] == sha256_text(disk)


def test_replace_text_zero_hit(tmp_path: Path) -> None:
    templates, workspace, root = _mini(tmp_path)
    write_workspace_file(
        root, workspace, templates, "core/ball.gd", "extends Node\n"
    )
    with pytest.raises(AgentWorkspaceError, match="零命中"):
        replace_workspace_text(
            root,
            workspace,
            templates,
            "core/ball.gd",
            "DOES_NOT_EXIST",
            "x",
        )


def test_replace_text_multi_hit(tmp_path: Path) -> None:
    templates, workspace, root = _mini(tmp_path)
    write_workspace_file(
        root,
        workspace,
        templates,
        "core/ball.gd",
        "extends Node\n# foo\nfunc a() -> void:\n\tpass\n# foo\n",
    )
    with pytest.raises(AgentWorkspaceError, match="多命中"):
        replace_workspace_text(
            root, workspace, templates, "core/ball.gd", "# foo\n", "# bar\n"
        )


def test_replace_text_stale_hash_soft_ok_when_unique(tmp_path: Path) -> None:
    """唯一命中时陈旧 hash 不挡写入（探针：LLM 常带错 hash）。"""
    templates, workspace, root = _mini(tmp_path)
    src = "extends Node\nfunc a() -> void:\n\tpass\n"
    write_workspace_file(root, workspace, templates, "core/ball.gd", src)
    result = replace_workspace_text(
        root,
        workspace,
        templates,
        "core/ball.gd",
        "func a() -> void:\n\tpass\n",
        "func a() -> void:\n\treturn\n",
        expected_sha256="0" * 64,
    )
    assert result.get("hash_mismatch_ignored") is True
    disk = (root / "core" / "ball.gd").read_text(encoding="utf-8")
    assert "return" in disk


def test_replace_text_lf_fragment_on_crlf_file(tmp_path: Path) -> None:
    """磁盘 CRLF、LLM 给 LF old_text → 应对齐后命中（platformer 探针根因）。"""
    templates, workspace, root = _mini(tmp_path)
    src = (
        "extends Node\r\n"
        "func _on_collectible_collected() -> void:\r\n"
        "\t_coins += 1\r\n"
        "\t_add_score(10)\r\n"
        "\n"
        "func other() -> void:\r\n"
        "\tpass\r\n"
    )
    # 写成真实 CRLF 字节
    (root / "core").mkdir(parents=True, exist_ok=True)
    (root / "core" / "game_manager.gd").write_bytes(src.encode("utf-8"))
    result = replace_workspace_text(
        root,
        workspace,
        templates,
        "core/game_manager.gd",
        "\t_coins += 1\n\t_add_score(10)\n",  # LF
        "\t_coins += 1\n\t_add_score(10)\n\tif _coins % 5 == 0:\n\t\tpass\n",
    )
    assert result.get("newline_aligned") is True
    disk = (root / "core" / "game_manager.gd").read_bytes().decode("utf-8")
    assert "_coins % 5" in disk
    assert "\r\n" in disk


def test_existing_large_file_requires_replace() -> None:
    big = "extends Node\n" + ("\n".join(f"func f{i}() -> void:\n\tpass" for i in range(130))
    )
    assert existing_file_requires_replace("core/ball.gd", big) is True
    small = "extends Node\nfunc a() -> void:\n\tpass\n"
    assert existing_file_requires_replace("core/ball.gd", small) is False
    assert existing_file_requires_replace(
        "core/ball.gd", big, allow_full_rewrite=True
    ) is False


def test_observations_multi_item_budget_keeps_valid_json_and_meta() -> None:
    # 三个大 read_file observation，总预算紧张
    obs = []
    for i in range(3):
        content = ("CHUNK%d-" % i) + ("Z" * 6000)
        obs.append(
            {
                "tool": "read_file",
                "path": f"core/file{i}.gd",
                "offset": 0,
                "limit": 8000,
                "total_chars": 20000,
                "returned_chars": len(content),
                "eof": False,
                "sha256": sha256_text(content),
                "content": content,
                "next_offset": len(content),
            }
        )
    obs.append(
        {
            "tool": "diagnose_workspace",
            "prompt": "低价值诊断 " + ("D" * 5000),
            "ok": True,
        }
    )
    text = serialize_observations_for_followup(obs, total_budget=12000, per_item_budget=5000)
    payload = json.loads(text)  # 必须是合法 JSON，禁止裸硬切
    assert isinstance(payload, list)
    assert len(payload) >= 1
    # read_file 优先保留 path / continuation
    read_items = [x for x in payload if x.get("tool") == "read_file"]
    assert read_items
    for item in read_items:
        assert item.get("path")
        assert "sha256" in item or item.get("truncated")
        if item.get("truncated") or item.get("eof") is False:
            assert "next_offset" in item or "path" in item
    # 不得出现被切断的非法 JSON 残片
    assert text.strip().startswith("[")
    assert text.strip().endswith("]")


def test_observations_prefer_read_over_diagnose() -> None:
    obs = [
        {"tool": "diagnose_workspace", "prompt": "DIAG" + ("x" * 8000)},
        {
            "tool": "read_file",
            "path": "core/ball.gd",
            "content": "READ" + ("y" * 2000),
            "offset": 0,
            "eof": False,
            "next_offset": 2004,
            "sha256": "abc",
            "total_chars": 9000,
        },
    ]
    text = serialize_observations_for_followup(obs, total_budget=5000, per_item_budget=3500)
    payload = json.loads(text)
    # 预算紧时 read 路径与 continuation 必须还在
    paths = [x.get("path") for x in payload if x.get("path")]
    assert "core/ball.gd" in paths
    read_item = next(x for x in payload if x.get("path") == "core/ball.gd")
    assert read_item.get("next_offset") is not None or read_item.get("truncated")


def test_default_read_limit_constant() -> None:
    assert READ_DEFAULT_LIMIT == 8000


def test_prompt_trim_preserves_disk_eof_true() -> None:
    """HF-12 Live：回灌预算截断不得把磁盘 eof=true 改成 false（防空转续读）。"""
    content = "extends Node\n" + ("# body\n" * 800)
    assert len(content) > 3000
    obs = [
        {
            "tool": "read_file",
            "path": "core/player_runner.gd",
            "offset": 0,
            "limit": 8000,
            "total_chars": len(content),
            "returned_chars": len(content),
            "eof": True,
            "sha256": sha256_text(content),
            "content": content,
            "next_offset": None,
        },
        {
            "tool": "diagnose_workspace",
            "prompt": "DIAG" + ("d" * 4000),
            "ok": True,
        },
    ]
    text = serialize_observations_for_followup(
        obs, total_budget=3500, per_item_budget=2200
    )
    payload = json.loads(text)
    read_item = next(x for x in payload if x.get("path") == "core/player_runner.gd")
    assert read_item.get("eof") is True
    assert read_item.get("next_offset") is None
    assert read_item.get("prompt_truncated") is True or read_item.get("truncated") is True
    assert "content_resume_offset" in read_item or "search_in_file" in str(
        read_item.get("note") or ""
    )


def test_read_past_eof_stops_pagination(tmp_path: Path) -> None:
    templates, workspace, root = _mini(tmp_path)
    path = "core/small.gd"
    body = "extends Node\nfunc ready() -> void:\n\tpass\n"
    write_workspace_file(root, workspace, templates, path, body)
    page = read_workspace_file_page(
        root, workspace, templates, path, offset=len(body) + 50, limit=8000
    )
    assert page["eof"] is True
    assert page["returned_chars"] == 0
    assert page["next_offset"] is None
    assert "末尾" in str(page.get("note") or "")
