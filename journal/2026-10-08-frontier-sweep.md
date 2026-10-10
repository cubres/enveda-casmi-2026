# Frontier sweep, 2026-10-08 (Enveda CASMI 2026)

Competition: Enveda CASMI 2026, molecule identification from mass spectra. Public, notebooks only, five submissions per day, deadline 2026-12-14.

Snapshot: the sweep ran 14:40 to 15:30 UTC on 2026-10-08, and an independent verification pass followed the same afternoon. Outcomes after that date are in the state document. Labels are defined in the README; [R] and [O] appear only in the plan notes (see the legend there).

## 1. Bottom line

- The public frontier had not moved in substance since the morning audit. The best displayed notebook scored 0.428 [V]. The same code, under four owners, scored 0.428, 0.423, 0.423 and 0.419 [V], and two of those files are byte-identical [V]. Differences below about 0.01 between notebooks carry no information.
- The frontier is one author's non-commercial engine fused with the campaign's own engine [V]. Every one-knob arm measured on that base came out flat or negative (single submissions [P]), including a tighter m/z tolerance, 12 retrained rankers, FIORA as a third forward model and an external library.
- The campaign's official best was 0.340 [O], the V6 composition, scored twice. The public card showed 0.335 at the sweep, with two F1 draws pending [V].
- About 0.05 of the gap to the displayed best is the non-commercial engine, which the campaign's rights policy excludes [V]. The verification's realistic ceiling on the campaign's own stack is 0.34 to 0.36 [I]. The sweep's sum of measured permitted levers gives +0.005 to +0.025, that is 0.345 to 0.365 [I].
- The host made three changes that affect scoring (section 4). The campaign's output was checked against the new metric key and is unaffected [V].

## 2. Where everyone stands

| Item | Score | Note |
|---|---|---|
| Leaderboard #1 | 0.481 | unchanged between 14:42 and 15:15 UTC [V] |
| Leaderboard #2, #3, #5, #10 | 0.466, 0.459, 0.452, 0.443 | same readings [V] |
| Leaderboard #30, #100 | 0.436, 0.432 | same readings [V] |
| Best displayed public notebook | 0.428 | [V] |
| Same code, four owners | mean 0.4233 (0.419 to 0.428) | [V] |
| Campaign official best | 0.340 | V6 composition, two draws [O] |
| Campaign public card | 0.335 | V33 draws pending at sweep [V] |
| Campaign engine alone (control) | 0.331 | [V] |

The public scorecard lists 290 scored notebooks [V].

## 3. Public notebooks

| Notebook (public slug) | Displayed score | What it adds over its parent |
|---|---|---|
| rajrajak99/casmi26-apex-v180-sovereign-titan | 0.428 | the non-commercial engine plus the campaign's engine, with list rules (locks, promotion, formula cap, a pool-popularity weight of 0.25) [V] |
| bobthebot369/enveda-casmi-2026-v18-sovereign-zenith | 0.425 | the 0.421 base with GLACIER-only forward weights on [M+H]+ and a promotion step [V] |
| goodjane/chem-v3-1, nursrijan/enveda-casmi-2026-w-sovereign-zenith | 0.425 | copies of the row above with small edits [V] |
| ghazarosbarseghyan91/enveda-casmi-2026-v19-clean-fusion | 0.425 | the row above plus adduct reconciliation and a formula cap [V] |
| rajrajak99/casmi26-apex-v185-sovereign-grandmaster | 0.424 | a stage-RRF re-sort of ranks 2 to 25; no gain on its base [V] |
| rajrajak99/casmi26-apex-v190-sovereign-zenith | 0.424 | v185 plus MetFrag-lite outside the GLACIER budget; 0.000 on its base [V] |
| lszlst/casmi26-b429 | 0.423 | byte-identical to the top notebook's file [V] |
| ahmedberatozer/casmi26-v6a-glonly-fusion | 0.423 | the engine author's own port of v180 without the DreaMS dataset [V] |
| huseyinemreaksoy/casmi26-v4n-fusion-pubchem-on-public-0-421 | 0.421 | a published ablation ladder; the PubChem join moved it from 0.409 to 0.420 [P] |
| evgendvorkin/enveda-casmi-2026 | 0.417 | the most-voted notebook (160 votes); 91 percent line-identical to another notebook [V] |

