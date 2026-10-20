#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 cubres
"""Read-only source/input-reference audit for one public CASMI notebook version.

This checks local Kaggle pull bytes against a fixed source binding. It never imports
or executes notebook code, accesses the network, reads model/data payloads, or
claims that attached dataset versions or licenses are pinned.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Optional

BINDING = Path(__file__).with_name("source_binding.json")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def cells_count(path: Path) -> int:
    nb = json.loads(path.read_text(encoding="utf-8"))
    cells = nb.get("cells")
    if not isinstance(cells, list):
        raise ValueError("notebook has no cells array")
    return len(cells)

def audit(source_dir: Path, readme_dir: Optional[Path], require_readmes: bool) -> dict:
    binding = json.loads(BINDING.read_text(encoding="utf-8"))
    expected = binding["notebook"]
    problems: list[str] = []
    meta_path = source_dir / "kernel-metadata.json"
    code_path = source_dir / expected["code_file"]
    if not meta_path.is_file():
        return {"status": "FAIL", "problems": [f"missing {meta_path.name}"]}
    if not code_path.is_file():
        return {"status": "FAIL", "problems": [f"missing {code_path.name}"]}
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    identity = {k: meta.get(k) for k in ("id", "id_no", "title", "code_file")}
    wanted_identity = {"id": expected["ref"], "id_no": expected["id_no"], "title": expected["title"], "code_file": expected["code_file"]}
    if identity != wanted_identity:
        problems.append("notebook identity differs from the fixed public source binding")
    got_datasets = meta.get("dataset_sources")
    if got_datasets != binding["dataset_sources"]:
        problems.append("dataset source refs differ from the fixed public source binding")
    if meta.get("competition_sources") != binding["competition_sources"]:
        problems.append("competition source refs differ from the fixed public source binding")
    actual_bytes = code_path.stat().st_size
    actual_sha = sha256(code_path)
    if actual_bytes != expected["source_bytes"]:
        problems.append(f"notebook byte count differs: {actual_bytes} != {expected['source_bytes']}")
    if actual_sha != expected["source_sha256"]:
        problems.append("notebook source SHA256 differs from the fixed public source binding")
    try:
        actual_cells = cells_count(code_path)
    except Exception as exc:
        actual_cells = None
        problems.append(f"cannot parse notebook JSON: {type(exc).__name__}")
    if actual_cells != expected["cell_count"]:
        problems.append(f"cell count differs: {actual_cells} != {expected['cell_count']}")
    readmes = []
    for pin in binding["supporting_readme_pins"]:
        item = {"file": pin["file"], "dataset_ref": pin["dataset_ref"], "version": pin["version"], "status": "NOT_CHECKED"}
        if readme_dir is not None:
            path = readme_dir / pin["file"]
            if not path.is_file():
                item["status"] = "MISSING"
                if require_readmes:
                    problems.append(f"missing supporting README {pin['file']}")
            else:
                size, digest = path.stat().st_size, sha256(path)
                item.update(bytes=size, sha256=digest)
                item["status"] = "PASS" if size == pin["bytes"] and digest == pin["sha256"] else "MISMATCH"
                if item["status"] == "MISMATCH":
                    problems.append(f"supporting README pin mismatch: {pin['file']}")
        elif require_readmes:
            problems.append("--require-readmes needs --readme-dir")
        readmes.append(item)
    return {
        "status": "PASS_SOURCE_BINDING_WITH_UNRESOLVED_INPUT_VERSIONS" if not problems else "FAIL",
        "notebook_identity": identity,
        "notebook_source_bytes": actual_bytes,
        "notebook_source_sha256": actual_sha,
        "cell_count": actual_cells,
        "dataset_source_count": len(got_datasets) if isinstance(got_datasets, list) else None,
        "dataset_version_ids_bound": False,
        "license_metadata_checked": False,
        "supporting_readmes": readmes,
        "public_score_observation": binding["notebook"]["observed_public_score"],
        "public_score_verified_by_this_script": False,
        "problems": problems,
    }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True, help="directory from the exact public Kaggle source pull")
    p.add_argument("--readme-dir", type=Path, help="optional directory with the three retained, version-pinned README captures")
    p.add_argument("--require-readmes", action="store_true", help="fail if any of the three supporting README captures is missing or mismatched")
    args = p.parse_args()
    result = audit(args.source_dir, args.readme_dir, args.require_readmes)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("PASS") else 1

if __name__ == "__main__":
    raise SystemExit(main())
