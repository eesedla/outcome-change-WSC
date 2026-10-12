#!/usr/bin/env python3
"""
Regenerate the DATA array in wcs_outcomes.html from cpd_data.csv.

Scope: cases whose Charges include a WCS (body camera) charge, counted per
year by DISCIPLINE OUTCOME.

Conventions are this chart's own, and differ from the sibling charts on two
points — both deliberate, both preserved here:

  * ONE category per case, the MOST SEVERE component of its Decision type
    (SEVERITY below, ordered high -> low). The "outcome per year" chart instead
    counts a case once per outcome it touches; this one is a severity profile,
    so its segments sum to exactly that year's case total.
  * Display labels fold three raw tokens: "separation" -> Resignation,
    "dismissal" -> Charge Dropped, and Verbal Warning -> Reinstruction (a
    single 2023 case, too small to warrant its own stack segment).

Years: 2017-2025, matching the sibling charts — 2016 (Oct-Dec only) and 2026
(partial) are excluded as partial edge years.

NOTE: wcs_outcomes_chart.py in this folder is the early plotly prototype of
this chart, not its build step. This script is the build step.

Run:  python3 build_data.py
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

HERE       = Path(__file__).resolve().parent
CSV_PATH   = HERE / "cpd_data.csv"
CHART_HTML = HERE / "wcs_outcomes.html"

YEAR_MIN, YEAR_MAX = 2017, 2025

# High -> low. First match on a case's Decision type wins.
SEVERITY = [
    ("Termination",       ["termination"]),
    ("Resignation",       ["separation", "resignation"]),
    ("Demotion",          ["demotion"]),
    ("Suspension",        ["suspension"]),
    ("Written Reprimand", ["written reprimand", "written warning"]),
    ("Reinstruction",     ["non-disciplinary letter of reinstruction",
                           "verbal warning", "verbal counseling"]),
    ("Charge Dropped",    ["dismissal"]),
]

# Column order written into each DATA row (the stack order itself lives in
# CATEGORIES in the HTML), with the digit width each value is padded to so the
# regenerated rows stay column-aligned the way they were written by hand.
COLUMNS = [("Termination", 1), ("Resignation", 1), ("Demotion", 1),
           ("Suspension", 2), ("Written Reprimand", 2), ("Reinstruction", 2),
           ("Charge Dropped", 1)]

ID_PAT = re.compile(r"^\s*(\d{2})-\d+")


def year_of(row):
    """Year for a case: Hearing Date, else Effective date of termination,
    else the YY- prefix of the report ID (e.g. 17-126 -> 2017)."""
    for col in ("Hearing Date", "Effective date of termination"):
        m = re.search(r"(20\d\d)", (row.get(col) or "").strip())
        if m:
            return int(m.group(1))
    p = ID_PAT.match(row.get("Link to original report") or "")
    return 2000 + int(p.group(1)) if p else None


def categorize(decision_type):
    dt = (decision_type or "").lower()
    for label, keywords in SEVERITY:
        if any(kw in dt for kw in keywords):
            return label
    return None


year_counts = defaultdict(lambda: defaultdict(int))
year_total  = defaultdict(int)
uncategorized = defaultdict(int)

with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        if "wcs" not in (row.get("Charges") or "").lower():
            continue
        year = year_of(row)
        if year is None or not (YEAR_MIN <= year <= YEAR_MAX):
            continue
        cat = categorize(row.get("Decision type"))
        if cat is None:
            uncategorized[(row.get("Decision type") or "").strip()] += 1
            continue
        year_counts[year][cat] += 1
        year_total[year] += 1

# ── Write back into wcs_outcomes.html ────────────────────────────────────────

lines = []
for y in sorted(year_counts):
    cells = ""
    for i, (col, width) in enumerate(COLUMNS):
        val = str(year_counts[y][col])
        cells += f'"{col}": {val}'
        if i < len(COLUMNS) - 1:
            cells += "," + " " * (width - len(val) + 1)
    lines.append(f"      {{ year: {y}, {cells} }},")
data_js = "const DATA = [\n" + "\n".join(lines) + "\n    ];"

raw = CHART_HTML.read_text(encoding="utf-8")
new_raw, n = re.subn(r"const DATA = \[.*?\];", data_js, raw, count=1, flags=re.DOTALL)
if n == 0:
    raise RuntimeError("Could not find 'const DATA = [...];' in wcs_outcomes.html")

changed = new_raw != raw
CHART_HTML.write_text(new_raw, encoding="utf-8")

total = sum(year_total.values())
print(f"{'Updated' if changed else 'No change to'} {CHART_HTML.name} — "
      f"{total} WCS cases across {len(year_counts)} years.")
peak = max(year_total, key=lambda y: year_total[y])
for y in sorted(year_total):
    print(f"  {y}: {year_total[y]} cases")
print(f"Peak year: {peak} ({year_total[peak]} cases). "
      f"Max stack total = {max(year_total.values())} (check MAX_Y in the HTML).")
if uncategorized:
    print("\nUNCATEGORIZED Decision type values (excluded — add to SEVERITY):")
    for d, c in sorted(uncategorized.items(), key=lambda x: -x[1]):
        print(f"  [{c:4d}x]  {d!r}")
