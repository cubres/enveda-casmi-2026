# Next official candidate: F1 = V6 with GLACIER-only forward weights

Written 2026-10-08 ~10:40 UTC by the Enveda workstream. Prepared and tested offline. **Nothing has been pushed or
submitted.** The root coordinator executes the push and both submissions.

## 1. First, a correction to the brief

The brief said the forward arm "so far left OFF". In fact **forward was ON in V6**, the version that holds our best
score of 0.340 twice (rows 56824628 and 56859903). The evidence:

- `codex_enveda_composition_20261004/` source-switch receipt: `forward: true`.
- V6 cell 3: `CFG.FWD_WEIGHTS = {'iceberg': 0.5, 'glacier': 0.5}`, `FWD_BUDGET_S = 9400`.
- The push used T4 GPU.

Forward was OFF only in the V18 diagnostic.

Our measured forward ledger:

| Arm | Score | Change |
|---|---|---|
| S0 (control) | 0.331 | — |
| forward only (row 56818694) | 0.338 | +0.007 |
| pop + tier | 0.340 | — |
| pop + tier + forward (V6) | 0.340, 0.340 | +0.000 over pop + tier |

The attached runner (`fwd_runner.py` sha `622d576e…`, line 213) **already restricts GLACIER to [M+H]+**. ICEBERG
scores both [M+H]+ and [M+Na]+.

One more risk sits in V6. `ForwardService` disables itself silently on any error and returns `None`, so a forward
failure in a hidden rerun is invisible. The candidate below closes that gap on the commit run.

## 2. Choice

| Candidate (ours to run) | Evidence | Expected Δ public | Cost / risk |
|---|---|---|---|
| **F1: V6 with ICEBERG weight 0, GLACIER weight 1.0** | Single-variable frontier A/B: `lszlst` b420 with ICE+GLACIER scored 0.402, b421 with GLACIER only scored 0.417, i.e. **+0.015** [R, from the in-code comment of `rajrajak99/casmi26-apex-v180…`]. `bobthebot369` v18 reports "+0.009" for isolated GLACIER [R]. Ours: forward alone +0.007. | **+0.005** (range −0.005 to +0.015) | One line of V6. About 1.2 T4-h for the commit. Weights are MIT ms-pred in our own packaged dataset. |
| R: second-list RRF of our two FP generations (deployed pair vs the clean-split pair) | None direct. A third model of the same kind cost −0.006. The frontier's +0.015 comes from fusing two *independent* engines; ours would share every channel except the FP weights. | +0.002 | New code, about +60 min runtime, ranker/feature mismatch |
| J: capped PubChem join (K ≤ 3, gate `lib_max` < 0.7) | +0.011 on a different ranker [R]. V18 shows our ranker gives PubChem 18–21 of 25 slots. | −0.005 to +0.005 | New code |
| P: popularity μ 0.20 → 0.25 | μ 0.15 → 0.25 gave +0.005 on the frontier [R] | +0.002 | One line |
| M: megayak ranker rows (CC0) in a 0.88/0.12 two-ranker blend | +0.006 against a noise-high base [R] | +0.003 | Third-party data, new code |

F1 has the best expected gain per unit of risk. It is the frontier's best-supported forward configuration, it
touches nothing else, and it is falsifiable with two draws.

## 3. Pre-declared hypothesis and decision rule

**H1.** Replacing ICEBERG's half of the forward weight with GLACIER, with everything else byte-identical to V6
(engine, ranker 463a8976…, popularity μ 0.20, PubChem tier and slots, gate 0.90, POP_TOP 60, budget 9,400 s), raises
the public score.

- **Noise model.** Our V6 draws were 0.340 and 0.340. The pair family has sd 0.004. One public molecule moved to
  rank 1 is worth about 0.0076. An identical frontier file scored 0.428 and 0.423.
- **Plan.** Make two official draws of the same F1 version. They use 2 of the 5 daily slots and can share one day.
- **Adopt F1** as the new incumbent if the mean of the two draws is ≥ 0.348 (+0.008, about one molecule) and neither
  draw is below 0.340.
