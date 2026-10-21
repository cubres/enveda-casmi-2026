# CASMI candidate generation: test whether analogue parents create answers or only extra decoys

Updated 2026-10-21 14:59 UTC from native Kaggle leaderboard and notebook pages. This is an original research note based on public Kaggle pages. It contains no competition rows, derived features, copied candidate tables, model weights, or notebook source code.

This is a proposed experiment only: it reports no measured gain, new official score, or new dataset.

## Current verified position

The native public leaderboard shows a top score of **0.499** and prvsiyan at **0.456**, rank **383/3,744** (fresh native leaderboard read, 2026-10-21). Kaggle says the public score covers about 31% of test molecules, so it is a partial and noisy view of final performance. The public code list sorted by score currently surfaces Gluzdov's data/method notebook at **0.464** and Flexonafft's notebook at **0.462**. The score-sorted code list does not surface a notebook for the current 0.499 leader, pikachu (`jzhpfn`); the live profile's Public Notebooks section returned “No results found.” This only means no public notebook was found on that profile, not that the leaderboard submission lacks a private source.

Our accepted Analog Propagation V43 result is 0.456. It remains terminal and must not be re-submitted. The current notebook-preservation workflow is still stopped, so this note makes no claim that V43's source or output was inspected or changed.

## Strong public lead: measure the loss between generation and ranking

Kino Lutor's public discussion reports a useful distinction on their held-out set: with suitable spectral analogues, their generator produced the answer for 100 of 130 database-absent molecules, but the full system placed the answer first for only 7 of those 130. The author says the then-default generator used six parent molecules and was testing 12, 20, and 30 on CPU. This is the author's reported evidence, not an independently reproduced result. The discussion itself asks whether more parents improve final identification or mostly add decoys, whether diverse parent selection helps, and whether errors occur at generation, filtering, or ranking.