Lineage: engine 1 is the non-commercial v4n engine and engine 2 is the campaign's analog-propagation engine, fused by a weighted reciprocal-rank sum [V]. The rise from 0.415 (October 2) to 0.425 to 0.428 came from the PubChem join and list rules [V].

## 4. Host statements and licences

Paraphrased from the forum (topic numbers are public):

- The metric now removes stereochemistry before keying, applied retroactively (topic 746878) [V]. In the campaign's CSV, 902 of 9,608 guesses carry stereo marks, stripping stereo changes 0 keys, and there are 0 duplicate keys and 0 unparseable guesses [V].
- The hidden rerun data was corrected for an electron-mass error in some peaks, and every submission is being rerun on it (topic 746954) [V]. Neither change had shown on the leaderboard by 15:15 UTC [V].
- Models trained on the competition's training file, and redistributed artifacts derived from it, are stated to be fine (topic 745841). The same post says the compliance check can remove teams from the leaderboard entirely [V]. A participant's question about the non-commercial assets has no reply [V].
- Newer GNPS, MassBank and MoNA releases are allowed, including CC BY-SA records (topic 745228). NIST-derived data is not (topics 745832 and 744470) [V].
- No identifier overlap was found between the visible placeholder file and the rerun test (topic 745715) [V].

