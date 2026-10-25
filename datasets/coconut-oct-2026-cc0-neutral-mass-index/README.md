# COCONUT October 2026 CC0 Mass and Structure Index

Published on Kaggle: [COCONUT Oct 2026 CC0 Mass and Structure Index](https://www.kaggle.com/datasets/prvsiyan/coconut-oct-2026-cc0-neutral-mass-index).

This is a source-only structure and mass lookup index for CASMI research. It does not contain competition spectra, labels, scorer keys, training features, model output, or leaderboard results.

## Contents

- `candidate_records.parquet`: 738,794 COCONUT rows in original CSV order, with selected source fields and RDKit-derived structure, formula, charge, and status fields.
- `neutral_mass_da.npy`: sorted RDKit exact masses for 728,033 neutral structures.
- `neutral_source_row.npy`: positions that map sorted mass rows back to `candidate_records.parquet`.
- `ion_mz.npy`: ten sorted theoretical ion channels, shape `(10, 728033)`. Channel order is in `adducts.csv`.
- `adducts.csv`: channel names, formulas, signed charge, calculated mass offsets, and index positions.
- `MANIFEST.json`, `RELEASE_FILES.json`, and `validate_formula_compositions.py`: provenance and integrity checks.

The ten ion channels follow the official CASMI test-adduct order: `[M+H]+`, `[M+NH4]+`, `[M-H2O+H]+`, `[M-2H2O+H]+`, `[M+Na]+`, `[M+K]+`, `[M-H]-`, `[M-H2O-H]-`, `[M+CH2O2-H]-`, `[M+Cl]-`. They are theoretical lookup channels, not observed adduct labels.

## Query example

Each `ion_mz` channel is sorted. `neutral_source_row.npy` maps every index entry to a row in the Parquet table. The example uses inclusive ppm boundaries.

```python
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

root = "/kaggle/input/coconut-oct-2026-cc0-neutral-mass-index"
ions = np.load(root + "/ion_mz.npy", mmap_mode="r", allow_pickle=False)
source_rows = np.load(root + "/neutral_source_row.npy", mmap_mode="r", allow_pickle=False)

channel = ions[0]  # adducts.csv channel 0: [M+H]+
center, ppm = 433.1493, 10.0
half_width = center * ppm * 1e-6
lo = np.searchsorted(channel, center - half_width, side="left")
hi = np.searchsorted(channel, center + half_width, side="right")

records = pq.read_table(root + "/candidate_records.parquet")
hits = records.take(pa.array(source_rows[lo:hi]))
print(hits.select(["coconut_id", "identifier", "rdkit_canonical_smiles"]))
```

Filter to positive m/z for a physically meaningful precursor window. A small number of structures produce nonpositive theoretical m/z in water-loss channels.

## Provenance and limits

COCONUT's official [October 2026 download page](https://coconut.naturalproducts.net/download) labels the data CC0. The source archive SHA-256 is `a602502a4fa0950cc2e59eed690dccd082d1a051bf9f85ccda50a82dd22ca154`; the source CSV SHA-256 is `fcdbf564b90d8a09e29b94b61250f3fe0d4332cb6f9f9ce45c3e829567b3b873`. RDKit 2026.03.3 derives the normalized structures and masses. NIST isotope values and 2022 CODATA proton/electron masses define the ion offsets. See `SOURCES.md` and `MANIFEST.json`.

Four source SMILES do not parse with RDKit. Their source records remain in Parquet and are not in the numeric index. Formula composition checks found 100 differences: 98 charged/non-neutral rows and two neutral rows. Formula agreement is not structure identity. Thirteen of fifteen vanadium-containing records show a larger source-versus-RDKit mass difference; the source isotope convention is unverified.

All 12 local release-file hashes and five data-artifact hashes matched before upload. Kaggle lists the same 12 files and byte sizes. A downloaded `adducts.csv` matches its local SHA-256 exactly. The dataset has no measured or claimed leaderboard gain.
