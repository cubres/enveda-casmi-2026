#!/usr/bin/env python3
"""Pure stdlib AST tests. All process, clock and /proc objects are invented.
No source module import, real child process, native call, or competition data.
"""
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import unittest
import uuid
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
BASE = HERE/'baseline_v37_launcher.source.py'
NEW = HERE/'preflight_launcher.source.py'
BASE_SHA = 'd706e954b7bd551e7662f223c90a12a4081ff686fa23b768b79cc9382c2b5cab'
NEW_SHA = 'ccd269209b64155602c333c55532f77af01befcb65e1455ffefd04079c45b126'
OLD_RAW, NEW_RAW = BASE.read_bytes(), NEW.read_bytes()
OLD_TREE, NEW_TREE = ast.parse(OLD_RAW), ast.parse(NEW_RAW)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def named(tree, name):
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(nodes) == 1
    return nodes[0]

OLD_HELPER = named(OLD_TREE, '_v6_missing_rss_reobserve')
NEW_HELPER = named(NEW_TREE, '_v6_missing_rss_reobserve')
RSS_BRANCH = next(n for n in ast.walk(NEW_TREE) if isinstance(n, ast.If)
                  and isinstance(n.test, ast.Name) and n.test.id == '_v6_rss')
FINAL_WAIT = next(n for n in ast.walk(NEW_TREE) if isinstance(n, ast.Expr)
                  and isinstance(n.value, ast.Call) and any(isinstance(a, ast.Constant)
                  and a.value == 'NATIVE_CHILD_FAILED_CONSUMED' for a in n.value.args))

def need(condition, code):
    if not condition:
        raise ValueError(code)

class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []
    def monotonic(self):
        result = self.now
        self.now += .0001
        return result
    def sleep(self, seconds):
        assert 0 <= seconds <= .01
        self.sleeps.append(seconds)
        self.now += seconds

class Child:
    def __init__(self, clock, polls=(None,), pid=123, wait_code=0):
        self.clock, self.polls, self.pid = clock, list(polls), pid
        self.calls, self.waits, self.wait_code = 0, [], wait_code
    def poll(self):
        value = self.polls[min(self.calls, len(self.polls)-1)]
        self.calls += 1
        if isinstance(value, tuple):
            value, delay = value
            self.clock.now += delay
        return value
    def wait(self, timeout):
        self.waits.append(timeout)
        return self.wait_code

def stat_text(state='S', group=123, start=987, threads=2, virtual=100000, resident=100, pid=123):
    fields = ['0']*22
    for index, value in {0:state, 2:group, 17:threads, 19:start, 20:virtual, 21:resident}.items():
        fields[index] = str(value)
    return str(pid)+' (invented process) '+' '.join(fields)

def status_text(rss=None, state='S', pid=123, tgid=123):
    text = 'Pid: '+str(pid)+'\nTgid: '+str(tgid)+'\nState: '+state+' (synthetic)\n'
    return text if rss is None else text+'VmRSS: '+rss+'\n'

class Proc:
    def __init__(self, clock, stats=None, statuses=None):
        self.clock = clock
        self.sequences = {'stat':list(stats or [stat_text()]), 'status':list(statuses or [status_text()])}
        self.counts = {'stat':0, 'status':0}
    def path(self, value):
        return FakePath(self, str(value))
    def read(self, path):
        assert path in ('/proc/123/stat', '/proc/123/status'), path
        key = path.rsplit('/', 1)[1]
        index = self.counts[key]
        self.counts[key] += 1
        values = self.sequences[key]
        value = values[min(index, len(values)-1)]
        if isinstance(value, tuple):
            value, delay = value
            self.clock.now += delay
        if isinstance(value, BaseException):
            raise value
        return value

class FakePath:
    def __init__(self, proc, value):
        self.proc, self.value = proc, value
    def __truediv__(self, part):
        return FakePath(self.proc, self.value+'/'+str(part))
    def read_text(self):
        return self.proc.read(self.value)

