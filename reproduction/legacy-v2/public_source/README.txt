CASMI legacy 6930-bit preparation and training source

This release supplies the original preparation, FPNet, trainers and 31-column ranker builder, plus two clearly marked reconstructed export steps. No historical training or ranking assay was rerun to prepare this release. The retained checkpoint bytes and source recipes are bound separately; the launch commands alone do not prove which run produced a particular checkpoint.

Quick, small validation
-----------------------
Install the versions in requirements-demo.txt into a new environment, then run:
  python demo_preparation_synthetic.py --output /absolute/new/toy-workspace
The demo uses four invented spectra and four invented fingerprint rows. It checks early float32 conversion of BOTH m/z and intensity, preprocessing, sorted structure split statements, a saved/reloaded cache, selected-bit order and padding. It imports no Torch, runs no model and accesses no competition records. SYNTHETIC_PREPARATION_RESULT.json records the completed ten-check validation. This is not a full-data cache/checkpoint reproduction result.

Original versus reconstructed files
-----------------------------------
Original byte-preserved: speclib.py, fpmodel.py, build_fps.py, build_coconut.py, build_dataset.py, build_pool.py, train_fp.py; ../checkpoint_lineage/original_sources/train_fp3.py and train_fp4.py; ../ranker_lineage/original_sources/make_ranker3.py and its companions.
New reconstructed bridge: prepare_legacy_exports.py writes the flat array cache using original speclib.load_flat, and the selected fingerprint export using the original train_fp.SpecData frequency recipe. The original standalone export wrappers were not recovered. The new wrapper's pickle serializer and archive timestamps are not asserted to reproduce old file bytes.
New opt-in deterministic launcher: ../checkpoint_lineage/deterministic_training_launcher.py. It seeds before initialization and enforces deterministic kernels. It deliberately differs from the historical launch behavior; see its recipe and limitations.

Full preparation in a NEW workspace
----------------------------------
Set these three absolute paths, then create a new WORK directory. SOURCE is this public_source folder; INPUT_TRAIN and INPUT_COCONUT are lawfully acquired immutable inputs. Do not run the original writers in an existing experiment directory: they write output names directly.
  SOURCE=/absolute/release/public_source
  INPUT_TRAIN=/absolute/authorized/train.parquet
  INPUT_COCONUT=/absolute/authorized/coconut_csv-09-2026.csv
  WORK=/absolute/new/legacy-rebuild
  mkdir "$WORK"
  cd "$WORK"
  python "$SOURCE/prepare_legacy_exports.py" flat --train "$INPUT_TRAIN" --output data
  ln -s "$INPUT_TRAIN" data/train.parquet
  mkdir -p db/coconut
  ln -s "$INPUT_COCONUT" db/coconut/coconut_csv-09-2026.csv
  python "$SOURCE/build_fps.py"
  python "$SOURCE/build_coconut.py"
  python "$SOURCE/build_dataset.py"
  python "$SOURCE/prepare_legacy_exports.py" selected --data data --output up_train
  python "$SOURCE/build_pool.py"
This writes ds/spec.npz and ds/split.pkl, up_train/{fp_bits.npy,fp_sel.npy,fp_meta.pkl}, and pool_{fp,mass}.npy plus pool_meta.pkl in WORK. Trainers can use ds/spec.npz directly. To match the old dataset layout in a fresh staging directory, copy spec.npz and split.pkl alongside the three up_train files; staging changes no scientific contents.

Input and resource contract
---------------------------
OBSERVED_LEGACY_ARTIFACT_BINDINGS.json supplies exact byte lengths and SHA256 for the current retained old train, September2026 COCONUT CSV, intermediate arrays and outputs. These are observed local byte pins, not a signed upstream release checksum or a historical build attestation. In particular, the later current train.parquet has different bytes and rows; it must not silently substitute for the pinned legacy train. COCONUT must supply canonical_smiles, molecular_formula and np_likeness. The source normalizes the largest fragment and filters molecule size, charge and mass before sorting np_likeness and deduplicating connectivity keys. Rights and original source attribution are in the dataset cards; this source release does not redistribute spectra or third-party databases.
The original full-data preparation loads large arrays, materializes fingerprint matrices and uses ten multiprocessing workers. It is not a 2GiB recipe. No new full-run memory/time measurement is claimed. Choose a separately budgeted machine before running it. The historical training record names a Kaggle T4 image digest, but exact historical NumPy/RDKit/Pandas/PyArrow/Torch versions are not recoverable. Demo package pins are validation-environment pins only. Full preparation additionally requires RDKit and PyTorch: build_dataset imports fpmodel, whose module imports Torch even though preparation does not execute FPNet. Training also requires PyTorch. Preserve their versions in any new run receipt.

