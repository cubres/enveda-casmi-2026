# CASMI 2026 fingerprint model protocol and code

Published by the Kaggle account prvsiyan, 2026. Version 1.0.

## What this dataset is

The two model pairs read a tandem mass spectrum (MS/MS) and predict a molecular fingerprint. The 6-layer pair predicts 6,930 bits and the 8-layer pair predicts 10,395 bits. In the Enveda CASMI 2026 setting, the predicted fingerprint is used to rank candidate structures from a pool. Each pair has a single-spectrum view and a merged-spectrum view.

This release contains the evaluation protocol that the file itself records as written before any model was loaded, the metric code, the network definition, the training settings and the training recipes. It also lists the public scores of our official submission rows.

**No held-out result is stated in this version.** The held-out result tables and the two 8-layer checkpoints are not included (see Provenance and Licence). The protocol and metric code let you run the same evaluation on your own per-query scores.

## Why this release exists

The intended readers are people building MS/MS-to-fingerprint or candidate-ranking systems who want a documented evaluation: how the candidates are chosen, how ties are handled, which metrics are used, and how the networks were trained.

## Files

| File | What it is |
|---|---|
| `README.md` | This card. Its text is also the Kaggle description. |
| `LICENSE`, `LICENSE-CODE-APACHE-2.0.txt` | Licence texts (see Licence). |
| `NOTICE.md` | Per-file terms and upstream sources. |
| `MANIFEST.json` | Byte counts and SHA-256 checksums of every other file in this dataset. |
| `dataset-metadata.json` | Kaggle dataset metadata. Its description is identical to this README. |
| `evaluation_protocol.json` | The protocol, unchanged from the file that was written before any model was loaded. |
| `training_settings.json` | Optimiser, learning-rate schedule, loss, decoy sampling, augmentation, validation rule and run status for all four models. |
| `training_recipe_spectrum.json` | Configuration of the 8-layer single-spectrum run (paths replaced by placeholders). |
| `training_recipe_merged.json` | Configuration of the 8-layer merged-spectrum run (paths replaced by placeholders). |
| `fpmodel.py` | PyTorch definition of the network (`FPNet`) and the peak preprocessing (`prep_peaks`). Apache-2.0. |
| `eval_metrics.py` | Metric-only code: candidate window, optimistic and pessimistic ranks, MRR@25, top-1, recall@25, paired bootstrap. No data. Apache-2.0. |

Not included in this version: the result tables and their column dictionary, the two 8-layer checkpoints, the 6-layer checkpoints, the bit index, per-query ranks, spectra and structures, the featuriser code and the trainer source. See Provenance.

Model keys used in the settings and recipes: `full_s2` (8-layer, single-spectrum view), `full_m1` (8-layer, merged view), `clean_s2` (6-layer, single-spectrum view) and `clean_m1` (6-layer, merged view).

## Terms

| Term | Meaning |
|---|---|
| MRR@25 | Mean reciprocal rank of the true structure among its candidates, truncated at rank 25: 1/rank if the rank is 25 or better, otherwise 0. 1.0 means the true structure is always ranked first. |
| top-1, recall@25 | Share of queries whose true structure is ranked first, and share ranked within the top 25. |
| Optimistic and pessimistic ties | Optimistic ties favour the true structure (the primary metric). Pessimistic ties count against it (reported as a check). |
| Pool, candidate window | The pool is the set of structures a ranker can choose from: competition training structures and COCONUT natural products. For one query, the candidates are every pool row within ±10 ppm of the true structure's mass. |
| Roles | Each structure belongs to one role fixed before training: optimizer (training weights, role code 0), checkpoint (choosing the saved checkpoint, role code 1), fusion-selection (the test structures of the protocol, role code 2) and final-test (sealed, role code 3). Fusion-selection and final-test structures are never used for training or checkpoint choice. |
| In-sample | Structures a model was trained on. |
| Single-spectrum and merged views | Single-spectrum view (`_s2`): trained on single spectra. Merged view (`_m1`): trained with same-structure spectra merged (merge probability 0.6). |
| Step 2, Step 1b | The protocol's labels for its two follow-up branches, quoted below as the protocol writes them. |

