# SPDX-License-Identifier: MIT
"""Create the original static contract diagram; no measured science plot."""
import argparse
from pathlib import Path

SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="820" viewBox="0 0 1280 820">
<defs><style>text{font-family:Arial,sans-serif;fill:#17304c}.title{font-size:36px;font-weight:700}.sub{font-size:20px;fill:#587088}.card{fill:white;stroke:#d9e4ec;stroke-width:2}.heading{font-size:24px;font-weight:700}.body{font-size:20px}.small{font-size:17px;fill:#587088}.num{font-size:24px;font-weight:700}.arrow{stroke:#66829a;stroke-width:3;fill:none}</style>
<marker id="tip" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="#66829a"/></marker></defs>
<rect width="1280" height="820" fill="#f3f7fa"/>
<text x="64" y="70" class="title">Change the intended slots. Keep the whole panel.</text>
<text x="64" y="110" class="sub">A source-bound audit of an intervention, illustrated with invented records.</text>
<rect x="64" y="155" width="550" height="235" rx="20" class="card"/>
<text x="92" y="197" class="heading">01  Freeze membership before inference</text>
<text x="92" y="234" class="body">All 16 predetermined groups stay in view.</text>
<text x="92" y="266" class="body">Keep absent and no-candidate outcomes.</text>
<text x="92" y="299" class="small">Panel hash + query hashes + exact order</text>
<g fill="#2e8094"><rect x="92" y="325" width="22" height="22" rx="5"/><rect x="122" y="325" width="22" height="22" rx="5"/><rect x="152" y="325" width="22" height="22" rx="5"/><rect x="182" y="325" width="22" height="22" rx="5"/></g>
<g fill="#d3e1e9"><rect x="212" y="325" width="22" height="22" rx="5"/><rect x="242" y="325" width="22" height="22" rx="5"/><rect x="272" y="325" width="22" height="22" rx="5"/><rect x="302" y="325" width="22" height="22" rx="5"/><rect x="332" y="325" width="22" height="22" rx="5"/><rect x="362" y="325" width="22" height="22" rx="5"/><rect x="392" y="325" width="22" height="22" rx="5"/><rect x="422" y="325" width="22" height="22" rx="5"/><rect x="452" y="325" width="22" height="22" rx="5"/><rect x="482" y="325" width="22" height="22" rx="5"/><rect x="512" y="325" width="22" height="22" rx="5"/><rect x="542" y="325" width="22" height="22" rx="5"/></g>
<text x="92" y="374" class="small">Color denotes sequence, not a measured outcome.</text>
<rect x="666" y="155" width="550" height="235" rx="20" class="card"/>
<text x="694" y="197" class="heading">02  Join the same candidates and scores</text>
<text x="694" y="234" class="body">Complete permutations; same source hash.</text>
<text x="694" y="266" class="body">Bind each pair to its captured query.</text>
<text x="694" y="307" class="small">Optional scalar responses add head alignment</text>
<text x="694" y="335" class="small">and finite-evidence checks.</text>
<path d="M628 270H650" class="arrow" marker-end="url(#tip)"/>
<rect x="64" y="432" width="550" height="235" rx="20" class="card"/>
<text x="92" y="474" class="heading">03  Protect every slot outside the mask</text>
<text x="92" y="511" class="small">Illustrative candidate ordinals, not chemical identities</text>
<g><rect x="104" y="532" width="74" height="46" rx="9" fill="#aedbe2"/><rect x="205" y="532" width="74" height="46" rx="9" fill="#e1e8ef"/><rect x="306" y="532" width="74" height="46" rx="9" fill="#aedbe2"/><rect x="407" y="532" width="74" height="46" rx="9" fill="#e1e8ef"/>
<text x="134" y="564" class="num">0</text><text x="235" y="564" class="num">1</text><text x="336" y="564" class="num">2</text><text x="437" y="564" class="num">3</text>
<rect x="104" y="604" width="74" height="46" rx="9" fill="#aedbe2"/><rect x="205" y="604" width="74" height="46" rx="9" fill="#e1e8ef"/><rect x="306" y="604" width="74" height="46" rx="9" fill="#aedbe2"/><rect x="407" y="604" width="74" height="46" rx="9" fill="#e1e8ef"/>
<text x="134" y="636" class="num">2</text><text x="235" y="636" class="num">1</text><text x="336" y="636" class="num">0</text><text x="437" y="636" class="num">3</text></g>
<path d="M242 581V596M444 581V596" class="arrow" marker-end="url(#tip)"/>
<rect x="666" y="432" width="550" height="235" rx="20" class="card"/>
<text x="694" y="474" class="heading">04  Report only what the records prove</text>
<text x="694" y="515" class="body">Count main-pair structural changes.</text>
<text x="694" y="551" class="body">Separate auxiliary and unmeasured evidence.</text>
<text x="694" y="593" class="small">Correctness, final control, hidden transfer and</text>
<text x="694" y="622" class="small">official scores require separate evidence.</text>
<path d="M628 550H650" class="arrow" marker-end="url(#tip)"/>
<rect x="64" y="710" width="1152" height="66" rx="14" fill="#17304c"/>
<text x="92" y="751" style="fill:white;font-size:22px">Invented example: 16 fixed groups · 1 main pair · 15 absent pairs · 2 allowed slots changed</text>
</svg>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("fixed-panel-audit.svg"))
    args = parser.parse_args()
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(SVG)


if __name__ == "__main__":
    main()