| Asset | Declared licence | Status for the campaign |
|---|---|---|
| Non-commercial engine assets (one author's v4b, v3, v2-pool, FPNet and pubchem-tier sets) | Other, non-commercial | not usable under the rights policy [V] |
| ICEBERG and GLACIER forward weights (ms-pred, MIT source) | Other, with a licence notice | weights usable; the campaign's own packaging is public, with an NVIDIA-wheel flag open [V] |
| FIORA OS and MIST | Other; source MIT, data CC BY 4.0 | usable only if repackaged from upstream [V] |
| Fold-safe FPNet training loop | Other; imports a non-commercial package | ideas only [V] |
| FRIGID checkpoints, CFM-ID 4 stock models, ISDB spectra | CC BY-NC upstream; METLIN-trained question | not eligible until the host answers [V] |
| Campaign's fingerprint pair and ranker features | CC0 label | flagged as train-derived; the label is a decision for the owner [V] |

## 5. Gap decomposition

| Step | Frontier [P, single submissions] | Campaign [V, official] |
|---|---|---|
| Base engine | non-commercial v4n alone 0.384 vs control 0.331: about 0.05, the main gap | not reachable with permitted assets [V] |
| Two-engine fusion | 0.384 to 0.399 (+0.015), between independent engines | no second list yet; the sweep estimated +0.002 to +0.008 for a list sharing the same channels, and the verification corrected that to 0 to +0.005 [I] |
| Popularity | weight 0.15 to 0.25: 0.404 to 0.409 | weight 0.20: +0.008 (0.331 to 0.339) [V] |
| PubChem-only candidates | join into ranker: 0.409 to 0.420 | fixed slots +0.001; uncapped join gave 18 to 21 of 25 slots to PubChem (V18) [V] |
| Forward check | GLACIER-only on fused list +0.015 (a code comment's pair, not one variable; see section 6) | ICE plus GLACIER +0.007 alone (one draw); +0.000 on top of popularity and tier [V] |
| Post-fusion list rules | 0.420 to 0.423 +/- 0.004 | inside the noise [V] |

## 6. What the verification changed

A separate verification pass challenged nine levers. Three survive, ranked: L1 (finish the GLACIER-only forward test), L7 (reference-library hygiene) and L3 (own second list). Six are rejected or parked: L2, L4, L5, L6, L8 and L9. No lever on the list closes the gap to 0.428 [V].

| Lever | Verdict | Corrected expected public gain | Main reason |
|---|---|---|---|
| L1 finish F1 (GLACIER-only) | keep, rank 1 | -0.003 to +0.006 (central +0.001) | pending; evidence confounded; forward is worth about 0 on top of popularity and tier [V] |
| L7 library hygiene | keep, rank 2 | 0 to +0.003 (central +0.001) | CPU only and reproducible; partly redundant with the existing instrument rule [V] |
| L3 own second list (RRF) | keep, conditional, rank 3 | 0 to +0.005 (central +0.002) | retrieval gains are not pipeline gains; a third view measured negative [V] |
| L2 capped PubChem join | no, rank 4 | -0.004 to +0.004 for K at most 3 (untested) | cited evidence is one submission on another ranker [V] |
| L8 configuration bundle | no, rank 5 | -0.002 to +0.003 | fails the sweep's own non-NP gate on the fold-safe table [V] |
| L6 MIST as independent view | no, rank 6 | -0.002 to +0.003 | no pilot; official evidence against extra views [V] |
| L9 newer reference spectra | no, rank 7 | 0 to +0.002 | the external merge measured 0 on one draw [V] |
| L4 gap-only isomer evidence | no, rank 8 | -0.002 to +0.002 | the same author's held-out gain (+0.023) was followed by a leaderboard change from 0.341 to 0.336 [P] |
| L5 in-domain forward scorer | no, parked, rank 9 | 0 to +0.008 (central +0.002), unmeasured | eight GPU-hours or TPU, no evidence yet [I] |

Corrections the verification made to the sweep (selected):

1. The GPU allowance was quoted as 75,600 s; the ledger uses 162,000 s, and the verification asked for reconciliation before any GPU plan [V].
2. L1 was costed at zero, but both F1 draws had already run at about 4,400 to 4,800 s each [V].
3. The +0.015 for GLACIER-only comes from a code comment comparing two runs that differ in more than one setting. Another author's ladder reports the opposite sign for ICEBERG on the main list (-0.013) [P].
4. The sweep's relative decision rule was written after the rescore was announced. The verification recommended keeping the absolute rule (adopt at 0.348, reject at 0.341) [V].
5. L2's cited step used another ranker and one submission; K at most 3 was never tested [V].
6. L3's +0.012 is retrieval MRR@25 on 4,096 structures, not pipeline MRR. A third fingerprint view scored 0.329 against 0.335 in the campaign's own rows, cited in the verification [V as cited].
7. L4's v190 scored 0.424, the same as v185 on its base, so the MetFrag addition is worth 0.000 there [V].
8. L8 fails the sweep's own non-NP gate: the fold-safe table gives -0.017 at popularity 0.15 and -0.072 at 0.25 [V].
9. The CFM-ID 4 approval rests on an assumption and conflicts with a host ruling on METLIN-derived weights, so the ISDB library is not clean [V].

Missing levers (none measured):

- M1: a spectrum-aggregation rule across a molecule's spectra, tested offline from one stored dump (0 to +0.004 [I]).
- M2: instrument-stratified ranker rows (0 to +0.005 [I]).
- M3: CFM-ID 4 as a negative-mode forward scorer; blocked until the host answers on METLIN-derived weights (0 to +0.005 [I]).

## 7. Predeclared rules, as written

Official gate (sweep section 6.2 and the campaign plan):

- two draws per arm;
- adopt if the mean is at least the incumbent plus 0.008 and neither draw is below the incumbent;
- reject if the mean is at most the incumbent plus 0.001;
- anything between is inconclusive: keep the incumbent and spend no third slot.

Local gates (sweep section 6.3):

- L1: re-read the two V6 rows after the rerun; apply the official gate to the rescored reference.
- L2: MRR on the PubChem-truth set rises by at least 0.02; control MRR falls by at most 0.005 (90 percent CI); injected rows take at most 3 slots per molecule on controls.
- L3: pipeline MRR change of at least +0.01 with a 90 percent lower bound above 0; neither stratum significantly negative.
- L4: pooled isomer-panel change of at least +0.03 with a 90 percent lower bound above 0; no library panel negative.
- L5: isomer-panel MRR over GLACIER of at least +0.02 in both strata.
- L6: fusion change of at least +0.01 with a lower bound above 0, in both strata.
- L7: class-2 pipeline change of at least +0.005, and class-1 loss at most 0.002.
- L8: natural-product stratum change of at least +0.005, and non-NP loss at most 0.003; never spend a slot on it alone.
- L9: at least 2,000 newly available structures before the L7 protocol is run.

The F1 reference that was actually applied, and how it was re-specified during the campaign, is in the state document.

## 8. Caveats

- Displayed notebook scores are each owner's best version, so there is selection bias. Most are single submissions [V].
- The corrected-data rerun shifts every row, including the campaign's own [V].
- Forum posts are claims [P]. Three licence questions were open at the sweep (topics 745072, 745615 and 746430). Asset licences were read from dataset descriptions and need upstream checks [V].
