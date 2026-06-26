#!/usr/bin/env python3
"""生成乒乓球 + 飞机品类冻结快照与 SHA256 清单。

用法:
  python 05-工具脚本/freeze_genre_snapshot.py write   # 写入/更新快照与 manifest
  python 05-工具脚本/freeze_genre_snapshot.py verify  # 校验当前文件是否与 manifest 一致
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
MANIFEST_PATH: Path = REPO_ROOT / "config" / "frozen_genres_pingpong_shmup.json"
SNAPSHOT_ROOT: Path = (
    REPO_ROOT / "开发文档" / "模板引擎" / "快照" / "frozen" / "6.24_pingpong_shmup_v1.0"
)

GENRE_DIRS: tuple[str, ...] = ("shmup", "pingpong")
EDU_HOOKS: tuple[str, ...] = ("shmup_hooks.gd", "pingpong_hooks.gd")
ANCHOR_FILES: tuple[str, ...] = (
    "config/code_anchors/shmup.json",
    "config/code_anchors/pingpong.json",
    "config/creative_templates/shmup.json",
    "config/creative_templates/pingpong.json",
)
SHARED_BASELINE: tuple[str, ...] = (
    "templates/_edu/edu_action_bridge.gd",
    "kiosk/edu/code-highlight.js",
    "config/kiosk_edu_spec.json",
)

INCLUDE_SUFFIXES: frozenset[str] = frozenset(
    {".gd", ".json", ".tscn", ".godot", ".md", ".import"}
)
EXCLUDE_DIR_NAMES: frozenset[str] = frozenset({".godot", "__pycache__"})


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_template_files(genre: str) -> list[Path]:
    base: Path = REPO_ROOT / "templates" / genre
    if not base.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() not in INCLUDE_SUFFIXES:
            continue
        files.append(path)
    return files


def collect_frozen_paths() -> list[Path]:
    paths: list[Path] = []
    for genre in GENRE_DIRS:
        paths.extend(_collect_template_files(genre))
    for hook in EDU_HOOKS:
        hook_path: Path = REPO_ROOT / "templates" / "_edu" / hook
        if hook_path.is_file():
            paths.append(hook_path)
    for rel in ANCHOR_FILES + SHARED_BASELINE:
        candidate: Path = REPO_ROOT / rel
        if candidate.is_file():
            paths.append(candidate)
    # 去重保序
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key: str = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def rel_posix(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def build_manifest() -> dict[str, object]:
    files: list[dict[str, object]] = []
    for path in collect_frozen_paths():
        files.append(
            {
                "path": rel_posix(path),
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return {
        "version": "1.0",
        "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "genres": list(GENRE_DIRS),
        "display_names": {"shmup": "街机飞机射击", "pingpong": "乒乓球"},
        "snapshot_dir": SNAPSHOT_ROOT.relative_to(REPO_ROOT).as_posix(),
        "policy": "未经用户显式解冻，禁止修改 manifest 内 paths；共享文件见 shared_baseline",
        "shared_baseline": list(SHARED_BASELINE),
        "files": files,
    }


def write_snapshot(manifest: dict[str, object]) -> None:
    if SNAPSHOT_ROOT.exists():
        shutil.rmtree(SNAPSHOT_ROOT)
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
    for entry in manifest["files"]:
        rel: str = str(entry["path"])
        src: Path = REPO_ROOT / rel
        dest: Path = SNAPSHOT_ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (SNAPSHOT_ROOT / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def verify_manifest() -> int:
    if not MANIFEST_PATH.is_file():
        print(f"MISSING manifest: {MANIFEST_PATH}")
        return 1
    manifest: dict[str, object] = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    mismatches: list[str] = []
    missing: list[str] = []
    for entry in manifest.get("files", []):
        rel: str = str(entry["path"])
        expected: str = str(entry["sha256"])
        path: Path = REPO_ROOT / rel
        if not path.is_file():
            missing.append(rel)
            continue
        actual: str = _sha256_file(path)
        if actual != expected:
            mismatches.append(rel)
    if missing:
        print("MISSING files:")
        for rel in missing:
            print(f"  - {rel}")
    if mismatches:
        print("HASH mismatches:")
        for rel in mismatches:
            print(f"  - {rel}")
    if missing or mismatches:
        return 1
    count: int = len(manifest.get("files", []))
    print(f"OK · {count} frozen files match manifest")
    return 0


def main() -> int:
    cmd: str = sys.argv[1] if len(sys.argv) > 1 else "write"
    if cmd == "write":
        manifest = build_manifest()
        write_snapshot(manifest)
        print(f"Wrote {len(manifest['files'])} files")
        print(f"Manifest: {MANIFEST_PATH}")
        print(f"Snapshot: {SNAPSHOT_ROOT}")
        return 0
    if cmd == "verify":
        return verify_manifest()
    print("Usage: freeze_genre_snapshot.py [write|verify]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