The latest public [Gluzdov V17 page](https://www.kaggle.com/code/dmitriigluzdov/casmi-26-the-data-behind-spectra-to-structures?scriptVersionId=360784035) confirms its version-table scores: V15 is 0.456, V16 is 0.464, and V17 is unscored. The older V16-specific snapshot showed a dash for V16, but this updated V17 table resolves that discrepancy. V16's listed change is to keep GLACIER proxy scores where ICEBERG scores exist and jointly reorder proxy-covered same-formula candidates; V17 changes spectral-parent count from 6 to 20. The V15-to-V16 score difference is useful public version evidence, but not an independent reproduction or isolated causal ablation. Flexonafft V47 (scriptVersionId=360486019) shows 0.462; its later multi-energy proxy experiment remains unscored. These badges and author-reported measurements are evidence leads, not a reproducible 0.495 baseline.

A separate high-visibility public candidate, [Dual-Gate Evidence Margin & PubChemLite CC0 V2](https://www.kaggle.com/code/saddamaditya/dual-gate-evidence-margin-pubchemlite-cc0?scriptVersionId=360314907), displays a **0.456** best-score badge and a 22m16s T4×2 run. Its input page reports 27.64 GB across the competition data, ranker features, fingerprint-model assets, popularity prior, PubChemLite fingerprints, and additional candidate/model packages. The notebook credits numerous prior contributors and states that substantial code is reused. Its visible E004 section identifies a Flexonafft V80 recipe whose author score was 0.436; the 0.456 badge therefore does not establish a reproduced V80 result. The visible smoke processed 12 of 400 molecules, and the E006 overlay changed one row, changed no top-1, and reports no measured score. This page is useful for tracing design lineage, but its badge is not evidence that the shown overlay improved the score. The notebook declares Apache-2.0 and highlights the PubChemLite CC0 mirror, while the full bundle has multiple other inputs; exact per-asset versions and terms were not established in this audit, so it is not a rights-qualified reproduction baseline.

The actionable hypothesis is that expanding and diversifying analogue parents can raise candidate recall, while the existing filters and ranker may discard the extra correct structures. We should measure each stage before tuning the ranker or blending more lists.

## New public analog-propagation lead and library to qualify · 21 October

A new public [Haideptry notebook](https://www.kaggle.com/code/haideptry/enveda-casmi-2026-fast-spectral-cosine-baseline) shows a **0.339 best score at V17** and a 59-minute T4×2 run. Its related [competition discussion](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion) describes “4-channel mass-shifted analog propagation” with neural Bayes reranking. That score is below our accepted V43 result (0.456) and the current public leader (0.499), so this is not a stronger baseline to reproduce. The discussion gives a useful hypothesis—separate mass-shift retrieval channels and calibrate their combined evidence—but does not provide a controlled ablation or a reproduction recipe in the listing.

The discussion index also surfaced Samar Talwar's public [CASMI 2026 Spectral Library (MassBank, harmonized), version 1](https://www.kaggle.com/datasets/samartalwar/casmi-2026-spectral-library-massbankharmonized). Kaggle reports 139,744 spectra and 20,204 structures, derived from MassBank/MassBank-data; the description says it preserves per-record licence metadata, excludes 149 records marked ND, and includes 648 records from CASMI 2012/2016 MassBank subsets. Its dataset-level licence is **CC BY-NC-SA 4.0**. The host's [licensing clarification](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/741359) says winning solutions cannot rely on licences that prohibit commercial use or redistribution. Treat this library as ineligible for a prize-oriented solution unless the host clarifies otherwise; permissive upstream record licences do not override the dataset's declared non-commercial, share-alike licence.

Overlap with the current competition training is unmeasured. Kaggle's [official data page](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/data) lists 101,727 MassBank spectra across 9,180 structures and states that exact duplicate spectra were removed across included sources while independently measured repeats of a compound remain. Because the new library shares MassBank provenance and includes CASMI 2012/2016 records, overlap is plausible, but no exact spectrum or scorer-identity overlap count has been verified. No files were downloaded or compared. This is a provenance and eligibility warning, not a usable new-data recommendation.

A distinct follow-up, once the source gate clears, is cross-fitted evidence calibration over per-candidate, metric-deduplicated channel evidence. Keep parent diversity explicit so near-duplicate analogues do not cast correlated votes; learn channel weights only on structure-disjoint folds; freeze the candidate union and compare full-list MRR@25, top-1, and query coverage on a separate holdout. Remove each answer from every candidate and spectral retrieval source before scoring, and use paired query uncertainty. This combines the public multi-channel idea with an independently testable correction for correlated parent evidence. No run or score gain is claimed.

## Complementary fingerprint checkpoint screen: no positive result · 20 October

A one-use, local CPU validation compared the 3,000-step complementary fingerprint checkpoint against its pinned baseline on 2,048 held-out structures. The measured sampled-draw MRR@25 was **0.706274** for the baseline and **0.702585** for the candidate (candidate minus baseline **−0.003689**). A paired 5,000-resample percentile bootstrap gave a 95% interval of **[−0.008241, 0.000569]**. The point estimate favors the baseline and the interval includes zero; this is not evidence of improvement.

The split contains one query per role-1-even structure and uses 63 fixed candidate draws per query sampled with replacement, retaining repeated draws in rank positions. The 64-query canary passed mechanics, resource and numerical checks; its score was not used as a quality gate. Both arms ran CPU FP32 with two threads. This local proxy is **not** the official unique-candidate metric, CUDA FP16 parity, a Kaggle score, native-serving qualification, or a submission. No GPU or Kaggle call occurred.

The evaluator script is Apache-2.0, but the executed copy currently binds local data and checkpoint paths. This note publishes only aggregate metrics and checkpoint hashes, not the script, model weights, queries or per-query rows; a portable public tool has not yet been released. The baseline checkpoint SHA-256 is `9c46ca4fcf19002fecbcded0d0808e8a81e3a25a143e684e259f265c44a5be31`; the candidate checkpoint SHA-256 is `c1c7650411d507f395e3077e90db72a8b1d692493e91c7f13ba6f55e6359b286`. Do not advance this checkpoint to serving or claim a score gain from this result.

## Proposed experiment

Use the already public V1 identity-disjoint split (10,859 train queries and 2,653 development queries) as the fixed source, but re-mask each development answer from every candidate bank and reference spectrum table by the recomputed competition scorer identity. Also remove every query's spectra from the retrieval index. This makes a removal-based unseen-structure analogue test; it is not a verified reconstruction of the hidden test's class-3 population.

Once the preservation gate allows source inspection, bind the actual V43 source/version/hash and record its current parent-selection count. Freeze one query-level split, that exact candidate generator, downstream filters, final ranker, all random seeds, and tie-breaking. Compare only parent selection:

| Arm | Parent set |
| --- | --- |
| Control | Exact parent policy and count from the hash-bound V43 source; the public six-parent method is a reference, not an assumption about V43 |
| Count | Twenty nearest spectral analogues |
| Diversity | Twenty parents selected from the top 40 spectral neighbours by greedy maximum-minimum Morgan-fingerprint diversity (radius 2, 2,048 bits); spectral-similarity rank breaks ties |

For every query, save aggregate counts and answer survival at four boundaries: before generation, after generation, after standardization/deduplication/mass filtering, and after final ranking. Report candidate recall@25/100/500, final MRR@25, top-1, eligible-query coverage, candidates generated per query, and runtime. Use the competition's pinned RDKit 2026.03.3 identity rules. Compare arms with a paired query bootstrap (10,000 resamples, fixed seed); do not use the public leaderboard as the tuning set.

### Canary and budget

Run a deterministic 64-query mechanics canary on CPU only, capped at 2 threads, 8 GiB RAM, and 15 minutes. It passes only if all three arms complete, answer identities are absent from all retrieval sources, stage counts reconcile, every emitted structure parses and has a unique scorer identity, and measured wall time projects the full cohort below a 60-minute CPU budget. The canary is a resource and contract check, not a score-selection set. If it passes, run the fixed full cohort once under the same 2-thread / 8-GiB cap and a 60-minute hard limit. Stop on any identity leakage, incomplete query coverage, runtime breach, or inconsistent stage accounting.

The primary decision is end-to-end: adopt a parent-selection change only if full-cohort MRR@25 improves with a paired 95% interval above zero and no loss of eligible-query coverage. Candidate recall alone is a diagnostic and cannot justify a score claim. If recall improves but MRR does not, publish that failure as evidence that filtering/ranking is the bottleneck.

## Stage map

~~~mermaid
flowchart LR
    A[Identity-disjoint development queries] --> B[Remove answer from all pools and spectra]
    B --> C{Fixed parent policy}
    C -->|6 nearest| D[Generate candidates]
    C -->|20 nearest| D
    C -->|20 diverse from top 40| D
    D --> E[Measure generated-answer recall]
    E --> F[Standardize, deduplicate, mass filter]
    F --> G[Measure surviving-answer recall]
    G --> H[Same frozen ranker]
    H --> I[Measure MRR@25 and top-1]
~~~


## Mass-calibration hypothesis: not confirmed for hidden spectra

A separate [public discussion on positive-mode m/z](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/743395) reports a possible **0.00055 Da** calibrant offset: its author argues the released positive-mode reference uses neutral sodium mass rather than Na⁺ mass and says released positive-mode fragments sit about 0.00049 Da above negative-mode fragments. Those are the author's observations, not an independently reproduced result. The organizer's latest visible reply, dated 29 September, says they are still checking which hidden spectra used that processing; hidden-test applicability remains unconfirmed.

The author notes the difference is unlikely to matter for a 0.01 Da or wider matching tolerance, though tighter fragment-formula matching could be sensitive. Do not shift every positive-mode spectrum on this evidence alone. If a clean, identity-disjoint local holdout is available, the useful test is a mode-stratified paired comparison that subtracts 0.00055 Da from positive-mode peaks only, freezes candidate generation and ranking, and reports eligible coverage and MRR with paired uncertainty. This is a proposed verification only; no score gain or official score is claimed.


## Release and notebook status

This note publishes no derived dataset. The V1 split and all source assets retain their own terms; the split is linked only as an input pointer. Gluzdov's notebook declares Apache-2.0, while its attributed data bundle declares CC BY-NC-SA 4.0 and preserves component-specific terms. The public notebook is credited as a source of the high-level parent-count idea; its code and outputs are not copied here.

No notebook was modified or run for this research note. V43 notebook work remains stopped pending the preservation gate and all required fresh identity/source/runtime/terminal checks. If the guard rejects an operation, stop that workflow.

## Sources

- [Live CASMI public leaderboard](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/leaderboard)
- [Public notebooks sorted by score](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/code?competitionId=143318&sortBy=scoreDescending&excludeNonAccessedDatasources=true)
- [Gluzdov V16, 0.464, exact version](https://www.kaggle.com/code/dmitriigluzdov/casmi-26-the-data-behind-spectra-to-structures?scriptVersionId=360635689)
- [Gluzdov V17, twenty-parent experiment, unscored](https://www.kaggle.com/code/dmitriigluzdov/casmi-26-the-data-behind-spectra-to-structures?scriptVersionId=360784035)
- [Kino Lutor's parent-count discussion](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/750241)
- [Flexonafft V47, 0.462](https://www.kaggle.com/code/flexonafft/casmi26-closing-the-evidence-gap?scriptVersionId=360486019)
- [Flexonafft V49 multi-energy proxy experiment, unscored](https://www.kaggle.com/code/flexonafft/casmi26-closing-the-evidence-gap?scriptVersionId=360740328)
- [Public identity-disjoint V1 validation split](https://www.kaggle.com/datasets/prvsiyan/casmi26-v6-checkpoint-disjoint-ranker-split/versions/1)
- [Samar Talwar's MassBank harmonized library, V1](https://www.kaggle.com/datasets/samartalwar/casmi-2026-spectral-library-massbankharmonized)
- [Official CASMI data description and scoring contract](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/data)
