"""Invented fixtures only. No competition files, identifiers, labels or models."""
import copy
import json
import math
import unittest

from strict_protection import validate_protection

ARM, CONTROL, INPUT = 'a' * 64, 'b' * 64, 'c' * 64
IDS = ['invented-A', 'invented-B']
BASE = [['CC', 'CCC'], ['CO', 'CCO']]
BINDINGS = {'candidate_pool': INPUT, 'library': 'd' * 64}


def fixture():
    return dict(schema_version=1, source_sha256=ARM, scope='neutral_full_core',
                control_source_sha256=CONTROL, ids=IDS[:], molecules=2,
                counterfactual_checked=2, gate_open=0, fired=0, not_fired=2, errors=0,
                arm_input_bindings=BINDINGS.copy(), control_input_bindings=BINDINGS.copy(),
                rows={m: dict(lib_max=1.0, gate_open=False, fired=False,
                             output=r[:], counterfactual=r[:]) for m, r in zip(IDS, BASE)})


_UNSET = object()

def check(audit=_UNSET, rows=None, **kw):
    args=dict(expected_source_sha256=ARM, lib_gate=.985, historical_rows=BASE,
              expected_control_source_sha256=CONTROL, expected_input_bindings=BINDINGS)
    args.update(kw)
    return validate_protection(IDS, BASE if rows is None else rows, fixture() if audit is _UNSET else audit, **args)


