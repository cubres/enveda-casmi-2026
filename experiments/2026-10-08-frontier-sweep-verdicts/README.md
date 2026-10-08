# Frontier sweep verdicts and the duplicate-key audit (2026-10-08)

**Frontier.** The robust public frontier is **0.423**: the same notebook scores 0.428 / 0.423 / 0.423 / 0.419 under four owners. It rests on an engine whose assets are non-commercial, which we do not use. The leaderboard spans #1 0.481 to #100 0.432. The host changed the metric to RemoveStereochemistry (retroactive) and is rerunning every submission on corrected test data, so our 0.340 incumbent will be rescored.

**Kept levers.**
1. GLACIER-only forward weights (F1), measured against the **rescored** incumbent.
2. Duplicate-key hygiene in the top 25.
3. Our own second fingerprint list, fused by reciprocal rank.

**Dropped levers.** A PubChem join into our ranker; a MetFrag-style gap re-score (our ranker already has a fragmentation feature); an in-domain forward scorer, unless the second-list experiment shows the ranker is the bottleneck.

**F1 rule, frozen before the rescored values are read.**
- R = mean of the rescored incumbent rows (56824628, 56859903).
- **Adopt** if the mean of the two F1 draws (56953547, 56956461) is ≥ R + 0.008 and neither draw is below R.
- **Reject** if the mean is ≤ R + 0.001.
- Otherwise the result is inconclusive and we keep the incumbent.

**Duplicate-key audit** (`dup_key_audit.json`). This audit covers the commit-run CSV of the F1 bench version (400 queries, 9,608 guesses, sha256 `0d1cad26…`), with the scorer key (RemoveStereochemistry → RDKit 2026.03.3 tautomer canonicalisation → InChIKey[:14]).
- It found **0 duplicate-key slots** and 0 unparseable guesses, so the upper bound on MRR@25 lost to wasted slots is **0**.
- The pipeline already keeps one slot per scorer-distinct answer, including the PubChem tier, so no dedupe step is added.
- 34 queries have fewer than 25 guesses because their ±10 ppm window holds fewer candidates. That is not a lever, since window recall is already 1.000.
