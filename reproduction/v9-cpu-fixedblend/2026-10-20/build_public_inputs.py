"""SOURCE-ONLY portable metadata adapter; no model, prediction or score.

SPDX-License-Identifier: Apache-2.0
Rebuild exactly the published development rows from PUBLIC split V1 and V7.
No historical private canonical map, old assay, truth fingerprint or positive
candidate index is an input. This adapter itself has not been executed here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal


def binding(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            h.update(block)
    return {'bytes':path.stat().st_size, 'sha256':h.hexdigest()}


def check(path, expected):
    if binding(path) != {key:expected[key] for key in ('bytes','sha256')}:
        raise ValueError('Public version input hash mismatch: '+Path(path).name)


def main():
    def expired(_signum, _frame):
        raise TimeoutError('Public metadata adapter60s deadline; preserve partial output')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 60)
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
                 'VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[name] = '2'
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bank','spectra','cache','split','v9','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).absolute().parent
    pins = json.loads((here/'PUBLIC_INPUT_PINS.json').read_text())
    roots = {name:getattr(args,name).resolve() for name in ('bank','spectra','cache','split','v9')}
    roots['source'] = here/'source'
    roots['derived'] = args.output.absolute()
    roots['derived'].mkdir(exist_ok=False)
    # Only public scalar/group metadata is decoded; raw FP/logit/weight files
    # are verified as bytes here and used later by the unchanged measured core.
    for name, expected in pins['split_derivation_files'].items():
        check(roots['split']/name, expected)
    for key, expected in pins['files'].items():
        area, name = expected['location']
        if area != 'derived':
            check(roots[area]/name if name else roots[area], expected)
    import numpy as np
    if np.__version__ != '2.2.6':
        raise ValueError('The measured metadata writer used NumPy2.2.6')
    load = lambda directory,name: np.load(directory/name, allow_pickle=False)
    mask = load(roots['split'],'split_train0_development1.npy') == 1
    cache_rows = load(roots['split'],'cache_query_rows.npy')[mask]
    trainer = load(roots['split'],'trainer_structure_indices.npy')[mask]
    groups = load(roots['split'],'canonical_group_ids.npy')[mask]
    spectra = load(roots['cache'],'spectrum_indices.npy')[cache_rows]
    if cache_rows.shape != (2653,) or len(np.unique(groups)) != 2650:
        raise ValueError('Frozen public development scope mismatch')
    values = {'eligible_cache_rows':cache_rows, 'eligible_trainer_indices':trainer,
              'eligible_groups':groups, 'eligible_spectrum_indices':spectra}
    for key, value in values.items():
        filename = pins['files'][key]['location'][1]
        np.save(roots['derived']/filename, value, allow_pickle=False)
        check(roots['derived']/filename, pins['files'][key])
    files = {}
    for key, expected in pins['files'].items():
        area, name = expected['location']
        path = roots[area]/name if name else roots[area]
        check(path, expected)
        files[key] = dict(path=str(path), bytes=expected['bytes'], sha256=expected['sha256'])
    contract = {'schema':'public-v9-cpu-fixedblend-input-contract/1', 'files':files,
                'development_rows':2653, 'canonical_groups':2650,
                'historical_private_map_required':False, 'metadata_adapter_only':True}
    with (roots['derived']/'public-inputs.json').open('x') as stream:
        json.dump(contract,stream,indent=2,sort_keys=True);stream.write('\n')
    signal.setitimer(signal.ITIMER_REAL, 0)
    print('Public metadata contract ready; no model or score was run.')


if __name__ == '__main__':
    main()
