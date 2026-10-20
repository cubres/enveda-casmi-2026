#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replay the fixed V14 PubChem-synonym prior on cached public CASMI panel rows.

This CPU-only audit re-ranks cached candidate scores. It performs no model
inference or fitting, and it writes aggregate metrics only. Its result is a
development-panel comparison, not a hidden-test or leaderboard score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAMBDA = 0.15
POP_UNION = 200
FP_SHORTLIST = 5000
SYNONYM_WEIGHT = 0.5
FOLD0_WEIGHT = 0.5
CANARY_N = 64
BOOTSTRAPS = 20_000
BOOTSTRAP_SEED = 20261020
CANARY_TAG = "casmi-v14-synonym-prior-fixed-canary-v1|"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canary_ids(ids: list[str]) -> list[str]:
    return sorted(ids, key=lambda x: hashlib.sha256((CANARY_TAG + x).encode()).digest())[:CANARY_N]


def clean_key(value: object, fallback: object) -> str:
    for item in (value, fallback):
        if pd.notna(item):
            result = str(item).strip()
            if result and result.lower() != "nan":
                return result
    return ""


def load_rows(args: argparse.Namespace) -> tuple[pd.DataFrame, list[str], dict[str, str]]:
    panel = pd.read_parquet(args.panel, columns=["molecule"])
    ids = panel["molecule"].astype(str).tolist()
    if len(ids) != 250 or len(set(ids)) != 250:
        raise ValueError("Expected the exact 250-identity public panel")

    scores = pd.read_parquet(
        args.scores,
        columns=["molecule", "tier_row", "candidate_row", "ab_full", "fold0_full", "ab_partial", "fold0_partial"],
    )
    signals = pd.read_parquet(args.signals, columns=["molecule", "tier_row", "candidate_row", "prior_v10"])
    signals = signals.rename(columns={"candidate_row": "signal_candidate_row"})
    candidates = pd.read_parquet(
        args.candidates,
        columns=["molecule", "tier_row", "connectivity", "scorer_key", "is_truth", "in_pool"],
    )

    keys = ["molecule", "tier_row"]
    for name, d in (("scores", scores), ("signals", signals), ("candidates", candidates)):
        if d.duplicated(keys).any():
            raise ValueError(f"Duplicate molecule/tier-row key in {name}")
    d = scores.merge(signals, on=keys, how="outer", validate="one_to_one", indicator="signal_join")
    if not d["signal_join"].eq("both").all():
        raise ValueError("Cached score and prior rows do not align one-to-one")
    if not np.array_equal(d["candidate_row"].to_numpy(), d["signal_candidate_row"].to_numpy()):
        raise ValueError("candidate_row order differs between score and prior files")
    d = d.drop(columns=["signal_join", "signal_candidate_row"])
    d = d.merge(candidates, on=keys, how="outer", validate="one_to_one", indicator="candidate_join")
    if not d["candidate_join"].eq("both").all():
        raise ValueError("Cached model rows do not align one-to-one with candidate identities")
    d = d.drop(columns="candidate_join")
    if not set(d["molecule"].astype(str)).issubset(set(ids)):
        raise ValueError("Found candidate rows outside the pinned public panel")

    synonyms = np.load(args.synonyms, mmap_mode="r")
    if synonyms.shape != (105_875_489,):
        raise ValueError(f"Unexpected PubChem synonym array shape: {synonyms.shape}")
    tier = d["tier_row"].to_numpy(dtype=np.int64)
    if tier.min(initial=0) < 0 or tier.max(initial=0) >= len(synonyms):
        raise ValueError("Panel tier_row falls outside the pinned synonym array")
    d["syn_log1p"] = np.asarray(synonyms[tier], dtype=np.float32)
    if not np.isfinite(d["syn_log1p"].to_numpy()).all() or (d["syn_log1p"] < 0).any():
        raise ValueError("Synonym prior contains invalid values for panel candidates")
    d["key"] = [clean_key(a, b) for a, b in zip(d["scorer_key"], d["connectivity"])]
    d["is_truth"] = d["is_truth"].fillna(False).astype(bool)
    d["in_pool"] = d["in_pool"].fillna(False).astype(bool)
    hashes = {p.name: sha256(p) for p in (args.panel, args.scores, args.signals, args.candidates, args.synonyms)}
    return d, ids, hashes


