#!/usr/bin/env python3
"""P2：人工晋升 Learned Skill → 官方 optional_skills 提案（不自动改 templates）。

用法:
  python 05-工具脚本/promote_learned_skill.py ls_platformer_xxxx
  # 审核提案 JSON 后，手工合并到 config/optional_skills.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.creative.learned_skills import (  # noqa: E402
    LearnedSkillsError,
    promote_learned_skill_to_proposal,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="导出 optional_skills 晋升提案")
    parser.add_argument("skill_id")
    parser.add_argument(
        "--store",
        type=Path,
        default=ROOT / "data" / "learned_skills",
    )
    parser.add_argument("-o", "--out", type=Path, default=None)
    args = parser.parse_args()
    out = args.out or (
        args.store / "proposals" / f"{args.skill_id}_optional_skills_proposal.json"
    )
    try:
        path = promote_learned_skill_to_proposal(args.store, args.skill_id, out)
    except LearnedSkillsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"proposal: {path}")
    print("下一步：人工审核后手工合并到 config/optional_skills.json（禁止自动改 templates）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
