# Enveda frontier, 2026-10-08

This snapshot was taken 10:08–10:20 UTC by the Enveda workstream. Everything was read-only: the API listing, a
logged-out page read, and source pulls. No model or weight payload was downloaded.

Labels: [V] verified here; [R] reported by another author (their own single submission); [O] our official row.

## Sources

- `frontier_20261008/kernels_list_raw.json`: `kernels_list(competition=…, sort_by='scoreDescending' | 'voteCount',
  page_size=50)`, two pages each, 100 rows per sort. The API returns no score field (`ApiKernelMetadata` has only
  `ref`, `title`, `author`, `lastRunTime` and `totalVotes`). The scores therefore come from the public Code tab.
- `frontier_20261008/public_scorecard_20261008T1015Z.tsv` (181 scored notebooks) and
  `public_leaderboard_top49_20261008T1018Z.txt` (2,773 teams).
- `frontier_pull_20261008T100838Z/<owner>__<slug>/`: 11 notebooks pulled with `kernels_pull` (latest version plus
  metadata). Hashes are in `pull_receipt.json`; the scan output is `frontier_20261008/frontier_scan.json`.
- Tools (all text-only, all run with `-I`): `tools/frontier_scan.py`, `tools/nb_similarity.py`, `tools/nb_diff.py`,
  `tools/nb_cells.py`.
- Licences: `frontier_20261008/dataset_licences_raw.json` and `dataset_meta/` (dataset-metadata.json only).

## Leaderboard context [V]

- LB #1 0.481, #2 0.466, #3 0.459, #10 0.443, #49 0.433. 2,773 teams.
- The best public notebook scores 0.428, which would rank about 60–70.
- Our best is 0.340 [O] (V6 of the private worker, twice). The public baseline notebook shows 0.335.
- **The noise floor is measured.** `rajrajak99/casmi26-apex-v180-sovereign-titan` (0.428) and `lszlst/casmi26-b429`
  (0.423) are **byte-identical files** (`cmp` equal) and scored 0.005 apart. Differences below about 0.01 between
  notebooks carry no information.

## Top public notebooks (score order, plus the most-voted)

All 11 run on a T4 GPU with internet off. "Ours" means the `prvsiyan/*` datasets they mount.

| # | Ref | Public | Votes | Last run (UTC) | Ours mounted | What it runs / adds over the 0.415 base |
|---|---|---|---|---|---|---|
| 1 | rajrajak99/casmi26-apex-v180-sovereign-titan | 0.428 | 54 | 10-07 13:48 | fp-models-v2, ranker-features, coconut, chebi-lipidmaps | v4n ⊕ our engine (embedded "pv.py … copied verbatim"). Adds a 4-seed engine 2 with N_ANALOG 250, adduct reconciliation (10 ppm cluster snap), lib ≥ 0.9 and two-engine top-1 locks, formula diversification in ranks ≥ 7, μ_pool 0.25, GLACIER-only final re-rank, and DreaMS (hengck23) attached |
| = | lszlst/casmi26-b429 | 0.423 | 0 | 10-08 04:34 | same | identical file to #1 |
| 2 | bobthebot369/enveda-casmi-2026-v18-sovereign-zenith | 0.425 | 99 | 10-05 22:49 | same 4 | the 0.421 architecture plus GLACIER only on [M+H]+ ("+0.009" [R]), dual PubChem promotion (S > 6 and pop ≥ 5, or rel > 250), library lock, and a DreaMS tail channel |
| 3 | nursrijan/enveda-casmi-2026-w-sovereign-zenith | 0.425 | 21 | 10-05 | same | copy of #2 (5 differing lines) |
| 4 | ghazarosbarseghyan91/enveda-casmi-2026-v19-clean-fusion | 0.425 | 7 | 10-07 10:03 | same | #2 plus adduct reconciliation, clean-spectrum entropy on engine 2, a promotion veto, GLACIER on the fused list, a formula cap in ranks 8–25, and DreaMS Enveda-180 cosine at even ranks ≥ 8 |
| 5 | huseyinemreaksoy/casmi26-v4n-fusion-pubchem-on-public-0-421 | 0.421 | 46 | 10-05 22:51 | same 4 | **published ablation ladder** [R]: 0.399 reference → μ_pool 0.15 + fragment re-score where ICEBERG is silent 0.404 → forward off for library hits 0.404 → μ 0.25 0.409 → **PubChem join** (PubChem-only proposals ranked by the v4n ranker, `PC_JOIN_N=50`, `PC_JOIN_MAX_LIB=0.7`) **0.420** |
| 6 | huaiansun/casmi26-opt-d-gpu-fusion | 0.421 | 2 | 10-06 | fp-models-v2, ranker-features, coconut | config overrides of #5 (`FP_BANK ens`, `FUSE_SKIP_LIB 0.97`, …). States "Public Kaggle notebook code is Apache 2.0" and ships a SOURCE_ATTRIBUTION.md |
| 7 | flexonafft/casmi26-public-baseline-adaptation-experiments | 0.42 | 69 | 10-08 09:34 | same 4 | derivative of #2 / #5. Adds a "Top-1 evidence shield" (restores the pre-fusion top-1 when lib ≥ 0.9 or the two engines agree) |
| — | evgendvorkin/enveda-casmi-2026 (most voted) | 0.417 | 160 | 10-04 11:23 | same 4 | "Forensics Lab": v4n ⊕ our engine plus a LambdaRank "pair-tail" and FIORA mentions; `imranarif536/casmi26-v44-pairtail-locked-top1` (0.417, 75 votes) is 91% line-identical |
| — | wangpenghua/casmi26-v29-fusion-pop-glmh | 0.415 | 90 | 10-02 | same 4 | the 0.415 base of Oct 2 (BRIEF §3) |
| — | dmitriigluzdov/casmi-26-from-spectra-to-structures | 0.411 | 90 | 10-08 | chebi-lipidmaps only (the rest of ours is re-hosted inside his `…open-model-and-candidate-resources` bundle, incl. our `rank_train.npz`) | an attributed, documented re-implementation; own "Other" datasets |

