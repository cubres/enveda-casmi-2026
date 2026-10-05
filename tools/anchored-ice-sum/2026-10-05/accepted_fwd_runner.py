#!/usr/bin/env python3
"""AP-2 Stage 1 forward-model runner. Original code written for this project.

Runs the UNMODIFIED upstream ms-pred models (coleygroup/ms-pred @ 708148c, MIT) -- ICEBERG `msg_all`
(gen + inten_contr) and the GLACIER MassSpecGym checkpoint -- inside this process, after putting a private
copy of the exact upstream stack first on sys.path (torch 2.6.0, dgl 2.5.0, torch-scatter 2.1.2,
torch-sparse 0.6.18, RDKit 2025.03.6, pytorch-lightning 2.5.0.post0). The calling notebook keeps its own
torch and RDKit 2026.03.3; it only talks to this process through files or JSON lines.

Modes
  batch IN.json OUT.json   score every item; OUT.json = {id: {"iceberg": [...], "glacier": [...]}}
  serve                    one JSON item per stdin line -> one JSON reply per stdout line (models stay loaded)
  raw IN.json OUT.npz      predicted peak lists only, for parity checks against an upstream reference run

Item: {"id": str, "candidates": [smiles, ...],
       "spectra": [{"mz": [...], "it": [...], "precursor_mz": float, "adduct": str, "ce": float,
                    "instrument": str, "mode": "positive" | "negative"}, ...]}
A score is the mean entropy similarity between a candidate's predicted spectrum and each covered measured
spectrum (positive mode, adduct in --adducts, finite collision energy); null when nothing is covered.

Stack selection: --stack gpu installs wheels/hi + wheels/lo into --site (CUDA build); --stack cpu installs
wheels/cpu + the CPU-agnostic wheels (reference runs); --stack none imports whatever the interpreter has.
"""
import argparse, glob, json, math, os, shutil, subprocess, sys, time

ADDUCTS_DEFAULT = '[M+H]+,[M+Na]+'          # the adducts MassSpecGym actually trains these models on
INSTR_MAP_DEFAULT = 'timsTOF=QTOF,QTOF=QTOF,Orbitrap=Orbitrap,IT-FT=IT-FT'


