# -*- coding: utf-8 -*-
"""GameForge K12 · 秒哒 11 品类批量创作 + 工作流全程记录。

用法（密钥见项目根 `.env` 或环境变量 `MIAODA_API_KEY`）：
  python 05-工具脚本/miaoda_batch_create.py
  python 05-工具脚本/miaoda_batch_create.py --slug platformer
  python 05-工具脚本/miaoda_batch_create.py --from fighting
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_JSON = ROOT / "03-背景与调研" / "config" / "miaoda_11_genre_prompts.json"
OUTPUT_ROOT = ROOT / "03-背景与调研" / "data" / "秒哒11品类批次"
MIAODA_API_PATH = ROOT / "tools" / "miaoda-skill" / "miaoda-app-builder" / "scripts" / "miaoda_api.py"
DEFAULT_BASE_URL = "https://api.miaoda.cn"

LOCAL_ENV_CANDIDATES: list[Path] = [
    ROOT / ".env",
    ROOT / "backend" / ".env",
    ROOT / "tools" / "miaoda-skill" / "miaoda-app-builder" / ".env",
]


def _load_local_env() -> None:
    """从本地 .env 文件注入 MIAODA_*（不覆盖已有环境变量）。"""
    for path in LOCAL_ENV_CANDIDATES:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key.startswith("MIAODA_") and key not in os.environ:
                os.environ[key] = val


def _load_miaoda_api() -> Any:
    spec = importlib.util.spec_from_file_location("miaoda_api", MIAODA_API_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {MIAODA_API_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _poll_and_log(
    api: Any,
    base_url: str,
    api_key: str,
    app_id: str,
    log_path: Path,
    phase: str,
    poll_interval: float = 3.0,
    max_wait_sec: int = 900,
) -> tuple[Optional[dict[str, Any]], str]:
    """Poll trajectory until terminal; append every event to log_path."""
    start = time.time()
    last_id = -1
    prd_action: Optional[dict[str, Any]] = None
    text_buf = ""

    while time.time() - start < max_wait_sec:
        events, max_id, is_terminal = api.fetch_trajectory_once(
            base_url, api_key, app_id, last_id, timeout=30,
        )
        for ev in events:
            _append_jsonl(log_path, {
                "ts": _utc_now(),
                "phase": phase,
                "event": ev,
            })
            text_buf += api._extract_text_from_event(ev)

        action = api._extract_prd_action_from_events(events)
        if action is not None:
            prd_action = action

        last_id = max_id
        if is_terminal:
            break
        time.sleep(poll_interval)

    return prd_action, text_buf


def _extract_ids(api: Any, chat_result: dict[str, Any], app_id: Optional[str]) -> tuple[str, str]:
    resolved_app, conv = api._extract_ids_from_chat_response(chat_result, app_id)
    if not resolved_app:
        raise RuntimeError("chat 响应中未找到 appId")
    return resolved_app, conv or ""


def run_one_genre(
    api: Any,
    base_url: str,
    api_key: str,
    genre: dict[str, Any],
    poll_interval: float,
    max_wait_sec: int,
) -> dict[str, Any]:
    slug: str = genre["slug"]
    out_dir = OUTPUT_ROOT / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    workflow_log = out_dir / "workflow.jsonl"
    result_path = out_dir / "result.json"

    meta: dict[str, Any] = {
        "slug": slug,
        "display_name": genre.get("display_name", slug),
        "reference_games": genre.get("reference_games", []),
        "started_at": _utc_now(),
        "steps": [],
    }

    _save_json(out_dir / "prompt_meta.json", genre)
    (out_dir / "prompt.txt").write_text(genre["prompt"], encoding="utf-8")

    print(f"\n=== [{slug}] {genre.get('display_name')} ===", flush=True)

    try:
        # Step 1: 首句需求 → PRD
        step1 = {"step": "chat_initial", "at": _utc_now()}
        chat1 = api.chat_no_stream(base_url, api_key, genre["prompt"], query_mode="deep_mode")
        app_id, conv_id = _extract_ids(api, chat1, None)
        step1["appId"] = app_id
        step1["conversationId"] = conv_id
        meta["steps"].append(step1)
        print(f"  appId={app_id} conv={conv_id}", flush=True)

        prd_action, _ = _poll_and_log(
            api, base_url, api_key, app_id, workflow_log,
            phase="prd_after_initial", poll_interval=poll_interval, max_wait_sec=max_wait_sec,
        )

        # Step 2: 确认生成
        need_gen = False
        if prd_action is not None:
            need_gen = (
                not prd_action.get("is_generated", False)
                and api._has_generate_app_button(prd_action)
            )

        step2 = {"step": "generate_confirm", "at": _utc_now(), "needGenerateApp": need_gen}
        if need_gen and conv_id:
            gen_result = api.generate_app_confirmation(
                base_url, api_key, context_id=conv_id, app_id=app_id,
                watch=False,
            )
            step2["submitted"] = True
            _append_jsonl(workflow_log, {"ts": _utc_now(), "phase": "generate_submit", "result": gen_result})
            _poll_and_log(
                api, base_url, api_key, app_id, workflow_log,
                phase="generation", poll_interval=poll_interval, max_wait_sec=max_wait_sec,
            )
        else:
            #  fallback: 文本确认
            chat2 = api.chat_no_stream(
                base_url, api_key, "立即创作", context_id=conv_id, app_id=app_id,
            )
            step2["fallback_chat"] = "立即创作"
            _append_jsonl(workflow_log, {"ts": _utc_now(), "phase": "chat_confirm", "result": chat2})
            _poll_and_log(
                api, base_url, api_key, app_id, workflow_log,
                phase="after_confirm", poll_interval=poll_interval, max_wait_sec=max_wait_sec,
            )

        meta["steps"].append(step2)

        # Step 3: 详情 + 对话摘要
        detail = api.get_app_detail(base_url, api_key, app_id)
        history = api.get_conversation_history(base_url, api_key, app_id)
        _save_json(out_dir / "app_detail.json", detail)
        _save_json(out_dir / "conversation_history.json", history)

        data = detail.get("data") or {}
        meta["finished_at"] = _utc_now()
        meta["appId"] = app_id
        meta["conversationId"] = conv_id
        meta["editor_url"] = f"https://www.miaoda.cn/projects/{app_id}"
        meta["preview_url"] = f"https://{app_id}.appmiaoda.com"
        meta["appFocus"] = data.get("appFocus")
        meta["status"] = "ok"

    except Exception as exc:
        meta["finished_at"] = _utc_now()
        meta["status"] = "error"
        meta["error"] = str(exc)
        meta["traceback"] = traceback.format_exc()
        print(f"  ERROR: {exc}", flush=True)

    _save_json(result_path, meta)
    _append_jsonl(OUTPUT_ROOT / "batch_summary.jsonl", meta)
    return meta


def main() -> int:
    parser = argparse.ArgumentParser(description="秒哒 11 品类批量创作")
    parser.add_argument("--slug", default="", help="仅运行指定 slug")
    parser.add_argument("--from", dest="from_slug", default="", help="从某 slug 起顺序执行")
    parser.add_argument("--poll-interval", type=float, default=3.0)
    parser.add_argument("--max-wait-sec", type=int, default=900, help="单阶段最长等待秒数")
    args = parser.parse_args()

    _load_local_env()
    api_key = os.environ.get("MIAODA_API_KEY", "").strip()
    if not api_key:
        print("Error: 请设置 MIAODA_API_KEY（项目根 .env 或环境变量）", file=sys.stderr)
        return 1

    base_url = os.environ.get("MIAODA_BASE_URL", DEFAULT_BASE_URL)
    api = _load_miaoda_api()

    cfg = json.loads(PROMPTS_JSON.read_text(encoding="utf-8"))
    genres: list[dict[str, Any]] = cfg["genres"]

    if args.slug:
        genres = [g for g in genres if g["slug"] == args.slug]
    elif args.from_slug:
        slugs = [g["slug"] for g in cfg["genres"]]
        if args.from_slug not in slugs:
            print(f"Unknown slug: {args.from_slug}", file=sys.stderr)
            return 1
        genres = [g for g in cfg["genres"] if slugs.index(g["slug"]) >= slugs.index(args.from_slug)]

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _save_json(OUTPUT_ROOT / "batch_manifest.json", {
        "started_at": _utc_now(),
        "genres": [g["slug"] for g in genres],
        "prompts_file": str(PROMPTS_JSON),
    })

    results: list[dict[str, Any]] = []
    for genre in genres:
        results.append(run_one_genre(
            api, base_url, api_key, genre,
            poll_interval=args.poll_interval,
            max_wait_sec=args.max_wait_sec,
        ))
        time.sleep(5)

    ok = sum(1 for r in results if r.get("status") == "ok")
    print(f"\n完成: {ok}/{len(results)} 成功 · 日志目录 {OUTPUT_ROOT}", flush=True)
    return 0 if ok == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
