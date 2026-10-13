"""Deterministic synthetic mass-basis SVG, generated from the numerical API."""
import argparse
from html import escape
from pathlib import Path

from mass_basis_sensitivity import MassIndex, audit_basis


def render_svg():
    # Invented numerical example only; no molecular table or reference record.
    report = audit_basis(MassIndex([]), 201.0072764665789, "[M+2H]2+", 10., polarity="positive")
    labels = ("Neutral monomer mass", "Total ion mass", "Precursor m/z")
    formulas = ("M = S", "M = (S − h·p) / n", "M = (|z|·S − h·p) / n")
    width_rules = ("half-width = S·ppm / 10⁶", "half-width = S·ppm / (n·10⁶)", "half-width = |z|·S·ppm / (n·10⁶)")
    colors = ("#28795a", "#4577b4", "#93613d")
    cards = []
    for i, row in enumerate(report["hypotheses"]):
        x = 36 + 390 * i
        cards.append(f'<rect x="{x}" y="174" width="368" height="294" rx="18" fill="#ffffff" stroke="#dce4ec"/>')
        cards.append(f'<text x="{x + 24}" y="216" class="card" fill="{colors[i]}">{labels[i]}</text>')
        cards.append(f'<text x="{x + 24}" y="251" class="formula">{escape(formulas[i])}</text>')
        cards.append(f'<text x="{x + 24}" y="298" class="value">M = {row["center_da"]:.9f} Da</text>')
        cards.append(f'<text x="{x + 24}" y="334" class="small">Closed numerical window</text>')
        cards.append(f'<text x="{x + 24}" y="365" class="mono">{row["lower_da"]:.9f}</text>')
        cards.append(f'<text x="{x + 24}" y="391" class="mono">to {row["upper_da"]:.9f}</text>')
        cards.append(f'<text x="{x + 24}" y="433" class="tiny">{escape(width_rules[i])}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1220" height="770" viewBox="0 0 1220 770" role="img" aria-labelledby="title desc">
<title id="title">One scalar, three conditional mass windows</title>
<desc id="desc">Synthetic numerical example with scalar201.0072764665789, declared double-proton positive ion channel, and10ppm referenced to that scalar. Three possible interpretations yield different neutral monomer mass windows. The tool does not qualify the source mass basis or identify chemicals. A singly charged ion total mass and m/z can agree numerically; a dimer conversion refers to monomer mass.</desc>
<defs><style>text{{font-family:system-ui,sans-serif}} .title{{font-size:32px;font-weight:700;fill:#183046}} .card{{font-size:22px;font-weight:650}} .formula{{font-size:22px;fill:#1e3347}} .value{{font-size:22px;font-weight:650;fill:#1e3347}} .small{{font-size:17px;fill:#526777}} .tiny{{font-size:15px;fill:#526777}} .mono{{font-family:monospace;font-size:19px;fill:#1e3347}} .section{{font-size:20px;font-weight:650;fill:#1e3347}}</style></defs>
<rect width="1220" height="770" fill="#f2f6f8"/>
<text x="36" y="57" class="title">One scalar, three conditional mass windows</text>
<text x="36" y="94" class="small">Synthetic S = 201.0072764665789 · declared [M+2H]2+ · n = 1, h = 2, z = +2 · 10 ppm</text>
<rect x="36" y="116" width="391" height="34" rx="17" fill="#fff0cf"/>
<text x="55" y="139" class="small">Source mass basis remains UNQUALIFIED</text>
{''.join(cards)}
<rect x="36" y="491" width="1148" height="190" rx="18" fill="#ffffff" stroke="#dce4ec"/>
<text x="60" y="528" class="section">Charge and dimers change the conversion, not the evidence</text>
<text x="60" y="563" class="small">Charge 2: total ion mass = 2 × precursor m/z. The m/z window scales with |z|.</text>
<text x="60" y="596" class="small">Dimer [2M+H]+: M = (ion mass − p) / 2. The neutral interpretation always means monomer M.</text>
<text x="60" y="629" class="small">Charge 1: ion mass and m/z windows coincide. Agreement still cannot qualify the basis.</text>
<text x="60" y="659" class="tiny">Candidate counts refer to source positions; equal masses stay separate. Chemical identity remains unmeasured.</text>
<text x="36" y="712" class="tiny">PPM denominator is the supplied scalar under each assumed unit; no original reference records or models are used.</text>
<text x="36" y="741" class="tiny">Rounded display. JSON reports the implemented binary64 endpoints. Neutral windows do not screen ion feasibility.</text>
</svg>\n'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Fresh .svg path; existing files are preserved")
    args = parser.parse_args()
    path = Path(args.output)
    if path.suffix.lower() != ".svg":
        raise ValueError("use a fresh SVG output")
    with path.open("x", encoding="utf-8") as stream:
        stream.write(render_svg())


if __name__ == "__main__":
    main()
