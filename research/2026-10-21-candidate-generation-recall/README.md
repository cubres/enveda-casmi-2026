# CASMI candidate generation: test whether analogue parents create answers or only extra decoys

Captured 2026-10-21 14:29 UTC. This is an original research note based on public Kaggle pages. It contains no competition rows, derived features, copied candidate tables, model weights, or notebook source code.

This is a proposed experiment only: it reports no measured gain, new official score, or new dataset.

## Current verified position

The native public leaderboard shows a top score of **0.495** and prvsiyan at **0.456**, rank **374/3,740**. Kaggle says the public score covers about 31% of test molecules, so it is a partial and noisy view of final performance. The public code list sorted by score currently surfaces Gluzdov's data/method notebook at **0.464** and Flexonafft's notebook at **0.462**. The 0.495 leaderboard row is not linked to a public notebook in that view.

Our accepted Analog Propagation V43 result is 0.456. It remains terminal and must not be re-submitted. The current notebook-preservation workflow is still stopped, so this note makes no claim that V43's source or output was inspected or changed.

## Strong public lead: measure the loss between generation and ranking

Kino Lutor's public discussion reports a useful distinction on their held-out set: with suitable spectral analogues, their generator produced the answer for 100 of 130 database-absent molecules, but the full system placed the answer first for only 7 of those 130. The author says the then-default generator used six parent molecules and was testing 12, 20, and 30 on CPU. This is the author's reported evidence, not an independently reproduced result. The discussion itself asks whether more parents improve final identification or mostly add decoys, whether diverse parent selection helps, and whether errors occur at generation, filtering, or ranking.

The latest public [Gluzdov V17 page](https://www.kaggle.com/code/dmitriigluzdov/casmi-26-the-data-behind-spectra-to-structures?scriptVersionId=360784035) confirms its version-table scores: V15 is 0.456, V16 is 0.464, and V17 is unscored. The older V16-specific snapshot showed a dash for V16, but this updated V17 table resolves that discrepancy. V16's listed change is to keep GLACIER proxy scores where ICEBERG scores exist and jointly reorder proxy-covered same-formula candidates; V17 changes spectral-parent count from 6 to 20. The V15-to-V16 score difference is useful public version evidence, but not an independent reproduction or isolated causal ablation. Flexonafft V47 (scriptVersionId=360486019) shows 0.462; its later multi-energy proxy experiment remains unscored. These badges and author-reported measurements are evidence leads, not a reproducible 0.495 baseline.

The actionable hypothesis is that expanding and diversifying analogue parents can raise candidate recall, while the existing filters and ranker may discard the extra correct structures. We should measure each stage before tuning the ranker or blending more lists.

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
- [Official CASMI data description and scoring contract](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/data)
