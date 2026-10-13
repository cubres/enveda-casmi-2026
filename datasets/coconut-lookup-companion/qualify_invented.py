"""Tiny invented controls only. No real dataset, model, structures or network.

Copyright 2026 cubres contributors. SPDX-License-Identifier: MIT
"""
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

START = time.monotonic()
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
signal.signal(signal.SIGALRM, lambda *_: os._exit(124))
signal.setitimer(signal.ITIMER_REAL, 30)
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"

import numpy as np

spec = importlib.util.spec_from_file_location("invented_coconut_lookup", Path(__file__).with_name("coconut_lookup.py"))
lookup = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lookup
spec.loader.exec_module(lookup)
checks = {}


def rejects(name, action):
    try:
        action()
    except (ValueError, TypeError):
        checks[name] = True
    else:
        checks[name] = False


masses = np.array([98., 99., 99., 100., 101., 102.])
rows = lookup.mass_window_rows(masses, 100., 10000.)
checks["inclusive_endpoints_and_duplicate_masses"] = rows.tolist() == [1, 2, 3, 4]
checks["empty_window"] = lookup.mass_window_rows(masses, 200., 0.).size == 0
checks["zero_ppm_retains_equal_mass_rows"] = lookup.mass_window_rows(masses, 99., 0.).tolist() == [1, 2]
checks["row_cap_exact_boundary"] = lookup.mass_window_rows(masses, 100., 10000., max_rows=4).tolist() == [1, 2, 3, 4]
rejects("row_cap_exceeded", lambda: lookup.mass_window_rows(masses, 100., 10000., max_rows=3))
rejects("unsorted_mass", lambda: lookup.mass_window_rows(masses[::-1], 100.))
rejects("nonfinite_mass_array", lambda: lookup.mass_window_rows(np.array([99., np.nan]), 100.))
rejects("bool_query", lambda: lookup.mass_window_rows(masses, True))
rejects("negative_neutral_mass", lambda: lookup.mass_window_rows(masses, -1.))
rejects("infinite_query", lambda: lookup.mass_window_rows(masses, np.inf))
rejects("negative_ppm", lambda: lookup.mass_window_rows(masses, 100., -1.))
rejects("infinite_ppm", lambda: lookup.mass_window_rows(masses, 100., np.inf))
rejects("bool_row_cap", lambda: lookup.mass_window_rows(masses, 100., max_rows=True))
packed = np.zeros((6, 867), dtype=np.uint8)
packed[1, 0] = 128
packed[4, -1] = 192
bits = np.arange(6930, dtype=np.int64)
bank = lookup.Bank(masses, packed, bits)
decoded = bank.decode(rows)
checks["big_bitorder_and_selected_width"] = decoded.shape == (4, 6930) and decoded[0, 0] == 1 and decoded[0, 1] == 0
checks["last_two_selected_bits"] = decoded[-1, -2:].tolist() == [1, 1]
checks["empty_decode"] = bank.decode(np.array([], dtype=np.int64)).shape == (0, 6930)
rejects("negative_row", lambda: bank.decode(np.array([-1], dtype=np.int64)))
rejects("row_out_of_bounds", lambda: bank.decode(np.array([6], dtype=np.int64)))
rejects("shuffled_decode_rows", lambda: bank.decode(np.array([4, 1], dtype=np.int64)))
rejects("duplicate_decode_rows", lambda: bank.decode(np.array([1, 1], dtype=np.int64)))
packed[2, -1] = 1
rejects("nonzero_padding", lambda: bank.decode(np.array([2], dtype=np.int64)))
lookup.assert_row_join(["invented-a", "invented-b"], ["invented-a", "invented-b"])
checks["exact_unique_row_join"] = True
rejects("shuffled_row_join", lambda: lookup.assert_row_join(["invented-a", "invented-b"], ["invented-b", "invented-a"]))
rejects("duplicate_row_join", lambda: lookup.assert_row_join(["invented-a", "invented-a"], ["invented-a", "invented-a"]))
rejects("missing_row_join", lambda: lookup.assert_row_join(["invented-a"], ["invented-a", "invented-b"]))
lookup.assert_model_columns(bits, bits.copy(), lookup.DESCRIPTOR_ORDER)
checks["exact_selected_model_columns"] = True
rejects("shuffled_selected_bits", lambda: lookup.assert_model_columns(bits, bits[::-1], lookup.DESCRIPTOR_ORDER))
rejects("Morgan2048_MACCS_width_mismatch", lambda: lookup.assert_model_columns(bits, np.arange(2215), lookup.DESCRIPTOR_ORDER))
rejects("different_descriptor_families", lambda: lookup.assert_model_columns(bits, bits, ["invented-Morgan2048", "invented-MACCS167"]))
duplicates = bits.copy()
duplicates[1] = duplicates[0]
rejects("duplicate_model_bit_indices", lambda: lookup.assert_model_columns(duplicates, duplicates, lookup.DESCRIPTOR_ORDER))
checks = {name: bool(value) for name, value in checks.items()}
elapsed = time.monotonic() - START
cpu = resource.getrusage(resource.RUSAGE_SELF)
result = {"schema": "coconut-lookup-invented-controls/1", "qualification": "PASS_INVENTED_ONLY" if all(checks.values()) else "FAIL_INVENTED_ONLY",
          "checks": checks, "failed_checks": [k for k, v in checks.items() if not v],
          "invented_mass_rows": 6, "real_dataset_reads": 0, "chemical_structure_rows": 0,
          "model_predictions": 0, "network_calls": 0, "official_score": None,
          "numpy_version": np.__version__, "wall_seconds": elapsed,
          "process_cpu_seconds": cpu.ru_utime + cpu.ru_stime,
          "limits": {"wall_seconds": 30, "CPU_seconds": 10}}
print(json.dumps(result, sort_keys=True), flush=True)
if time.monotonic() - START >= 30 or cpu.ru_utime + cpu.ru_stime >= 10:
    os._exit(2)
os._exit(0 if not result["failed_checks"] else 2)
