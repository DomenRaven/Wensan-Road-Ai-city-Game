#!/usr/bin/env python3
"""Generate assets/previews/{genre}.png from theme_paths.json hero sprites."""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
THEME_PATHS: Path = ROOT / "assets" / "theme_paths.json"
PREVIEWS: Path = ROOT / "assets" / "previews"
MANIFEST: Path = PREVIEWS / "manifest.json"

KEY_PRIORITY: list[str] = [
    "player_sprite",
    "player",
    "ball_sprite",
    "table_sprite",
    "crop_sprite",
    "tower_sprite",
]


def pick_sprite_path(genre_cfg: dict[str, object]) -> str:
    for key in KEY_PRIORITY:
        val: object = genre_cfg.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    for key, val in genre_cfg.items():
        if key.endswith("_sprite") and isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def main() -> int:
    data: dict[str, object] = json.loads(THEME_PATHS.read_text(encoding="utf-8"))
    genres: dict[str, object] = data.get("genres", {})  # type: ignore[assignment]
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    for slug, cfg in genres.items():
        if not isinstance(cfg, dict):
            continue
        rel: str = pick_sprite_path(cfg)
        dest: Path = PREVIEWS / f"{slug}.png"
        record: dict[str, object] = {"genre": slug, "source": rel, "status": "skipped"}
        if not rel:
            record["status"] = "no_path"
            results.append(record)
            continue
        src: Path = ROOT / rel.replace("/", "\\")
        if not src.is_file():
            record["status"] = "missing"
            results.append(record)
            print(f"MISS {slug}: {rel}")
            continue
        shutil.copy2(src, dest)
        record["status"] = "copied"
        record["dest"] = str(dest.relative_to(ROOT))
        results.append(record)
        print(f"OK   {slug}")
    manifest: dict[str, object] = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "entries": results,
        "ok": sum(1 for r in results if r["status"] == "copied"),
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": manifest["ok"], "total": len(results)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
