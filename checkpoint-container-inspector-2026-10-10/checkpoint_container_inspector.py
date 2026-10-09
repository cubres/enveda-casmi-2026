"""Original offline metadata inspector. Never deserialize pickle or load weights.

Copyright 2026 cubres. SPDX-License-Identifier: MIT.
Bounded reads follow purported ZIP records, tiny markers or NPY headers.
Physical payload-access assurance on untrusted offsets remains unverified.
The result never certifies model, architecture, numerical or training compatibility.
"""
import argparse
import ast
import io
import json
import os
import platform
import re
import stat
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path


CEILINGS = {
    'file_bytes': 512 * 1024 * 1024, 'metadata_bytes': 5 * 1024 * 1024,
    'central_bytes': 4 * 1024 * 1024, 'members': 512, 'name_bytes': 256,
    'extra_bytes': 8192, 'member_comment_bytes': 256, 'npy_header_bytes': 8192,
    'ast_nodes': 128, 'ast_depth': 8, 'dimensions': 4,
    'dimension_size': 10_000_000, 'elements': 512_000_000,
}


@dataclass(frozen=True)
class Limits:
    file_bytes: int = 512 * 1024 * 1024
    metadata_bytes: int = 5 * 1024 * 1024
    central_bytes: int = 4 * 1024 * 1024
    members: int = 512
    name_bytes: int = 256
    extra_bytes: int = 8192
    member_comment_bytes: int = 256
    npy_header_bytes: int = 8192
    ast_nodes: int = 128
    ast_depth: int = 8
    dimensions: int = 4
    dimension_size: int = 10_000_000
    elements: int = 512_000_000

    def __post_init__(self):
        for name, maximum in CEILINGS.items():
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError('LIMIT_MUST_BE_POSITIVE_INTEGER_WITHIN_CEILING')


class Hold(Exception):
    """An explicit unsupported, malformed or out-of-budget condition."""


class Reader:
    def __init__(self, handle, limits):
        self.handle, self.limits, self.read_bytes = handle, limits, 0
        handle.seek(0, io.SEEK_END)
        self.size = handle.tell()
        if self.size < 0 or self.size > limits.file_bytes:
            raise Hold('FILE_SIZE_LIMIT')

    def read(self, offset, count):
        if offset < 0 or count < 0 or offset + count > self.size:
            raise Hold('TRUNCATED_RECORD')
        if self.read_bytes + count > self.limits.metadata_bytes:
            raise Hold('METADATA_READ_LIMIT')
        self.handle.seek(offset)
        data = self.handle.read(count)
        self.read_bytes += len(data)
        if len(data) != count:
            raise Hold('TRUNCATED_RECORD')
        return data


def _directory(r):
    # Bound EOCD/central directory before constructing any member collection.
    # Torch's usual no-comment archive lets us read exactly the final record.
    # A general 64 KiB backward search could read tensor/pickle bytes, so an
    # archive comment is outside this deliberately narrow inspector.
    if r.size < 22:
        raise Hold('ZIP_END_RECORD_MISSING')
    eocd_offset = r.size - 22
    tail = r.read(eocd_offset, 22)
    if tail[:4] != b'PK\x05\x06':
        raise Hold('ZIP_END_RECORD_MISSING')
    e = struct.unpack('<4s4H2IH', tail)
    if e[7] != 0:
        raise Hold('ZIP_TRAILING_OR_BAD_COMMENT')
    if e[1] != 0 or e[2] != 0 or e[3] != e[4]:
        raise Hold('MULTIDISK_ZIP_UNSUPPORTED')
    count, length, offset = e[4], e[5], e[6]
    if eocd_offset >= 20:
        locator = r.read(eocd_offset - 20, 20)
    else:
        locator = b''
    if locator[:4] == b'PK\x06\x07':
        _, disk, zoff, disks = struct.unpack('<4sIQI', locator)
        if disk != 0 or disks != 1:
            raise Hold('MULTIDISK_ZIP64_UNSUPPORTED')
        z = struct.unpack('<4sQ2H2I4Q', r.read(zoff, 56))
        if (z[0] != b'PK\x06\x06' or not 44 <= z[1] <= 4096 or
                zoff + 12 + z[1] != eocd_offset - 20 or z[4] or z[5] or z[6] != z[7]):
            raise Hold('INVALID_ZIP64_END_RECORD')
        for legacy, full, sentinel in ((count, z[7], 65535),
                                       (length, z[8], 0xffffffff),
                                       (offset, z[9], 0xffffffff)):
            if legacy != sentinel and legacy != full:
                raise Hold('ZIP64_LEGACY_DISAGREEMENT')
        count, length, offset = z[7], z[8], z[9]
        directory_end = zoff
    else:
        if count == 65535 or length == 0xffffffff or offset == 0xffffffff:
            raise Hold('ZIP64_LOCATOR_MISSING')
        directory_end = eocd_offset
    if count < 1 or count > r.limits.members:
        raise Hold('ZIP_MEMBER_COUNT_LIMIT')
    if length > r.limits.central_bytes or offset + length != directory_end:
        raise Hold('ZIP_DIRECTORY_SIZE_OR_EXTENT')
    return count, offset, r.read(offset, length)


