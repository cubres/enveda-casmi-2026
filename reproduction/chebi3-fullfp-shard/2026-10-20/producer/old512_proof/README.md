# Distinct macOS V6 fingerprint integrity/resource canary

**Source-only; root has not executed the chemistry canary.** This adapter runs
exactly 512 old-bank structures and 512 ChEBI/LMSD structures, then stops. It
cannot continue to the full shard and cannot train, load or execute a model,
score an assay, inspect hidden test data, launch a notebook or publish a dataset.
The separately reviewed Linux gated-full packet remains unchanged.

Inputs, fingerprint definition, mask SHA, RDKit2026.03.3, MSB-first packing,
mass tolerance and canonical-group helpers are identical to the Linux source.
The exact frozen builder is imported as a library; its `main`/full implementation
is never called. Input hashes are checked before all data deserialization and
again after both canaries. Old bank FP/mass arrays are read-only mmaps. The
external table is loaded only after all 512 old fingerprints match bit-for-bit.
Both chemistry stages require exactly 512 distinct jobs. No comparison or
checksum is relaxed on failure.

Two spawn chemistry workers run with one numerical thread each. Arrow CPU/I/O
thread counts are one and Parquet reading disables multithreaded decoding.
macOS has no supported CPU affinity API here: this is explicitly a two-worker
and aggregate CPU-time budget, not a hard two-core-binding claim. The owned
process-group wrapper limits 300s wall, 600 aggregate CPU-seconds, sampled
summed RSS4GiB and output64MiB. The canary has a 240s inner deadline; final
input rehash and cleanup must also fit. RSS is sampled every0.1s, not a cgroup
allocation guarantee. Root must first confirm its other two-CPU job is terminal.

The new512 files are saved and reloaded exactly, including Parquet source joins.
The frozen mask is copied byte-for-byte. The source table's actual source/star
counts are reported because its card describes2/3-star but stats lists1/2/3.
No full-bank novelty or hidden-answer coverage is inferred from this canary.
The full-size throughput forecast is informational for this exact Mac runtime;
it does not qualify a future Kaggle/Linux full job and never triggers one.

## Public input acquisition

`DOWNLOAD_PLAN.json` lists all seven exact public V1 input byte/SHA pins.
All four old-bank files already exist in root's verified historical local cache;
their now-public dataset identity is not changed by a historical folder name.
Use that cache directly read-only. The three external source files (5,410,581B)
were already acquired and independently rights-reviewed. No ~1GB copy or download
is needed. No download is performed by this adapter.

The root-only operational `ROOT_RUN_RECIPE.json` supplies absolute cache/run
paths and the exact source-manifest hash. It is not a public dataset payload.

## One-attempt machine protocol

- Root dispatches the exact recipe only if the per-run directory does not exist.
- The wrapper creates that directory exclusively, then writes `ADMISSION.json`
  and `ATTEMPT_CONSUMED.json` before starting its one owned child.
- `CHILD_HANDLE.json` records the same child PID/process group to observe until
  terminal. An observation timeout is not a reason to restart.
- `RESULT.json` is the terminal machine result. Success requires status
  `COMPLETE_MAC_CANARY_ONLY`, child0, exact512/512/no-full child receipt, clean
  process group and every resource gate. `COMPLETE.json` duplicates that result.
- Any failure creates `STOPPED_UNPROMOTABLE.json`; all files remain. An existing
  directory, consumed marker, failed result or ambiguous live state is never
  reset or automatically retried by this adapter.
- No chemistry/old/new passing claim exists until root inspects that exact
  completed result and independent exact-output review.

Licenses remain component-specific: original ChEBI/LMSD CC BY4.0 with unchanged
source attribution, existing separate V6-mask terms, and Apache2.0 for new source.
See `DATA-LICENSE.md`. PubChemLite is not included.
