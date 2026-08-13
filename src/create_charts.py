import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)
SUMMARY = json.loads((ROOT / "results" / "summary.json").read_text())


def bar_chart(path, title, subtitle, labels, values, color, value_format=lambda x: f"{x:,.0f}"):
    width, height = 1200, 650
    left, top, chart_w, chart_h = 150, 120, 950, 400
    maximum = max(values) * 1.12
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#FAFAF7"/>',
             f'<text x="{left}" y="50" font-family="Arial" font-size="30" font-weight="700" fill="#17324D">{title}</text>',
             f'<text x="{left}" y="82" font-family="Arial" font-size="16" fill="#52616B">{subtitle}</text>']
    gap = chart_w / len(values); bar_w = gap * .58
    for i, (label, value) in enumerate(zip(labels, values)):
        x = left + i * gap + (gap - bar_w) / 2
        bar_h = chart_h * value / maximum; y = top + chart_h - bar_h
        parts += [f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" rx="4" fill="{color}"/>',
                  f'<text x="{x+bar_w/2}" y="{y-10}" text-anchor="middle" font-family="Arial" font-size="14" font-weight="700">{value_format(value)}</text>',
                  f'<text x="{x+bar_w/2}" y="{top+chart_h+28}" text-anchor="middle" font-family="Arial" font-size="14">{label}</text>']
    parts.append('</svg>')
    path.write_text("\n".join(parts))


borough = SUMMARY["borough_counts"][:-1]
bar_chart(ASSETS / "requests_by_borough.svg", "NYC 311 requests by borough",
          "24,684 requests created January 1–2, 2025; source: NYC Open Data",
          [x[0].title().replace("Staten Island", "Staten I.") for x in borough], [x[1] for x in borough], "#007C91")

with (ROOT / "data" / "processed" / "agency_performance.csv").open() as handle:
    agencies = list(csv.DictReader(handle))[:8]
bar_chart(ASSETS / "agency_median_closure.svg", "Median closure time by agency",
          "Top eight agencies by request volume; calculated from valid nonnegative durations",
          [x["agency"] for x in agencies], [float(x["median_closure_hours"]) for x in agencies], "#E06C3B",
          lambda x: f"{x:.1f}h")
print("created 2 SVG charts")
