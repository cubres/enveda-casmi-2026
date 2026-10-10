# Lessons from the Enveda CASMI 2026 campaign

Each lesson gives the situation, the rule adopted, the evidence (ledger rows by UTC time, or campaign notes) and how it was checked. Snapshot as of 2026-10-10.

## 1. Replicates of a deterministic pipeline add no test-sampling information

- Situation: two F1 draws from different notebook versions both scored 0.344. The V6 composition scored 0.340 three times, and the exact redraw reproduced 0.340.
- Rule: one official draw per arm. Replicates only check reproduction; they do not shrink the noise.
- Evidence: ledger 2026-10-08 17:04:08 and 20:17:33 UTC; plan addendum 17:05 UTC.
- Checked: the tallies match across the ledger. Caveat: an earlier verification pass cites same-notebook submissions that scored 0.292 and 0.298, and same-code runs at 0.335 and 0.328, with an unseeded fit. "Exact" describes these rows only.

## 2. Name the decision reference as a measurement you will have, and do not re-specify it after the draws

- Situation: the F1 reference moved from the absolute incumbent (0.340, written 10:40 UTC) to the rescored V6 rows (15:50 UTC), then to a fresh redraw (17:10 UTC, after both F1 draws were scored). The thresholds stayed the same.
- Rule: name the reference rows before the first draw. If the reference must change, write the change down before the new reference is measured, and disclose it.
- Evidence: next-experiment note, section 3; plan addenda 15:50 and 17:10 UTC; ledger 2026-10-08 17:04:08 UTC.
- Checked: all three versions give the same verdict at an F1 mean of 0.344 and R of 0.340, because each sets bounds as offsets from R. The late change is disclosed in the state document.

## 3. Inconclusive is the right outcome when the effect is below one resolvable step

- Situation: the F1 mean was 0.344 against R of 0.340. One public molecule is worth about 0.0076, and the adopt bound was +0.008.
- Rule: between the bands, keep the incumbent, spend no third slot, and report the result as inconclusive, not as a win or a loss.
- Evidence: ledger 2026-10-08 20:17:33 UTC.
- Checked: the arithmetic (the difference is about half a molecule).

## 4. A check that passes on the visible file cannot test a lever whose gate is closed there

- Situation: every visible molecule is a library hit (lib_max at least 0.9), so the forward stage and the second list are gated off there. The visible CSV matched V6 by construction. In the CPU arm, the second list fired on 0 of 400 visible molecules.
- Rule: use the visible CSV only as a fidelity check of the code path. Record that it is uninformative for any arm whose gate is closed on it.
- Evidence: plan addendum 2026-10-08 17:10 UTC; ledger 2026-10-08 17:23:45 UTC and 2026-10-09 19:22:59 UTC.
- Checked: the CPU arm's gate count (0 of 400) and the visible-CSV digest match.

## 5. A different host can change a deterministic pipeline's output; compare only against a reference that reproduces on that host

- Situation: the CPU arm (V21) was held on an inherited check that the visible CSV equals V6's. On the CPU host, V6's visible output differed on 330 of 400 rows (ranks 2 to 25); top-1 matched on all 400.
- Rule: compare a CPU arm to a reference only where the reference reproduces on the same host class. Otherwise a band of plus or minus 0.008 is inconclusive. The GPU arm is the deciding draw.
- Evidence: ledger 2026-10-09 18:00:46 and 18:15:18 UTC; ledger 2026-10-09 22:15:08 UTC (CPU arm 0.335, inside the band, neither credited nor debited).
- Checked: V22's replacement checks were tested on V21's actual outputs (52 of 52 tests); the commit passed 14 of 14 checks.

## 6. A gate built on training-library answers overstates the gain; pre-register a falsifier on inputs known at test time

- Situation: the second list's class-2 gate was +0.0155 on 988 structures with MRRs of 0.85 to 0.94, against a hidden-test level of about 0.34. The gain was +0.0173 on Enveda-180 and +0.0113 elsewhere, and -0.023 on the qTof subset (n = 24).
- Rule: define falsifier slices from inputs the pipeline sees at test time (top probability, best analog similarity, library match), never from the outcome. Pre-register the protocol with a timestamp before scoring. Treat the gate effect as an upper guide.
- Evidence: plan entries 2026-10-09 19:00 and 22:45 UTC; ledger 2026-10-09 22:39:55 UTC.
- Checked: the CPU re-run reproduced the gate of record exactly. The falsifier slices are small (n from 38 to 142) and their intervals cross zero, so it shows only that the gain did not vanish.

