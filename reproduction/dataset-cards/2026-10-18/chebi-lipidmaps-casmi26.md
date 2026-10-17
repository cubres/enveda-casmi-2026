# ChEBI + LIPID MAPS candidate bank: schema and source scope

[Dataset V1](https://www.kaggle.com/datasets/prvsiyan/chebi-lipidmaps-casmi26/versions/1), id **12051681**. Anonymous public access, V1 and the existing **CC BY-NC-SA 4.0** metadata label were verified on 18 October 2026.

| File | Recorded contract |
| --- | --- |
| `bio_mass.npy` | 62,744 ascending neutral masses, float64; 502080 bytes |
| `bio_fp.npy` | `(62744, 867)` uint8; 6,930 selected fingerprint bits and six trailing padding bits; 54399176 bytes |
| `bio_meta.pkl` | 5545993 bytes; companion keys/SMILES metadata, historically used through pickle |

This is a candidate-structure bank, not a query spectral library or a submission. Schema details above are retained observations; this audit refreshed metadata, not every payload byte. Neutral mass is not precursor m/z. Preserve row alignment across all files when filtering or sorting.

## License correction

The current [ChEBI notice](https://www.ebi.ac.uk/chebi/about/) and [LIPID MAPS terms](https://www.lipidmaps.org/terms-of-use) both identify **CC BY 4.0** for their databases. The old card's inference that fingerprint-checkpoint training makes all candidate structures noncommercial/share-alike is not justified. A checkpoint license does not automatically attach to independently obtained candidate records.

The uploader's existing NC-SA selection is retained for any uploader-owned original contribution. It does not revoke the rights available in original ChEBI or LIPID MAPS material. Historical raw download releases, checksums and per-source row provenance are not established by today's terms pages or by the combined bank's name. See [LICENSE-SCOPE.md](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/LICENSE-SCOPE.md).

## Rebuilding and checking

An exact historical download-and-build command cannot yet be supplied: the original raw-source snapshot and combined-bank producer are not bound. Do not label a fresh current-database build as reproduction of these V1 bytes. A qualified rebuild must record both raw releases/checksums, source IDs, standardization and deduplication rules, neutral-mass calculation, RDKit version, exact ordered selected-bit vector and a shared stable row sort. It should export metadata as a non-pickle table with per-row source membership.

The original [fingerprint source](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/public_source/build_fps.py) documents the descriptor family construction, but it alone does not reconstruct this bank's missing historical ingestion. The [fingerprint contract tool](https://github.com/cubres/enveda-casmi-2026/blob/main/tools/fingerprint-contract/README.md) offers runnable invented 6,930/10,395-bit fixtures and a byte/order/padding checker. A checker pass is not chemical provenance or checkpoint-compatibility proof.

For a numeric neutral-mass window on an already qualified download:

```python
import numpy as np
mass = np.load("bio_mass.npy", mmap_mode="r", allow_pickle=False)
lo, hi = np.searchsorted(mass, [299.997, 300.003])
packed = np.load("bio_fp.npy", mmap_mode="r", allow_pickle=False)
bits = np.unpackbits(packed[lo:hi], axis=1, bitorder="big")[:, :6930]
print(bits.shape)  # illustrative 300-Da neutral-mass window, not accuracy evidence
```

Credit ChEBI/EMBL-EBI and LIPID MAPS using their source identifiers and [citation guidance](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/ATTRIBUTION.md). No score gain, newly qualified historical build or blanket relicensing is claimed.
