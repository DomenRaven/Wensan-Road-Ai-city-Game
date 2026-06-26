# -*- coding: utf-8 -*-
"""GameForge K12 · 秒哒精选 7 项 → Godot game_config 一键转译。

从本地落盘秒哒源码提取 tuning/theme，补丁 templates/{slug}/config/game_config.json（±30% clamp）。

用法：
  python 05-工具脚本/miaoda_apply_translation.py --all
  python 05-工具脚本/miaoda_apply_translation.py --slug platformer
  python 05-工具脚本/miaoda_apply_translation.py --all --dry-run
  python 05-工具脚本/miaoda_apply_translation.py --all --backup --verify
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "config" / "miaoda_reference_registry.json"
MAPPINGS_PATH = ROOT / "config" / "miaoda_translation_mappings.json"
WORKSHEET_TEMPLATE = ROOT / "03-背景与调研" / "config" / "miaoda_translation_worksheet.template.json"
SOURCE_ROOT = ROOT / "03-背景与调研" / "data" / "秒哒精选源码"
WORKSHEET_OUT_DIR = ROOT / "03-背景与调研" / "config"
SUMMARY_PATH = SOURCE_ROOT / "translation_summary.json"
TEMPLATES = ROOT / "templates"

DEFAULT_GODOT = Path(
    r"F:\Godot\Godot_v4.6.3-stable_win64.exe\Godot_v4.6.3-stable_win64_console.exe"
)

CONST_OBJECT_RE = re.compile(
    r"export\s+const\s+(\w+)\s*=\s*\{([^}]+)\}",
    re.DOTALL,
)
KV_RE = re.compile(r"(\w+)\s*:\s*(-?[\d.]+)")
INITIAL_STATE_RE = re.compile(
    r"const\s+INITIAL_STATE\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}",
    re.DOTALL,
)
PRD_TITLE_RE = re.compile(r"###\s*1\.1\s*应用名称\s*\n\s*(.+?)(?:\n|$)")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def clamp_value(base_val: float, new_val: float, clamp_percent: float) -> float:
    if base_val == 0:
        return new_val
    ratio = abs(new_val / base_val)
    low = 1.0 - clamp_percent / 100.0
    high = 1.0 + clamp_percent / 100.0
    if ratio < low:
        return base_val * low
    if ratio > high:
        return base_val * high
    return new_val


def get_nested(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def set_nested(data: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    current = data
    for part in parts[:-1]:
        nxt = current.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            current[part] = nxt
        current = nxt
    current[parts[-1]] = value


def _glob_one(base: Path, pattern: str) -> Optional[Path]:
    if not base.is_dir():
        return None
    hits = sorted(base.glob(pattern))
    return hits[0] if hits else None


def find_constants_file(slug_dir: Path) -> Optional[Path]:
    return _glob_one(slug_dir, "src/**/constants.ts") or _glob_one(slug_dir, "src/**/game/constants.ts")


def parse_constants_object(text: str, export_name: str) -> dict[str, float]:
    for m in CONST_OBJECT_RE.finditer(text):
        if m.group(1) != export_name:
            continue
        body = m.group(2)
        out: dict[str, float] = {}
        for km in KV_RE.finditer(body):
            out[km.group(1)] = float(km.group(2))
        return out
    return {}


def parse_game_store(text: str) -> dict[str, float]:
    m = INITIAL_STATE_RE.search(text)
    if not m:
        return {}
    body = m.group(1)
    out: dict[str, float] = {}
    for km in KV_RE.finditer(body):
        out[km.group(1)] = float(km.group(2))
    return out


def parse_prd_title(slug_dir: Path) -> str:
    for rel in ("docs/需求文档.md", "src/需求文档.md"):
        p = slug_dir / rel
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        m = PRD_TITLE_RE.search(text)
        if m:
            return m.group(1).strip().strip("\\n")
    return ""


def apply_transform(
    transform: str,
    raw: float,
    godot_base: float,
    field: dict[str, Any],
    constants: dict[str, float],
) -> float:
    baseline = float(field.get("miaoda_baseline", godot_base or 1.0))

    if transform == "direct":
        return raw
    if transform == "abs":
        return abs(raw)
    if transform == "ratio":
        if baseline == 0:
            return godot_base
        return godot_base * (raw / baseline)
    if transform == "inverse_ratio":
        if raw == 0:
            return godot_base
        return godot_base * (baseline / raw)
    if transform == "obstacle_chance":
        return max(0.0, min(1.0, 1.0 - raw))
    if transform == "sum":
        k2 = field.get("miaoda_key_2", "")
        extra = constants.get(k2, 0.0)
        return raw + extra
    if transform == "ms_to_sec_avg":
        base_ms = raw
        max_ms = float(field.get("_regex_max_val", 0))
        avg_ms = base_ms + max_ms / 2.0
        return avg_ms / 1000.0
    return raw


def extract_miaoda_values(
    slug_dir: Path,
    genre_cfg: dict[str, Any],
) -> tuple[dict[str, float], dict[str, float], dict[str, float], set[str]]:
    values: dict[str, float] = {}
    pre_transformed: set[str] = set()
    const_file = find_constants_file(slug_dir)
    constants: dict[str, float] = {}
    if const_file:
        text = const_file.read_text(encoding="utf-8")
        export_name = genre_cfg.get("constants_export", "CONSTANTS")
        constants = parse_constants_object(text, export_name)

    store_file = _glob_one(slug_dir, "src/**/gameStore.ts") or _glob_one(slug_dir, "src/**/store/gameStore.ts")
    store_vals: dict[str, float] = {}
    if store_file:
        store_vals = parse_game_store(store_file.read_text(encoding="utf-8"))

    for field in genre_cfg.get("fields", []):
        if field.get("regex"):
            pattern = field["regex"]
            inline = field.get("inline_file", genre_cfg.get("inline_file", ""))
            if not inline:
                continue
            hit = _glob_one(slug_dir, inline)
            if not hit:
                continue
            text = hit.read_text(encoding="utf-8")
            m = re.search(pattern, text)
            if not m:
                continue
            raw = float(m.group(1))
            godot_path = field.get("godot_path", pattern)
            transform = field.get("transform", "direct")
            if transform == "ms_to_sec_avg" and field.get("regex_max"):
                m2 = re.search(field["regex_max"], text)
                max_ms = float(m2.group(1)) if m2 else 0.0
                values[godot_path] = (raw + max_ms / 2.0) / 1000.0
                pre_transformed.add(godot_path)
            else:
                values[godot_path] = raw
            continue

        source = field.get("source", "constants")
        key = field.get("miaoda_key", "")
        if source == "gameStore":
            if key in store_vals:
                values[field["godot_path"]] = store_vals[key]
        elif key in constants:
            values[field["godot_path"]] = constants[key]

    return values, constants, store_vals, pre_transformed


def resolve_godot_path() -> Path:
    for env_path in (ROOT / "backend" / ".env", ROOT / ".env"):
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("GODOT_PATH="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                p = Path(val)
                if p.is_file():
                    return p
    return DEFAULT_GODOT


def run_godot_smoke(slug: str) -> tuple[bool, list[str]]:
    godot = resolve_godot_path()
    project = TEMPLATES / slug
    if not godot.is_file():
        return False, [f"Godot not found: {godot}"]
    try:
        proc = subprocess.run(
            [str(godot), "--path", str(project), "--headless", "--quit-after", "2"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False, ["Godot smoke timeout"]
    combined = proc.stdout + proc.stderr
    errors = [
        ln.strip()
        for ln in combined.splitlines()
        if "ERROR:" in ln
        and "RemoteException" not in ln
        and "resources still in use at exit" not in ln
    ]
    return len(errors) == 0, errors[:8]


def translate_slug(
    slug: str,
    entry: dict[str, Any],
    mappings: dict[str, Any],
    worksheet_template: dict[str, Any],
    *,
    dry_run: bool,
    backup: bool,
    verify: bool,
) -> dict[str, Any]:
    genre_cfg = mappings["genres"].get(slug)
    if not genre_cfg:
        return {"slug": slug, "status": "skipped", "reason": "no mapping"}

    slug_dir = SOURCE_ROOT / slug
    config_path = TEMPLATES / slug / "config" / "game_config.json"
    if not config_path.is_file():
        return {"slug": slug, "status": "error", "reason": f"missing {config_path}"}
    if not slug_dir.is_dir():
        return {"slug": slug, "status": "error", "reason": f"missing source {slug_dir}"}

    base_config = _load_json(config_path)
    working = copy.deepcopy(base_config)
    base_tuning = base_config.get("tuning", {})
    clamp_pct = float(mappings.get("clamp_percent", 30))

    miaoda_by_path, constants, _store, pre_transformed = extract_miaoda_values(slug_dir, genre_cfg)
    changes: list[dict[str, Any]] = []

    for field in genre_cfg.get("fields", []):
        godot_path = field.get("godot_path")
        if not godot_path:
            continue

        raw: Optional[float] = None
        if godot_path in miaoda_by_path:
            raw = miaoda_by_path[godot_path]
        elif field.get("miaoda_key") and field["miaoda_key"] in constants:
            raw = constants[field["miaoda_key"]]
        elif field.get("transform") == "sum":
            k1 = field.get("miaoda_key", "")
            if k1 in constants:
                raw = constants[k1]

        if raw is None:
            continue

        base_val = get_nested(base_tuning, godot_path)
        if not isinstance(base_val, (int, float)):
            continue

        transform = field.get("transform", "direct")
        if godot_path in pre_transformed:
            transform = "direct"
        proposed = apply_transform(transform, raw, float(base_val), field, constants)
        clamped = clamp_value(float(base_val), float(proposed), clamp_pct)
        if isinstance(base_val, int):
            final_val: int | float = int(round(clamped))
        else:
            final_val = round(clamped, 4) if isinstance(base_val, float) else clamped

        changes.append({
            "godot_path": godot_path,
            "miaoda_raw": raw,
            "godot_before": base_val,
            "proposed": proposed,
            "godot_after": final_val,
            "clamped": final_val != proposed,
            "transform": transform,
        })
        set_nested(working.setdefault("tuning", {}), godot_path, final_val)

    theme_changes: dict[str, str] = {}
    if genre_cfg.get("theme_from_prd"):
        title = parse_prd_title(slug_dir)
        if title:
            working.setdefault("meta", {})["display_name"] = title
            theme_changes["meta.display_name"] = title
            working.setdefault("theme", {})["title"] = title
            theme_changes["theme.title"] = title

    preview = entry.get("preview_url", "")

    ws_tpl = copy.deepcopy(worksheet_template.get("entries", {}).get(slug, {}))
    ws_tpl["preview_url"] = preview
    ws_tpl["verified"] = False
    ws_tpl["verified_at"] = ""
    for ch in changes:
        path = ch["godot_path"]
        cand = ws_tpl.get("tuning_candidates", {}).get(path)
        if isinstance(cand, dict):
            cand["miaoda_value"] = ch["miaoda_raw"]
            cand["godot_default"] = ch["godot_before"]
            cand["proposed"] = ch["godot_after"]
            note = f"transform={ch['transform']}"
            if ch["clamped"]:
                note += "; clamped"
            cand["notes"] = note
    for tk, tv in theme_changes.items():
        short = tk.split(".")[-1]
        tc = ws_tpl.get("theme_candidates", {}).get(short)
        if isinstance(tc, dict):
            tc["miaoda"] = tv
            tc["proposed"] = tv

    worksheet_path = WORKSHEET_OUT_DIR / f"miaoda_translation_worksheet_{slug}.json"

    if not dry_run:
        if backup:
            bak = config_path.with_suffix(".json.pre_miaoda_translation")
            shutil.copy2(config_path, bak)
        _save_json(config_path, working)
        _save_json(worksheet_path, ws_tpl)

    result: dict[str, Any] = {
        "slug": slug,
        "status": "ok",
        "app_id": entry.get("app_id", ""),
        "preview_url": preview,
        "changes_count": len(changes),
        "changes": changes,
        "theme_changes": theme_changes,
        "worksheet": str(worksheet_path.relative_to(ROOT)).replace("\\", "/"),
        "dry_run": dry_run,
    }

    if verify and not dry_run:
        ok, errs = run_godot_smoke(slug)
        result["godot_smoke"] = "pass" if ok else "fail"
        result["godot_errors"] = errs
        if not ok:
            result["status"] = "verify_fail"

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="秒哒精选 → Godot game_config 一键转译")
    parser.add_argument("--all", action="store_true", help="处理全部 7 slug")
    parser.add_argument("--slug", type=str, default="", help="单个 slug")
    parser.add_argument("--dry-run", action="store_true", help="只报告不写入")
    parser.add_argument("--backup", action="store_true", help="写入前备份 game_config.json")
    parser.add_argument("--verify", action="store_true", help="写入后 Godot headless smoke")
    args = parser.parse_args()

    if not args.all and not args.slug:
        parser.error("需要 --all 或 --slug")

    registry = _load_json(REGISTRY_PATH)
    mappings = _load_json(MAPPINGS_PATH)
    worksheet_template = _load_json(WORKSHEET_TEMPLATE)

    entries_by_slug = {e["slug"]: e for e in registry.get("entries", [])}
    order: list[str] = mappings.get("slug_order", list(entries_by_slug.keys()))
    if args.slug:
        order = [args.slug]

    results: list[dict[str, Any]] = []
    for slug in order:
        entry = entries_by_slug.get(slug, {"slug": slug})
        print(f"\n=== [{slug}] ===", flush=True)
        res = translate_slug(
            slug,
            entry,
            mappings,
            worksheet_template,
            dry_run=args.dry_run,
            backup=args.backup,
            verify=args.verify,
        )
        results.append(res)
        status = res.get("status", "?")
        n = res.get("changes_count", 0)
        print(f"  {status}: {n} tuning fields", flush=True)
        for ch in res.get("changes", []):
            flag = " *" if ch.get("clamped") else ""
            print(
                f"    {ch['godot_path']}: {ch['godot_before']} -> {ch['godot_after']}{flag}",
                flush=True,
            )
        if res.get("theme_changes"):
            print(f"  theme: {res['theme_changes']}", flush=True)
        if res.get("godot_smoke"):
            print(f"  godot smoke: {res['godot_smoke']}", flush=True)

    summary = {"at": _utc_now(), "dry_run": args.dry_run, "results": results}
    if not args.dry_run:
        _save_json(SUMMARY_PATH, summary)

    ok = sum(1 for r in results if r.get("status") == "ok")
    print(f"\nDone: {ok}/{len(results)} ok", flush=True)
    if args.dry_run:
        print("(dry-run: no files written)", flush=True)
    else:
        print(f"Summary: {SUMMARY_PATH}", flush=True)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