class ProtectionTests(unittest.TestCase):
    def hold(self, receipt, code=None):
        self.assertEqual(receipt['status'], 'HOLD')
        self.assertFalse(receipt['matched_full_core_contract'])
        if code:
            self.assertIn(code, receipt['failures'])

    def test_complete_neutral_contract(self):
        r=check()
        self.assertEqual(r['status'],'PASS_NEUTRAL_CORE_CONTRACT')
        self.assertEqual(r['counts']['protected_rows'],2)
        self.assertTrue(r['matched_full_core_contract'])
        self.assertFalse(r['remote_execution_authenticated'])
        self.assertFalse(r['submission_authorized'])

    def test_terminal_scope_cannot_be_full_core(self):
        a=fixture();a['scope']='terminal_hook'
        self.hold(check(a),'counterfactual_scope')
        r=check(a,required_scope='terminal_hook')
        self.assertEqual(r['status'],'PASS_TERMINAL_HOOK_ONLY')
        self.assertFalse(r['matched_full_core_contract'])

    def test_empty_and_partial_audit(self):
        for names in ([],[IDS[0]]):
            with self.subTest(names=names):
                a=fixture();a['rows']={k:a['rows'][k] for k in names}
                a['molecules']=a['counterfactual_checked']=len(names)
                self.hold(check(a),'audit_exact_coverage')

    def test_fired_closed_gate_cannot_escape(self):
        a=fixture();a['rows'][IDS[1]]['fired']=True;a['fired']=1;a['not_fired']=1
        self.hold(check(a),'fired_outside_open_gate')

    def test_complete_protected_order_not_top1(self):
        a=fixture();out=['CO','CCN'];a['rows'][IDS[1]]['output']=out
        rows=[BASE[0],out]
        self.hold(check(a,rows),'protected_complete_order_changed')

    def test_faithful_terminal_tail_drift_still_holds_history(self):
        a=fixture();out=['CO','CCN'];a['scope']='terminal_hook'
        a['rows'][IDS[1]].update(output=out,counterfactual=out[:])
        self.hold(check(a,[BASE[0],out],required_scope='terminal_hook'),
                  'protected_historical_complete_order_changed')

    def test_gate_open_changed_candidates_pass_only_declared_arm(self):
        a=fixture();out=['CCN','CO'];r=a['rows'][IDS[1]]
        r.update(lib_max=.5,gate_open=True,fired=True,output=out)
        a.update(gate_open=1,fired=1,not_fired=1)
        rows=[BASE[0],out]
        self.assertEqual(check(a,rows)['status'],'PASS_NEUTRAL_CORE_CONTRACT')
        self.hold(check(a,rows,exact_control=True),'protected_complete_order_changed')

    def test_nonfinite_and_non_numeric_gate(self):
        for v in (float('nan'),float('inf'),-float('inf'),'1.0',True,None,10**1000):
            with self.subTest(value_type=type(v).__name__):
                a=fixture();a['rows'][IDS[0]]['lib_max']=v
                self.hold(check(a),'finite_library_gate_evidence')
        self.hold(check(lib_gate=float('nan')),'library_gate_invalid')

    def test_gate_record_disagrees(self):
        a=fixture();a['rows'][IDS[0]]['gate_open']=True
        self.hold(check(a),'recorded_gate_disagrees')

    def test_count_consistency(self):
        for field in ('molecules','counterfactual_checked','gate_open','fired','not_fired'):
            for value in (-1,True,42):
                with self.subTest(field=field,value=value):
                    a=fixture();a[field]=value;self.hold(check(a))

    def test_missing_duplicate_or_wrong_identity(self):
        a=fixture();a['ids']=list(reversed(IDS));self.hold(check(a),'audit_identity_order')
        a=fixture();a['rows']['invented-extra']=a['rows'][IDS[0]]
        self.hold(check(a),'audit_exact_coverage')
        self.hold(validate_protection([IDS[0],IDS[0]],BASE,fixture(),expected_source_sha256=ARM,lib_gate=.985),'submission_identity')

    def test_bad_full_output_or_control(self):
        for field in ('output','counterfactual'):
            for v in (None,[],['CC','CC'],[''],['CC']*26,{'bad':'shape'}):
                with self.subTest(field=field):
                    a=fixture();a['rows'][IDS[0]][field]=v;self.hold(check(a))
        a=fixture();a['rows'][IDS[0]]['output']=['C','CCC']
        self.hold(check(a),'audit_output_disagrees_with_submission')

    def test_source_and_binding_manifest(self):
        a=fixture();a['source_sha256']='e'*64;self.hold(check(a),'source_binding')
        a=fixture();a['control_source_sha256']='e'*64;self.hold(check(a),'neutral_core_source_binding')
        self.hold(check(expected_input_bindings=None),'complete_expected_input_manifest_missing')
        for field in ('arm_input_bindings','control_input_bindings'):
            for values in ({},{'candidate_pool':INPUT},{**BINDINGS,'extra':'e'*64},
                           {**BINDINGS,'candidate_pool':'e'*64}):
                a=fixture();a[field]=values;self.hold(check(a),field+'_incomplete_or_changed')

    def test_malformed_audit_scope_and_missing_history(self):
        for a in ([],None,{},dict(fixture(),scope=[]),dict(fixture(),errors=1)):
            self.hold(check(a))
        self.hold(check(historical_rows=None),'historical_reference_missing_or_malformed')
        self.hold(check(exact_control='yes'),'control_flags_invalid')

    def test_historical_waiver_is_only_a_terminal_diagnostic(self):
        self.hold(check(historical_rows=None, require_historical_match=False),
                  'full_core_historical_reference_required')
        a=fixture();a['scope']='terminal_hook'
        r=check(a,required_scope='terminal_hook',historical_rows=None,require_historical_match=False)
        self.assertEqual(r['status'],'PASS_TERMINAL_HOOK_ONLY')
        self.assertFalse(r['matched_full_core_contract'])

    def test_receipt_never_discloses_private_records_or_lists(self):
        r=check();s=json.dumps(r)
        self.assertTrue(all(x not in s for x in IDS))
        self.assertTrue(all(json.dumps(x) not in s for row in BASE for x in row))
        self.assertFalse(r['private_records_exported'])
        self.assertEqual(check(),r)


if __name__=='__main__':
    unittest.main()
