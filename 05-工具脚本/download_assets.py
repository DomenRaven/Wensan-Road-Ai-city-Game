#!/usr/bin/env python3
"""Download Kenney CC0 + fonts + Godot-friendly assets into assets/."""
from __future__ import annotations

import json
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

ROOT: Path = Path(__file__).resolve().parents[1]
ASSETS: Path = ROOT / "assets"
KENNEY: Path = ASSETS / "kenney"
FONTS: Path = ASSETS / "fonts"
THIRD: Path = ASSETS / "third_party"
MANIFEST: Path = ASSETS / "manifest.json"

OGA: str = "https://opengameart.org/sites/default/files"
GH: str = "https://raw.githubusercontent.com"


class AssetEntry(TypedDict):
    url: str
    dest_dir: str
    filename: str
    license: str
    genre_tags: list[str]


ASSETS_TO_FETCH: list[AssetEntry] = [
    {
        "url": f"{OGA}/Platformer%20Pack%20Redux%20%28360%20assets%29.zip",
        "dest_dir": "kenney/platformer-pack-redux",
        "filename": "platformer-pack-redux.zip",
        "license": "CC0",
        "genre_tags": ["platformer", "parkour", "fighting"],
    },
    {
        "url": f"{OGA}/platformerGraphicsDeluxe_Updated.zip",
        "dest_dir": "kenney/platformer-art-deluxe",
        "filename": "platformer-art-deluxe.zip",
        "license": "CC0",
        "genre_tags": ["platformer", "parkour"],
    },
    {
        "url": f"{OGA}/kenney_pixel-platformer.zip",
        "dest_dir": "kenney/pixel-platformer",
        "filename": "pixel-platformer.zip",
        "license": "CC0",
        "genre_tags": ["platformer", "life_sim"],
    },
    {
        "url": f"{OGA}/SpaceShooterRedux.zip",
        "dest_dir": "kenney/space-shooter-redux",
        "filename": "space-shooter-redux.zip",
        "license": "CC0",
        "genre_tags": ["shooter", "shmup"],
    },
    {
        "url": f"{OGA}/topdown-shooter.zip",
        "dest_dir": "kenney/topdown-shooter",
        "filename": "topdown-shooter.zip",
        "license": "CC0",
        "genre_tags": ["shooter", "survivor"],
    },
    {
        "url": f"{OGA}/Tower%20Defense%20%28top-down%29.zip",
        "dest_dir": "kenney/tower-defense-topdown",
        "filename": "tower-defense-topdown.zip",
        "license": "CC0",
        "genre_tags": ["tower_defense"],
    },
    {
        "url": f"{OGA}/kenney_tower-defense-kit.zip",
        "dest_dir": "kenney/tower-defense-kit-3d",
        "filename": "tower-defense-kit-3d.zip",
        "license": "CC0",
        "genre_tags": ["tower_defense"],
    },
    {
        "url": f"{OGA}/racing-pack.zip",
        "dest_dir": "kenney/racing-pack",
        "filename": "racing-pack.zip",
        "license": "CC0",
        "genre_tags": ["racing", "sports_race"],
    },
    {
        "url": f"{OGA}/kenney_sportsPack.zip",
        "dest_dir": "kenney/sports-pack",
        "filename": "sports-pack.zip",
        "license": "CC0",
        "genre_tags": ["pingpong", "sports_race"],
    },
    {
        "url": f"{OGA}/kenney_microroguelike_1.2.zip",
        "dest_dir": "kenney/micro-roguelike",
        "filename": "micro-roguelike.zip",
        "license": "CC0",
        "genre_tags": ["survivor", "life_sim"],
    },
    {
        "url": f"{OGA}/kenney_ui-pack.zip",
        "dest_dir": "kenney/ui-pack",
        "filename": "ui-pack.zip",
        "license": "CC0",
        "genre_tags": ["all"],
    },
    {
        "url": f"{OGA}/Platformer%20Art%20Pixel%20Redux.zip",
        "dest_dir": "kenney/platformer-art-pixel-redux",
        "filename": "platformer-art-pixel-redux.zip",
        "license": "CC0",
        "genre_tags": ["platformer", "fighting"],
    },
    {
        "url": f"{GH}/adobe-fonts/source-han-sans/release/SubsetOTF/CN/SourceHanSansCN-Regular.otf",
        "dest_dir": "fonts",
        "filename": "SourceHanSansCN-Regular.otf",
        "license": "OFL (Adobe Source Han Sans)",
        "genre_tags": ["ui"],
    },
    {
        "url": f"{GH}/adobe-fonts/source-han-sans/release/SubsetOTF/CN/SourceHanSansCN-Bold.otf",
        "dest_dir": "fonts",
        "filename": "SourceHanSansCN-Bold.otf",
        "license": "OFL (Adobe Source Han Sans)",
        "genre_tags": ["ui"],
    },
    {
        "url": f"{OGA}/Digital_SFX_Set.zip",
        "dest_dir": "kenney/digital-audio",
        "filename": "digital-audio.zip",
        "license": "CC0",
        "genre_tags": ["shooter", "shmup", "all"],
    },
    {
        "url": f"{OGA}/RPGsounds_Kenney.zip",
        "dest_dir": "kenney/rpg-sounds",
        "filename": "rpg-sounds.zip",
        "license": "CC0",
        "genre_tags": ["all"],
    },
    {
        "url": f"{OGA}/JumperPack_Kenney.zip",
        "dest_dir": "kenney/jumper-pack",
        "filename": "JumperPack_Kenney.zip",
        "license": "CC0",
        "genre_tags": ["parkour", "platformer"],
    },
    {
        "url": f"{OGA}/kenney_food-kit.zip",
        "dest_dir": "kenney/food-kit",
        "filename": "kenney_food-kit.zip",
        "license": "CC0",
        "genre_tags": ["life_sim"],
    },
    {
        "url": f"{OGA}/kenney_pixel-platformer-food-expansion.zip",
        "dest_dir": "kenney/pixel-platformer-food-expansion",
        "filename": "kenney_pixel-platformer-food-expansion.zip",
        "license": "CC0",
        "genre_tags": ["life_sim"],
    },
    {
        "url": f"{OGA}/kenney_pixelplatformerfarmexpansion.zip",
        "dest_dir": "kenney/pixel-platformer-farm-expansion",
        "filename": "kenney_pixelplatformerfarmexpansion.zip",
        "license": "CC0",
        "genre_tags": ["life_sim"],
    },
    {
        "url": f"{OGA}/kenney_particlePack.zip",
        "dest_dir": "kenney/particle-pack",
        "filename": "kenney_particlePack.zip",
        "license": "CC0",
        "genre_tags": ["shooter", "shmup", "survivor", "all"],
    },
    {
        "url": f"{OGA}/kenney_interfaceSounds.zip",
        "dest_dir": "kenney/interface-sounds",
        "filename": "kenney_interfaceSounds.zip",
        "license": "CC0",
        "genre_tags": ["all", "ui"],
    },
    {
        "url": "https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip",
        "dest_dir": "kenney/impact-sounds",
        "filename": "kenney_impact-sounds.zip",
        "license": "CC0",
        "genre_tags": ["all"],
    },
    {
        "url": "https://kenney.nl/media/pages/assets/pixel-vehicle-pack/570a4c9051-1677578609/kenney_pixel-vehicle-pack.zip",
        "dest_dir": "kenney/pixel-vehicle-pack",
        "filename": "kenney_pixel-vehicle-pack.zip",
        "license": "CC0",
        "genre_tags": ["racing"],
    },
    {
        "url": f"{OGA}/kenney_input-prompts.zip",
        "dest_dir": "kenney/input-prompts",
        "filename": "kenney_input-prompts.zip",
        "license": "CC0",
        "genre_tags": ["all", "ui"],
    },
    {
        "url": "https://kenney.nl/media/pages/assets/abstract-platformer/a8f4badcb5-1677579172/kenney_abstract-platformer.zip",
        "dest_dir": "kenney/abstract-platformer",
        "filename": "kenney_abstract-platformer.zip",
        "license": "CC0",
        "genre_tags": ["fighting", "platformer"],
    },
    {
        "url": f"{OGA}/kenney_tinydungeon.zip",
        "dest_dir": "kenney/tiny-dungeon",
        "filename": "kenney_tinydungeon.zip",
        "license": "CC0",
        "genre_tags": ["survivor", "life_sim"],
    },
    {
        "url": f"{OGA}/Roguelike%20Cave%20pack.zip",
        "dest_dir": "kenney/roguelike-caves",
        "filename": "Roguelike Cave pack.zip",
        "license": "CC0",
        "genre_tags": ["survivor"],
    },
    {
        "url": f"{OGA}/1bitpack_kenney_1.1.zip",
        "dest_dir": "kenney/1-bit-pack",
        "filename": "1bitpack_kenney_1.1.zip",
        "license": "CC0",
        "genre_tags": ["survivor", "shmup", "all"],
    },
]


