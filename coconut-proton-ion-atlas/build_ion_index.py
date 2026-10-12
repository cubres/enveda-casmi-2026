"""Build one real COCONUT mass product from one exact public NumPy file.

Original code copyright 2026 prvsiyan, MIT. Derived data: CC BY-NC-SA 4.0.
The only input data are the pinned 436,389-row public mass array. Outputs must
be a new directory. No notebook, competition data, model, pickle or API access.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from draw_figures import render_figures

from ion_index import (CHANNELS, PROTON_MASS_U, SOURCE_BYTES, SOURCE_ROWS,
                       SOURCE_SHA256, _validate_vector, sha256_file)

PUBLIC_COMPANIONS = ("ion_index.py", "build_ion_index.py", "quickstart.py", "test_ion_index.py", "draw_figures.py",
                     "README.md", "DATA_DICTIONARY.md", "SOURCES.md",
                     "LICENSE-CODE-MIT.txt", "DATA_LICENSE.md", "ion-atlas.svg")


def write_json_new(path: Path, obj) -> None:
    with path.open("x", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def build(source: Path, output: Path) -> dict:
    if source.is_symlink() or not source.is_file():
        raise ValueError("source must be a regular file")
    if source.stat().st_size != SOURCE_BYTES or sha256_file(source) != SOURCE_SHA256:
        raise ValueError("only the exact public COCONUT V2 mass bytes are admitted")
    mass = np.load(source, mmap_mode="r", allow_pickle=False)
    _validate_vector(mass, expected_rows=SOURCE_ROWS)
    here = Path(__file__).resolve().parent
    for name in PUBLIC_COMPANIONS:
        if not (here / name).is_file():
            raise ValueError(f"missing reviewed public companion: {name}")
    # Refuse any existing destination. Partial outputs remain available for audit.
    output.mkdir(parents=False, exist_ok=False)
    pins = {}
    with (output / "neutral_mass_da.npy").open("xb") as dst:
        with source.open("rb") as src:
            while block := src.read(1024 * 1024):
                dst.write(block)
    if sha256_file(output / "neutral_mass_da.npy") != SOURCE_SHA256:
        raise ValueError("source changed during the read-only copy")
    mass = np.load(output / "neutral_mass_da.npy", mmap_mode="r", allow_pickle=False)
    ion_matrix = np.empty((len(CHANNELS), SOURCE_ROWS), dtype="<f8")
    for c in CHANNELS:
        ion_mz = np.asarray(c.precursor_mz(mass), dtype="<f8")
        _validate_vector(ion_mz, expected_rows=SOURCE_ROWS)
        ion_matrix[c.channel_index] = ion_mz
    with (output / "ion_mz.npy").open("xb") as f:
        np.save(f, ion_matrix, allow_pickle=False)
    for name in ["neutral_mass_da.npy", "ion_mz.npy"]:
        p = output / name
        pins[name] = dict(bytes=p.stat().st_size, sha256=sha256_file(p),
                          shape=[SOURCE_ROWS] if name == "neutral_mass_da.npy" else [len(CHANNELS), SOURCE_ROWS],
                          dtype="<f8")
    with (output / "adducts.csv").open("x", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["adduct", "array_file", "channel_index", "polarity", "signed_charge",
                         "molecule_multiplier", "signed_protons", "mass_shift_da"])
        for c in CHANNELS:
            writer.writerow([c.label, "ion_mz.npy", c.channel_index, c.polarity, c.signed_charge,
                             c.molecule_multiplier, c.signed_protons,
                             format(c.signed_protons * PROTON_MASS_U, ".17g")])
    unique, starts, counts = np.unique(mass, return_index=True, return_counts=True)
    with (output / "equal_mass_groups.csv").open("x", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["neutral_mass_da", "source_row_start",
                         "source_row_stop_exclusive", "row_count"])
        for value, start, count in zip(unique, starts, counts):
            if count > 1:
                writer.writerow([format(float(value), ".17g"), int(start),
                                 int(start + count), int(count)])
    with (output / "mass_distribution.csv").open("x", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["lower_da_inclusive", "upper_da_exclusive", "source_rows",
                         "distinct_exact_float64_mass_values"])
        for lower in range(100, 1300, 50):
            upper = lower + 50
            lo, hi = np.searchsorted(mass, [lower, upper], side="left")
            ul, uh = np.searchsorted(unique, [lower, upper], side="left")
            writer.writerow([lower, upper, int(hi - lo), int(uh - ul)])
    for name in PUBLIC_COMPANIONS:
        with (output / name).open("xb") as f:
            f.write((here / name).read_bytes())
    render_figures(output)
    generated = datetime.now(timezone.utc).isoformat()
    manifest = dict(
        schema="coconut-proton-ion-index-v1", generated_utc=generated,
        source=dict(dataset_ref="prvsiyan/coconut-casmi26-candidates",
                    dataset_id=12039473, dataset_version=2,
                    filename="coco_mass.npy", bytes=SOURCE_BYTES,
                    sha256=SOURCE_SHA256, rows=SOURCE_ROWS),
        source_row_id="zero-based position in exact source mass file; implicit array index",
        channels=[dict(label=c.label, channel_index=c.channel_index, signed_charge=c.signed_charge,
                       molecule_multiplier=c.molecule_multiplier,
                       signed_protons=c.signed_protons) for c in CHANNELS],
        proton_mass_u=PROTON_MASS_U,
        proton_mass_source="NIST CODATA 2022: proton mass in u",
        formula="precursor_mz = (molecule_multiplier * neutral_mass_da + signed_protons * proton_mass_u) / abs(signed_charge)",
        files=pins,
        measured_source_mass=dict(finite_positive=True, nondecreasing=True,
            minimum_da=float(mass[0]), maximum_da=float(mass[-1]),
            distinct_exact_float64_mass_values=len(unique),
            additional_rows_at_duplicate_exact_masses=int(SOURCE_ROWS - len(unique)),
            maximum_exact_mass_multiplicity=int(counts.max()),
            repeated_exact_mass_groups=int(np.count_nonzero(counts > 1))),
        evidence_limits=dict(molecular_keys_included=False, structures_included=False,
            metadata_alignment_established=False, observed_ions=False,
            competition_query_coverage_measured=False, training_overlap_measured=False,
            ms2_model_quality_measured=False, official_score=None),
        licenses=dict(derived_numerical_data="CC BY-NC-SA 4.0", original_code="MIT"),
    )
    write_json_new(output / "MANIFEST.json", manifest)
    metadata = dict(
        title="COCONUT Proton Ion Atlas: 436k Mass Index",
        id="prvsiyan/coconut-proton-ion-mass-index",
        subtitle="Eight charge and dimer channels with exact source-row alignment",
        description=(here / "README.md").read_text(encoding="utf-8"),
        licenses=[dict(name="CC-BY-NC-SA-4.0")],
        keywords=["chemistry", "tabular"],
        resources=[
            dict(path="neutral_mass_da.npy", description="Exact public COCONUT V2 neutral mass source: 436389 float64 rows; position is the source-row ID."),
            dict(path="ion_mz.npy", description="8x436389 theoretical precursor m/z matrix, float64, channel-major; all columns preserve source position."),
            dict(path="adducts.csv", description="Eight explicit signed proton, charge and homodimer channel definitions; no observed ion assignments."),
            dict(path="equal_mass_groups.csv", description="Contiguous source-row runs with exactly equal float64 neutral masses; not molecular equivalence."),
            dict(path="mass_distribution.csv", description="Measured source-row and distinct numerical mass counts in 50-Da bins; not query coverage."),
            dict(path="MANIFEST.json", description="Exact source pin, channel definitions, payload hashes, measured mass summaries and evidence limits."),
        ],
    )
    write_json_new(output / "dataset-metadata.json", metadata)
    # Creation metadata is consumed by Kaggle and is not a downloadable blob.
    # Bind it privately for publication; the public inventory covers downloadable files.
    files = {}
    for p in sorted(output.iterdir()):
        if p.is_file() and p.name != "dataset-metadata.json":
            files[p.name] = dict(bytes=p.stat().st_size, sha256=sha256_file(p))
    write_json_new(output / "RELEASE_FILES.json", dict(schema="release-file-hashes-v1", files=files,
        creation_metadata_scope="dataset-metadata.json is private publication configuration; it is not a downloadable payload file"))
    return dict(status="PASS_REAL_MASS_DERIVATION", rows=SOURCE_ROWS,
                ion_channels=len(CHANNELS), source_sha256=SOURCE_SHA256,
                molecular_identity_claim=False, official_score=None,
                generated_utc=generated, manifest_sha256=sha256_file(output / "MANIFEST.json"),
                release_files_sha256=sha256_file(output / "RELEASE_FILES.json"))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-mass", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    result = build(args.source_mass, args.output)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
