# SPDX-License-Identifier: MIT
"""Generate only an original SVG from the saved invented-control output."""
from html import escape
import json
from pathlib import Path


def render(results):
    pair = results["duplicate_centroids"]["per_view"][0]
    accidental = results["single_accidental_view"]
    med = accidental["features"][1]
    dense = results["dense_hypotheses"]["per_view"][0]
    bars = [
        ("Independent peak credit", pair["independent_explain"], "#c06b50"),
        ("One-to-one credit", pair["assignment"], "#295d68"),
        ("One accidental view: max", accidental["features"][0], "#c06b50"),
        ("Three views: median", med, "#295d68"),
        ("Dense ion bank: coverage", dense["uniform_mass_coverage"], "#c06b50"),
        ("Dense ion bank: excess", dense["uniform_excess"], "#295d68"),
    ]
    items = []
    for i, (label, value, color) in enumerate(bars):
        y = 305 + i*53
        items.append(
            f'<text x="65" y="{y}" fill="#2b3640" font-size="17">{escape(label)}</text>'
            f'<rect x="380" y="{y-18}" width="360" height="22" rx="4" fill="#e4e7e1"/>'
            f'<rect x="380" y="{y-18}" width="{360*value:.6f}" height="22" rx="4" fill="{color}"/>'
            f'<text x="766" y="{y}" fill="#2b3640" font-size="17">{value:.4f}</text>'
        )
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="800" viewBox="0 0 1100 800">
<rect width="1100" height="800" fill="#f6f4eb"/>
<g font-family="Arial, sans-serif">
<text x="65" y="65" font-size="31" font-weight="bold" fill="#233844">Fragment evidence across spectra</text>
<text x="65" y="102" font-size="18" fill="#62716c">Original numerical prototype • all displayed spectra are invented</text>
<rect x="65" y="140" width="260" height="105" rx="12" fill="#e4e7e1"/>
<rect x="420" y="140" width="260" height="105" rx="12" fill="#d7e5e2"/>
<rect x="775" y="140" width="260" height="105" rx="12" fill="#e5ded1"/>
<text x="90" y="175" font-size="19" font-weight="bold" fill="#233844">Compatible ion hypotheses</text>
<text x="90" y="205" font-size="16" fill="#233844">Centroids + declared window</text>
<text x="90" y="228" font-size="16" fill="#233844">No structures or weights</text>
<text x="445" y="175" font-size="19" font-weight="bold" fill="#233844">Exact weighted assignment</text>
<text x="445" y="205" font-size="16" fill="#233844">One ion / one observed peak</text>
<text x="445" y="228" font-size="16" fill="#233844">Density diagnostic per view</text>
<text x="800" y="175" font-size="19" font-weight="bold" fill="#233844">Nine extra ranker features</text>
<text x="800" y="205" font-size="16" fill="#233844">Max, median, lower tail</text>
<text x="800" y="228" font-size="16" fill="#233844">Independent holdout next</text>
<path d="M340 194 L397 194 M386 184 L397 194 L386 204 M695 194 L752 194 M741 184 L752 194 L741 204" stroke="#62716c" stroke-width="3" fill="none"/>
''' + "\n".join(items) + '''
<text x="65" y="675" font-size="18" font-weight="bold" fill="#233844">These bars illustrate failure modes, not predictive accuracy.</text>
<text x="65" y="710" font-size="16" fill="#62716c">No competition data, model fitting, native execution, or official submission.</text>
<text x="65" y="740" font-size="16" fill="#62716c">One CPU timing: 786,432 DP cells / 0.159041 CPU s. Native runtime remains unverified.</text>
<text x="65" y="775" font-size="14" fill="#62716c">Source: synthetic_results.json • original diagram and code MIT licence</text>
</g></svg>
'''


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    result = json.loads((base/"synthetic_results.json").read_text())
    with (base/"fragment-consensus.svg").open("x", encoding="utf-8") as file:
        file.write(render(result))

