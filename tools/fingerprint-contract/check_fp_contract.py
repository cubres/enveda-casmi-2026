"""Original stdlib-only NPY fingerprint contract checker; see LICENSE-CODE.txt.

Checks bytes, selected-index order and packing. It cannot establish the chemical
meaning of an unpinned descriptor implementation or checkpoint compatibility.
"""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def header(path):
    with Path(path).open("rb") as stream:
        require(stream.read(6) == b"\x93NUMPY", "not an NPY file")
        version = stream.read(2)
        require(version in (b"\x01\x00", b"\x02\x00", b"\x03\x00"), "NPY version")
        width = 2 if version[0] == 1 else 4
        raw = stream.read(width)
        require(len(raw) == width, "truncated NPY header length")
        length = int.from_bytes(raw, "little")
        require(0 < length <= 65536, "NPY header length")
        raw = stream.read(length)
        require(len(raw) == length, "truncated NPY header")
        data = ast.literal_eval(raw.decode("utf-8" if version[0] == 3 else "latin1"))
        require(type(data) is dict and set(data) == {"descr", "fortran_order", "shape"}, "NPY header schema")
        require(data["fortran_order"] is False, "C-order required")
        require(type(data["shape"]) is tuple and all(type(n) is int and n >= 0 for n in data["shape"]), "NPY shape")
        require(type(data["descr"]) is str, "structured/object dtype forbidden")
        return data, stream.tell()


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def check(manifest, packed_path, indices_path):
    require(manifest.get("schema") == "casmi-fingerprint-contract/1", "manifest schema")
    base, bits, rows = (manifest.get(k) for k in ("base_bits", "selected_bits", "rows"))
    require(all(type(n) is int for n in (base, bits, rows)) and 0 < bits <= base <= 100000 and rows > 0, "manifest dimensions")
    require(manifest.get("bitorder") == "big", "only big-endian packbits supported")
    for key in ("indices_sha256", "packed_sha256"):
        require(type(manifest.get(key)) is str and re.fullmatch("[0-9a-f]{64}", manifest[key]), "required file SHA256")
    require(digest(indices_path) == manifest["indices_sha256"], "selected-index bytes/order differ")
    h, offset = header(indices_path)
    require(h["shape"] == (bits,), "selected-index count differs")
    match = re.fullmatch(r"([<>|])([iu])([1248])", h["descr"])
    require(match is not None, "selected indices must be explicit-endian integer NPY")
    endian, signed, itemsize = match.group(1), match.group(2) == "i", int(match.group(3))
    require(endian != "|" or itemsize == 1, "integer byte order")
    require(Path(indices_path).stat().st_size == offset + bits * itemsize, "selected-index payload size")
    with Path(indices_path).open("rb") as stream:
        stream.seek(offset)
        values = [int.from_bytes(stream.read(itemsize), "big" if endian == ">" else "little", signed=signed) for _ in range(bits)]
    require(len(set(values)) == bits and all(0 <= n < base for n in values), "duplicate/out-of-range selected indices")
    h, offset = header(packed_path)
    packed_width = (bits + 7) // 8
    require(h["descr"] == "|u1" and h["shape"] == (rows, packed_width), "packed uint8 shape differs")
    require(Path(packed_path).stat().st_size == offset + rows * packed_width, "packed payload size")
    require(digest(packed_path) == manifest["packed_sha256"], "packed bytes differ")
    padding = packed_width * 8 - bits
    if padding:
        mask = (1 << padding) - 1
        with Path(packed_path).open("rb") as stream:
            stream.seek(offset)
            while True:
                block = stream.read(packed_width * 1024)
                if not block:
                    break
                require(all(value & mask == 0 for value in block[packed_width - 1::packed_width]), "nonzero trailing padding bits")
    return {"status": "PASS_BYTE_AND_PACKING_CONTRACT", "rows": rows, "base_bits": base,
            "selected_bits": bits, "packed_bytes_per_row": packed_width, "padding_bits": padding,
            "chemical_semantics_verified": False, "checkpoint_compatibility_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("packed", type=Path)
    parser.add_argument("indices", type=Path)
    args = parser.parse_args()
    print(json.dumps(check(json.loads(args.manifest.read_text()), args.packed, args.indices), sort_keys=True))


if __name__ == "__main__":
    main()
