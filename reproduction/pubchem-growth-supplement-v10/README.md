# PubChem growth supplement V10: input binding and evaluation plan

This note records the **public publisher-manifest claims** for the growth supplement in [CASMI26 PubChem Popularity Prior](https://www.kaggle.com/datasets/dmitriigluzdov/casmi26-pubchem-popularity-prior), Kaggle dataset version 10. It does not include the dataset payload or grant rights to reuse it.

## What the supplement adds

The version-10 data card describes 11,177 structures absent from the existing PubChem tier and its earlier supplement. The rows come from a dated public PubChem Compound Extras snapshot. Its manifest reports 11,176 distinct metric identities and 11,139 identities novel under the competition scorer's identity mapping. Thirteen rows differ between the official raw InChIKey-14 and the RDKit-derived key, so recompute identities with the competition scorer before deciding whether a candidate is new.

All `growth_*` arrays and `growth_pubchem_tier.csv` are aligned to one common row order; the arrays are mass sorted. Keep that order intact when building candidate windows. The growth rows are a separate supplement from the 105,875,489-row base tier and the 36,303-row earlier delta. Report candidate recall separately from ranking quality.

The manifest says depositor source groups were not measured for these rows. A zero `*_src_observed` value means source membership is unknown, not that the structure has no depositor.

## Publisher-manifest fingerprints

These sizes and SHA-256 digests were copied from the expanded public `GROWTH_MANIFEST.json` preview. They have **not** been independently rehashed from downloaded payloads.

| File | Bytes | SHA-256 |
|---|---:|---|
| `growth_pc_cid.npy` | 44,836 | `dd182e3b29c435b4a8b6f8db9af271a26bd895d04dbe2f63c60e9c7a403eb4cf` |
| `growth_pc_ik14.npy` | 156,606 | `4b5cc955bd472bf4b6f79111382f08da2b2e13d0955fd9f7ae7861df636f6867` |
| `growth_pc_lotus_refs.npy` | 44,836 | `c36054e30c5762a76287242dd6905fe673f8998be356c2c10b4dfd2525d65d07` |
| `growth_pc_lpmid.npy` | 22,482 | `6087f448d23c830d71b507f0d37d2fa03e8a7edb439fc4f11cac2c6dc296272f` |
| `growth_pc_lsid.npy` | 22,482 | `b61869798298ec8bc909263a58f5025830f599ec8488d16ef4f94b5625a40e6b` |
| `growth_pc_lsynonyms.npy` | 22,482 | `82104705a06d5296d8fb14a6daa786e47fe193359b0fc881d7f32d439f0105da` |
| `growth_pc_mass.npy` | 89,544 | `ca46c1c72932c1cc6b58ab9bcb833a2125281f20c0b623af9fa30b182561ef1b` |
| `growth_pc_np.npy` | 11,305 | `0247d671abeee3d605859f4f95b6d9876fca22539136039ece9c7f73c0ba6464` |
| `growth_pc_off.npy` | 89,552 | `07ba3dc94264691e8a74912aa85c9e64415a4511d41e58055de36fdda34cce5e` |
| `growth_pc_smiles.npy` | 559,296 | `578590187454a7b01d3af9f994ab7cd148041a8fcab913bffa44a99909167ab4` |
| `growth_pc_src_mask.npy` | 22,482 | `9723906a530f498a678018ae5ea4c616690aaf6f435f2bbd9f588594b3676ea8` |
| `growth_pc_src_observed.npy` | 11,305 | `befe16f61edd8b2d9bb0947026c01b52f01763b6641b0ba402d13dd44a0ca3f5` |
| `growth_pubchem_tier.csv` | 2,040,254 | `c1f25947913aa809e63888ba66b635e02a42082a5beba8cf46ec99cd1de162f3` |

The manifest's `payload_bytes=3,511,140` is larger than these 13 growth-file sizes (3,137,462 bytes). Five visible delta-array entries explain most, but not all, of the difference. Treat this as a broader package aggregate until its composition is independently verified.

## Runnable integrity check

Attach Kaggle dataset version 10 as an input before running this cell. It verifies the publisher-declared size and SHA-256 for each growth file, then checks the row count of every NumPy array and the mass ordering. It reads only the 11,177-row supplement. This example has **not** been run against the mounted payload, so it does not upgrade the copied manifest hashes to independent verification.

```python
import hashlib
import json
from pathlib import Path

import numpy as np

roots = [
    Path("/kaggle/input/datasets/dmitriigluzdov/casmi26-pubchem-popularity-prior"),
    Path("/kaggle/input/casmi26-pubchem-popularity-prior"),
]
data = next(p for p in roots if (p / "GROWTH_MANIFEST.json").is_file())
manifest = json.loads((data / "GROWTH_MANIFEST.json").read_text())
files = manifest["files"]
names = sorted(
    name for name in files
    if name.startswith("growth_pc_") and name.endswith(".npy")
)
names.append("growth_pubchem_tier.csv")
assert len(names) == 13

for name in names:
    path = data / name
    expected = files[name]
    assert path.stat().st_size == expected["bytes"], name
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    assert digest.hexdigest() == expected["sha256"], name
    if name.endswith(".npy"):
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        assert array.shape[0] == manifest["rows"], name
        if name == "growth_pc_mass.npy":
            assert np.all(array[1:] >= array[:-1]), "mass order"

print(f"PASS: {len(names)} V10 growth files; {manifest['rows']} aligned rows")
```

The proposed score test comes after integrity and identity checks:

```mermaid
flowchart LR
    A[Pinned V10 input] --> B[Verify bytes and row alignment]
    B --> C[Mass-window candidate lookup]
    C --> D[Competition-identity deduplication]
    D --> E[Identity/scaffold holdout]
    E --> F[Candidate recall@K]
    E --> G[MRR@25]
```

This diagram describes a proposed evaluation workflow, not a completed experiment.

## Integration gate

Before using the supplement, pin dataset version 10 in the Kaggle notebook's input configuration, verify all listed file hashes and row counts at the mounted root, and record runtime/tool versions. Use identity/scaffold-heldout known-answer cases to compare incremental candidate recall and MRR against the already-used base tier plus earlier delta. Recompute scorer identities, preserve aligned row order, and keep the candidate-generation and ranking effects separate. CID dates are a compound creation-date proxy, not evidence of source deposition time.

The active CASMI V43 scoring run must reach a terminal state before any new CASMI compute starts. No score gain is claimed for this untested supplement.

## Rights

Kaggle labels the dataset license “Other (specified in description).” The card notes PubChem public-domain information subject to NLM and source-specific terms, LOTUS annotations under CC BY 4.0, and NPAtlas under CC BY-NC 4.0; other structural-asset and competition-derived terms still apply. This note does not relicense any input or establish prize eligibility. Follow the current source terms and competition rules before redistribution or use.