def fixture(polls=(None,), stats=None, statuses=None, deadline=1., pid=123, helper=NEW_HELPER, wait_code=0):
    clock = Clock()
    proc = Proc(clock, stats, statuses)
    child = Child(clock, polls, pid, wait_code)
    env = {'_v6_need':need, '_V6_Path':proc.path, '_v6_time':clock, '_v6_child':child}
    exec(compile(ast.Module(body=[copy.deepcopy(helper)], type_ignores=[]), '<invented helper>', 'exec'), env)
    def invoke():
        return env['_v6_missing_rss_reobserve'](123, 123, deadline)
    return invoke, clock, proc, child, env

def execute_nodes(nodes, env):
    exec(compile(ast.Module(body=copy.deepcopy(nodes), type_ignores=[]), '<actual extracted statements>', 'exec'), env)

class WrapperExitTests(unittest.TestCase):
    def reject(self, call, code='NATIVE_RSS_EVIDENCE_REQUIRED'):
        with self.assertRaisesRegex(ValueError, '^'+code+'$'):
            call()

    def test_exact_source_pins_and_only_narrow_delta(self):
        self.assertEqual(sha(OLD_RAW), BASE_SHA)
        self.assertEqual(sha(NEW_RAW), NEW_SHA)
        raw = NEW_RAW.decode()
        lines = raw.splitlines(True)
        owned = named(NEW_TREE, 'owned_exit_observed')
        loop = next(n for n in NEW_HELPER.body if isinstance(n, ast.For))
        call = loop.body[0]
        self.assertIsInstance(call, ast.If)
        self.assertEqual(ast.unparse(call.test), 'owned_exit_observed()')
        self.assertEqual(ast.unparse(call.body[0]), 'return 0')
        # Remove the exact two added source ranges, preserving every other byte.
        for begin, end in sorted([(owned.lineno-1, owned.end_lineno), (call.lineno-1, call.end_lineno)], reverse=True):
            del lines[begin:end]
        self.assertEqual(''.join(lines).encode(), OLD_RAW)
        self.assertIsInstance(RSS_BRANCH.orelse[-1], ast.Continue)
        self.assertEqual(ast.unparse(FINAL_WAIT), "_v6_need(_v6_child.wait(timeout=5) == 0, 'NATIVE_CHILD_FAILED_CONSUMED')")

    def test_zero_exit_before_proc_samples(self):
        invoke, clock, proc, child, env = fixture(polls=(0,))
        self.assertEqual(invoke(), 0)
        self.assertEqual(proc.counts, {'stat':0, 'status':0})
        self.assertEqual(child.calls, 1)
        execute_nodes([FINAL_WAIT], env)
        self.assertEqual(child.waits, [5])

    def test_nonzero_exit_before_proc_still_fails_final_wait(self):
        for code in (1, -9):
            with self.subTest(code=code):
                invoke, clock, proc, child, env = fixture(polls=(code,), wait_code=code)
                self.assertEqual(invoke(), 0)
                self.assertEqual(proc.counts, {'stat':0, 'status':0})
                self.reject(lambda: execute_nodes([FINAL_WAIT], env), 'NATIVE_CHILD_FAILED_CONSUMED')

    def test_exit_during_reobservation_before_next_proc_sample(self):
        for code in (0, 2):
            with self.subTest(code=code):
                invoke, clock, proc, child, env = fixture(polls=(None, code), wait_code=code)
                self.assertEqual(invoke(), 0)
                self.assertEqual(child.calls, 2)
                self.assertEqual(proc.counts, {'stat':2, 'status':1})
                self.assertEqual(len(clock.sleeps), 1)
                if code:
                    self.reject(lambda: execute_nodes([FINAL_WAIT], env), 'NATIVE_CHILD_FAILED_CONSUMED')
                else:
                    execute_nodes([FINAL_WAIT], env)

    def test_old_helper_fails_same_known_exit_fixture_new_helper_passes(self):
        old, oldclock, oldproc, oldchild, env = fixture(polls=(0,), helper=OLD_HELPER)
        self.reject(old)
        self.assertEqual(oldchild.calls, 0)
        self.assertGreater(oldproc.counts['status'], 0)
        new, clock, proc, child, env = fixture(polls=(0,))
        self.assertEqual(new(), 0)
        self.assertEqual(proc.counts['status'], 0)

    def test_none_poll_retains_valid_rss_recovery(self):
        invoke, clock, proc, child, env = fixture(statuses=[status_text(), status_text('17 kB')])
        self.assertEqual(invoke(), 17*1024)
        self.assertEqual(child.calls, 2)
        self.assertEqual(proc.counts, {'stat':4, 'status':2})

    def test_none_live_absence_still_fails_within_bound(self):
        invoke, clock, proc, child, env = fixture()
        self.reject(invoke)
        self.assertLessEqual(child.calls, 11)
        self.assertLessEqual(clock.now, .101)
        self.assertGreater(proc.counts['status'], 0)

    def test_over_cap_recovery_rejected_by_actual_unchanged_call_site(self):
        invoke, clock, proc, child, env = fixture(statuses=[status_text('3 kB')])
        env.update({'_v6_total_deadline':1., '_v6_outer_deadline':2., '_v6_canary_deadline':.5,
                    '_v6_canary_pass':True, '_v6_peak_rss':1024, '_v6_fixed':{'peak_rss_limit_bytes':2048}})
        self.reject(lambda: execute_nodes(RSS_BRANCH.orelse[:-1], env), 'GLOBAL_NATIVE_RSS_LIMIT')
        self.assertEqual(env['_v6_peak_rss'], 3072)
        self.assertEqual(child.calls, 1)

    def test_owned_exit_cannot_erase_prior_peak_over_cap(self):
        invoke, clock, proc, child, env = fixture(polls=(0,))
        env.update({'_v6_total_deadline':1., '_v6_outer_deadline':2., '_v6_canary_deadline':.5,
                    '_v6_canary_pass':True, '_v6_peak_rss':3072, '_v6_fixed':{'peak_rss_limit_bytes':2048}})
        self.reject(lambda: execute_nodes(RSS_BRANCH.orelse[:-1], env), 'GLOBAL_NATIVE_RSS_LIMIT')
        self.assertEqual(env['_v6_peak_rss'], 3072)

    def test_wrong_child_or_group_rejected_before_poll(self):
        invoke, clock, proc, child, env = fixture(polls=(0,), pid=999)
        self.reject(invoke)
        self.assertEqual(child.calls, 0)
        self.assertEqual(proc.counts, {'stat':0, 'status':0})
        invoke, clock, proc, child, env = fixture(polls=(0,))
        self.reject(lambda: env['_v6_missing_rss_reobserve'](123, 124, 1.))
        self.assertEqual(child.calls, 0)
        env['_v6_child'] = None
        self.reject(invoke)

    def test_none_poll_keeps_pid_group_start_and_malformed_rss_checks(self):
        cases = [
            {'stats':[stat_text(pid=999)]},
            {'stats':[stat_text(group=999)]},
            {'stats':[stat_text(), stat_text(start=988)]},
            {'stats':[stat_text(), stat_text(), stat_text(start=988)]},
            {'statuses':[status_text(pid=999)]},
            {'statuses':[status_text(tgid=999)]},
            {'statuses':[status_text('-1 kB')]},
            {'statuses':[status_text('3 MB')]},
            {'statuses':[status_text('1 kB')+'VmRSS: 2 kB\n']},
        ]
        for case in cases:
            with self.subTest(case=case):
                invoke, clock, proc, child, env = fixture(**case)
                self.reject(invoke)
                self.assertGreater(child.calls, 0)

    def test_poll_crossing_local_deadline_cannot_rescue_exit(self):
        for result in (None, 0, 7):
            with self.subTest(result=result):
                invoke, clock, proc, child, env = fixture(polls=((result, .1),))
                self.reject(invoke)
                self.assertEqual(child.calls, 1)
                self.assertEqual(proc.counts, {'stat':0, 'status':0})

    def test_poll_crossing_global_deadline_cannot_rescue_exit(self):
        for result in (None, 0, 7):
            with self.subTest(result=result):
                invoke, clock, proc, child, env = fixture(polls=((result, .03),), deadline=.02)
                self.reject(invoke, 'RESOURCE_OBSERVATION_DEADLINE')
                self.assertEqual(child.calls, 1)
                self.assertEqual(proc.counts, {'stat':0, 'status':0})

    def test_already_expired_global_deadline_prevents_poll(self):
        invoke, clock, proc, child, env = fixture(polls=(0,), deadline=0.)
        self.reject(invoke, 'RESOURCE_OBSERVATION_DEADLINE')
        self.assertEqual(child.calls, 0)

    def test_slow_proc_crossing_local_or_global_deadline_still_fails(self):
        for name in ('stat', 'status'):
            for deadline, delay, code in ((1., .1, 'NATIVE_RSS_EVIDENCE_REQUIRED'),
                                          (.02, .03, 'RESOURCE_OBSERVATION_DEADLINE')):
                with self.subTest(name=name, deadline=deadline):
                    kwargs = {'stats':[(stat_text(), delay)]} if name == 'stat' else {'statuses':[(status_text('1 kB'), delay)]}
                    invoke, clock, proc, child, env = fixture(deadline=deadline, **kwargs)
                    self.reject(invoke, code)
                    self.assertEqual(child.calls, 1)

    def test_existing_proc_disappearance_and_zombie_evidence_unchanged(self):
        for case in ({'stats':[FileNotFoundError('invented only')]},
                     {'stats':[stat_text(state='Z', threads=1, virtual=0, resident=0)], 'statuses':[status_text(state='Z')]}):
            with self.subTest(case=repr(case)):
                invoke, clock, proc, child, env = fixture(**case)
                self.assertEqual(invoke(), 0)
                self.assertEqual(child.calls, 1)

