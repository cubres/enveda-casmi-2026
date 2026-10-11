# Provenance and publication boundary

This directory contains original adapter code, original tests, an original bounded diagnostic reader and an original schematic. They are released under the included MIT license. No top-scorer source, checkpoint, predicted spectrum, candidate table or competition data is redistributed here.

## Frozen original sources

Before the private diagnostic's new label-value reads, the final source pins were:

| File | SHA256 |
|---|---|
| `charged_ion_adapter.py` | `0ff785544ea07d741cf888202d20cb3a823608f3f7f78a09f3cee353e137c7ad` |
| `test_charged_ion_adapter.py` | `490b2e487cd927664bdeedc105e685067599ec7aaaf5bef59e82b08819d00d62` |
| `run_development_diagnostic.py` | `c75581e25002687e4017829b89df40400d437ac2edf9ea6cfac322cb137b814e` |

The final pre-label seal was retained at 2026-10-11 17:57:46 UTC. It follows an amendment that fixed the diagnostic geometry to absolute 0.01 Da/zero ppm and explicitly marked the owned stable-tie cleaner as changed preprocessing. A further before-label amendment required a caller-established same-query token before metadata grouping. The private diagnostic then ran once, starting at 18:00:57 UTC and exiting successfully at 18:01:02 UTC. These retained author execution observations bound the reported new label-read interval; they are not independently authenticated proof of historical access. The saved panel already had prior aggregate/selection/fitting exposure.

The private protocol, exact input pins, source inspections, schema-only receipt, stdout, execution receipt and competition-derived results are retained outside the public allowlist. Numeric development outcomes are not reproduced in this directory. An independent reviewer checked source contracts, metric arithmetic and retained result/receipt consistency without repeating the data run or authenticating historical access chronology.

## Operational chemistry conventions

The adapter preserves operational monoisotopic constants from the existing account-owned precursor-index implementation, inspected read-only at SHA256 `21ca1560d9820b1c7288c5d1e2e21380df6c2d5d5d58704c4f04d3f28e20dc76`. The prototype is an independent rewrite with stricter annotation/family gates, not a claim that these are the latest metrological values. In particular, its proton convention is neutral-H minus electron mass. Keep those operational values fixed when seeking native numerical parity; a standards update would be a separately registered intervention.

The neutral precursor inversion is `(abs_charge * precursor_mz - adduct_shift) / multiplicity`. Fragment ion families are separately chosen, singly charged hypotheses. The small H-shift bank is explicitly not a chemical valence/atom-balance proof. The code does not infer a fragment's exact chemical formula or support general arbitrary charge states.

The inspected account-owned cleaning source SHA256 was `3448096df103657f5bf366c72c69a2c81b434d8891a7ded3e4e5ac78d5037c46`; the feature contract source SHA256 was `716e01b30f55ad89780d433dd81c683037bf60e759e710756a0b40f28c830c86`. Those sources were not executed or redistributed. Stable Python top-k ties and precision differ from the native NumPy implementation unless a future comparison proves parity. Original independent peak matching used fixed 0.01 Da; this diagnostic holds ppm at zero.

## Component licenses and data rights

The adapter and its controls use the Python standard library. The optional private reader imports NumPy and PyArrow. NumPy's primary [license page](https://numpy.org/doc/stable/license.html) provides its three-clause BSD terms. Apache Arrow's primary [license file](https://raw.githubusercontent.com/apache/arrow/main/LICENSE.txt) starts with Apache License 2.0 and includes notices for bundled components. Those library distributions keep their own licenses and notices; their code/binaries are not bundled into this packet. No RDKit, restricted spectral library, model checkpoint or notebook code is loaded.

The diagnostic inputs are saved participant competition training spectra and a previously exposed derived numerical rank table. Their local accessibility permits this authorized private inspection; it does not grant public redistribution. The reader selects nine input fields and supplies no declared acquisition bounds. A separately retained schema-only receipt confirms that the inspected training schema has no fields named `acquisition_mz_min` or `acquisition_mz_max`; acquisition records elsewhere were not inspected. It never infers an acquisition window from measured peak extrema.

Public transport includes only the explicitly allowlisted original UTF-8 files. It excludes raw/derived spectra, structures, compound/query identifiers, private paths, dataset source lists, candidate rows, model weights, probabilities, private results and receipts. The MIT release of this code does not change the rights of any input data or third-party component.

## Scientific scope

The adapter's control tests verify stated conversions, holds, grouping and cleaning behavior. The saved-data run measures metadata availability, potential peak-interval overlap and existing feature-only ranks on exposed development data. It does not measure the new matching algorithm's ranking effect, actual predicted-ion reuse, a fitted ranker improvement or hidden-test transfer. It has no native execution, competition submission or official score.
