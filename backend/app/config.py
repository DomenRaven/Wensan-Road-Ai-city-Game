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
    # 创作经验 → Learned Skill 长期库（不随 session 销毁）
    learned_skills_dir: Path = ROOT_DIR / "data" / "learned_skills"
    # 策展参考 Skill（只读；与 learned 分离）
    reference_skills_dir: Path = ROOT_DIR / "data" / "reference_skills"
    # 总纲 Q1–Q3 / HF-13：轮次预算 / 软续杯 / 墙钟（秒）
    # 前端 kiosk nl-patch 超时 420s（略大于墙钟，避免 salvage 返回前被 abort）
    agent_max_rounds: int = 16
    agent_soft_extra_rounds: int = 16
    agent_wall_clock_sec: float = 360.0
    deployment_server_os: str = "TBD"
    deployment_terminal_layout: str = "TBD"
    # 实装公网域名，如 https://gameforge.example.com — 二维码编码此地址供游客扫码
    public_api_base: str = ""
    certificate_download_ttl_sec: int = 259200
    # 无 PUBLIC_API_BASE 时：把证书 PNG 中继到临时图床（Litterbox/SM.MS），供手机扫码
    certificate_relay_enabled: bool = True
    # S-A2 · nl-patch 大模型（OpenAI / DeepSeek 兼容 Chat Completions）
    # 留空 LLM_API_KEY 时 nl-patch 走本地规则 stub，绝不假装 llm 成功
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_timeout_sec: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
