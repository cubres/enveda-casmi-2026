#!/usr/bin/env python3
"""Aggregate official CASMI training coverage by scorer-canonical identity.

Reads only train.parquet. It recomputes the competition's tautomer-canonical
InChIKey14 from each unique normalized_smiles, groups adduct and collision
energy coverage, and emits aggregate counts only. It never reads test data,
predictions, submissions, spectra, or candidate structures.

Source code: Apache-2.0. Derived counts remain subject to the competition
training data's CC BY-NC 4.0 terms.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Iterable

import pyarrow.parquet as pq
from rdkit import Chem, rdBase
from rdkit.Chem.MolStandardize import rdMolStandardize


EXPECTED_TRAIN_SHA256 = "9423f90ec08b941a9646b535bf0606183e86ff0c5a297978f5a70693d41bcd98"
REQUIRED_COLUMNS = (
    "inchikey14",
    "normalized_smiles",
    "adduct",
    "collision_energy_orig",
    "collision_energy_orig_units",
    "ingest_lib",
)
PROXY_ADDUCTS = {
    "[M+NH4]+": "ammonium",
    "[M+H-H2O]+": "dehydrated_protonated",
    "[M-H2O+H]+": "dehydrated_protonated",
}
_SCORER = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def energy_signature(value: Any, units: Any) -> tuple[str, str]:
    if value is None:
        energy = ""
    else:
        pieces = []
        for token in str(value).split(","):
            token = token.strip()
            if not token or token.lower() in {"none", "nan", "unknown"}:
                continue
            try:
                pieces.append(f"{float(token):g}")
            except ValueError:
                pieces.append(token)
        energy = ",".join(pieces)
    unit = "unknown" if units is None else str(units).strip().lower()
    return energy, unit


def _init_worker() -> None:
    global _SCORER
    _SCORER = rdMolStandardize.TautomerEnumerator()


def _score_smiles(smiles: str) -> tuple[str, str | None]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return smiles, None
    mol = _SCORER.Canonicalize(mol)
    key = Chem.MolToInchiKey(mol)
    return smiles, key[:14] if key and len(key) >= 14 else None


def _coverage_counts(
    molecule_adducts: dict[str, set[str]],
    proxy_energy_configs: dict[str, dict[str, set[tuple[str, str]]]],
) -> tuple[dict[str, int], dict[str, int]]:
    direct = missing = any_proxy = ammonium = dehydrated = both = multi_energy = 0
    multi_energy_by_proxy: Counter[str] = Counter()
    for identity, adducts in molecule_adducts.items():
        if "[M+H]+" in adducts:
            direct += 1
            continue
        missing += 1
        proxies = proxy_energy_configs.get(identity, {})
        types = {name for name, energies in proxies.items() if energies}
        any_proxy += bool(types)
        ammonium += "ammonium" in types
        dehydrated += "dehydrated_protonated" in types
        both += len(types) >= 2
        had_multi = False
        for name in types:
            if len(proxies[name]) >= 2:
                multi_energy_by_proxy[name] += 1
                had_multi = True
        multi_energy += had_multi
    result = {
        "structures_with_direct_[M+H]+": direct,
        "structures_without_direct_[M+H]+": missing,
        "without_[M+H]+_with_any_proxy": any_proxy,
        "without_[M+H]+_with_[M+NH4]+": ammonium,
        "without_[M+H]+_with_dehydrated_protonated_proxy": dehydrated,
        "without_[M+H]+_with_both_proxy_types": both,
        "without_[M+H]+_with_at_least_two_distinct_proxy_CE_signatures": multi_energy,
    }
    return result, dict(sorted(multi_energy_by_proxy.items()))


def audit(train: Path, workers: int, max_rows: int | None) -> dict[str, Any]:
    started = time.monotonic()
    observed_sha = sha256_file(train)
    if observed_sha != EXPECTED_TRAIN_SHA256:
        raise ValueError(f"Training file SHA-256 mismatch: {observed_sha}")
    parquet = pq.ParquetFile(train)
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(parquet.schema_arrow.names))
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    rows_read = 0
    adduct_row_counts: Counter[str] = Counter()
    energy_row_counts: Counter[str] = Counter()
    library_row_counts: Counter[str] = Counter()
    raw_adducts: dict[str, set[str]] = defaultdict(set)
    raw_proxy_energies: dict[str, dict[str, set[tuple[str, str]]]] = defaultdict(
        lambda: defaultdict(set)
    )
    smile_adducts: dict[str, set[str]] = defaultdict(set)
    smile_proxy_energies: dict[str, dict[str, set[tuple[str, str]]]] = defaultdict(
        lambda: defaultdict(set)
    )

    for batch in parquet.iter_batches(batch_size=65_536, columns=list(REQUIRED_COLUMNS)):
        if max_rows is not None:
            remaining = max_rows - rows_read
            if remaining <= 0:
                break
            batch = batch.slice(0, remaining)
        columns = {name: batch.column(name).to_pylist() for name in REQUIRED_COLUMNS}
        for raw_key, smiles, adduct, energy, unit, library in zip(
            columns["inchikey14"],
            columns["normalized_smiles"],
            columns["adduct"],
            columns["collision_energy_orig"],
            columns["collision_energy_orig_units"],
            columns["ingest_lib"],
        ):
            rows_read += 1
            adduct_text = "" if adduct is None else str(adduct).strip()
            adduct_row_counts[adduct_text] += 1
            signature = energy_signature(energy, unit)
            energy_row_counts[f"{signature[0]} {signature[1]}".strip()] += 1
            library_row_counts["" if library is None else str(library)] += 1
            if raw_key:
                raw_identity = str(raw_key)[:14]
                raw_adducts[raw_identity].add(adduct_text)
                proxy = PROXY_ADDUCTS.get(adduct_text)
                if proxy and signature[0]:
                    raw_proxy_energies[raw_identity][proxy].add(signature)
            if smiles:
                smile = str(smiles)
                smile_adducts[smile].add(adduct_text)
                proxy = PROXY_ADDUCTS.get(adduct_text)
                if proxy and signature[0]:
                    smile_proxy_energies[smile][proxy].add(signature)
        if max_rows is not None and rows_read >= max_rows:
            break

    scorer_adducts: dict[str, set[str]] = defaultdict(set)
    scorer_proxy_energies: dict[str, dict[str, set[tuple[str, str]]]] = defaultdict(
        lambda: defaultdict(set)
    )
    unique_smiles = list(smile_adducts)
    invalid_smiles = 0
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker) as pool:
        for smile, identity in pool.map(_score_smiles, unique_smiles, chunksize=256):
            if identity is None:
                invalid_smiles += 1
                continue
            scorer_adducts[identity].update(smile_adducts[smile])
            for proxy_type, signatures in smile_proxy_energies.get(smile, {}).items():
                scorer_proxy_energies[identity][proxy_type].update(signatures)

    raw_counts, raw_multi_energy = _coverage_counts(raw_adducts, raw_proxy_energies)
    scorer_counts, scorer_multi_energy = _coverage_counts(scorer_adducts, scorer_proxy_energies)
    return {
        "status": "COMPLETE_CANARY" if max_rows is not None else "COMPLETE",
        "scope": "aggregate training coverage only; no model score or test-data access",
        "training_file": train.name,
        "training_sha256": observed_sha,
        "training_license": "CC BY-NC 4.0; derived aggregates retain source terms",
        "rows_read": rows_read,
        "all_training_rows": parquet.metadata.num_rows,
        "stored_inchikey14_unique_structures": len(raw_adducts),
        "unique_normalized_smiles": len(unique_smiles),
        "scorer_unique_structures": len(scorer_adducts),
        "identity_basis": "RDKit TautomerEnumerator canonicalization then InChIKey14",
        "rdkit_version": rdBase.rdkitVersion,
        "workers": workers,
        "invalid_unique_smiles": invalid_smiles,
        "adduct_row_counts": dict(sorted(adduct_row_counts.items())),
        "collision_energy_signature_row_counts_top_20": dict(energy_row_counts.most_common(20)),
        "ingest_library_row_counts": dict(sorted(library_row_counts.items())),
        "stored_identity_coverage": raw_counts,
        "stored_identity_multi_energy_by_proxy": raw_multi_energy,
        "scorer_identity_coverage": scorer_counts,
        "scorer_identity_multi_energy_by_proxy": scorer_multi_energy,
        "limitations": [
            "A comma-separated collision-energy label is one acquisition setting, not several spectra.",
            "Training coverage does not establish hidden-test coverage or model-quality improvement.",
            "Only aggregate counts are emitted; no spectra, structures, labels, or predictions are emitted.",
        ],
        "runtime_seconds": round(time.monotonic() - started, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--max-rows", type=int)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    result = audit(args.train, args.workers, args.max_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = args.output.with_suffix(args.output.suffix + ".tmp")
    temp_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temp_path.replace(args.output)
    print(json.dumps({key: result[key] for key in ("status", "rows_read", "unique_normalized_smiles", "scorer_unique_structures", "runtime_seconds", "training_sha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