## 7. Check the names a notebook resolves from attached datasets before the first push

- Situation: a candidate's fingerprint file had a shorter path than the file the existing lookup needed, so a shortest-match lookup would have loaded the wrong bit index. It was caught offline before any push.
- Rule: list the dataset-mounted files a lookup can match, and test it against a replica of the real mount listing in each mount layout. Add a guard that leaves existing inputs unchanged.
- Evidence: ledger 2026-10-08 22:11:09 and 22:12:34 UTC; plan entry 22:15 UTC.
- Checked: the bug reproduced without the guard. With it, the lookup matched the old lookup on 192 names, and 12 of 12 tests passed per arm.

## 8. A dataset's licence verdict must be on record before the dataset is published or mounted

- Situation: the forward-reference dataset was published at 12:05 UTC on 2026-10-08 under the licence "Other (terms in description)", and a public notebook mounted it at 12:23 UTC. An NVIDIA-wheel flag went to the owner at 19:37:55 UTC. Two train-derived datasets attached to the live public notebook were relabelled from CC0 to CC BY-NC-SA 4.0 at 22:26:38 UTC.
- Rule: a verdict and any permission record come before publication and before a public notebook mounts the dataset. A label on train-derived data is not a default.
- Evidence: ledger 2026-10-08 11:55:21 (audit requested), 12:05:27 (published), 12:23:49 (mounted), 19:37:55 (flag) and 22:26:38 UTC (relabel).
- Checked: a verification pass found no verdict or permission record in the audit folder. The wheel list (71 entries, 13 NVIDIA proprietary) was read from the audit output. The question was still open at the snapshot.

## 9. Keep Kaggle-side ERROR rows in the table, and separate platform errors from runner defects

- Situation: three official rows from 2026-10-06 (56882879, 56883185, 56883630) are ERROR with the platform message "A system error" and no score. Separately, a bench run ended ERROR after 588 s because the runner executed a numba-cached cell under a pseudo-filename. The science was not at fault.
- Rule: report ERROR rows in the official table with no score. Diagnose each ERROR from its run log before drawing any inference. Fix runner defects by writing cells to disk, then retest.
- Evidence: ledger inventory at 2026-10-08 09:46 UTC; ledger 2026-10-08 10:59 and 11:06 UTC; next-experiment note, section 7.
- Checked: the runner defect was read from the log at 11.7 s in one cell. The rebuilt version passed 61 of 61 tests and a dry run. The cause of the three platform errors is not recorded.

## 10. Gate thresholds must be reachable by the expected effect; compute pass probabilities before the run

- Situation: an offline gate required a change of at least +0.005 with a positive lower bound, while the lever's own expected range was 0 to +0.004 (central +0.001). A verification pass put the pass probability at 0.126 for a true +0.002 and 0.259 for +0.004 (SE 0.004). Another gate, at +0.02, had a pass probability of 0.016 for a true +0.005.
- Rule: set the threshold from the expected effect and a stated SE, compute pass probabilities for a few true effects, and correct for the number of arms tried.
- Evidence: strategy document, section 7 (verification figures, labelled as inferences).
- Checked: a second verification pass reproduced the first pass's calculations within Monte Carlo error. The SE of 0.004 is an assumption; the notes say it was not measured.

## 11. An audit that passes on the commit CSV covers that CSV, not the hidden score

- Situation: the duplicate-key audit found 0 duplicate slots and 0 unparseable guesses in the F1 commit CSV (400 queries, 9,608 guesses). The metric-key audit found 902 stereo-marked guesses, and stereo stripping changed no keys. The hidden rerun CSV cannot be observed.
- Rule: record such audits as preconditions for the commit output, and state what they do not cover.
- Evidence: plan entry 2026-10-08 15:50 UTC (duplicate keys); frontier notes, 15:00 to 15:20 UTC (metric key).
- Checked: the key chain (stereo removal, tautomer canonicalisation, 14-character InChIKey) was run with a pinned RDKit. The result covers the commit CSV only.
