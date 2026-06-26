from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import CONFIG_DIR
from app.services.creative.loader import load_code_anchors


def _find_line_by_token(file_path: Path, token: str) -> int | None:
    if not file_path.is_file():
        return None
    lines: list[str] = file_path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines, start=1):
        if token in line:
            return idx
    return None


def _resolution_map(resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    by_anchor: dict[str, Any] = {}
    for item in resolutions:
        anchor_id: str = str(item.get("code_anchor_id", "")).strip()
        if not anchor_id:
            continue
        by_anchor[anchor_id] = item
    return by_anchor


def build_code_map_preview(
    genre: str,
    resolutions: list[dict[str, Any]],
    config_dir: Path | None = None,
) -> dict[str, Any]:
    anchors_doc: dict[str, Any] = load_code_anchors(genre, config_dir or CONFIG_DIR)
    anchors: dict[str, Any] = anchors_doc.get("anchors", {})
    by_anchor: dict[str, Any] = _resolution_map(resolutions)
    preview: dict[str, Any] = {}
    for anchor_id, anchor in anchors.items():
        item: dict[str, Any] = {
            "file": anchor.get("file"),
            "path": anchor.get("path"),
            "caption": anchor.get("caption"),
            "line_hint": anchor.get("line_hint"),
        }
        resolution: Any = by_anchor.get(anchor_id)
        if isinstance(resolution, dict):
            item["value"] = resolution.get("value")
        preview[anchor_id] = item
    return preview


def build_code_map_for_workspace(
    workspace_root: Path,
    genre: str,
    resolutions: list[dict[str, Any]],
    config_dir: Path | None = None,
) -> dict[str, Any]:
    anchors_doc: dict[str, Any] = load_code_anchors(genre, config_dir or CONFIG_DIR)
    anchors: dict[str, Any] = anchors_doc.get("anchors", {})
    by_anchor: dict[str, Any] = _resolution_map(resolutions)
    code_map: dict[str, Any] = {}

    for anchor_id, anchor in anchors.items():
        rel_file: str = str(anchor.get("file", "")).strip()
        if not rel_file:
            continue
        file_path: Path = (workspace_root / rel_file).resolve()
        if workspace_root.resolve() not in file_path.parents and file_path != workspace_root.resolve():
            continue

        line: int | None = None
        path_token: str = str(anchor.get("path", "")).strip()
        if path_token:
            key_token: str = f'"{path_token.split(".")[-1]}"'
            line = _find_line_by_token(file_path, key_token)
        if line is None:
            snippet: str = str(anchor.get("snippet_gd", "")).strip()
            if snippet:
                first_line: str = snippet.splitlines()[0].strip()
                if first_line:
                    line = _find_line_by_token(file_path, first_line)
        if line is None and isinstance(anchor.get("line_hint"), int):
            line = int(anchor["line_hint"])

        entry: dict[str, Any] = {
            "file": rel_file,
            "path": anchor.get("path"),
            "caption": anchor.get("caption"),
            "line": line,
            "line_hint": anchor.get("line_hint"),
        }
        action_id: str | None = anchor.get("action_id")
        if isinstance(action_id, str) and action_id.strip():
            entry["action_id"] = action_id.strip()
        resolution: Any = by_anchor.get(anchor_id)
        if isinstance(resolution, dict):
            entry["value"] = resolution.get("value")
        code_map[anchor_id] = entry

    return code_map
