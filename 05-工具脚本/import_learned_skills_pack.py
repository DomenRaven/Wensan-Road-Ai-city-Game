#!/usr/bin/env python3
"""P2：导入 Learned Skill 经验包（跨馆，去重合并）。

用法:
  python 05-工具脚本/import_learned_skills_pack.py path/to/pack.zip
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.creative.learned_skills import (  # noqa: E402
    LearnedSkillsError,
    import_experience_pack,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="导入经验包 zip")
    parser.add_argument("zip_path", type=Path)
    parser.add_argument(
        "--store",
        type=Path,
        default=ROOT / "data" / "learned_skills",
    )
    args = parser.parse_args()
    try:
        result = import_experience_pack(args.store, args.zip_path)
    except LearnedSkillsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
