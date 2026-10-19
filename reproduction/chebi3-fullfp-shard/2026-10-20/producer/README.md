# A bounded 4,096-row ChEBI three-star structure shard

This source packet specifies a deterministic, mass-balanced subset of public
ChEBI records for CPU fingerprint preparation. It does not train a model or
establish a score improvement. Root's driver and owning wrapper qualify real
inputs, numerical processing, canary measurements and completed outputs
separately. Previous broader Linux and Mac packets remain preserved.

## Selection contract

`selection_and_budget.py` uses only the Python standard library. The coordinator
supplies the complete original source-table rows in their original order and
the existing bank's raw keys. This module does not open files, deserialize
pickles, invoke RDKit or process actual input data during its pure tests.

Eligibility requires all of the following:

- `source == "ChEBI"` and `str(chebi_star) == "3"`.
- The original `inchikey14` raw key is absent from the old bank.
- Numeric, finite `monoisotopic_mass` is within **80–1,400 Da**, inclusive.
- Each eligible raw key occurs once; duplicates retain their earliest eligible
  original source-table position.

The independent metadata audit expects **8,895 eligible unique keys**. The
selector returns its actual count; the driver must check it against that frozen
expectation. Malformed row schemas or nonnumeric masses reject. Numeric
nonfinite/out-of-range masses are excluded and counted.

Divide the mass interval into 64 equal-width bins of 20.625 Da. Bins include
their left endpoint; the final bin also includes 1,400 Da. Sort each bin by
lexicographic raw key and original source index, then take ascending-bin
round-robin entries, skipping exhausted bins, until exactly **4,096** rows have
been selected. The first **64** selected rows form the deterministic canary.
This spreads selection across occupied mass bins; it cannot create occupancy
in a bin without eligible records.

```python
from selection_and_budget import select_shard

# Both arguments are supplied by the driver's separately verified input load.
selection = select_shard(source_rows, old_raw_keys)
assert selection["eligible_count"] == 8895
selected_source_indices = selection["selected_indices"]
canary_source_indices = selection["canary_indices"]
```

The result includes original source positions, eligible/selected/canary bin
counts and filter counts. Raw-key absence is **not** proof of metric-distinct or
canonical-group novelty. Preserve source identifiers, representations and
row joins; report subsequent metric/group checks separately.

## Budget forecast from this selected canary

The original 64 selected canary records are measured in eight-row chunks using
exactly two workers. Continue the same run; do not repeat the canary as a full
run prelude or substitute timings from an older broader experiment.

`forecast_budget(timings, completed_rows=..., elapsed_seconds=...)` requires
at least eight positive, finite chunk durations. It uses the last 128 timings
and the conservative duration `1.5 * max(nearest-rank p90, median)`. Remaining
work is `ceil(ceil((4096 - completed_rows) / 8) / 2)` parallel waves. Include all
input loading, proof checking, profiling and canary costs in elapsed time.

```python
from selection_and_budget import forecast_budget

decision = forecast_budget(
    measured_selected_shard_chunk_seconds,
    completed_rows=completed_count,
    elapsed_seconds=all_driver_elapsed_seconds,
)
if not decision["passes"]:
    raise RuntimeError("remaining work does not fit the bounded driver")
```

The forecast passes only when **elapsed + remaining compute + 120 seconds for
I/O < 1,760 seconds**. The owning wrapper retains its separate **1,800-second**
hard deadline. Rolling checks include completed rows and all elapsed time.
These are admission estimates, not a guarantee that work completes; the driver
and wrapper must still enforce their actual deadlines and process cleanup.

## Exact producer, input and identity bindings

The fingerprint producer is `build_external_fp_shard.py`, SHA256
`0d25816ad0de134d9c4a790530b15e3a89285332aef90f3252bc263ca48ed092`.
Its `EXPECTED_INPUTS` binds every existing required input byte hash. Public
source and dataset identities are recorded in `PUBLIC_SOURCE_BINDINGS.json`:

