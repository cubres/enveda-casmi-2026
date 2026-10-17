CASMI historical S2/M1 checkpoint lineage — source review, 2026-10-18

Exact configured source recipes:
S2: train_fp3.py; steps 24000; seed 202; no merge_p option; single spectra; time limit 300 minutes.
M1: train_fp4.py; steps 50000; seed 404; merge_p 0.60; time limit 420 minutes.
Shared: batch 256, lr 2e-4, K 63, lam 1.0, d 512, layers 6, val_every 2000, default warm 2000.
Full symbolic argv and exact source hashes are in PUBLIC_CHECKPOINT_BINDINGS.json. D1 and D2 are unresolved historical mount directories; original recipes use unversioned dataset references and shortest-path glob discovery.

Fresh raw-byte hashes bind up_model3/fp_single_s2.pt and fp_merged_m1.pt to retained casmi26-fp-models-v2 version1 observations. Retained JSON metadata gives selected steps 20000 and 24000, nbits6930, d512, layers6. These differ from configured maximum steps. No checkpoint was deserialized in this review.

The original-named fp_model_s2.pt matches the optimizer-bearing v4/v1 S2 receipt. The original-named fp_model_m1.pt differs from the retained v4/v1 M1 hash. No byte-equivalence or rename/optimizer-stripping chain is proven between original-named files and v2 stripped files.

Retained notebook metadata records a T4 and the exact Kaggle image digest in the JSON. Actual training package versions are UNKNOWN. The notebook language_info value 3.11 and later checkpoint-measurement Torch2.10.0+cu128 are not training runtime evidence.

Both trainers initialize the model before torch.manual_seed. Re-running these historical recipes does not promise the same starting weights or final checkpoint bytes. Best-validation selection uses sampled hard-negative top1, not MRR@25 or an official score. M1 merges peers across all rows of each structure; split provenance must establish structure-disjoint roles.

The three original_sources files are exact historical source copies. They contain no embedded credentials or explicit network calls. They read trusted pickle metadata and optional torch resume checkpoints, so they are not safe readers for arbitrary untrusted files. No historical push launcher is copied, no source was executed, and no input data, model weights, notebook identity or guard was changed. Coordinator publication and data-rights review remain separate.