- **Reject** if the mean is ≤ 0.341. Keep V6, and record that ICEBERG-vs-GLACIER is not a lever for our stack.
- **In between** (0.342–0.347) is inconclusive. Do not spend a third slot. Keep V6, and carry F1 only as a component
  of a later composition that is itself tested with two draws.
- Exposed-panel or visible-test diagnostics are **not** used for selection. On the commit run the visible test opens
  no gate, so the visible CSV must be **identical** to V6's. That is a fidelity check, not evidence.

## 4. The candidate

| Item | Value |
|---|---|
| Path | `candidate_f1_20261008T103330Z/zz-gpuchk-844231.ipynb` |
| sha256 | `b5b5440cd5bda7b5fa768e84583c9f8ddf561086e36572e4b15a7ae138d20992` (888,386 bytes, below the 900,000-byte release limit; Kaggle refuses ≥ 1 MB) |
| Built from | fresh read-only pull `fresh_pull_20261008T100446Z/` (sha `9ea5b1bc…` = V18 canonical, status COMPLETE) and canonical V6 `codex_enveda_composition_20261004/push_evidence/push_zz-gpuchk-844231_20261004T115946Z/postpush/zz-gpuchk-844231.ipynb` (sha `92c4e53a…`) |
| Builder | `tools/build_f1_candidate.py` (asserts the source hashes and that the edit target is unique) → `BUILD_RECEIPT.json`, `f1_payload.json`, `f1_top_cell.py` |
| Cells | 67 = 1 new active cell (id `f1active`) + all 66 existing cells, byte-identical and in order. The JSON is serialised exactly like the server copy, so each old cell's bytes are unchanged. |
| Change | V6 cell 3, one line: `CFG.FWD_WEIGHTS = {'iceberg': 0.0, 'glacier': 1.0}`. The other 20 V6 code cells are byte-identical, and each matches the V18-pinned original bank. |
| Superseded | `candidate_f1_20261008T102930Z/` (first build; used `os.waitid`, which is not portable). Do not push it. |

**How the top cell works.** The steps run in this order:

1. **Turn off the old cells.** It installs an IPython cleanup input transformer keyed on the exact sha256 of the 37
   preserved code cells. Each of those cells then executes only `print('F1_SKIPPED_PRESERVED_CELL …')`. The cells
   are not modified, and the old V18 runner (cell 65) cannot re-run. The transformer is self-tested before anything
   long starts.
2. **Detect the mode.** A run is a scoring rerun if `KAGGLE_IS_COMPETITION_RERUN` is set, or if the test signature
   differs from the placeholder md5 `654e030e…`. I verified that md5 locally on the visible test.
3. **Check for a GPU.** It requires `nvidia-smi -L` to list a GPU and HOLDs otherwise, because the forward channel
   only runs on CUDA.
4. **Run the V6 code.** It decodes the sha-pinned zlib/base64 payload (21 V6 code cells plus a commit-only canary
   placed after V6 cell 30). It runs them in **one new session / process group** through
   `python f1_runner.py f1_payload.json`, with cwd `/kaggle/working/f1_run` and `MPLBACKEND=Agg`.
5. **Enforce the deadline.** The cap is 7,130 s on the commit run and 30,600 s on the scoring rerun, minus a 150 s
   reserve. The leader stays unreaped until its group is empty. TERM goes to the whole group, then KILL after 30 s.
   This happens on success too, so no forward-service or pool orphan survives.
