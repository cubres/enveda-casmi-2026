"""Verify published completed RR files; never run a model or search a weight.
SPDX-License-Identifier: Apache-2.0
"""
import hashlib
import json
from pathlib import Path


def main():
    import numpy as np
    if np.__version__ != '2.2.6':
        raise ValueError('Use pinned NumPy2.2.6 for the seeded bootstrap')
    root = Path(__file__).absolute().parent
    result = json.loads((root/'PUBLIC_RESULT.json').read_text())
    arrays = []
    for name, shape in [('per_query_rr.npy',(2653,2)),('group_rr.npy',(2650,2))]:
        path = root/'results'/name
        raw = path.read_bytes()
        expected = result['artifacts'][name]
        assert len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256']
        values = np.load(path,allow_pickle=False)
        assert values.shape == shape and values.dtype == np.float64 and np.isfinite(values).all()
        assert np.all((values >= 0) & (values <= 1))
        arrays.append(values)
    query, groups = arrays
    assert np.array_equal(query.mean(axis=0),result['unconditional_query_MRR25'])
    assert np.array_equal(groups.mean(axis=0),result['canonical_group_MRR25'])
    delta = groups[:,1]-groups[:,0]
    rng = np.random.default_rng(20261020)
    bootstrap = np.asarray([delta[rng.integers(len(delta),size=len(delta))].mean() for _ in range(2000)])
    assert float(delta.mean()) == result['canonical_group_delta']
    assert np.array_equal(np.quantile(bootstrap,[.025,.975]),result['bootstrap_group_delta_95pct'])
    print('Saved local result verified. The 95% interval includes zero; no official score is claimed.')


if __name__ == '__main__':
    main()
