"""HF-14 辅助：智能体 Live 轨迹落盘（供 watch_agent_live 实时盯盘）。

默认开启（Settings.agent_live_trace）。写入会话：
  workspace/.agent/live_trace.jsonl
不进 learned harvest；体量大时自动轮转。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

LIVE_TRACE_REL: str = ".agent/live_trace.jsonl"
_MAX_FILE_BYTES: int = 8_000_000
_MAX_FIELD_CHARS: int = 6_000
_MAX_MESSAGES: int = 24


def live_trace_enabled(settings: Any) -> bool:
    return bool(getattr(settings, "agent_live_trace", True))


def _clip(text: str, limit: int = _MAX_FIELD_CHARS) -> str:
    s = str(text or "")
    if len(s) <= limit:
        return s
    return s[: limit - 20] + "\n…(truncated)…"


def _summarize_messages(messages: list[dict[str, str]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in (messages or [])[-_MAX_MESSAGES:]:
        role = str(m.get("role") or "")
        content = str(m.get("content") or "")
        # system 只留头尾，避免刷屏；user/assistant 保留更多
        lim = 1800 if role == "system" else _MAX_FIELD_CHARS
        out.append(
            {
                "role": role,
                "chars": len(content),
                "content": _clip(content, lim),
            }
        )
    return out


def _rotate_if_needed(path: Path) -> None:
    try:
        if path.is_file() and path.stat().st_size > _MAX_FILE_BYTES:
            prev = path.with_suffix(".jsonl.prev")
            if prev.is_file():
                prev.unlink()
            path.replace(prev)
    except OSError:
        pass


def append_live_trace(
    workspace_root: Path | None,
    event: str,
    payload: dict[str, Any] | None = None,
    *,
    enabled: bool = True,
) -> None:
    """追加一条 JSONL 事件。失败静默（不影响 Agent）。"""
    if not enabled or workspace_root is None:
        return
    try:
        root = Path(workspace_root)
        agent_dir = root / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        path = root / LIVE_TRACE_REL
        _rotate_if_needed(path)
        row: dict[str, Any] = {
            "ts": time.time(),
            "event": str(event),
            **(payload or {}),
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        return


def trace_llm_round(
    workspace_root: Path | None,
    *,
    round_idx: int,
    messages: list[dict[str, str]],
    parsed: dict[str, Any] | None,
    error: str = "",
    enabled: bool = True,
) -> None:
    """记录一轮 LLM 输入（截断）与解析后的输出摘要。"""
    actions = []
    if isinstance(parsed, dict):
        raw = parsed.get("actions")
        if isinstance(raw, list):
            for a in raw[:16]:
                if isinstance(a, dict):
                    actions.append(
                        {
                            "tool": str(a.get("tool") or ""),
                            "path": str(a.get("path") or "")[:200],
                        }
                    )
    append_live_trace(
        workspace_root,
        "llm_round",
        {
            "round": round_idx,
            "error": _clip(error, 400),
            "understanding": _clip(str((parsed or {}).get("understanding") or ""), 400),
            "goals": [
                str(g)[:200]
                for g in ((parsed or {}).get("goals") or [])
                if str(g).strip()
            ][:6],
            "thought": _clip(str((parsed or {}).get("thought") or ""), 500),
            "actions": actions,
            "messages": _summarize_messages(messages),
            "raw_assistant": _clip(
                json.dumps(parsed, ensure_ascii=False) if parsed else "",
                _MAX_FIELD_CHARS,
            ),
        },
        enabled=enabled,
    )


def trace_tools(
    workspace_root: Path | None,
    *,
    round_idx: int,
    observations: list[dict[str, Any]],
    enabled: bool = True,
) -> None:
    slim: list[dict[str, Any]] = []
    for o in observations[:24]:
        if not isinstance(o, dict):
            continue
        item = {
            "tool": str(o.get("tool") or ""),
            "path": str(o.get("path") or "")[:200],
            "error": _clip(str(o.get("error") or ""), 300),
        }
        if o.get("ok") is not None:
            item["ok"] = o.get("ok")
        # 写入类：带前后摘要长度
        for k in ("written", "sha256", "bytes", "hits", "gate_errors"):
            if k in o:
                item[k] = o[k] if k != "gate_errors" else o[k]
        slim.append(item)
    append_live_trace(
        workspace_root,
        "tools",
        {"round": round_idx, "observations": slim},
        enabled=enabled,
    )


def trace_gate(
    workspace_root: Path | None,
    *,
    round_idx: int,
    gate_errors: list[str],
    evidence: list[dict[str, Any]] | None = None,
    enabled: bool = True,
) -> None:
    append_live_trace(
        workspace_root,
        "gate",
        {
            "round": round_idx,
            "gate_errors": [_clip(e, 400) for e in (gate_errors or [])[:20]],
            "evidence": (evidence or [])[:12],
        },
        enabled=enabled,
    )


def trace_done(
    workspace_root: Path | None,
    *,
    round_idx: int,
    summary: str,
    gate_passed: bool,
    rolled_back: bool,
    written: list[str],
    evidence: list[dict[str, Any]] | None = None,
    enabled: bool = True,
) -> None:
    append_live_trace(
        workspace_root,
        "done",
        {
            "round": round_idx,
            "gate_passed": gate_passed,
            "rolled_back": rolled_back,
            "summary": _clip(summary, 800),
            "written": list(written or [])[:40],
            "evidence": (evidence or [])[:12],
        },
        enabled=enabled,
    )
