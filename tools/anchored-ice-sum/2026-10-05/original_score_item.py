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
