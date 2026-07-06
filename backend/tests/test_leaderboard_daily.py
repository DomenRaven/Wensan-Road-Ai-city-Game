from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.services.leaderboard_daily import append_entry, get_daily_top, resolve_date


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    root: Path = tmp_path / "data"
    root.mkdir()
    return root


def test_append_and_get_daily_top_platformer(data_dir: Path) -> None:
    append_entry(
        data_dir,
        "platformer",
        creator_name="小明",
        display_name="跳跳冒险",
        score=100,
        elapsed_ms=50000,
        level_reached=1,
        metric="level_reached",
        session_id="sess-a",
    )
    append_entry(
        data_dir,
        "platformer",
        creator_name="小红",
        display_name="金币猎人",
        score=200,
        elapsed_ms=60000,
        level_reached=2,
        metric="level_reached",
        session_id="sess-b",
    )
    append_entry(
        data_dir,
        "platformer",
        creator_name="小刚",
        display_name="同关高分",
        score=300,
        elapsed_ms=40000,
        level_reached=2,
        metric="level_reached",
        session_id="sess-c",
    )
    append_entry(
        data_dir,
        "platformer",
        creator_name="小丽",
        display_name="同关低分",
        score=250,
        elapsed_ms=30000,
        level_reached=2,
        metric="level_reached",
        session_id="sess-d",
    )

    today: date = resolve_date("today")
    rows = get_daily_top(data_dir, "platformer", day=today, limit=10)
    assert len(rows) == 4
    assert rows[0]["rank"] == 1
    assert rows[0]["level_reached"] == 2
    assert rows[0]["score"] == 300
    assert rows[1]["level_reached"] == 2
    assert rows[1]["score"] == 250
    assert rows[2]["level_reached"] == 2
    assert rows[2]["score"] == 200
    assert rows[3]["level_reached"] == 1


def test_survivor_sort_by_survival_ms(data_dir: Path) -> None:
    append_entry(
        data_dir,
        "survivor",
        creator_name="A",
        display_name="A",
        survival_ms=120000,
        metric="survival_ms",
    )
    append_entry(
        data_dir,
        "survivor",
        creator_name="B",
        display_name="B",
        survival_ms=180000,
        metric="survival_ms",
    )

    today: date = resolve_date("today")
    rows = get_daily_top(data_dir, "survivor", day=today, limit=10)
    assert rows[0]["survival_ms"] == 180000
    assert rows[1]["survival_ms"] == 120000


def test_creator_name_fallback(data_dir: Path) -> None:
    entry = append_entry(
        data_dir,
        "shmup",
        creator_name="",
        display_name="雷霆",
        score=50,
        metric="score",
    )
    assert entry["creator_name"] == "小创作者"


def test_parkour_sort_by_distance(data_dir: Path) -> None:
    append_entry(
        data_dir,
        "parkour",
        creator_name="A",
        display_name="A",
        score=100,
        survival_ms=60000,
        metric="distance_m",
    )
    append_entry(
        data_dir,
        "parkour",
        creator_name="B",
        display_name="B",
        score=250,
        survival_ms=30000,
        metric="distance_m",
    )
    today: date = resolve_date("today")
    rows = get_daily_top(data_dir, "parkour", day=today, limit=10)
    assert rows[0]["score"] == 250


def test_racing_sort_by_laps(data_dir: Path) -> None:
    append_entry(
        data_dir,
        "racing",
        creator_name="A",
        display_name="A",
        score=2,
        elapsed_ms=50000,
        metric="lap_count",
    )
    append_entry(
        data_dir,
        "racing",
        creator_name="B",
        display_name="B",
        score=5,
        elapsed_ms=80000,
        metric="lap_count",
    )
    today: date = resolve_date("today")
    rows = get_daily_top(data_dir, "racing", day=today, limit=10)
    assert rows[0]["score"] == 5


def test_racing_same_laps_faster_wins(data_dir: Path) -> None:
    append_entry(
        data_dir,
        "racing",
        creator_name="慢车",
        display_name="A",
        score=4,
        elapsed_ms=85000,
        metric="lap_count",
    )
    append_entry(
        data_dir,
        "racing",
        creator_name="快车",
        display_name="B",
        score=4,
        elapsed_ms=72000,
        metric="lap_count",
    )
    today: date = resolve_date("today")
    rows = get_daily_top(data_dir, "racing", day=today, limit=10)
    assert rows[0]["elapsed_ms"] == 72000
    assert rows[1]["elapsed_ms"] == 85000


def test_parkour_same_distance_faster_wins(data_dir: Path) -> None:
    append_entry(
        data_dir,
        "parkour",
        creator_name="A",
        display_name="A",
        score=300,
        survival_ms=45000,
        metric="distance_m",
    )
    append_entry(
        data_dir,
        "parkour",
        creator_name="B",
        display_name="B",
        score=300,
        survival_ms=32000,
        metric="distance_m",
    )
    today: date = resolve_date("today")
    rows = get_daily_top(data_dir, "parkour", day=today, limit=10)
    assert rows[0]["survival_ms"] == 32000


def test_survivor_same_time_higher_level_wins(data_dir: Path) -> None:
    append_entry(
        data_dir,
        "survivor",
        creator_name="A",
        display_name="A",
        score=5,
        survival_ms=120000,
        metric="survival_ms",
    )
    append_entry(
        data_dir,
        "survivor",
        creator_name="B",
        display_name="B",
        score=8,
        survival_ms=120000,
        metric="survival_ms",
    )
    today: date = resolve_date("today")
    rows = get_daily_top(data_dir, "survivor", day=today, limit=10)
    assert rows[0]["score"] == 8


def test_fighting_win_over_draw_over_loss(data_dir: Path) -> None:
    append_entry(
        data_dir,
        "fighting",
        creator_name="败",
        display_name="A",
        score=0,
        metric="win",
    )
    append_entry(
        data_dir,
        "fighting",
        creator_name="平",
        display_name="B",
        score=1,
        metric="win",
    )
    append_entry(
        data_dir,
        "fighting",
        creator_name="胜",
        display_name="C",
        score=2,
        metric="win",
    )
    today: date = resolve_date("today")
    rows = get_daily_top(data_dir, "fighting", day=today, limit=10)
    assert [row["score"] for row in rows] == [2, 1, 0]


def test_shmup_same_score_longer_survival_wins(data_dir: Path) -> None:
    append_entry(
        data_dir,
        "shmup",
        creator_name="A",
        display_name="A",
        score=500,
        survival_ms=60000,
        metric="score",
    )
    append_entry(
        data_dir,
        "shmup",
        creator_name="B",
        display_name="B",
        score=500,
        survival_ms=90000,
        metric="score",
    )
    today: date = resolve_date("today")
    rows = get_daily_top(data_dir, "shmup", day=today, limit=10)
    assert rows[0]["survival_ms"] == 90000
