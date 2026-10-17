"""One admitted native job: exact mechanical canary, then pure V6 inference.

No old ranker, second list, blend, training, unsafe loader or artifact discovery.
All paths and bytes are explicit in a root-bound, public-source-safe config.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import resource
import signal
import stat
import sys
import time
import zipfile
import zlib

WORK = Path('/kaggle/working/casmi_v6_native_once')
MARKER = WORK / 'V6_NATIVE_SCIENCE_ONE_ATTEMPT.json'
WEIGHT_SHA = '9c46ca4fcf19002fecbcded0d0808e8a81e3a25a143e684e259f265c44a5be31'
FULL_MASK_SHA = 'f771cb6aa87a418b06d9abfbdac0c1759040afb955b9dfa59e8932105a65bdc6'
MODEL_SOURCE_SHA = '69f2656778a08233e22235bf4853f0b3d2420b431390a32d6c8ed453cde85c76'
PARSER_SHA = '1f10d75ba7daa86e6979811ffb382f28c34bb04436c2291dd69eff2bb8f42294'
SPEC_SHA = '99dbf966d2607e2da8085a6550206a71fc912d2c90b9555a725a2569e4af4500'
ROLES_SHA = 'fe654a3f5f655df3897a344ca222e01a9f555a7dfd22a786e6cb32b126c76049'
POOL_FP_SHA = '84afb2d17d567359963f1941c4c8b20523770aad4167ccc0bd715530360611e0'
POOL_META_SHA = '53c276a6625f38c90d93e3a8c23c25a2d08712754358b1160f6683e42a922324'
POOL_MASS_SHA = '0d28d5c288201e3598ba2fffea7f3d7284e397341ab0d72e5111b4cc67dabd1e'
POOL_MANIFEST_SHA = '5b08ca4b830de1558be4ce568a10f0997b5fa2fe875a872dcd6a216f901fd9ef'
STRUCTURE_META_SHA = '88411e98cec6f862f7b121dbc27b807e5e18782416219fe2b11566deb3254132'
RDKIT_WHEEL_SHA = 'c69a40ad52a2489cf592d55b41f5f6fa482f028341c038f3ed7d6b46834d1d3d'
TRAIN_SHA = '9423f90ec08b941a9646b535bf0606183e86ff0c5a297978f5a70693d41bcd98'

# Diagnostics are fixed public categories only; never raw error text or data.
PUBLIC_FAILURE_CODES = frozenset(('ACTUAL_MAPPING_RECEIPT_PIN_REQUIRED', 'ACTUAL_NATIVE_CANARY_REQUIRED_BEFORE_SERVING', 'ACTUAL_NATIVE_RUNTIME_DRIFT', 'ACTUAL_TEST_OR_SAMPLE_SCHEMA', 'CACHE_OFFSETS_SCHEMA', 'CANARY_NONEMPTY_PREPARED_SEQUENCE', 'CANARY_SOURCE_ROW_JOIN_NOT_UNIQUE', 'CANDIDATE_WINDOW_MISSING_OR_PREALLOCATION_CAP', 'COMPETITION_INPUT_CHANGED_DURING_NATIVE_JOB', 'COMPETITION_MOUNT_IDENTITY', 'CONFIG_CAP', 'CUDA_UNAVAILABLE', 'DECODED_ROLE_TABLE_DRIFT', 'DUPLICATE_JSON_KEY', 'ENTRY_OR_CONFIG_DRIFT', 'EXACT_COMPLETED_ROOT_CSV_READBACK', 'EXACT_EMBEDDED_SOURCE_SET', 'EXACT_GATHER_DIGEST', 'EXACT_GATHER_SCHEMA', 'EXACT_MOLECULE_SET', 'EXACT_NATIVE_ROUTE', 'EXACT_OFFICIAL_RDKIT_WHEEL_REQUIRED', 'EXACT_OWNED_ARTIFACT_REQUIRED', 'EXACT_RDKIT_WHEEL_ABI_REQUIRED', 'EXACT_REQUIRED_INPUT_SET', 'EXACT_STRING_SEQUENCE_SCHEMA', 'EXACT_SUBMISSION_SCHEMA', 'EXACT_TRAINING_PREPROCESSING_REFERENCE_DRIFT:adduct_index', 'EXACT_TRAINING_PREPROCESSING_REFERENCE_DRIFT:collision_energy', 'EXACT_TRAINING_PREPROCESSING_REFERENCE_DRIFT:instrument_index', 'EXACT_TRAINING_PREPROCESSING_REFERENCE_DRIFT:intensity', 'EXACT_TRAINING_PREPROCESSING_REFERENCE_DRIFT:ion_mode', 'EXACT_TRAINING_PREPROCESSING_REFERENCE_DRIFT:mz', 'EXACT_TRAINING_PREPROCESSING_REFERENCE_DRIFT:precursor', 'EXACT_V6_CHECKPOINT_BYTES_REQUIRED', 'EXACT_WHEEL_INVENTORY', 'EXCLUSIVE_DEPENDENCY_DIRECTORY_REQUIRED', 'EXPLICIT_BACKEND_REQUIRED', 'EXPLICIT_DISPATCH_SCOPE', 'EXPLICIT_NPY_HEADER_VERSION', 'EXPLICIT_REGULAR_FILE_REQUIRED', 'FILE_BINDING_SCHEMA', 'FINITE_CANDIDATE_SCORES_REQUIRED', 'FINITE_FULL_LOGITS_REQUIRED', 'FINITE_NATIVE_FULL_HEAD_REQUIRED', 'FULL_CANDIDATE_BITS_REQUIRED', 'FULL_JOB_DEADLINE_EXPIRED_AT_CANARY', 'FULL_MASK_SCHEMA', 'FULL_POOL_KEY_UNIQUENESS', 'FULL_POOL_MASS_SCHEMA_OR_ORDER', 'FULL_POOL_METADATA_CAP', 'FULL_POOL_METADATA_SCHEMA', 'FULL_POOL_PACKED_SCHEMA', 'FULL_RAW_LOGITS_REQUIRED', 'INDEPENDENT_FULL10395_CANDIDATE_FINGERPRINT_PARITY', 'INDEPENDENT_PREPARED_CACHE_FIELDS', 'INPUT_CHANGED_DURING_NATIVE_JOB', 'INVALID_CANDIDATE_SMILES', 'JSON_INPUT_CAP', 'MANYLINUX_2_28_COMPATIBLE_GLIBC_REQUIRED', 'MAPPING_QUALIFICATION_SCOPE', 'MAPPING_RECEIPT_CAP', 'MOLECULE_OBSERVED_NEUTRAL_MASS_MISSING', 'MOUNT_BYTE_BINDING', 'MPS_UNAVAILABLE_OR_FALLBACK', 'NATIVE_RSS_LIMIT', 'NONFINITE_JSON_CONSTANT', 'ONE_CANARY_SCOPE_REQUIRED', 'ONE_JOB_ALREADY_CONSUMED_OR_OUTPUT_EXISTS', 'OPTIMIZER_CANARY_MISSING', 'OPTIMIZER_FULL_BANK_CANARY_MISSING', 'OWNED_ARCHITECTURE_OR_FEATURIZER_DRIFT', 'OWNED_PREPROCESSOR_SOURCE_DRIFT', 'OWNED_SOURCE_DRIFT', 'OWNED_SOURCE_IMPORT_ROUTE', 'PREPARED_METADATA_SCHEMA', 'PREPARED_PEAK_SCHEMA', 'PREPARED_REFERENCE_DIMENSION:adduct_index', 'PREPARED_REFERENCE_DIMENSION:collision_energy', 'PREPARED_REFERENCE_DIMENSION:instrument_index', 'PREPARED_REFERENCE_DIMENSION:intensity', 'PREPARED_REFERENCE_DIMENSION:ion_mode', 'PREPARED_REFERENCE_DIMENSION:mz', 'PREPARED_REFERENCE_DIMENSION:precursor', 'PREPARED_REFERENCE_SCHEMA', 'RAW_DESCRIPTOR_RECIPE_DRIFT', 'REGULAR_EXPLICIT_FILE_REQUIRED', 'ROLE_STORAGE_SIZE', 'ROOT_FULL_BANK_PREPARATION_REVIEW_REQUIRED', 'ROOT_NATIVE_SCOPE', 'ROOT_SERVING_QUALIFICATION_MISSING', 'SELECTED_CACHE_MEMBER_SCHEMA', 'SELECTED_CACHE_MEMBER_TRUNCATED', 'SELECTED_CACHE_SLICE_BOUND', 'SINGLE_CANARY_FORWARD_CONSUMED', 'SOURCE_JOIN_SCHEMA', 'SOURCE_ROW_NOT_FOUND', 'SOURCE_ROW_SCHEMA', 'STRUCTURE_KEY_JOIN_NOT_UNIQUE', 'SYMBOLIC_STRING_ARRAY_REQUIRED', 'SYMBOLIC_STRING_DTYPE_REQUIRED', 'UNIQUE_CACHE_MEMBER_REQUIRED', 'V6_ARCHITECTURE_OR_FINITE_STATE_DRIFT', 'V6_CHECKPOINT_SEMANTICS_DRIFT', 'VALID_TOP25_REQUIRED', 'WHEEL_MEMBER_BYTES', 'WHEEL_MEMBER_PATH_TYPE_OR_SIZE'))
PUBLIC_FAILURE_PHASES = frozenset(('input_byte_binding', 'offline_dependency_bootstrap', 'scientific_imports_and_runtime', 'scientific_source_binding', 'full_mask', 'candidate_bank', 'raw_preprocessing_canary', 'candidate_fingerprint_canary', 'model_canary_construction', 'model_canary_forward', 'conditional_full_model', 'full_input_loading', 'full_molecule_scoring', 'final_input_recheck', 'root_output_validation'))


def public_failure_diagnostic(error, phase):
    code = (str(error) if type(error) is ValueError and str(error) in PUBLIC_FAILURE_CODES
            else "UNCLASSIFIED_NATIVE_SCIENCE_FAILURE")
    return {"phase": phase if type(phase) is str and phase in PUBLIC_FAILURE_PHASES else "unknown",
            "error_code": code, "private_values_published": False}


def need(ok, code):
    if not ok:
        raise ValueError(code)


def sha(path):
    path = Path(path)
    need(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), 'REGULAR_EXPLICIT_FILE_REQUIRED')
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            result.update(block)
    return result.hexdigest()


def write_new(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def unique_pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def rejected_constant(value):
    raise ValueError('NONFINITE_JSON_CONSTANT')


def bounded_json(path, cap=65536):
    need(Path(path).stat().st_size <= cap, 'JSON_INPUT_CAP')
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique_pairs,
                      parse_constant=rejected_constant)


def check_budget(config):
    need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 <= config['peak_rss_limit_bytes'],
         'NATIVE_RSS_LIMIT')


def imported(path, expected, name):
    need(sha(path) == expected, 'OWNED_SOURCE_DRIFT')
    spec = importlib.util.spec_from_file_location(name, path)
    need(spec is not None and spec.loader is not None, 'OWNED_SOURCE_IMPORT_ROUTE')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pinned_files(config):
    paths = {}
    for label, record in config['files'].items():
        need(type(record) is dict and set(record) == {'path', 'bytes', 'sha256'}, 'FILE_BINDING_SCHEMA')
        path = Path(record['path'])
        need(type(record['bytes']) is int and record['bytes'] > 0
             and type(record['sha256']) is str and re.fullmatch('[0-9a-f]{64}', record['sha256'])
             and path.is_absolute() and '..' not in path.parts and str(path).startswith('/kaggle/input/')
             and path.stat().st_size == record['bytes'] and sha(path) == record['sha256'], 'MOUNT_BYTE_BINDING')
        paths[label] = path
    expected = {'checkpoint': WEIGHT_SHA, 'full_mask': FULL_MASK_SHA,
                'spectrum_cache': SPEC_SHA, 'structure_roles': ROLES_SHA,
                'pool_meta': POOL_META_SHA, 'pool_mass': POOL_MASS_SHA, 'pool_fp': POOL_FP_SHA,
                'structure_meta': STRUCTURE_META_SHA, 'rdkit_wheel': RDKIT_WHEEL_SHA,
                'train': TRAIN_SHA}
    for label, expected_sha in expected.items():
        need(config['files'][label]['sha256'] == expected_sha, 'EXACT_OWNED_ARTIFACT_REQUIRED')
    need(set(paths) == set(expected), 'EXACT_REQUIRED_INPUT_SET')
    return paths


def bootstrap_rdkit(wheel, config):
    """Expand the exact public wheel in a fresh private temp directory, offline."""
    need(sys.version_info[:2] == (3, 12) and platform.machine() == 'x86_64'
         and sys.byteorder == 'little' and 'rdkit' not in sys.modules,
         'EXACT_RDKIT_WHEEL_ABI_REQUIRED')
    libc_name, libc_version = platform.libc_ver()
    need(libc_name == 'glibc' and re.fullmatch(r'[0-9]+\.[0-9]+(?:\.[0-9]+)*', libc_version)
         and tuple(int(part) for part in libc_version.split('.')[:2]) >= (2, 28),
         'MANYLINUX_2_28_COMPATIBLE_GLIBC_REQUIRED')
    need(Path(wheel).stat().st_size == 37188323 and sha(wheel) == RDKIT_WHEEL_SHA,
         'EXACT_OFFICIAL_RDKIT_WHEEL_REQUIRED')
    destination = Path('/tmp/casmi_v6_dependency_once')
    need(not destination.exists() and not any(p.is_symlink() for p in (destination, *destination.parents)),
         'EXCLUSIVE_DEPENDENCY_DIRECTORY_REQUIRED')
    with zipfile.ZipFile(wheel) as archive:
        members = archive.infolist()
        need(len(members) == 1140 and sum(entry.file_size for entry in members) == 146955986
             and len({entry.filename for entry in members}) == len(members), 'EXACT_WHEEL_INVENTORY')
        for entry in members:
            path = Path(entry.filename)
            mode = entry.external_attr >> 16
            need(not path.is_absolute() and path.parts and '..' not in path.parts
                 and '\\' not in entry.filename and '\x00' not in entry.filename
                 and path.parts[0] in {'rdkit', 'rdkit.libs', 'rdkit-stubs', 'rdkit-2026.3.3.dist-info'}
                 and (stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR))
                 and not entry.flag_bits & 1 and 0 <= entry.file_size <= 64*(1 << 20),
                 'WHEEL_MEMBER_PATH_TYPE_OR_SIZE')
        os.mkdir(destination, mode=0o700)
        for entry in members:
            target = destination / entry.filename
            if entry.is_dir():
                target.mkdir(mode=0o700, parents=True, exist_ok=True)
            else:
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                body = archive.read(entry)
                need(len(body) == entry.file_size, 'WHEEL_MEMBER_BYTES')
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(body)
            check_budget(config)
    sys.path.insert(0, str(destination))
    return destination


def symbolic_strings(value, parser, expected_count, cap):
    if type(value) is list:
        result = tuple(value)
    else:
        need(type(value) is parser.ArrayState and value.built and value.count == expected_count,
             'SYMBOLIC_STRING_ARRAY_REQUIRED')
        if value.dtype.code == 'O8':
            result = value.payload
        else:
            need(value.dtype.width is not None, 'SYMBOLIC_STRING_DTYPE_REQUIRED')
            width = 4 * value.dtype.width
            codec = 'utf-32-le' if value.dtype.order == '<' else 'utf-32-be'
            result = tuple(value.payload[i:i+width].decode(codec, errors='strict').rstrip('\x00')
                           for i in range(0, len(value.payload), width))
    need(len(result) == expected_count and all(type(x) is str and x and '\x00' not in x
         and len(x.encode('utf-8')) <= cap for x in result), 'EXACT_STRING_SEQUENCE_SCHEMA')
    return result


def full_pool_metadata(path, parser):
    need(path.stat().st_size <= 80 * (1 << 20), 'FULL_POOL_METADATA_CAP')
    parsed = parser.parse_primitive_metadata(path.read_bytes())
    need(type(parsed) is dict and set(parsed) == {'keys', 'smiles', 'src', 'npl', 'nbits'}
         and type(parsed['nbits']) is int and parsed['nbits'] == 10395, 'FULL_POOL_METADATA_SCHEMA')
    keys = symbolic_strings(parsed['keys'], parser, 711705, 1024)
    smiles = symbolic_strings(parsed['smiles'], parser, 711705, 16384)
    need(len(set(keys)) == len(keys), 'FULL_POOL_KEY_UNIQUENESS')
    return keys, smiles


def raw_row(parquet, row_index, columns, pq):
    need(type(row_index) is int and row_index >= 0, 'SOURCE_ROW_SCHEMA')
    offset = 0
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=4096, columns=columns):
        if row_index < offset+batch.num_rows:
            return batch.slice(row_index-offset, 1).to_pylist()[0]
        offset += batch.num_rows
    raise ValueError('SOURCE_ROW_NOT_FOUND')


def selected_cache_values(archive, name, begin, count, dtype, np):
    """Return only the frozen optimizer row's bytes, never a whole feature array."""
    need(type(begin) is int and begin >= 0 and type(count) is int and 0 < count <= 128,
         'SELECTED_CACHE_SLICE_BOUND')
    need(archive.namelist().count(name + '.npy') == 1, 'UNIQUE_CACHE_MEMBER_REQUIRED')
    with archive.open(name + '.npy', 'r') as member:
        version = np.lib.format.read_magic(member)
        need(version in ((1, 0), (2, 0)), 'EXPLICIT_NPY_HEADER_VERSION')
        reader = (np.lib.format.read_array_header_1_0 if version == (1, 0)
                  else np.lib.format.read_array_header_2_0)
        shape, fortran, actual_dtype = reader(member)
        need(len(shape) == 1 and fortran is False and actual_dtype == np.dtype(dtype)
             and begin + count <= shape[0], 'SELECTED_CACHE_MEMBER_SCHEMA')
        start = member.tell()
        member.seek(start + begin * actual_dtype.itemsize)
        body = member.read(count * actual_dtype.itemsize)
        need(len(body) == count * actual_dtype.itemsize, 'SELECTED_CACHE_MEMBER_TRUNCATED')
    return np.frombuffer(body, dtype=actual_dtype).copy()


