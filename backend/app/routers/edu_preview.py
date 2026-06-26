from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/edu", tags=["edu"])

_PREVIEW_FILE_PREFIXES: tuple[str, ...] = ("config/", "core/", "scenes/")
_PREVIEW_ROOT_FILES: frozenset[str] = frozenset({"project.godot"})


class EduPreviewFileResponse(BaseModel):
    ok: bool
    genre: str
    content: str
    path: str


def _resolve_template_relative_file(templates_dir: Path, genre: str, rel_path: str) -> Path:
    rel: str = rel_path.strip().replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        raise HTTPException(status_code=400, detail=f"非法相对路径: {rel_path!r}")
    if rel not in _PREVIEW_ROOT_FILES and not rel.startswith(_PREVIEW_FILE_PREFIXES):
        raise HTTPException(
            status_code=400,
            detail=f"仅允许读取 project.godot、config/、core/、scenes/ 下文件: {rel_path!r}",
        )
    genre_dir: Path = (templates_dir / genre).resolve()
    if not genre_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"未知品类模板: {genre}")
    target: Path = (genre_dir / rel).resolve()
    try:
        target.relative_to(genre_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"路径越界: {rel_path!r}") from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"模板中未找到文件: {rel}")
    return target


@router.get("/preview/{genre}/file", response_model=EduPreviewFileResponse)
def preview_template_file(genre: str, rel_path: str) -> EduPreviewFileResponse:
    settings = get_settings()
    resolved: Path = _resolve_template_relative_file(settings.templates_dir, genre, rel_path)
    content: str = resolved.read_text(encoding="utf-8")
    rel_normalized: str = rel_path.strip().replace("\\", "/").lstrip("/")
    return EduPreviewFileResponse(ok=True, genre=genre, content=content, path=rel_normalized)
