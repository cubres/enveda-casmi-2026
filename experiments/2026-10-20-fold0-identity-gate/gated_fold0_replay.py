#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evaluate a top-identity-preserving fold-safe FPNet blend on the public panel.

This reselects between cached per-query outputs only; it performs no inference,
training, network access, or raw-data redistribution. Panel results are a
public development proxy, not a competition score.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

WEIGHT = 1.0 / 3.0
BASE_WEIGHT = 0.0
SEED = 20261019
BOOTSTRAPS = 20_000
CANARY_N = 64


def stable_ids(ids, tag):
    return sorted(ids, key=lambda x: hashlib.sha256((tag + str(x)).encode()).digest())


def metric_record(mrr, top1):
    return {"mrr25": float(np.mean(mrr)), "top1": float(np.mean(top1))}


def summarize(per_query: Path, panel_path: Path):
    panel = pd.read_parquet(panel_path)
    ids = panel["molecule"].astype(str).tolist()
    if len(ids) != 250 or len(set(ids)) != 250:
        raise ValueError("Expected the exact 250-row public panel with unique molecule IDs")
    d = pd.read_csv(per_query)
    d["weight"] = pd.to_numeric(d["weight"], errors="raise")
    d = d[(d["mode"] == "fp_only") & d["weight"].isin([BASE_WEIGHT, WEIGHT])].copy()
    keycols = ["molecule", "mode", "weight"]
    if d.duplicated(keycols).any():
        raise ValueError("Duplicate per-query arm")
    base = d[d["weight"] == BASE_WEIGHT].set_index("molecule").reindex(ids)
    alt = d[np.isclose(d["weight"], WEIGHT)].set_index("molecule").reindex(ids)
    missing_base = int(base["mrr"].isna().sum())
    missing_alt = int(alt["mrr"].isna().sum())
    base_mrr = base["mrr"].fillna(0).to_numpy(float)
    alt_mrr = alt["mrr"].fillna(0).to_numpy(float)
    base_top1 = base["top1"].fillna(0).astype(float).to_numpy()
    alt_top1 = alt["top1"].fillna(0).astype(float).to_numpy()
    base_id = base["top_identity"].fillna("").astype(str).to_numpy()
    alt_id = alt["top_identity"].fillna("").astype(str).to_numpy()
    preserve = base_id == alt_id
    gated_mrr = np.where(preserve, alt_mrr, base_mrr)
    gated_top1 = np.where(preserve, alt_top1, base_top1)

    canary_ids = stable_ids(ids, "casmi-top-identity-gate-canary-v1|")[:CANARY_N]
    ix = pd.Index(canary_ids)
    canary = {
        "n": CANARY_N,
        "gate_accepts": int(preserve[[ids.index(x) for x in canary_ids]].sum()),
        "baseline": metric_record(base.loc[ix, "mrr"].fillna(0).to_numpy(float), base.loc[ix, "top1"].fillna(0).astype(float).to_numpy()),
        "static_one_third": metric_record(alt.loc[ix, "mrr"].fillna(0).to_numpy(float), alt.loc[ix, "top1"].fillna(0).astype(float).to_numpy()),
        "gated_one_third": metric_record(np.where(preserve[[ids.index(x) for x in canary_ids]], alt.loc[ix, "mrr"].fillna(0).to_numpy(float), base.loc[ix, "mrr"].fillna(0).to_numpy(float)), np.where(preserve[[ids.index(x) for x in canary_ids]], alt.loc[ix, "top1"].fillna(0).astype(float).to_numpy(), base.loc[ix, "top1"].fillna(0).astype(float).to_numpy())),
    }
    canary["gated_delta_mrr"] = canary["gated_one_third"]["mrr25"] - canary["baseline"]["mrr25"]
    canary["gated_delta_top1"] = canary["gated_one_third"]["top1"] - canary["baseline"]["top1"]

    delta = gated_mrr - base_mrr
    dtop = gated_top1 - base_top1
    rng = np.random.default_rng(SEED)
    boot = rng.integers(0, len(ids), size=(BOOTSTRAPS, len(ids)))
    report = {
        "implementation": {
            "file": "gated_fold0_replay.py",
            "license": "Apache-2.0",
            "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "source": {
            "dataset": "dmitriigluzdov/casmi26-natural-product-panel-benchmark",
            "dataset_id": 12288074,
            "dataset_version": 7,
            "last_updated_utc": "2026-10-20T15:30:47.943Z",
            "license": "Other (specified in description); competition-derived data and third-party annotations retain source terms",
            "dataset_url": "https://www.kaggle.com/datasets/dmitriigluzdov/casmi26-natural-product-panel-benchmark",
            "score_source": "public panel cached predictions; not an official competition score",
        },
        "method": "At inference, accept the fold0-weight=1/3 list only if its top metric identity equals the fold0-weight=0 top identity; otherwise retain the complete baseline list.",
        "gate_feature": "Exact predicted top metric identity from each list; no labels used by the gate.",
        "canary": canary,
        "full_panel": {
            "n": len(ids),
            "missing_baseline_rows_padded_zero": missing_base,
            "missing_candidate_rows_padded_zero": missing_alt,
            "gate_accepts": int(preserve.sum()),
            "baseline": metric_record(base_mrr, base_top1),
            "static_one_third": metric_record(alt_mrr, alt_top1),
            "gated_one_third": metric_record(gated_mrr, gated_top1),
            "gated_delta_mrr25": float(delta.mean()),
            "gated_delta_mrr25_paired_bootstrap_95ci": [float(x) for x in np.quantile(delta[boot].mean(axis=1), [0.025, 0.975])],
            "gated_delta_top1": float(dtop.mean()),
            "gated_delta_top1_paired_bootstrap_95ci": [float(x) for x in np.quantile(dtop[boot].mean(axis=1), [0.025, 0.975])],
            "identity_changes_static_blend": int((~preserve).sum()),
        },
        "limitations": [
            "Uses cached public panel predictions; no model inference or training was run.",
            "The 250-molecule public development panel does not establish hidden-test or leaderboard performance.",
            "The gate is evaluated once on the same public panel and needs a separate identity-disjoint inference replay before notebook integration.",
        ],
        "inputs": {
            "per_query_file": per_query.name,
            "per_query_sha256": hashlib.sha256(per_query.read_bytes()).hexdigest(),
            "panel_file": panel_path.name,
            "panel_sha256": hashlib.sha256(panel_path.read_bytes()).hexdigest(),
        },
        "bootstrap": {"seed": SEED, "replicates": BOOTSTRAPS, "unit": "molecule", "interval": "paired percentile 95%"},
    }
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--per-query", type=Path, required=True)
    p.add_argument("--panel", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = summarize(a.per_query, a.panel)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"canary": result["canary"], "full_panel": result["full_panel"]}, indent=2))
