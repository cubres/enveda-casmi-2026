# Preregistration snapshot before native execution

# A four-parameter GLACIER intensity calibration experiment

This is an original, offline mathematical proposal. No GLACIER model was
imported, no spectrum/model was downloaded or inferred, and no real-data fit,
Kaggle notebook change, submission, or publication is included.

## Mechanism and scope

Freeze GLACIER's complete raw fragment masses and intensities for each known
structure, protonated adduct, QTOF instrument token, and explicit singleton CE.
Apply a positive intensity correction before the SAME final top-100 processing
in both arms. Four coefficients control a bounded temperature and mass tilt:

`e = (round_to_5_eV(CE) - 40) / 20`

`T(e) = 1 + 0.25 tanh(a0 + a1 e)`

`B(e) = 0.5 tanh(b0 + b1 e)`

`I'_j ∝ I_j ** T(e) * exp(B(e) * r_j)`

`r_j = model_bin_mass_j / (model_bin_mass_j + theoretical_precursor_mass) - 0.5`

The theoretical precursor and fragment masses come from the known-structure
forward path. Measured precursor mass, measured peaks, target-dependent masks,
candidate pools and rankings are never model features. Positive temperature
retains zero support and the duplicate-MAX winner within a bin. This cannot
repair missing fragments. It adds output-level CE calibration even if the
pretrained model lacks CE embedding; that would be a NEW fitted CE mechanism,
not evidence that the original checkpoint learned energy response.

Fit full-spectrum sparse cosine distance with unmatched predicted and measured
peaks included in their respective norms. Use equal weight per structure, then
equal acquisition weight within a structure, plus fixed coefficient penalty
1e-3. This NumPy prototype uses already coalesced unique physical bins and an
analytic gradient; it does not implement a corpus/model producer or tolerance
matching. The future producer must attest actual loaded `num_bins` and
`upper_limit`, exact source bin-MAX behavior, and strict raw-forward pins. Do
not substitute nominal 0.01-Da rounding for the released floor-and-offset rule.
Final evaluation also uses the exact released sparse scorer with one common
top-100/max-normalization stage; the training binned objective is a surrogate.

## Source contracts, separately from checkpoint training provenance

