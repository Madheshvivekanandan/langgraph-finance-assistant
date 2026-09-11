"""Render every route of the running app and check its layout and contrast.

The dataviz skill's last step is "render it and look at it" - a palette
validator checks colour, not geometry, and a geometry check alone is blind to
contrast. This script is how both steps get done without a person squinting
at dozens of browser windows.

It catches, automatically: a page that scrolls horizontally, text clipped by
its own container, a table column whose header does not line up with the
values beneath it, a route that silently renders nothing (the landmark
check), and text that does not meet WCAG contrast against its own background
-- including the mermaid pipeline diagram, which is where the contrast gap
that motivated this gate's extension actually shipped.

    docker compose up -d --build   # the app must be running on the NEW build
    python scripts/screenshot_ui.py

Screenshots land in .screenshots/ (gitignored). Requires:
    pip install -e './backend[dev]' && playwright install chromium
"""

import sys
from pathlib import Path
from typing import Callable

from playwright.sync_api import Page, sync_playwright

URL = "http://localhost:5173"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / ".screenshots"

# Path and the `data-view` landmark each view renders (D5's anti-false-PASS
# assertion: a router misconfiguration that renders a blank outlet must fail
# loudly, not pass every geometry check trivially).
ROUTES: list[tuple[str, str]] = [
    ("/", "overview"),
    ("/transactions", "transactions"),
    ("/statements", "statements"),
    ("/review", "review"),
    ("/pipeline", "pipeline"),
]

# Width, label, colour scheme. Mobile first, because that is where layout breaks.
VIEWPORTS = [
    (390, "mobile", "light"),
    (768, "tablet", "light"),
    (1280, "desktop", "light"),
    (1280, "desktop", "dark"),
]

# The number of states a full run must capture, written out as a literal on
# purpose. Deriving it from VIEWPORTS/ROUTES would compare the counter against
# the very collections that drive the loop, so a shrunken matrix would still
# pass (D5: fewer than this many states is a failure even when every state
# printed is ok). Update it deliberately, in the same commit, when a route,
# a viewport, or an overlay state is added or removed.
#   4 viewports x 5 routes = 20, plus 4 overlay states (3 chat, 1 nav drawer).
EXPECTED_STATES = 24

# Elements whose text must never be cut off by its own box.
CLIP_SELECTOR = (
    ".stat-value, .stat-label, .bar-value, .bar-label, "
    ".nav-item-label, .badge-count, .view-title"
)

# The narrow, deliberate list of chrome text checked for contrast on every
# state (D5). Chart internals (axis labels, tooltips) are excluded: they are
# not chrome, and the token layer's own AA verification already covers them.
CHROME_CONTRAST_SELECTOR = ".stat-value, .stat-label, .nav-item-label, .badge-count, h1, .bar-label, .bar-value"

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

# Shared colour-math helpers, inlined into both contrast checks below (no
# module system inside `page.evaluate` — string concatenation is the
# mechanism Playwright gives us for reusing JS across two evaluate calls).
_CONTRAST_HELPERS = """
  function parseRgb(str) {
    if (!str) return null;
    const m = str.match(/rgba?\\(([^)]+)\\)/);
    if (!m) return null;
    const parts = m[1].split(',').map((s) => parseFloat(s.trim()));
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  }
  function relLuminance(rgb) {
    const toLinear = (c) => {
      const s = c / 255;
      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * toLinear(rgb.r) + 0.7152 * toLinear(rgb.g) + 0.0722 * toLinear(rgb.b);
  }
  function contrastRatio(a, b) {
    const l1 = relLuminance(a);
    const l2 = relLuminance(b);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  }
"""

