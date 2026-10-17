"""Write invented, fixed-seed NPY fixtures only; never reads competition data."""
import argparse
import json
import random
import struct
from pathlib import Path
from check_fp_contract import digest


def write_npy(path, descr, shape, payload):
    text = repr({"descr": descr, "fortran_order": False, "shape": shape})
    raw = text.encode("ascii")
    raw += b" " * ((-(10 + len(raw) + 1)) % 64) + b"\n"
    with Path(path).open("xb") as stream:
        stream.write(b"\x93NUMPY\x01\x00" + struct.pack("<H", len(raw)) + raw + payload)


def make_demo(output, bits=6930):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    if bits not in (6930, 10395):
        raise ValueError("demo bit count")
    width = (bits + 7) // 8
    rng = random.Random(20261018)
    payload = bytearray(rng.getrandbits(8) for _ in range(2 * width))
    for row in range(2):
        payload[(row + 1) * width - 1] &= 255 << (width * 8 - bits) & 255
    write_npy(output / "packed.npy", "|u1", (2, width), payload)
    write_npy(output / "indices.npy", "<i8", (bits,), b"".join(struct.pack("<q", n) for n in range(bits)))
    manifest = {"schema": "casmi-fingerprint-contract/1", "synthetic": True,
                "base_bits": 10407, "selected_bits": bits, "rows": 2, "bitorder": "big",
                "indices_sha256": digest(output / "indices.npy"),
                "packed_sha256": digest(output / "packed.npy")}
    with (output / "manifest.json").open("x") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--bits", type=int, choices=(6930, 10395), default=6930)
    args = parser.parse_args()
    make_demo(args.output, args.bits)