def download_file(url: str, dest: Path, timeout: int = 120) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req: urllib.request.Request = urllib.request.Request(
        url,
        headers={"User-Agent": "GameForge-K12-AssetDownloader/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data: bytes = resp.read()
    dest.write_bytes(data)
    return len(data)


def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)


def main() -> int:
    results: list[dict[str, object]] = []
    for entry in ASSETS_TO_FETCH:
        dest_dir: Path = ASSETS / entry["dest_dir"]
        dest_file: Path = dest_dir / entry["filename"]
        record: dict[str, object] = {
            "id": entry["dest_dir"],
            "url": entry["url"],
            "license": entry["license"],
            "genre_tags": entry["genre_tags"],
            "status": "pending",
        }
        try:
            if dest_file.exists() and dest_file.stat().st_size > 0:
                size: int = dest_file.stat().st_size
                record["status"] = "skipped_exists"
                record["bytes"] = size
            else:
                size = download_file(entry["url"], dest_file)
                record["status"] = "downloaded"
                record["bytes"] = size
            if dest_file.suffix.lower() == ".zip":
                extract_root: Path = dest_dir / "extracted"
                if not extract_root.exists() or not any(extract_root.iterdir()):
                    extract_zip(dest_file, extract_root)
                record["extracted_to"] = str(extract_root.relative_to(ROOT))
            results.append(record)
            print(f"OK  {record['status']:16} {entry['dest_dir']}")
        except (urllib.error.URLError, urllib.error.HTTPError, zipfile.BadZipFile) as exc:
            record["status"] = "failed"
            record["error"] = str(exc)
            results.append(record)
            print(f"ERR {entry['dest_dir']}: {exc}", file=sys.stderr)
    manifest: dict[str, object] = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(ASSETS.relative_to(ROOT)),
        "entries": results,
        "ok": sum(1 for r in results if r["status"] in ("downloaded", "skipped_exists")),
        "failed": sum(1 for r in results if r["status"] == "failed"),
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": manifest["ok"], "failed": manifest["failed"], "manifest": str(MANIFEST)}, ensure_ascii=False))
    return 0 if manifest["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
