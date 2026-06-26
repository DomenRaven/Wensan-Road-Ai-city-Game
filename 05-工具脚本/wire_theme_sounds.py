#!/usr/bin/env python3
"""Link Kenney impact/interface audio into templates and theme.sounds in game_config.json."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

ROOT: Path = Path(__file__).resolve().parents[1]
GENRES: list[str] = [
    "platformer",
    "tower_defense",
    "shmup",
    "shooter",
    "survivor",
    "fighting",
    "parkour",
    "life_sim",
    "sports_race",
    "pingpong",
    "racing",
]

IMPACT_SRC: Path = ROOT / "assets/kenney/impact-sounds/extracted"
IFACE_SRC: Path = ROOT / "assets/kenney/interface-sounds/extracted"
IMPACT: str = "res://assets/kenney/impact-sounds/Audio"
IFACE: str = "res://assets/kenney/interface-sounds/Audio"


class SoundBlock(TypedDict):
    interface: dict[str, str]
    impact: dict[str, str]


INTERFACE_SOUNDS: dict[str, str] = {
    "click": f"{IFACE}/click_001.ogg",
    "confirm": f"{IFACE}/confirmation_001.ogg",
    "back": f"{IFACE}/back_001.ogg",
    "error": f"{IFACE}/error_001.ogg",
    "select": f"{IFACE}/select_001.ogg",
}

GENRE_IMPACT: dict[str, dict[str, str]] = {
    "platformer": {
        "hit": f"{IMPACT}/impactGeneric_light_000.ogg",
        "collect": f"{IMPACT}/impactBell_heavy_000.ogg",
        "jump": f"{IMPACT}/footstep_grass_000.ogg",
    },
    "parkour": {
        "hit": f"{IMPACT}/impactGeneric_light_000.ogg",
        "jump": f"{IMPACT}/footstep_grass_000.ogg",
    },
    "sports_race": {
        "hit": f"{IMPACT}/impactWood_heavy_000.ogg",
        "jump": f"{IMPACT}/footstep_grass_000.ogg",
        "land": f"{IMPACT}/footstep_concrete_000.ogg",
    },
    "fighting": {
        "hit": f"{IMPACT}/impactPunch_medium_000.ogg",
        "block": f"{IMPACT}/impactMetal_light_000.ogg",
    },
    "shooter": {
        "shoot": f"{IMPACT}/impactMining_000.ogg",
        "hit": f"{IMPACT}/impactMetal_light_000.ogg",
        "hurt": f"{IMPACT}/impactGeneric_light_000.ogg",
    },
    "shmup": {
        "shoot": f"{IMPACT}/impactTin_medium_000.ogg",
        "hit": f"{IMPACT}/impactMetal_heavy_000.ogg",
        "explode": f"{IMPACT}/impactGlass_heavy_000.ogg",
    },
    "survivor": {
        "shoot": f"{IMPACT}/impactMining_000.ogg",
        "hit": f"{IMPACT}/impactSoft_heavy_000.ogg",
        "collect": f"{IMPACT}/impactBell_heavy_000.ogg",
    },
    "tower_defense": {
        "shoot": f"{IMPACT}/impactTin_medium_000.ogg",
        "hit": f"{IMPACT}/impactGeneric_light_000.ogg",
    },
    "racing": {
        "crash": f"{IMPACT}/impactMetal_heavy_000.ogg",
        "pass": f"{IMPACT}/impactBell_heavy_000.ogg",
    },
    "pingpong": {
        "rally": f"{IMPACT}/impactTin_medium_000.ogg",
        "score": f"{IFACE}/confirmation_002.ogg",
    },
    "life_sim": {
        "harvest": f"{IMPACT}/impactWood_heavy_000.ogg",
        "cook": f"{IFACE}/drop_001.ogg",
        "serve": f"{IFACE}/pluck_001.ogg",
    },
}


def ensure_junction(link: Path, target: Path) -> str:
    if link.exists():
        return "exists"
    link.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        check=True,
        capture_output=True,
        text=True,
    )
    return "linked"


def link_audio_packs() -> list[str]:
    messages: list[str] = []
    for genre in GENRES:
        kenney_dir: Path = ROOT / "templates" / genre / "assets" / "kenney"
        for name, src in (
            ("impact-sounds", IMPACT_SRC),
            ("interface-sounds", IFACE_SRC),
        ):
            status: str = ensure_junction(kenney_dir / name, src)
            messages.append(f"{genre}/{name}: {status}")
    return messages


def build_sounds(genre: str) -> SoundBlock:
    impact: dict[str, str] = dict(GENRE_IMPACT.get(genre, {"hit": f"{IMPACT}/impactGeneric_light_000.ogg"}))
    return {"interface": dict(INTERFACE_SOUNDS), "impact": impact}


def patch_configs() -> list[str]:
    messages: list[str] = []
    for genre in GENRES:
        config_path: Path = ROOT / "templates" / genre / "config" / "game_config.json"
        data: dict[str, object] = json.loads(config_path.read_text(encoding="utf-8"))
        theme: dict[str, object] = data.get("theme", {})  # type: ignore[assignment]
        if not isinstance(theme, dict):
            theme = {}
        theme["sounds"] = build_sounds(genre)
        data["theme"] = theme
        config_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        messages.append(f"patched {genre}")
    return messages


def verify_paths() -> list[str]:
    errors: list[str] = []
    for genre in GENRES:
        sounds: SoundBlock = build_sounds(genre)
        for group in ("interface", "impact"):
            block: dict[str, str] = sounds[group]  # type: ignore[literal-required]
            for key, res_path in block.items():
                rel: str = res_path.removeprefix("res://")
                disk: Path = ROOT / "templates" / genre / rel
                if not disk.exists():
                    errors.append(f"missing {genre} {group}.{key} -> {disk}")
    return errors


def main() -> int:
    links: list[str] = link_audio_packs()
    patches: list[str] = patch_configs()
    errors: list[str] = verify_paths()
    print(json.dumps({"links": len(links), "patched": len(patches), "errors": errors}, ensure_ascii=False, indent=2))
    for line in links:
        print(line)
    for line in patches:
        print(line)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
