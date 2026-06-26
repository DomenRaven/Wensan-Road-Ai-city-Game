#!/usr/bin/env python3
"""生成 RECIPE（配方问卷 + 作品证书）冻结快照与 SHA256 清单。

用法:
  python 05-工具脚本/freeze_recipe_snapshot.py write
  python 05-工具脚本/freeze_recipe_snapshot.py verify
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
MANIFEST_PATH: Path = REPO_ROOT / "config" / "frozen_recipe_v1.json"
SNAPSHOT_ROOT: Path = (
    REPO_ROOT / "开发文档" / "模板引擎" / "快照" / "frozen" / "6.26_recipe_v1.0"
)

GENRES: tuple[str, ...] = (
    "platformer",
    "shmup",
    "pingpong",
    "survivor",
    "parkour",
    "racing",
    "fighting",
)

KIOSK_EDU_FILES: tuple[str, ...] = (
    "kiosk/edu/certificate.js",
    "kiosk/edu/edu-wizard.js",
    "kiosk/edu/edu-styles.css",
    "kiosk/edu/index.html",
    "kiosk/edu/code-viewer.js",
    "kiosk/edu/layout/dual-pane.js",
)

CONFIG_FILES: tuple[str, ...] = (
    "config/kiosk_edu_spec.json",
    "config/l1_e2e_acceptance.json",
)

E2E_FILES: tuple[str, ...] = (
    "05-工具脚本/check_recipe_alignment.py",
    "05-工具脚本/e2e_recipe_a_certificate.py",
    "05-工具脚本/e2e_b_edu_batch.py",
    "05-工具脚本/e2e_b_edu_browser_smoke.py",
    "05-工具脚本/e2e_b_edu_platformer.py",
)

BACKEND_FILES: tuple[str, ...] = (
    "backend/app/services/creative/loader.py",
    "backend/tests/run_regression_api.py",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_frozen_paths() -> list[Path]:
    paths: list[Path] = []
    for genre in GENRES:
        for subdir in ("creative_templates", "code_anchors"):
            candidate: Path = REPO_ROOT / "config" / subdir / f"{genre}.json"
            if candidate.is_file():
                paths.append(candidate)
    for rel in CONFIG_FILES + KIOSK_EDU_FILES + E2E_FILES + BACKEND_FILES:
        candidate = REPO_ROOT / rel
        if candidate.is_file():
            paths.append(candidate)
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key: str = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return sorted(unique, key=lambda p: str(p.relative_to(REPO_ROOT)))


def build_manifest() -> dict[str, object]:
    files: list[dict[str, str]] = []
    for path in collect_frozen_paths():
        rel: str = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        files.append({"path": rel, "sha256": _sha256_file(path)})
    return {
        "name": "recipe_v1",
        "label": "RECIPE 配方问卷 + 作品证书",
        "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    print(f"OK · {count} frozen RECIPE files match manifest")
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
    print("Usage: freeze_recipe_snapshot.py [write|verify]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