# ------------------------------------------------------------------------------------------- environment
def install_site(pkg, site, stack):
    """Install the shipped wheels into private target dirs once (marker file). Returns (front, back) dirs."""
    if stack == 'none':
        return None, None
    front, back = os.path.join(site, f'{stack}_front'), os.path.join(site, f'{stack}_back')
    groups = {'gpu': (['hi'], ['lo']), 'cpu': (['cpu', 'cpu_common'], ['lo'])}[stack]
    for target, subdirs in ((front, groups[0]), (back, groups[1])):
        marker = os.path.join(target, '.fwd_site_ok')
        if os.path.exists(marker):
            continue
        stage = target + '_wheels'
        os.makedirs(stage, exist_ok=True)
        files = []
        for sd in subdirs:
            for f in sorted(glob.glob(os.path.join(pkg, 'wheels', sd, '*.whl.fwd'))):
                dst = os.path.join(stage, os.path.basename(f)[:-len('.fwd')])
                if not os.path.exists(dst):
                    shutil.copyfile(f, dst)
                files.append(dst)
        if not files:
            raise RuntimeError(f'no wheels found for {subdirs} under {pkg}/wheels')
        cmd = [sys.executable, '-m', 'pip', 'install', '--no-index', '--no-deps', '--quiet',
               '--disable-pip-version-check', '--target', target] + files
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(f'pip install into {target} failed: {r.stderr[-3000:]}')
        open(marker, 'w').write(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    return front, back


def activate(pkg, front, back):
    if front:
        sys.path.insert(0, front)
    sys.path.insert(0, os.path.join(pkg, 'ms_pred_src'))
    if back:
        # RDKit and Lightning must also shadow the host image inside this subprocess.
        sys.path.insert(0, back)


# ------------------------------------------------------------------------------------------- scoring
def clean_spectrum(mz, it, floor=0.002, top=256):
    import numpy as np
    m = np.asarray(mz, np.float64); i = np.asarray(it, np.float64)
    ok = np.isfinite(m) & np.isfinite(i) & (i > 0)
    m, i = m[ok], i[ok]
    if len(i) == 0:
        return m, i
    keep = i >= floor * i.max()
    m, i = m[keep], i[keep]
    if len(i) > top:
        o = np.argsort(-i, kind='stable')[:top]; m, i = m[o], i[o]
    o = np.argsort(m, kind='stable')
    return m[o], i[o] / i.sum()


def merge_predicted(spec, merge_tol=1e-3, top=100):
    """Predicted rows (m/z, intensity) -> one peak per m/z (max within merge_tol), the `top` strongest kept."""
    import numpy as np
    a = np.asarray(spec, np.float64).reshape(-1, 2)
    a = a[np.isfinite(a).all(1) & (a[:, 1] > 0)]
    if len(a) == 0:
        return np.zeros(0), np.zeros(0)
    a = a[np.argsort(a[:, 0], kind='stable')]
    mz, it = [a[0, 0]], [a[0, 1]]
    for m, v in a[1:]:
        if m - mz[-1] <= merge_tol:
            it[-1] = max(it[-1], v)
        else:
            mz.append(m); it.append(v)
    mz, it = np.array(mz), np.array(it)
    if len(it) > top:
        o = np.argsort(-it, kind='stable')[:top]; o.sort(); mz, it = mz[o], it[o]
    return mz, it / it.sum()


def _weighted(p):
    """Li et al. (2021) entropy weighting of low-entropy spectra."""
    import numpy as np
    s = float(-(p * np.log(p)).sum())
    if s < 3.0:
        w = 0.25 + 0.25 * s
        p = p ** w; p = p / p.sum()
    return p


def entropy_similarity(m1, p1, m2, p2, tol=0.01):
    """1 - (2 H(mix) - H(A) - H(B)) / ln 4, peaks matched one-to-one within tol (strongest first)."""
    import numpy as np
    if len(p1) == 0 or len(p2) == 0:
        return 0.0
    p1, p2 = _weighted(p1), _weighted(p2)
    used = np.zeros(len(m2), bool); mix = []
    matched_b = set()
    for j in np.argsort(-p1, kind='stable'):
        lo, hi = np.searchsorted(m2, m1[j] - tol), np.searchsorted(m2, m1[j] + tol, 'right')
        best, bd = -1, None
        for k in range(lo, hi):
            if not used[k]:
                d = abs(m2[k] - m1[j])
                if bd is None or d < bd:
                    best, bd = k, d
        if best >= 0:
            used[best] = True; matched_b.add(best); mix.append((p1[j] + p2[best]) / 2)
        else:
            mix.append(p1[j] / 2)
    mix.extend(p2[k] / 2 for k in range(len(m2)) if k not in matched_b)
    h = lambda p: float(-(p * np.log(p)).sum())
    mix = np.array(mix)
    return max(0.0, 1.0 - (2 * h(mix) - h(p1) - h(p2)) / math.log(4))


# ------------------------------------------------------------------------------------------- models
class Models:
    def __init__(self, pkg, names, device, bs, max_nodes, threshold):
        import torch
        self.torch, self.device, self.bs = torch, device, bs
        self.max_nodes, self.threshold = max_nodes, threshold
        self.m = {}
        ck = os.path.join(pkg, 'ckpt')
        if 'iceberg' in names:
            from ms_pred.iceberg.joint_model import JointModel as IcebergJoint
            self.m['iceberg'] = IcebergJoint.from_checkpoints(
                os.path.join(ck, 'iceberg_msg_all', 'gen', 'best.ckpt'),
                os.path.join(ck, 'iceberg_msg_all', 'inten_contr', 'best.ckpt')).to(device).eval()
        if 'glacier' in names:
            from ms_pred.glacier.joint_model import JointModel as GlacierJoint
            self.m['glacier'] = GlacierJoint.load_from_checkpoint(
                os.path.join(ck, 'glacier_msg', 'best.ckpt'), map_location='cpu').to(device).eval()

    def predict(self, name, smis, ces, adducts, instruments, precs):
        """Raw upstream predict_mol over lists, in chunks of bs; returns one (rows, 2) numpy array per input."""
        out = []
        with self.torch.no_grad():
            for s in range(0, len(smis), self.bs):
                sl = slice(s, s + self.bs)
                if name == 'iceberg':
                    r = self.m[name].predict_mol(smi=list(smis[sl]), collision_eng=list(ces[sl]),
                                                 precursor_mz=list(precs[sl]), adduct=list(adducts[sl]),
                                                 threshold=self.threshold, device=self.device,
                                                 max_nodes=self.max_nodes, instrument=list(instruments[sl]),
                                                 binned_out=False)
                else:
                    r = self.m[name].predict_mol(smi=list(smis[sl]), collision_eng=list(ces[sl]),
                                                 adduct=list(adducts[sl]), device=self.device,
                                                 instrument=list(instruments[sl]))
                out.extend(x.detach().float().cpu().numpy() for x in r['spec'])
        return out


def conditions(item, allowed, instr_map, ce_bucket):
    """Covered measured spectra grouped by prediction condition (adduct, instrument, CE bucket)."""
    conds = {}
    for sp in item.get('spectra', []):
        add, ce = sp.get('adduct'), sp.get('ce')
        if sp.get('mode', 'positive') != 'positive' or add not in allowed:
            continue
        try:
            ce = float(ce)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(ce):
            continue
        ce_b = round(ce / ce_bucket) * ce_bucket if ce_bucket > 0 else ce
        ins = instr_map.get(str(sp.get('instrument')), instr_map.get('*', 'Unknown'))
        key = (add, ins, float(ce_b))
        conds.setdefault(key, []).append(sp)
    return conds


def score_item(models, item, args, allowed, instr_map, keep_raw=False):
    import numpy as np
    cands = item['candidates']
    conds = conditions(item, allowed, instr_map, args.ce_bucket)
    res = {name: [None] * len(cands) for name in models.m}
    raw = {}
    if not conds or not cands:
        return res, raw, 0
    keys = list(conds)
    meas = {k: [clean_spectrum(sp['mz'], sp['it']) for sp in conds[k]] for k in keys}
    prec = {k: float(np.median([sp['precursor_mz'] for sp in conds[k]])) for k in keys}
    n_jobs = 0
    for name in models.m:
        model_keys = [k for k in keys if name != 'glacier' or k[0] == '[M+H]+']
        jobs = [(c, k) for c in range(len(cands)) for k in model_keys]
        n_jobs += len(jobs)
        if not jobs:
            continue
        preds = models.predict(name, [cands[c] for c, _ in jobs], [k[2] for _, k in jobs],
                               [k[0] for _, k in jobs], [k[1] for _, k in jobs], [prec[k] for _, k in jobs])
        sims = {c: [] for c in range(len(cands))}
        for (c, k), sp in zip(jobs, preds):
            if keep_raw:
                raw[(name, c, k)] = sp
            pm, pp = merge_predicted(sp, args.merge_tol, args.pred_top)
            sims[c].extend(entropy_similarity(pm, pp, mm, mp, args.tol) for mm, mp in meas[k])
        for c, v in sims.items():
            res[name][c] = float(np.mean(v)) if v else None
    return res, raw, n_jobs


# ------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pkg'); ap.add_argument('mode', choices=['batch', 'serve', 'raw'])
    ap.add_argument('inp', nargs='?'); ap.add_argument('out', nargs='?')
    ap.add_argument('--stack', default='gpu', choices=['gpu', 'cpu', 'none'])
    ap.add_argument('--site', default='/kaggle/tmp/fwd_site')
    ap.add_argument('--device', default='cuda')
    ap.add_argument('--models', default='iceberg,glacier')
    ap.add_argument('--bs', type=int, default=64)
    ap.add_argument('--max_nodes', type=int, default=100)        # upstream elucidation default
    ap.add_argument('--threshold', type=float, default=0.0)      # upstream elucidation default
    ap.add_argument('--adducts', default=ADDUCTS_DEFAULT)
    ap.add_argument('--instrument_map', default=INSTR_MAP_DEFAULT + ',*=Unknown')
    ap.add_argument('--ce_bucket', type=float, default=5.0)
    ap.add_argument('--tol', type=float, default=0.01)
    ap.add_argument('--merge_tol', type=float, default=1e-3)
    ap.add_argument('--pred_top', type=int, default=100)         # upstream sparse_k default
    ap.add_argument('--budget', type=float, default=0.0, help='seconds; 0 = no limit (batch mode)')
    ap.add_argument('--any_rdkit', action='store_true')
    ap.add_argument('--nondeterministic', action='store_true')
    args = ap.parse_args()
    t0 = time.time()
    meta = dict(started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), args=vars(args), status='starting',
                errors=[])
    meta_path = (args.out + '.meta.json') if args.out else None
    def save_meta():
        if meta_path:
            json.dump(meta, open(meta_path, 'w'), indent=1)
    try:
        front, back = install_site(args.pkg, args.site, args.stack)
        activate(args.pkg, front, back)
        os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
        import torch, rdkit
        meta.update(torch=torch.__version__, rdkit=rdkit.__version__, python=sys.version.split()[0],
                    cuda=torch.version.cuda, cuda_available=torch.cuda.is_available())
        if rdkit.__version__ != '2025.03.6' and not args.any_rdkit:
            raise RuntimeError(f'RDKit {rdkit.__version__} loaded; fragmentation needs 2025.03.6 (use --any_rdkit to override)')
        if not args.nondeterministic:
            torch.use_deterministic_algorithms(True, warn_only=True)
            torch.backends.cudnn.benchmark = False
        torch.manual_seed(0)
        device = args.device if (args.device != 'cuda' or torch.cuda.is_available()) else 'cpu'
        meta['device'] = device
        models = Models(args.pkg, args.models.split(','), device, args.bs, args.max_nodes, args.threshold)
        meta['load_seconds'] = round(time.time() - t0, 1)
    except Exception as e:  # environment failure -> all-null output, exit 0, reason in meta
        meta.update(status='failed_setup', errors=[repr(e)[:3000]]); save_meta()
        if args.out and args.mode == 'batch':
            json.dump({}, open(args.out, 'w'))
        print(json.dumps({'fwd_runner_error': repr(e)[:500]}), flush=True)
        return 0
    allowed = set(a.strip() for a in args.adducts.split(',') if a.strip())
    instr_map = dict(kv.split('=', 1) for kv in args.instrument_map.split(',') if '=' in kv)

    if args.mode == 'serve':
        print(json.dumps({'ready': True, 'device': meta['device'], 'torch': meta['torch'], 'rdkit': meta['rdkit']}), flush=True)
        for line in sys.stdin:
            if not line.strip():
                continue
            t = time.time()
            try:
                item = json.loads(line)
                res, _, n = score_item(models, item, args, allowed, instr_map)
                print(json.dumps({'id': item.get('id'), **res, 'predictions': n, 'seconds': round(time.time() - t, 3)}), flush=True)
            except Exception as e:
                print(json.dumps({'id': None, 'error': repr(e)[:500]}), flush=True)
        return 0

    items = json.load(open(args.inp))
    out, raw_all, done, n_pred = {}, {}, 0, 0
    if args.mode == 'batch':
        json.dump(out, open(args.out, 'w'))
    for it in items:
        if args.budget and time.time() - t0 > args.budget:
            meta['errors'].append(f'budget reached after {done} items'); break
        try:
            res, raw, n = score_item(models, it, args, allowed, instr_map, keep_raw=(args.mode == 'raw'))
            out[it['id']] = res; n_pred += n; done += 1
            for (name, c, k), sp in raw.items():
                raw_all[f'{name}|{it["id"]}|{c}|{k[0]}|{k[1]}|{k[2]:g}'] = sp
        except Exception as e:
            meta['errors'].append(f'{it.get("id")}: {repr(e)[:500]}')
        if args.mode == 'batch' and done % 20 == 0:
            json.dump(out, open(args.out, 'w'))
    if args.mode == 'batch':
        json.dump(out, open(args.out, 'w'))
    else:
        import numpy as np
        np.savez_compressed(args.out, **raw_all)
        json.dump(out, open(args.out + '.scores.json', 'w'))
    meta.update(status='ok', items_done=done, items_total=len(items), predictions=n_pred,
                seconds=round(time.time() - t0, 1),
                predictions_per_second=round(n_pred / max(time.time() - t0 - meta.get('load_seconds', 0), 1e-9), 2))
    save_meta()
    return 0


if __name__ == '__main__':
    sys.exit(main())