- Original 10,407-bit definition: Morgan radius 2 / 4,096 bits, Morgan radius 3 /
  4,096 bits, RDKit path `maxPath=6` / 2,048 bits, MACCS / 167 bits. Public
  `build_fps.py` Git blob `eeb07246ba893fbecf6e3ef587250ac9f0a83b94`.
- Frozen ordered 10,395-bit V6 mask SHA256
  `f771cb6aa87a418b06d9abfbdac0c1759040afb955b9dfa59e8932105a65bdc6`;
  MSB-first packing, five zero padding bits, 1,300 bytes per row. Never learn or
  recompute this mask from the new records or development labels.
- Exact metric helper SHA256
  `b4c0bbbafca0d821d872733d28f39518f41be53004970a9eeb725aef94a47b4f`.
- Exact extracted canonical-group helper SHA256
  `dd4c1750cf4816cdc3d880df837bdffec6a2beb62f3b676cc5ca663107ee042d`.
- Source structure dataset: public `sergiomalv/casmi-chebi-lmsd-structures` V1,
  ID 12431882. Old-bank/mask input dataset:
  `prvsiyan/casmi26-full-fingerprint-inputs` V1, ID 12350648.

The pinned numerical runtime is **Python 3.12.14, NumPy 2.2.6, RDKit
2026.03.3** (distribution version `2026.3.3`). I/O and resource monitoring
also pin **PyArrow 25.0.0** and **psutil 7.2.2**, as listed in
`requirements.txt`. An earlier completed 512-row numerical proof is reusable only for
its verified bit-definition claim when producer bytes, all mask/input byte
pins, source definition and numerical runtime match exactly. It does not
qualify this subset's timing, canonical-group novelty, metric coverage or
completed output. New canonical-helper versions must be pinned and qualified
independently; old broader timing estimates do not admit this run.

## Pure synthetic checks

```sh
python -B -m unittest -v test_selection_and_budget.py
python -B -m unittest -v test_owned_chebi3_admission.py
```

These tests use invented metadata and durations. They check mass-bin edges,
deterministic ordering, source joins, filtering/deduplication, occupied-bin
balance, rolling timing windows, strict deadlines and invalid-input rejection.
They do not read molecular datasets or execute fingerprints, models or assays.

Data terms are scoped in `DATA-LICENSE.md`; original source code uses
`LICENSE-SOURCE`. No PubChemLite mirror is included. The previously stopped
third-party notebook review remains stopped and is not a prerequisite bypass.

## Owned execution and diagnostic scope

Only `run_owned_chebi3_shard.py` may start the numerical driver. It binds the
complete source manifest, creates an exclusive run directory and consumes the
attempt before spawning one owned process group. The coordinator observes that
same group through terminal cleanup. A failed or ambiguous consumed run is not
automatically retried. Budget: 1,800 wall seconds, 3,600 aggregate CPU seconds,
4 GiB sampled aggregate RSS and 512 MiB owned output. macOS has no hard core
affinity here; two chemistry workers plus single numerical threads are an
explicit process configuration, with aggregate CPU time also monitored.

The 64 selected canary rows are instrumented in an initial two-worker pool.
After that pool fully closes, a fresh two-worker pool computes the same rows
with the byte-identical original producer. Every fingerprint byte, exact mass,
raw key and canonical-group digest must match the instrumentation. Only the
original producer supplies stored fingerprints and the chunk timings that
admit continuation. Thus the diagnostic pool cannot warm the original
producer's metric cache. This repeats the selected 64 rows for a timing
comparison, not a score assay or a repetition of the earlier 512-row proof.

Per-row timing separates parsing, each fingerprint family, mask/packing,
mass/raw InChIKey, unchanged metric canonicalization and group hashing. Phase
wall times include input verification, proof binding, metadata selection,
both worker pools, disk reloads and output hashing. All elapsed time counts
against admission. The 120-second I/O reserve remains mandatory; timeout,
numeric mismatch or rejected forecast stops the job without admitting the
remaining 4,032 records. A successful driver receipt is provisional until the
wrapper confirms child exit zero, clean owned process group, unchanged source
and actual resource bounds. Publication and any model use are separate gates.
