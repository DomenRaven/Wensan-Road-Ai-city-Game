# -*- coding: utf-8 -*-
"""GameForge K12 · 秒哒精选 7 项 · trajectory 重建源码落盘。

用法（密钥见项目根 `.env` 或环境变量 `MIAODA_API_KEY`）：
  python 05-工具脚本/miaoda_download_sources.py --resolve-only
  python 05-工具脚本/miaoda_download_sources.py --slug platformer
  python 05-工具脚本/miaoda_download_sources.py --all
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "config" / "miaoda_reference_registry.json"
OUTPUT_ROOT = ROOT / "03-背景与调研" / "data" / "秒哒精选源码"
MIAODA_API_PATH = ROOT / "tools" / "miaoda-skill" / "miaoda-app-builder" / "scripts" / "miaoda_api.py"
DEFAULT_BASE_URL = "https://api.miaoda.cn"

LOCAL_ENV_CANDIDATES: list[Path] = [
    ROOT / ".env",
    ROOT / "backend" / ".env",
    ROOT / "tools" / "miaoda-skill" / "miaoda-app-builder" / ".env",
]

KEY_FILE_PATTERNS: list[str] = [
    r"Game\.tsx?$",
    r"game/Game\.tsx?$",
    r"constants?\.tsx?$",
    r"config\.tsx?$",
    r"tuning",
    r"player",
    r"package\.json",
    r"需求文档\.md",
]

WORKSPACE_PREFIX_RE = re.compile(r"^/workspace/app-[^/]+/")


def _load_local_env() -> None:
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


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _save_registry(reg: dict[str, Any]) -> None:
    reg["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _save_json(REGISTRY_PATH, reg)


def _list_all_apps(api: Any, base_url: str, api_key: str) -> list[dict[str, Any]]:
    """Paginate list-apps until no more items."""
    all_items: list[dict[str, Any]] = []
    page = 1
    page_size = 50
    while True:
        result = api.list_apps(base_url, api_key, name="", page=page, size=page_size, brief=True)
        data = result.get("data", {})
        items = data.get("items", data.get("list", []))
        if not items:
            break
        all_items.extend(items)
        total = data.get("total", data.get("totalCount", 0))
        if total and len(all_items) >= int(total):
            break
        if len(items) < page_size:
            break
        page += 1
        time.sleep(0.3)
    return all_items


def _score_app_name(name: str, entry: dict[str, Any]) -> float:
    """Higher score = better match."""
    name_lower = name.lower()
    score = 0.0
    keywords: list[str] = entry.get("name_keywords", [])
    matched = 0
    for kw in keywords:
        if kw.lower() in name_lower:
            score += 2.0
            matched += 1
    if matched == 0:
        return 0.0
    user_title = entry.get("user_title", "")
    if user_title and user_title.lower() in name_lower:
        score += 5.0
    # Boost substring before version/parenthesis in user_title
    base_title = re.split(r"[（(v]", user_title, maxsplit=1)[0].strip()
    if base_title and len(base_title) >= 4 and base_title in name:
        score += 4.0
    # Prefer version suffixes mentioned in user title (v2, v3, etc.)
    ver_match = re.search(r"v(\d+)", user_title, re.I)
    if ver_match:
        ver = ver_match.group(0).lower()
        if ver in name_lower:
            score += 3.0
    display = entry.get("display_name", "")
    if display and display in name:
        score += 1.5
    return score


def resolve_app_ids(api: Any, base_url: str, api_key: str, reg: dict[str, Any]) -> None:
    print("Fetching app list …", flush=True)
    apps = _list_all_apps(api, base_url, api_key)
    print(f"  total apps: {len(apps)}", flush=True)

    for entry in reg.get("entries", []):
        slug: str = entry["slug"]
        scored: list[tuple[float, dict[str, Any]]] = []
        for app in apps:
            app_name = app.get("name", "")
            s = _score_app_name(app_name, entry)
            if s > 0:
                scored.append((s, app))
        scored.sort(key=lambda x: (-x[0], x[1].get("updatedAt", "")))

        if not scored:
            entry["match_status"] = "not_found"
            entry["candidates"] = []
            print(f"  [{slug}] NO MATCH", flush=True)
            continue

        best_score, best = scored[0]
        candidates = [
            {"appId": a.get("appId"), "name": a.get("name"), "score": s}
            for s, a in scored[:5]
        ]
        entry["candidates"] = candidates

        if best_score < 2.0:
            entry["match_status"] = "ambiguous"
            print(f"  [{slug}] ambiguous (best score {best_score:.1f}): {best.get('name')}", flush=True)
            continue

        app_id = best.get("appId", "")
        entry["app_id"] = app_id
        entry["matched_name"] = best.get("name", "")
        entry["match_score"] = best_score
        entry["match_status"] = "matched" if len(scored) == 1 or best_score >= scored[1][0] + 1 else "matched_best"
        entry["matched_at"] = _utc_now()

        host = best.get("host", "")
        if host and not host.startswith("http"):
            entry["preview_url"] = f"https://{host}"
        elif host:
            entry["preview_url"] = host
        else:
            entry["preview_url"] = f"https://{app_id}.appmiaoda.com"
        entry["editor_url"] = f"https://www.miaoda.cn/projects/{app_id}"

        print(f"  [{slug}] {entry['match_status']}: {app_id} · {best.get('name')}", flush=True)


def _normalize_path(raw_path: str) -> Optional[str]:
    if not raw_path:
        return None
    p = raw_path.replace("\\", "/")
    p = WORKSPACE_PREFIX_RE.sub("", p)
    if p.startswith("/"):
        p = p.lstrip("/")
    if not p or p.startswith(".."):
        return None
    return p


def _extract_event_id(event: dict[str, Any]) -> int:
    result = event.get("result", event)
    meta = result.get("metadata", {})
    eid = meta.get("eventId")
    if eid is not None:
        return int(eid)
    artifact = result.get("artifact", {})
    ameta = artifact.get("metadata", {})
    aeid = ameta.get("eventId")
    return int(aeid) if aeid is not None else 0


def fetch_full_trajectory(
    api: Any,
    base_url: str,
    api_key: str,
    app_id: str,
    max_retries: int = 3,
) -> list[dict[str, Any]]:
    """Fetch all trajectory events with pagination and retries."""
    all_events: list[dict[str, Any]] = []
    last_id = -1
    empty_rounds = 0

    while empty_rounds < 2:
        for attempt in range(max_retries):
            try:
                events, max_id, _ = api.fetch_trajectory_once(
                    base_url, api_key, app_id, last_id, timeout=60,
                )
                break
            except Exception as exc:
                if attempt + 1 >= max_retries:
                    raise
                print(f"    trajectory retry {attempt + 1}: {exc}", flush=True)
                time.sleep(2 ** attempt)
        else:
            events, max_id = [], last_id

        if not events:
            empty_rounds += 1
            break
        all_events.extend(events)
        if max_id <= last_id:
            empty_rounds += 1
        else:
            empty_rounds = 0
        last_id = max_id
        time.sleep(0.2)

    # Deduplicate by event id keeping last occurrence
    by_id: dict[int, dict[str, Any]] = {}
    no_id: list[dict[str, Any]] = []
    for ev in all_events:
        eid = _extract_event_id(ev)
        if eid:
            by_id[eid] = ev
        else:
            no_id.append(ev)
    ordered = [by_id[k] for k in sorted(by_id.keys())]
    return ordered + no_id


class SourceRebuilder:
    """Rebuild file tree from trajectory events."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.file_parts: dict[str, list[str]] = {}
        self.stats = {"add": 0, "edit": 0, "file_add": 0, "file_part": 0, "skipped": 0, "failed": 0}

    def process_events(self, events: list[dict[str, Any]]) -> None:
        indexed = sorted(events, key=_extract_event_id)
        for event in indexed:
            self._process_event(event)
        self._finalize_file_parts()

    def _process_event(self, event: dict[str, Any]) -> None:
        result = event.get("result", event)
        parts = result.get("parts", [])
        artifact = result.get("artifact", {})
        if artifact:
            parts = parts or artifact.get("parts", [])

        for part in parts:
            if part.get("kind") != "data":
                continue
            data = part.get("data", {})
            dtype = data.get("type", "")

            if dtype == "file_edit_action":
                self._apply_file_edit(data)
            elif dtype == "file_add_action":
                self._apply_file_add(data)
            elif dtype == "filePart":
                self._accumulate_file_part(data)

    def _apply_file_edit(self, data: dict[str, Any]) -> None:
        rel = _normalize_path(data.get("path", ""))
        if not rel:
            self.stats["skipped"] += 1
            return
        action = data.get("action", "")
        command = data.get("command", "")
        file_text = data.get("file_text")

        if action == "add" or (file_text and not self.files.get(rel)):
            if file_text is not None:
                self.files[rel] = file_text
                self.stats["add"] += 1
            return

        if command == "str_replace":
            old_str = data.get("old_str", "")
            new_str = data.get("new_str", "")
            if rel not in self.files:
                if file_text:
                    self.files[rel] = file_text
                    self.stats["add"] += 1
                else:
                    self.stats["failed"] += 1
                return
            content = self.files[rel]
            if old_str in content:
                self.files[rel] = content.replace(old_str, new_str, 1)
                self.stats["edit"] += 1
            elif file_text:
                self.files[rel] = file_text
                self.stats["edit"] += 1
            else:
                self.stats["failed"] += 1
        elif file_text:
            self.files[rel] = file_text
            self.stats["edit"] += 1
        else:
            self.stats["skipped"] += 1

    def _apply_file_add(self, data: dict[str, Any]) -> None:
        rel = _normalize_path(data.get("path", ""))
        content = data.get("content") or data.get("file_text", "")
        if not rel:
            self.stats["skipped"] += 1
            return
        self.files[rel] = content
        self.stats["file_add"] += 1

    def _accumulate_file_part(self, data: dict[str, Any]) -> None:
        fname = data.get("filename", "")
        text = data.get("text", "")
        if not fname:
            return
        self.file_parts.setdefault(fname, []).append(text)
        self.stats["file_part"] += 1

    def _finalize_file_parts(self) -> None:
        for fname, chunks in self.file_parts.items():
            rel = _normalize_path(fname) or fname
            self.files[rel] = "".join(chunks)

    def write_tree(self, src_root: Path) -> int:
        written = 0
        for rel, content in self.files.items():
            out = src_root / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content, encoding="utf-8")
            written += 1
        return written