def rank_query(g: pd.DataFrame, synonym_weight: float) -> tuple[float, float, int, int]:
    if g.empty:
        return 0.0, 0.0, 0, 0
    partial = g["ab_partial"].to_numpy(np.float64) + FOLD0_WEIGHT * g["fold0_partial"].to_numpy(np.float64)
    full = g["ab_full"].to_numpy(np.float64) + FOLD0_WEIGHT * g["fold0_full"].to_numpy(np.float64)
    pop = g["prior_v10"].to_numpy(np.float64) + synonym_weight * g["syn_log1p"].to_numpy(np.float64)
    valid = np.isfinite(partial) & np.isfinite(full) & np.isfinite(pop) & g["key"].ne("").to_numpy()
    base_idx = np.flatnonzero(valid)
    if not len(base_idx):
        return 0.0, 0.0, 0, 0

    # Match the published candidate-generation contract: ECFP4 top 5,000,
    # unioned with the top 200 by the complete documentation prior.
    n_fp = min(FP_SHORTLIST, len(base_idx))
    local = np.argpartition(-partial[base_idx], n_fp - 1)[:n_fp]
    selected = base_idx[local]
    n_pop = min(POP_UNION, len(base_idx))
    local_pop = np.argpartition(-pop[base_idx], n_pop - 1)[:n_pop]
    selected = np.union1d(selected, base_idx[local_pop])

    f = full[selected]
    z = (f - f.mean()) / (f.std() + 1e-9)
    order = np.argsort(-(z + LAMBDA * pop[selected]), kind="stable")
    truth_keys = set(g.loc[g["is_truth"], "key"].astype(str))
    rank = 0
    seen: set[str] = set()
    for j in order:
        i = int(selected[j])
        key = str(g.iloc[i]["key"])
        if key in seen:
            continue
        seen.add(key)
        if bool(g.iloc[i]["in_pool"]) and key not in truth_keys:
            continue
        rank += 1
        if key in truth_keys:
            return 1.0 / rank, float(rank == 1), rank, len(selected)
        if rank >= 25:
            break
    return 0.0, 0.0, 0, len(selected)


def score_ids(d: pd.DataFrame, ids: list[str], weight: float) -> dict[str, tuple[float, float, int, int]]:
    groups = {str(k): g.reset_index(drop=True) for k, g in d.groupby("molecule", sort=False)}
    return {mid: rank_query(groups.get(mid, pd.DataFrame()), weight) for mid in ids}


def summarize(vals: dict[str, tuple[float, float, int, int]], ids: list[str], ref: dict[str, float] | None = None) -> dict:
    mrr = np.array([vals[mid][0] for mid in ids], dtype=np.float64)
    top1 = np.array([vals[mid][1] for mid in ids], dtype=np.float64)
    out = {"n": len(ids), "mrr25": float(mrr.mean()), "top1": float(top1.mean()), "hit25": float((mrr > 0).mean())}
    if ref is not None:
        r = np.array([ref.get(mid, 0.0) for mid in ids], dtype=np.float64)
        delta = mrr - r
        out["max_abs_delta_vs_cached_baseline"] = float(np.abs(delta).max(initial=0.0))
        out["mean_delta_vs_cached_baseline"] = float(delta.mean())
    return out


