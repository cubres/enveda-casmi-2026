# V43 and the PubChem growth supplement

**Observed 20 October 2026. Read-only source and data-card audit; no inference, output/log inspection, submission, or new score claim.**

## What V43 currently uses

The public [Analog Propagation – CASMI 2026 baseline, version 43](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline?scriptVersionId=360497306) is bound to a 35-cell source snapshot with SHA-256 `f254dfbca64c0b332049860d1f6c1dd5f67a80fdaee7e78b8f63597cdf8f57b1`. Its retained push receipt records version 43 and `cells_identical: true`.

A source-only scan of all 35 cell sources found references to the base arrays `pc_lsid.npy`, `pc_lpmid.npy`, `pc_mass.npy`, `pc_off.npy`, and `pc_smiles.npy`. It found no references to `growth_pc_*`, `delta_pc_*`, `GROWTH_MANIFEST`, or `growth_pubchem`. The notebook therefore does not visibly consume the new growth store. The notebook metadata names the popularity dataset slug but does not pin a dataset version, so the currently visible input version cannot establish which data revision the V43 run mounted.

## What the public V10 manifest says

The current [PubChem popularity dataset card](https://www.kaggle.com/datasets/dmitriigluzdov/casmi26-pubchem-popularity-prior/data?select=GROWTH_MANIFEST.json) displays dataset version 10. Its new supplement has 11,177 rows, 11,176 distinct metric identities, and 11,139 publisher-reported “scorer-novel” identities. The manifest does not define the comparator behind that novelty count, and its payload was not independently downloaded or rehashed in this audit. It also reports 13 differences between the source’s official connectivity/CID mapping and an RDKit-derived mapping.

The linked [`GROWTH_README.md`](https://www.kaggle.com/datasets/dmitriigluzdov/casmi26-pubchem-popularity-prior/data?select=GROWTH_README.md) says the rows have official connectivity blocks absent from the original tier plus the V4 delta; alternate PubChem strings for represented connectivities are excluded. `growth_pc_*` is a separate mass-sorted store, so its arrays must retain a common row order. The supplement’s depositor/source masks were not measured: zero is unknown membership, not evidence that a source is absent. The dataset card also retains the component terms for PubChem, COCONUT, LOTUS, and NPAtlas data; this audit does not treat the package as blanket CC0 or Apache-2.0.

The [competition rules](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/rules) allow external data that is public, equally accessible, and free, and specify non-commercial use for competition data. Those provisions do not erase external component terms or make the V10 “scorer-novel” count a validated coverage gain. Recheck source rights before redistributing data or relying on a component in a winning submission.

## Next test, gated on V43 becoming terminal

First bind the exact mounted version and every growth-file hash, verify shapes and offset/string alignment, resolve the 13 identity discrepancies, and finish the component-rights check. If those gates pass, run one CPU-only retrieval canary over 64 hash-selected, identity-held-out training groups. Freeze the split and candidate retrieval before joining labels. Compare the pinned base tier plus V4 delta against that same pool with the growth store added, using only observed precursor/adduct mass windows. Report incremental mass-window recall and candidate counts over all selected groups, including misses. Do not call this MRR or leaderboard evidence. Continue to the full frozen split only if alignment, provenance, coverage, and runtime checks pass; consider a ranking experiment only if the supplement contributes actual new held-out answers.

```mermaid
flowchart LR
  A[V43 finishes] --> B[Bind exact V10 payload and rights]
  B --> C{Alignment and identity checks pass?}
  C -- no --> H[Hold; record the gap]
  C -- yes --> D[64 fixed identity-held-out groups]
  D --> E[Mass-window recall: base plus V4 delta]
  D --> F[Mass-window recall: base plus V4 delta plus growth]
  E --> G{New held-out answers and budget pass?}
  F --> G
  G -- no --> H
  G -- yes --> I[Full frozen recall audit, then separate ranking test]
```

Until those gates pass, the supplement is an untested retrieval opportunity, not a score improvement. V43 remains the only active CASMI scoring job observed in the native submissions page during this audit.