def _is_key_file(path: str) -> bool:
    for pat in KEY_FILE_PATTERNS:
        if re.search(pat, path, re.I):
            return True
    return False


def _build_file_index(files: dict[str, str]) -> dict[str, Any]:
    paths = sorted(files.keys())
    key_files = [p for p in paths if _is_key_file(p)]
    return {
        "total_files": len(paths),
        "paths": paths,
        "key_files": key_files,
    }


def download_one(
    api: Any,
    base_url: str,
    api_key: str,
    entry: dict[str, Any],
) -> dict[str, Any]:
    slug: str = entry["slug"]
    app_id: str = entry.get("app_id", "")
    if not app_id:
        return {"slug": slug, "status": "skipped", "reason": "no app_id"}

    out_dir = OUTPUT_ROOT / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "slug": slug,
        "app_id": app_id,
        "started_at": _utc_now(),
        "status": "running",
    }

    print(f"\n=== [{slug}] downloading {app_id} ===", flush=True)

    try:
        # App detail
        detail = api.get_app_detail(base_url, api_key, app_id)
        detail_data = detail.get("data", {})
        app_meta = {
            "app_id": app_id,
            "name": entry.get("matched_name") or detail_data.get("name", ""),
            "user_title": entry.get("user_title", ""),
            "preview_url": entry.get("preview_url", ""),
            "editor_url": entry.get("editor_url", ""),
            "matched_at": entry.get("matched_at", _utc_now()),
            "appFocus": detail_data.get("appFocus", ""),
        }
        if detail_data.get("host"):
            host = detail_data["host"]
            app_meta["preview_url"] = host if host.startswith("http") else f"https://{host}"
        _save_json(out_dir / "app_meta.json", app_meta)

        # Conversation history (non-fatal on timeout)
        print("  fetching conversation history …", flush=True)
        history: list[dict[str, Any]] = []
        for attempt in range(3):
            try:
                history = api.get_conversation_history(
                    base_url, api_key, app_id, full=False, limit=200, fetch_timeout=60,
                )
                break
            except Exception as exc:
                if attempt + 1 >= 3:
                    print(f"    conversation history skipped: {exc}", flush=True)
                    history = []
                else:
                    time.sleep(2 ** attempt)
        _save_json(out_dir / "conversation_history.json", history)

        # Full trajectory
        print("  fetching full trajectory …", flush=True)
        events = fetch_full_trajectory(api, base_url, api_key, app_id)
        workflow_path = out_dir / "workflow_full.jsonl"
        with workflow_path.open("w", encoding="utf-8") as wf:
            for ev in events:
                wf.write(json.dumps({"ts": _utc_now(), "event": ev}, ensure_ascii=False) + "\n")
        manifest["trajectory_events"] = len(events)

        # Rebuild sources
        print("  rebuilding source tree …", flush=True)
        rebuilder = SourceRebuilder()
        rebuilder.process_events(events)
        src_root = out_dir / "src"
        if src_root.exists():
            import shutil
            shutil.rmtree(src_root)
        written = rebuilder.write_tree(src_root)
        manifest["files_written"] = written
        manifest["rebuild_stats"] = rebuilder.stats

        # 需求文档.md
        prd_name = "docs/需求文档.md"
        docs_dir = out_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        prd_content = rebuilder.files.get("需求文档.md") or rebuilder.files.get(prd_name, "")
        for k, v in rebuilder.files.items():
            if k.endswith("需求文档.md"):
                prd_content = v
                break
        if prd_content:
            (docs_dir / "需求文档.md").write_text(prd_content, encoding="utf-8")
            manifest["has_prd"] = True
        else:
            manifest["has_prd"] = False

        file_index = _build_file_index(rebuilder.files)
        _save_json(out_dir / "file_index.json", file_index)

        manifest["status"] = "ok" if written > 0 else "empty"
        manifest["finished_at"] = _utc_now()
        _save_json(out_dir / "manifest.json", manifest)
        print(f"  done: {written} files, {len(events)} events", flush=True)
        return manifest

    except Exception as exc:
        manifest["status"] = "error"
        manifest["error"] = str(exc)
        manifest["traceback"] = traceback.format_exc()
        manifest["finished_at"] = _utc_now()
        _save_json(out_dir / "manifest.json", manifest)
        print(f"  ERROR: {exc}", flush=True)
        return manifest


