#!/usr/bin/env python3
"""E2E-B-EDU-BROWSER · B 链教育版浏览器冒烟（6.24 P1-R 窗13）.

实现路径：Playwright（推荐）· 无 Playwright 时降级 HTTP API 链并提示手工 checklist。
复用 e2e_b_edu_batch.SLUG_CASES · platformer 见 E2E-B-EDU-001。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR: Path = Path(__file__).resolve().parent
ROOT: Path = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from e2e_b_edu_batch import SLUG_CASES, api_call, cleanup_sessions  # noqa: E402

DEFAULT_KIOSK: str = "http://127.0.0.1:8080"
DEFAULT_API: str = "http://127.0.0.1:8000"
DEFAULT_SLUGS: str = (
    "platformer,shmup,survivor,pingpong,fighting,parkour,racing"
)

PLATFORMER_CASE: dict[str, Any] = {
    "case_id": "E2E-B-EDU-001",
    "intent_text": "我想玩马里奥闯关",
    "display_name": "星星大冒险",
    "creative_answers": {
        "q_move": "fast",
        "q_jump": "high",
        "q_enemy": "hard",
        "q_lives": "high",
        "q_coin": "high",
    },
}

ALL_CASES: dict[str, dict[str, Any]] = {
    "platformer": PLATFORMER_CASE,
    **SLUG_CASES,
}


def has_playwright() -> bool:
    return importlib.util.find_spec("playwright") is not None


def assert_ok(name: str, condition: bool, detail: str = "") -> None:
    status: str = "PASS" if condition else "FAIL"
    msg: str = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def run_slug_http(api_base: str, slug: str, case: dict[str, Any]) -> dict[str, Any]:
    """降级：与 batch 相同 API 链 · 仅断言 generate/v2 ok."""
    from e2e_b_edu_batch import run_slug_e2e

    result: dict[str, Any] = run_slug_e2e(api_base, slug, case)
    return {
        "slug": slug,
        "case_id": case.get("case_id"),
        "mode": "http",
        "pass": bool(result.get("pass")),
        "session_id": result.get("session_id"),
    }


def run_slug_playwright(
    kiosk_base: str,
    api_base: str,
    slug: str,
    case: dict[str, Any],
    *,
    test_mode_edu: bool = False,
) -> dict[str, Any]:
    from playwright.sync_api import Page, sync_playwright

    display_name: str = str(case["display_name"])
    intent_text: str = str(case["intent_text"])
    answers: dict[str, Any] = dict(case["creative_answers"])
    gen_ok: bool = False
    work_name_ok: bool = False
    code_text_ok: bool = slug != "platformer"
    mode_edu_ok: bool = not test_mode_edu

    if test_mode_edu:
        start_url: str = f"{kiosk_base.rstrip('/')}/kiosk/?mode=edu"
    else:
        start_url = f"{kiosk_base.rstrip('/')}/kiosk/edu/"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page: Page = browser.new_page()

        def on_response(resp: Any) -> None:
            nonlocal gen_ok
            if (
                resp.request.method == "POST"
                and "/generate/v2" in resp.url
                and resp.status == 200
            ):
                try:
                    body: dict[str, Any] = resp.json()
                    if body.get("ok") is True:
                        gen_ok = True
                except Exception:
                    pass

        page.on("response", on_response)

        print(f"  → 打开 {start_url}")
        page.goto(start_url, wait_until="domcontentloaded", timeout=60_000)

        if test_mode_edu:
            page.wait_for_timeout(500)
            current: str = page.url
            mode_edu_ok = "/kiosk/edu" in current.replace("\\", "/")
            assert_ok(f"{slug}/mode_edu_redirect", mode_edu_ok, current)

        page.wait_for_selector("#btnNext:not([disabled])", timeout=30_000)

        # B1
        chip = page.locator(f"#intentExamples .chip[data-text='{intent_text}']")
        if chip.count() > 0:
            chip.first.click()
        else:
            page.fill("#intentInput", intent_text)
        page.click("#btnNext")

        # B2
        page.wait_for_selector("#nameInput", timeout=15_000)
        name_chip = page.locator(f"#nameChips .chip[data-name='{display_name}']")
        if name_chip.count() > 0:
            name_chip.first.click()
        else:
            page.fill("#nameInput", display_name)
        page.click("#btnNext")

        # B3
        page.wait_for_selector("#btnDualNext", timeout=15_000)
        page.click("#btnDualNext")

        # B4（用 JS 点击，避免双栏底栏遮挡与 DOM 稳定性问题）
        page.wait_for_selector(".creative-form-panel .question-block", timeout=20_000)
        page.wait_for_timeout(300)
        page.evaluate(
            """
            (answers) => {
              for (const [qid, value] of Object.entries(answers)) {
                const input = document.querySelector(
                  `.question-block[data-qid="${qid}"] input[type="radio"][value="${value}"]`
                );
                input?.closest(".option-card")?.click();
              }
            }
            """,
            answers,
        )
        page.wait_for_timeout(200)

        page.click("#btnDualNext")

        # B5 → generate
        deadline: float = time.time() + 120
        while time.time() < deadline and not gen_ok:
            page.wait_for_timeout(500)

        if gen_ok and slug == "platformer":
            deadline_code: float = time.time() + 45
            while time.time() < deadline_code:
                try:
                    page.wait_for_selector("#codeContent .line", timeout=5_000)
                    code_text = page.locator("#codeContent").inner_text(timeout=2_000)
                    if (
                        display_name in code_text
                        and "jump_velocity" in code_text
                        and "move_speed" in code_text
                    ):
                        code_text_ok = True
                        break
                except Exception:
                    pass
                page.wait_for_timeout(500)
            assert_ok(
                f"{slug}/workspace_game_config",
                code_text_ok,
                "左侧须含 display_name 与 tuning 真字段",
            )

        work_name: str = page.locator("#workName").inner_text(timeout=5_000)
        work_name_ok = display_name in work_name

        browser.close()

    assert_ok(f"{slug}/generate_v2", gen_ok, "POST generate/v2 ok=true")
    assert_ok(f"{slug}/workName", work_name_ok, work_name)

    return {
        "slug": slug,
        "case_id": case.get("case_id"),
        "mode": "playwright",
        "pass": gen_ok and work_name_ok and mode_edu_ok and code_text_ok,
        "generate_ok": gen_ok,
        "work_name_ok": work_name_ok,
        "code_text_ok": code_text_ok,
        "mode_edu_redirect": mode_edu_ok,
    }


def run_smoke(
    kiosk_base: str,
    api_base: str,
    slugs: list[str],
    *,
    use_playwright: bool | None = None,
) -> dict[str, Any]:
    playwright_available: bool = has_playwright()
    mode: str = "playwright" if (use_playwright is not False and playwright_available) else "http"

    if use_playwright is True and not playwright_available:
        raise RuntimeError(
            "需要 Playwright：pip install playwright && playwright install chromium"
        )

    cleanup_sessions(api_base)

    summary: dict[str, Any] = {
        "case_id": "E2E-B-EDU-BROWSER",
        "kiosk": kiosk_base,
        "api": api_base,
        "mode": mode,
        "slugs": slugs,
        "results": [],
    }

    if mode == "http":
        print(
            "WARN Playwright unavailable - HTTP API fallback only. "
            "Manual browser checklist (>=3 genres) still required for gate #6."
        )

    passed: int = 0
    for idx, slug in enumerate(slugs):
        if slug not in ALL_CASES:
            raise ValueError(f"未知 slug: {slug} · 可选: {','.join(ALL_CASES)}")
        case: dict[str, Any] = ALL_CASES[slug]
        print(f"\n=== {case.get('case_id')} · {slug} · {mode} ===")
        if mode == "playwright":
            result = run_slug_playwright(
                kiosk_base,
                api_base,
                slug,
                case,
                test_mode_edu=(idx == 0 and slug == "platformer"),
            )
        else:
            if slug == "platformer":
                from e2e_b_edu_platformer import run_e2e_b_edu

                r = run_e2e_b_edu(api_base, str(case["display_name"]))
                result = {
                    "slug": slug,
                    "case_id": case.get("case_id"),
                    "mode": "http",
                    "pass": bool(r.get("pass")),
                    "session_id": r.get("session_id"),
                }
            else:
                result = run_slug_http(api_base, slug, case)
        summary["results"].append(result)
        if result.get("pass"):
            passed += 1

    summary["passed"] = passed
    summary["total"] = len(slugs)
    summary["pass"] = passed == len(slugs)
    return summary


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="E2E-B-EDU-BROWSER 七款浏览器冒烟")
    parser.add_argument(
        "--kiosk",
        default=DEFAULT_KIOSK,
        help=f"Static server base (default: {DEFAULT_KIOSK})",
    )
    parser.add_argument(
        "--api",
        default=DEFAULT_API,
        help=f"Backend API base (default: {DEFAULT_API})",
    )
    parser.add_argument(
        "--slugs",
        default=DEFAULT_SLUGS,
        help=f"Comma-separated slugs (default: all 7)",
    )
    parser.add_argument(
        "--http-only",
        action="store_true",
        help="强制 HTTP 降级（不启 Playwright）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    slugs: list[str] = [s.strip() for s in args.slugs.split(",") if s.strip()]
    use_pw: bool | None = False if args.http_only else None
    print(
        f"E2E-B-EDU-BROWSER · kiosk={args.kiosk} · api={args.api} · "
        f"slugs={','.join(slugs)}"
    )
    try:
        summary = run_smoke(args.kiosk, args.api, slugs, use_playwright=use_pw)
        print("\n=== SUMMARY ===")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"\n{summary['passed']}/{summary['total']} PASS · mode={summary['mode']}")
        return 0 if summary.get("pass") else 1
    except (AssertionError, ValueError, RuntimeError) as exc:
        print(f"冒烟失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
