#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 cubres
"""Verify the small public CASMI PubChem growth supplement against its manifest.

This reads a local copy of GROWTH_MANIFEST.json and the 13 named payload files.
It does not access the network, change inputs, execute notebook code, or inspect
competition labels. NumPy is the only non-standard dependency.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


PAYLOAD_FILES = (
    "growth_pc_cid.npy",
    "growth_pc_ik14.npy",
    "growth_pc_lotus_refs.npy",
    "growth_pc_lpmid.npy",
    "growth_pc_lsid.npy",
    "growth_pc_lsynonyms.npy",
    "growth_pc_mass.npy",
    "growth_pc_np.npy",
    "growth_pc_off.npy",
    "growth_pc_smiles.npy",
    "growth_pc_src_mask.npy",
    "growth_pc_src_observed.npy",
    "growth_pubchem_tier.csv",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify(data_dir: Path, manifest_path: Path) -> dict[str, Any]:
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    files: dict[str, dict[str, Any]] = {}
    arrays: dict[str, np.ndarray] = {}

    for name in PAYLOAD_FILES:
        path = data_dir / name
        require(path.is_file(), f"missing payload file: {path}")
        raw = path.read_bytes()
        expected = manifest["files"][name]
        actual_hash = sha256(raw)
        require(len(raw) == expected["bytes"], f"byte-count mismatch: {name}")
        require(actual_hash == expected["sha256"], f"SHA-256 mismatch: {name}")
        item: dict[str, Any] = {
            "bytes": len(raw),
            "sha256": actual_hash,
        }
        if name.endswith(".npy"):
            array = np.load(path, allow_pickle=False)
            require(list(array.shape) == expected["shape"], f"shape mismatch: {name}")
            require(array.dtype == np.dtype(expected["dtype"]), f"dtype mismatch: {name}")
            arrays[name] = array
            item.update({"shape": list(array.shape), "dtype": array.dtype.str})
        files[name] = item

    n = int(manifest["rows"])
    row_arrays = [a for name, a in arrays.items() if name not in {
        "growth_pc_off.npy", "growth_pc_smiles.npy"
    }]
    require(all(len(a) == n for a in row_arrays), "per-row arrays are not aligned")

    offsets = arrays["growth_pc_off.npy"]
    smiles = arrays["growth_pc_smiles.npy"].tobytes()
    mass = arrays["growth_pc_mass.npy"]
    cid = arrays["growth_pc_cid.npy"]
    ik14 = arrays["growth_pc_ik14.npy"]
    require(len(offsets) == n + 1, "offset array must have rows + 1 entries")
    require(int(offsets[0]) == 0, "first SMILES offset must be zero")
    require(int(offsets[-1]) == len(smiles), "last SMILES offset must equal byte length")
    require(bool(np.all(offsets[1:] >= offsets[:-1])), "SMILES offsets are not monotone")
    require(bool(np.all(offsets[1:] > offsets[:-1])), "empty SMILES row found")
    require(bool(np.all(np.isfinite(mass)) and np.all(mass > 0)), "invalid mass value")
    require(bool(np.all(mass[1:] >= mass[:-1])), "mass rows are not sorted")
    require(len(np.unique(cid)) == n, "representative CIDs are not unique")
    require(len(np.unique(ik14)) == n, "raw InChIKey14 values are not unique")
    require(bool(np.all(arrays["growth_pc_np.npy"] <= 7)), "unexpected natural-product bits")
    require(bool(np.all(arrays["growth_pc_src_mask.npy"] == 0)), "source mask is not all zero")
    require(bool(np.all(arrays["growth_pc_src_observed.npy"] == 0)), "source-observed mask is not all zero")
    for name in ("growth_pc_lotus_refs.npy", "growth_pc_lpmid.npy", "growth_pc_lsid.npy", "growth_pc_lsynonyms.npy"):
        a = arrays[name]
        require(bool(np.all(np.isfinite(a)) and np.all(a >= 0)), f"invalid count values: {name}")

    aligned = {"cid": 0, "mass": 0, "smiles": 0, "ik14": 0}
    official_key_disagreements = 0
    with (data_dir / "growth_pubchem_tier.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        reader = csv.DictReader(stream)
        required_columns = {"cid", "mass", "smiles", "ik14", "official_ik14"}
        require(required_columns.issubset(reader.fieldnames or ()), "CSV columns are incomplete")
        csv_rows = 0
        for i, row in enumerate(reader):
            csv_rows += 1
            expected_smiles = smiles[int(offsets[i]):int(offsets[i + 1])].decode("utf-8")
            checks = (
                int(row["cid"]) == int(cid[i]),
                float(row["mass"]) == float(mass[i]),
                row["smiles"] == expected_smiles,
                row["ik14"] == ik14[i].decode("ascii"),
            )
            for key, passed in zip(aligned, checks):
                if passed:
                    aligned[key] += 1
            official_key_disagreements += row["official_ik14"] != row["ik14"]
            require(all(checks), f"CSV row {i} does not align with arrays")
    require(csv_rows == n, f"CSV row count {csv_rows} != manifest rows {n}")

    return {
        "status": "PASS",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "dataset_slug": "dmitriigluzdov/casmi26-pubchem-popularity-prior",
        "dataset_version_observed": 10,
        "manifest_sha256": sha256(manifest_bytes),
        "manifest_rows": n,
        "manifest_total_new_payload_bytes": int(manifest["payload_bytes"]),
        "manifest_growth_files_bytes": sum(manifest["files"][name]["bytes"] for name in PAYLOAD_FILES),
        "verified_growth_payload_bytes": sum(item["bytes"] for item in files.values()),
        "checks": {
            "all_13_growth_payload_files_match_manifest": True,
            "npy_manifest_shapes_and_dtypes": True,
            "row_arrays_aligned": True,
            "offsets_and_smiles_valid": True,
            "mass_finite_positive_sorted": True,
            "representative_cids_unique": True,
            "raw_ik14_unique": True,
            "natural_product_bits_valid": True,
            "unmeasured_source_masks_are_zero": True,
            "count_arrays_finite_nonnegative": True,
            "csv_row_count_and_four_array_columns_aligned": True,
        },
        "csv_rows": csv_rows,
        "csv_array_alignment_rows": aligned,
        "csv_official_ik14_vs_ik14_disagreements": official_key_disagreements,
        "identity_note": (
            "official_ik14 is retained separately; the dataset manifest reports "
            "13 official-versus-RDKit CID mapping differences. The CSV field "
            "disagreement count above is a different row-wise comparison."
        ),
        "files": files,
        "provenance_note": (
            "Source/depositor masks are all zero because they were not measured; "
            "zero means unknown, not absent. The receipt does not relicense the "
            "source data or assert competition eligibility."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True, help="directory containing the 13 payload files")
    parser.add_argument("--manifest", type=Path, help="manifest path; defaults to DATA_DIR/GROWTH_MANIFEST.json")
    parser.add_argument("--receipt", type=Path, help="optional JSON output path")
    args = parser.parse_args()
    manifest_path = args.manifest or (args.data_dir / "GROWTH_MANIFEST.json")
    result = verify(args.data_dir, manifest_path)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