## Protocol

`evaluation_protocol.json` records its own status as written before any model was loaded (`"written_before_models_loaded": true`). Its SHA-256 is `5e37e575b8f837c0c02710582b0e9bb0b88dbf8e2807ee38ee5bc2a2614f5d3e`, and the file was created on 2026-10-08 at 14:41 UTC.

- **Question.** Does the full 8-layer pair (10,395 bits) rank unseen structures better than the clean 6-layer pair (6,930 bits)?
- **Queries.** 4,096 structures sampled from the fusion-selection role with seed 20261008. Each query uses one spectrum, chosen with seed 20261009.
- **Input.** A single spectrum, with no augmentation and no merging, at most 128 peaks (`fpmodel.MAX_PEAKS=128`).
- **Candidates.** Every pool row whose mass is within ±10 ppm of the true structure's mass.
- **Ties.** Optimistic rank is the primary metric. Pessimistic rank is reported.
- **Metrics.** MRR@25, top-1 and recall@25. Paired bootstrap with 5,000 resamples over structures, giving 90% intervals.
- **Decision rule.** Quoted exactly as the protocol file states it:

```
promote full pair to Step 2 (engine integration) if BOTH views show delta MRR@25 >= +0.03 with 90% lower bound > 0; if both deltas < +0.01 the 8L/10395 recipe is not stronger -> Step 1b (new recipe); otherwise integrate only the view that passes. Deployed pair is contaminated (trained on these structures) and is reported, never used for the decision.
```

The "deployed pair" named in the rule is contaminated: it was trained on these structures. The protocol reports it as a reference and never uses it for the decision.

`eval_metrics.py --demo` runs on synthetic scores. The candidate window, tie handling and bootstrap are implemented as the protocol describes.

## Architecture (`fpmodel.py`)

The network follows the CSI:FingerID-style neural ranker design (Dührkop et al., 2015): it reads a spectrum and predicts a fingerprint, which is then used to score candidates.

