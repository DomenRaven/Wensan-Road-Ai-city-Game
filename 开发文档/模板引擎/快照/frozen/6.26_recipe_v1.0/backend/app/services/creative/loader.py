from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import CONFIG_DIR

# creative_templates / code_anchors 使用进程内 lru_cache；改 config/ 后需重启 API 或触发 backend 重载。


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"配置不存在: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def load_intent_lexicon(config_dir: Path | None = None) -> dict[str, Any]:
    base: Path = config_dir or CONFIG_DIR
    return _read_json(base / "intent_genre_lexicon.json")


@lru_cache
def load_creative_template(genre: str, config_dir: Path | None = None) -> dict[str, Any]:
    base: Path = config_dir or CONFIG_DIR
    path: Path = base / "creative_templates" / f"{genre}.json"
    data: dict[str, Any] = _read_json(path)
    if str(data.get("genre", "")).strip() != genre:
        raise ValueError(f"creative template genre 不匹配: {genre}")
    return data


@lru_cache
def load_code_anchors(genre: str, config_dir: Path | None = None) -> dict[str, Any]:
    base: Path = config_dir or CONFIG_DIR
    path: Path = base / "code_anchors" / f"{genre}.json"
    data: dict[str, Any] = _read_json(path)
    anchors: Any = data.get("anchors")
    if not isinstance(anchors, dict):
        return {"anchors": {}}
    return {"anchors": anchors}


def get_name_suggestions(genre: str, config_dir: Path | None = None) -> list[str]:
    template: dict[str, Any] = load_creative_template(genre, config_dir)
    values: Any = template.get("name_suggestions", [])
    if not isinstance(values, list):
        return []
    return [str(v).strip() for v in values if str(v).strip()]
