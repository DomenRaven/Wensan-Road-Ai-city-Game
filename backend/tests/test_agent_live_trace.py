"""HF-14 辅助：live_trace 落盘。"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.creative.agent_live_trace import (
    LIVE_TRACE_REL,
    append_live_trace,
    trace_gate,
    trace_llm_round,
)


def test_append_live_trace_jsonl(tmp_path: Path) -> None:
    append_live_trace(tmp_path, "ping", {"x": 1}, enabled=True)
    path = tmp_path / LIVE_TRACE_REL
    assert path.is_file()
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["event"] == "ping"
    assert row["x"] == 1


def test_trace_llm_and_gate(tmp_path: Path) -> None:
    msgs = [
        {"role": "system", "content": "sys " * 200},
        {"role": "user", "content": "每过20秒无敌"},
    ]
    parsed = {
        "understanding": "要时间轴无敌",
        "goals": ["冷却循环"],
        "actions": [{"tool": "read_file", "path": "core/player.gd"}],
    }
    trace_llm_round(tmp_path, round_idx=0, messages=msgs, parsed=parsed, enabled=True)
    trace_gate(
        tmp_path,
        round_idx=0,
        gate_errors=["evidence 接线失败：demo"],
        evidence=[{"path": "core/a.gd", "symbol": "_update_x", "wired_by": "_process"}],
        enabled=True,
    )
    lines = (tmp_path / LIVE_TRACE_REL).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    ev0 = json.loads(lines[0])
    assert ev0["event"] == "llm_round"
    assert ev0["goals"] == ["冷却循环"]
    assert "messages" in ev0
    ev1 = json.loads(lines[1])
    assert ev1["event"] == "gate"
    assert "接线失败" in ev1["gate_errors"][0]


def test_disabled_noop(tmp_path: Path) -> None:
    append_live_trace(tmp_path, "x", enabled=False)
    assert not (tmp_path / LIVE_TRACE_REL).is_file()
