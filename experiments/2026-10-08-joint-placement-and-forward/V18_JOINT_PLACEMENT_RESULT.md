# V18 result: fixed vs joint placement of PubChem-tier proposals

Written 2026-10-08 ~10:35 UTC by the Enveda workstream (Claude). Diagnostic evidence only. It is not an official
score, not held-out, and no submission came from it.

## What ran

- Notebook `prvsiyan/zz-gpuchk-844231` Version 18. CPU, private, launched 2026-10-07 22:52:55 UTC, run status COMPLETE.
  The run took 1,164.6 s (owned supervisor 1,173.0 s; deadline 7,130 s; TERM/KILL teardown proven; nothing left running).
- The receipts are in `../enveda_v18_outputs/enveda_joint_placement_oct7_v3/`. All 10 sha256 values match the fetch
  receipt `fetch_receipt_v18_20261008T094827Z.json`. I recomputed them locally on 2026-10-08.
- The panel is 16 query groups from the public Enveda-180 Zenodo release (CC BY 4.0, DOI 10.5281/zenodo.21346580).
  These groups were already exposed in earlier research (`prior_public_exposure: true`). Model pretraining overlap
  is `UNKNOWN`.
- Both arms take the same V6 engine, the same 8 HistGBM rankers (sha `463a8976…`) and the same frozen PubChem tier
  slate. Popularity is ON in both; forward and second list are OFF in both. So **this is not the V6 composition**,
  which ran with forward ON.
  - *fixed* = the V6 `slot_merge`. Tier items go to slots (4,8,12,16,20), or to (2,4,6,8,10) when the tier's best
    f·z beats the pool's best by more than `PC_MARGIN` = 300.
  - *joint* = the tier proposals are appended to the pool. The 31 features are recomputed over the union and
    everything is re-ranked by the same 8 rankers. No slots and no cap apply.
- The rankings were sealed before the truth was parsed (`sealed_before_truth: true`, sealed at monotonic 6260.203971 s,
  truth parsed at 6260.203973 s).

## What it measured

| | fixed | joint |
|---|---|---|
| MRR@25 over 16 groups | **0.9417** | 0.9375 |
| Mean paired delta | | −0.0042 |
| Groups with the library gate open (tier present) | 2 | 2 |
| Groups whose list changed | — | 2 |
| Groups improved / unchanged / worse | — | 0 / 15 / 1 |

14 of the 16 groups have `lib_max ≥ 0.90`. On those the gate is closed, and the two arms are byte-identical
(all 14 have reciprocal rank 1.0 in both arms). So the experiment had **two informative queries**, and it cannot
detect a gain or a loss smaller than about one query in 16.

## The lost query, and what caused it

Query hashes only. Analysis: `tools/v18_attribution.py` → `v18_attribution.json`. Tier items can be identified
exactly. PubChem SMILES arrive in PubChem's own non-RDKit-canonical (Kekulé) form, while every pool SMILES is
RDKit-canonical, and the non-canonical positions in the fixed arm coincide exactly with the slot sets.

| Query (sha256[:12]) | fixed slots used | tier items in fixed top 25 | tier items in joint top 25 | pool items left in joint | truth (fixed → joint) |
|---|---|---|---|---|---|
| `7bf6778e1ac7` | normal (4,8,12,16,20) | 5 | **18** | 7 | rank 1 → rank 1 (unaffected) |
| `ba2e2be595b4` | strong (2,4,6,8,10) | 5 | **21** | 4 | rank 15 → **absent** (RR 0.067 → 0) |

The loss in `ba2e2be595b4` happened like this:

1. The true structure is a **pool** candidate (COCONUT/train) at pool rank 10. Five strong-slot tier items sat above it.
2. In the joint arm, the 8 rankers scored the PubChem proposals above nearly every pool candidate. Tier items took
   21 of the 25 positions, and only pool items that ranked 1, 6, 8 and 9 under fixed placement stayed.
3. Recomputing the rank-normalised features over the union also reshuffled the pool items among themselves. Pool
   items from below the fixed top 25 entered the joint list in `7bf6778e1ac7`.

So the change that caused the loss is **removing the slot cap and letting the ranker score the PubChem slate**, not
the gate. The gate was identical in both arms by construction. This is the same mechanism as our September PubChem
pool expansion (official 0.205 against 0.335). The ranker's analog-Tanimoto features reward near-duplicates of the
spectral analogs, and a large isomer set supplies many of them. Fixed slots exist to cap exactly that exposure. The
strong-slot choice for this query (the tier's best f·z beat the pool's best by more than 300) shows the same signal
from the other side: the PubChem slate looked better than the pool to the fingerprint model, and the ranker
amplified that.

## Context the diagnostic cannot settle

The public notebook `huseyinemreaksoy/casmi26-v4n-fusion-pubchem-on-public-0-421` reports that a "PubChem join"
moved its score from 0.409 to 0.420 [R, single submissions]. The join hands PubChem-only proposals to the main
ranker. It runs on a different main engine (ahmedberatozer v4n, LightGBM over 160 features), caps the joined
proposals (`PC_JOIN_N=50`) and gates more strictly (`PC_JOIN_MAX_LIB=0.7`). That is evidence about *their* ranker,
not ours. Our ranker was never trained with PubChem decoys in its groups, and V18 shows how it treats them.

## Verdict

**Drop joint placement for our engine. Keep the fixed slots.** The decision rests on mechanism, not on −0.004:

- One of the two informative queries lost its answer, and the other was saved only because its truth was already at
  rank 1.
- In both queries the joint arm gave 18–21 of the 25 slots to PubChem. That is the known failure mode, and it is
  measured here directly.
- No version of this experiment could produce selection evidence on this panel: 14 of 16 groups are gate-closed
  library hits, and the panel was already exposed.

Any future join should be a **capped** variant: at most K ≤ 3 PubChem proposals scored by the ranker, gate
`lib_max < 0.7`. It must be predeclared as an official A/B with replicates. I do not recommend it as the next
candidate (see `NEXT_EXPERIMENT.md`).
