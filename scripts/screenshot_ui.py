"""Render the running app and check its layout at several widths.

The dataviz skill's last step is "render it and look at it" - a palette
validator checks colour, not geometry. This script is how that step gets done
without a person squinting at three browser windows.

It catches, automatically, three failures that are invisible in code review:
a page that scrolls horizontally, text clipped by its own container, and a
table column whose header does not line up with the values beneath it.

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

# Every column header must share both its alignment and its visible text edge
# with the cells below it. A header drifting from its own values reads as data
# in the wrong column, and no amount of correct markup makes that look right.
ALIGNMENT_CHECK = """() => {
  const problems = [];
  document.querySelectorAll('table').forEach((table, ti) => {
    const headers = [...table.querySelectorAll('thead th')];
    const rows = [...table.querySelectorAll('tbody tr')];
    headers.forEach((th, ci) => {
      const headerAlign = getComputedStyle(th).textAlign;
      const headerBox = th.getBoundingClientRect();
      rows.forEach((tr, ri) => {
        const td = tr.children[ci];
        if (!td) return;
        const cellAlign = getComputedStyle(td).textAlign;
        const cellBox = td.getBoundingClientRect();
        const where = `table ${ti} col "${th.textContent.trim()}" row ${ri}`;
        if (headerAlign !== cellAlign) {
          problems.push(`${where}: header is ${headerAlign}, cell is ${cellAlign}`);
          return;
        }
        const drift = cellAlign === 'right'
          ? Math.abs(headerBox.right - cellBox.right)
          : Math.abs(headerBox.left - cellBox.left);
        if (drift > 1) {
          problems.push(`${where}: ${cellAlign} edges differ by ${Math.round(drift)}px`);
        }
      });
    });
  });
  return problems;
}"""


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

            misaligned = page.evaluate(ALIGNMENT_CHECK)

            if overflow > 0:
                failures.append(f"{name}: page scrolls horizontally by {overflow}px")
            if clipped:
                failures.append(f"{name}: text clipped -> {clipped}")
            failures += [f"{name}: {problem}" for problem in misaligned]

            ok = overflow == 0 and not clipped and not misaligned
            print(
                f"  {name:<16} {'ok' if ok else 'FAIL':<5} "
                f"overflow={overflow}px clipped={len(clipped)} misaligned={len(misaligned)}"
            )
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