- **Peak preprocessing (`prep_peaks`).** Peaks above precursor m/z plus 1.5 Da are dropped, as are peaks below 0.1% of the base peak. If more than 128 peaks remain, the function keeps up to 8 of the most intense peaks in each 50 Da window, then the 128 most intense overall. Peaks are sorted by m/z and intensities become square roots of relative intensity.
- **Peak tokens.** Each peak is embedded from its m/z (log-spaced sinusoidal features, as in the code's docstring citing Voronov et al.), its neutral loss (precursor m/z minus peak m/z) and its intensity, then projected to width 512.
- **Global token.** One extra token carries the precursor m/z embedding, collision energy divided by 100, a merge-mode flag, a log-scaled precursor value, and learned embeddings for adduct (26 entries, including an unknown class) and instrument family (timsTOF, Orbitrap, QTOF, ion trap, other).
- **Encoder.** Pre-norm transformer blocks with width 512, 8 attention heads, a 4x GELU feed-forward block, dropout 0.1 and a padding mask. The 6-layer models use 6 blocks, the 8-layer models use 8.
- **Readout.** A final LayerNorm, then the global token and the mean of the peak tokens are concatenated and passed through Linear(1024, 2048), GELU, dropout and Linear(2048, nbits). Each output is one logit per fingerprint bit.

Parameter counts computed from the definition in `fpmodel.py`: 49,424,027 for the 8-layer, 10,395-bit model, and 36,019,474 for the 6-layer, 6,930-bit model.

**Output bits.** The 8-layer pair's stored candidate fingerprints have 10,395 bits. They are a molecular fingerprint descriptor; the featuriser is not included, so the output logits cannot be matched to descriptor positions from this release.

## Training

Settings for all four models are in `training_settings.json`. The 8-layer runs and their recipes are in `training_recipe_spectrum.json` and `training_recipe_merged.json`.

- **Optimiser and schedule.** AdamW with weight decay 0.01 and betas (0.9, 0.98), peak learning rate 2e-4. Linear warm-up for min(2,000, steps/10) steps, which is 2,000 steps for every configured run, then cosine decay to 2% of the peak at the configured final step. Gradients are clipped to global norm 1.0. Mixed precision (fp16 autocast with a gradient scaler) on CUDA.
- **Loss.** Binary cross-entropy with logits over the output bits (mean), plus a ranking cross-entropy over one true candidate and 63 decoys with ranking weight 1.0. Each candidate's score is its stored fingerprint dotted with the model's logits, centred over candidates and divided by the square root of the output bit count.
- **Decoys.** 63 per training query, drawn uniformly with replacement from pool rows within ±10 ppm of the true structure, excluding the true row. If the window holds one row or none, decoys are drawn from the whole pool.
- **Augmentation (training only).** Peak dropout with a per-spectrum rate drawn uniformly from [0, 0.3]; intensities multiplied by lognormal noise (sigma 0.25); m/z multiplied by 1 + N(0, 5e-6).
- **Batch.** 256 spectra per step. The 8-layer runs used micro-batches of 128. The 6-layer runs do not record a micro-batch size.
- **Data split.** The optimizer role only was used for training. For the 8-layer recipes this is 1,886,521 spectra from 219,140 structures. Checkpoints were chosen on the even-index half of the checkpoint role, which for the 8-layer pair is 111,020 spectra from 13,589 structures.
- **Hardware.** The 8-layer runs used two T4-class GPUs each, with both views trained concurrently, one per GPU. The 6-layer models used one GPU per model, with the two models running concurrently.
- **Checkpoint rule.** Validation every 2,000 steps; keep the checkpoint with the highest validation metric. The 8-layer metric is sampled-decoy MRR@25 on 2,048 checkpoint-role structures (63 fixed decoys each). The 6-layer metric is hardneg-top1, which is not MRR@25; the two histories are not comparable.

Run status:

- **8-layer single-spectrum.** 30,000 configured steps completed in 17,626 s. Checkpoint at step 26,000 selected.
- **8-layer merged.** 30,000 configured steps completed in 16,273 s. Checkpoint at step 26,000 selected.
- **6-layer single-spectrum.** 24,000 configured steps completed (about 9,100 s, from the log). Checkpoint at step 24,000 selected.
- **6-layer merged.** Stopped by its time budget at about step 27,600 of a 50,000-step schedule (12,444 s of training). The learning rate was 9.18e-5 when the run stopped, so the cosine schedule did not finish. Checkpoint at step 26,000 selected. This model is less fully trained than the other three.

The four runs did not have the same configured number of steps (24,000 to 50,000), so the 6-layer and 8-layer comparison tests the two recipes as they were run, not depth alone.

## Official submission rows

The public scores below are from the Kaggle submissions listing snapshot taken on 2026-10-10 at 11:47 UTC. The descriptions are paraphrases of the listing text in the same snapshot, with internal build labels replaced by plain wording. The baseline composition is our own pipeline version 6 (V6). The forward re-scoring variant is defined in the notes below.

| Row id | Public score | Listing description (paraphrased) |
|---|---|---|
| 56859903 | 0.340 | Exact repeat of the baseline composition as a control reproducibility draw, on source unchanged from a previously scored submission. No new method claim. |
| 56824628 | 0.340 | Original combined popularity-tier forward composition, pinned to the private baseline composition, with the precursor union off and the production ranker unchanged. Hidden composition score unverified. |
| 56963908 | 0.340 | Exact redraw of the baseline composition on the corrected test data (host RemoveStereochemistry fix). Deterministic pipeline, with source and output unchanged from rows 56824628 and 56859903. Gives the rescored baseline for the frozen adopt/reject rule. No new method. |
| 56953547 | 0.344 | Draw 1 of 2 of the forward re-scoring variant: the baseline composition (scored 0.340 in two runs) with re-scoring weights of 0.0 and 1.0 on two scoring components, everything else byte-identical. Predeclared rule: adopt if the mean of two draws is at least 0.348 and both are at least 0.340; reject if the mean is at most 0.341. Visible CSV identical to the baseline composition. |
| 56956461 | 0.344 | Draw 2 of 2, from the public notebook: the baseline composition (scored 0.340 in two runs) with the same re-scoring weights, everything else byte-identical. Same predeclared rule: adopt if the mean of two draws is at least 0.348 and both are at least 0.340; reject if the mean is at most 0.341. The forward-stack dataset is now public. |
| 57018380 | 0.335 | Corrected-checks CPU-only run of the baseline composition with forward re-scoring off (popularity prior and PubChem tier), plus our own second candidate list fused by reciprocal rank fusion. Judged against the exact redraw of the baseline composition, R = 0.340 (machine-numerics caveat recorded). |

Notes on the rows:

- The listing description of row 56963908 says it was run on the corrected test data.
- The listing descriptions of rows 56953547 and 56956461 give the predeclared rule (paraphrased in the table). Both rows have public score 0.344, so the mean is 0.344. That meets neither threshold of the rule.
- The listing descriptions of rows 56953547, 56956461 and 57018380 do not state a test-data version.
- The listing description of row 57018380 records a machine-numerics caveat against the exact redraw of the baseline composition (row 56963908).
- Row 57040985 was submitted on 2026-10-10. It had no public score in the 11:47 UTC snapshot and is not reported.
- The forward re-scoring variant is the baseline composition with re-scoring weights of 0.0 and 1.0 on two scoring components, as the row descriptions state.
- The public scores are the platform's figures. They are not computed from the files in this release.

## Limitations

- **No held-out result.** This version states no held-out MRR@25 or other evaluation result, because the result tables are not included. The metric code can be run on your own per-query scores, but this release does not reproduce the held-out numbers.
- **Public score.** The public scores are the platform's figures, and this release does not reproduce the public pipeline.
- **Output bits.** The bit index is not included, so the 8-layer logits cannot be matched to descriptor positions.
- **Weights.** The checkpoints are not included, so the trained models cannot be run from this release. The architecture can be instantiated.
- **Unequal training.** The 6-layer merged run stopped early (see Training). The 6-layer and 8-layer runs use different validation metrics.
- **Missing code.** The trainer source and the featuriser are not included. The training settings describe the trainers.

## How to load

Check the architecture and parameter counts (PyTorch and NumPy required; run from the folder that contains `fpmodel.py`):

```python
from fpmodel import FPNet, prep_peaks

eight = FPNet(10395, d=512, layers=8)
six = FPNet(6930, d=512, layers=6)
print(sum(p.numel() for p in eight.parameters()))    # 49,424,027
print(sum(p.numel() for p in six.parameters()))      # 36,019,474

# peak m/z, intensities and precursor m/z -> model inputs (m/z, square root of relative intensity)
mz, sqrt_rel = prep_peaks([100.0, 200.0, 300.0], [1.0, 0.5, 0.2], 400.0)
print(mz, sqrt_rel)
```

Compare two models with the metric definitions (NumPy required; no data needed):

```python
import numpy as np
from eval_metrics import ranks_for_query, reciprocal_rank, paired_bootstrap, summarise

rng = np.random.default_rng(0)
ranks_a, ranks_b = [], []
for _ in range(200):
    base = rng.normal(size=90)              # one query with 90 candidates
    truth = int(rng.integers(0, 90))
    a = base.copy(); a[truth] += 1.2        # scores from model A (replace with yours)
    b = base.copy(); b[truth] += 1.0        # scores from model B (replace with yours)
    ranks_a.append(ranks_for_query(a, truth)[0])    # optimistic rank
    ranks_b.append(ranks_for_query(b, truth)[0])
print(summarise(np.array(ranks_a)))
print(paired_bootstrap(reciprocal_rank(np.array(ranks_a)), reciprocal_rank(np.array(ranks_b))))
```

The code in this release was checked with Python 3.12.14, PyTorch 2.8.0 and NumPy 2.2.6.

## Provenance

- **Competition data.** The models were trained on the Enveda CASMI 2026 competition training data, and the candidate pool includes its training structures. The host's licence for this data is recorded in the project's source notes as CC BY-NC 4.0 (not independently re-verified for this release). The competition rules, as recorded in the same notes, forbid redistribution. This release therefore contains no competition spectra, structures, fingerprints or per-query arrays.
- **Withheld from this version.** The five result tables (`eval_results.csv`, `paired_deltas.csv`, `fusion_results.csv`, `training_histories.csv`, `training_histories_clean_6layer.csv`) and their column dictionary; the two 8-layer checkpoints (`full_spectrum.pt`, `full_merged.pt`); the 6-layer checkpoints; the bit index; the featuriser code and the trainer source. The result tables and checkpoints are derived from the competition training data, and their redistribution has not been cleared for this release.
- **Candidate pool.** The pool combines competition training structures with structures from the COCONUT natural-products collection, which is licensed CC BY 4.0 as recorded in the project's source notes (not independently re-verified for this release). COCONUT is credited below.
- **Official rows.** Row ids, public scores and listing paraphrases come from the Kaggle submissions listing snapshot taken on 2026-10-10 at 11:47 UTC. They are our own submission records and public listing facts.

## Licence

- **Dataset field.** CC-BY-NC-SA-4.0.
- **Card, protocol, settings, recipes and metadata.** CC BY-NC-SA 4.0 (`LICENSE`, `NOTICE.md`).
- **Code.** `fpmodel.py` and `eval_metrics.py` are also offered under the Apache License 2.0 (`LICENSE-CODE-APACHE-2.0.txt`).
- **Official row facts.** The row ids, public scores and listing paraphrases in this card are offered under CC BY 4.0 (see `NOTICE.md`).
- **Upstream terms.** See Provenance. Third-party licences are listed as stated by each project and are not independently re-verified for this release.

## Credits

The models, protocol and this card are by prvsiyan (Kaggle account). The competition is the Enveda CASMI 2026 molecule identification challenge (Kaggle, `enveda-CASMI26-molecule-id-mass-spectra`). The network follows CSI:FingerID.

Dependencies and upstream sources:

| Component | Used for | Licence |
|---|---|---|
| PyTorch | `fpmodel.py` (network definition) | BSD-3-Clause |
| NumPy | `fpmodel.py` and `eval_metrics.py` | BSD-3-Clause |
| COCONUT natural-products collection | Candidate pool structures | CC BY 4.0 |
| Enveda CASMI 2026 competition training data | Training data and candidate pool | CC BY-NC 4.0 (host) |

Licences are as stated by each project and as recorded in the project's source notes. They are not independently re-verified for this release.

Citations:

- Dührkop K. et al. (2015). Searching molecular structure databases with tandem mass spectra using CSI:FingerID. *PNAS* 112(41), 12580–12585.
- Sorokina M. et al. (2021). COconut online: Collection of Open Natural Products database. *Journal of Cheminformatics* 13, 2.
- Voronov et al., cited in the docstring of `fpmodel.py` for the log-spaced m/z embedding. The full reference was not recorded for this release.
- Enveda CASMI 2026 molecule identification challenge (Kaggle, `enveda-CASMI26-molecule-id-mass-spectra`).

To cite this dataset: prvsiyan (Kaggle account) (2026). *CASMI 2026 fingerprint model protocol and code.* Kaggle dataset `prvsiyan/casmi-2026-fingerprint-model-eval`.

## Changelog

- **1.0 (2026-10-10).** First release: evaluation protocol, metric code, network definition, training settings and recipes, and official submission rows. Result tables and checkpoints are not included in this version.
