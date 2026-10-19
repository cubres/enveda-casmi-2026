"""Synthetic, in-memory demo tests; no dataset files or chemistry required.

SPDX-License-Identifier: Apache-2.0
"""

import unittest

import numpy as np
import pyarrow as pa

from demo_mass_window import Bank, ROWS, SELECTED_BITS, demo_result, mass_window_indices, validate_bank


def synthetic_bank():
    keys = [f"TEST{i:010d}" for i in range(ROWS)]
    masses = np.full(ROWS, 100.0, dtype=np.float64)
    source_rows = np.arange(ROWS, dtype=np.int64) + 10000
    source = pa.table({
        "inchikey14": keys,
        "smiles": ["C"] * ROWS,  # Invented strings, never parsed as molecules.
        "source": ["ChEBI"] * ROWS,
        "source_id": [f"SYNTHETIC:{i}" for i in range(ROWS)],
        "chebi_star": ["3"] * ROWS,
        "original_source_row": source_rows,
        "computed_raw_key": keys,
        "computed_mass": masses,
    })
    return Bank(np.zeros((ROWS, 1300), dtype=np.uint8), masses, np.argsort(masses, kind="stable"), source, source_rows, np.arange(SELECTED_BITS, dtype=np.int64))


class DemoTests(unittest.TestCase):
    def test_closed_window_and_stable_ties(self):
        masses = np.array([200.0, 100.0, 100.0, 300.0])
        order = np.argsort(masses, kind="stable")
        np.testing.assert_array_equal(mass_window_indices(masses, order, 100, 200), [1, 2, 0])
        np.testing.assert_array_equal(mass_window_indices(masses, order, 100, 100), [1, 2])
        self.assertEqual(mass_window_indices(masses, order, 101, 199).size, 0)

    def test_window_rejects_invalid_endpoints(self):
        masses = np.array([100.0])
        for low, high in [(2, 1), (float("nan"), 1), (1, float("inf"))]:
            with self.subTest(low=low, high=high), self.assertRaises(ValueError):
                mass_window_indices(masses, np.array([0]), low, high)

    def test_valid_synthetic_bank_and_deterministic_demo(self):
        bank = synthetic_bank()
        validate_bank(bank)
        first = demo_result(bank, ppm=10, limit=2)
        self.assertEqual(first, demo_result(bank, ppm=10, limit=2))
        self.assertEqual(first["matching_rows"], ROWS)
        self.assertEqual(first["shown_rows"], 2)
        self.assertEqual([r["row"] for r in first["records"]], [0, 1])
        self.assertEqual(first["records"][0]["selected_on_bits"], 0)
        self.assertEqual(demo_result(bank, query_mass=200)["matching_rows"], 0)

    def test_padding_mass_order_and_source_join_reject(self):
        bank = synthetic_bank()
        padded = bank.fingerprints.copy()
        padded[0, -1] = 1
        bad_banks = [bank._replace(fingerprints=padded), bank._replace(mass_order=bank.mass_order[::-1]), bank._replace(source_rows=bank.source_rows[::-1]), bank._replace(fingerprints=np.zeros((ROWS, 1299), dtype=np.uint8))]
        for bad in bad_banks:
            with self.subTest(kind=str(bad.fingerprints.shape)), self.assertRaises(ValueError):
                validate_bank(bad)

    def test_demo_rejects_bad_arguments(self):
        bank = synthetic_bank()
        for kwargs in [{"query_mass": 0}, {"query_mass": float("inf")}, {"ppm": 0}, {"ppm": float("nan")}, {"limit": 0}, {"limit": True}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                demo_result(bank, **kwargs)


if __name__ == "__main__":
    unittest.main()
