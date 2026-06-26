# -*- coding: utf-8 -*-
"""街机飞机设计游戏 (shmup) · 完整落盘：trajectory 源码 + Kenney Pixel Shmup 素材。

秒哒 API trajectory 不含二进制；素材来自 Kenney CC0（与秒哒沙箱 catalog `pixel-plane-shmup` 同源包）。

用法：
  python 05-工具脚本/miaoda_fetch_shmup_full.py
"""
from __future__ import annotations

import json
import re
import shutil
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "03-背景与调研" / "data" / "秒哒精选源码" / "shmup"
KENNEY_ZIP_URL = "https://opengameart.org/sites/default/files/kenney_pixelshmup.zip"
KENNEY_CENTRAL = ROOT / "assets" / "kenney" / "pixel-shmup"

# 秒哒 assets.ts 引用的文件名（含特殊字符）
SHIPS_ALIAS = "ships_packed (128x192)[frames=1].png"
TILES_ALIAS = "tiles_packed (192x160)[frames=1].png"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _download_kenney_zip(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 10000:
        return dest
    req = urllib.request.Request(KENNEY_ZIP_URL, headers={"User-Agent": "GameForge-K12/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return dest


def _install_assets_pack(extract_root: Path, miaoda_tilemap: Path) -> dict[str, Any]:
    """解压 Kenney 包并生成秒哒兼容路径。"""
    miaoda_pack = miaoda_tilemap.parent
    miaoda_pack.mkdir(parents=True, exist_ok=True)

    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True)

    zip_path = OUT / "_cache" / "kenney_pixelshmup.zip"
    _download_kenney_zip(zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_root)

    tilemap_src = extract_root / "Tilemap"
    ships_src = tilemap_src / "ships_packed.png"
    tiles_src = tilemap_src / "tiles_packed.png"
    if not ships_src.is_file():
        raise FileNotFoundError(f"missing {ships_src}")

    miaoda_tilemap.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ships_src, miaoda_tilemap / SHIPS_ALIAS)
    shutil.copy2(tiles_src, miaoda_tilemap / TILES_ALIAS)

    # 可平铺背景：用 tiles 图集（与秒哒 TileSprite 滚动背景兼容）
    bg_dst = miaoda_tilemap / "background.png"
    shutil.copy2(tilemap_src / "tiles.png", bg_dst)

    # 完整 Kenney 目录副本（Ships/ Tiles/ Tilemap/ 单帧等）
    full_pack = miaoda_pack.parent / "pixel-plane-shmup-kenney-full"
    if full_pack.exists():
        shutil.rmtree(full_pack)
    shutil.copytree(extract_root, full_pack)

    # 中央库
    if KENNEY_CENTRAL.exists():
        shutil.rmtree(KENNEY_CENTRAL)
    shutil.copytree(extract_root, KENNEY_CENTRAL)

    png_count = sum(1 for _ in miaoda_pack.rglob("*.png"))
    return {
        "pack_id": "pixel-plane-shmup",
        "source": "Kenney Pixel Shmup CC0 (OGA)",
        "miaoda_aliases": {
            "ships": str(miaoda_tilemap / SHIPS_ALIAS),
            "tiles": str(miaoda_tilemap / TILES_ALIAS),
            "background": str(bg_dst),
        },
        "full_pack_dir": str(full_pack.relative_to(OUT)).replace("\\", "/"),
        "png_files_under_pack": png_count,
    }


def _flatten_src_tree() -> dict[str, Any]:
    """将 src/src/... 整理为 src/project/（秒哒工程相对路径）。"""
    raw = OUT / "src"
    project = OUT / "src" / "project"
    if project.exists():
        shutil.rmtree(project)
    project.mkdir(parents=True)

    # 优先 src/src 下的游戏代码
    inner = raw / "src"
    if inner.is_dir():
        shutil.copytree(inner, project / "src")
    else:
        for item in raw.iterdir():
            if item.name in ("project", "assets"):
                continue
            dest = project / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            elif item.is_file():
                shutil.copy2(item, dest)

    # assets 放到 project/src/assets（与秒哒 /workspace/.../src/assets 一致）
    assets_dst = project / "src" / "assets"
    assets_dst.mkdir(parents=True, exist_ok=True)

    code_files = [p for p in project.rglob("*") if p.is_file() and p.suffix in (".ts", ".tsx", ".json", ".md")]
    return {
        "project_root": str(project.relative_to(OUT)).replace("\\", "/"),
        "code_files": len(code_files),
        "paths": sorted(str(p.relative_to(OUT)).replace("\\", "/") for p in code_files),
    }


def _extract_phraser_guide() -> str:
    wf = OUT / "workflow_full.jsonl"
    if not wf.is_file():
        return ""
    for line in wf.read_text(encoding="utf-8").splitlines():
        if "agent_finish" not in line and "街机飞机射击游戏 — Phaser" not in line:
            continue
        try:
            obj = json.loads(line)
            ev = obj.get("event", {})
            artifact = ev.get("result", {}).get("artifact", {})
            if artifact.get("name") == "agent_finish":
                for part in artifact.get("parts", []):
                    data = part.get("data", {})
                    if isinstance(data, dict) and data.get("message"):
                        return str(data["message"])
        except json.JSONDecodeError:
            continue
        m = re.search(r'"message":\s*"((?:[^"\\]|\\.)*)"', line)
        if m and "Phaser" in m.group(1):
            return bytes(m.group(1), "utf-8").decode("unicode_escape")
    return ""


def main() -> int:
    print("=== shmup 完整落盘 ===", flush=True)

    src_info = _flatten_src_tree()
    # 刷新 code 列表（flatten 后）
    project = OUT / "src" / "project"
    code_files = [p for p in project.rglob("*") if p.is_file() and p.suffix in (".ts", ".tsx", ".json", ".md")]
    src_info["code_files"] = len(code_files)
    src_info["paths"] = sorted(str(p.relative_to(OUT)).replace("\\", "/") for p in code_files)

    assets_info = _install_assets_pack(
        OUT / "_cache" / "kenney_extract",
        OUT / "src" / "project" / "src" / "assets" / "pixel-plane-shmup" / "Tilemap",
    )
    # 同时挂到扁平 assets/ 便于浏览
    flat_assets = OUT / "assets" / "pixel-plane-shmup"
    if flat_assets.exists():
        shutil.rmtree(flat_assets)
    shutil.copytree(
        OUT / "src" / "project" / "src" / "assets" / "pixel-plane-shmup",
        flat_assets,
    )
    full_src = OUT / "src" / "project" / "src" / "assets" / "pixel-plane-shmup-kenney-full"
    if full_src.is_dir():
        shutil.copytree(full_src, OUT / "assets" / "pixel-plane-shmup-kenney-full")

    guide = _extract_phraser_guide()
    if guide:
        (OUT / "docs" / "phaser_assets_guide.md").write_text(guide, encoding="utf-8")

    # 统计
    all_png = list(OUT.rglob("*.png"))
    all_code = list(OUT.rglob("*.ts")) + list(OUT.rglob("*.tsx"))

    manifest: dict[str, Any] = {
        "slug": "shmup",
        "title": "街机飞机设计游戏v2",
        "app_id": "app-chu7pw7h454x",
        "preview_url": "https://app-chu7pw7h454x.appmiaoda.com",
        "fetched_at": _utc_now(),
        "method": "trajectory_code + kenney_cc0_assets",
        "limitations": [
            "秒哒 API trajectory 无法导出沙箱二进制；素材为 Kenney Pixel Shmup CC0 对齐包",
            "无 package.json/vite/index.html（秒哒平台脚手架未出现在 trajectory）",
            "预览站为 SPA，无法直接 HTTP 扒取打包后资源",
        ],
        "assets": assets_info,
        "source_tree": src_info,
        "counts": {
            "png": len(all_png),
            "ts_tsx": len(all_code),
            "total_files": sum(1 for _ in OUT.rglob("*") if _.is_file()),
        },
        "key_paths": {
            "prd": "docs/需求文档.md",
            "main_game": "src/project/src/game/scenes/MainGame.ts",
            "constants": "src/project/src/game/constants.ts",
            "app_ui": "src/project/src/App.tsx",
            "assets_tilemap": "assets/pixel-plane-shmup/Tilemap",
            "kenney_full": assets_info.get("full_pack_dir"),
        },
    }

    (OUT / "fetch_full_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"  PNG: {manifest['counts']['png']}", flush=True)
    print(f"  TS/TSX: {manifest['counts']['ts_tsx']}", flush=True)
    print(f"  manifest: {OUT / 'fetch_full_manifest.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
