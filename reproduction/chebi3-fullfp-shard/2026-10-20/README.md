# CASMI: source-linked ChEBI fingerprint shard

![Verified ChEBI fingerprint pipeline](assets/pipeline.png)

Reproducible producer code and a small retrieval demo for 4,096 public ChEBI
three-star structures. Each record has source identifiers, SMILES, neutral mass,
a packed 10,395-bit fingerprint and an explicit source-row join. This contains
no newly trained model or verified leaderboard gain.

The exact data artifacts and hashes are described by `DATASET_FILES_MANIFEST.json`.
The source collections are public: [ChEBI + LIPID MAPS V1](https://www.kaggle.com/datasets/sergiomalv/casmi-chebi-lmsd-structures/versions/1)
and [full-fingerprint inputs V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-full-fingerprint-inputs/versions/1).
`producer/PUBLIC_SOURCE_BINDINGS.json` pins the fingerprint definition, mask and
metric/group helpers. See `producer/README.md` for the recorded Mac CPU producer
and `verification/` for the numerical proof and its limits. In this data release,
the data files are included beside this source. The earlier source-only commit
[`917f833d77e8ffc7b2ce6b8a28d8dc823f40a272`](https://github.com/cubres/enveda-casmi-2026/commit/917f833d77e8ffc7b2ce6b8a28d8dc823f40a272)
does not contain those binary files; use a later reviewed data commit or current
`main` after the data release, and record the exact commit used.

Clone into a new folder and run the portable demo with NumPy and PyArrow:

~~~sh
git clone https://github.com/cubres/enveda-casmi-2026.git enveda-casmi-2026-data-demo
cd enveda-casmi-2026-data-demo
git rev-parse HEAD
git merge-base --is-ancestor 917f833d77e8ffc7b2ce6b8a28d8dc823f40a272 HEAD
cd reproduction/chebi3-fullfp-shard/2026-10-20
python -m pip install -r requirements-demo.txt
python -B -m unittest -v test_demo_mass_window.py
python demo_mass_window.py --data-dir . --limit 3
~~~

The demo dependencies are NumPy **2.2.6** and PyArrow **25.0.0**, with recorded
Python runtime **3.12.14**. It needs neither RDKit nor psutil. The numerical
producer's separate runtime uses RDKit **2026.03.3**. Confirm the six consumer
files are present: `external_fp.npy`, `external_mass.npy`, `mass_order.npy`,
`external_chebi3_4096.parquet`, `original_source_rows.npy` and `fp_bits.npy`.

Omitting `--mass` uses the first dataset row as an explicitly illustrative query.
For a user-chosen neutral monoisotopic mass, use
`python demo_mass_window.py --data-dir . --mass 300 --ppm 10 --limit 10`.
An empty window is valid; this does not convert precursor m/z or adducts.
The demo performs read-only neutral-mass-window lookup and reports source rows
and on-bit counts; it does not rank spectra, use labels or call RDKit or a model.
The supplied synthetic tests cover its retrieval and schema checks.

All 4,096 raw keys and exact SMILES are absent from the older 711,705-row bank.
They form 4,092 canonical groups within this shard. Canonical novelty versus the
entire old bank, official-metric novelty, hidden-answer coverage and score
improvement remain unmeasured.

Molecular records retain CC BY 4.0 attribution; the frozen training-derived mask
has separate component terms. Code uses Apache 2.0. Read `DATA-LICENSE.md` and
preserve `SOURCE_ATTRIBUTION.md`; the mixed bundle has per-component terms.

The Kaggle copy is pending. Dataset creation and upload have not been attempted
for this release; the reviewed GitHub data release is a separate delivery.
