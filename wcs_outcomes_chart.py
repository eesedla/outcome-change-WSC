import pandas as pd
import re
import plotly.graph_objects as go

df = pd.read_csv(
    "/Users/emmasedlak/Library/Mobile Documents/com~apple~CloudDocs/Signal Freelance/CPD Analysis/outcome changes/cpd_data.csv",
    encoding="utf-8-sig",
)

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

out_path = "/Users/emmasedlak/Library/Mobile Documents/com~apple~CloudDocs/Signal Freelance/CPD Analysis/outcome changes/wcs_outcomes.html"
fig.write_html(out_path, include_plotlyjs="cdn")
print(f"Saved: {out_path}")

# Print summary table
print("\nOutcome counts by year:")
print(pivot.to_string())
print("\nOutcome proportions (%) by year:")
print(pivot_pct.round(1).to_string())