def _zip64_values(extra, uncompressed, compressed, local_offset, disk):
    pos, record = 0, None
    while pos < len(extra):
        if pos + 4 > len(extra):
            raise Hold('TRUNCATED_ZIP_EXTRA')
        kind, n = struct.unpack_from('<HH', extra, pos)
        pos += 4
        if pos + n > len(extra):
            raise Hold('TRUNCATED_ZIP_EXTRA')
        if kind == 1:
            if record is not None:
                raise Hold('DUPLICATE_ZIP64_EXTRA')
            record = extra[pos:pos + n]
        pos += n
    values, used = [uncompressed, compressed, local_offset, disk], 0
    for i, sentinel in enumerate((0xffffffff, 0xffffffff, 0xffffffff, 65535)):
        if values[i] == sentinel:
            width = 4 if i == 3 else 8
            if record is None or used + width > len(record):
                raise Hold('ZIP64_MEMBER_EXTRA_MISSING')
            values[i] = int.from_bytes(record[used:used + width], 'little')
            used += width
    return values


def _safe_name(raw):
    try:
        name = raw.decode('ascii')
    except UnicodeDecodeError:
        raise Hold('NON_ASCII_MEMBER_UNSUPPORTED') from None
    parts = name.split('/')
    if (name.startswith('/') or '\\' in name or ':' in name or '\x00' in name or
            any(x in ('', '.', '..') for x in parts)):
        raise Hold('UNSAFE_MEMBER_PATH')
    if len(parts) < 2 or not re.fullmatch(r'[A-Za-z0-9_.-]{1,96}', parts[0]):
        raise Hold('UNSUPPORTED_TORCH_MEMBER_ROOT')
    return parts[0], '/'.join(parts[1:])


