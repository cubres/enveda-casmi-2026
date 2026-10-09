"""Invented in-memory regressions. No checkpoints, pickle loaders or downloads."""
import io
import math
import stat
import struct
import unittest
import warnings
import zipfile

from checkpoint_container_inspector import Limits, inspect_stream


class TracedBytes(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.ranges = []

    def read(self, count=-1):
        if count < 0:
            raise AssertionError('Inspector attempted an unbounded read')
        start = self.tell()
        result = super().read(count)
        self.ranges.append((start, start + len(result)))
        return result


def torch_fixture(extra=(), compression=zipfile.ZIP_STORED, no_storage=False):
    f = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(f, 'w', compression=compression) as z:
            # Deliberately opaque bytes: the scanner must not inspect their
            # pickle semantics, regardless of names resembling executable ops.
            z.writestr('fixture/data.pkl', b'cos\nsystem\n(VNEVER EXECUTE\ntR.')
            z.writestr('fixture/version', b'3\n')
            z.writestr('fixture/byteorder', b'little')
            if not no_storage:
                z.writestr('fixture/data/0', b'WEIGHTS_NOT_TOUCHED!' * 4)
            for name, content in extra:
                z.writestr(name, content)
    return f.getvalue()


def npy_fixture(shape=(2, 3), dtype='<f4', version=1, payload=None, raw_header=None):
    text = raw_header if raw_header is not None else repr({
        'descr': dtype, 'fortran_order': False, 'shape': shape})
    length_bytes = 2 if version == 1 else 4
    prefix = b'\x93NUMPY' + bytes((version, 0))
    padding = (-len(text.encode()) - 1 - 8 - length_bytes) % 16
    header = text.encode() + b' ' * padding + b'\n'
    if payload is None:
        count = math.prod(shape)
        width = int(dtype[-1])
        if count * width > 4096:
            raise AssertionError('Fixture payload allocation exceeded test cap')
        payload = b'\x00' * (count * width)
    return prefix + len(header).to_bytes(length_bytes, 'little') + header + payload


def zip64_end(data, sentinels=False):
    e = list(struct.unpack('<4s4H2IH', data[-22:]))
    offset = len(data) - 22
    record = struct.pack('<4sQ2H2I4Q', b'PK\x06\x06', 44, 45, 45, 0, 0,
                         e[3], e[4], e[5], e[6])
    locator = struct.pack('<4sIQI', b'PK\x06\x07', 0, offset, 1)
    if sentinels:
        e[3] = e[4] = 65535
        e[5] = e[6] = 0xffffffff
    return data[:-22] + record + locator + struct.pack('<4s4H2IH', *e)


class InspectorTests(unittest.TestCase):
    def hold(self, data, reason=None, limits=None):
        result = inspect_stream(TracedBytes(data), limits)
        self.assertEqual(result['verdict'], 'HOLD')
        self.assertEqual(result['metadata_status'], 'HOLD')
        if reason:
            self.assertEqual(result['reason'], reason)
        return result

    def test_torch_metadata_is_not_model_compatibility(self):
        result = inspect_stream(TracedBytes(torch_fixture()))
        self.assertEqual(result['metadata_status'], 'PASS_BOUNDED_CONTAINER')
        self.assertEqual(result['verdict'], 'HOLD')
        self.assertEqual(result['markers'], {'version': 3, 'byteorder': 'little'})
        self.assertIsNone(result['tensor_shapes'])
        self.assertEqual(result['architecture_status'], 'UNVERIFIED')

    def test_wellformed_fixture_payload_ranges_untouched(self):
        data = torch_fixture()
        trace = TracedBytes(data)
        result = inspect_stream(trace)
        self.assertEqual(result['metadata_status'], 'PASS_BOUNDED_CONTAINER')
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in ('fixture/data.pkl', 'fixture/data/0'):
                info = z.getinfo(name)
                h = struct.unpack_from('<4s5H3I2H', data, info.header_offset)
                start = info.header_offset + 30 + h[9] + h[10]
                end = start + info.compress_size
                self.assertTrue(all(b <= start or a >= end for a, b in trace.ranges))
        self.assertFalse(result['pickle_deserialized'])
        self.assertFalse(result['model_objects_loaded'])
        self.assertEqual(result['payload_access_assurance'], 'UNVERIFIED_ON_UNTRUSTED_OFFSETS')

    def test_payload_corruption_is_explicitly_unverified(self):
        data = bytearray(torch_fixture())
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            i = z.getinfo('fixture/data/0')
            h = struct.unpack_from('<4s5H3I2H', data, i.header_offset)
            start = i.header_offset + 30 + h[9] + h[10]
        data[start] ^= 1
        result = inspect_stream(TracedBytes(data))
        self.assertEqual(result['metadata_status'], 'PASS_BOUNDED_CONTAINER')
        self.assertFalse(result['full_crc_or_content_hash_verified'])
        self.assertEqual(result['verdict'], 'HOLD')

    def test_zip64_end_bounded(self):
        for sentinel in (False, True):
            result = inspect_stream(TracedBytes(zip64_end(torch_fixture(), sentinel)))
            self.assertEqual(result['metadata_status'], 'PASS_BOUNDED_CONTAINER')

    def test_zip64_local_sizes(self):
        f = io.BytesIO()
        with zipfile.ZipFile(f, 'w') as z:
            for name, value in (('fixture/data.pkl', b'opaque'),
                                ('fixture/version', b'3'), ('fixture/data/0', b'abcd')):
                with z.open(name, 'w', force_zip64=True) as out:
                    out.write(value)
        self.assertEqual(inspect_stream(TracedBytes(f.getvalue()))['metadata_status'], 'PASS_BOUNDED_CONTAINER')

    def test_descriptor_layout(self):
        class NonSeekable(io.BytesIO):
            def seek(self, *args):
                raise OSError('invented nonseekable writer')
        f = NonSeekable()
        with zipfile.ZipFile(f, 'w') as z:
            for name, value in (('fixture/data.pkl', b'opaque'),
                                ('fixture/version', b'3'), ('fixture/data/0', b'abcd')):
                z.writestr(name, value)
        self.assertEqual(inspect_stream(TracedBytes(f.getvalue()))['metadata_status'], 'PASS_BOUNDED_CONTAINER')

    def test_duplicate_member(self):
        self.hold(torch_fixture((('fixture/version', b'3'),)), 'DUPLICATE_MEMBER_NAME')

    def test_unsafe_paths(self):
        for name in ('fixture/../bad', '/absolute/bad', 'C:/bad', 'fixture\\bad', 'fixture//bad'):
            self.hold(torch_fixture(((name, b'abc'),)), 'UNSAFE_MEMBER_PATH')

    def test_member_name_limit(self):
        self.hold(torch_fixture((('fixture/' + 'x' * 257, b'a'),)), 'ZIP_MEMBER_METADATA_LIMIT')

    def test_symlink(self):
        info = zipfile.ZipInfo('fixture/other')
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.hold(torch_fixture(((info, b'target'),)), 'SYMLINK_MEMBER')

    def test_compressed_members_are_unsupported(self):
        self.hold(torch_fixture(compression=zipfile.ZIP_DEFLATED), 'ENCRYPTED_COMPRESSED_OR_MULTIDISK_MEMBER')

    def test_unknown_torch_layout(self):
        self.hold(torch_fixture((('fixture/code/model.py', b'unexecuted text'),)), 'UNSUPPORTED_TORCH_STORAGE_LAYOUT')

    def test_storage_required(self):
        self.hold(torch_fixture(no_storage=True), 'UNSUPPORTED_TORCH_STORAGE_LAYOUT')

    def test_version_marker_size_limit(self):
        data = torch_fixture()
        f = io.BytesIO()
        with zipfile.ZipFile(f, 'w') as z:
            z.writestr('fixture/data.pkl', b'opaque')
            z.writestr('fixture/version', b'3' * 33)
            z.writestr('fixture/data/0', b'abc')
        self.hold(f.getvalue(), 'TORCH_MARKER_SIZE_LIMIT')

    def test_invalid_byteorder(self):
        f = io.BytesIO()
        with zipfile.ZipFile(f, 'w') as z:
            for name, value in (('fixture/data.pkl', b'opaque'), ('fixture/version', b'3'),
                                ('fixture/byteorder', b'unknown'), ('fixture/data/0', b'abc')):
                z.writestr(name, value)
        self.hold(f.getvalue(), 'UNSUPPORTED_TORCH_BYTEORDER_MARKER')

    def test_member_count_rejected_before_member_read(self):
        data = bytearray(torch_fixture())
        struct.pack_into('<HH', data, len(data) - 22 + 8, 513, 513)
        result = self.hold(data, 'ZIP_MEMBER_COUNT_LIMIT')
        self.assertLess(result['metadata_bytes_read'], 100)

    def test_central_size_limit(self):
        self.hold(torch_fixture(), 'ZIP_DIRECTORY_SIZE_OR_EXTENT', Limits(central_bytes=1))

    def test_local_central_crc_mismatch(self):
        data = bytearray(torch_fixture())
        at = data.find(b'PK\x01\x02')
        struct.pack_into('<I', data, at + 16, 0)
        self.hold(data, 'LOCAL_CENTRAL_SIZE_OR_CRC_DISAGREEMENT')

    def test_marker_crc_detects_changed_tiny_content(self):
        data = bytearray(torch_fixture())
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            i = z.getinfo('fixture/version')
            h = struct.unpack_from('<4s5H3I2H', data, i.header_offset)
            start = i.header_offset + 30 + h[9] + h[10]
        data[start] = ord('4')
        self.hold(data, 'TORCH_MARKER_CRC_MISMATCH')

    def test_comment_is_outside_narrow_format(self):
        data = io.BytesIO(torch_fixture())
        with zipfile.ZipFile(data, 'a') as z:
            z.comment = b'comment'
        self.hold(data.getvalue())

    def test_truncated_and_empty(self):
        for data in (b'', b'PK\x03\x04', torch_fixture()[:-5]):
            self.hold(data)

    def test_pickle_legacy_is_opaque(self):
        self.hold(b'\x80\x04opaque pickle bytes', 'OPAQUE_OR_UNSUPPORTED_FORMAT')

    def test_whole_file_cap(self):
        self.hold(torch_fixture(), 'FILE_SIZE_LIMIT', Limits(file_bytes=4))

    def test_metadata_byte_cap(self):
        self.hold(torch_fixture(), 'METADATA_READ_LIMIT', Limits(metadata_bytes=8))

    def test_npy_numeric_header(self):
        data = npy_fixture()
        trace = TracedBytes(data)
        result = inspect_stream(trace)
        self.assertEqual(result['metadata_status'], 'PASS_BOUNDED_HEADER')
        self.assertEqual(result['shape'], [2, 3])
        self.assertEqual(result['dtype'], '<f4')
        header_end = 10 + int.from_bytes(data[8:10], 'little')
        self.assertTrue(all(end <= header_end for start, end in trace.ranges))
        self.assertEqual(result['verdict'], 'HOLD')

    def test_npy_versions(self):
        for version in (1, 2, 3):
            self.assertEqual(inspect_stream(TracedBytes(npy_fixture(version=version)))['metadata_status'], 'PASS_BOUNDED_HEADER')

    def test_npy_zero_size(self):
        result = inspect_stream(TracedBytes(npy_fixture(shape=(0, 3))))
        self.assertEqual(result['metadata_status'], 'PASS_BOUNDED_HEADER')
        self.assertEqual(result['declared_payload_bytes'], 0)

    def test_npy_object_and_string_are_opaque(self):
        for dtype in ('|O8', '|S8', '<c8'):
            self.hold(npy_fixture(dtype=dtype), 'NPY_OPAQUE_OR_UNSUPPORTED_DTYPE')

    def test_npy_call_is_not_executed(self):
        text = "{'descr':'<f4','fortran_order':False,'shape':(__import__('os').getpid(),)}"
        self.hold(npy_fixture(raw_header=text), 'NPY_HEADER_AST_LIMIT_OR_UNSUPPORTED_SYNTAX')

    def test_npy_duplicate_keys(self):
        text = "{'descr':'<f4','fortran_order':False,'shape':(2,),'shape':(0,)}"
        self.hold(npy_fixture(raw_header=text), 'NPY_HEADER_KEYS_OR_DUPLICATES')

    def test_npy_negative_bool_or_large_dimension(self):
        for shape in ((-1,), (True,), (10_000_001,)):
            self.hold(npy_fixture(shape=shape, payload=b''), 'NPY_SHAPE_LIMIT')

    def test_npy_rank_limit(self):
        self.hold(npy_fixture(shape=(1, 1, 1, 1, 1)), 'NPY_SHAPE_LIMIT')

    def test_npy_element_limit(self):
        self.hold(npy_fixture(shape=(1_000_000, 1000), payload=b''), 'NPY_ELEMENT_LIMIT')

    def test_npy_header_size_limit(self):
        self.hold(npy_fixture(), 'NPY_HEADER_SIZE_LIMIT', Limits(npy_header_bytes=1))

    def test_npy_ast_limit(self):
        self.hold(npy_fixture(), 'NPY_HEADER_AST_LIMIT_OR_UNSUPPORTED_SYNTAX', Limits(ast_nodes=2))

    def test_npy_truncated_and_extra_payload(self):
        data = npy_fixture()
        for malformed in (data[:-1], data + b'x'):
            self.hold(malformed, 'NPY_PAYLOAD_LENGTH_MISMATCH')

    def test_npy_fortran_type(self):
        text = "{'descr':'<f4','fortran_order':'no','shape':(2,3)}"
        self.hold(npy_fixture(raw_header=text), 'NPY_HEADER_TYPES')

    def test_forged_offset_can_touch_opaque_bytes_before_hold(self):
        data = bytearray(torch_fixture())
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            i = z.getinfo('fixture/data.pkl')
            h = struct.unpack_from('<4s5H3I2H', data, i.header_offset)
            start = i.header_offset + 30 + h[9] + h[10]
            end = start + i.compress_size
        central = data.find(b'PK\x01\x02')
        struct.pack_into('<I', data, central + 42, start)
        trace = TracedBytes(data)
        result = inspect_stream(trace)
        self.assertEqual(result['metadata_status'], 'HOLD')
        self.assertTrue(any(a < end and b > start for a, b in trace.ranges))
        self.assertEqual(result['payload_access_assurance'], 'UNVERIFIED_ON_UNTRUSTED_OFFSETS')
        self.assertFalse(result['pickle_deserialized'])
        self.assertFalse(result['model_objects_loaded'])

    def test_limits_reject_invalid_or_above_ceiling_values(self):
        for values in ({'file_bytes': 0}, {'metadata_bytes': -1}, {'members': True},
                       {'npy_header_bytes': 1.5}, {'ast_nodes': '128'},
                       {'file_bytes': 513 * 1024 * 1024}):
            with self.assertRaises(ValueError):
                Limits(**values)

    def test_invalid_limits_object_does_not_read_input(self):
        for invalid in (False, 0, {}, 'limits'):
            trace = TracedBytes(torch_fixture())
            result = inspect_stream(trace, invalid)
            self.assertEqual(result['reason'], 'INVALID_LIMITS_OBJECT')
            self.assertEqual(result['metadata_status'], 'HOLD')
            self.assertEqual(trace.ranges, [])


if __name__ == '__main__':
    unittest.main()
