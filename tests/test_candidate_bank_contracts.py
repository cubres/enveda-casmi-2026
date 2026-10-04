"""Run with PYTHONPATH=src python -m unittest discover -s tests -v."""

# MIT License
# Copyright (c) 2026 cubres
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import unittest

import numpy as np

from candidate_bank_contracts import validate_candidate_bank


class CandidateBankTests(unittest.TestCase):
    def bank(self):
        values = np.array([[1, 0, 1, 0, 0, 1, 1, 0, 1, 0], [0] * 10, [1] * 10], dtype=np.uint8)
        return np.array([100.0, 100.0, 101.0]), np.packbits(values, axis=1), np.array([20, 3, 9, 1, 4, 8, 5, 10, 12, 16])

    def test_valid_bank_accepts_mass_ties_and_preserves_bit_order(self):
        mass, fp, bits = self.bank()
        old = bits.copy()
        result = validate_candidate_bank(mass, fp, bits, chunk_rows=1)
        self.assertEqual(result["rows"], 3)
        self.assertEqual(result["padding_bits"], 6)
        np.testing.assert_array_equal(bits, old)

    def test_cross_chunk_mass_disorder(self):
        mass, fp, bits = self.bank()
        mass[:] = [101, 102, 100]
        with self.assertRaisesRegex(ValueError, "sorted"):
            validate_candidate_bank(mass, fp, bits, chunk_rows=2)

    def test_nonfinite_mass(self):
        for value in (np.nan, np.inf, -np.inf):
            mass, fp, bits = self.bank()
            mass[1] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_candidate_bank(mass, fp, bits)

    def test_nonpositive_mass(self):
        for value in (0, -10):
            mass, fp, bits = self.bank()
            mass[0] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_candidate_bank(mass, fp, bits)

    def test_wrong_row_count(self):
        mass, fp, bits = self.bank()
        with self.assertRaisesRegex(ValueError, "row counts"):
            validate_candidate_bank(mass[:-1], fp, bits)

    def test_wrong_packed_width(self):
        mass, fp, bits = self.bank()
        with self.assertRaisesRegex(ValueError, "width"):
            validate_candidate_bank(mass, fp[:, :1], bits)

    def test_padding_contamination(self):
        mass, fp, bits = self.bank()
        fp[-1, -1] |= 1
        with self.assertRaisesRegex(ValueError, "padding"):
            validate_candidate_bank(mass, fp, bits, chunk_rows=2)

    def test_byte_aligned_bank(self):
        result = validate_candidate_bank(np.array([1.0]), np.array([[255]], dtype=np.uint8), np.arange(8))
        self.assertEqual(result["padding_bits"], 0)

    def test_duplicate_or_negative_selected_bit(self):
        mass, fp, bits = self.bank()
        for value in (-1, bits[1]):
            changed = bits.copy()
            changed[0] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "distinct"):
                validate_candidate_bank(mass, fp, changed)

    def test_selected_bit_dtype_and_shape(self):
        mass, fp, bits = self.bank()
        for changed in (bits.astype(float), bits.astype(bool), bits[:, None], np.array([], dtype=int)):
            with self.subTest(shape=changed.shape), self.assertRaises(ValueError):
                validate_candidate_bank(mass, fp, changed)

    def test_invalid_chunk_rows(self):
        for value in (0, -1, True, 2.5):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "chunk_rows"):
                validate_candidate_bank(*self.bank(), chunk_rows=value)

    def test_invalid_mass_and_fingerprint_types(self):
        mass, fp, bits = self.bank()
        for args in ((mass.astype(int), fp, bits), (mass[:, None], fp, bits), (mass, fp.astype(np.int8), bits), (mass, fp.ravel(), bits)):
            with self.subTest(), self.assertRaises(ValueError):
                validate_candidate_bank(*args)

    def test_empty_bank(self):
        with self.assertRaises(ValueError):
            validate_candidate_bank(np.array([], dtype=float), np.empty((0, 2), dtype=np.uint8), np.arange(10))

    def test_inputs_are_preserved(self):
        arrays = self.bank()
        originals = [a.copy() for a in arrays]
        validate_candidate_bank(*arrays)
        for actual, original in zip(arrays, originals):
            np.testing.assert_array_equal(actual, original)


if __name__ == "__main__":
    unittest.main()
