# CASMI26 fingerprint models: exact V1 bundle and recovered training source

[Dataset V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v2/versions/1), id **12054715**. Public access and the existing **CC BY-NC-SA 4.0** label were verified on 18 October 2026. The suffix `v2` is a release name, not Kaggle's version number.

| File | Bytes | Selected step | SHA256 |
| --- | ---: | ---: | --- |
| `fp_single_s2.pt` | 144110255 | 20000 | `c19aa29016ed4d7a67bac38105b8fa5076c696c29eb66a504558c9b2e52b614a` |
| `fp_merged_m1.pt` | 144110255 | 24000 | `261529c823825cbe2028684bbf7214a95a7e631ca9f656336d577c507cce8294` |

The hashes were freshly checked on retained local copies and agree with earlier version-bound checkpoint observations; this audit did not download the current public payload again. Recorded architecture: **FPNet, 6,930 outputs, width 512, six layers**. These are not the newer 10,395-output, eight-layer full-fingerprint checkpoint. The 6,930 selected-bit order must be bound separately; shape equality is insufficient.

## Original source and commands

The release includes unchanged [FPNet](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/checkpoint_lineage/original_sources/fpmodel.py), [single-spectrum trainer](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/checkpoint_lineage/original_sources/train_fp3.py) and [merged-spectrum trainer](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/checkpoint_lineage/original_sources/train_fp4.py), recovered byte-for-byte from retained training notebook source. Preparation, data access and split auditing are documented in the [source release](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/README.md). Use the original preprocessing when investigating these weights; do not silently apply a later correction.

From `reproduction/legacy-v2/checkpoint_lineage/original_sources/`, set `CASMI_SPEC` to the qualified spectra/fingerprint export, `CASMI_POOL` to its matching candidate pool, and `CASMI_OUT` to your output directory. Use absolute paths for these three variables:

```bash
python -u train_fp3.py --spec "$CASMI_SPEC/spec.npz" --fpdir "$CASMI_SPEC" --pooldir "$CASMI_POOL" --steps 24000 --bs 256 --lr 2e-4 --K 63 --lam 1.0 --seed 202 --d 512 --layers 6 --val_every 2000 --max_minutes 300 --out "$CASMI_OUT/fp_model_s2.pt"
python -u train_fp4.py --spec "$CASMI_SPEC/spec.npz" --fpdir "$CASMI_SPEC" --pooldir "$CASMI_POOL" --steps 50000 --bs 256 --lr 2e-4 --K 63 --lam 1.0 --seed 404 --d 512 --layers 6 --merge_p 0.60 --val_every 2000 --max_minutes 420 --out "$CASMI_OUT/fp_model_m1.pt"
```

These are the recovered source recipes, not newly executed training runs. The configured maxima, 24,000 and 50,000 steps, differ from the selected checkpoint steps above. Selection uses stochastic hard-negative top-1 validation, not competition MRR@25. The model returns fingerprint logits, not calibrated molecule-identification probabilities.

## What is and is not reproducibly bound

The historical launchers attached unversioned spectra/pool inputs. Their exact training versions and runtime package versions remain unbound. The CLI seed is applied **after FPNet construction**, so it does not determine initial weights. The trainer saves optimizer state, while this small public bundle omits it; the historical export/rename transformation has not been proven. Original source is available, but a byte-exact source-to-published-weight reproduction is not established.

An optional [new deterministic training recipe](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/checkpoint_lineage/DETERMINISTIC_RECIPE.txt) seeds before initialization and requests deterministic kernels. It is source-reviewed but unexecuted, and is not the historical recipe or a promise to recover these weights. Compare runs at the same completed step budget; a wall-clock cutoff can stop them at different steps.

The merged trainer groups peers over all same-structure rows. The inspected local legacy cache (`99dbf966…4500`) contains 2,334,531 spectra and zero observed structures spanning both training and validation roles. That resolves the cross-role merge concern for those exact cache bytes; it does not prove that every historical checkpoint used those bytes or certify later evaluation isolation. Consult the preparation release's split audit and known limits. Do not advertise random candidate-row validation as molecule-disjoint evaluation.

## License and attribution

The existing CC BY-NC-SA label is retained for the uploader's contributed bundle. It does not relicense original training libraries, candidate structures or other third-party material. The hosts' [weight-sharing clarification](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/748882) requires original training code and lawful training-data access, including non-prize submissions. Publishing a checkpoint alone does not satisfy that requirement.

See [license scope](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/LICENSE-SCOPE.md), [attribution](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/ATTRIBUTION.md), the [Analog notebook](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) and [public development repository](https://github.com/cubres/enveda-casmi-2026). No new score or compliance certification is claimed by this card.
