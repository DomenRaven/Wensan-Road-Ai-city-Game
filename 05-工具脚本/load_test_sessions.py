#!/usr/bin/env python3
"""10 并发 Session 压测 · GameForge K12 D7 验收脚本."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

DEFAULT_API: str = "http://127.0.0.1:8000"


def api_call(base: str, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any] | str]:
    url: str = f"{base}{path}"
    data: bytes | None = None
    headers: dict[str, str] = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            raw: str = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw_err: str = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw_err)
        except json.JSONDecodeError:
            return exc.code, raw_err


def create_session(base: str, index: int) -> dict[str, Any]:
    started: float = time.perf_counter()
    status, payload = api_call(base, "POST", "/sessions")
    elapsed_ms: float = (time.perf_counter() - started) * 1000.0
    return {
        "index": index,
        "status": status,
        "ok": status == 201,
        "elapsed_ms": round(elapsed_ms, 1),
        "session_id": payload.get("session_id") if isinstance(payload, dict) else None,
    }


def main() -> int:
    base: str = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_API
    count: int = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    print(f"压测目标: {base} · 并发创建 {count} 个 Session")
    _, health = api_call(base, "GET", "/health")
    if not isinstance(health, dict):
        print("health 检查失败", file=sys.stderr)
        return 1
    print(f"health: backend={health.get('session_backend')} active={health.get('active_sessions')}/{health.get('max_sessions')}")
    started_all: float = time.perf_counter()
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = [pool.submit(create_session, base, i) for i in range(count)]
        for fut in as_completed(futures):
            results.append(fut.result())
    elapsed: float = time.perf_counter() - started_all
    ok_count: int = sum(1 for r in results if r["ok"])
    _, health_after = api_call(base, "GET", "/health")
    overflow_status, overflow_payload = api_call(base, "POST", "/sessions")
    summary: dict[str, Any] = {
        "requested": count,
        "created_ok": ok_count,
        "elapsed_sec": round(elapsed, 2),
        "overflow_status": overflow_status,
        "overflow_detail": overflow_payload,
        "health_after": health_after if isinstance(health_after, dict) else health_after,
        "pass": ok_count >= min(8, count) and overflow_status == 429,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["pass"] and "--keep" not in sys.argv:
        try:
            import redis

            redis.Redis.from_url("redis://127.0.0.1:6379/0").flushdb()
            print("已清理 Redis Session（便于继续联调；加 --keep 保留）")
        except Exception:
            pass
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
