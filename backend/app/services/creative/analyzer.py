from __future__ import annotations

import json
from typing import Any

from app.config import CONFIG_DIR
from app.services.config_builder import get_path, load_optional_skills_catalog, set_path
from app.services.creative.loader import load_creative_template
from app.services.tuning_mapper import DEFAULT_CLAMP_PERCENT, clamp_value, load_feel_overrides


def _clamp_tuning_value(base_val: Any, requested: Any, clamp_percent: float) -> Any:
    if not isinstance(base_val, (int, float)) or not isinstance(requested, (int, float)):
        return requested
    clamped: float = clamp_value(float(base_val), float(requested), clamp_percent)
    if isinstance(base_val, int):
        return int(round(clamped))
    return clamped


def _clamp_percent() -> float:
    doc: dict[str, Any] = load_feel_overrides()
    raw: Any = doc.get("clamp_percent", DEFAULT_CLAMP_PERCENT)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return DEFAULT_CLAMP_PERCENT


def _load_base_game_config(templates_dir: Any, genre: str) -> dict[str, Any]:
    path = templates_dir / genre / "config" / "game_config.json"
    return json.loads(path.read_text(encoding="utf-8"))


def analyze_preset_only(
    genre: str,
    answers: dict[str, Any],
    templates_dir: Any,
    config_dir: Any | None = None,
) -> dict[str, Any]:
    base_config_dir: Any = config_dir or CONFIG_DIR
    template: dict[str, Any] = load_creative_template(genre, base_config_dir)
    base_config: dict[str, Any] = _load_base_game_config(templates_dir, genre)
    percent: float = _clamp_percent()

    questions: list[dict[str, Any]] = list(template.get("questions", []))
    question_map: dict[str, dict[str, Any]] = {str(q.get("id")): q for q in questions}
    optional_rules: dict[str, Any] = load_optional_skills_catalog()
    allowed_skills: set[str] = set(optional_rules.get(genre, []))
    max_skills: int = 2
    skills_catalog_raw: Any = json.loads(
        (base_config_dir / "optional_skills.json").read_text(encoding="utf-8")
    )
    rules: Any = skills_catalog_raw.get("rules", {})
    if isinstance(rules, dict):
        max_skills = int(rules.get("max_skills_per_session", 2))

    resolutions: list[dict[str, Any]] = []
    selected_skills: list[str] = []

    for question_id, raw_answer in answers.items():
        qid: str = str(question_id)
        question: dict[str, Any] | None = question_map.get(qid)
        if question is None:
            raise ValueError(f"未知题目: {qid}")

        widget: str = str(question.get("widget", "single_choice"))
        if widget == "skill_pick":
            if raw_answer in (None, "", []):
                continue
            raw_skills: list[str]
            if isinstance(raw_answer, list):
                raw_skills = [str(v) for v in raw_answer]
            else:
                raw_skills = [str(raw_answer)]
            for skill_id in raw_skills:
                if skill_id not in allowed_skills:
                    raise ValueError(f"非法技能选项: {skill_id}")
                if skill_id not in selected_skills:
                    selected_skills.append(skill_id)
            if len(selected_skills) > max_skills:
                raise ValueError(f"技能数量超过上限: {max_skills}")
            resolutions.append(
                {
                    "question_id": qid,
                    "resolution": "preset",
                    "tuning_path": "tuning.enabled_skills",
                    "value": selected_skills,
                    "code_anchor_id": question.get("code_anchor_id"),
                }
            )
            continue

        options: list[dict[str, Any]] = list(question.get("options", []))
        option_map: dict[str, dict[str, Any]] = {str(opt.get("id")): opt for opt in options}
        answer_id: str = str(raw_answer).strip()
        if answer_id not in option_map:
            raise ValueError(f"非法选项: {qid}.{answer_id}")
        option: dict[str, Any] = option_map[answer_id]
        tuning_path: str = str(option.get("tuning_path", "")).strip()
        if not tuning_path:
            raise ValueError(f"缺少 tuning_path: {qid}.{answer_id}")
        requested: Any = option.get("value")
        base_val: Any = get_path(base_config, tuning_path)
        value: Any = _clamp_tuning_value(base_val, requested, percent)
        resolutions.append(
            {
                "question_id": qid,
                "resolution": "preset",
                "tuning_path": tuning_path,
                "value": value,
                "code_anchor_id": option.get("code_anchor_id"),
            }
        )

    return {
        "resolutions": resolutions,
        "llm_patch_required": False,
    }


def apply_resolutions_to_config(
    config: dict[str, Any],
    base_config: dict[str, Any],
    resolutions: list[dict[str, Any]],
) -> dict[str, Any]:
    merged: dict[str, Any] = json.loads(json.dumps(config))
    percent: float = _clamp_percent()
    for res in resolutions:
        path: str = str(res.get("tuning_path", "")).strip()
        if not path:
            continue
        value: Any = res.get("value")
        if path == "tuning.enabled_skills":
            set_path(merged, path, list(value) if isinstance(value, list) else [])
            continue
        base_val: Any = get_path(base_config, path)
        safe_value: Any = _clamp_tuning_value(base_val, value, percent)
        set_path(merged, path, safe_value)
    return merged
