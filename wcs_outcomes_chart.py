import pandas as pd
import re
from pathlib import Path
import plotly.graph_objects as go

# Paths are relative to this script, so the tool needs nothing outside its own
# folder (matches the other build scripts; the previous absolute path pointed
# at a folder that no longer exists).
HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "cpd_data.csv"

df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

# Filter to rows where WCS is in Charges
wcs = df[df["Charges"].str.contains("WCS", na=False)].copy()


def extract_year(row):
    for field in ["Hearing Date", "Effective date of termination"]:
        m = re.search(r"(20[12]\d)", str(row.get(field, "")))
        if m:
            return int(m.group(1))
    link = str(row.get("Link to original report", ""))
    m = re.match(r"(\d{2})-", link)
    if m:
        return 2000 + int(m.group(1))
    return None


wcs["year"] = wcs.apply(extract_year, axis=1)
wcs = wcs[wcs["year"].notna()].copy()
wcs["year"] = wcs["year"].astype(int)

# Exclude 2026 (in-progress year, only 6 records)
wcs = wcs[wcs["year"] <= 2025]

# Categorize outcome by most severe component
SEVERITY = [
    ("Termination", ["termination"]),
    ("Separation", ["separation"]),
    ("Demotion", ["demotion"]),
    ("Suspension", ["suspension"]),
    ("Written Reprimand", ["written reprimand", "written warning"]),
    ("Verbal Warning", ["verbal warning", "verbal counseling"]),
    ("Non-Disciplinary Reinstruction", ["non-disciplinary letter of reinstruction"]),
    ("Charges Dismissed", ["dismissal"]),
]

COLORS = {
    "Termination": "#c0392b",
    "Separation": "#e67e22",
    "Demotion": "#8e44ad",
    "Suspension": "#2980b9",
    "Written Reprimand": "#16a085",
    "Verbal Warning": "#27ae60",
    "Non-Disciplinary Reinstruction": "#95a5a6",
    "Charges Dismissed": "#bdc3c7",
}


def categorize(decision_type):
    dt = str(decision_type).lower()
    for label, keywords in SEVERITY:
        if any(kw in dt for kw in keywords):
            return label
    return "Other"


wcs["outcome_category"] = wcs["Decision type"].apply(categorize)

# --- Chart 1: Stacked bar count by year ---
pivot = (
    wcs.groupby(["year", "outcome_category"])
    .size()
    .reset_index(name="count")
    .pivot(index="year", columns="outcome_category", values="count")
    .fillna(0)
)

# Order columns by severity
ordered_cols = [label for label, _ in SEVERITY if label in pivot.columns]
if "Other" in pivot.columns:
    ordered_cols.append("Other")
pivot = pivot[ordered_cols]

years = pivot.index.tolist()

# --- Chart 2: 100% stacked (proportion) ---
pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100

fig = go.Figure()

for col in ordered_cols:
    color = COLORS.get(col, "#7f8c8d")
    fig.add_trace(
        go.Bar(
            name=col,
            x=years,
            y=pivot[col].tolist(),
            marker_color=color,
            hovertemplate=f"<b>{col}</b><br>Year: %{{x}}<br>Count: %{{y}}<extra></extra>",
        )
    )

fig.update_layout(
    barmode="stack",
    title=dict(
        text="How WCS Charge Outcomes Have Changed Over Time<br><sup>Cleveland Division of Police disciplinary records</sup>",
        font=dict(size=18),
    ),
    legend=dict(
        title="Outcome",
        traceorder="normal",
        font=dict(size=12),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#ccc",
        borderwidth=1,
    ),
    plot_bgcolor="white",
    paper_bgcolor="white",
    height=500,
    hovermode="x unified",
    yaxis=dict(title="Number of Cases", gridcolor="#eee"),
    xaxis=dict(tickmode="linear", dtick=1, tickangle=-30, gridcolor="#eee"),
)

# NOTE: this is the early plotly PROTOTYPE of the chart, kept for reference. The
# published chart is the hand-built, Signal-styled wcs_outcomes.html (its data
# comes from build_data.py) — so this writes to its own filename rather than
# overwriting it.
out_path = HERE / "wcs_outcomes_plotly_prototype.html"
fig.write_html(out_path, include_plotlyjs="cdn")
print(f"Saved: {out_path}")

# Companion data export (same pivot, plus a Total column) kept in step with the
# chart so it can't drift from it.
counts_path = HERE / "wcs_outcomes_by_year.csv"
export = pivot.astype(int)
export["Total"] = export.sum(axis=1)
export.to_csv(counts_path, index_label="year")
print(f"Saved: {counts_path}")

# Print summary table
print("\nOutcome counts by year:")
print(pivot.to_string())
print("\nOutcome proportions (%) by year:")
print(pivot_pct.round(1).to_string())