# On `/pipeline` states only: the WCAG contrast ratio between each mermaid
# node's fill and its label must be >= 4.5. The shipped bug measured ~1.05 --
# this check would have caught it outright. Zero nodes is also a failure: a
# diagram that failed to render must not pass a contrast check by vacuity.
DIAGRAM_CONTRAST_CHECK = (
    """() => {"""
    + _CONTRAST_HELPERS
    + """
  const nodes = [...document.querySelectorAll('.graph-diagram g.node')];
  if (nodes.length === 0) return ['no mermaid nodes found -- diagram failed to render'];
  const problems = [];
  nodes.forEach((node, i) => {
    const shape = node.querySelector('rect, polygon, path');
    const label = node.querySelector('.nodeLabel') || node.querySelector('text');
    if (!shape || !label) {
      problems.push(`node ${i}: missing shape or label element`);
      return;
    }
    const fillRgb = parseRgb(getComputedStyle(shape).fill);
    const colourProp = label.tagName.toLowerCase() === 'text'
      ? getComputedStyle(label).fill
      : getComputedStyle(label).color;
    const textRgb = parseRgb(colourProp);
    if (!fillRgb || !textRgb) {
      problems.push(`node ${i}: could not parse fill/text colour`);
      return;
    }
    const ratio = contrastRatio(fillRgb, textRgb);
    if (ratio < 4.5) {
      problems.push(`node ${i} contrast ${ratio.toFixed(2)} < 4.5`);
    }
  });
  return problems;
}"""
)

# On every state: chrome text against its nearest non-transparent ancestor
# background. 4.5:1, relaxed to 3.0:1 for large text per WCAG (>=24px, or
# >=18.66px at bold). Empty or zero-size elements are skipped -- an element
# hidden by the current breakpoint (e.g. `.nav-item-label` in the icon rail)
# has nothing to be illegible.
CHROME_CONTRAST_CHECK = (
    """(selector) => {"""
    + _CONTRAST_HELPERS
    + """
  function backgroundOf(el) {
    let node = el;
    while (node) {
      const rgb = parseRgb(getComputedStyle(node).backgroundColor);
      if (rgb && rgb.a !== 0) return rgb;
      node = node.parentElement;
    }
    return { r: 255, g: 255, b: 255, a: 1 };
  }
  const problems = [];
  document.querySelectorAll(selector).forEach((el) => {
    const text = el.textContent.trim();
    const box = el.getBoundingClientRect();
    if (!text || box.width === 0 || box.height === 0) return;
    const cs = getComputedStyle(el);
    const textRgb = parseRgb(cs.color);
    if (!textRgb) return;
    const bgRgb = backgroundOf(el.parentElement || el);
    const ratio = contrastRatio(textRgb, bgRgb);
    const fontSize = parseFloat(cs.fontSize);
    const isBold = parseInt(cs.fontWeight, 10) >= 700;
    const isLarge = fontSize >= 24 || (fontSize >= 18.66 && isBold);
    const threshold = isLarge ? 3.0 : 4.5;
    if (ratio < threshold) {
      problems.push(`"${text.slice(0, 40)}" contrast ${ratio.toFixed(2)} < ${threshold}`);
    }
  });
  return problems;
}"""
)


