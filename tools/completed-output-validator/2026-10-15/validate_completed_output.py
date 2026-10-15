#!/usr/bin/env python3
"""Read-only V35 output artifact checks; stdlib only, no API or model imports.

Usage: python3 -B validate_completed_output.py --output-dir EXACT_OUTPUT_ROOT \
    --sample EXACT_CURRENT_SAMPLE_CSV
Root must separately verify public V35 COMPLETE and its native linkage. This
program does not submit or establish an official score. It prints no CSV rows.
Budget is checked around bounded local I/O; I/O is not independently preempted.
"""
import argparse
import copy
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import stat
import sys
import time

BINDINGS_SHA = '4175116ccd23f865f1a4abfc797ed6a39a7fba5b62ad8a784adce9ae42d0af02'
JSON_CAP = 65536
CSV_CAP = 64 << 20
SAMPLE_CAP = 2 << 20
RSS_CAP = 20 << 30
BUDGET_SECONDS = 120
RUNTIME_KEYS = {'python', 'numpy', 'torch', 'pandas', 'pyarrow', 'pillow'}
FAILURES = ('PREFLIGHT_FAILURE.json', 'FAILURE.json', 'WRAPPER_FAILURE.json')
START = time.monotonic()


def need(ok, code):
    if not ok:
        raise ValueError(code)


def clock():
    need(time.monotonic() - START <= BUDGET_SECONDS, 'LOCAL_REVIEW_BUDGET_EXCEEDED')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def equal(actual, expected, code):
    need(canonical(actual) == canonical(expected), code)


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def nonfinite(value):
    raise ValueError('NONFINITE_JSON_CONSTANT')


def parse(raw):
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def checked_file(path, cap):
    clock()
    path = Path(path).absolute()
    need('..' not in path.parts, 'PATH_ESCAPE')
    for part in (path, *path.parents):
        mode = part.lstat().st_mode
        need(not stat.S_ISLNK(mode), 'SYMLINK_ARTIFACT')
    meta = path.stat()
    need(stat.S_ISREG(meta.st_mode) and 0 < meta.st_size <= cap, 'FILE_TYPE_OR_SIZE_CAP')
    return path, meta.st_size


def read_bytes(path, cap=JSON_CAP):
    path, size = checked_file(path, cap)
    with path.open('rb') as stream:
        raw = stream.read(cap + 1)
    need(len(raw) == size and len(raw) <= cap, 'READ_SIZE_DRIFT')
    clock()
    return raw


def read_json(path):
    raw = read_bytes(path)
    value = parse(raw)
    need(type(value) is dict, 'JSON_OBJECT_REQUIRED')
    return value, sha(raw)


def file_digest(path, cap):
    path, size = checked_file(path, cap)
    digest = hashlib.sha256()
    consumed = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            consumed += len(block)
            need(consumed <= cap, 'STREAM_SIZE_CAP')
            digest.update(block)
            clock()
    need(consumed == size, 'STREAM_SIZE_DRIFT')
    return digest.hexdigest(), size


def number(value, code, low=0, high=None):
    need(type(value) in (int, float) and math.isfinite(value) and value >= low
         and (high is None or value <= high), code)


def integer(value, code, low=0, high=None):
    need(type(value) is int and value >= low and (high is None or value <= high), code)


def expected_fields(value, expected, code):
    need(type(value) is dict, code)
    for key, wanted in expected.items():
        need(key in value, code)
        equal(value[key], wanted, code)


