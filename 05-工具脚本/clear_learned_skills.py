#!/usr/bin/env python3
"""讲解员运维：清空本机 Learned Skill 经验库。

用法:
  python 05-工具脚本/clear_learned_skills.py --confirm CLEAR
  python 05-工具脚本/clear_learned_skills.py --confirm CLEAR --keep-experiences
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.creative.learned_skills import clear_learned_skills  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="清空 Learned Skill 长期库")
    parser.add_argument("--confirm", required=True, help="必须为 CLEAR")
    parser.add_argument(
        "--keep-experiences",
        action="store_true",
        help="只清 Skill 索引与片段，保留 experiences/",
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=ROOT / "data" / "learned_skills",
        help="长期库目录",
    )
    args = parser.parse_args()
    if args.confirm.strip() != "CLEAR":
        print("拒绝：请传 --confirm CLEAR", file=sys.stderr)
        return 2
    result = clear_learned_skills(args.store, keep_experiences=args.keep_experiences)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
