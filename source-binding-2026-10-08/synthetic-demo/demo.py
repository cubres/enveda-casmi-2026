"""Portable synthetic source-binding demo. Standard library only.

Every fixture is retained. This script never loads a model, executes a bank
cell, queries Kaggle, or sends network requests.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MODULE_PINS = {
    "scoped_mount_resolver.py": "a4609ef7526bf112497457eeac645b62cd2a771794d0b4968d9be47abedb2ab3",
    "native_mount_bridge.py": "3405ae869d5291ae82f4eadcc9b9e68d5e62a721c7127960e7623ec169f32c18",
}
OWNER = "example-lab"
SLUG = "synthetic-assets"
FILENAME = "example.bin"
PAYLOAD = b"Neutral synthetic fixture bytes; no scientific data or models.\n"
PAYLOAD_SHA = hashlib.sha256(PAYLOAD).hexdigest()


def verified_modules():
    modules = {}
    for filename, expected in MODULE_PINS.items():
        path = HERE / filename
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError("source-binding module SHA256 mismatch: " + filename)
        name = "verified_demo_" + path.stem
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules[filename] = module
    return modules["scoped_mount_resolver.py"], modules["native_mount_bridge.py"]


def put_file(input_root, layout, payload=PAYLOAD):
    """Create only new synthetic files in an explicitly chosen layout."""
    path = input_root / layout / FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
    return path


def resolve(resolver, input_root, expected_sha=PAYLOAD_SHA):
    return resolver.resolve_mapped_file(
        input_root, OWNER, SLUG, FILENAME, len(PAYLOAD), expected_sha
    )


def public_receipt(receipt):
    """Defensive check before emitting this demo's relative-path receipts."""
    encoded = json.dumps(receipt, sort_keys=True)
    forbidden = ("/Users/", "/kaggle/working/", "zz-gpuchk", "prvsiyan", "cubres",
                 "opaque-secret", "uid-secret", "Harmless synthetic", PAYLOAD.decode().strip())
    if any(value in encoded for value in forbidden):
        raise RuntimeError("demo output privacy contract")
    return receipt


def run_demo(output_root):
    resolver, bridge = verified_modules()
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    run_name = "run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_root = output_root / run_name
    run_root.mkdir()
    namespaced = Path("datasets") / OWNER / SLUG
    scenarios = {}

    single_root = run_root / "single" / "input"
    single_root.mkdir(parents=True)
    single_path = put_file(single_root, namespaced)
    single = resolve(resolver, single_root)
    assert single.path == single_path.resolve(strict=True)
    scenarios["single_canonical"] = single.receipt

    alias_root = run_root / "alias" / "input"
    alias_root.mkdir(parents=True)
    alias_path = put_file(alias_root, namespaced)
    try:
        (alias_root / SLUG).symlink_to(
            (alias_root / namespaced).resolve(strict=True), target_is_directory=True
        )
    except (OSError, NotImplementedError):
        # Some Windows accounts cannot create symlinks without OS permission.
        # The ordinary source/hash checks still run; no workaround is attempted.
        scenarios["same_physical_alias"] = {
            "status": "SKIP_SYMLINK_UNAVAILABLE",
            "reason": "platform_symlink_capability",
        }
    else:
        alias = resolve(resolver, alias_root)
        assert alias.path == alias_path.resolve(strict=True)
        assert alias.receipt["counts"]["canonical_aliases"] == 1
        scenarios["same_physical_alias"] = alias.receipt

    duplicate_root = run_root / "distinct_duplicates" / "input"
    duplicate_root.mkdir(parents=True)
    put_file(duplicate_root, namespaced)
    put_file(duplicate_root, Path(SLUG))
    try:
        resolve(resolver, duplicate_root)
    except resolver.MappedFileResolutionError as error:
        assert error.receipt["reason"] == "DISTINCT_CANONICAL_SOURCES"
        scenarios["distinct_physical_duplicates"] = error.receipt
    else:
        raise AssertionError("distinct physical sources must be rejected")

    hash_root = run_root / "wrong_hash" / "input"
    hash_root.mkdir(parents=True)
    put_file(hash_root, namespaced)
    try:
        resolve(resolver, hash_root, expected_sha="0" * 64)
    except resolver.MappedFileResolutionError as error:
        assert error.receipt["reason"] == "SHA256_MISMATCH"
        scenarios["wrong_hash"] = error.receipt
    else:
        raise AssertionError("wrong byte pins must be rejected")

    fallback_calls = []
    def original_find(name):
        fallback_calls.append(name)
        return "original-selection:" + name
    known_find = bridge.bind_known_find(original_find, {FILENAME: single.path})
    assert known_find(FILENAME) == str(single.path)
    assert not fallback_calls
    assert known_find("unmapped.bin") == "original-selection:unmapped.bin"
    assert fallback_calls == ["unmapped.bin"]

    selector_checks = []
    for index, (old, replacement) in bridge.IO_SITES.items():
        source = "# Synthetic selector text only; never executed.\nselected = sorted(" + old + ")\n"
        transformed = bridge.transform_io_binding(index, source)
        assert transformed == source.replace(old, replacement)
        assert transformed.replace(replacement, old) == source
        ast.parse(transformed)  # Syntax inspection, never execution.
        selector_checks.append({
            "index": index,
            "exact_single_expression_change": True,
            "inverse_restores_all_source_bytes": True,
        })

    receipt = public_receipt({
        "status": "PASS_SYNTHETIC_SOURCE_BINDING_DEMO",
        "artifact_directory": run_name,
        "module_sha256": MODULE_PINS,
        "scenarios": scenarios,
        "known_find_uses_only_qualified_path": True,
        "unknown_find_preserves_original_selector": True,
        "selector_text_checks": selector_checks,
        "fixtures_retained": True,
        "synthetic_files_only": True,
        "network_calls": 0,
        "model_loads": 0,
        "bank_cell_executions": 0,
        "official_score": None,
    })
    with (run_root / "DEMO_RESULT.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="synthetic_runs",
                        help="Retained fixture directory; nothing is deleted.")
    args = parser.parse_args()
    print(json.dumps(run_demo(args.output_root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

