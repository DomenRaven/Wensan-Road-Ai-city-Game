# -*- coding: utf-8 -*-
"""为 AI 小游戏创作工坊 research_crawler 注入游戏设计相关关键词，提升打分相关性。"""
from __future__ import annotations

GAME_PROJECT_KEYWORDS = [
    "godot", "gdscript", "unity", "游戏", "game", "小游戏", "独立游戏",
    "ai", "llm", "gpt", "cursor", "mcp", "agent", "智能体", "大模型",
    "射击", "塔防", "platformer", "横版", "闯关", "跑酷", "竞速",
    "手感", "game feel", "juice", "反馈", "命中", "碰撞",
    "数值", "平衡", "波次", "关卡", "模板", "template", "参数化",
    "程序化", "procedural", "生成", "教育游戏", "研学", "k12", "少儿",
    "展陈", "museum", "serious game", "游戏化",
    "开源", "sdk", "api", "demo", "github", "教程", "bilibili", "csdn",
]

GAME_CATEGORY_RULES_EXTRA = [
    ("TUTORIAL", ["教程", "教学", "入门", "实战", "video", "bilibili", "零基础"]),
    ("OPEN_SOURCE", ["github", "开源", "open source", "gitee", "template"]),
    ("TECH_DOC", ["文档", "documentation", "api", "指南", "godot docs"]),
]


def apply_game_keyword_patch() -> None:
    """在 import pipeline 之前调用。"""
    from research_crawler import classifier
    from research_crawler.models import ContentCategory

    classifier.PROJECT_KEYWORDS = list(
        dict.fromkeys(classifier.PROJECT_KEYWORDS + GAME_PROJECT_KEYWORDS)
    )

    extra_rules: list[tuple[ContentCategory, list[str]]] = [
        (ContentCategory.TUTORIAL, ["godot", "游戏设计", "game design", "game feel", "塔防", "射击", "platformer"]),
        (ContentCategory.OPEN_SOURCE, ["godot template", "game template", "godot-mcp", "starter kit"]),
        (ContentCategory.TECH_DOC, ["godotengine.org", "gamedev", "mda", "游戏设计"]),
    ]
    existing = {cat: kws for cat, kws in classifier.CATEGORY_RULES}
    for cat, kws in extra_rules:
        merged = list(dict.fromkeys(existing.get(cat, []) + kws))
        existing[cat] = merged
    classifier.CATEGORY_RULES = list(existing.items())