Retained source commit: `708148c2a8eb0c32120644436fefd2fe90cd2214`.
The original publisher [MSGym training config](https://github.com/coleygroup/ms-pred/blob/708148c2a8eb0c32120644436fefd2fe90cd2214/configs/glacier/joint_train_msg.yaml)
enables collision embedding and cosine intensity loss. The source trainer
requires MAGMa fragment labels and performs fragment boundary/cardinality
cross entropy with Hungarian assignment, auxiliary decoder weighting, then a
MAGMa-to-end-to-end loss schedule. Enveda-180 supplies measured spectra and
known structures, not those fragment-tree training annotations. Our intensity
adapter therefore does not invoke that trainer or its contrastive decoy route.

`joint_model.py` lines 1256-1450 implement full sparse binned cosine and entropy
losses. They coalesce positive intensities with duplicate MAX. The actual
training config has 150000 bins and the class default upper limit 1500;
checkpoint HP must still be observed. The separate contrastive MSGym recipe
adds decoy entropy ranking, which is outside this proposal.

Observed retained SHA-256 pins:

| File | SHA-256 |
|---|---|
| configs/glacier/joint_train_msg.yaml | b5da82ad41dcb9968d11bb3b9dfe6397f72c7d761e6f3ebe29f70442069d3b7b |
| configs/glacier/joint_contr_finetune_msg.yaml | 377889a4413a66c904952cd3e3a5c48e82147f7c35030a668203813b7c2f88b8 |
| src/ms_pred/glacier/joint_model.py (retained LF source) | bde7e581197f13342cbc0857b1834f8856e178de275e8f84077ef35f533924a1 |
| src/ms_pred/glacier/dataset.py (retained LF source) | 3e21c91b0594e9c80d0de9e49c13d2766b3d143d33ade6c22a2b455a38b3bf82 |
| src/ms_pred/glacier/train_joint.py | 5424664b2cfd4cf518e41b646d6bfa43ddde6a1762b24a8999b47636b8957bc0 |

These retained LF bytes are evidence for inspection, not replacements for the
literal released Kaggle runtime files. Source config settings are not a
checkpoint training manifest. Publisher declares the released checkpoint
MSGym-trained; exact structure overlap and the training distribution at
20/40/60 eV remain UNKNOWN. The README's 119029-known-CE simulation subset and
CE-imputation workflows concern ICEBERG and cannot prove this GLACIER model's
history. No original checkpoint-byte verification or weights redistribution.

Code is [MIT, Samuel Goldman 2023](https://github.com/coleygroup/ms-pred/blob/708148c2a8eb0c32120644436fefd2fe90cd2214/LICENSE).
The [GLACIER paper](https://arxiv.org/abs/2606.29161) motivates training spectrum
prediction directly. The original mathematical code here does not copy its
figures or competitor notebooks. Public Enveda-180 data is
[CC BY 4.0, Enveda 2026](https://zenodo.org/records/21346580), DOI
10.5281/zenodo.21346580. Existing local parquet SHA-256:
`e578c6f401605cc29250c9c7c93d0016b044f6b8d4dc9c7e05f4adbb9efde256`.
Its exact acquisition settings are Bruker timsTOF Pro 2 / Q-TOF / ESI Positive;
QTOF is the declared model instrument abstraction, not an exact machine match.

## Minimal real-data pilot, still requiring root review

First perform a metadata-only availability/chemistry audit on the existing
licensed parquet, without selecting by model outcomes. Require at least 64
distinct scaffold-connected components with positive `[M+H]+` singleton CE
records (prefer paired 40/60 eV; actual sufficient counts are not yet measured).
Freeze structure keys from standardized stereo-free canonical molecules and
generic Murcko scaffolds with an explicit acyclic sentinel. Union repeated
structure/scaffold associations before splitting; every CE, replicate,
merged acquisition and alternative identifier of a molecule stays together.
An all-acyclic group can reduce coverage; do not quietly split that group.
Exclude the eight previously inspected CE-mixing pilot structures from fit and
test. Deterministically hash whole components before looking at predictions:
32 fit / 16 development / 16 untouched test components. If components contain
several molecules, select a deterministic representative before prediction;
keep all sibling structures out of other splits. If requirements fail, HOLD
or propose a new explicitly reviewed cohort before any fit.

Cache at most two singleton forwards per selected structure (128 calls) on
the exact reviewed CPU inference path. Baseline and adapter use the same raw
outputs, masses, rounding and final peak budget. Freeze four coefficients and
optimizer/penalty choices before external held-out scoring. Development is
diagnostic only in the first pilot, not a hyperparameter search. Evaluate the
identity and fitted adapter with task-level paired deltas, equal structure
weight, all errors/abstentions, and instrument/CE strata. Use a predeclared
paired sign test and structure bootstrap with fixed seed; require positive
test mean delta, lower 95% CI >0, and no singleton-energy stratum mean loss
increase before a larger independent validation. With 16 test components this
is a falsification screen, not a strong generalization estimate. Do not train
on test labels or use failed test results for another fit.

The calibration split measures held-out generalization of NEW adapter fitting.
It does not prove the pretrained GLACIER never saw those structures. Establish
that stronger claim only with publisher training structure/split provenance;
otherwise label baseline-training overlap UNKNOWN. Enveda-180's drug-like
chemical domain also differs from hidden natural-product CASMI. No Kaggle
quality claim or ranking integration follows from this pilot.

## Hardware and current offline check

Four-parameter fitting over frozen sparse outputs is CPU NumPy work, with no
Torch autograd, DGL, TPU or GPU needed. Native forward caching cost must be
projected from the actual V11 measured CPU path; 128 calls cannot be declared
to fit a 300-second cap until measured. Full GLACIER training requires MAGMa
labels and two >=24-GB GPUs in the publisher README. A later intensity-decoder
fine-tune would require a separate gradient/CPU-shim audit and measured memory;
the current inference-only shim test does not prove backward correctness.
TPU offers no established advantage for four-parameter CPU fitting, and the
full graph/assignment training path is not an authorized TPU port.

Run the original synthetic math contracts without model/data imports:

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_calibration_math.py`

from this directory. Synthetic held-out spectra are generated by a declared
four-parameter correction and validate arithmetic/optimization only. They are
not Enveda observations, calibration performance, or an official score.
