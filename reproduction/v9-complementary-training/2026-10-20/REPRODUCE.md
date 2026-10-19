# Reproduce and inspect the exact V9 treatment

## Download the exact completed V9 artifacts

1. Open [the version-pinned public notebook](https://www.kaggle.com/code/prvsiyan/casmi-fp-trainer-merged-spectra?scriptVersionId=360180749). Verify the page shows **Version 9** and a successful completed run. Do not switch to the latest version.
2. Open that version's **Output** tab. In `casmi_complementary_fp_3000_training_20261019/`, download `complementary_full_model.pt` and `optimizer_state.pt`. Save both files into a fresh local artifact directory. If the complete output archive is downloaded instead, find that exact nested training directory after extraction.
3. Run the hash-only checker below before loading either file. It checks the expected sizes and SHA256 values in [ARTIFACTS.json](ARTIFACTS.json). A mismatch stops the check; do not treat a later version's output as V9.

```bash
python verify_v9_artifacts.py --directory /path/to/v9-artifacts
```

No expiring signed download URL is embedded here. `kaggle kernels output` using only the notebook ref is a latest-output operation and does not guarantee native run `360180749`; it is not a pinned V9 download command. The exact version page plus content hashes is the documented route.

The `.pt` weights/state and sampler `.npy` arrays are not Git blobs. `PUBLIC_FILE_MANIFEST.json` lists the small source/documentation/receipt files in this Git directory; `ARTIFACTS.json` lists the two native files checked by `verify_v9_artifacts.py`.

## Reproduce the training treatment

Use the exact [public V1 inputs](INPUTS_V1.json):

- [Full fingerprint inputs V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-full-fingerprint-inputs/versions/1).
- [Prepared spectra V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-spec-fp/versions/1).
- [Selected V6 checkpoint V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-v6-structure-uniform-checkpoint/versions/1), `best_full_model.pt`, SHA256 `9c46ca4fcf19002fecbcded0d0808e8a81e3a25a143e684e259f265c44a5be31`.

Fork the exact V9 trainer or place those input files under the paths below. The unchanged source verifies its source/input hashes before training. Use the recorded Python 3.12.13, NumPy 2.0.2 and PyTorch 2.10.0+cu128 / CUDA 12.8 runtime, with suitable CUDA hardware; the configuration does not pin the current container image.

```bash
python -B -u source/train_complementary_fp.py \
  --data /kaggle/input/casmi26-full-fingerprint-inputs \
  --spec /kaggle/input/casmi26-spec-fp/spec.npz \
  --checkpoint /kaggle/input/casmi26-v6-structure-uniform-checkpoint/best_full_model.pt \
  --out /kaggle/working/new_complementary_training_output
```

The output directory must not already exist. Preserve any failed output; the driver does not retry it or support `--resume`. Start from the selected V6 parent to reproduce this recipe, not from the newly trained V9 file. A fresh AdamW optimizer performs a 64-update finite-loss/gradient/memory/throughput canary and then the remaining 2,936 updates without reset. The recipe is fixed in the source: 3,000 updates, seed 20261019, learning rate 2e-5, warmup 128, batch 256 / microbatch 64, merge probability 0.5, role 0 only. The parent was selected at update 28,000 from its separate 30,000-step run.

The driver limit is 2,700 seconds including a 120-second saving reserve, with 20 GiB RSS and 13 GiB CUDA-memory limits. Forking exact V9 retains its separate 3,000-second wrapper limit; direct CLI execution does not install that wrapper. Budget the native job and all allocated resources separately. The recorded T4×2 allocation exposed one CUDA device to the driver; the whole allocation consumes resources.

The V9 driver performs no validation, held-role query, model selection or official submission. Its final checkpoint has not been quality-evaluated. Recorded source/input hashes and RNG state make the treatment inspectable, but deterministic CUDA algorithms were not enabled and bit-identical GPU weights are not guaranteed. No model execution was performed to prepare this source release.
