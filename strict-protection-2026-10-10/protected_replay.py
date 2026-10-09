"""Original same-run fidelity check for gated candidate-list experiments.

No labels, spectra, query identifiers, checkpoints or submission I/O are used.
The module is source-ready only; it has not run on a Kaggle worker.
Copyright (c) 2026 cubres. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import math


class ProtectedReplay:
    """Compare protected output against the same-run disabled-hook control.

    Integration requires the exact pre-experiment final-list function, the
    configuration object with USE_SECOND_LIST/LIB_GATE, and the exact diagnostic
    list that the function appends to. Both paths see the same scientific inputs
    and runtime. The replay control's diagnostic entry is removed from that
    in-memory list so the active arm still produces one diagnostic row per query.

    In changed-arm mode a gate-open query is allowed to change. Every gate-closed
    query must match its disabled-hook control as a complete ordered SMILES list.
    In strict-control mode every query must match. All schema, input, source,
    runtime and owned-process gates remain the caller's responsibility.
    """

    def __init__(self, final_list_fn, cfg, diagnostics, *, changed_arm=True):
        self.fn = final_list_fn
        self.cfg = cfg
        self.diagnostics = diagnostics
        self.changed_arm = bool(changed_arm)
        self.rows = self.protected_rows = self.open_rows = 0
        self.actual_gate_open_rows = 0
        self.protected_mismatches = 0
        self.passed = True

    def _control(self, args, kwargs):
        flag = self.cfg.USE_SECOND_LIST
        before = len(self.diagnostics)
        try:
            self.cfg.USE_SECOND_LIST = False
            result = self.fn(*args, **kwargs)
            if len(self.diagnostics) != before + 1:
                raise RuntimeError("Control must append exactly one diagnostic")
            self.diagnostics.pop()
            # Snapshot before the active call; a mutable result list could be
            # reused and modified by the original function on its second call.
            return tuple(result)
        finally:
            self.cfg.USE_SECOND_LIST = flag

    def __call__(self, *args, **kwargs):
        try:
            return self._call_checked(*args, **kwargs)
        except BaseException:
            self.passed = False
            raise

    def _call_checked(self, *args, **kwargs):
        # ap2_final(mid, sub, csmi, p, full_order, keys, lib_max, ...)
        lib_max = kwargs.get("lib_max") if "lib_max" in kwargs else args[6]
        lib_max = float(lib_max)
        if not math.isfinite(lib_max):
            raise ValueError("Nonfinite library gate evidence")
        protected = (not self.changed_arm) or lib_max >= self.cfg.LIB_GATE
        self.rows += 1
        self.actual_gate_open_rows += int(lib_max < self.cfg.LIB_GATE)
        if protected:
            control = self._control(args, kwargs)
            before = len(self.diagnostics)
            actual = self.fn(*args, **kwargs)
            if len(self.diagnostics) != before + 1:
                self.passed = False
                raise RuntimeError("Active arm must append exactly one diagnostic")
            self.protected_rows += 1
            if list(actual) != list(control):
                self.protected_mismatches += 1
                self.passed = False
                raise RuntimeError("Protected complete candidate ordering changed")
            return actual
        self.open_rows += 1
        try:
            before = len(self.diagnostics)
            actual = self.fn(*args, **kwargs)
            if len(self.diagnostics) != before + 1:
                raise RuntimeError("Active arm must append exactly one diagnostic")
            return actual
        except BaseException:
            self.passed = False
            raise

    def receipt(self, expected_rows):
        expected_rows = int(expected_rows)
        passed = (self.passed and self.rows == expected_rows and
                  self.rows == self.protected_rows + self.open_rows and
                  self.protected_mismatches == 0 and self.protected_rows > 0)
        return {"protocol": "same-run-disabled-second-hook-control-v1",
                "status": "PASS" if passed else "HOLD",
                "changed_arm": self.changed_arm,
                "rows": self.rows, "expected_rows": expected_rows,
                "protected_rows": self.protected_rows,
                "gate_open_rows": self.actual_gate_open_rows,
                "unprotected_rows": self.open_rows,
                "protected_order_mismatches": self.protected_mismatches,
                "complete_ordered_lists_compared": True,
                "query_identifiers_or_lists_exported": False}
