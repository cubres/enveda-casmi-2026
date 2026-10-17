# CASMI legacy FP and ranker reproducibility

This packet releases the recovered preparation, FPNet, S2/M1 training and ranker source, with exact retained artifact hashes and the gaps in historical reproducibility stated explicitly. It contains source and aggregate evidence; it contains no competition records, candidate structures, role assignments or weights.

Start with [the runnable preparation recipe](public_source/README.txt). It explains how to produce `ds/spec.npz`, `ds/split.pkl`, selected `up_train` files and the candidate pool in a **new** workspace. The flat-cache and selected-fingerprint exporters are explicitly labeled new reconstructions of the original functions. A [four-spectrum invented demo](public_source/demo_preparation_synthetic.py) passed ten checks, including early float32 rounding, structure split behavior, cache serialization and fingerprint column order. It is not a full-data reproduction or score measurement.

| Component | Source and evidence | What is established |
| --- | --- | --- |
| Preparation | [recipe](public_source/README.txt), [retained byte pins](public_source/OBSERVED_LEGACY_ARTIFACT_BINDINGS.json) | Original preprocessing/builders plus reconstructed exports; actual legacy cache has no structure crossing train/validation |
| S2 and M1 | [original source](checkpoint_lineage/original_sources/), [commands and limitations](checkpoint_lineage/README.txt), [public binding](checkpoint_lineage/PUBLIC_CHECKPOINT_BINDINGS.json) | Exact retained launch argv, architecture and public checkpoint bytes; historical initialization is not deterministic |
| Optional new deterministic recipe | [launcher](checkpoint_lineage/deterministic_training_launcher.py), [instructions](checkpoint_lineage/DETERMINISTIC_RECIPE.txt) | Seeds before initialization and requires deterministic kernels; source-reviewed, not executed, and not claimed to reproduce old weights |
| Ranker | [original make_ranker3.py](ranker_lineage/original_sources/make_ranker3.py), [31 feature definitions](ranker_lineage/FEATURE_COLUMNS.json), [limitations](ranker_lineage/README.txt) | Recovered original builder and retained 142762×31 cache binding; exact historical producer of all FP logits remains unresolved |
| Later 10395-bit bank | [original builder](full_fingerprint_lineage/build_clean_full_fingerprints.py), [scope](full_fingerprint_lineage/README.txt) | Optimizer-only selection is distinct from legacy6930; original portable role-generation closure is not yet complete |

The legacy launch limits were24,000 steps/seed202 for single S2 and50,000 steps/seed404/merge probability0.60 for M1. Selected public checkpoints record20,000 and24,000 steps respectively. Both original trainers seed PyTorch after constructing FPNet. Exact historical package versions, mount versions and a complete cache-generation manifest were not recovered. These limits are evidence gaps, not parameters to guess.

Original sources contain trusted-pickle readers. Use only their reviewed, hash-bound inputs. The source files are preserved unchanged and no notebook identity or guard is included. Dataset rights, third-party attribution and access are documented separately in the dataset cards. Source publication does not make private data public or change its license.
