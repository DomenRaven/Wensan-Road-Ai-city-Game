from __future__ import annotations

from pathlib import Path

from app.services.workspace_guard import (
    copy_template_to_workspace,
    workspace_root_for_session,
)

__all__ = [
    "copy_template_to_workspace",
    "workspace_config_path",
    "workspace_root_for_session",
]


def workspace_config_path(workspace_root: Path) -> Path:
    return workspace_root / "config" / "game_config.json"
