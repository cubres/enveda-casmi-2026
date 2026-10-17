"""CPU-only invented fixtures: no third-party arrays, pickle or model execution."""
import tempfile
import unittest
from pathlib import Path
from check_fp_contract import check, digest, header
from make_demo import make_demo, write_npy


class ContractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "fixture"
        self.m = make_demo(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def run_check(self, manifest=None, packed=None, indices=None):
        return check(manifest or self.m, packed or self.path / "packed.npy", indices or self.path / "indices.npy")

    def test_selected6930(self):
        self.assertEqual(self.run_check()["padding_bits"], 6)

    def test_full10395(self):
        path = Path(self.temp.name) / "full"
        m = make_demo(path, 10395)
        self.assertEqual(check(m, path / "packed.npy", path / "indices.npy")["padding_bits"], 5)

    def test_width_swap(self):
        path = Path(self.temp.name) / "full"
        make_demo(path, 10395)
        with self.assertRaisesRegex(ValueError, "shape differs"):
            self.run_check(packed=path / "packed.npy")

    def test_order_changed(self):
        path = self.path / "indices.npy"
        raw = bytearray(path.read_bytes()); _, offset = header(path)
        raw[offset:offset+16] = raw[offset+8:offset+16] + raw[offset:offset+8]
        path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "bytes/order differ"):
            self.run_check()

    def test_duplicate_indices_even_if_rehashed(self):
        path = self.path / "indices.npy"
        raw = bytearray(path.read_bytes()); _, offset = header(path)
        raw[offset+8:offset+16] = raw[offset:offset+8]; path.write_bytes(raw)
        self.m["indices_sha256"] = digest(path)
        with self.assertRaisesRegex(ValueError, "duplicate/out-of-range"):
            self.run_check()

    def test_padding_even_if_rehashed(self):
        path = self.path / "packed.npy"
        raw = bytearray(path.read_bytes()); raw[-1] |= 1; path.write_bytes(raw)
        self.m["packed_sha256"] = digest(path)
        with self.assertRaisesRegex(ValueError, "padding"):
            self.run_check()

    def test_extra_payload_even_if_rehashed(self):
        path = self.path / "packed.npy"; path.write_bytes(path.read_bytes() + b"0")
        self.m["packed_sha256"] = digest(path)
        with self.assertRaisesRegex(ValueError, "payload size"):
            self.run_check()

    def test_object_npy_rejected(self):
        path = self.path / "object.npy"
        write_npy(path, "|O", (6930,), b"not a pickle")
        self.m["indices_sha256"] = digest(path)
        with self.assertRaisesRegex(ValueError, "integer NPY"):
            self.run_check(indices=path)


if __name__ == "__main__":
    unittest.main()