**Lineage [V, line-set Jaccard].**

- `bobthebot369` v18 shares 0.57 of its lines with `wangpenghua` v29 and 0.71 with #1.
- #5 and #6 share 0.81.
- Every notebook above is the same two-engine design as on Oct 2. Engine 1 is **ahmedberatozer v4n** (FPNet,
  LightGBM over 160 features, derivative generation). Engine 2 is **our engine** (analog propagation, our two FP
  models, our ranker rows, COCONUT) plus megayak's CC0 rows, AFIX and ChEBI/LIPID MAPS. The two are fused by RRF
  `1/(3+r₁) + 0.6/(3+r₂)`.
- The rise since Oct 2 (0.415 → 0.425–0.428) comes from the PubChem join and from post-fusion list rules: locks,
  promotion, GLACIER-only, diversification, tails. The +0.005 at the top is inside the identical-file noise.

**Our assets in the frontier [V].** 10 of 11 notebooks mount `prvsiyan/casmi26-fp-models-v2`,
`casmi26-ranker-features` and `coconut-casmi26-candidates`, and 10 of 11 mount `chebi-lipidmaps-casmi26`
(CC BY-NC-SA). All 10 embed our public notebook's engine code as engine 2. The 11th
(`dmitriigluzdov/casmi-26-from-spectra-to-structures`) mounts only `chebi-lipidmaps-casmi26` and re-hosts the rest
of our files in its own bundle.

## Licences [V unless marked]

