"""Meaningful CPU regressions; run anywhere with Python and NumPy.

No Torch/model imports, files from the workspace, held labels, or API calls.
"""
import unittest
import numpy as np
from ce_mixing import (Refusal, ce_bucket, validate_energies, mass_basis,
                       finalize, mixture, paired_outputs, entropy_similarity)


def released_post_reference(sp, k=100):
    # Numerical oracle transcribed from pinned GLACIER V1 gl_runner.py::post.
    sp = sp[(sp[:, 1] > 0) & (sp[:, 0] > 0)]
    key = np.round(sp[:, 0].astype(np.float64), 4)
    u, inv = np.unique(key, return_inverse=True)
    it = np.zeros(len(u), np.float64)
    np.maximum.at(it, inv, sp[:, 1].astype(np.float64))
    if len(u) > k:
        o = np.argsort(-it, kind='stable')[:k]; u, it = u[o], it[o]
    o = np.argsort(u); u, it = u[o], it[o]
    return np.column_stack((u.astype(np.float32), (it / it.max()).astype(np.float32)))


def nonlinear_forward(ce):
    # Independent toy model: intensity curvature makes f(mean CE) differ
    # from the equal mixture of f(CE), with an explicit analytic answer.
    return np.array([[100., 1.], [200., (ce / 20.) ** 2]], dtype=np.float64)


class MixingContract(unittest.TestCase):
    def test_rounding_matches_released_convention(self):
        self.assertEqual([ce_bucket(x) for x in [0., 7.5, 12.5, 17.5]], [5., 10., 10., 20.])
        for x in [True, '40', float('nan'), float('inf')]:
            with self.assertRaises(Refusal): ce_bucket(x)

    def test_frozen_ce_refusals(self):
        self.assertEqual(validate_energies([60, 20, 40]), (20., 40., 60.))
        for x in [[], [20, 40], [20, 40, 60, 80], [40, 40], [40, float('nan')], [True], np.array([40.])]:
            with self.assertRaises(Refusal): validate_energies(x)

    def test_duplicate_max_and_sparse_basis(self):
        a=np.array([[100.00001, 2.], [100.00002, 5.], [200., 3.], [0., 6.], [300., 0.]])
        mz,it=mass_basis(a)
        np.testing.assert_array_equal(mz,[100.,200.]);np.testing.assert_array_equal(it,[5.,3.])

    def test_exact_released_final_processing(self):
        rng=np.random.default_rng(913)
        a=np.column_stack((rng.uniform(10,1000,220),rng.uniform(0.01,30,220)))
        a=np.vstack((a,[0.,10.],[100.,0.],[100.,5.],[100.,10.]))
        np.testing.assert_array_equal(finalize(a),released_post_reference(a))
        self.assertEqual(finalize(a).shape,(100,2));self.assertEqual(finalize(a).dtype,np.float32)

    def test_singleton_exact_parity(self):
        raw=nonlinear_forward(40.)
        a,b=paired_outputs({40.:raw},[40.])
        np.testing.assert_array_equal(a,b)

    def test_independent_nonlinear_reference(self):
        raws={e:nonlinear_forward(e) for e in (20.,40.,60.)}
        a,b=paired_outputs(raws,[20.,40.,60.])
        expected_a=np.array([[100.,.25],[200.,1.]],np.float32)
        expected_b=np.array([[100.,(1.+.25+1./9.)/3.],[200.,1.]],np.float32)
        np.testing.assert_array_equal(a,expected_a)
        np.testing.assert_allclose(b,expected_b,rtol=0,atol=1e-7)
        self.assertFalse(np.array_equal(a,b))
        self.assertGreater(entropy_similarity(expected_b,b),entropy_similarity(expected_b,a))

    def test_same_final_budget_without_early_truncation(self):
        raw={20.:np.column_stack((np.arange(1.,151.),np.ones(150))),
             40.:np.column_stack((np.arange(101.,251.),np.ones(150))),
             60.:np.column_stack((np.arange(101.,251.),np.ones(150)))}
        out=mixture(raw,[20.,40.,60.])
        self.assertEqual(out.shape,(100,2));self.assertTrue(np.any(out[:,0]>150))
        # The 101..150 overlap has all three sources and must survive.
        self.assertEqual(np.count_nonzero((out[:,0]>=101)&(out[:,0]<=150)),50)

    def test_order_and_input_immutability(self):
        raw={e:nonlinear_forward(e)[::-1].copy() for e in (60.,20.,40.)}
        copies={e:a.copy() for e,a in raw.items()}
        a=mixture(raw,[60.,20.,40.]);b=mixture(dict(reversed(list(raw.items()))),[20.,40.,60.])
        np.testing.assert_array_equal(a,b)
        for e in raw:np.testing.assert_array_equal(raw[e],copies[e])

    def test_invalid_raw_contract(self):
        invalid=[np.array([[1,2]]),np.array([[1.,2.]],dtype=np.float16),
                 np.zeros((0,2)),np.ones((2,3)),np.array([[1.,np.nan]]),
                 np.array([[np.inf,1.]]),np.array([[0.,1.]]),[[1.,2.]]]
        for a in invalid:
            with self.assertRaises(Refusal):finalize(a)

    def test_missing_or_extra_forward_results_refused(self):
        a=nonlinear_forward(40.)
        for raw,ce in [({40.:a},[20.,40.,60.]),({20.:a,40.:a},[40.]),({20.:a,60.:a},[20.,40.,60.])]:
            with self.assertRaises(Refusal):paired_outputs(raw,ce)

    def test_per_energy_amplitude_scale_invariance(self):
        raw={e:nonlinear_forward(e) for e in (20.,40.,60.)}
        scaled={e:np.column_stack((a[:,0],a[:,1]*scale)) for (e,a),scale in zip(raw.items(),[3.,5.,7.])}
        np.testing.assert_array_equal(mixture(raw,[20.,40.,60.]),mixture(scaled,[20.,40.,60.]))


    def test_finite_mass_overflow_and_rounding_refused(self):
        for mass in [float(np.finfo(np.float32).max)*2., 1e-8]:
            with self.assertRaises(Refusal):finalize(np.array([[mass,1.]],np.float64))

    def test_bad_output_containers_refused(self):
        for value in [None, [], (), np.array([40.]), '40']:
            with self.assertRaises(Refusal):paired_outputs(value,[40.])


if __name__ == '__main__':
    unittest.main()
