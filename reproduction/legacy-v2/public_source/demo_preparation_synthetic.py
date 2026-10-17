"""Small deterministic reconstruction check using invented records only.

Runs no model, training, assay or remote request. The only inputs read are the
adjacent pinned source files and synthetic files created by this invocation.
"""
import argparse
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import pickle
import time
import types
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from prepare_legacy_exports import export_flat, export_selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New synthetic workspace')
    args = parser.parse_args()
    home = Path(__file__).resolve().parent
    source_pins = {
        'speclib.py': '27e149dd8f705389a969f1b9232b7b2451c7f3189f5586f5a42160864ff403eb',
        'fpmodel.py': '69f2656778a08233e22235bf4853f0b3d2420b431390a32d6c8ed453cde85c76',
        'build_dataset.py': 'ec90d3d9ef3ec9b1e45d2dc9e2e766439ef7431cce8f8388ccb96b0be96a517b',
    }
    for name, expected in source_pins.items():
        assert hashlib.sha256((home / name).read_bytes()).hexdigest() == expected, name
    out = args.output.absolute(); out.mkdir(parents=True, exist_ok=False)
    (out / 'source').mkdir()
    rows = []
    for i in range(4):
        rows.append(dict(ingest_lib='enveda-np-examples' if i < 2 else 'synthetic-library',
            inchikey14='SYNTHETIC_AAAA' if i < 2 else 'SYNTHETIC_BBBB',
            normalized_smiles='C' if i < 2 else 'CC', molecular_formula='CH4' if i < 2 else 'C2H6',
            adduct='[M+H]+', precursor_mz=100., instrument_type='Orbitrap', ionization_mode='positive',
            collision_energy_orig='20;40', collision_energy_ev=[20., 40.], precursor_error_ppm=0.,
            ms2_mzs=[10.123456789, 20.234567891, 30.345678912],
            ms2_normalized_intensities=[.1, .2, .3]))
    train = out / 'source/train.parquet'
    pq.write_table(pa.Table.from_pylist(rows), train)
    with contextlib.redirect_stdout(io.StringIO()):
        count = export_flat(train, out / 'data')
    off = np.load(out / 'data/lib_off.npy', allow_pickle=False)
    mz = np.load(out / 'data/lib_mz.npy', allow_pickle=False)
    intensity = np.load(out / 'data/lib_in.npy', allow_pickle=False)
    assert count == {'spectra':4, 'peaks':12}
    assert np.array_equal(off, np.array([0,3,6,9,12], np.int64))
    assert mz.dtype == intensity.dtype == np.float32
    assert mz[:3].tobytes() == np.asarray(rows[0]['ms2_mzs'], np.float32).tobytes()
    assert intensity[:3].tobytes() == np.asarray(rows[0]['ms2_normalized_intensities'], np.float32).tobytes()
    # This pickle was created above from invented local records, not downloaded.
    with (out / 'data/lib_meta.pkl').open('rb') as stream:
        meta = pickle.load(stream)

    # Exact pure preprocessing definitions; exclude imports, classes and models.
    tree = ast.parse((home / 'fpmodel.py').read_text())
    constants = {'MAX_PEAKS','ADDUCT_LIST','ADDUCT_IX','INSTR_LIST','INSTR_IX'}
    selected = [node for node in tree.body if
        isinstance(node, ast.FunctionDef) and node.name in {'instr_family','prep_peaks'} or
        isinstance(node, ast.Assign) and len(node.targets)==1 and
        isinstance(node.targets[0], ast.Name) and node.targets[0].id in constants]
    assert len(selected) == 7
    ns = {'np':np}
    exec(compile(ast.Module(body=selected, type_ignores=[]), 'pinned_pure_preprocessing', 'exec'), ns)
    prepared = [ns['prep_peaks'](mz[off[i]:off[i+1]], intensity[off[i]:off[i+1]], 100.) for i in range(4)]
    direct_old = ns['prep_peaks'](rows[0]['ms2_mzs'], rows[0]['ms2_normalized_intensities'], 100.)
    assert prepared[0][1].tobytes() != direct_old[1].tobytes(), 'fixture must expose early-rounding drift'
    assert all(a.dtype == b.dtype == np.float32 and len(a) == len(b) == 3 for a,b in prepared)

    # Execute only the exact retained split statement slice, on the toy metadata.
    dataset_tree = ast.parse((home / 'build_dataset.py').read_text())
    main_block = next(n for n in dataset_tree.body if isinstance(n, ast.If))
    def assigns(node, name):
        return isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
    begin = next(i for i,n in enumerate(main_block.body) if assigns(n, 'coco'))
    finish = next(i for i,n in enumerate(main_block.body) if assigns(n, 'is_val'))
    libs = next(n for n in dataset_tree.body if assigns(n, 'NP_LIBS'))
    (out / 'db').mkdir()
    pd.DataFrame({'ik14':['SYNTHETIC_AAAA']}).to_parquet(out / 'db/coconut_clean.parquet', index=False)
    split_ns = {'np':np, 'pd':pd, 'meta':meta, 'idx':np.arange(4)}
    previous = Path.cwd()
    try:
        os.chdir(out)
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(ast.Module(body=[libs]+main_block.body[begin:finish+1], type_ignores=[]),
                         'pinned_original_split_statements', 'exec'), split_ns)
    finally:
        os.chdir(previous)
    is_val = split_ns['is_val']
    assert np.array_equal(is_val, [True,True,False,False])
    assert all(len(set(is_val[[i for i,k in enumerate(meta['inchikey14']) if k==key]])) == 1
               for key in set(meta['inchikey14']))
    (out / 'ds').mkdir()
    np.savez(out / 'ds/spec.npz', off=off, mz=np.concatenate([a for a,b in prepared]),
        it=np.concatenate([b for a,b in prepared]), prec=np.full(4,100.,np.float32),
        ad=np.zeros(4,np.int16), ins=np.ones(4,np.int8), ce=np.full(4,30.,np.float32),
        mode=np.ones(4,np.float32), six=np.array([0,0,1,1],np.int32),
        is_val=is_val, src=np.arange(4,dtype=np.int64))
    with np.load(out / 'ds/spec.npz', allow_pickle=False) as restored:
        assert set(restored.files) == {'off','mz','it','prec','ad','ins','ce','mode','six','is_val','src'}
        assert restored['off'].tobytes() == off.tobytes()
        assert restored['mz'].tobytes() == np.concatenate([a for a,b in prepared]).tobytes()
        assert restored['it'].tobytes() == np.concatenate([b for a,b in prepared]).tobytes()
        assert restored['is_val'].tobytes() == is_val.tobytes()
        assert np.array_equal(restored['src'], np.arange(4,dtype=np.int64))

    # Invented full10407 target matrix; validates selection, padding and row order.
    full = np.zeros((4,10407),np.uint8)
    full[:,0]=1;full[0,3]=1;full[:2,40]=1;full[2:,999]=1
    np.save(out / 'data/struct_fp.npy',np.packbits(full,axis=1),allow_pickle=False)
    with (out / 'data/struct_fp_meta.pkl').open('xb') as stream:
        pickle.dump({'keys':['TOY_0','TOY_1','TOY_2','TOY_3'], 'smiles':['C','CC','CCC','CCCC'],
                     'nbits':10407}, stream, protocol=4)
    selected_summary=export_selected(out / 'data',out / 'up_train')
    bits=np.load(out / 'up_train/fp_bits.npy',allow_pickle=False)
    packed=np.load(out / 'up_train/fp_sel.npy',allow_pickle=False)
    assert np.array_equal(bits,[3,40,999]) and selected_summary['selected_bits']==3
    assert np.array_equal(np.unpackbits(packed,axis=1)[:,:3],full[:,bits])
    assert not np.unpackbits(packed,axis=1)[:,3:].any()
    import sys
    assert 'torch' not in sys.modules
    result={'status':'PASS_INVENTED_PREPARATION_REBUILD_ONLY','invented_spectra':4,
        'invented_full_fingerprint_rows':4,'checks':['flat_float32_rounding','offsets_and_row_order',
        'pure_peak_preprocessing','old_rounding_drift_fixture','original_structure_split_statements',
        'single_split_per_structure','prepared_cache_roundtrip','original_frequency_selection',
        'selected_column_order','zero_padding'], 'source_sha256':source_pins,
        'runtime':{'python':sys.version.split()[0], 'numpy':np.__version__, 'pandas':pd.__version__, 'pyarrow':pa.__version__},
        'model_or_training_or_assay':False,'real_competition_records_read':False,
        'scope':'Toy serialization/selection/preprocessing/split checks only; no historical full cache or checkpoint byte reproduction claimed.'}
    with (out / 'SYNTHETIC_RESULT.json').open('x') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({'status':result['status'],'checks':len(result['checks'])}))


if __name__ == '__main__':
    main()
