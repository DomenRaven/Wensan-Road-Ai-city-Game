"""创作经验 → Learned Skill 长期库（展厅侧能力增长）。

销毁会话 workspace 之前 harvest；后续对话 Top-K 检索注入。
存储默认本机：data/learned_skills/（不随 session 删除）。
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.agent_workspace import FORBIDDEN_GD_SNIPPETS, validate_gdscript_safe
from app.services.config_builder import (
    get_path,
    load_optional_skills_catalog,
    load_optional_skills_entries,
    load_optional_skills_max,
    set_path,
)

SESSION_AI_LOG_REL: str = ".session_ai_log.jsonl"
_VIOLENCE_WORDS: tuple[str, ...] = (
    "血腥",
    "杀戮",
    "自杀",
    "恐怖袭击",
    "裸体",
    "porn",
    "gore",
)


class LearnedSkillsError(ValueError):
    """长期库操作失败。"""


def ensure_store(store_dir: Path) -> Path:
    root: Path = store_dir.resolve()
    (root / "experiences").mkdir(parents=True, exist_ok=True)
    (root / "snippets").mkdir(parents=True, exist_ok=True)
    index: Path = root / "index.jsonl"
    if not index.is_file():
        index.write_text("", encoding="utf-8")
    return root


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _skill_id_from(genre: str, title: str, phrases: list[str]) -> str:
    seed: str = f"{genre}|{title}|{'|'.join(phrases[:3])}".lower()
    digest: str = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    safe_genre: str = re.sub(r"[^a-z0-9_]+", "_", genre.lower())[:16] or "genre"
    return f"ls_{safe_genre}_{digest}"


def append_session_patch_log(
    workspace_root: Path,
    entry: dict[str, Any],
) -> None:
    """nl-patch 成功后追加一条本局改动日志，供 release 前 harvest。"""
    log_path: Path = workspace_root / SESSION_AI_LOG_REL
    payload: dict[str, Any] = dict(entry)
    payload.setdefault("ts", _now_iso())
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_session_patch_log(workspace_root: Path) -> list[dict[str, Any]]:
    log_path: Path = workspace_root / SESSION_AI_LOG_REL
    if not log_path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def format_recent_session_writes_for_prompt(
    workspace_root: Path,
    *,
    limit_rows: int = 6,
    limit_files: int = 12,
) -> str:
    """本局近期成功写入路径，供 Agent 开放读盘定位（HF-11）。"""
    logs: list[dict[str, Any]] = read_session_patch_log(workspace_root)
    if not logs:
        return ""
    files: list[str] = []
    notes: list[str] = []
    for row in reversed(logs[-max(1, limit_rows) :]):
        if not row.get("ok"):
            continue
        summary: str = str(row.get("summary") or "").strip()[:80]
        user_text: str = str(row.get("user_text") or "").strip()[:60]
        if summary or user_text:
            notes.append(f"- 用户「{user_text or '…'}」→ {summary or '（无摘要）'}")
        for f in row.get("sandbox_files") or []:
            rel: str = str(f).replace("\\", "/").strip()
            if rel and rel not in files:
                files.append(rel)
            if len(files) >= limit_files:
                break
        if len(files) >= limit_files:
            break
    if not files and not notes:
        return ""
    lines: list[str] = [
        "【本局近期改动 · 开放读盘时优先阅读】"
    ]
    lines.extend(notes[:4])
    if files:
        lines.append("路径：" + "、".join(files))
        lines.append(
            "反馈类需求：先 read_file 这些路径，对照用户原话核对状态是否成对开闭，"
            "再 replace_text 最小 patch；done 前确保磁盘已有对应改动。"
        )
    return "\n".join(lines)


def _load_index(store_dir: Path) -> list[dict[str, Any]]:
    ensure_store(store_dir)
    index: Path = store_dir / "index.jsonl"
    skills: list[dict[str, Any]] = []
    text: str = index.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("skill_id"):
            skills.append(obj)
    return skills


def _write_index(store_dir: Path, skills: list[dict[str, Any]]) -> None:
    ensure_store(store_dir)
    index: Path = store_dir / "index.jsonl"
    lines: list[str] = [
        json.dumps(s, ensure_ascii=False) for s in skills if s.get("skill_id")
    ]
    index.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _safety_ok(text: str) -> tuple[bool, str]:
    lowered: str = text.lower()
    for word in _VIOLENCE_WORDS:
        if word.lower() in lowered:
            return False, f"rejected:violence:{word}"
    try:
        if ".gd" in text or "extends " in text or "func " in text:
            validate_gdscript_safe(text)
    except Exception as exc:  # noqa: BLE001
        return False, f"rejected:api:{exc}"
    for snip in FORBIDDEN_GD_SNIPPETS:
        if snip in text:
            return False, f"rejected:api:{snip}"
    return True, "ok"


def snippet_quality_ok(snippet: str) -> bool:
    """P1：片段质量过滤——过短、无可执行结构、含禁 API / 幻想 API 则丢弃。"""
    from app.services.creative.agent_contracts import snippet_has_invented_apis

    body: str = snippet.strip()
    if len(body) < 24:
        return False
    if "extends " not in body and "func " not in body:
        return False
    ok, _reason = _safety_ok(body)
    if not ok:
        return False
    if snippet_has_invented_apis(body):
        return False
    return True


def _phrase_overlap(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    sa: set[str] = {x.strip().lower() for x in a if x.strip()}
    sb: set[str] = {x.strip().lower() for x in b if x.strip()}
    if not sa or not sb:
        return 0.0
    inter: int = len(sa & sb)
    union: int = len(sa | sb)
    return float(inter) / float(union) if union else 0.0


def _text_tokens(text: str) -> list[str]:
    parts: list[str] = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z_]{3,}", text.lower())
    return parts[:24]


def _score_skill(skill: dict[str, Any], query: str, genre: str) -> tuple[float, float]:
    """返回 (总分, 相关分)。相关分不含「同品类保底」，避免无关经验仅因同 genre 被注入。"""
    if str(skill.get("safety", "ok")) != "ok":
        return -1.0, 0.0
    score: float = 0.0
    relevance: float = 0.0
    if str(skill.get("genre", "")) == genre:
        score += 3.0
    phrases: list[str] = [str(p) for p in (skill.get("trigger_phrases") or [])]
    q_tokens: list[str] = _text_tokens(query)
    for p in phrases:
        if p and p in query:
            score += 2.5
            relevance += 2.5
        for tok in q_tokens:
            if tok and tok in p.lower():
                score += 0.4
                relevance += 0.4
    summary: str = str(skill.get("summary", ""))
    title: str = str(skill.get("title", ""))
    for tok in q_tokens:
        if tok and tok in summary.lower():
            score += 0.25
            relevance += 0.25
        if tok and tok in title.lower():
            score += 0.35
            relevance += 0.35
    use_count: int = int(skill.get("use_count") or 0)
    success_count: int = int(skill.get("success_count") or 0)
    fail_count: int = int(skill.get("fail_count") or 0)
    score += min(2.0, 0.15 * float(success_count))
    score += min(1.0, 0.05 * float(use_count))
    # P1：没生效强降权（最多 -12），verified_gate 加权；未验证 Skill 额外降权（总纲 Q7）
    score -= min(12.0, 2.0 * float(fail_count))
    if bool(skill.get("verified_gate")):
        score += 2.5
    else:
        score -= 1.5
    if fail_count >= 3:
        score -= 3.0  # 多次没生效几乎不再进 Top-K
    return score, relevance


def search_learned_skills(
    store_dir: Path,
    query: str,
    genre: str,
    k: int = 5,
) -> list[dict[str, Any]]:
    """检索 Top-K Learned Skills。

    必须与当前话术有实质相关（相关分≥1），禁止「同品类就塞进提示词」造成串味。
    """
    skills: list[dict[str, Any]] = _load_index(store_dir)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for skill in skills:
        sc, rel = _score_skill(skill, query, genre)
        if sc < 0:
            continue
        # 仅同 genre 保底、话术完全不沾边 → 不注入
        if rel < 1.0:
            continue
        ranked.append((sc, skill))
    ranked.sort(key=lambda x: x[0], reverse=True)
    out: list[dict[str, Any]] = []
    for sc, skill in ranked[: max(1, k)]:
        item: dict[str, Any] = dict(skill)
        item["_score"] = round(sc, 3)
        out.append(item)
    return out


def format_skills_for_prompt(skills: list[dict[str, Any]]) -> str:
    if not skills:
        return ""
    lines: list[str] = [
        "【长期库 Learned Skills · 与当前原话明确相关时再复用】"
    ]
    for i, sk in enumerate(skills, start=1):
        phrases: list[str] = [str(p) for p in (sk.get("trigger_phrases") or [])][:4]
        lines.append(
            f"{i}. [{sk.get('genre')}] {sk.get('title')} · "
            f"触发:{' / '.join(phrases) or '（无）'} · "
            f"{str(sk.get('summary', ''))[:120]}"
        )
        how: list[str] = [str(h) for h in (sk.get("how_to_play") or [])][:2]
        if how:
            lines.append("   试玩: " + "；".join(how))
    return "\n".join(lines)


def bump_skill_counts(
    store_dir: Path,
    skill_ids: list[str],
    *,
    used: bool = True,
    success: bool = False,
    failed: bool = False,
) -> int:
    """P1：更新 use_count / success_count / fail_count。"""
    if not skill_ids:
        return 0
    skills: list[dict[str, Any]] = _load_index(store_dir)
    wanted: set[str] = {str(x) for x in skill_ids if x}
    touched: int = 0
    for sk in skills:
        sid: str = str(sk.get("skill_id", ""))
        if sid not in wanted:
            continue
        if used:
            sk["use_count"] = int(sk.get("use_count") or 0) + 1
        if success:
            sk["success_count"] = int(sk.get("success_count") or 0) + 1
        if failed:
            sk["fail_count"] = int(sk.get("fail_count") or 0) + 1
        sk["updated_at"] = _now_iso()
        touched += 1
    if touched:
        _write_index(store_dir, skills)
    return touched


def record_not_effective_feedback(
    store_dir: Path,
    query: str,
    genre: str,
    k: int = 3,
) -> list[str]:
    """「没生效」反馈：对检索到的相近 Skill 降权（fail_count++）。"""
    hits: list[dict[str, Any]] = search_learned_skills(store_dir, query, genre, k=k)
    ids: list[str] = [str(h.get("skill_id")) for h in hits if h.get("skill_id")]
    bump_skill_counts(store_dir, ids, used=False, success=False, failed=True)
    return ids


def enable_catalog_skill(
    workspace_root: Path,
    genre: str,
    skill_id: str,
    *,
    with_icon_hint: bool = True,
) -> dict[str, Any]:
    """智能体工具：打开 optional_skills 目录内预制技能（受每局 max 推荐上限）。"""
    sid: str = skill_id.strip()
    catalog: list[str] = load_optional_skills_catalog().get(genre, [])
    if sid not in catalog:
        raise LearnedSkillsError(f"技能不在本品类目录: {sid}")
    config_path: Path = workspace_root / "config" / "game_config.json"
    if not config_path.is_file():
        raise LearnedSkillsError("缺少 config/game_config.json")
    config: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
    before_raw = get_path(config, "tuning.enabled_skills")
    before: list[str] = [str(x) for x in before_raw] if isinstance(before_raw, list) else []
    max_n: int = load_optional_skills_max()
    if sid in before:
        label_map = {eid: label for eid, label, _d in load_optional_skills_entries(genre)}
        return {
            "tool": "enable_catalog_skill",
            "skill_id": sid,
            "already": True,
            "enabled_skills": before,
            "label": label_map.get(sid, sid),
            "hint": "该技能已开启；请重开游戏试玩",
        }
    if len(before) >= max_n:
        raise LearnedSkillsError(
            f"本局预制技能已满（最多 {max_n} 个）。可现场写沙箱新技能，或先关掉一个。"
        )
    after: list[str] = before + [sid]
    set_path(config, "tuning.enabled_skills", after)
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    label_map = {eid: label for eid, label, _d in load_optional_skills_entries(genre)}
    label: str = label_map.get(sid, sid)
    hint: str = f"已开启「{label}」；请重开游戏后试用"
    if with_icon_hint:
        hint += "（左上角可能有技能图标）"
    return {
        "tool": "enable_catalog_skill",
        "skill_id": sid,
        "already": False,
        "enabled_skills": after,
        "label": label,
        "hint": hint,
        "path": "config/game_config.json",
    }


def _extract_candidate_skills(
    genre: str,
    logs: list[dict[str, Any]],
    workspace_root: Path,
) -> list[dict[str, Any]]:
    """从本局日志提炼 ≥0 条候选 Learned Skill。"""
    candidates: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for row in logs:
        if not row.get("ok"):
            continue
        provider: str = str(row.get("provider") or "")
        user_text: str = str(row.get("user_text") or "").strip()
        summary: str = str(row.get("summary") or "").strip()
        how: list[str] = [str(h) for h in (row.get("how_to_play") or []) if str(h).strip()]
        files: list[str] = [str(f) for f in (row.get("sandbox_files") or [])]
        caps: list[str] = [str(c) for c in (row.get("applied_capabilities") or [])]
        changes: list[dict[str, Any]] = [
            c for c in (row.get("changes") or []) if isinstance(c, dict)
        ]

        has_skill_toggle: bool = any(
            str(c.get("path")) == "tuning.enabled_skills" for c in changes
        )
        has_sandbox_rules: bool = any(
            str(c.get("path", "")).startswith("sandbox_rules.") for c in changes
        )
        has_script: bool = any(
            f.endswith(".gd") or f.startswith("core/") for f in files
        )
        if not (has_skill_toggle or has_sandbox_rules or has_script or caps):
            continue
        # stub 也允许入库（门槛：有可复述改动）
        if provider not in ("agent", "llm", "stub"):
            continue

        title: str = summary[:40] or (user_text[:40] if user_text else "会话创作")
        phrases: list[str] = []
        if user_text:
            phrases.append(user_text[:80])
        for cap in caps[:4]:
            phrases.append(cap)
        phrases = list(dict.fromkeys(phrases))[:6]

        snippet: str = ""
        snippet_rel: str = ""
        had_bad_gd: bool = False
        for rel in files:
            if not rel.endswith(".gd"):
                continue
            path: Path = workspace_root / rel
            if path.is_file():
                body: str = path.read_text(encoding="utf-8", errors="ignore")
                if snippet_quality_ok(body):
                    if not snippet:
                        snippet = body[:4000]
                        snippet_rel = rel
                else:
                    had_bad_gd = True

        # 坏片段拒绝入库（幻想 API / 质量不过）
        if had_bad_gd and not snippet:
            candidates.append(
                {
                    "genre": genre,
                    "title": title,
                    "trigger_phrases": phrases,
                    "summary": summary or user_text,
                    "how_to_play": how[:6],
                    "safety": "rejected",
                    "safety_reason": "rejected:invented_api_or_quality",
                    "snippet": "",
                    "snippet_rel": "",
                    "provider": provider,
                    "verified_gate": False,
                }
            )
            continue

        blob: str = "\n".join([title, summary, user_text, snippet])
        ok, safety = _safety_ok(blob)
        if not ok:
            candidates.append(
                {
                    "genre": genre,
                    "title": title,
                    "trigger_phrases": phrases,
                    "summary": summary or user_text,
                    "how_to_play": how[:6],
                    "safety": "rejected",
                    "safety_reason": safety,
                    "snippet": "",
                    "snippet_rel": "",
                    "provider": provider,
                }
            )
            continue

        gate_passed: bool = bool(row.get("gate_passed"))
        key: str = f"{genre}|{'|'.join(phrases[:2])}|{title[:20]}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        candidates.append(
            {
                "genre": genre,
                "title": title,
                "trigger_phrases": phrases,
                "summary": summary or user_text or title,
                "how_to_play": how[:6],
                "safety": "ok",
                "safety_reason": "ok",
                "snippet": snippet,
                "snippet_rel": snippet_rel,
                "provider": provider,
                "applied_capabilities": caps,
                "verified_gate": gate_passed and provider == "agent",
            }
        )
    return candidates


def _upsert_skill(
    store_dir: Path,
    skills: list[dict[str, Any]],
    candidate: dict[str, Any],
    source_session: str,
) -> tuple[list[dict[str, Any]], str, bool]:
    """去重：同品类 + 相似触发话术 → 合并计数；否则新建。返回 (skills, skill_id, created)。"""
    if candidate.get("safety") != "ok":
        return skills, "", False
    genre: str = str(candidate.get("genre", ""))
    phrases: list[str] = [str(p) for p in (candidate.get("trigger_phrases") or [])]
    for sk in skills:
        if str(sk.get("genre")) != genre:
            continue
        if str(sk.get("safety", "ok")) != "ok":
            continue
        old_phrases: list[str] = [str(p) for p in (sk.get("trigger_phrases") or [])]
        if _phrase_overlap(phrases, old_phrases) >= 0.45:
            sk["use_count"] = int(sk.get("use_count") or 0)
            sk["success_count"] = int(sk.get("success_count") or 0) + 1
            sk["updated_at"] = _now_iso()
            if candidate.get("verified_gate"):
                sk["verified_gate"] = True
            # 合并话术
            merged_phrases: list[str] = list(
                dict.fromkeys(old_phrases + phrases)
            )[:8]
            sk["trigger_phrases"] = merged_phrases
            if candidate.get("summary") and len(str(candidate["summary"])) > len(
                str(sk.get("summary") or "")
            ):
                sk["summary"] = candidate["summary"]
            return skills, str(sk.get("skill_id", "")), False

    sid: str = _skill_id_from(genre, str(candidate.get("title", "")), phrases)
    snippet_ref: str = ""
    snippet: str = str(candidate.get("snippet") or "")
    if snippet and snippet_quality_ok(snippet):
        snippet_ref = f"snippets/{sid}.gd.txt"
        (store_dir / snippet_ref).write_text(snippet, encoding="utf-8")

    skill: dict[str, Any] = {
        "skill_id": sid,
        "genre": genre,
        "title": str(candidate.get("title") or sid)[:80],
        "trigger_phrases": phrases[:8],
        "summary": str(candidate.get("summary") or "")[:300],
        "how_to_play": list(candidate.get("how_to_play") or [])[:6],
        "source_session": source_session[:16] + "…" if len(source_session) > 16 else source_session,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "use_count": 0,
        "success_count": 1,
        "fail_count": 0,
        "safety": "ok",
        "snippet_ref": snippet_ref,
        "provider": str(candidate.get("provider") or ""),
        "applied_capabilities": list(candidate.get("applied_capabilities") or [])[:8],
        "verified_gate": bool(candidate.get("verified_gate")),
    }
    skills.append(skill)
    return skills, sid, True


def session_is_negative_for_harvest(
    logs: list[dict[str, Any]],
    *,
    user_rejected: bool = False,
) -> tuple[bool, str]:
    """总纲 G8：终局否定态 → 禁止入库有效 Learned Skill。"""
    if user_rejected:
        return True, "user_rejected"
    if not logs:
        return False, ""
    last: dict[str, Any] = logs[-1]
    if bool(last.get("rolled_back")):
        return True, "rolled_back"
    if bool(last.get("playability_suspect")):
        return True, "playability_suspect"
    # 显式 False 才算未过门禁；缺字段兼容旧日志
    if last.get("gate_passed") is False:
        return True, "ungated"
    if bool(last.get("partial")):
        return True, "partial"
    last_gate_idx: int = -1
    for i, row in enumerate(logs):
        if bool(row.get("gate_passed")):
            last_gate_idx = i
    for i, row in enumerate(logs):
        blob: str = f"{row.get('feedback') or ''}\n{row.get('user_text') or ''}"
        if ("没生效" in blob or "没有生效" in blob) and i > last_gate_idx:
            return True, "not_effective_after_last_gate"
    return False, ""


def harvest_session_experience(
    store_dir: Path,
    session_id: str,
    workspace_root: Path,
    genre: str,
    *,
    display_name: str = "",
    user_rejected: bool = False,
) -> dict[str, Any]:
    """销毁前：沉淀 Experience，并提炼 Learned Skill 入库。

    本局从未成功 nl-patch → 跳过入库（空经验不计 Skill）。
    终局否定态 → 可记 experience，但 **不** 入库有效 Skill（总纲 G8）。
    """
    ensure_store(store_dir)
    logs: list[dict[str, Any]] = read_session_patch_log(workspace_root)
    success_logs: list[dict[str, Any]] = [r for r in logs if r.get("ok")]
    if not success_logs:
        return {
            "ok": True,
            "skipped": True,
            "reason": "no_successful_patch",
            "experience_id": "",
            "skills_created": [],
            "skills_merged": [],
        }

    negative, neg_reason = session_is_negative_for_harvest(
        success_logs, user_rejected=user_rejected
    )

    exp_id: str = f"exp_{uuid.uuid4().hex[:12]}"
    # 隐私：不存真实姓名；展示名可保留短哈希
    name_hash: str = ""
    if display_name.strip():
        name_hash = hashlib.sha1(display_name.strip().encode("utf-8")).hexdigest()[:10]

    experience: dict[str, Any] = {
        "experience_id": exp_id,
        "session_id": session_id,
        "genre": genre,
        "display_name_hash": name_hash,
        "created_at": _now_iso(),
        "patch_count": len(success_logs),
        "user_texts": [str(r.get("user_text") or "")[:120] for r in success_logs][:12],
        "providers": list(
            dict.fromkeys(str(r.get("provider") or "") for r in success_logs)
        ),
        "files_touched": list(
            dict.fromkeys(
                f
                for r in success_logs
                for f in (r.get("sandbox_files") or [])
                if f
            )
        )[:40],
        "summaries": [str(r.get("summary") or "")[:200] for r in success_logs][:8],
        "negative_end_state": negative,
        "negative_reason": neg_reason,
    }
    exp_path: Path = store_dir / "experiences" / f"{exp_id}.json"
    exp_path.write_text(
        json.dumps(experience, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if negative:
        return {
            "ok": True,
            "skipped": True,
            "reason": f"negative_end_state:{neg_reason}",
            "experience_id": exp_id,
            "skills_created": [],
            "skills_merged": [],
            "rejected": 0,
            "patch_count": len(success_logs),
        }

    candidates: list[dict[str, Any]] = _extract_candidate_skills(
        genre, success_logs, workspace_root
    )
    skills: list[dict[str, Any]] = _load_index(store_dir)
    created: list[str] = []
    merged: list[str] = []
    rejected: int = 0
    for cand in candidates:
        if cand.get("safety") != "ok":
            rejected += 1
            continue
        skills, sid, is_new = _upsert_skill(store_dir, skills, cand, session_id)
        if not sid:
            continue
        if is_new:
            created.append(sid)
        else:
            merged.append(sid)
    _write_index(store_dir, skills)

    return {
        "ok": True,
        "skipped": False,
        "experience_id": exp_id,
        "skills_created": created,
        "skills_merged": merged,
        "rejected": rejected,
        "patch_count": len(success_logs),
    }


def clear_learned_skills(store_dir: Path, *, keep_experiences: bool = False) -> dict[str, Any]:
    """P1：讲解员清空经验库（本机运维）。"""
    root: Path = ensure_store(store_dir)
    index: Path = root / "index.jsonl"
    before_n: int = len(_load_index(root))
    index.write_text("", encoding="utf-8")
    snip_dir: Path = root / "snippets"
    removed_snips: int = 0
    if snip_dir.is_dir():
        for p in snip_dir.glob("*"):
            if p.is_file():
                p.unlink()
                removed_snips += 1
    removed_exps: int = 0
    if not keep_experiences:
        exp_dir: Path = root / "experiences"
        if exp_dir.is_dir():
            for p in exp_dir.glob("*.json"):
                p.unlink()
                removed_exps += 1
    return {
        "ok": True,
        "skills_cleared": before_n,
        "snippets_removed": removed_snips,
        "experiences_removed": removed_exps,
    }


def export_experience_pack(store_dir: Path, out_zip: Path) -> Path:
    """P2：跨馆导出经验包（zip：index + experiences + snippets）。"""
    root: Path = ensure_store(store_dir)
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(root / "index.jsonl", "index.jsonl")
        for p in (root / "experiences").glob("*.json"):
            zf.write(p, f"experiences/{p.name}")
        for p in (root / "snippets").glob("*"):
            if p.is_file():
                zf.write(p, f"snippets/{p.name}")
        meta = {
            "exported_at": _now_iso(),
            "skill_count": len(_load_index(root)),
            "format": "gameforge_learned_skills_v1",
        }
        zf.writestr("pack_meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
    return out_zip


def import_experience_pack(store_dir: Path, zip_path: Path) -> dict[str, Any]:
    """P2：导入经验包；Skill 按去重合并。"""
    if not zip_path.is_file():
        raise LearnedSkillsError(f"找不到经验包: {zip_path}")
    root: Path = ensure_store(store_dir)
    tmp: Path = root / f"_import_{int(time.time())}"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)
        incoming_index: Path = tmp / "index.jsonl"
        if not incoming_index.is_file():
            raise LearnedSkillsError("经验包缺少 index.jsonl")
        incoming: list[dict[str, Any]] = []
        for line in incoming_index.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("skill_id"):
                incoming.append(obj)

        skills: list[dict[str, Any]] = _load_index(root)
        created = 0
        merged = 0
        for cand_meta in incoming:
            if str(cand_meta.get("safety", "ok")) != "ok":
                continue
            # 复制 snippet
            snip_ref: str = str(cand_meta.get("snippet_ref") or "")
            snippet: str = ""
            if snip_ref:
                src: Path = tmp / snip_ref
                if src.is_file():
                    snippet = src.read_text(encoding="utf-8", errors="ignore")
            cand = {
                "genre": cand_meta.get("genre"),
                "title": cand_meta.get("title"),
                "trigger_phrases": cand_meta.get("trigger_phrases") or [],
                "summary": cand_meta.get("summary"),
                "how_to_play": cand_meta.get("how_to_play") or [],
                "safety": "ok",
                "snippet": snippet,
                "provider": cand_meta.get("provider") or "import",
                "applied_capabilities": cand_meta.get("applied_capabilities") or [],
            }
            skills, sid, is_new = _upsert_skill(root, skills, cand, "import")
            if not sid:
                continue
            if is_new:
                created += 1
            else:
                merged += 1
            # 若新建且有 snippet，路径已写；若导入自带 snip 文件名不同，上面已用内容重写

        _write_index(root, skills)
        # 可选拷贝 experiences（不去重）
        exp_imported = 0
        for p in (tmp / "experiences").glob("*.json"):
            dest = root / "experiences" / p.name
            if not dest.exists():
                shutil.copy2(p, dest)
                exp_imported += 1
        return {
            "ok": True,
            "skills_created": created,
            "skills_merged": merged,
            "experiences_imported": exp_imported,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def promote_learned_skill_to_proposal(
    store_dir: Path,
    skill_id: str,
    out_path: Path,
) -> Path:
    """P2：人工晋升——导出提案 JSON（不自动改 templates / optional_skills）。"""
    skills: list[dict[str, Any]] = _load_index(store_dir)
    skill: dict[str, Any] | None = next(
        (s for s in skills if str(s.get("skill_id")) == skill_id), None
    )
    if skill is None:
        raise LearnedSkillsError(f"Skill 不存在: {skill_id}")
    snippet: str = ""
    snip_ref: str = str(skill.get("snippet_ref") or "")
    if snip_ref:
        p: Path = store_dir / snip_ref
        if p.is_file():
            snippet = p.read_text(encoding="utf-8", errors="ignore")
    proposal: dict[str, Any] = {
        "format": "optional_skills_promotion_proposal_v1",
        "note": (
            "人工审核后手工合并到 config/optional_skills.json；"
            "禁止自动改 templates/** / 官方 optional_skills；本提案仅导出。"
        ),
        "auto_write_templates": False,
        "proposed_at": _now_iso(),
        "source_skill": skill,
        "verified_gate": bool(skill.get("verified_gate")),
        "suggested_catalog_entry": {
            "id": re.sub(r"[^a-z0-9_]+", "_", skill_id.lower())[:40],
            "label": str(skill.get("title") or skill_id)[:20],
            "desc": str(skill.get("summary") or "")[:60],
            "default_cooldown_ms": 0,
            "genre": skill.get("genre"),
            "how_to_play": skill.get("how_to_play") or [],
            "trigger_phrases": skill.get("trigger_phrases") or [],
        },
        "reference_snippet": snippet[:4000],
        "review_checklist": [
            "片段无幻想 API（add_method / set_color 等）",
            "how_to_play 与磁盘实现一致",
            "不自动写入 templates 或 optional_skills.json",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out_path
