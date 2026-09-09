"""Render the running app and check its layout at several widths.

The dataviz skill's last step is "render it and look at it" - a palette
validator checks colour, not geometry. This script is how that step gets done
without a person squinting at three browser windows.

It catches, automatically, the two failures that are invisible in code review:
a page that scrolls horizontally, and text clipped by its own container.

    docker compose up -d          # the app must be running
    python scripts/screenshot_ui.py

Screenshots land in .screenshots/ (gitignored). Requires:
    pip install -e './backend[dev]' && playwright install chromium
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:5173"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / ".screenshots"
# Width, label, colour scheme. Mobile first, because that is where layout breaks.
VIEWPORTS = [
    (390, "mobile", "light"),
    (768, "tablet", "light"),
    (1280, "desktop", "light"),
    (1280, "desktop", "dark"),
]
# Elements whose text must never be cut off by its own box.
CLIP_SELECTOR = ".stat-value, .stat-label, .bar-value, .bar-label"


def main() -> int:
    """Capture each viewport and report layout defects. Returns a process exit code."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    failures: list[str] = []

    with sync_playwright() as runner:
        browser = runner.chromium.launch()
        for width, label, scheme in VIEWPORTS:
            name = f"{label}-{scheme}"
            page = browser.new_page(
                viewport={"width": width, "height": 900}, color_scheme=scheme
            )
            page.goto(URL, wait_until="networkidle")
            page.wait_for_selector(".app", timeout=15_000)
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUTPUT_DIR / f"{name}.png"), full_page=True)

            overflow = page.evaluate(
                "() => document.documentElement.scrollWidth"
                " - document.documentElement.clientWidth"
            )
            clipped = page.evaluate(
                "(selector) => [...document.querySelectorAll(selector)]"
                ".filter(el => el.scrollWidth > el.clientWidth + 1)"
                ".map(el => el.textContent.trim())",
                CLIP_SELECTOR,
            )

            if overflow > 0:
                failures.append(f"{name}: page scrolls horizontally by {overflow}px")
            if clipped:
                failures.append(f"{name}: text clipped -> {clipped}")
            status = "ok" if overflow == 0 and not clipped else "FAIL"
            print(f"  {name:<16} {status:<5} overflow={overflow}px clipped={len(clipped)}")
            page.close()
        browser.close()

    if failures:
        print("\nLayout problems:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"\nAll viewports clean. Screenshots in {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
