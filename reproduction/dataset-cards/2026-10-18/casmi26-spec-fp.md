# CASMI26 spectra tensors and selected fingerprints: preparation and rights boundary

[Dataset V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-spec-fp/versions/1), id **12036447**, was **private** on 18 October 2026. Its metadata currently says CC0 and its description is empty. This draft documents the inputs; it does not make them public or establish that the CC0 label is appropriate.

| File | Current V1 listed bytes | Role |
| --- | ---: | --- |
| `spec.npz` | 920788910 | Flattened spectrum tensors and row/split indices |
| `fp_sel.npy` | 239127398 | Packed selected structure fingerprints |
| `fp_bits.npy` | 55568 | Ordered 6,930-bit selection vector |
| `fp_meta.pkl` | 17095875 | Structure mapping and fingerprint metadata |
| `split.pkl` | 47965 | Retained structure-role selection |

This is the legacy selected-bit input, not the 10,395-bit full target bank. The retained trainer consumes `off,mz,it,prec,ad,ins,ce,mode,six,is_val` from `spec.npz`. Current file listings do not prove their content, original training-file version or alignment.

## Preparation source

The [source release](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/README.md) provides original `speclib.py`, `fpmodel.py`, `build_fps.py`, `build_coconut.py`, `build_dataset.py` and `build_pool.py`. The explicit flat-cache/selected-bit export helper is a **new reconstruction** of missing standalone writers; it is not presented as a recovered historical exporter.

Stage the files from `reproduction/legacy-v2/public_source/` in a new working directory, as described in its [preparation recipe](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/public_source/README.txt). After obtaining legally accessible `data/train.parquet` and the qualified historical COCONUT CSV at `db/coconut/coconut_csv-09-2026.csv`, the source-shaped command chain is:

```bash
python prepare_legacy_exports.py flat --train data/train.parquet --output data
python build_fps.py
python build_coconut.py
python build_dataset.py
python prepare_legacy_exports.py selected --data data --output up_train
python build_pool.py
```

The original scripts use this fixed working-directory layout. `build_dataset.py` writes `ds/spec.npz` and `ds/split.pkl`; the selected exporter writes `up_train/fp_bits.npy`, `up_train/fp_sel.npy` and `up_train/fp_meta.pkl`; `build_pool.py` writes the matching pool files. A packaging step must preserve these bytes and record their hashes. The command chain has not been run on real competition data in this repair. It does not prove byte-identical reconstruction of current V1.

## Split and model bindings

The original preparation assigns validation by structure membership: Enveda natural-product examples are forced into validation, with up to 2,500 additional eligible structures sampled using NumPy seed 0. The source sorts eligible keys before sampling; exact filtering inputs, COCONUT membership and runtime still need binding. The inspected local cache has SHA256 `99dbf966d2607e2da8085a6550206a71fc912d2c90b9555a725a2569e4af4500`: 2,334,531 spectra, 273,983 observed structures and **zero structures spanning both roles**. This is evidence about those exact current cache bytes, not a historical build attestation or proof that every checkpoint used them.

The invented preparation demo checks the forced split and serialization; its eligible random-sampling pool is empty. It does not verify reproduction of nonempty stochastic split selection.

The legacy bit-frequency selection uses all prepared structures, rather than an optimizer-only role. Do not describe this selection as holdout-fitted. For the two six-layer, 6,930-output FPNet checkpoints, see the exact [S2/M1 training commands and limitations](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/casmi26-fp-models-v2.md). The merged trainer can use all rows sharing a structure; verify role consistency before using that behavior as an isolation claim.

## License correction before sharing

Competition-derived spectra are not made public-domain by assigning CC0 to a private tensor archive. The host's [training-data clarification](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/745072) permits qualifying artifacts from the open training compilation but does not waive every contributor's rights. The public release must state the applicable source terms and uploader-owned contribution scope, and correct unsupported metadata before changing visibility. No hidden test data belongs in this release.

Use [LICENSE-SCOPE.md](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/LICENSE-SCOPE.md) and [ATTRIBUTION.md](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/ATTRIBUTION.md). Public data access, lawful redistribution and original-training reproducibility are separate requirements. This draft grants no new license over third-party spectra and makes no performance claim.