def validate(output_dir, sample_path, bindings_path=None):
    binding_path = bindings_path or Path(__file__).with_name('validation_bindings.json')
    binding_raw = read_bytes(binding_path)
    need(sha(binding_raw) == BINDINGS_SHA, 'VALIDATOR_BINDINGS_DRIFT')
    binding = parse(binding_raw)
    sources = binding['source_sha256']
    policy_text = binding['native_policy_text'].encode('utf-8')
    policy_sha = binding['native_policy_sha256']
    need(sha(policy_text) == policy_sha, 'BINDING_POLICY_HASH')
    policy = parse(policy_text)
    fixed = policy['fixed_config']
    root = Path(output_dir).absolute()
    work = root / 'casmi_v6_native_once'
    for name in FAILURES:
        try:
            (work / name).lstat()
        except FileNotFoundError:
            pass
        else:
            raise ValueError('NATIVE_FAILURE_RECEIPT_PRESENT')
    native_policy = read_bytes(work / 'PREFLIGHT_POLICY.json')
    need(native_policy == policy_text and sha(native_policy) == policy_sha, 'NATIVE_POLICY_BYTE_DRIFT')
    config, config_sha = read_json(work / 'NATIVE_CONFIG.json')
    wrapper_marker, _ = read_json(work / 'V6_NATIVE_WRAPPER_ONE_ATTEMPT.json')
    preflight, _ = read_json(work / 'PREFLIGHT_RESULT.json')
    science_marker, _ = read_json(work / 'V6_NATIVE_SCIENCE_ONE_ATTEMPT.json')
    canary, _ = read_json(work / 'CANARY.json')
    result, _ = read_json(work / 'RESULT.json')
    wrapper, _ = read_json(work / 'WRAPPER_RESULT.json')
    equal(canary, binding['exact_canary_receipt'], 'EXACT_CANARY_RECEIPT')
    for obj, status in ((wrapper_marker, 'CONSUMED_BEFORE_PREFLIGHT'),
                        (preflight, 'PASS_PREFLIGHT_OBSERVATIONS_ONLY'),
                        (wrapper, 'COMPLETE_ONE_CHILD_WITH_CONTINUOUS_PREFLIGHT_BUDGET')):
        expected_fields(obj, {'status': status, 'source_sha256': sources,
                             'policy_sha256': policy_sha, 'retry_authorized': False},
                        'WRAPPER_PREFLIGHT_SOURCE_BINDING')
    expected_fields(science_marker, {'consumed_before_input_or_model_load': True,
        'source_sha256': sources['native_canary_and_infer.source.py'], 'config_sha256': config_sha,
        'canary_dispatches': 1, 'conditional_inference': True, 'retry_authorized': False,
        'official_submission': False}, 'SCIENCE_MARKER_BINDING')
    expected_fields(preflight, {'resolved_config_sha256': config_sha, 'same_pid_exec': True,
        'native_compatibility_before_driver_canary': 'UNKNOWN', 'private_rows_or_arrays_published': False,
        'declared_platform_image': policy['immutable_platform_image'], 'image_attested_by_preflight': False},
        'PREFLIGHT_HANDOFF_BINDING')
    need(set(config) == set(fixed) | {'runtime', 'competition_root'}, 'RESOLVED_CONFIG_SCHEMA')
    runtime = config['runtime']
    need(type(runtime) is dict and set(runtime) == RUNTIME_KEYS and all(
        type(value) is str and 0 < len(value) <= 512 and '\n' not in value for value in runtime.values()),
        'RUNTIME_STRING_SCHEMA')
    equal(preflight['runtime'], runtime, 'RUNTIME_OBSERVATION_DRIFT')
    need(type(config['files']) is dict and set(config['files']) == set(fixed['files']), 'TEN_FILES_REQUIRED')
    restored = copy.deepcopy(config)
    restored.pop('runtime'); restored.pop('competition_root')
    resolved_paths = []
    for label, original in fixed['files'].items():
        record = config['files'][label]
        need(type(record) is dict and set(record) == {'path', 'bytes', 'sha256'}, 'RESOLVED_FILE_SCHEMA')
        equal({k: record[k] for k in ('bytes', 'sha256')}, original, 'INPUT_PIN_DRIFT')
        route = policy['file_routes'][label]
        allowed = [str(PurePosixPath(x) / route['relative_path'])
                   for x in policy['mounts'][route['mount']]['allowed_roots']]
        need(record['path'] in allowed, 'UNAPPROVED_RESOLVED_MOUNT')
        resolved_paths.append(record['path']); restored['files'][label].pop('path')
    need(len(set(resolved_paths)) == len(resolved_paths), 'RESOLVED_PATHS_NOT_DISTINCT')
    competition = config['competition_root']
    need(competition in policy['mounts']['competition']['allowed_roots'] and
         config['files']['train']['path'] == str(PurePosixPath(competition) / 'train.parquet'),
         'COMPETITION_ROOT_BINDING')
    integer(config['canary_wall_seconds'], 'CANARY_BUDGET', 60, 300)
    integer(config['wall_seconds'], 'TOTAL_BUDGET', 60, 1800)
    need(config['wall_seconds'] - config['canary_wall_seconds'] == 1500, 'CONTINUOUS_BUDGET_DELTA')
    for key in ('canary_wall_seconds', 'wall_seconds'):
        restored[key] = fixed[key]
    equal(restored, fixed, 'FIXED_CONFIG_DRIFT')
    expected_fields(preflight, {'driver_remaining_canary_seconds': config['canary_wall_seconds'],
        'driver_remaining_total_seconds': config['wall_seconds']}, 'PREFLIGHT_REMAINING_BUDGETS')
    number(preflight['preflight_elapsed_seconds'], 'PREFLIGHT_TIME', high=300)
    expected_fields(wrapper, {'canary_pass_observed_within_global_deadline': True,
        'same_pid_preflight_exec': True, 'hard_memory_isolation_claimed': False,
        'competition_submission_authorized': False, 'rss_poll_seconds': .1}, 'WRAPPER_COMPLETION')
    expected_fields(wrapper_marker, {'competition_submission_authorized': False}, 'WRAPPER_MARKER_SCOPE')
    start = wrapper_marker['global_start_monotonic']
    number(start, 'GLOBAL_CLOCK')
    equal(preflight['global_start_monotonic'], start, 'PREFLIGHT_GLOBAL_CLOCK')
    equal(wrapper['global_start_monotonic'], start, 'WRAPPER_GLOBAL_CLOCK')
    equal(wrapper_marker['canary_deadline_monotonic'], start + 300, 'CANARY_ABSOLUTE_CLOCK')
    equal(wrapper_marker['total_deadline_monotonic'], start + 1800, 'TOTAL_ABSOLUTE_CLOCK')
    number(wrapper['prepublication_elapsed_seconds'], 'WRAPPER_TIME', high=1860)
    integer(wrapper['peak_sampled_child_rss_bytes'], 'WRAPPER_RSS', high=RSS_CAP)
    expected_fields(result, {'status': 'COMPLETE_PURE_V6_NATIVE_INFERENCE_NO_SCORE',
        'source_sha256': sources['native_canary_and_infer.source.py'], 'config_sha256': config_sha,
        'checkpoint_sha256': fixed['files']['checkpoint']['sha256'],
        'clean_coordinate_projection_performed': False, 'local_assay_gain_transferred': False,
        'official_submission': False, 'official_score': None, 'retry_authorized': False,
        'input_sha256': {k: v['sha256'] for k, v in fixed['files'].items()}}, 'FINAL_RESULT_BINDING')
    for key in ('candidate_bank_policy', 'candidate_policy', 'spectrum_policy', 'fallback_policy'):
        equal(result[key], config[key], 'FINAL_SCIENTIFIC_POLICY_DRIFT')
    rruntime = result['runtime']
    need(type(rruntime) is dict and set(rruntime) == {'torch','numpy','rdkit','python','device'}, 'RESULT_RUNTIME_SCHEMA')
    expected_fields(rruntime, {'torch':runtime['torch'], 'numpy':runtime['numpy'],
        'python':runtime['python'], 'rdkit':'2026.03.3'}, 'RESULT_RUNTIME_BINDING')
    need(type(rruntime['device']) is str and 'T4' in rruntime['device'], 'RESULT_DEVICE')
    number(result['seconds'], 'DRIVER_TIME', high=config['wall_seconds'])
    integer(result['peak_rss_bytes'], 'DRIVER_RSS', high=RSS_CAP)
    hashes = result['competition_input_sha256']
    need(type(hashes) is dict and set(hashes) == {'test.parquet', 'sample_submission.csv'} and all(
        type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)
        for value in hashes.values()), 'COMPETITION_HASH_SCHEMA')
    source_count = 0
    for name, digest in sources.items():
        try:
            (work / name).lstat()
        except FileNotFoundError:
            continue
        need(sha(read_bytes(work / name, 2 << 20)) == digest, 'RETAINED_SOURCE_BYTE_DRIFT')
        source_count += 1
    sample_raw = read_bytes(sample_path, SAMPLE_CAP)
    need(sha(sample_raw) == hashes['sample_submission.csv'], 'SAMPLE_INPUT_HASH_DRIFT')
    csv.field_size_limit(1 << 20)
    sample_reader = csv.reader(io.StringIO(sample_raw.decode('utf-8'), newline=''))
    need(next(sample_reader, None) == ['molecule_id', 'smiles'], 'SAMPLE_HEADER')
    expected_ids = []
    for row in sample_reader:
        clock(); need(len(row) == 2 and row[0] != '', 'SAMPLE_ROW_SCHEMA')
        expected_ids.append(row[0])
    need(expected_ids and len(set(expected_ids)) == len(expected_ids), 'SAMPLE_UNIQUE_NONEMPTY_IDS')
    submission = root / 'submission.csv'
    digest, size = file_digest(submission, CSV_CAP)
    equal(size, result['submission_bytes'], 'SUBMISSION_BYTE_COUNT')
    equal(digest, result['submission_sha256'], 'SUBMISSION_BYTE_HASH')
    count = 0
    minimum, maximum = 25, 0
    with submission.open('r', encoding='utf-8', newline='') as stream:
        reader = csv.reader(stream)
        need(next(reader, None) == ['molecule_id', 'smiles'], 'SUBMISSION_HEADER')
        for row in reader:
            clock(); need(len(row) == 2 and count < len(expected_ids), 'SUBMISSION_ROW_SCHEMA')
            need(row[0] == expected_ids[count], 'SUBMISSION_ID_ORDER')
            candidates = row[1].split(';')
            need(1 <= len(candidates) <= 25 and all(x != '' for x in candidates), 'SUBMISSION_TOP25')
            minimum = min(minimum, len(candidates)); maximum = max(maximum, len(candidates)); count += 1
    need(count == len(expected_ids), 'SUBMISSION_ROW_COUNT')
    equal(file_digest(submission, CSV_CAP), (digest, size), 'SUBMISSION_CHANGED_DURING_REVIEW')
    diagnostics = result['diagnostics']
    need(type(diagnostics) is dict and set(diagnostics) == {'molecules','empty_10ppm','spectrum_fallbacks','candidate_rows_scored'}, 'DIAGNOSTICS_SCHEMA')
    integer(diagnostics['molecules'], 'DIAGNOSTIC_MOLECULES', count, count)
    for key in ('empty_10ppm', 'spectrum_fallbacks'):
        integer(diagnostics[key], 'DIAGNOSTIC_COUNTS', 0, count)
    integer(diagnostics['candidate_rows_scored'], 'DIAGNOSTIC_SCORED_ROWS')
    clock()
    return {'status':'PASS_COMPLETED_OUTPUT_ARTIFACTS_NO_OFFICIAL_SCORE',
        'candidate_sha256':binding['candidate_sha256'], 'native_policy_sha256':policy_sha,
        'resolved_config_sha256':config_sha, 'submission_sha256':digest, 'submission_bytes':size,
        'rows':count, 'minimum_candidates':minimum, 'maximum_candidates':maximum,
        'diagnostics':diagnostics, 'canary_receipt_exact':True, 'failure_receipts_absent':True,
        'retained_source_hashes_checked':source_count, 'expected_source_count':len(sources),
        'sample_hash_and_exact_id_order_verified':True, 'rows_or_candidates_printed':False,
        'native_terminal_status_and_version_linkage_verified_by_this_program':False,
        'official_submission':False, 'official_score':None, 'retry_authorized':False,
        'elapsed_seconds':time.monotonic()-START}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--sample', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.output_dir, args.sample)
    except BaseException as error:
        # ValueError messages are fixed internal codes only; never expose paths,
        # JSON decoder snippets, molecule IDs, raw values, or exception repr.
        allowed = type(error) is ValueError and str(error).isascii() and str(error).replace('_','').isalnum() and str(error).isupper()
        result = {'status':'HOLD_OUTPUT_ARTIFACT_VALIDATION','error_code':str(error) if allowed else 'LOCAL_ARTIFACT_READ_OR_SCHEMA_ERROR',
                  'official_submission':False,'retry_authorized':False,'rows_or_candidates_printed':False}
        print(json.dumps(result, sort_keys=True, allow_nan=False), flush=True)
        return 2
    print(json.dumps(result, sort_keys=True, allow_nan=False), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
