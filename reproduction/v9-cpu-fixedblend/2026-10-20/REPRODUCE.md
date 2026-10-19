# Public input recipe

The measured backend was Apple Silicon macOS, Python 3.12.14, Torch 2.8.0,
NumPy 2.2.6, RDKit 2026.03.3, threadpoolctl 3.6.0 and psutil 7.2.2. The exact
core deliberately requires Mac CPU FP32; GPU/MPS and another backend are not
qualified by this result. Reproduction commands below are examples, not another
run of the campaign's already completed test.

Obtain these **specific public versions**, retaining their source/rights cards:

- [V7/native359867655 cached V6 output](https://www.kaggle.com/code/prvsiyan/casmi-fp-trainer-merged-spectra?scriptVersionId=359867655): extract the files named in `PUBLIC_INPUT_PINS.json`, including `query_logits.npy`. This is a notebook output, not a separately published raw-cache dataset.
- [V9/native360180749 model and complete training recipe](https://www.kaggle.com/code/prvsiyan/casmi-fp-trainer-merged-spectra?scriptVersionId=360180749): `complementary_full_model.pt`, SHA256 `c1c7650411d507f395e3077e90db72a8b1d692493e91c7f13ba6f55e6359b286`, and its `training_config.json`. The version's training outputs include the original source/contract, 3,000-step history and full continuation recipe; preserve those when redistributing parameters.
- [Public full fingerprint bank V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-full-fingerprint-inputs/versions/1).
- [Public prepared spectra V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-spec-fp/versions/1), containing `spec.npz`.
- [Public checkpoint-disjoint split V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-v6-checkpoint-disjoint-ranker-split/versions/1). Its full public-input rebuild was verified byte-for-byte before release.
- [Original selected V6 source/permission](https://github.com/cubres/enveda-casmi-2026/tree/6987d48bab9e6ea36ce07db322d64e282463c838/reproduction/selected-v6-training/2026-10-18).

Store the bank/cache/split files flat in their respective directories. Put the
V9 model and its training config together. The adapter accepts paths on any
volume; no author-specific filesystem path is embedded:

```bash
python build_public_inputs.py \
  --bank /path/to/public-bank-v1 \
  --spectra /path/to/public-spectra-v1/spec.npz \
  --cache /path/to/native359867655-cache \
  --split /path/to/public-split-v1 \
  --v9 /path/to/native360180749-training-output \
  --output ./new-public-metadata
```

It takes the published `development1` mask without retuning or exclusions,
joins spectrum rows through V7, and checks all four resulting array byte hashes.
Only public scalar/group metadata is decoded. No truth fingerprint, positive
candidate index, old assay, historical private map or signed URL is an input.
The resulting contract contains machine-local paths generated from your flags.

The metadata adapter **completed once**, producing exact matches for all four
frozen development-array hashes and the 29-input portable contract. The saved-
result verifier also exited successfully. Neither check ran a model or selected
a weight. Original source-only labels are retained as the exact preparation
snapshot; the release manifest records their completed verification. For a fork,
the adapter's output hash checks must pass before using the unchanged measured
core:

```bash
env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  VECLIB_MAXIMUM_THREADS=2 NUMEXPR_NUM_THREADS=2 \
  CUDA_VISIBLE_DEVICES='' PYTORCH_ENABLE_MPS_FALLBACK=0 \
  python -B source/v9_cpu_fixedblend_schema_successor.py \
  --contract ./new-public-metadata/public-inputs.json \
  --output ./new-fork-cpu-result
```

The output directory must not exist. The unchanged core retains its blind
64-query canary, conservative forecast and 880-second/6-GiB limits; a failed gate
stops instead of changing the experiment. For the original campaign, root-owned
external supervision also verified positive sampled RSS, terminal exit and
closed process ownership within a 900-second envelope. Those private operational
captures are not public dependencies.
