from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR: Path = Path(__file__).resolve().parents[2]
CONFIG_DIR: Path = ROOT_DIR / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GameForge K12 API"
    app_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000
    redis_url: str = "redis://127.0.0.1:6379/0"
    max_sessions: int = 10
    session_ttl_sec: int = 900
    allow_memory_fallback: bool = True
    godot_path: str = r"F:\Godot\Godot_v4.6.3-stable_win64.exe\Godot_v4.6.3-stable_win64.exe"
    templates_dir: Path = ROOT_DIR / "templates"
    workspace_dir: Path = ROOT_DIR / "workspace"
    deployment_server_os: str = "TBD"
    deployment_terminal_layout: str = "TBD"


@lru_cache
def get_settings() -> Settings:
    return Settings()