def evaluate(args: argparse.Namespace) -> dict:
    d, ids, hashes = load_rows(args)
    chosen = ids if args.n == 250 else canary_ids(ids)
    base = score_ids(d, chosen, 0.0)
    syn = score_ids(d, chosen, SYNONYM_WEIGHT)

    cached = pd.read_csv(args.cached_per_query)
    cached = cached[(cached["mode"] == "v10_prior") & np.isclose(cached["weight"], 0.5)]
    if cached.duplicated(["molecule"]).any():
        raise ValueError("Cached baseline contains duplicate query rows")
    reference = cached.set_index("molecule")["mrr"].astype(float).to_dict()
    base_delta = np.array([base[mid][0] - reference.get(mid, 0.0) for mid in chosen])

    result = {
        "script_license": "Apache-2.0",
        "data_license_note": "This report contains aggregate metrics and input hashes only; upstream dataset contents remain subject to their source terms.",
        "source": {
            "public_notebook": "dmitriigluzdov/casmi-26-the-data-behind-spectra-to-structures",
            "public_notebook_script_version": 360413706,
            "reported_best_score": 0.456,
            "reported_best_score_version": 13,
            "notebook_source_sha256": sha256(args.notebook_source),
            "panel_dataset": "dmitriigluzdov/casmi26-natural-product-panel-benchmark",
            "panel_dataset_version": 7,
            "pubchem_dataset": "dmitriigluzdov/casmi26-pubchem-popularity-prior",
            "pubchem_dataset_version": 9,
            "pubchem_synonym_feature": "pc_lsynonyms.npy; row-aligned log(1 + PubChem synonym count)",
            "score_type": "public labelled development-panel replay, not official leaderboard score",
        },
        "method": {
            "baseline": "cached A+B plus 0.5 fold0 full/partial FPNet scores; v10 prior; 5,000 partial-score shortlist union top 200 prior; 0.15 prior coefficient; metric-identity dedupe; exclude pool identities except truth",
            "candidate": "same replay with fixed +0.5 * log1p(PubChem synonym count) added to the prior before the 5,000/200 shortlist and final ranking",
            "canary_selection": f"first {CANARY_N} IDs in lexical SHA256 order over {CANARY_TAG!r}; label-free and fixed before scoring",
            "canary_gate": "full panel allowed only if candidate MRR does not fall and top-1 does not fall on the fixed 64-query canary",
        },
        "inputs": hashes,
        "panel_candidate_rows": int(len(d)),
        "queries_with_candidate_rows": int(d["molecule"].nunique()),
        "n_queries_requested": args.n,
        "baseline_replay": summarize(base, chosen),
        "candidate_replay": summarize(syn, chosen),
        "canary_or_panel_delta": {
            "mrr25": float(np.mean([syn[m][0] - base[m][0] for m in chosen])),
            "top1": float(np.mean([syn[m][1] - base[m][1] for m in chosen])),
            "improved_queries": int(sum(syn[m][0] > base[m][0] for m in chosen)),
            "worse_queries": int(sum(syn[m][0] < base[m][0] for m in chosen)),
            "unchanged_queries": int(sum(syn[m][0] == base[m][0] for m in chosen)),
        },
        "cached_baseline_check": {
            "max_abs_per_query_delta": float(np.abs(base_delta).max(initial=0.0)),
            "mean_per_query_delta": float(base_delta.mean()),
            "reference_queries_present": int(sum(mid in reference for mid in chosen)),
        },
        "limitations": [
            "Public development panel is a labelled training-derived natural-product subset and does not establish hidden-test performance.",
            "The synonym feature and fixed weight were already reported from this panel by the public baseline author; this replay verifies transfer/alignment and does not provide an untouched scientific holdout.",
            "Cached scores are used; no spectra, model weights, fitting, or GPU inference are used.",
        ],
    }
    if args.n == 250:
        delta = np.array([syn[mid][0] - base[mid][0] for mid in chosen], dtype=np.float64)
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        idx = rng.integers(0, len(chosen), size=(BOOTSTRAPS, len(chosen)))
        result["full_panel_paired_bootstrap"] = {
            "seed": BOOTSTRAP_SEED,
            "replicates": BOOTSTRAPS,
            "unit": "molecule",
            "mrr_delta_95ci": [float(x) for x in np.quantile(delta[idx].mean(axis=1), [0.025, 0.975])],
            "top1_delta_95ci": [float(x) for x in np.quantile(np.array([syn[m][1] - base[m][1] for m in chosen])[idx].mean(axis=1), [0.025, 0.975])],
        }
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--panel", type=Path, required=True)
    p.add_argument("--scores", type=Path, required=True)
    p.add_argument("--signals", type=Path, required=True)
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--synonyms", type=Path, required=True)
    p.add_argument("--cached-per-query", type=Path, required=True)
    p.add_argument("--notebook-source", type=Path, required=True)
    p.add_argument("--n", type=int, choices=[64, 250], required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = evaluate(args)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("n_queries_requested", "baseline_replay", "candidate_replay", "canary_or_panel_delta", "cached_baseline_check")}, indent=2))


if __name__ == "__main__":
    main()
