#!/usr/bin/env python3
"""实时盯盘：智能体 LLM 轮次 / 工具 / 门禁 / 进度（HF-14 Live Trace）。

依赖后端写入会话：
  workspace/.../.agent/live_trace.jsonl
  workspace/.../.agent_progress.json
  workspace/.../.session_ai_log.jsonl

用法（仓库根）:
  python 05-工具脚本/watch_agent_live.py
  python 05-工具脚本/watch_agent_live.py --session ec9bfaeb-...
  python 05-工具脚本/watch_agent_live.py --workspace "workspace/users/<uid>/<sid>"
  python 05-工具脚本/watch_agent_live.py --once   # 只打当前快照后退出

分析缺陷时：盯 event=gate / done(rolled_back) / llm_round 的 goals vs actions。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
WS_ROOT = REPO / "workspace" / "users"


def _newest_workspace() -> Path | None:
    if not WS_ROOT.is_dir():
        return None
    best: Path | None = None
    best_mtime = 0.0
    for user_dir in WS_ROOT.iterdir():
        if not user_dir.is_dir():
            continue
        for sid_dir in user_dir.iterdir():
            if not sid_dir.is_dir():
                continue
            # 优先有 live_trace / progress 的
            candidates = [
                sid_dir / ".agent" / "live_trace.jsonl",
                sid_dir / ".agent_progress.json",
                sid_dir / "project.godot",
            ]
            m = 0.0
            for c in candidates:
                if c.is_file():
                    m = max(m, c.stat().st_mtime)
            if m > best_mtime:
                best_mtime = m
                best = sid_dir
    return best


def _resolve_workspace(session: str, workspace: str) -> Path:
    if workspace:
        p = Path(workspace)
        if not p.is_absolute():
            p = REPO / p
        return p.resolve()
    if session:
        # workspace/users/*/<session>
        if WS_ROOT.is_dir():
            for user_dir in WS_ROOT.iterdir():
                cand = user_dir / session
                if cand.is_dir():
                    return cand.resolve()
        raise SystemExit(f"未找到 session={session} 的 workspace")
    newest = _newest_workspace()
    if newest is None:
        raise SystemExit(f"无可用 workspace（{WS_ROOT}）")
    return newest.resolve()


def _read_progress(ws: Path) -> dict[str, Any]:
    p = ws / ".agent_progress.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _tail_new_lines(path: Path, offset: int) -> tuple[list[str], int]:
    if not path.is_file():
        return [], offset
    try:
        size = path.stat().st_size
        if offset > size:
            offset = 0  # 轮转后重置
        with path.open("r", encoding="utf-8") as fh:
            fh.seek(offset)
            chunk = fh.read()
            new_off = fh.tell()
        lines = [ln for ln in chunk.splitlines() if ln.strip()]
        return lines, new_off
    except OSError:
        return [], offset


def _fmt_event(row: dict[str, Any]) -> str:
    ev = str(row.get("event") or "?")
    rnd = row.get("round")
    prefix = f"[r{rnd}] " if rnd is not None else ""
    if ev == "llm_round":
        err = str(row.get("error") or "")
        if err:
            return f"{prefix}LLM 解析失败 · {err}"
        goals = row.get("goals") or []
        actions = row.get("actions") or []
        tools = [str(a.get("tool")) for a in actions if isinstance(a, dict)]
        und = str(row.get("understanding") or "")[:120]
        return (
            f"{prefix}LLM ← understanding: {und}\n"
            f"         goals: {goals}\n"
            f"         tools: {tools}"
        )
    if ev == "tools":
        obs = row.get("observations") or []
        parts = []
        for o in obs:
            if not isinstance(o, dict):
                continue
            t = o.get("tool")
            path = o.get("path") or ""
            err = o.get("error") or ""
            line = f"{t}"
            if path:
                line += f" {path}"
            if err:
                line += f" ERR={err[:160]}"
            parts.append(line)
        return f"{prefix}TOOLS · " + " | ".join(parts[:12])
    if ev == "gate":
        errs = row.get("gate_errors") or []
        evd = row.get("evidence") or []
        return (
            f"{prefix}GATE FAIL · {errs}\n"
            f"         evidence: {json.dumps(evd, ensure_ascii=False)[:500]}"
        )
    if ev == "done":
        return (
            f"{prefix}DONE · gate_passed={row.get('gate_passed')} "
            f"rolled_back={row.get('rolled_back')}\n"
            f"         written={row.get('written')}\n"
            f"         summary={str(row.get('summary') or '')[:200]}"
        )
    return f"{prefix}{ev} · {json.dumps(row, ensure_ascii=False)[:400]}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Watch agent live_trace / progress")
    ap.add_argument("--session", default="", help="会话 id")
    ap.add_argument("--workspace", default="", help="workspace 相对/绝对路径")
    ap.add_argument("--interval", type=float, default=0.8, help="轮询秒")
    ap.add_argument("--once", action="store_true", help="打一次快照后退出")
    ap.add_argument(
        "--dump-messages",
        action="store_true",
        help="llm_round 时打印截断后的 messages 全文（很长）",
    )
    args = ap.parse_args()

    ws = _resolve_workspace(args.session, args.workspace)
    trace_path = ws / ".agent" / "live_trace.jsonl"
    print(f"watching: {ws}", flush=True)
    print(f"trace:    {trace_path}", flush=True)
    print("---", flush=True)

    offset = 0
    if trace_path.is_file():
        # 启动时先跳到文件末尾，只看新事件；--once 则读尾部若干行
        if args.once:
            try:
                lines = trace_path.read_text(encoding="utf-8").splitlines()
                for ln in lines[-30:]:
                    try:
                        row = json.loads(ln)
                    except json.JSONDecodeError:
                        continue
                    print(_fmt_event(row), flush=True)
                    if args.dump_messages and row.get("event") == "llm_round":
                        print(
                            json.dumps(row.get("messages"), ensure_ascii=False, indent=2)[:8000],
                            flush=True,
                        )
            except OSError as exc:
                print(f"read fail: {exc}", file=sys.stderr)
            prog = _read_progress(ws)
            if prog:
                print(
                    f"progress: {prog.get('title')} · {prog.get('detail')}",
                    flush=True,
                )
            return 0
        offset = trace_path.stat().st_size

    last_prog_sig = ""
    try:
        while True:
            prog = _read_progress(ws)
            sig = f"{prog.get('stage')}|{prog.get('detail')}"
            if prog and sig != last_prog_sig:
                last_prog_sig = sig
                print(
                    f"PROGRESS · {prog.get('title') or prog.get('stage')} · {prog.get('detail')}",
                    flush=True,
                )

            lines, offset = _tail_new_lines(trace_path, offset)
            for ln in lines:
                try:
                    row = json.loads(ln)
                except json.JSONDecodeError:
                    print(f"RAW {ln[:200]}", flush=True)
                    continue
                print(_fmt_event(row), flush=True)
                print("---", flush=True)
                if args.dump_messages and row.get("event") == "llm_round":
                    print(
                        json.dumps(row.get("messages"), ensure_ascii=False, indent=2)[:12000],
                        flush=True,
                    )
                    print("---", flush=True)

            if args.once:
                break
            time.sleep(max(0.2, args.interval))
    except KeyboardInterrupt:
        print("\nstopped.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
