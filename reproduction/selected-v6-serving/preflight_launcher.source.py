# One root-admitted child; the absolute clocks include staging and preflight.
# Parent file I/O is counted and checked, not independently interrupted. Once
# started, the child remains under continuous deadline/RSS polling through exec.
if V6_ROOT_NATIVE_JOB_AUTHORIZED:
    import time as _v6_time
    _v6_started = _v6_time.monotonic()
    import hashlib as _v6_hashlib
    import json as _v6_json
    import os as _v6_os
    from pathlib import Path as _V6_Path
    import signal as _v6_signal
    import stat as _v6_stat
    import subprocess as _v6_subprocess
    import sys as _v6_sys

    def _v6_need(ok, code):
        if not ok:
            raise ValueError(code)

    def _v6_sha(raw):
        return _v6_hashlib.sha256(raw).hexdigest()

    def _v6_pairs(items):
        result = {}
        for key, value in items:
            _v6_need(key not in result, 'DUPLICATE_NATIVE_JSON_KEY')
            result[key] = value
        return result

    def _v6_nonfinite(value):
        raise ValueError('NONFINITE_NATIVE_JSON_CONSTANT')

    def _v6_parse(raw):
        return _v6_json.loads(raw, object_pairs_hook=_v6_pairs, parse_constant=_v6_nonfinite)

    _v6_need(V6_ROOT_NATIVE_JOB_AUTHORIZED is True and V6_NATIVE_OUTER_TIMEOUT_SECONDS == 1860,
             'EXACT_ONE_JOB_ROOT_ADMISSION_AND_OUTER_BUDGET')
    _v6_policy_raw = V6_PREFLIGHT_POLICY_JSON.encode('utf-8')
    _v6_need(len(_v6_policy_raw) <= 65536 and _v6_sha(_v6_policy_raw) == V6_PREFLIGHT_POLICY_SHA256,
             'FROZEN_PREFLIGHT_POLICY_BINDING')
    _v6_policy = _v6_parse(_v6_policy_raw)
    _v6_sources = {'v6_single_view_scoring.source.py', 'native_canary_and_infer.source.py',
                   'project_required_metadata_recovery_once.source.py', 'fpmodel.py',
                   'native_preflight.source.py', 'preflight_launcher.source.py'}
    _v6_need(set(V6_SOURCE_TEXTS) == set(V6_SOURCE_SHA256) == _v6_sources
             and _v6_policy['source_files'] == V6_SOURCE_SHA256, 'EXACT_SIX_NATIVE_SOURCE_SET')
    for _v6_name, _v6_text in V6_SOURCE_TEXTS.items():
        _v6_need(type(_v6_text) is str and len(_v6_text.encode('utf-8')) <= (2 << 20)
                 and _v6_sha(_v6_text.encode('utf-8')) == V6_SOURCE_SHA256[_v6_name], 'NATIVE_SOURCE_DRIFT')
    _v6_fixed = _v6_policy['fixed_config']
    _v6_need(type(_v6_fixed['canary_wall_seconds']) is int and _v6_fixed['canary_wall_seconds'] == 300
             and type(_v6_fixed['wall_seconds']) is int and _v6_fixed['wall_seconds'] == 1800
             and type(_v6_fixed['peak_rss_limit_bytes']) is int
             and _v6_fixed['peak_rss_limit_bytes'] == 20*(1 << 30), 'EXACT_GLOBAL_RESOURCE_CEILINGS')
    _v6_canary_deadline, _v6_total_deadline = _v6_started + 300, _v6_started + 1800
    _v6_outer_deadline = _v6_started + 1860
    _v6_work = _V6_Path('/kaggle/working/casmi_v6_native_once')
    _v6_need(not any(p.is_symlink() for p in (_v6_work, *_v6_work.parents))
             and _v6_work.parent.is_dir() and not _v6_work.exists()
             and not _V6_Path('/kaggle/working/submission.csv').exists(), 'EXCLUSIVE_NATIVE_JOB_AND_OUTPUT')
    _v6_os.mkdir(_v6_work, mode=0o700)

    def _v6_exclusive(name, raw):
        _v6_need(_V6_Path(name).name == name, 'NATIVE_OUTPUT_BASENAME')
        fd = _v6_os.open(_v6_work/name, _v6_os.O_WRONLY|_v6_os.O_CREAT|_v6_os.O_EXCL|_v6_os.O_NOFOLLOW, 0o600)
        with _v6_os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); _v6_os.fsync(stream.fileno())

    def _v6_receipt(name, value):
        _v6_exclusive(name, _v6_json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode('utf-8'))

    # The attempt is consumed before discovery, ordinary imports or input access.
    _v6_receipt('V6_NATIVE_WRAPPER_ONE_ATTEMPT.json', {
        'status':'CONSUMED_BEFORE_PREFLIGHT', 'policy_sha256':V6_PREFLIGHT_POLICY_SHA256,
        'source_sha256':V6_SOURCE_SHA256, 'global_start_monotonic':_v6_started,
        'canary_deadline_monotonic':_v6_canary_deadline, 'total_deadline_monotonic':_v6_total_deadline,
        'retry_authorized':False, 'competition_submission_authorized':False})
    _v6_child = None
    _v6_peak_rss = 0
    _v6_canary_pass = False

    def _v6_small_receipt(name):
        path = _v6_work/name
        if not path.exists():
            return None
        _v6_need(not path.is_symlink() and _v6_stat.S_ISREG(path.stat().st_mode)
                 and path.stat().st_size <= 65536, 'BOUNDED_NATIVE_PHASE_RECEIPT')
        raw = path.read_bytes()
        _v6_need(len(raw) <= 65536, 'NATIVE_PHASE_RECEIPT_BYTE_CAP')
        try:
            return _v6_parse(raw)
        except _v6_json.JSONDecodeError:
            return None  # writer may still be fsyncing; never promotes a partial receipt

    def _v6_observe_canary():
        result = _v6_small_receipt('CANARY.json')
        if result is None:
            return False
        expected = {
            'status':'PASS_NATIVE_MECHANICS_ONLY', 'raw_preprocessing_bytes_exact':True,
            'source_row_join_qualified':True,
            'checkpoint_sha256':'9c46ca4fcf19002fecbcded0d0808e8a81e3a25a143e684e259f265c44a5be31',
            'full_logits':10395, 'finite':True, 'clean_coordinate_projection_performed':False,
            'candidate_fingerprint_sample_parity':True, 'whole_bank_fingerprint_parity_established':False,
            'exact_existing_full_bank_used':True,
            'full_bank_preparation_manifest_sha256':'5b08ca4b830de1558be4ce568a10f0997b5fa2fe875a872dcd6a216f901fd9ef',
            'one_forward_only':True, 'model_quality_established':False,
            'historical_mps_numeric_equality_established':False,
            'identifiers_or_logits_published':False, 'official_score':None}
        _v6_need(type(result) is dict and set(result) == set(expected)
                 and all(type(result[k]) is type(v) and result[k] == v for k, v in expected.items()),
                 'EXACT_FROZEN_DRIVER_CANARY_RECEIPT')
        preflight = _v6_small_receipt('PREFLIGHT_RESULT.json')
        _v6_need(type(preflight) is dict and preflight.get('status') == 'PASS_PREFLIGHT_OBSERVATIONS_ONLY'
                 and preflight.get('policy_sha256') == V6_PREFLIGHT_POLICY_SHA256
                 and preflight.get('source_sha256') == V6_SOURCE_SHA256
                 and preflight.get('same_pid_exec') is True
                 and preflight.get('native_compatibility_before_driver_canary') == 'UNKNOWN',
                 'EXACT_PREFLIGHT_SOURCE_AND_POLICY_HANDOFF')
        cfg_path = _v6_work/'NATIVE_CONFIG.json'
        _v6_need(not cfg_path.is_symlink() and cfg_path.stat().st_size <= 65536
                 and _v6_sha(cfg_path.read_bytes()) == preflight['resolved_config_sha256'], 'FROZEN_RESOLVED_CONFIG_RECEIPT')
        return True

    def _v6_missing_rss_reobserve(member, pgid, callback_deadline):
        """Resolve missing RSS only to a real reading or corroborated process exit."""
        _v6_need(type(member) is int and member > 0 and type(pgid) is int and pgid > 0,
             'NATIVE_RSS_EVIDENCE_REQUIRED')
        directory = _V6_Path('/proc')/str(member)
        stop = min(callback_deadline, _v6_time.monotonic() + .1)
        identity = None
        def check():
            now = _v6_time.monotonic()
            _v6_need(now < callback_deadline, 'RESOURCE_OBSERVATION_DEADLINE')
            _v6_need(now < stop, 'NATIVE_RSS_EVIDENCE_REQUIRED')
        def stat():
            check()
            text = (directory/'stat').read_text()
            check()
            split = text.rfind(')')
            fields = text[split+2:].split()
            _v6_need(text.startswith(str(member)+' (') and split > 0 and text[split:split+2] == ') ' and len(fields) >= 22,
                 'NATIVE_RSS_EVIDENCE_REQUIRED')
            _v6_need(fields[0] in ('R','S','D','T','t','Z','X','P','I') and
                 all(fields[i].isascii() and fields[i].isdecimal() for i in (2,17,19,20,21)),
                 'NATIVE_RSS_EVIDENCE_REQUIRED')
            group, threads, start, virtual, resident = (int(fields[i]) for i in (2,17,19,20,21))
            _v6_need(group == pgid and start > 0, 'NATIVE_RSS_EVIDENCE_REQUIRED')
            return (member, group, start), (fields[0], threads, virtual, resident)
        for attempt in range(11):
            try:
                before, a = stat()
                _v6_need(identity is None or identity == before, 'NATIVE_RSS_EVIDENCE_REQUIRED')
                identity = before
                check()
                lines = (directory/'status').read_text().splitlines()
                after, b = stat()
            except FileNotFoundError:
                check()
                return 0  # The previously owned member disappeared, as in the original observer.
            _v6_need(before == after, 'NATIVE_RSS_EVIDENCE_REQUIRED')
            def values(key):
                return [line.split()[1:] for line in lines if line.startswith(key+':')]
            pid, tgid, state = values('Pid'), values('Tgid'), values('State')
            _v6_need(pid == [[str(member)]] and tgid == [[str(member)]] and len(state) == 1 and
                 state[0] and state[0][0] in ('R','S','D','T','t','Z','X','P','I'),
                 'NATIVE_RSS_EVIDENCE_REQUIRED')
            rss = values('VmRSS')
            if rss:
                _v6_need(len(rss) == 1 and len(rss[0]) == 2 and rss[0][1] == 'kB' and
                     rss[0][0].isascii() and rss[0][0].isdecimal(), 'NATIVE_RSS_EVIDENCE_REQUIRED')
                check()
                return int(rss[0][0])*1024
            if all(s in ('Z','X') and threads <= 1 and virtual == resident == 0
                   for s, threads, virtual, resident in (a,b)):
                check()
                return 0
            now = _v6_time.monotonic()
            if attempt == 10 or now >= stop:
                break
            _v6_time.sleep(min(.01, stop-now))
        _v6_need(False, 'NATIVE_RSS_EVIDENCE_REQUIRED')


    try:
        for _v6_name, _v6_text in V6_SOURCE_TEXTS.items():
            _v6_exclusive(_v6_name, _v6_text.encode('utf-8'))
        _v6_exclusive('PREFLIGHT_POLICY.json', _v6_policy_raw)
        _v6_need(_v6_time.monotonic() < _v6_canary_deadline, 'STAGING_WITHIN_GLOBAL_CANARY_DEADLINE')
        _v6_child = _v6_subprocess.Popen([
            _v6_sys.executable, '-I', '-B', str(_v6_work/'native_preflight.source.py'),
            '--source-sha256', V6_SOURCE_SHA256['native_preflight.source.py'],
            '--policy-sha256', V6_PREFLIGHT_POLICY_SHA256,
            '--started-monotonic', repr(_v6_started),
        ], cwd=str(_v6_work), stdin=_v6_subprocess.DEVNULL, start_new_session=True)
        while _v6_child.poll() is None:
            _v6_now = _v6_time.monotonic()
            _v6_need(_v6_now <= _v6_total_deadline and _v6_now <= _v6_outer_deadline, 'GLOBAL_NATIVE_TOTAL_DEADLINE')
            if not _v6_canary_pass:
                _v6_need(_v6_now <= _v6_canary_deadline, 'GLOBAL_PREFLIGHT_AND_CANARY_DEADLINE')
                _v6_observed = _v6_observe_canary()
                _v6_need(_v6_time.monotonic() <= _v6_canary_deadline, 'CANARY_RECEIPT_IO_WITHIN_GLOBAL_DEADLINE')
                _v6_canary_pass = _v6_observed
            try:
                _v6_status = (_V6_Path('/proc')/str(_v6_child.pid)/'status').read_text()
            except FileNotFoundError:
                _v6_need(_v6_child.poll() is not None, 'NATIVE_CHILD_STATUS_AMBIGUOUS')
                break
            _v6_rss = [line.split() for line in _v6_status.splitlines() if line.startswith('VmRSS:')]
            if _v6_rss:
                _v6_need(len(_v6_rss) == 1 and len(_v6_rss[0]) == 3 and _v6_rss[0][2] == 'kB', 'LINUX_RSS_UNITS')
                _v6_peak_rss = max(_v6_peak_rss, int(_v6_rss[0][1])*1024)
                _v6_need(_v6_peak_rss <= _v6_fixed['peak_rss_limit_bytes'], 'GLOBAL_NATIVE_RSS_LIMIT')
            else:
                _v6_rss_deadline = min(_v6_total_deadline, _v6_outer_deadline,
                    _v6_canary_deadline if not _v6_canary_pass else _v6_total_deadline)
                _v6_reobserved_rss = _v6_missing_rss_reobserve(
                    _v6_child.pid, _v6_child.pid, _v6_rss_deadline)
                _v6_peak_rss = max(_v6_peak_rss, _v6_reobserved_rss)
                _v6_need(_v6_peak_rss <= _v6_fixed['peak_rss_limit_bytes'], 'GLOBAL_NATIVE_RSS_LIMIT')
                continue
            try:
                _v6_child.wait(timeout=0.1)
            except _v6_subprocess.TimeoutExpired:
                pass
        _v6_need(_v6_child.wait(timeout=5) == 0, 'NATIVE_CHILD_FAILED_CONSUMED')
        _v6_need(_v6_time.monotonic() <= _v6_total_deadline, 'CHILD_COMPLETION_WITHIN_GLOBAL_TOTAL')
        if not _v6_canary_pass:
            _v6_need(_v6_time.monotonic() <= _v6_canary_deadline, 'CANARY_DEADLINE_BEFORE_FINAL_READ')
            _v6_observed = _v6_observe_canary()
            _v6_need(_v6_time.monotonic() <= _v6_canary_deadline and _v6_observed, 'QUALIFIED_CANARY_BEFORE_COMPLETION')
            _v6_canary_pass = True
        _v6_receipt('WRAPPER_RESULT.json', {
            'status':'COMPLETE_ONE_CHILD_WITH_CONTINUOUS_PREFLIGHT_BUDGET',
            'source_sha256':V6_SOURCE_SHA256, 'policy_sha256':V6_PREFLIGHT_POLICY_SHA256,
            'peak_sampled_child_rss_bytes':_v6_peak_rss, 'rss_poll_seconds':0.1,
            'global_start_monotonic':_v6_started, 'prepublication_elapsed_seconds':_v6_time.monotonic()-_v6_started,
            'canary_pass_observed_within_global_deadline':_v6_canary_pass,
            'same_pid_preflight_exec':True, 'hard_memory_isolation_claimed':False,
            'retry_authorized':False, 'competition_submission_authorized':False})
        _v6_need(_v6_time.monotonic() <= _v6_outer_deadline, 'FINAL_WRAPPER_DEADLINE')
        print('CASMI_V6_COMPLETED_OUTPUT_REQUIRES_ROOT_VALIDATION', flush=True)
        _v6_need(_v6_time.monotonic() <= _v6_outer_deadline, 'FINAL_FLUSH_WITHIN_OUTER_DEADLINE')
    except BaseException:
        if _v6_child is not None:
            if _v6_child.poll() is None:
                try:
                    _v6_os.killpg(_v6_child.pid, _v6_signal.SIGKILL)
                except ProcessLookupError:
                    pass
            _v6_child.wait(timeout=10)
        _v6_receipt('WRAPPER_FAILURE.json', {
            'status':'HOLD_CONSUMED_PREFLIGHT_OR_DRIVER', 'child_exit_observed':_v6_child is None or _v6_child.poll() is not None,
            'peak_sampled_child_rss_bytes':_v6_peak_rss, 'retry_authorized':False,
            'competition_submission_authorized':False})
        raise
else:
    print('V6_PREFLIGHT_HOLD: source packaged; no native job or submission dispatched.')