def _torch_zip(r):
    count, central_offset, data = _directory(r)
    pos, members, roots, names, ranges = 0, [], set(), set(), []
    for _ in range(count):
        if pos + 46 > len(data):
            raise Hold('TRUNCATED_CENTRAL_RECORD')
        c = struct.unpack_from('<4s6H3I5H2I', data, pos)
        if c[0] != b'PK\x01\x02':
            raise Hold('BAD_CENTRAL_SIGNATURE')
        n, ex, comment = c[10:13]
        if n < 1 or n > r.limits.name_bytes or ex > r.limits.extra_bytes or comment > r.limits.member_comment_bytes:
            raise Hold('ZIP_MEMBER_METADATA_LIMIT')
        end = pos + 46 + n + ex + comment
        if end > len(data):
            raise Hold('TRUNCATED_CENTRAL_RECORD')
        raw_name = data[pos + 46:pos + 46 + n]
        extra = data[pos + 46 + n:pos + 46 + n + ex]
        root, role = _safe_name(raw_name)
        roots.add(root)
        if raw_name in names:
            raise Hold('DUPLICATE_MEMBER_NAME')
        names.add(raw_name)
        size, compressed, local_offset, disk = _zip64_values(extra, c[9], c[8], c[16], c[13])
        if disk or c[3] & ~(0x800 | 8) or c[4] != 0:
            raise Hold('ENCRYPTED_COMPRESSED_OR_MULTIDISK_MEMBER')
        if stat.S_IFMT(c[15] >> 16) == stat.S_IFLNK:
            raise Hold('SYMLINK_MEMBER')
        if size != compressed or size > r.limits.file_bytes:
            raise Hold('MEMBER_SIZE_LIMIT_OR_STORED_MISMATCH')
        h = struct.unpack('<4s5H3I2H', r.read(local_offset, 30))
        if h[0] != b'PK\x03\x04' or h[2] != c[3] or h[3] != c[4] or h[9] != n or h[10] > r.limits.extra_bytes:
            raise Hold('LOCAL_CENTRAL_HEADER_DISAGREEMENT')
        if r.read(local_offset + 30, n) != raw_name:
            raise Hold('LOCAL_CENTRAL_NAME_DISAGREEMENT')
        if not c[3] & 8:
            local_extra = r.read(local_offset + 30 + n, h[10])
            local_size, local_compressed, _, _ = _zip64_values(local_extra, h[8], h[7], 0, 0)
            if local_size != size or local_compressed != compressed or h[6] != c[7]:
                raise Hold('LOCAL_CENTRAL_SIZE_OR_CRC_DISAGREEMENT')
        start = local_offset + 30 + n + h[10]
        if start + compressed > central_offset:
            raise Hold('MEMBER_OUTSIDE_PAYLOAD_EXTENT')
        ranges.append((local_offset, start + compressed))
        members.append({'role': role, 'bytes': size, 'offset': start, 'crc32': c[7]})
        pos = end
    if pos != len(data) or len(roots) != 1:
        raise Hold('DIRECTORY_COUNT_OR_ROOT_MISMATCH')
    ranges.sort()
    if any(left[1] > right[0] for left, right in zip(ranges, ranges[1:])):
        raise Hold('OVERLAPPING_MEMBER_EXTENTS')
    by_role = {m['role']: m for m in members}
    permitted = {'data.pkl', 'version', 'byteorder', '.data/serialization_id',
                 '.format_version', '.storage_alignment'}
    storages = [m for m in members if re.fullmatch(r'data/[0-9]+', m['role'])]
    if (not {'data.pkl', 'version'} <= set(by_role) or not storages or
            any(m['role'] not in permitted and not re.fullmatch(r'data/[0-9]+', m['role']) for m in members)):
        raise Hold('UNSUPPORTED_TORCH_STORAGE_LAYOUT')
    tiny = {}
    for role in ('version', 'byteorder'):
        if role in by_role:
            m = by_role[role]
            if not 1 <= m['bytes'] <= 32:
                raise Hold('TORCH_MARKER_SIZE_LIMIT')
            value = r.read(m['offset'], m['bytes'])
            if zlib.crc32(value) & 0xffffffff != m['crc32']:
                raise Hold('TORCH_MARKER_CRC_MISMATCH')
            if role == 'version':
                if re.fullmatch(rb'[0-9]{1,8}\n?', value) is None:
                    raise Hold('UNSUPPORTED_TORCH_VERSION_MARKER')
                tiny[role] = int(value.strip())
            else:
                if value not in (b'little', b'big'):
                    raise Hold('UNSUPPORTED_TORCH_BYTEORDER_MARKER')
                tiny[role] = value.decode('ascii')
    return {'format': 'torch_zip_storage_layout', 'metadata_status': 'PASS_BOUNDED_CONTAINER',
            'member_count': len(members), 'storage_count': len(storages),
            'declared_storage_bytes': sum(m['bytes'] for m in storages),
            'opaque_pickle_bytes': by_role['data.pkl']['bytes'], 'markers': tiny,
            'tensor_shapes': None,
            'full_crc_or_content_hash_verified': False}


