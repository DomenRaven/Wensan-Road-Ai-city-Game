#!/usr/bin/env python3
"""RECIPE-A · B6 作品登记证书 · Playwright 冒烟（横屏 + 竖屏）."""
from __future__ import annotations

import argparse
import sys
from typing import Any

from playwright.sync_api import Page, sync_playwright

DEFAULT_KIOSK: str = "http://127.0.0.1:8080"

PLATFORMER_CASE: dict[str, Any] = {
    "intent_text": "我想玩马里奥闯关",
    "display_name": "星星大冒险",
    "genre_label": "横版闯关",
    "creative_answers": {
        "q_move": "fast",
        "q_jump": "high",
        "q_enemy": "hard",
        "q_lives": "high",
        "q_coin": "high",
    },
}


def assert_ok(name: str, condition: bool, detail: str = "") -> None:
    status: str = "PASS" if condition else "FAIL"
    msg: str = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def advance_to_b6(page: Page, case: dict[str, Any]) -> None:
    intent_text: str = str(case["intent_text"])
    display_name: str = str(case["display_name"])
    answers: dict[str, str] = dict(case["creative_answers"])

    page.wait_for_selector("#btnNext:not([disabled])", timeout=30_000)
    chip = page.locator(f"#intentExamples .chip[data-text='{intent_text}']")
    if chip.count() > 0:
        chip.first.click()
    else:
        page.fill("#intentInput", intent_text)
    page.click("#btnNext")

    page.wait_for_selector("#nameInput", timeout=15_000)
    name_chip = page.locator(f"#nameChips .chip[data-name='{display_name}']")
    if name_chip.count() > 0:
        name_chip.first.click()
    else:
        page.fill("#nameInput", display_name)
    page.click("#btnNext")

    page.wait_for_selector("#btnDualNext", timeout=15_000)
    page.click("#btnDualNext")

    page.wait_for_selector(".creative-form-panel .question-block", timeout=20_000)
    page.evaluate(
        """
        (answers) => {
          for (const [qid, value] of Object.entries(answers)) {
            document.querySelector(
              `.question-block[data-qid="${qid}"] input[type="radio"][value="${value}"]`
            )?.closest('.option-card')?.click();
          }
        }
        """,
        answers,
    )
    page.wait_for_timeout(200)
    page.click("#btnDualNext")


def verify_certificate(page: Page, case: dict[str, Any], orientation: str) -> None:
    display_name: str = str(case["display_name"])
    genre_label: str = str(case["genre_label"])

    page.wait_for_selector("#edu-certificate-overlay:not([hidden])", timeout=180_000)
    cert_text: str = page.locator("#edu-certificate").inner_text(timeout=5_000)

    assert_ok(f"{orientation}/cert_title", "作品登记证书" in cert_text or "AI 小游戏创作工坊" in cert_text)
    assert_ok(f"{orientation}/cert_name", display_name in cert_text, display_name)
    assert_ok(f"{orientation}/cert_genre", genre_label in cert_text, genre_label)
    assert_ok(
        f"{orientation}/cert_recipe",
        "快一点" in cert_text or "你的选择" in cert_text,
    )
    assert_ok(f"{orientation}/no_skill", "小技能" not in cert_text)

    mode: str | None = page.evaluate("document.body.getAttribute('data-orientation')")
    assert_ok(f"{orientation}/body_orientation", mode == orientation, str(mode))

    box = page.locator("#edu-certificate").bounding_box()
    assert_ok(
        f"{orientation}/cert_in_viewport",
        bool(box and box.get("height", 0) > 80),
        str(box),
    )

    print_btn = page.locator("#btnCertPrint")
    continue_btn = page.locator("#btnCertContinue")
    print_box = print_btn.bounding_box()
    continue_box = continue_btn.bounding_box()
    assert_ok(
        f"{orientation}/touch_targets",
        bool(
            print_box
            and continue_box
            and print_box.get("height", 0) >= 44
            and continue_box.get("height", 0) >= 44
        ),
    )

    page.click("#btnCertContinue")
    page.wait_for_function(
        "() => document.getElementById('edu-certificate-overlay')?.hidden === true",
        timeout=5_000,
    )
    assert_ok(f"{orientation}/overlay_hidden", page.locator("#edu-certificate-overlay").is_hidden())

    page.wait_for_selector("#btnLaunch", timeout=10_000)
    launch_box = page.locator("#btnLaunch").bounding_box()
    assert_ok(
        f"{orientation}/launch_cta",
        bool(launch_box and launch_box.get("height", 0) >= 44),
    )

    print_rules: int = page.evaluate(
        """
        () => {
          let n = 0;
          for (const sheet of document.styleSheets) {
            try {
              for (const rule of sheet.cssRules) {
                if (rule.cssText && rule.cssText.includes('edu-printing')) n += 1;
              }
            } catch (_) {}
          }
          return n;
        }
        """
    )
    assert_ok(f"{orientation}/print_css", print_rules >= 1, str(print_rules))


def run_case(kiosk_base: str) -> None:
    url: str = f"{kiosk_base.rstrip('/')}/kiosk/edu/"
    viewports: list[tuple[str, tuple[int, int]]] = [
        ("landscape", (1280, 800)),
        ("portrait", (480, 900)),
    ]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        for orientation, size in viewports:
            print(f"\n=== {orientation} {size[0]}x{size[1]} ===")
            page.set_viewport_size({"width": size[0], "height": size[1]})
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(500)
            advance_to_b6(page, PLATFORMER_CASE)
            verify_certificate(page, PLATFORMER_CASE, orientation)

        browser.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RECIPE-A certificate B6 smoke")
    parser.add_argument("--kiosk", default=DEFAULT_KIOSK)
    args = parser.parse_args(argv)
    print(f"E2E-RECIPE-A-CERT · kiosk={args.kiosk}")
    try:
        run_case(args.kiosk)
        print("\nALL PASS")
        return 0
    except AssertionError as exc:
        print(f"\nFAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
