"""Invented tests only; no task/query/output data. SPDX-License-Identifier: MIT."""
import json
import unittest
import numpy as np
from paired_slice_audit import input_slices, paired_summary, exact_sign_p


class SliceAuditTests(unittest.TestCase):
    def test_paired_constant_and_ties(self):
        r=paired_summary([.2,.3,.4],[.3,.4,.5],bootstrap=100)
        self.assertAlmostEqual(r['mean_delta'],.1)
        self.assertAlmostEqual(r['percentile_interval'][0],.1)
        self.assertEqual(r['wins'],3)
        r=paired_summary([.5,.5],[.5,.5],bootstrap=100)
        self.assertEqual(r['ties'],2);self.assertEqual(r['exact_direction_sign_p'],1)

    def test_equal_directions_unequal_magnitude(self):
        r=paired_summary([.1,.8],[.5,.6],bootstrap=100)
        self.assertEqual((r['wins'],r['losses']),(1,1))
        self.assertAlmostEqual(r['mean_delta'],.1)
        self.assertEqual(r['exact_direction_sign_p'],1)
        self.assertAlmostEqual(r['mean_gain_when_improved'],.4)
        self.assertAlmostEqual(r['mean_loss_when_worse'],.2)

    def test_exact_sign_known_cases(self):
        self.assertEqual(exact_sign_p(0,0),1)
        self.assertEqual(exact_sign_p(9,9),1)
        self.assertAlmostEqual(exact_sign_p(5,0),.0625)
        self.assertEqual(exact_sign_p(5,0),exact_sign_p(0,5))

    def test_chunk_matches_frozen_full_draw(self):
        a=.2+np.arange(7)/10;b=a+.1
        b[[0,2]]-=.2
        expected=(b-a)[np.random.default_rng(77).integers(0,7,size=(513,7))].mean(1)
        r=paired_summary(a,b,bootstrap=513,seed=77)
        np.testing.assert_allclose(r['percentile_interval'],np.quantile(expected,[.05,.95]),rtol=0,atol=1e-14)
        self.assertEqual(r,paired_summary(a,b,bootstrap=513,seed=77))

    def test_fixed_input_selection_and_tied_quantiles(self):
        gate=np.array([True,True,True,False]);prob=[.1,.2,.3,.0];analog=[.1,.5,.9,.0]
        masks,q=input_slices(gate,prob,analog,np.array([False,True,False,True]))
        self.assertEqual(masks['S1_primary'].tolist(),[True,False,False,False])
        self.assertEqual(masks['S2_np_proxy'].tolist(),[False,True,False,False])
        self.assertAlmostEqual(q['confidence_tercile'],.1+(.2-.1)*2/3)
        m,_=input_slices([True,True],[.2,.2],[.5,.5],[False,False])
        self.assertEqual(m['S1_primary'].tolist(),[True,True])

    def test_outcome_order_is_material(self):
        a=[1,0,.5];b=[1,.5,0]
        self.assertNotEqual(paired_summary(a,b,bootstrap=100),paired_summary(a,list(reversed(b)),bootstrap=100))

    def test_bad_inputs_rejected(self):
        for a,b in [([],[]),([.1],[.1,.2]),([float('nan')],[.2]),([-.1],[0]),([1.1],[0]),(['.1'],['.2']),([True],[False]),([[.1]],[[.2]])]:
            with self.subTest(a=a):
                with self.assertRaises(ValueError):paired_summary(a,b,bootstrap=100)
        for kw in [dict(bootstrap=True),dict(bootstrap=99),dict(seed=-1),dict(seed=True),dict(confidence=1),dict(confidence=float('nan'))]:
            with self.assertRaises(ValueError):paired_summary([.1],[.2],**kw)
        with self.assertRaises(ValueError):input_slices([1,1],[.1,.2],[.2,.3],[False,False])
        with self.assertRaises(ValueError):input_slices([False],[.1],[.2],[False])

    def test_scalar_receipt_and_non_mutation(self):
        a=np.array([0.,.5]);b=np.array([.5,.25]);copya=a.copy();copyb=b.copy()
        r=paired_summary(a,b,bootstrap=100)
        np.testing.assert_array_equal(a,copya);np.testing.assert_array_equal(b,copyb)
        json.dumps(r,allow_nan=False)
        for key in ('independent_holdout_certified','domain_transport_certified','promotion_authorized','explicit_unit_records_exported','aggregate_privacy_certified'):
            self.assertFalse(r[key])


if __name__=='__main__':unittest.main()