def capture_state(
    browser,
    *,
    name: str,
    path: str,
    view_id: str,
    width: int,
    scheme: str,
    check_diagram: bool,
    before_capture: Callable[[Page], None] | None = None,
) -> list[str]:
    """Load one route at one viewport/scheme, screenshot it, and return its failures."""
    failures: list[str] = []
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
    page.goto(f"{URL}{path}", wait_until="networkidle")
    page.wait_for_selector(".app", timeout=15_000)

    try:
        page.wait_for_selector(f'[data-view="{view_id}"]', timeout=5_000)
    except Exception:
        failures.append(f"{name}: missing [data-view=\"{view_id}\"] landmark")

    if before_capture:
        before_capture(page)

    if view_id == "pipeline":
        # mermaid is dynamically imported and renders async; give it a real
        # chance before the contrast check decides the diagram never showed up.
        try:
            page.wait_for_selector(".graph-diagram svg", timeout=10_000)
        except Exception:
            pass

    page.wait_for_timeout(400)
    page.screenshot(path=str(OUTPUT_DIR / f"{name}.png"), full_page=True)

    h1_count = page.evaluate("() => document.querySelectorAll('h1').length")
    if h1_count != 1:
        failures.append(f"{name}: expected exactly one <h1>, found {h1_count}")

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
    chrome_contrast = page.evaluate(CHROME_CONTRAST_CHECK, CHROME_CONTRAST_SELECTOR)
    diagram_contrast = page.evaluate(DIAGRAM_CONTRAST_CHECK) if check_diagram else []
    low_contrast = chrome_contrast + diagram_contrast

    if overflow > 0:
        failures.append(f"{name}: page scrolls horizontally by {overflow}px")
    if clipped:
        failures.append(f"{name}: text clipped -> {clipped}")
    failures += [f"{name}: {problem}" for problem in misaligned]
    failures += [f"{name}: {problem}" for problem in low_contrast]

    ok = not failures
    print(
        f"  {name:<28} {'ok' if ok else 'FAIL':<5} "
        f"overflow={overflow}px clipped={len(clipped)} misaligned={len(misaligned)} "
        f"low-contrast={len(low_contrast)}"
    )
    page.close()
    return failures


def open_nav_drawer(page: Page) -> None:
    """Drives the mobile nav drawer open via its stable toggle attribute. Failing to
    find the toggle is itself an assertion -- the drawer must exist at this width."""
    toggle = page.locator("[data-nav-toggle]")
    if toggle.count() == 0:
        raise AssertionError("[data-nav-toggle] not found at mobile width")
    toggle.first.click()
    page.wait_for_selector("dialog.sidebar[open]", timeout=5_000)


def main() -> int:
    """Capture every route at every viewport/scheme, plus the chat/nav overlay
    states, and report layout and contrast defects. Returns a process exit code."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    failures: list[str] = []
    state_count = 0

    with sync_playwright() as runner:
        browser = runner.chromium.launch()

        for width, viewport_label, scheme in VIEWPORTS:
            for path, view_id in ROUTES:
                name = f"{view_id}-{viewport_label}-{scheme}"
                failures += capture_state(
                    browser,
                    name=name,
                    path=path,
                    view_id=view_id,
                    width=width,
                    scheme=scheme,
                    check_diagram=view_id == "pipeline",
                )
                state_count += 1

        # Chat/nav overlay states (D5): the two surfaces that can cover
        # content, squeeze the main column, or introduce a scrollbar.
        failures += capture_state(
            browser,
            name="overview-desktop-light-chat",
            path="/?chat=open",
            view_id="overview",
            width=1280,
            scheme="light",
            check_diagram=False,
        )
        state_count += 1

        failures += capture_state(
            browser,
            name="transactions-desktop-light-chat",
            path="/transactions?chat=open",
            view_id="transactions",
            width=1280,
            scheme="light",
            check_diagram=False,
        )
        state_count += 1

        failures += capture_state(
            browser,
            name="transactions-mobile-light-chat",
            path="/transactions?chat=open",
            view_id="transactions",
            width=390,
            scheme="light",
            check_diagram=False,
        )
        state_count += 1

        try:
            failures += capture_state(
                browser,
                name="overview-mobile-light-nav",
                path="/",
                view_id="overview",
                width=390,
                scheme="light",
                check_diagram=False,
                before_capture=open_nav_drawer,
            )
        except AssertionError as error:
            failures.append(f"overview-mobile-light-nav: {error}")
            print(f"  {'overview-mobile-light-nav':<28} FAIL  {error}")
        state_count += 1

        browser.close()

    if state_count != EXPECTED_STATES:
        failures.append(
            f"expected {EXPECTED_STATES} states, ran {state_count} -- "
            "a shrunken matrix is a failure even if every state printed is ok"
        )

    if failures:
        print("\nLayout problems:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"\nAll {state_count} states clean. Screenshots in {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