6. **Validate the output.** It checks the exact columns, rows and order against `sample_submission.csv` and the ids
   against `test.parquet`. Every row must have 1–25 guesses, with no empty or repeated guess and no nulls, and every
   guess must parse in RDKit. V6's own metric-class check also stays. On the commit run only, the CSV sha256 must
   start with **`0d1cad26`** (V6's visible CSV).
7. **Require the canary on the commit run.** The canary starts a separate `ForwardService` on one real visible
   [M+H]+ spectrum and a same-formula pool group. It must report `cuda`, torch 2.6.0+cu124 and RDKit 2025.03.6, and
   return at least 2 finite GLACIER scores. The canary runs after `submission.csv` already exists, so it cannot change
   any list.
8. **Write the result.** It copies the CSV atomically to `/kaggle/working/submission.csv`, and writes
   `f1_run/F1_RUN_RECEIPT.json` whether the run passes or fails.

**Offline contract tests: 42/42 PASS.** The suite is `tests_f1/test_f1_contract.py` and the results are in
`tests_f1/runs_20261008T103444Z/RESULTS.json`. It covers:

- preservation (cells and bytes);
- payload binding and tamper refusal;
- the single-line diff;
- the real V6 `forward_fusion`: with ICEBERG weight 0, ICEBERG cannot move anything, while under the V6 weights it
  does;
- the canary against a fake forward package (PASS on `cuda`, FAIL on `cpu`);
- 13 end-to-end runs in a real IPython kernel (nbclient). These cover the commit and rerun PASS paths, all 37
  preserved cells stubbed, and the HOLD paths: canary fail, visible-CSV drift, a missing molecule, 26 guesses, a
  repeated guess, a payload error, no GPU, and a timeout that kills the group with no grandchild left. A success run
  also gets a TERM-ignoring orphan killed by TERM → KILL.

**What the tests cannot show.** No real V6 engine, model or forward model ran locally (no CUDA, and the competition
inputs differ). The Linux `/proc` branch of the process table is unit-tested only through its parser; macOS took the
`ps` branch. The Kaggle commit run is the integration test, and its hard gates make it fail closed.

## 5. What root does (in order)

1. **Push.** Run a fresh `safe_push` with `ref='prvsiyan/zz-gpuchk-844231'`, `expected={'id_no':135014612,
   'title':'zz gpuchk 844231','code_file':'zz-gpuchk-844231.ipynb'}`. Use **`overrides={'is_private': True,
   'enable_gpu': True, 'machine_shape': 'NvidiaTeslaT4'}`**.
   - GPU is demonstrably needed: `ForwardService.start` rejects anything but `cuda` + torch 2.6.0+cu124. With
     `{'is_private': True}` alone the server metadata is CPU, so F1 would HOLD on the GPU gate. Without that gate it
     would silently measure pop+tier only.
   - **Do not pass `timeout_seconds`.** A 7,200 s server cap might also bind the 9-hour scoring rerun (unverified).
     The top cell owns the commit cap.
   - The dry run passed: `push_evidence/push_zz-gpuchk-844231_20261008T103608Z/receipt.json`, `DRY_RUN_OK`. The
     identity triple matched, the server status was COMPLETE, the pre-push sha was `9ea5b1bc…`, the docker image is
     pinned to `37c64f7d…` (same as V6), and all 8 attachments are kept.
2. **Watch the commit run.** It should take about 3,515 s (V6's commit) plus the canary (≤ 1,200 s), well under
   7,130 s. GPU cost is about 1.3 h of the 14.2 h free; the quota resets on 10-10.
3. **Accept the commit only if all of these hold.** Fetch with
   `fetch_version_output.py prvsiyan/zz-gpuchk-844231 <V> 'f1_run/(F1_RUN_RECEIPT|F1_FORWARD_CANARY|composition_environment|composition_runtime_receipt)\.json$' <new dir>`:
   - the version status is COMPLETE;
   - `F1_RUN_RECEIPT.status == PASS_F1_SUBMISSION_WRITTEN`, every check is true, and `visible_csv_equals_v6` is true;
   - `forward_canary.status == PASS`, with `environment.device == 'cuda'` and `glacier_finite ≥ 2`;
   - `process.cleanup_proven` is true;
   - `composition_environment.switches.forward` is true.
4. **Submit two draws** of that version, each with one log line before and one after in `../LEDGER.md`. Suggested
   description: "F1: exact V6 composition, forward weights ICEBERG 0 / GLACIER 1.0 (GLACIER [M+H]+ only); single
   change; predeclared adopt if mean ≥ 0.348 over 2 draws".
5. **Apply §3.** Do not iterate on the public score beyond that rule.

## 6. If F1 is adopted, what comes next

The next candidates are F2 = F1 with pool popularity μ 0.25 (one line), then the AP-2 stage-5 second list. Each gets
its own predeclared two-draw rule. If F1 is rejected, ICEBERG-vs-GLACIER is closed for our stack and P/M go next.
None of these closes the 0.08 gap to the 0.42 public notebooks: that gap is their main engine (non-commercial
assets), as `FRONTIER_20261008.md` shows.
