"""Original provenance recorder for actual consumed files and derived arrays.

Call at actual loader sites, using the exact path handed to the loader. This is
not a finder and never changes file selection. Receipts contain no paths, query
identifiers, spectra, model contents or labels. It is source-ready only.
Copyright (c) 2026 cubres. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import numpy as np


class ConsumedBindings:
    def __init__(self):
        self.records = {}

    def file(self, role, consumed_path, *, expected_sha256=None, deadline=None):
        path = Path(consumed_path)
        if role in self.records:
            raise ValueError("Duplicate consumed-input role")
        h, size = hashlib.sha256(), 0
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1 << 20), b""):
                if deadline is not None and time.monotonic() >= deadline:
                    raise TimeoutError("Input hashing exhausted its allotted deadline")
                h.update(chunk)
                size += len(chunk)
        actual = h.hexdigest()
        if expected_sha256 is not None and actual != expected_sha256:
            raise ValueError("Actual consumed input differs from the expected binding")
        self.records[role] = {"kind": "file", "bytes": size, "sha256": actual,
                              "expected_verified": expected_sha256 is not None}
        return actual

    def array(self, role, value):
        if role in self.records:
            raise ValueError("Duplicate derived-array role")
        value = np.asarray(value)
        if value.dtype.hasobject or value.dtype.fields or value.dtype.subdtype or value.dtype.kind not in "biufc":
            raise ValueError("Derived-array binding requires a plain numeric dtype")
        h = hashlib.sha256()
        h.update(repr((value.dtype.str, value.shape)).encode("ascii"))
        # Buffered iteration avoids copying a multi-GB non-contiguous array.
        for piece in np.nditer(value, flags=["external_loop", "buffered", "zerosize_ok"],
                               op_flags=["readonly"], order="C", buffersize=65536):
            h.update(piece.tobytes(order="C"))
        self.records[role] = {"kind": "derived_numeric_array",
                              "shape": list(value.shape), "dtype": value.dtype.str,
                              "sha256": h.hexdigest()}
        return h.hexdigest()

    def ordered_strings(self, role, values):
        if role in self.records:
            raise ValueError("Duplicate ordered-string role")
        h, count = hashlib.sha256(), 0
        for value in values:
            if not isinstance(value, str):
                raise ValueError("Ordered identifier binding requires strings")
            data = value.encode("utf-8")
            h.update(len(data).to_bytes(8, "big"))
            h.update(data)
            count += 1
        self.records[role] = {"kind": "ordered_string_sequence",
                              "count": count, "sha256": h.hexdigest()}
        return h.hexdigest()

    def receipt(self, required_roles=None):
        roles_complete = required_roles is not None and set(self.records) == set(required_roles)
        return {"protocol": "actual-consumed-input-and-derived-state-bindings-v1",
                "records": self.records.copy(),
                "paths_or_data_exported": False,
                "expected_role_coverage_complete": roles_complete,
                "observed_file_expectations_verified": all(
                    r.get("expected_verified", False) for r in self.records.values()
                    if r["kind"] == "file") and any(
                    r["kind"] == "file" for r in self.records.values())}
