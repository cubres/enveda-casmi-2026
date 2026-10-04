# Validate candidate arrays before ranking

`src/candidate_bank_contracts.py` inspects a sorted neutral-mass index, packed fingerprints, and the ordered fingerprint-bit selection. It reads `.npy` inputs through read-only memory maps with object-array loading disabled. It requires Python 3.12 and NumPy.

```bash
python -m pip install numpy==2.0.2
python src/candidate_bank_contracts.py \
  --mass coco_mass.npy \
  --fingerprints coco_fp.npy \
  --bits fp_bits.npy
```

Checks include finite positive masses, sorting across chunk boundaries, matching row counts, integer bit indices with no duplicates, exact packed width, uint8 storage, and zero unused padding bits. Equal masses are valid. The declared bit order is preserved.

A passing array contract cannot establish molecular identity alignment, descriptor semantics, chemical validity, or asset licensing. Record those separately from shape and numeric validation.

## Inclusive precursor-window union

`src/precursor_window_union.py` is a standard-library primitive for combining several neutral-mass windows with an existing fallback candidate set:

For the import example below, start Python from the repository root with `PYTHONPATH=src python`, or run your own script with `PYTHONPATH=src python your_script.py`.

```python
from precursor_window_union import union_precursor_windows

indices = union_precursor_windows(
    [399.0, 400.0, 400.003, 401.0],
    baseline_indices=[0],
    neutral_mass_estimates=[400.0, 401.0],
    ppm=10.0,
    check_mass_index=True,
)
assert indices == (0, 1, 2, 3)
```

Windows include both boundaries. Indices are unique and sorted, and the baseline remains in the union. Nonpositive and nonfinite estimates are ignored. Baseline indices must refer to the same sorted mass index.

Provide neutral masses after an explicit adduct/charge conversion; raw precursor m/z is not an interchangeable input. This function applies no candidate cap. A later cap can change retention and must be evaluated separately. Candidate-set expansion alone does not establish a ranking improvement.

## Reproduce mechanics checks

From the repository root:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python src/precursor_window_union.py --self-test
```

These run 14 adversarial array tests and 16 window-contract checks. They use synthetic inputs and require no competition data, GPU, model weights, or external service.

Both original utilities and the array tests carry the MIT license in their source files. The license for these utilities does not grant rights to independently supplied data or weights.