Schema and split
----------------
Raw fingerprint layout: Morgan radius2 4096 + Morgan radius3 4096 + RDKit path(maxPath6)2048 + MACCS167 =10407. Structure rows use sorted first-seen inchikey14 keys after invalid-molecule removal. Legacy selected bits satisfy 0.005 <= frequency <= 0.995 over ALL legacy training structures; the retained mask contains6930 bits, and this includes structures later used for legacy validation. It is not the later optimizer-only10395-bit selection.
The exact split code sorts np_keys before sampling. It takes qualifying NP-library structures also in cleaned COCONUT, forces all enveda-np-examples structures into validation, then samples up to2500 additional keys with np.random.default_rng(0), excluding forced keys. Every prepared spectrum inherits its structure's is_val. The saved split.pkl contains sorted VAL and forced lists. Exact source/filter/input/NumPy bindings are necessary; PYTHONHASHSEED does not affect this sorted candidate list.
The retained cache has2,334,531 spectra and273,983 observed structures. Direct aggregate checking found zero structures with spectra in both legacy train and validation. This supports the legacy merged-spectrum grouping boundary; it does not certify a fresh blind test or the newer four-role protocol.
spec.npz keys: off(int64 ragged offsets), mz/it(float32 prepared peaks), prec(float32), ad(int16), ins(int8), ce/mode(float32), six(int32 structure row), is_val(bool), src(int64 raw row). src preserves the exact raw row index; changing train order invalidates that join. Both raw peak arrays must be rounded to float32 before original prep_peaks. Missing CE is stored -1 and the trainer later substitutes25.
Pool metadata aligns keys/smiles/src/npl to packed pool_fp rows and ascending pool_mass. The original mass ordering uses np.argsort without an explicit stable sort; exact tie order/package bindings should be recorded in new runs. Retained pool shape is711705x867 packed bytes for6930 selected bits.

Exact retained S2/M1 launch recipes
----------------------------------
Run from the NEW prepared WORK directory. TRAINERS points to ../checkpoint_lineage/original_sources. These commands reproduce the retained configured argv with explicit local paths; they are expensive training commands and have not been run for this release.
  TRAINERS=/absolute/release/checkpoint_lineage/original_sources
  python -u "$TRAINERS/train_fp3.py" --spec ds/spec.npz --fpdir up_train --pooldir . --steps 24000 --bs 256 --lr 2e-4 --K 63 --lam 1.0 --seed 202 --d 512 --layers 6 --val_every 2000 --max_minutes 300 --out fp_model_s2.pt
  python -u "$TRAINERS/train_fp4.py" --spec ds/spec.npz --fpdir up_train --pooldir . --steps 50000 --bs 256 --lr 2e-4 --K 63 --lam 1.0 --seed 404 --d 512 --layers 6 --merge_p 0.60 --val_every 2000 --max_minutes 420 --out fp_model_m1.pt
Defaults: warmup2000, heads8, dropout0.1, negative mass window10ppm, no resume. S2 has no merge_p option. M1 applies merge probability0.60 during both training and validation. The selected public v2 checkpoint steps are20000(S2) and24000(M1), not the configured maximum24000/50000. Both original trainers call torch.manual_seed AFTER constructing FPNet, so identical initial weights/final checkpoints are not promised. The optional deterministic launcher is a separate new recipe, not a historical correction.
Checkpoint hashes: fp_single_s2.pt c19aa29016ed4d7a67bac38105b8fa5076c696c29eb66a504558c9b2e52b614a; fp_merged_m1.pt261529c823825cbe2028684bbf7214a95a7e631ca9f656336d577c507cce8294. Both144110255 bytes,6930bits,d512,layers6. See checkpoint_lineage for byte lineage and the unresolved original-M1 export relationship. Do not rename newly trained outputs to imply byte identity with these checkpoints.

Ranker reconstruction and remaining evidence gaps
-------------------------------------------------
../ranker_lineage/original_sources/make_ranker3.py is the recovered original rank_train.npz builder. FEATURE_COLUMNS.json describes its31 columns:15 non-FP analog/context,6 FP-logit scores,4 fragmentation and6 FP cross-channel features. The retained142762x31 matrix hash is41ccec87fba5f8ab255aaf5a723567f25bd766064265c5cc2b83ba2cf15f57f8. Its A/B logit inputs are6930-wide raw logits, not probabilities. The source reads several prerequisite query/analog/fragment caches and must not silently substitute cache variants. The exact historical FP checkpoint and producer of all cached columns remain unresolved; multiple sources write the same hard_model_logits.npy name, and no literal A-combo writer was recovered. Therefore the original source and feature definitions are available, but a byte-exact old ranker rebuild is not claimed. RANKER_COMMANDS.txt lists the original command and prerequisite gaps. A new pinned cache route is still under source review and is not included in this publication; any later outputs must be labeled new.
Do not equate the public dataset version6 with local directory suffix up_rank6: the retained public rank_train has31 columns, while the inspected suffix6 route has39 and a different dependency contract.

Later full10395 lineage
----------------------
The later full fingerprint bank selects only nonconstant optimizer-role bits and preserves the existing candidate order. It uses separate four-role/group metadata and is not created by the legacy selection command above. ../full_fingerprint_lineage contains the exact original builder and an aggregate manifest, with its unresolved portable role-generation closure explicit. ../selected_v6_serving is separate from S2/M1 and records the actual V37 source and native state. None of these source packets implies a completed official score.

Trusted file boundary
---------------------
The original scripts contain trusted-pickle reads and are published unchanged for provenance. Only use their own hash-bound outputs or an explicitly reviewed local source. Do not load arbitrary downloaded pickle/checkpoint files. The new selected exporter restricts its own primitive metadata reader, and the toy demo reads only files it just created. No spectra, structure IDs, role lists, checkpoints, credentials, launch authorization or notebook identity files are included in the source-only publication candidate.
