# Attach a negative only after qualifying the positive

The runnable example is a reference consumer, not a training job:

```sh
python3 -B source/sample_curriculum.py --run-root completed --anchor 0 --stage 2 --epoch 0
```

Run from the package root. The release worker did not execute it. The copied
consumer checks the qualified owning result, completion, source and all file
hashes before sampling. Anchor 0 has one train-fold candidate,192, in the
actual CSV; `anchor0_frozen_rows.json` contains those exact read rows.

In a separately licensed training pipeline:

1. Qualify the positive spectrum's structure and source-provided InChIKey
   first block. Join to `anchors.csv` and the exact selected FP row in the
   immutable ChEBI release. Audit aliases/external duplicates too.
2. Keep all spectra of a connectivity inside that reference fold. Use only
   train anchors for optimizer steps; validation/test recipes stay held.
3. Choose stage 0, 1 or 2 at your own training milestones. Call the deterministic
   train-only sampler with anchor/stage/epoch. Skip an empty pool.
4. Retrieve the positive and candidate targets from the pinned source release;
   the exported row IDs, source IDs and FP digests make the join auditable.

No positive spectra, permissive spectrum license, optimizer/loss choice or
proof of spectral distinguishability is supplied here. Removing equal-target
contrasts does not remove every possible spectral false negative.

Public inputs are pinned in `source/INPUT_CONTRACT.json`: atlas commit
8f2fd96360ddeb878053bc89298401657fe3e25d and clean structure commit
9cb4a4a6bc9ce2e97ce7dfcbaca1419bbb5bbb34. Download only exact pinned paths and
verify lengths/SHA256 before a fresh reproduction. A public portable owner is
not yet qualified; the historical ROOT owner is not a public launcher. Do not
disable its guards or substitute a direct unowned builder call.