| Asset | Declared | Upstream terms | Usable by us? |
|---|---|---|---|
| Frontier notebook **code** | Apache 2.0 (Kaggle default for public notebooks; stated explicitly by huaiansun and dmitriigluzdov) | — | yes, with attribution. Ideas and code are fine; the problem is the *assets* below |
| ahmedberatozer/casmi26-v4b-models, -fpnet-full1, -v3-models, -v2-pool, -pubchem-tier | "Other" | own text: "derived from the Enveda CASMI26 competition training data … Use under the respective source licenses (non-commercial, with attribution)". Training code unpublished | **no** (rights policy, BRIEF §5). v2-pool also redistributes training structures (rule 2.4(b)) |
| ahmedberatozer/casmi26-iceberg, -glacier | "Other" + LICENSE-NOTICE | ms-pred MIT weights; the packager's own runner and shims carry no licence | weights yes (host-approved). We already ship our own packaging: `prvsiyan/casmi26-forward-reference-stack` v2, pinned in V6 |
| hengck23/hengck23-dreams-enveda-casmi26 (5.7 GB) | MIT | DreaMS MIT | yes. Not yet evaluated by us; our DreaMS analog test was negative (memory, Sep 21) |
| megayak/casmi26-simulated-ranker-rows | CC0 | derived from competition data and our pipeline | yes, with credit |
| dmitriigluzdov/* (popularity prior, attributed v4g mirror, open bundle, fold-safe FPNet) | "Other" | own text: the mirror keeps v4g's non-commercial terms; the popularity prior is PubChem counts (free) plus LOTUS CC0 and NPAtlas CC BY 4.0 flags, row-aligned to v2-pool | popularity: usable with credit, but we have our own (`prvsiyan/pubchem-popularity-counts`, CC0). Mirror: **no** |
| ours: casmi26-fp-models-v2, ranker-features, pubchem-npformula-massindex | CC0 | trained or derived from competition data (CC BY-NC) | flag stands (BRIEF §5): CC0 on train-derived weights is a mis-declaration |
| ours: chebi-lipidmaps-casmi26 | CC BY-NC-SA 4.0 | ChEBI, LIPID MAPS | not in our runs (USE_BIO_DB False). 10 of 11 frontier notebooks still attach it |

**Is anything above our 0.340 reproducible with permitted assets?** Not with any public notebook as-is. Every
notebook at ≥ 0.40 needs the v4n engine assets (non-commercial, training code unpublished). Under our rights
policy, the permitted pieces are:

- our engine;
- ms-pred ICEBERG/GLACIER (MIT, our packaging);
- PubChem popularity and the PubChem tier (ours, CC0);
- megayak rows (CC0);
- DreaMS (MIT);
- Apache-2.0 notebook code: the join, promotion, locks and other list rules.

The frontier's own ablations attribute only about +0.03 of its score to those pieces on *their* base: popularity
+0.010, PubChem join +0.011, and GLACIER-only versus ICE+GLACIER up to +0.015. Applied to our 0.340, a plausible
fully-permitted ceiling is about **0.35–0.37**. Anything beyond that needs a stronger engine of our own (BRIEF §8).

## Gap table (BRIEF §4, updated)

Our official best is 0.340. The best public notebook is 0.428 (gap 0.088). LB #1 is 0.481 (gap 0.141).

| # | Piece | Frontier size [R] | Ours, measured [O] | Status for us |
|---|---|---|---|---|
| 1 | Base engine: v4n (FPNet 10,226 bits, 160 features, LightGBM, generation) vs ours | v4n alone 0.384 vs our S0 0.331 → **≈ +0.05**, the dominant piece | — | **not reachable** with permitted assets. Needs our own stronger FP model and ranker (12–24 GPU-h, BRIEF §8 alt. 1) |
| 2 | RRF of two independent engines | 0.384 → 0.399 (+0.015) | not run (AP-2 stage 5) | a second list of *ours* shares all channels; expected +0.002 |
| 3 | Pool popularity prior | μ 0.15: +0.005, μ 0.25: +0.010 | **+0.008** (S0 0.331 → pop 0.339; μ 0.20) | done; μ 0.25 is a candidate (+0.002 expected) |
| 4 | PubChem-only channel | gated fixed slots +0.004 (Oct 2); **join into the ranker 0.409 → 0.420** | fixed-slot tier +0.000 alone, +0.001 on pop (0.339 → 0.340) | V18 shows our ranker floods 18–21/25 slots when joined; a capped join is unproven |
| 5 | Forward isomer check | ICEBERG + GLACIER ≈ +0.026; **GLACIER-only vs ICE+GL +0.015** (b420 0.402 → b421 0.417) | forward alone **+0.007** (0.338); on pop+tier **+0.000** (V6 0.340 ×2) | **F1 = GLACIER-only, prepared** (NEXT_EXPERIMENT.md) |
| 6 | Post-fusion list rules (locks, promotion, diversification, DreaMS tail, adduct reconciliation) | 0.420 → 0.425–0.428 | — | below the identical-file noise (0.005). Not worth a slot alone |
| 7 | Top-3 teams (0.459–0.481) | unexplained by anything public | — | — |

**Bottom line.** The public frontier is still "their engine plus ours". What separates 0.34 from 0.42 is mostly an
engine we may not use, not a trick we lack. The best-evidenced permitted lever we have not yet run is GLACIER-only
forward weighting. After that, the realistic route upward is a stronger own engine, not further list surgery.
