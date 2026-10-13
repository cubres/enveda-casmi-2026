# A reproducible mass-window lookup for COCONUT CASMI26 V2

The [COCONUT 2.0 candidates + fingerprints (CASMI26)](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates) bank supports mass-window candidate retrieval and fingerprint-based ranking. The companion lookup is original numerical code; it reads no spectra, molecular structures, pickle metadata or model weights.

The retained V2 evidence records **436,389 candidate mass rows**. Use the bank to retrieve plausible natural-product candidates by neutral monoisotopic mass, then join the same original row indices to fingerprints and separately justified molecular identifiers. A mass hit is a candidate, not an identification.

```text
measured precursor + explicitly chosen adduct
                    |
             neutral mass in Da
                    |
           inclusive ppm window
                    |
          ORIGINAL candidate indices
           /                    \
packed fingerprint rows     independently justified IDs
           |                    |
exact model bit-order join   exact candidate row-order join
           \                    /
            candidate evidence
```

## The exact retained V2 numerical contract

| File | Retained contract | Evidence scope |
|---|---|---|
| `coco_mass.npy` | `(436389,)`, float64, finite and ascending | Complete small-array check on 7 October 2026 |
| `coco_fp.npy` | `(436389, 867)`, uint8 | Binary header only; complete fingerprint correctness unverified |
| `fp_bits.npy` | `(6930,)`, int64, unique indices; minimum 2, maximum 10405 | Complete small-array check on 7 October 2026 |
| `coco_meta.pkl` | 41,450,156-byte historical pickle | Optional; the numerical quickstart never opens it |

The measured mass range in that retained receipt is **100.009519128–1299.7599298120003 Da**. The retained 4 October text inventory records 436,389 unique keys and unique SMILES strings, without chemical parsing. These checks do not prove that every fingerprint row belongs to its declared molecule.

Each packed row contains 6,930 selected bits and six padding bits. The documented producer vector is Morgan radius 2 with 4096 bits, Morgan radius 3 with 4096 bits, RDKit path fingerprint with 2048 bits and `maxPath=6`, then MACCS with 167 bits: **10,407 columns before selection**. `fp_bits.npy` selects from that full vector. It must not be applied again to the already selected 6,930-column decode. NumPy decoding uses `bitorder='big'`.

Keep mass, fingerprint and identifier rows in their original order. Sorting only the masses, joining on row count, or pairing a model with a different bit map can yield plausible numerical results for the wrong candidates.

## Forkable numerical quickstart

Place the companion `coconut_lookup.py` beside your code, and attach the existing V2 dataset. NumPy is the only external dependency. No RDKit installation is needed for this lookup; the tool does not generate fingerprints or canonicalize molecules.

```python
from coconut_lookup import load_v2

bank = load_v2('/kaggle/input/coconut-casmi26-candidates')
# Illustrative neutral mass, already converted from precursor/adduct.
rows = bank.window(300.0, ppm=10.0, max_rows=4096)
selected_fp = bank.decode(rows)
print('row indices:', rows, 'selected bits:', selected_fp.shape)
```

An empty window stays empty; the tool never widens it automatically. Endpoints are inclusive, equal-mass rows are retained, and a window over 4096 rows is rejected. Only selected rows are decoded. At the maximum cap the unpacking intermediate has 28,409,856 uint8 entries; the selected 6,930-column view has 28,385,280 entries. Additional indexing arrays and copies consume memory too. This is array-size arithmetic, not a measured runtime or peak-memory result.

`load_v2` verifies the retained mass/selection hashes and matrix headers. It memory-maps the packed matrix, rejects object-array loading, and never reads `coco_meta.pkl`. The six discarded padding bits are checked on the selected rows. The large fingerprint file is not fully hashed or chemically validated by this helper.

Before attaching a model, check its declared descriptor families and exact ordered selection with `assert_model_columns(bank.bits, model_bits, model_descriptor_order)`. Before joining identifiers from different sources, use `assert_row_join(candidate_row_ids, fingerprint_row_ids)` with independently justified IDs. The latter rejects duplicate and reordered supplied IDs; it cannot certify that a producer assigned those IDs correctly. RDKit version, normalization, source snapshot and model provenance still require their own pins.

## Related plain-array work and compatibility

The user-linked [Morgan/MACCS dataset](https://www.kaggle.com/datasets/aryanawasthiteykik/casmi26-coconut-morgan-maccs-fingerprints) and [spectrum-to-fingerprint MLP model dataset](https://www.kaggle.com/datasets/aryanawasthiteykik/casmi26-spectrum-to-fingerprint-mlp) are worth comparing for portable data access. Their descriptions in the request mention a 436k bank, Morgan 2048 plus MACCS and Parquet/NumPy. The exact user-provided fingerprint-dataset URL could not be retrieved in the earlier public reads. On 13 October 2026, a separate public read of the exact user-provided MLP model-dataset URL above also returned inaccessible, with no page content. Their precise row count, bit layout, files, generation recipe and terms remain unverified here.

A Morgan 2048/MACCS output cannot be substituted into this bank merely because both resources have about 436k rows. Establish molecule identifiers and row order first; then establish fingerprint families, parameters, normalization, producer version, selection order and packing. This companion includes no implementation or weights from either linked resource and no chemical tables.

## Provenance and limits

Credit [COCONUT](https://coconut.naturalproducts.net/) and the [existing Analog Propagation baseline](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline). The retained 9 October Kaggle metadata recorded **CC BY 4.0**; that is historical evidence. The canonical [dataset card](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates), read in full by the coordinator on 13 October 2026, displayed a [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) license link. This discrepancy remains recorded; this companion changes no dataset license, and the full current-card evidence and component rights still require a concrete join before updating its description.

COCONUT's current [About](https://coconut.naturalproducts.net/about) page describes curated downloadable data as CC0 and infrastructure code as MIT, while its [license documentation](https://steinbeck-lab.github.io/coconut/license.html) labels repository data CC BY 4.0 and its [terms](https://coconut.naturalproducts.net/terms-of-service) retain source-specific rights. These pages do not establish the historical bank's exact snapshot or relicense attached models, restricted training structures or the linked author's assets. The MIT notice covers only this original companion's code, documentation and diagram.

The original COCONUT snapshot date, complete generation manifest, producer RDKit version and row-level source tags are not established by the retained evidence. Today's upstream download date cannot fill those historical gaps. This proposal redistributes no structures, training data or weights; unresolved component rights stay unresolved.

The bank is limited to its retained natural-product candidates and mass range. Wrong adduct interpretation, absent chemistry or changed normalization can exclude the correct identity. Similar fingerprints do not uniquely identify stereochemistry. Candidate reachability and ranking should be evaluated separately on an independently eligible panel.

The small-file pins, dated contract and invented-data controls accompany this proposal. No current vote total, medal, runtime improvement or new competition score is claimed. For the broader reproduction contract, see the [public baseline guide at its exact commit](https://github.com/cubres/enveda-casmi-2026/blob/77c93ead4e4f8d4452d60f962a009abc9787c2bb/frontier/public-baseline-replication-2026-10-13.md).
