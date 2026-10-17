# CASMI26 prepared training spectra and selected fingerprints

This V1 dataset supplies the prepared inputs for the original 6,930-output FPNet training recipe: 2,334,531 spectra, 275,810 structure fingerprint rows, the exact selected fingerprint columns and the saved legacy split. It contains provided CASMI training-derived records and transformations. It contains no competition test data or model checkpoints.

[Exact dataset V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-spec-fp/versions/1) · [Original preparation and training source](https://github.com/cubres/enveda-casmi-2026/tree/main/reproduction/legacy-v2) · [Existing competition notebook](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline)

## Files and integrity

The file hashes below identify the actual existing V1 payload. Four files were acquired through the official version-bound API and matched to retained files on 18 October 2026; the mounted `spec.npz` hash was observed in the exact native run's input receipt. This metadata update does not replace or regenerate those files.

| File | Bytes | Use |
| --- | ---: | --- |
| `spec.npz` | 920,788,910 | Prepared ragged spectra, metadata, source-row and structure indices, legacy `is_val` |
| `fp_sel.npy` | 239,127,398 | Packed `uint8[275810,867]` selected fingerprints |
| `fp_bits.npy` | 55,568 | Ordered `int64[6930]` indices into the original 10,407-bit fingerprint |
| `fp_meta.pkl` | 17,095,875 | Ordered train structure keys and SMILES, `nbits=6930` |
| `split.pkl` | 47,965 | Exact saved `VAL` and `forced` training-structure keys |

After downloading V1 to a fresh directory, this standard-library check verifies its exact files without loading pickle contents:

```python
from pathlib import Path
import hashlib
root = Path("/path/to/casmi26-spec-fp-v1")
expected = {
    'spec.npz': (920788910, '99dbf966d2607e2da8085a6550206a71fc912d2c90b9555a725a2569e4af4500'),
    'fp_sel.npy': (239127398, 'f7cb256a8351f9defd82e54b3eb4d8abdfa6a50beadc34e15214827e8ef6466f'),
    'fp_bits.npy': (55568, 'a61e372fc41091bf5c7467e08134081266262665077cb9e2c56d73e4887f3013'),
    'fp_meta.pkl': (17095875, 'd6ad0dd33bf66e92c5a85054b7f914b4ac538fc4b06c4aabca8d0df9f985b85b'),
    'split.pkl': (47965, '25e00a31cd8acfdd97e0dd40e9a43aa257fefabd74416a0813f4710f62aa4b1e'),
}
for name, (size, digest) in expected.items():
    path = root / name
    assert path.is_file() and path.stat().st_size == size, name
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    assert h.hexdigest() == digest, name
print("All five V1 files match")
```

`spec.npz` has eleven numeric arrays: `off:int64`, `mz,it,prec,ce,mode:float32`, `ad:int16`, `ins:int8`, `six:int32`, `is_val:bool`, and `src:int64`. `off` has 2,334,532 entries; `mz` and `it` each have 104,592,893 entries; the other arrays have one entry per spectrum. `six` indexes the ordered structure metadata and `src` indexes the retained original train file. These are actual data arrays, not aggregate statistics.

## Use the supplied preparation with the original trainers

The exact [S2/M1 training commands](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/casmi26-fp-models-v2.md) and original `train_fp3.py`/`train_fp4.py` are public. Stage these prepared files in a new working directory as `ds/spec.npz`, `ds/split.pkl` and `up_train/{fp_meta.pkl,fp_sel.npy,fp_bits.npy}`. Preserve original source filenames and imports as described in the [source index](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/README.md).

The original trainers also require the matching [6,930-bit candidate pool V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-pool/versions/1): `pool_fp.npy`, `pool_mass.npy` and `pool_meta.pkl`. That is a separate dataset and access must be available before these commands can run. The 10,395-bit full fingerprint bank cannot substitute for it. The trainer consumes `is_val` directly; it does not read `split.pkl`, so reproducing the historical split-generation process is unnecessary when consuming these exact prepared bytes.

For a new preparation from authorized raw inputs, the [complete preparation recipe](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/public_source/README.txt) uses the original builders plus an explicitly labelled reconstructed flat-cache/selected-export bridge. Start with an external immutable training file and a fresh output directory:

```bash
python prepare_legacy_exports.py flat --train /absolute/authorized/train.parquet --output data
ln -s /absolute/authorized/train.parquet data/train.parquet
python build_fps.py
python build_coconut.py
python build_dataset.py
python prepare_legacy_exports.py selected --data data --output up_train
python build_pool.py
```

Place the qualified COCONUT CSV at the exact path required by that recipe before running its builder. This command chain documents source reconstruction; it is not a claim that the complete historical build was rerun in this release.

## Provenance and checks

All 2,334,531 prepared source-row indices and their structure joins were checked against the retained provided training compilation. All 275,810 metadata key/SMILES pairs match training structures. All selected packed fingerprint rows and all 6,930 selected column indices match the retained original fingerprint matrix and its frequency selection. Thirty-two fixed, evenly spaced structure fingerprints were independently recomputed with RDKit 2026.03.3 and matched exactly.

The original split forces eligible Enveda natural-product examples into validation and samples up to 2,500 other eligible training structures with NumPy seed 0 after sorting eligible keys. Cleaned COCONUT membership influences eligibility; these five payloads do not add novel COCONUT candidate structures or spectra. Every saved split identifier belongs to the training metadata, and the saved validation membership matches every `is_val` entry. The exact cache has 273,983 structures observed among its spectra and zero structures spanning both legacy roles.

The original selected-bit frequency filter uses all retained training structures, not an optimizer-only population. All peak values were not recomputed in the bounded release audit; the checks above establish the stated lineage and alignment. No separately supplied NIST input is read by these preparation sources and no retained ingest-library name contains `nist`; this name check is not an independent audit of every underlying library record.

The original trainers seed Torch after model initialization. Exact supplied inputs, code and commands make training inspectable and runnable once all dependencies are accessible, but do not promise byte-identical reproduction of historical S2/M1 checkpoint weights or resolve the separate historical ranker-cache producer question. No leaderboard score is claimed for this dataset.

## License and attribution — Other (specified in description)

This is a compilation of transformed records from the competition-provided training data. The competition hosts' [training-data clarification](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/745072) permits qualifying artifacts derived from that open training compilation; the competition noncommercial provision was intended for test data. This release relies on that permission for the provided-train-derived artifacts. It does not apply a blanket CC0 dedication or grant new rights over every constituent source.

Original library contributors retain their respective rights and applicable source terms. Consult the [competition training data](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/data) for source attribution and conditions, and preserve those notices when redistributing relevant material. The uploader's contributions here are preparation, numeric array organization, derived fingerprints, selected-column metadata and legacy split assignments; those contributions do not relicense the underlying spectra or molecular records. They are provided for reproducing this CASMI workflow within the host-permitted training-artifact scope. Software licenses on the published builders apply to software, not automatically to third-party data.

COCONUT contributes membership information to the split recipe; credit its [original authors and CC0 dataset](https://coconut.naturalproducts.net/about). The separate candidate pool contains additional COCONUT structures and has its own provenance notice. See the campaign [component attribution](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/ATTRIBUTION.md) and [license-scope notice](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/LICENSE-SCOPE.md). Neither the dataset label nor publication waives contributor rights, permits proprietary source redistribution or includes hidden test data.
