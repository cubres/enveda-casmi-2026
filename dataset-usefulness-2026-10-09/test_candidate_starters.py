"""Meaningful boundary tests for numerical examples; all fixtures are invented."""
import unittest
import numpy as np
from candidate_starters import lookup_popularity, mass_window, decode_selected_bits


class StarterTests(unittest.TestCase):
    def setUp(self):
        self.keys = np.asarray(['MMMMMMMMMMMMMM', 'YYYYYYYYYYYYYY'], dtype='S14')
        self.sid = np.asarray([3, 0], dtype=np.uint32)
        self.pmid = np.asarray([7, 0], dtype=np.uint32)

    def test_missing_after_final_key_does_not_index_length(self):
        row = lookup_popularity(self.keys, self.sid, self.pmid, ['ZZZZZZZZZZZZZZ'])
        self.assertEqual(row['matched'].tolist(), [False])
        self.assertEqual(row['pop'].tolist(), [0.0])

    def test_missing_before_and_between_keys(self):
        row = lookup_popularity(self.keys, self.sid, self.pmid,
                                ['AAAAAAAAAAAAAA', 'NNNNNNNNNNNNNN'])
        self.assertEqual(row['matched'].tolist(), [False, False])

    def test_matching_zero_counts_is_distinct_from_absence(self):
        row = lookup_popularity(self.keys, self.sid, self.pmid, ['YYYYYYYYYYYYYY'])
        self.assertEqual(row['matched'].tolist(), [True])
        self.assertEqual(row['pop'].tolist(), [0.0])

    def test_duplicates_preserve_input_order(self):
        row = lookup_popularity(self.keys, self.sid, self.pmid,
                                ['YYYYYYYYYYYYYY', 'MMMMMMMMMMMMMM', 'MMMMMMMMMMMMMM'])
        self.assertEqual(row['substances'].tolist(), [0, 3, 3])
        self.assertAlmostEqual(row['pop'][1], np.log(4) + np.log(8))

    def test_empty_bank_and_queries(self):
        empty = lookup_popularity(self.keys[:0], self.sid[:0], self.pmid[:0], ['MMMMMMMMMMMMMM'])
        self.assertEqual(empty['matched'].tolist(), [False])
        empty = lookup_popularity(self.keys, self.sid, self.pmid, [])
        self.assertEqual(empty['matched'].shape, (0,))

    def test_invalid_query_never_silently_truncates(self):
        for q in ['MMMMMMMMMMMMMM-NNNNNNNNNN-O', 'lowercase', '12345678901234']:
            with self.assertRaises(ValueError):
                lookup_popularity(self.keys, self.sid, self.pmid, [q])

    def test_count_header_mismatch(self):
        with self.assertRaises(ValueError):
            lookup_popularity(self.keys, self.sid[:1], self.pmid, ['MMMMMMMMMMMMMM'])

    def test_mass_window_includes_both_boundaries(self):
        center, ppm = 100.0, 10000.0
        self.assertEqual(mass_window(np.asarray([98.0, 99.0, 100.0, 101.0, 102.0]), center, ppm), (1, 4))

    def test_mass_empty_outside_and_duplicate_exact_mass(self):
        self.assertEqual(mass_window(np.asarray([], dtype=float), 100), (0, 0))
        mass = np.asarray([100.0, 100.0, 101.0])
        self.assertEqual(mass_window(mass, 100, 0), (0, 2))
        self.assertEqual(mass_window(mass, 200), (3, 3))

    def test_mass_input_rejections(self):
        for mass in [np.asarray([2.0, 1.0]), np.asarray([np.nan]), np.asarray([np.inf])]:
            with self.assertRaises(ValueError):
                mass_window(mass, 100)
        for center, ppm in [(0, 10), (100, -1), (np.inf, 10), (100, np.nan)]:
            with self.assertRaises(ValueError):
                mass_window(np.asarray([100.0]), center, ppm)

    def test_unpack_is_big_endian_and_discards_only_padding(self):
        a = np.asarray([[0b10000000, 0b00000001]], dtype=np.uint8)
        self.assertEqual(decode_selected_bits(a, 10).tolist(), [[1, 0, 0, 0, 0, 0, 0, 0, 0, 0]])

    def test_empty_packed_window(self):
        self.assertEqual(decode_selected_bits(np.empty((0, 867), dtype=np.uint8)).shape, (0, 6930))


if __name__ == '__main__':
    unittest.main()
