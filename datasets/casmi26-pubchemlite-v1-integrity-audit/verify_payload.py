#!/usr/bin/env python3
"""Verify the pinned Kaggle PubChemLite V1 archive without loading its pickle.

SPDX-License-Identifier: Apache-2.0

This script checks the exact archive bytes, ZIP CRC, manifest, payload hashes,
and NPY headers. It never extracts files and never executes pickle opcodes.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import struct
import sys
import zipfile
from pathlib import Path
from typing import BinaryIO


ARCHIVE_BYTES = 113_498_418
ARCHIVE_SHA256 = "fb4be2fe5d12d3c5bfb16dcec7bfe4462fb94572a3125d5eb2bde156c3ef0cf7"
MANIFEST_SHA256 = "f333f6fa150f807f2981faa7dcb930b90c6f5022015f7314f428cb8bd84e42cb"
EXPECTED_FILES = {
    "pubchemlite_fp.npy": {
        "bytes": 334_454_048,
        "sha256": "724926ecb4bfb2efc7e63014e7f6b8bed8aec34882a435f039c0ddab139e569c",
        "shape": [385_760, 867],
        "descr": "|u1",
        "dtype": "uint8",
    },
    "pubchemlite_mass.npy": {
        "bytes": 3_086_208,
        "sha256": "f107bdf361b75fb2f6115abb2a28eda053b476b6c3694f4b0a2bfdadb248730f",
        "shape": [385_760],
        "descr": "<f8",
        "dtype": "float64",
    },
    "pubchemlite_meta.pkl": {
        "bytes": 23_642_096,
        "sha256": "3c9a18c7662022bce51759b1660292b712fe7544459020e38299d2f0747517ce",
    },
}
EXPECTED_MANIFEST = {
    "source": "cosmicbe/casmi26-pubchemlite",
    "source_license": "CC0-1.0",
    "source_csv_sha256": "4a2d111a1fd63e993f65beed48745df0dbc7590993199f968beed392551ec2fc",
    "fp_bits_sha256": "a61e372fc41091bf5c7467e08134081266262665077cb9e2c56d73e4887f3013",
    "rows": 385_760,
    "nbits": 6_930,
    "rdkit": "2026.03.3",
}


def sha256_stream(stream: BinaryIO) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(1 << 20):
        size += len(chunk)
        digest.update(chunk)
    return size, digest.hexdigest()


def read_npy_header(zf: zipfile.ZipFile, name: str) -> dict[str, object]:
    """Read only the NPY header; never allocate or decode the array payload."""
    with zf.open(name) as stream:
        prefix = stream.read(8)
        if len(prefix) != 8 or prefix[:6] != b"\x93NUMPY":
            raise ValueError(f"{name}: invalid NPY magic")
        major, minor = prefix[6], prefix[7]
        if (major, minor) == (1, 0):
            length_bytes = stream.read(2)
            if len(length_bytes) != 2:
                raise ValueError(f"{name}: short NPY v1 header length")
            header_length = struct.unpack("<H", length_bytes)[0]
            encoding = "latin1"
        elif (major, minor) in {(2, 0), (3, 0)}:
            length_bytes = stream.read(4)
            if len(length_bytes) != 4:
                raise ValueError(f"{name}: short NPY v{major} header length")
            header_length = struct.unpack("<I", length_bytes)[0]
            encoding = "utf8" if major == 3 else "latin1"
        else:
            raise ValueError(f"{name}: unsupported NPY version {major}.{minor}")
        if header_length > 1 << 20:
            raise ValueError(f"{name}: unreasonable NPY header length")
        raw_header = stream.read(header_length)
        if len(raw_header) != header_length:
            raise ValueError(f"{name}: truncated NPY header")
        parsed = ast.literal_eval(raw_header.decode(encoding).strip())
        if not isinstance(parsed, dict):
            raise ValueError(f"{name}: NPY header is not a dictionary")
        shape = parsed.get("shape")
        descr = parsed.get("descr")
        fortran = parsed.get("fortran_order")
        if not isinstance(shape, tuple) or not all(type(v) is int for v in shape):
            raise ValueError(f"{name}: invalid NPY shape")
        if not isinstance(descr, str) or type(fortran) is not bool:
            raise ValueError(f"{name}: invalid NPY dtype/order fields")
        return {
            "npy_version": [major, minor],
            "shape": list(shape),
            "descr": descr,
            "fortran_order": fortran,
        }


def audit(archive: Path) -> dict[str, object]:
    with archive.open("rb") as stream:
        size, digest = sha256_stream(stream)
    if size != ARCHIVE_BYTES or digest != ARCHIVE_SHA256:
        raise ValueError("archive bytes/hash do not match the pinned Kaggle V1 archive")

    result: dict[str, object] = {
        "archive": archive.name,
        "archive_bytes": size,
        "archive_sha256": digest,
        "dataset": "franciscoangulo/casmi26-pubchemlite-cc0-candidate-fingerprints",
        "dataset_version": 1,
        "zip_crc": "pending",
        "manifest_sha256": None,
        "files": {},
        "arrays": {},
        "metadata_pickle_loaded": False,
        "row_identity_alignment_verified": False,
        "license_cleared_for_competition_use": False,
    }

    with zipfile.ZipFile(archive) as zf:
        expected_names = {"MANIFEST.json", *EXPECTED_FILES.keys()}
        if set(zf.namelist()) != expected_names:
            raise ValueError("ZIP member set differs from the pinned V1 file set")
        bad_member = zf.testzip()
        if bad_member is not None:
            raise ValueError(f"ZIP CRC failure in {bad_member}")
        result["zip_crc"] = "passed"

        manifest_bytes = zf.read("MANIFEST.json")
        manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
        if manifest_hash != MANIFEST_SHA256:
            raise ValueError("manifest hash does not match the pinned Kaggle V1 manifest")
        manifest = json.loads(manifest_bytes)
        for key, expected in EXPECTED_MANIFEST.items():
            if manifest.get(key) != expected:
                raise ValueError(f"manifest field {key!r} differs from the pinned V1 value")
        result["manifest_sha256"] = manifest_hash
        if manifest.get("files") != {
            name: {"bytes": pins["bytes"], "sha256": pins["sha256"]}
            for name, pins in EXPECTED_FILES.items()
        }:
            raise ValueError("manifest member pins differ from the pinned V1 values")

        observed_files: dict[str, dict[str, object]] = {}
        for name, pins in EXPECTED_FILES.items():
            with zf.open(name) as member:
                member_size, member_hash = sha256_stream(member)
            if member_size != pins["bytes"] or member_hash != pins["sha256"]:
                raise ValueError(f"payload hash/size mismatch for {name}")
            observed_files[name] = {"bytes": member_size, "sha256": member_hash}
        result["files"] = observed_files

        arrays: dict[str, dict[str, object]] = {}
        for name in ("pubchemlite_fp.npy", "pubchemlite_mass.npy"):
            header = read_npy_header(zf, name)
            pins = EXPECTED_FILES[name]
            if header["shape"] != pins["shape"] or header["descr"] != pins["descr"]:
                raise ValueError(f"NPY header mismatch for {name}")
            if header["fortran_order"]:
                raise ValueError(f"{name}: unexpected Fortran-order array")
            arrays[name] = {
                **header,
                "dtype": pins["dtype"],
                "logical_nbits_from_manifest": EXPECTED_MANIFEST["nbits"],
            }
        result["arrays"] = arrays

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path, help="path to the exact Kaggle dataset V1 ZIP")
    parser.add_argument("--output", type=Path, help="optional path for the JSON receipt")
    args = parser.parse_args()
    receipt = audit(args.archive)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
