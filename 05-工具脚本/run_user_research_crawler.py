# -*- coding: utf-8 -*-
"""启动 K12 用户向调研检索（Survey-02）。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRAWLER_SRC = (
    ROOT.parent
    / "1未来隧道部分"
    / "研究资料"
    / "AI出行体验舱_技术调研"
    / "crawler"
    / "src"
)
CONFIG = ROOT / "03-背景与调研" / "config" / "k12_user_research_queries.yaml"
OUTPUT = ROOT / "03-背景与调研" / "data" / "K12用户向调研"
PATCH = Path(__file__).resolve().parent / "game_crawler_patch.py"
PYTHON = os.environ.get(
    "GAME_RESEARCH_PYTHON",
    str(
        ROOT.parent
        / "1未来隧道部分"
        / "研究资料"
        / "AI出行体验舱_技术调研"
        / "crawler"
        / ".venv"
        / "Scripts"
        / "python.exe"
    ),
)

LAUNCHER = r"""
import sys
from pathlib import Path
sys.path.insert(0, r"{crawler_src}")
sys.path.insert(0, r"{tools}")
from game_crawler_patch import apply_game_keyword_patch
apply_game_keyword_patch()
from research_crawler.cli import main
sys.argv = [
    "research_crawler",
    "--config", r"{config}",
    "-o", r"{output}",
    "--sources", "web,bilibili,csdn,github,zhihu,juejin",
    "--max-per-query", "5",
    "--min-score", "25",
    "--time-limit-minutes", "45",
    "--fetch",
] + sys.argv[1:]
raise SystemExit(main())
""".strip()


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    code = LAUNCHER.format(
        crawler_src=str(CRAWLER_SRC),
        tools=str(Path(__file__).resolve().parent),
        config=str(CONFIG),
        output=str(OUTPUT),
    )
    cmd = [PYTHON, "-c", code] + sys.argv[1:]
    print("Python:", PYTHON)
    print("Config:", CONFIG)
    print("Output:", OUTPUT)
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