if __name__ == '__main__':
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WrapperExitTests))
    unchanged = BASE.read_bytes() == OLD_RAW and NEW.read_bytes() == NEW_RAW
    receipt = {
        'status':'PASS_SYNTHETIC_ONLY' if result.wasSuccessful() and unchanged else 'FAIL_SYNTHETIC_ONLY',
        'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'tests_run':result.testsRun, 'failures':len(result.failures), 'errors':len(result.errors),
        'old_wrapper_sha256':sha(OLD_RAW), 'new_wrapper_sha256':sha(NEW_RAW),
        'test_source_sha256':sha(Path(__file__).read_bytes()), 'sources_unchanged':unchanged,
        'execution_scope':'Only actual extracted helper and cap/final-wait AST with invented in-memory proc, clock, child; no launcher/module import/main execution.',
        'real_processes_started':0, 'native_calls':0, 'competition_data_read':False,
        'model_or_scientific_code_executed':False, 'notebook_candidate_created':False,
        'launch_or_submission_qualified':False, 'official_score_claimed':False,
        'test_output':stream.getvalue(),
    }
    target = HERE/('WRAPPER_EXIT_SYNTHETIC_TEST_RESULT_'+uuid.uuid4().hex+'.json')
    with target.open('x') as handle:
        json.dump(receipt, handle, indent=2); handle.write('\n')
    print(json.dumps({'status':receipt['status'], 'tests_run':result.testsRun,
                      'receipt':target.name, 'receipt_sha256':sha(target.read_bytes()),
                      'test_source_sha256':receipt['test_source_sha256']}))
    if not result.wasSuccessful():
        print(stream.getvalue())
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
