#!/usr/bin/env python3
"""Import curated SFX from local library into assets/sfx/."""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

ROOT: Path = Path(__file__).resolve().parents[1]
ASSETS: Path = ROOT / "assets"
SFX: Path = ASSETS / "sfx"
MANIFEST: Path = ASSETS / "audio_paths.json"

DEFAULT_SOURCE: Path = Path(r"D:\AAA学习\大一上\数字音视频\素材-音效")


class SfxRule(TypedDict):
    dest: str
    patterns: list[str]


RULES: list[SfxRule] = [
    {"dest": "ui/click.wav", "patterns": ["click_01.wav", "click1.wav", "CLICK.WAV"]},
    {"dest": "ui/button.wav", "patterns": ["BUTTON1.WAV", "Button11.WAV"]},
    {"dest": "ui/select.wav", "patterns": ["SELECT (44100 Hz).mp3", "SELECT.WAV"]},
    {"dest": "hit/punch.wav", "patterns": ["PUNCH1.WAV", "PUNCH2.WAV"]},
    {"dest": "hit/impact.wav", "patterns": ["Explosive impact.wav", "Electronic impact.wav", "CATHIT.WAV"]},
    {"dest": "shoot/gun.wav", "patterns": ["GUN1.WAV", "BIGGUN.WAV"]},
    {"dest": "shoot/laser.wav", "patterns": ["LASER1 (44100 Hz).mp3", "LASER1.WAV"]},
    {"dest": "fx/explode.wav", "patterns": ["EXPLODEA.WAV", "c4_explode1 (44100 Hz).mp3"]},
    {"dest": "fx/coin.wav", "patterns": ["COINDROP.WAV", "COINROLL.WAV"]},
    {"dest": "fx/jump.wav", "patterns": ["JUMP.WAV", "jump.wav"]},
]


def find_file(source_root: Path, names: list[str]) -> Path | None:
    name_set: set[str] = {n.lower() for n in names}
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".wav", ".mp3", ".ogg"}:
            continue
        if path.name.lower() in name_set:
            return path
    return None


def import_sfx(source_root: Path) -> dict[str, object]:
    if not source_root.is_dir():
        raise FileNotFoundError(f"Source not found: {source_root}")
    entries: list[dict[str, object]] = []
    mapping: dict[str, str] = {}
    for rule in RULES:
        dest_rel: str = rule["dest"]
        dest: Path = SFX / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        found: Path | None = find_file(source_root, rule["patterns"])
        record: dict[str, object] = {
            "dest": f"assets/sfx/{dest_rel}",
            "patterns": rule["patterns"],
            "status": "missing",
        }
        if found is not None:
            if found.suffix.lower() != dest.suffix.lower():
                dest = dest.with_suffix(found.suffix.lower())
                record["dest"] = f"assets/sfx/{dest.relative_to(SFX).as_posix()}"
            shutil.copy2(found, dest)
            record["status"] = "copied"
            record["source"] = str(found)
            record["bytes"] = dest.stat().st_size
            key: str = dest_rel.split("/")[0]
            if key == "ui":
                mapping.setdefault("ui_click", record["dest"])
                if "button" in dest_rel:
                    mapping["ui_button"] = str(record["dest"])
                if "select" in dest_rel:
                    mapping["ui_select"] = str(record["dest"])
            elif key == "hit":
                mapping.setdefault("hit_default", str(record["dest"]))
            elif key == "shoot":
                mapping.setdefault("shoot_gun", str(record["dest"]))
                if "laser" in dest_rel:
                    mapping["shoot_laser"] = str(record["dest"])
            elif key == "fx":
                if "explode" in dest_rel:
                    mapping["fx_explode"] = str(record["dest"])
                if "coin" in dest_rel:
                    mapping["fx_collect"] = str(record["dest"])
        entries.append(record)
        print(f"{record['status']:8} {dest_rel}")
    genres: dict[str, dict[str, str]] = {
        "all": {
            "ui_click": mapping.get("ui_click", ""),
            "ui_confirm": mapping.get("ui_button", mapping.get("ui_click", "")),
        },
        "shooter": {"shoot": mapping.get("shoot_gun", ""), "hit": mapping.get("hit_default", "")},
        "shmup": {"shoot": mapping.get("shoot_laser", ""), "hit": mapping.get("fx_explode", "")},
        "survivor": {"hit": mapping.get("hit_default", ""), "collect": mapping.get("fx_collect", "")},
        "fighting": {"hit": mapping.get("hit_default", "")},
        "platformer": {"jump": mapping.get("fx_jump", ""), "collect": mapping.get("fx_collect", "")},
    }
    manifest: dict[str, object] = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root),
        "license": "local-education-library",
        "entries": entries,
        "mapping": mapping,
        "genres": genres,
        "kiosk": {
            "click": mapping.get("ui_click", ""),
            "success": mapping.get("ui_button", ""),
            "step": mapping.get("ui_select", mapping.get("ui_click", "")),
        },
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    ok: int = sum(1 for e in entries if e["status"] == "copied")
    return {"ok": ok, "total": len(entries), "manifest": str(MANIFEST)}


def main() -> int:
    source: Path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    try:
        result = import_sfx(source)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] > 0 else 1
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
