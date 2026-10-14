# Connect arrays only after their contract is known

The library operates on plain in-memory NumPy arrays. It does not fetch data, deserialize models, compute fingerprints or normalize chemical identities. Start with the invented example; keep the real producer status `UNKNOWN` until the following evidence is independently established.

| Input or convention | Required contract |
|---|---|
| Neutral mass | Finite positive `float64` vector, sorted ascending; document units, precursor/adduct/charge conversion and ppm denominator separately |
| Row tokens | Unique nonempty strings, at most 128 characters; real tokens must use the competition's reviewed identity normalization |
| Packed rows | `uint8`, shape `(n, 277)`, same row permutation as masses and tokens |
| Physical join | Trusted manifest binds mass, metadata and fingerprint file hashes plus the row-token order digest |
| Generator | Exact implementation/version, molecular preprocessing and Morgan options; width alone is insufficient |
| Packing | Declared `big` or `little`; positions `0:2048`, `2049:2215` are active, positions `2048` and `2215` must be zero |
| Model output | Finite true-logit vector of shape `(2216,)`, exact target order and frozen spectrum-view aggregation |
| Eligibility | Current competition-use and redistribution terms reviewed independently; this package supplies no real training structures |

`EXTERNALLY_QUALIFIED` is a caller declaration, not a certification performed by the library. A correctly shaped but incorrectly paired array can pass shape checks. A digest computed from the wrong pairing does not repair it. Keep arrays unchanged after validation; returned fingerprint slices are views.

## First run: invented rows

Run this from `original/` in your NumPy environment:

```python
from synthetic_demo import make_synthetic_demo
from packed_window_lab import aligned_window, row_order_digest, score_window, topk_with_ties

masses, tokens, bits, packed, logits, contract = make_synthetic_demo("big")
interval, window_tokens, window_packed = aligned_window(
    masses, tokens, packed, contract, 100.0,
    expected_row_order_sha256=row_order_digest(tokens), ppm=10.0,
)
scores = score_window(window_packed, logits, contract)
result = topk_with_ties(scores, window_tokens, k=5)
```

The synthetic contract is explicitly synthetic. It must never be copied onto a real bank as a shortcut to admission. For caller-owned plain `.npy` arrays, an illustrative read-only load is `np.load(path, mmap_mode="r", allow_pickle=False, max_header_size=8192)`; check the file's own provenance and dtype before use. This is not a hostile-file sandbox.

## A real comparison, once independently eligible

Freeze the candidate bank and identity normalization, mass convention/window, model weights, spectrum-view aggregation and logits. Compare only `likelihood_order` against the single fixed `balanced_prospective` formula. Record a treatment before examining truth, and use an independently eligible evaluation panel whose prior exposures are documented. Keep truth and `evaluation_only_expected_rr` outside inference code.

Report per-query candidate counts, absent-truth frequency, exact tie groups and tie-neutral expected reciprocal rank at the chosen cutoff. Keep score differences paired by query. These are proposed measurements; this release contains no real panel or comparison result. Do not relabel a repeatedly inspected development panel as untouched validation.

The helper admits at most 1,000,000 bank rows and 32,768 rows in one complete window, with top k from 1 to 25. It refuses oversized windows instead of truncating them. Complete-axis validation is linear on each call; this transparent companion has no measured performance claim on a 436k-row bank. Any optimization of repeated queries needs its own controls and measured evidence.