def canary_reference(paths, np, pq, fpmodel, scoring):
    # Stored src provides the original source-row join. No answer/quality is read.
    with np.load(paths['spectrum_cache'], allow_pickle=False) as stored:
        need(set(('off','mz','it','prec','ad','ins','ce','mode','six','src')) <= set(stored.files),
             'INDEPENDENT_PREPARED_CACHE_FIELDS')
        six, src = stored['six'], stored['src']
        need(six.ndim == src.ndim == 1 and six.shape == src.shape and six.dtype.kind in 'iu'
             and src.dtype.kind in 'iu' and np.all((six >= 0) & (six < 275810)), 'SOURCE_JOIN_SCHEMA')
        encoded = base64.b64decode(paths['structure_roles'].read_text().strip(), validate=True)
        raw = zlib.decompress(encoded)
        need(len(raw) == (2*275810+7)//8, 'ROLE_STORAGE_SIZE')
        bits = np.unpackbits(np.frombuffer(raw, np.uint8), bitorder='big')[:2*275810].reshape(-1, 2)
        roles = 2*bits[:, 0]+bits[:, 1]
        need(hashlib.sha256(roles.tobytes()).hexdigest() == scoring.ROLE_SHA, 'DECODED_ROLE_TABLE_DRIFT')
        off = stored['off']
        need(off.shape == (len(six)+1,) and off.dtype.kind in 'iu' and off[0] == 0
             and np.all(off[1:] >= off[:-1]), 'CACHE_OFFSETS_SCHEMA')
        ids = np.flatnonzero((roles[six] == 0) & (np.diff(off) > 0))
        need(len(ids) > 0, 'OPTIMIZER_CANARY_MISSING')
        selected = int(ids[np.argmin(src[ids])])
        source_row = int(src[selected])
        need(np.count_nonzero(src == source_row) == 1, 'CANARY_SOURCE_ROW_JOIN_NOT_UNIQUE')
        begin, end = int(off[selected]), int(off[selected+1])
        need(end > begin, 'CANARY_NONEMPTY_PREPARED_SEQUENCE')
    with zipfile.ZipFile(paths['spectrum_cache']) as archive:
        scalar = lambda name, dtype: selected_cache_values(archive, name, selected, 1, dtype, np)[0]
        ce = np.float32(scalar('ce', 'float32'))
        reference = dict(mz=selected_cache_values(archive, 'mz', begin, min(end-begin,128), 'float32', np),
            intensity=selected_cache_values(archive, 'it', begin, min(end-begin,128), 'float32', np),
            precursor=np.float32(scalar('prec', 'float32')), adduct_index=np.int64(scalar('ad', 'int16')),
            instrument_index=np.int64(scalar('ins', 'int8')),
            collision_energy=np.float32(25. if ce < 0 else ce), ion_mode=np.float32(scalar('mode', 'float32')))
    columns = ['precursor_mz','adduct','instrument_type','ionization_mode','collision_energy_ev',
               'ms2_mzs','ms2_normalized_intensities']
    original = raw_row(paths['train'], source_row, columns, pq)
    prepared = scoring.prepare_raw_spectrum(original, fpmodel)
    scoring.qualify_prepared_reference(prepared, reference)
    private_binding = dict(raw_sha256=hashlib.sha256(json.dumps(original, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest(),
        prepared_sha256=hashlib.sha256(b''.join(name.encode('ascii') + b'\0' +
            np.asarray(prepared[name]).tobytes() for name in sorted(prepared))).hexdigest())
    # Row/index/values and derived hashes remain private in memory, never output.
    return prepared, roles, private_binding


def neutral_mass(row):
    # Observed adduct arithmetic, including electron correction for sodium ions.
    H, C, N, O, Na, K, Cl, E = 1.00782503207, 12., 14.0030740048, 15.9949146196, 22.9897692809, 38.96370668, 34.96885268, .00054857990
    p, water, nh4 = H-E, 2*H+O, N+4*H
    formate, acetate = C+2*H+2*O, 2*C+4*H+2*O
    shifts = {'[M+H]+':(1,1,p),'[M+NH4]+':(1,1,nh4-E),'[M+Na]+':(1,1,Na-E),
        '[M+K]+':(1,1,K-E),'[M-H2O+H]+':(1,1,p-water),'[M-2H2O+H]+':(1,1,p-2*water),
        '[M+2H]2+':(1,2,2*p),'[M]+':(1,1,-E),'[M-H2O]+':(1,1,-E-water),
        '[M+CH3OH+H]+':(1,1,p+C+4*H+O),'[M+CH3CN+H]+':(1,1,p+2*C+3*H+N),
        '[M-H]-':(1,1,-p),'[M-H2O-H]-':(1,1,-p-water),'[M+CH2O2-H]-':(1,1,formate-p),
        '[M+C2H4O2-H]-':(1,1,acetate-p),'[M+Cl]-':(1,1,Cl+E),'[M]-':(1,1,E),
        '[M-2H]-':(1,2,-2*p),'[M-2H]2-':(1,2,-2*p),'[M+Na-2H]-':(1,1,Na-E-2*p),
        '[2M+H]+':(2,1,p),'[2M+Na]+':(2,1,Na-E),'[2M+NH4]+':(2,1,nh4-E),
        '[2M+K]+':(2,1,K-E),'[2M-H]-':(2,1,-p),'[2M+CH2O2-H]-':(2,1,formate-p),
        '[2M+C2H4O2-H]-':(2,1,acetate-p),'[2M+Na-2H]-':(2,1,Na-E-2*p),
        '[3M+H]+':(3,1,p),'[3M-H]-':(3,1,-p)}
    entry = shifts.get(row['adduct'])
    if entry is None:
        return float('nan')
    n, z, delta = entry
    try:
        return (float(row['precursor_mz'])*z-delta)/n
    except (TypeError, ValueError):
        return float('nan')


def candidate_pool(paths, parser, np, config):
    # Reuse the exact full bank's row order, mass filter and provenance. Never
    # reconstruct it by reading training labels or combining a different bank.
    need(config['full_bank_preparation_manifest_sha256'] == POOL_MANIFEST_SHA
         and config['full_bank_row_alignment_source_reviewed'] is True,
         'ROOT_FULL_BANK_PREPARATION_REVIEW_REQUIRED')
    keys, smiles = full_pool_metadata(paths['pool_meta'], parser)
    check_budget(config)
    mass = np.load(paths['pool_mass'], mmap_mode='r', allow_pickle=False)
    packed = np.load(paths['pool_fp'], mmap_mode='r', allow_pickle=False)
    need(mass.shape == (711705,) and mass.dtype == np.float64 and np.isfinite(mass).all()
         and np.all((mass >= 80) & (mass <= 1400)) and np.all(mass[1:] >= mass[:-1]),
         'FULL_POOL_MASS_SCHEMA_OR_ORDER')
    need(packed.shape == (711705, 1300) and packed.dtype == np.uint8,
         'FULL_POOL_PACKED_SCHEMA')
    check_budget(config)
    return mass, keys, smiles, packed


def full_bits(smiles, mask, generators, np, Chem, MACCSkeys):
    molecule = Chem.MolFromSmiles(smiles)
    need(molecule is not None, 'INVALID_CANDIDATE_SMILES')
    raw = np.concatenate([g.GetFingerprintAsNumPy(molecule).astype(np.uint8) for g in generators]
                         + [np.asarray(MACCSkeys.GenMACCSKeys(molecule), np.uint8)])
    need(raw.shape == (10407,), 'RAW_DESCRIPTOR_RECIPE_DRIFT')
    return raw[mask]


def candidate_canary(paths, parser, mask, generators, np, Chem, MACCSkeys, keys, smiles, packed, roles):
    # Freeze the first optimizer key in original full-bank order before computing
    # any fingerprint. No role1/2/3 structure is a canary and no score is read.
    structure = parser.parse_primitive_metadata(paths['structure_meta'].read_bytes())
    projected, _ = parser.required_projection(structure, 275810, 10395, 3)
    structure_keys = projected['keys']
    need(len(set(structure_keys)) == len(structure_keys), 'STRUCTURE_KEY_JOIN_NOT_UNIQUE')
    optimizer_keys = {key for index, key in enumerate(structure_keys) if roles[index] == 0}
    selected = next((index for index, key in enumerate(keys) if key in optimizer_keys), None)
    need(selected is not None, 'OPTIMIZER_FULL_BANK_CANARY_MISSING')
    expected = packed[selected].tobytes()
    actual = full_bits(smiles[selected], mask, generators, np, Chem, MACCSkeys)
    need(np.packbits(actual, bitorder='big').tobytes() == expected,
         'INDEPENDENT_FULL10395_CANDIDATE_FINGERPRINT_PARITY')
    return True


def usable_spectrum(row, np):
    # Reject malformed raw rows before calling the pinned transform. Unexpected
    # transform exceptions remain job failures, not an unreviewed silent fallback.
    try:
        precursor = float(row['precursor_mz'])
        mz = np.asarray(row['ms2_mzs'], np.float64)
        intensity = np.asarray(row['ms2_normalized_intensities'], np.float64)
        energy = row['collision_energy_ev']
        return (np.isfinite(precursor) and precursor > 0 and mz.ndim == intensity.ndim == 1
                and mz.shape == intensity.shape and len(mz) > 0
                and np.isfinite(mz).all() and np.isfinite(intensity).all()
                and np.all(mz > 0) and np.all(intensity >= 0)
                and (energy is None or (np.asarray(energy).ndim == 1
                     and np.isfinite(np.asarray(energy, np.float64)).all()))
                and isinstance(row['adduct'], str)
                and row['ionization_mode'] in ('positive', 'negative'))
    except (TypeError, ValueError):
        return False


def alarm(signum, frame):
    raise TimeoutError('NATIVE_ONE_JOB_DEADLINE')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-sha256', required=True)
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--config-sha256', required=True)
    args = ap.parse_args()
    need(sys.flags.isolated == 1 and sys.dont_write_bytecode and sys.platform == 'linux'
         and Path(__file__).absolute() == WORK/'native_canary_and_infer.source.py'
         and args.config == WORK/'NATIVE_CONFIG.json', 'EXACT_NATIVE_ROUTE')
    need(sha(__file__) == args.source_sha256 and sha(args.config) == args.config_sha256, 'ENTRY_OR_CONFIG_DRIFT')
    need(args.config.stat().st_size <= 65536, 'CONFIG_CAP')
    config = bounded_json(args.config)
    need(config['schema'] == 'casmi-v6-native-one-job/2' and config['root_authorized_one_job'] is True
         and config['conditional_full_inference_after_canary'] is True
         and config['public_source_safe'] is True and config['explicit_canary_identifiers_embedded'] is False
         and config['private_input_public_notebook_compatibility_qualified'] is True
         and config['competition_use_and_mount_rights_qualified'] is True
         and config['mode'] == 'PURE_FULL10395_SINGLE_VIEW'
         and config['spectrum_policy'] == 'first_usable_in_original_test_row_order'
         and config['candidate_policy'] == 'observed_neutral_mass_median_10ppm_then_empty_30ppm'
         and config['fallback_policy'] == 'valid_window_candidates_by_mass_distance_or_hold_if_none'
         and config['candidate_canary_policy'] == 'first_optimizer_structure_in_full_bank_order'
         and config['canary_spectrum_policy'] == 'minimum_original_source_row_nonempty_optimizer_cache'
         and config['tie_policy'] == 'stable_original_full_bank_order'
         and config['candidate_bank_policy'] == 'exact_existing_full711705_bank_no_rebuild'
         and config['dependency_image_or_offline_bootstrap_qualified'] is True
         and config['external_linux_rss_supervisor_qualified'] is True
         and config['ranker_blend_training_or_official_submission_authorized'] is False
         and config['retry_authorized'] is False and config['device'] == 'cuda:0'
         and type(config['wall_seconds']) is int and 60 <= config['wall_seconds'] <= 30600
         and type(config['canary_wall_seconds']) is int
         and 60 <= config['canary_wall_seconds'] <= min(600, config['wall_seconds'])
         and type(config['peak_rss_limit_bytes']) is int
         and 1*(1<<30) <= config['peak_rss_limit_bytes'] <= 24*(1<<30), 'ROOT_NATIVE_SCOPE')
    need(not MARKER.exists() and not (WORK/'RESULT.json').exists()
         and not Path('/kaggle/working/submission.csv').exists(), 'ONE_JOB_ALREADY_CONSUMED_OR_OUTPUT_EXISTS')
    write_new(MARKER, dict(consumed_before_input_or_model_load=True, source_sha256=args.source_sha256,
        config_sha256=args.config_sha256, canary_dispatches=1, conditional_inference=True,
        retry_authorized=False, official_submission=False))
    started = time.monotonic()
    signal.signal(signal.SIGALRM, alarm); signal.setitimer(signal.ITIMER_REAL, config['canary_wall_seconds'])
    try:
        phase = 'input_byte_binding'
        paths = pinned_files(config)
        phase = 'offline_dependency_bootstrap'
        dependency_site = bootstrap_rdkit(paths['rdkit_wheel'], config)
        phase = 'scientific_imports_and_runtime'
        import numpy as np
        import pandas as pd
        import pyarrow
        import pyarrow.parquet as pq
        import torch
        import rdkit
        import PIL
        from rdkit import Chem, RDLogger
        from rdkit.Chem import MACCSkeys, rdFingerprintGenerator
        RDLogger.DisableLog('rdApp.*')  # Molecular values must never enter public logs.
        need(rdkit.__version__ == '2026.03.3'
             and Path(rdkit.__file__).is_relative_to(dependency_site)
             and np.__version__ == config['runtime']['numpy']
             and str(torch.__version__) == config['runtime']['torch']
             and sys.version.split()[0] == config['runtime']['python']
             and pd.__version__ == config['runtime']['pandas']
             and pyarrow.__version__ == config['runtime']['pyarrow']
             and PIL.__version__ == config['runtime']['pillow']
             and torch.cuda.is_available() and 'T4' in torch.cuda.get_device_name(0), 'ACTUAL_NATIVE_RUNTIME_DRIFT')
        check_budget(config)
        phase = 'scientific_source_binding'
        source = config['source_files']
        need(set(source) == {'native_canary_and_infer.source.py', 'fpmodel.py',
             'project_required_metadata_recovery_once.source.py', 'v6_single_view_scoring.source.py'}
             and source['native_canary_and_infer.source.py'] == args.source_sha256
             and source['fpmodel.py'] == MODEL_SOURCE_SHA
             and source['project_required_metadata_recovery_once.source.py'] == PARSER_SHA,
             'EXACT_EMBEDDED_SOURCE_SET')
        fpmodel = imported(WORK/'fpmodel.py', MODEL_SOURCE_SHA, 'owned_v6_fpmodel')
        parser = imported(WORK/'project_required_metadata_recovery_once.source.py', PARSER_SHA, 'inert_metadata_parser')
        scoring = imported(WORK/'v6_single_view_scoring.source.py', source['v6_single_view_scoring.source.py'], 'owned_v6_scoring')
        phase = 'full_mask'
        mask = np.load(paths['full_mask'], allow_pickle=False)
        need(mask.dtype == np.int64 and mask.shape == (10395,)
             and np.all((mask >= 0) & (mask < 10407)) and np.all(mask[1:] > mask[:-1]), 'FULL_MASK_SCHEMA')
        phase = 'candidate_bank'
        mass, keys, smiles, packed = candidate_pool(paths, parser, np, config)
        generators = [rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=4096),
            rdFingerprintGenerator.GetMorganGenerator(radius=3, fpSize=4096),
            rdFingerprintGenerator.GetRDKitFPGenerator(fpSize=2048, maxPath=6)]
        phase = 'raw_preprocessing_canary'
        prepared, roles, private_canary_binding = canary_reference(paths, np, pq, fpmodel, scoring)
        phase = 'candidate_fingerprint_canary'
        candidate_parity = candidate_canary(paths, parser, mask, generators, np, Chem, MACCSkeys,
            keys, smiles, packed, roles)
        check_budget(config)
        common = dict(checkpoint_sha256=WEIGHT_SHA, owned_fpmodel_sha256=MODEL_SOURCE_SHA,
            raw_test_preprocessing_matches_training=True,
            candidate_raw_10407_recipe_and_full_mask_qualified=candidate_parity,
            competition_use_and_private_artifact_mount_rights_qualified=True,
            merged_view_or_autocast_or_new_blend_authorized=False, actual_device='cuda:0')
        phase = 'model_canary_construction'
        native = scoring.V6SingleView(fpmodel, paths['checkpoint'], 'cuda:0', dict(common,
            status='ADMITTED_ONE_NATIVE_V6_SINGLE_SPECTRUM_CANARY_ONLY', maximum_spectrum_forward_calls=1,
            competition_submission_authorized=False), canary_only=True)
        phase = 'model_canary_forward'
        logits = native.prepared_spectrum_logits(**prepared)
        need(logits.shape == (10395,) and logits.dtype == np.float32 and np.isfinite(logits).all(),
             'FINITE_NATIVE_FULL_HEAD_REQUIRED')
        write_new(WORK/'CANARY.json', dict(status='PASS_NATIVE_MECHANICS_ONLY', raw_preprocessing_bytes_exact=True,
            source_row_join_qualified=True, checkpoint_sha256=WEIGHT_SHA, full_logits=10395,
            finite=True, clean_coordinate_projection_performed=False,
            candidate_fingerprint_sample_parity=True, whole_bank_fingerprint_parity_established=False,
            exact_existing_full_bank_used=True, full_bank_preparation_manifest_sha256=POOL_MANIFEST_SHA,
            one_forward_only=True, model_quality_established=False, historical_mps_numeric_equality_established=False,
            identifiers_or_logits_published=False, official_score=None))
        del native, logits, prepared, roles, private_canary_binding
        torch.cuda.empty_cache()
        remaining_seconds = config['wall_seconds'] - (time.monotonic() - started)
        need(remaining_seconds > 0, 'FULL_JOB_DEADLINE_EXPIRED_AT_CANARY')
        signal.setitimer(signal.ITIMER_REAL, remaining_seconds)
        # Same admitted job, only after actual canary PASS. No additional Save.
        phase = 'conditional_full_model'
        native = scoring.V6SingleView(fpmodel, paths['checkpoint'], 'cuda:0', dict(common,
            status='ADMITTED_EXACT_V6_SINGLE_VIEW_SERVING_PRIMITIVES', actual_native_fp32_canary_qualified=True))
        phase = 'full_input_loading'
        competition = Path(config['competition_root'])
        need(str(competition) in ('/kaggle/input/enveda-CASMI26-molecule-id-mass-spectra',
             '/kaggle/input/competitions/enveda-CASMI26-molecule-id-mass-spectra'), 'COMPETITION_MOUNT_IDENTITY')
        test = pq.read_table(competition/'test.parquet').to_pandas()
        sample = pd.read_csv(competition/'sample_submission.csv', dtype={'molecule_id': str})
        need(len(test) > 0 and list(sample.columns) == ['molecule_id', 'smiles']
             and sample.molecule_id.notna().all() and sample.molecule_id.is_unique,
             'ACTUAL_TEST_OR_SAMPLE_SCHEMA')
        check_budget(config)
        test['molecule_id'] = test.molecule_id.astype(str)
        need(set(test.molecule_id) == set(sample.molecule_id), 'EXACT_MOLECULE_SET')
        competition_input_sha256 = {name: sha(competition/name) for name in ('test.parquet', 'sample_submission.csv')}
        output, diagnostics = {}, dict(molecules=0, empty_10ppm=0, spectrum_fallbacks=0, candidate_rows_scored=0)
        phase = 'full_molecule_scoring'
        for molecule_id, group in test.groupby('molecule_id', sort=False):
            rows = group.to_dict('records')
            observed = np.asarray([neutral_mass(row) for row in rows], np.float64)
            observed = observed[np.isfinite(observed) & (observed > 0)]
            need(len(observed) > 0, 'MOLECULE_OBSERVED_NEUTRAL_MASS_MISSING')
            target = float(np.median(observed))
            lo = int(np.searchsorted(mass, target-target*10e-6, side='left'))
            hi = int(np.searchsorted(mass, target+target*10e-6, side='right'))
            if lo == hi:
                diagnostics['empty_10ppm'] += 1
                lo = int(np.searchsorted(mass, target-target*30e-6, side='left'))
                hi = int(np.searchsorted(mass, target+target*30e-6, side='right'))
            need(0 < hi-lo <= 4096, 'CANDIDATE_WINDOW_MISSING_OR_PREALLOCATION_CAP')
            ids = np.arange(lo, hi)
            candidate_fp = np.unpackbits(packed[lo:hi], axis=1, bitorder='big')[:, :10395]
            check_budget(config)
            chosen = None
            for row in rows:
                if not usable_spectrum(row, np):
                    continue
                candidate = scoring.prepare_raw_spectrum(row, fpmodel)
                if (len(candidate['mz']) > 0 and np.isfinite(candidate['mz']).all()
                        and np.isfinite(candidate['intensity']).all()
                        and np.isfinite(candidate['collision_energy'])):
                    chosen = candidate; break
            if chosen is None:
                diagnostics['spectrum_fallbacks'] += 1
                order = np.argsort(np.abs(mass[np.asarray(ids)]-target), kind='stable')
            else:
                z = native.prepared_spectrum_logits(**chosen)
                scores = scoring.exact_full_candidate_scores(candidate_fp, z)
                order = np.argsort(-scores, kind='stable')
                diagnostics['candidate_rows_scored'] += len(ids)
            # Exact candidate key identity dedup, no tautomer/metric relabeling.
            ranked, seen = [], set()
            for position in order:
                index = ids[int(position)]
                if keys[index] not in seen:
                    seen.add(keys[index]); ranked.append(smiles[index])
                if len(ranked) == 25:
                    break
            need(len(ranked) > 0 and all(type(x) is str and x for x in ranked), 'VALID_TOP25_REQUIRED')
            output[molecule_id] = ';'.join(ranked)
            diagnostics['molecules'] += 1
            check_budget(config)
        result = sample[['molecule_id']].copy()
        result['smiles'] = result.molecule_id.map(output)
        need(len(result) == len(sample) and result.smiles.notna().all()
             and result.smiles.str.split(';').map(len).between(1,25).all(), 'EXACT_SUBMISSION_SCHEMA')
        phase = 'final_input_recheck'
        for label, path in paths.items():
            need(sha(path) == config['files'][label]['sha256'], 'INPUT_CHANGED_DURING_NATIVE_JOB')
        need(all(sha(competition/name) == digest for name, digest in competition_input_sha256.items()),
             'COMPETITION_INPUT_CHANGED_DURING_NATIVE_JOB')
        phase = 'root_output_validation'
        destination = Path('/kaggle/working/submission.csv')
        with destination.open('x', encoding='utf-8', newline='') as stream:
            result.to_csv(stream, index=False)
            stream.flush(); os.fsync(stream.fileno())
        written = pd.read_csv(destination, dtype=str, keep_default_na=False)
        need(list(written.columns) == ['molecule_id', 'smiles'] and len(written) == len(sample)
             and written.molecule_id.tolist() == sample.molecule_id.tolist()
             and written.smiles.tolist() == result.smiles.tolist()
             and written.molecule_id.is_unique and written.smiles.str.len().gt(0).all(),
             'EXACT_COMPLETED_ROOT_CSV_READBACK')
        check_budget(config)
        write_new(WORK/'RESULT.json', dict(status='COMPLETE_PURE_V6_NATIVE_INFERENCE_NO_SCORE',
            source_sha256=args.source_sha256, config_sha256=args.config_sha256,
            checkpoint_sha256=WEIGHT_SHA, clean_coordinate_projection_performed=False,
            input_sha256={label: value['sha256'] for label, value in config['files'].items()},
            competition_input_sha256=competition_input_sha256, candidate_bank_policy=config['candidate_bank_policy'],
            candidate_policy=config['candidate_policy'], spectrum_policy=config['spectrum_policy'],
            fallback_policy=config['fallback_policy'], diagnostics=diagnostics,
            submission_bytes=destination.stat().st_size, submission_sha256=sha(destination),
            runtime=dict(torch=str(torch.__version__), numpy=np.__version__, rdkit=rdkit.__version__,
                         python=sys.version.split()[0], device=torch.cuda.get_device_name(0)),
            seconds=time.monotonic()-started, peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            local_assay_gain_transferred=False, official_submission=False, official_score=None, retry_authorized=False))
        print('COMPLETE_PURE_V6_NATIVE_INFERENCE_NO_SCORE', flush=True)
        return 0
    except BaseException as error:
        diagnostic = public_failure_diagnostic(error, phase)
        write_new(WORK/'FAILURE.json', dict(status='HOLD_CONSUMED_NATIVE_ONE_JOB', error_type=type(error).__name__,
            retry_authorized=False, official_submission=False, official_score=None, seconds=time.monotonic()-started,
            **diagnostic))
        print(json.dumps(dict(status='HOLD_CONSUMED_NATIVE_ONE_JOB', **diagnostic),
                         sort_keys=True, allow_nan=False), flush=True)
        print('HOLD_CONSUMED_NATIVE_ONE_JOB', flush=True)
        return 2
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    raise SystemExit(main())
