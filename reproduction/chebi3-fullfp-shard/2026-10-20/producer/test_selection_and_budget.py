"""Pure synthetic tests; no real dataset, model, chemistry or benchmark use.

SPDX-License-Identifier: Apache-2.0
"""

import copy
import math
import unittest

import selection_and_budget as sb


def synthetic_rows():
    # 8895 distinct eligible keys, present in all 64 mass bins.
    rows = []
    width = (sb.MASS_MAX_DA - sb.MASS_MIN_DA) / sb.MASS_BIN_COUNT
    for b in range(64):
        for rank in range(139 if b < 63 else 138):
            rows.append({"source": "ChEBI", "chebi_star": "3", "inchikey14": f"K{b:02d}{rank:011d}", "monoisotopic_mass": 80 + width * (b + 0.5)})
    return list(reversed(rows))


class SelectionTests(unittest.TestCase):
    def test_all_bins_balanced_exact_size_and_source_indices(self):
        rows = synthetic_rows()
        before = copy.deepcopy(rows)
        result = sb.select_shard(rows, set())
        self.assertEqual(result["eligible_count"], 8895)
        self.assertEqual(len(result["selected_indices"]), 4096)
        self.assertEqual(len(set(result["selected_indices"])), 4096)
        self.assertEqual(result["selected_bin_counts"], [64] * 64)
        self.assertEqual(result["canary_bin_counts"], [1] * 64)
        keys = [rows[i]["inchikey14"] for i in result["canary_indices"]]
        self.assertEqual(keys, [f"K{b:02d}{0:011d}" for b in range(64)])
        self.assertEqual(rows, before)
        self.assertEqual(sb.select_shard(rows, set()), result)

    def test_filtering_deduplication_and_earliest_source_index(self):
        rows = synthetic_rows()
        original_key = rows[0]["inchikey14"]
        rows.append(dict(rows[0]))
        extras = [
            {"source": "LIPID MAPS LMSD"}, {"chebi_star": "2"},
            {"chebi_star": 3.0}, {"inchikey14": "OLD"},
            {"monoisotopic_mass": math.nan}, {"monoisotopic_mass": math.inf},
            {"monoisotopic_mass": 79.99}, {"monoisotopic_mass": 1400.01},
        ]
        for n, changes in enumerate(extras):
            row = dict(rows[1], inchikey14=f"EXCLUDED{n:06d}")
            row.update(changes)
            rows.append(row)
        result = sb.select_shard(rows, {"OLD"})
        self.assertEqual(result["eligible_count"], 8895)
        self.assertEqual(result["excluded_counts"], {"other_source": 1, "other_star": 2, "old_bank_key": 1, "nonfinite_mass": 2, "mass_range": 2, "duplicate_raw_key": 1})
        # This key sorts beyond the selected subset, so specifically ensure its
        # retained occurrence is accounted for in counts and duplicate policy.
        self.assertEqual(rows[0]["inchikey14"], original_key)
        self.assertNotIn(8895, result["selected_indices"])

    def test_duplicate_canary_key_uses_original_index(self):
        rows = synthetic_rows()
        chosen = next(i for i, r in enumerate(rows) if r["inchikey14"] == "K0000000000000")
        rows.append(dict(rows[chosen]))
        result = sb.select_shard(rows, set())
        self.assertEqual(result["canary_indices"][0], chosen)
        self.assertNotIn(len(rows) - 1, result["selected_indices"])

    def test_empty_bins_are_skipped_without_losing_rows(self):
        rows = synthetic_rows()
        for row in rows:
            row["monoisotopic_mass"] = 100.0
        result = sb.select_shard(rows, set())
        self.assertEqual(result["eligible_bin_counts"], [8895] + [0] * 63)
        self.assertEqual(result["selected_bin_counts"], [4096] + [0] * 63)
        self.assertEqual(result["canary_bin_counts"], [64] + [0] * 63)
        self.assertEqual([rows[i]["inchikey14"] for i in result["selected_indices"]], sorted(r["inchikey14"] for r in rows)[:4096])

    def test_mass_boundaries(self):
        self.assertEqual(sb.mass_bin_index(80), 0)
        self.assertEqual(sb.mass_bin_index(100.625), 1)
        self.assertEqual(sb.mass_bin_index(1400), 63)
        for bad in [79.99, 1400.01, math.nan, math.inf, True, "80"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                sb.mass_bin_index(bad)

    def test_invalid_rows_and_bank_keys_reject(self):
        for bad_rows in ["rows", [None], [{}], [dict(synthetic_rows()[0], inchikey14="")], [dict(synthetic_rows()[0], monoisotopic_mass=True)], [dict(synthetic_rows()[0], monoisotopic_mass="100")]]:
            with self.subTest(bad_rows=str(bad_rows)[:80]), self.assertRaises(ValueError):
                sb.select_shard(bad_rows, set())
        for bad_keys in ["rawkey", {None}, {1}, {""}, {"some": "mapping"}]:
            with self.subTest(bad_keys=bad_keys), self.assertRaises(ValueError):
                sb.select_shard(synthetic_rows(), bad_keys)
        with self.assertRaises(ValueError):
            sb.select_shard(synthetic_rows()[:4095], set())


class BudgetTests(unittest.TestCase):
    def test_initial_canary_forecast_counts_only_remaining_rows(self):
        result = sb.forecast_budget([1.0] * 8, completed_rows=64, elapsed_seconds=200)
        self.assertEqual(result["remaining_rows"], 4032)
        self.assertEqual(result["remaining_chunks"], 504)
        self.assertEqual(result["remaining_waves"], 252)
        self.assertEqual(result["remaining_compute_seconds"], 378)
        self.assertEqual(result["forecast_total_seconds"], 698)
        self.assertTrue(result["passes"])

    def test_p90_slow_chunk_and_strict_deadline(self):
        result = sb.forecast_budget([1.0] * 7 + [4.0], completed_rows=64, elapsed_seconds=10)
        self.assertEqual(result["p90_chunk_seconds"], 4)
        self.assertEqual(result["median_chunk_seconds"], 1)
        self.assertEqual(result["remaining_compute_seconds"], 1512)
        self.assertTrue(result["passes"])
        self.assertFalse(sb.forecast_budget([1.0] * 8, completed_rows=64, elapsed_seconds=1262)["passes"])
        self.assertTrue(sb.forecast_budget([1.0] * 8, completed_rows=64, elapsed_seconds=1261.999)["passes"])

    def test_rolling_uses_last_128_and_keeps_all_elapsed_time(self):
        timings = [100.0] * 8 + [0.5] * 128
        result = sb.forecast_budget(timings, completed_rows=1088, elapsed_seconds=800)
        self.assertEqual(result["measured_chunk_count"], 136)
        self.assertEqual(result["recent_chunk_count"], 128)
        self.assertEqual(result["p90_chunk_seconds"], 0.5)
        self.assertEqual(result["elapsed_seconds"], 800)
        self.assertEqual(result["remaining_waves"], 188)
        self.assertEqual(result["forecast_total_seconds"], 1061)

    def test_final_row_count_retains_io_reserve(self):
        result = sb.forecast_budget([1.0] * 8, completed_rows=4096, elapsed_seconds=1639)
        self.assertEqual(result["remaining_compute_seconds"], 0)
        self.assertEqual(result["forecast_total_seconds"], 1759)
        self.assertTrue(result["passes"])
        self.assertFalse(sb.forecast_budget([1.0] * 8, completed_rows=4096, elapsed_seconds=1640)["passes"])

    def test_invalid_timings_rows_and_elapsed_reject(self):
        bad_timings = [[], [1.0] * 7, "timings", [1.0] * 7 + [0], [1.0] * 7 + [-1], [1.0] * 7 + [math.nan], [1.0] * 7 + [math.inf], [1.0] * 7 + [True], [1.0] * 7 + ["1"], [1.0] * 9]
        for values in bad_timings:
            with self.subTest(values=values), self.assertRaises(ValueError):
                sb.forecast_budget(values, completed_rows=64, elapsed_seconds=1)
        for rows in [0, 63, 65, 4095, 4104, True, 64.0, "64"]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                sb.forecast_budget([1.0] * 8, completed_rows=rows, elapsed_seconds=1)
        for elapsed in [-1, math.nan, math.inf, True, "1"]:
            with self.subTest(elapsed=elapsed), self.assertRaises(ValueError):
                sb.forecast_budget([1.0] * 8, completed_rows=64, elapsed_seconds=elapsed)


if __name__ == "__main__":
    unittest.main()
