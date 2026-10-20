# Public reproducibility audit: CASMI fingerprint and ranker assets

**Checked 20 October 2026.** Public source, preparation and split code, configured checkpoint commands, and scoped source-code licences are now findable. Exact historical checkpoint export, the FP-logit cache producer used in the published ranker features, and the combined ChEBI/LIPID MAPS ingestion lineage remain open. This is a source/provenance audit, not a retraining or model-quality result.

## Public dataset versions and current license labels

The anonymous Kaggle metadata and complete version-specific file listings checked for this audit identify:

| Asset | Kaggle data ID / version | Files and declared bytes | Kaggle metadata label |
|---|---:|---|---|
| [casmi26-fp-models-v2](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v2/versions/1) | 12054715 / 1 | fp_merged_m1.pt — 144,110,255; fp_single_s2.pt — 144,110,255 | CC BY-NC-SA 4.0 |
| [casmi26-ranker-features](https://www.kaggle.com/datasets/prvsiyan/casmi26-ranker-features/versions/6) | 12039490 / 6 | rank_train.npz — 9,553,020 | CC BY-NC-SA 4.0 |
| [chebi-lipidmaps-casmi26](https://www.kaggle.com/datasets/prvsiyan/chebi-lipidmaps-casmi26/versions/1) | 12051681 / 1 | bio_fp.npy — 54,399,176; bio_mass.npy — 502,080; bio_meta.pkl — 5,545,993 | CC BY-NC-SA 4.0 |

The three assets above are the released model, ranker-feature, and bio-fingerprint outputs. The prepared inputs used by the legacy 6,930-output trainers are also public:

| Prepared input asset | Version | Published files and declared bytes | Kaggle metadata label |
|---|---:|---|---|
| [casmi26-spec-fp](https://www.kaggle.com/datasets/prvsiyan/casmi26-spec-fp/versions/1) | 1 | spec.npz — 920,788,910; fp_sel.npy — 239,127,398; fp_bits.npy — 55,568; fp_meta.pkl — 17,095,875; split.pkl — 47,965 | Other (specified in description) |
| [casmi26-pool](https://www.kaggle.com/datasets/prvsiyan/casmi26-pool/versions/1) | 1 | pool_fp.npy — 617,048,363; pool_mass.npy — 5,693,768; pool_meta.pkl — 64,843,052 | Other (specified in description) |

The published `split.pkl` includes the retained legacy validation split. These releases make the prepared spectra, selected fingerprint metadata, and matching 6,930-bit pool available without access to the private trainer kernel. The full file hashes are listed on their versioned dataset pages; this audit checked public metadata and inventories, not downloaded payload bytes or hash equality.

[casmi26-full-fingerprint-inputs v1](https://www.kaggle.com/datasets/prvsiyan/casmi26-full-fingerprint-inputs/versions/1) is a distinct 10,395-bit, 711,705-candidate input bank with explicit training roles for the newer full-fingerprint workflow. It is not a replacement input for the legacy S2/M1 checkpoints or their 6,930-output trainers. Its Kaggle metadata also says “Other (specified in description).”

The listed datasets' own descriptions govern permitted reuse and source terms; “Other” is not a general-purpose open-data licence. The “v2” string in the first table is the fingerprint bundle's name; its Kaggle dataset version is 1.

## FP preparation and validation split

The public [preparation guide](https://github.com/cubres/enveda-casmi-2026/blob/f4b645acffa70809885eb14082fbe83af47a903d/reproduction/legacy-v2/public_source/README.txt) retains the original preparation source. In a new working directory, the published sequence is:

~~~bash
SOURCE=/absolute/release/public_source
WORK=/absolute/new/legacy-rebuild
cd "$WORK"
python "$SOURCE/build_fps.py"
python "$SOURCE/build_coconut.py"
python "$SOURCE/build_dataset.py"
python "$SOURCE/build_pool.py"
~~~

It writes ds/spec.npz, ds/split.pkl, up_train/fp_bits.npy, up_train/fp_sel.npy, up_train/fp_meta.pkl, pool_fp.npy, pool_mass.npy, and pool_meta.pkl. The matching prepared arrays are now published in the versioned `casmi26-spec-fp` and `casmi26-pool` assets above; `split.pkl` carries the retained structure-level validation assignment. The source files [build_fps.py](https://github.com/cubres/enveda-casmi-2026/blob/f4b645acffa70809885eb14082fbe83af47a903d/reproduction/legacy-v2/public_source/build_fps.py), [build_dataset.py](https://github.com/cubres/enveda-casmi-2026/blob/f4b645acffa70809885eb14082fbe83af47a903d/reproduction/legacy-v2/public_source/build_dataset.py), [build_coconut.py](https://github.com/cubres/enveda-casmi-2026/blob/f4b645acffa70809885eb14082fbe83af47a903d/reproduction/legacy-v2/public_source/build_coconut.py), and [build_pool.py](https://github.com/cubres/enveda-casmi-2026/blob/f4b645acffa70809885eb14082fbe83af47a903d/reproduction/legacy-v2/public_source/build_pool.py) are byte-preserved. Public availability closes the missing-prepared-files issue raised in the notebook comment. What remains unbound is the complete upstream input-version/checksum chain, exact environment/package lock, and a fresh payload hash comparison; no payload was downloaded or rehashed for this audit.

Source inspection records sorted eligible natural-product keys, forces all enveda-np-examples structures into validation, then samples up to 2,500 additional keys with NumPy default_rng(0). Every spectrum inherits the structure-level is_val value. Legacy bit selection uses frequency thresholds 0.005–0.995 over the legacy structure matrix, including validation structures; it is not the later optimizer-only 10,395-bit selection recipe. The public guide reports zero structure overlap between its retained legacy train and validation spectra, but that is not a fresh blind validation result. Original full-data preparation uses large arrays and ten workers; no full-run memory or time measurement is claimed.

## Checkpoint-specific trainers

The public [checkpoint binding record](https://github.com/cubres/enveda-casmi-2026/blob/f4b645acffa70809885eb14082fbe83af47a903d/reproduction/legacy-v2/checkpoint_lineage/PUBLIC_CHECKPOINT_BINDINGS.json) retains the configured commands and file bindings. The [single-spectrum trainer](https://github.com/cubres/enveda-casmi-2026/blob/f4b645acffa70809885eb14082fbe83af47a903d/reproduction/legacy-v2/checkpoint_lineage/original_sources/train_fp3.py) uses seed 202 and no merge_p option. The [merged-spectrum trainer](https://github.com/cubres/enveda-casmi-2026/blob/f4b645acffa70809885eb14082fbe83af47a903d/reproduction/legacy-v2/checkpoint_lineage/original_sources/train_fp4.py) uses seed 404 and merge_p 0.60 for training and validation. Both use FPNet with 6,930 outputs, width 512, six layers:

~~~bash
TRAINERS=/absolute/release/checkpoint_lineage/original_sources
python -u "$TRAINERS/train_fp3.py" --spec ds/spec.npz --fpdir up_train --pooldir . --steps 24000 --bs 256 --lr 2e-4 --K 63 --lam 1.0 --seed 202 --d 512 --layers 6 --val_every 2000 --max_minutes 300 --out fp_model_s2.pt
python -u "$TRAINERS/train_fp4.py" --spec ds/spec.npz --fpdir up_train --pooldir . --steps 50000 --bs 256 --lr 2e-4 --K 63 --lam 1.0 --seed 404 --d 512 --layers 6 --merge_p 0.60 --val_every 2000 --max_minutes 420 --out fp_model_m1.pt
~~~

The retained public checkpoints are recorded at selected steps 20,000 (S2) and 24,000 (M1), rather than configured limits 24,000 and 50,000. The record lists fp_single_s2.pt SHA-256 c19aa29016ed4d7a67bac38105b8fa5076c696c29eb66a504558c9b2e52b614a and fp_merged_m1.pt SHA-256 261529c823825cbe2028684bbf7214a95a7e631ca9f656336d577c507cce8294. It records that original trainer code calls torch.manual_seed after model construction, so byte-identical retraining is not promised. The source record binds checkpoint files to retained metadata, but the exact historical export chain, input dataset versions and runtime packages remain unresolved. These commands were read from source; this audit did not run them.

## Ranker builder and the FP columns

The recovered [make_ranker3.py](https://github.com/cubres/enveda-casmi-2026/blob/f4b645acffa70809885eb14082fbe83af47a903d/reproduction/legacy-v2/ranker_lineage/original_sources/make_ranker3.py) recipe, from a new prepared working directory, is:

~~~bash
RANK_SOURCE=/absolute/release/ranker_lineage/original_sources
python -u "$RANK_SOURCE/make_ranker3.py" --model
~~~

It needs pool_fp.npy, pool_mass.npy, pool_meta.pkl and query/analog/fragmentation caches, including data/val_model_logits_combo.npy (A: 250 × 6,930 raw FP logits) and data/hard_model_logits.npy (B: 569 × 6,930 raw FP logits). It writes up_rank3/rank_train.npz and data/w1_v3.pkl. This is not a complete historical rebuild command: the exact A-cache writer and B-cache producer are unresolved. If either FP cache is absent, the optional loader can silently return no model features and the corresponding twelve FP-derived columns become zeros.

The [31-feature order](https://github.com/cubres/enveda-casmi-2026/blob/f4b645acffa70809885eb14082fbe83af47a903d/reproduction/legacy-v2/ranker_lineage/FEATURE_COLUMNS.json) and source dependencies are public. The archived NPZ G array still lacks query/structure identity mapping, and no cache binds a checkpoint hash to its FP logits. The exact FPNet version and checkpoint that produced the historical published FP columns therefore remain unresolved. The retained archive is recorded as 142,762 × 31 with SHA-256 41ccec87fba5f8ab255aaf5a723567f25bd766064265c5cc2b83ba2cf15f57f8; this audit did not download or remeasure the NPZ. Historical validation also used query-index-modulo-five CV on a leaderboard-calibrated A cohort, not an independent blind evaluation.

## License boundaries

The Kaggle metadata labels above describe the three published assets. The public [LICENSE-SOURCE](https://github.com/cubres/enveda-casmi-2026/blob/3b1ba8eb9d064632f6aaed2283e6b7da958e1d1a/reproduction/legacy-v2/LICENSE-SOURCE), [NOTICE](https://github.com/cubres/enveda-casmi-2026/blob/3b1ba8eb9d064632f6aaed2283e6b7da958e1d1a/reproduction/legacy-v2/NOTICE), and [license scope](https://github.com/cubres/enveda-casmi-2026/blob/3b1ba8eb9d064632f6aaed2283e6b7da958e1d1a/reproduction/legacy-v2/LICENSE_SCOPE.md) grant Apache-2.0 to 29 enumerated owned source files, including the trainers, FPNet, ranker builder, and preparation code. That grant excludes weights, caches, datasets, dependencies, and other files.

Current upstream pages state that [ChEBI data](https://www.ebi.ac.uk/chebi/about/) and [LIPID MAPS databases](https://www.lipidmaps.org/terms-of-use) are CC BY 4.0. Those current terms do not identify the exact historical source snapshots used in the combined Kaggle dataset, nor replace its published CC BY-NC-SA 4.0 metadata label. Its original release dates/checksums, per-source row counts, and ingestion/deduplication producer remain unbound.

The separate [V465 source-binding audit](../../tools/casmi-public-notebook-audit/2026-10-20/README.md) has its own Apache-2.0 licence for audit_v465_public_binding.py only. Neither that script licence nor the legacy code grant changes any data, model, cache, notebook, or third-party terms.

## What is still needed for a complete reproduction

1. Bind the public preparation outputs to exact upstream input versions and checksums, pin the runtime, and independently download/hash the published spec, metadata, pool, and split artifacts.
2. Record the generator and FPNet/checkpoint SHA-256 for both FP-logit caches, and bind ranker G to its query and structure identities.
3. Reproduce and hash each checkpoint export, including the mapping from training output names to the public bundle filenames.
4. Publish a source-release manifest and rebuild recipe for the combined ChEBI/LIPID MAPS bank, subject to each source's terms.
5. Run the resulting recipe on an identity-disjoint validation protocol before making any score or generalization claim.

The report links existing public source rather than redistributing competition-derived input files or model payloads.