def enrich_urls_from_detail(api: Any, base_url: str, api_key: str, entry: dict[str, Any]) -> None:
    app_id = entry.get("app_id", "")
    if not app_id:
        return
    try:
        detail = api.get_app_detail(base_url, api_key, app_id)
        data = detail.get("data", {})
        host = data.get("host", "")
        if host:
            entry["preview_url"] = host if host.startswith("http") else f"https://{host}"
        entry["editor_url"] = f"https://www.miaoda.cn/projects/{app_id}"
        if data.get("name") and not entry.get("matched_name"):
            entry["matched_name"] = data["name"]
    except Exception as exc:
        entry["detail_error"] = str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="秒哒精选 7 项 · trajectory 源码落盘")
    parser.add_argument("--resolve-only", action="store_true", help="仅 list-apps 匹配 appId")
    parser.add_argument("--slug", type=str, default="", help="单个 slug")
    parser.add_argument("--all", action="store_true", help="全部 7 项")
    args = parser.parse_args()

    _load_local_env()
    api_key = os.environ.get("MIAODA_API_KEY", "")
    base_url = os.environ.get("MIAODA_BASE_URL", DEFAULT_BASE_URL)
    if not api_key:
        print("ERROR: MIAODA_API_KEY not set", file=sys.stderr)
        return 1

    api = _load_miaoda_api()
    reg = _load_registry()
    entries: list[dict[str, Any]] = reg.get("entries", [])

    if args.slug:
        entries = [e for e in entries if e["slug"] == args.slug]
        if not entries:
            print(f"Unknown slug: {args.slug}", file=sys.stderr)
            return 1

    resolve_app_ids(api, base_url, api_key, reg)
    for entry in reg.get("entries", []):
        enrich_urls_from_detail(api, base_url, api_key, entry)
    _save_registry(reg)

    if args.resolve_only:
        print("\nRegistry updated (resolve-only).", flush=True)
        return 0

    if not args.all and not args.slug:
        print("Specify --all, --slug, or --resolve-only", file=sys.stderr)
        return 1

    results: list[dict[str, Any]] = []
    for entry in entries:
        if entry.get("match_status") in ("not_found", "ambiguous") and not entry.get("app_id"):
            results.append({"slug": entry["slug"], "status": "skipped", "reason": entry.get("match_status")})
            continue
        results.append(download_one(api, base_url, api_key, entry))
        time.sleep(1)

    summary_path = OUTPUT_ROOT / "download_summary.json"
    _save_json(summary_path, {"at": _utc_now(), "results": results})
    ok = sum(1 for r in results if r.get("status") == "ok")
    print(f"\nSummary: {ok}/{len(results)} ok → {summary_path}", flush=True)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
