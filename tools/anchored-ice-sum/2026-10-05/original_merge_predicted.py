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
