#!/usr/bin/env python3
"""P2：导出 Learned Skill 经验包（跨馆）。

用法:
  python 05-工具脚本/export_learned_skills_pack.py
  python 05-工具脚本/export_learned_skills_pack.py -o /path/to/pack.zip
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.creative.learned_skills import export_experience_pack  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="导出经验包 zip")
    parser.add_argument(
        "--store",
        type=Path,
        default=ROOT / "data" / "learned_skills",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="输出 zip 路径",
    )
    args = parser.parse_args()
    out = args.out or (args.store / "exports" / "learned_skills_pack.zip")
    path = export_experience_pack(args.store, out)
    print(f"exported: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