def _npy(r):
    major, minor = r.read(6, 2)
    if (major, minor) == (1, 0):
        length, offset = int.from_bytes(r.read(8, 2), 'little'), 10
    elif (major, minor) in ((2, 0), (3, 0)):
        length, offset = int.from_bytes(r.read(8, 4), 'little'), 12
    else:
        raise Hold('UNSUPPORTED_NPY_VERSION')
    if length < 1 or length > r.limits.npy_header_bytes:
        raise Hold('NPY_HEADER_SIZE_LIMIT')
    raw = r.read(offset, length)
    if not raw.endswith(b'\n'):
        raise Hold('NPY_HEADER_NEWLINE_MISSING')
    try:
        tree = ast.parse(raw.decode('utf-8' if major == 3 else 'latin1').strip(), mode='eval')
    except (SyntaxError, UnicodeError, RecursionError):
        raise Hold('NPY_HEADER_PARSE_HOLD') from None
    allowed = (ast.Expression, ast.Dict, ast.Tuple, ast.Constant, ast.Load, ast.UnaryOp, ast.USub)
    stack, nodes = [(tree, 0)], 0
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if nodes > r.limits.ast_nodes or depth > r.limits.ast_depth or not isinstance(node, allowed):
            raise Hold('NPY_HEADER_AST_LIMIT_OR_UNSUPPORTED_SYNTAX')
        stack.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    if not isinstance(tree.body, ast.Dict):
        raise Hold('NPY_HEADER_NOT_DICTIONARY')
    keys = [n.value if isinstance(n, ast.Constant) else None for n in tree.body.keys]
    if len(keys) != 3 or set(keys) != {'descr', 'fortran_order', 'shape'}:
        raise Hold('NPY_HEADER_KEYS_OR_DUPLICATES')
    try:
        header = ast.literal_eval(tree)
    except (ValueError, TypeError, RecursionError):
        raise Hold('NPY_HEADER_LITERAL_HOLD') from None
    shape, dtype, fortran = header['shape'], header['descr'], header['fortran_order']
    if (not isinstance(shape, tuple) or len(shape) > r.limits.dimensions or
            any(type(n) is not int or n < 0 or n > r.limits.dimension_size for n in shape)):
        raise Hold('NPY_SHAPE_LIMIT')
    if type(fortran) is not bool or not isinstance(dtype, str):
        raise Hold('NPY_HEADER_TYPES')
    match = re.fullmatch(r'([<>=|])([uif])([1248])', dtype)
    if match is None or (match[2] == 'f' and match[3] == '1') or (match[1] == '|' and match[3] != '1'):
        raise Hold('NPY_OPAQUE_OR_UNSUPPORTED_DTYPE')
    count = 1
    for n in shape:
        count *= n
        if count > r.limits.elements:
            raise Hold('NPY_ELEMENT_LIMIT')
    byte_count = count * int(match[3])
    if offset + length + byte_count != r.size:
        raise Hold('NPY_PAYLOAD_LENGTH_MISMATCH')
    return {'format': 'npy_numeric_header', 'metadata_status': 'PASS_BOUNDED_HEADER',
            'shape': list(shape), 'dtype': dtype, 'fortran_order': fortran,
            'declared_elements': count, 'declared_payload_bytes': byte_count,
            'array_order_values_verified': False}


def inspect_stream(handle, limits=None):
    if limits is None:
        limits = Limits()
    r = None
    result = {'verdict': 'HOLD', 'architecture_status': 'UNVERIFIED',
              'numerical_status': 'UNVERIFIED', 'model_runtime_status': 'UNVERIFIED',
              'pickle_deserialized': False, 'model_objects_loaded': False,
              'payload_access_assurance': 'UNVERIFIED_ON_UNTRUSTED_OFFSETS'}
    if not isinstance(limits, Limits):
        result.update(metadata_status='HOLD', reason='INVALID_LIMITS_OBJECT')
        return result
    try:
        r = Reader(handle, limits)
        prefix = r.read(0, min(8, r.size))
        if prefix.startswith(b'PK\x03\x04'):
            result.update(_torch_zip(r))
        elif prefix.startswith(b'\x93NUMPY'):
            result.update(_npy(r))
        else:
            raise Hold('OPAQUE_OR_UNSUPPORTED_FORMAT')
        result['reason'] = 'MODEL_COMPATIBILITY_REQUIRES_SEPARATE_TRUSTED_VALIDATION'
    except (Hold, OSError, ValueError, struct.error) as exc:
        result['metadata_status'] = 'HOLD'
        result['reason'] = str(exc) if isinstance(exc, Hold) else type(exc).__name__
    finally:
        if r is not None:
            result['file_bytes'] = r.size
            result['metadata_bytes_read'] = r.read_bytes
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    args = parser.parse_args()
    try:
        with args.file.open('rb') as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
                raise Hold('REGULAR_FILE_REQUIRED')
            result = inspect_stream(f)
    except (OSError, Hold) as exc:
        result = {'verdict': 'HOLD', 'metadata_status': 'HOLD',
                  'reason': str(exc) if isinstance(exc, Hold) else type(exc).__name__}
    result['inspector_runtime'] = {'python': platform.python_version(),
                                   'byteorder': sys.byteorder,
                                   'framework_imported': False}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get('metadata_status', '').startswith('PASS_') else 2


if __name__ == '__main__':
    raise SystemExit(main())
