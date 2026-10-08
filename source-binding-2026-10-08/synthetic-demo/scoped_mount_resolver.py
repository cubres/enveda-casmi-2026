"""Resolve one byte-pinned mounted file in two explicitly accepted layouts.

Only ``datasets/<owner>/<slug>/<relative_filename>`` and
``<slug>/<relative_filename>`` below the supplied input root are candidates.
There is no recursive search or filename-only fallback. Symlink aliases of the
same canonical path are accepted; two different canonical paths are ambiguous
even when their bytes match. Receipts contain relative paths and aggregate
metadata, never file contents, absolute OS paths, or OS error text.

The module performs no networking, model loading, deserialization, or mutation.
Dataset-version and lineage assertions belong to the caller's pinned manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any


_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class ResolvedMappedFile:
    path: Path
    receipt: dict[str, Any]


class MappedFileResolutionError(RuntimeError):
    """A fail-closed resolution error with a sanitized, JSON-safe receipt."""

    def __init__(self, receipt: dict[str, Any]):
        self.receipt = receipt
        super().__init__(json.dumps(receipt, sort_keys=True, separators=(",", ":")))


def _safe_component(value: Any) -> bool:
    return isinstance(value, str) and bool(_COMPONENT.fullmatch(value))


def _safe_relative_file(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return False
    parts = value.split("/")
    return all(part not in ("", ".", "..") for part in parts) and not Path(value).is_absolute()


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _fail(receipt: dict[str, Any], reason: str) -> None:
    receipt["status"] = "FAIL"
    receipt["reason"] = reason
    raise MappedFileResolutionError(receipt)


def _refresh_counts(receipt: dict[str, Any], unique_paths: int = 0) -> None:
    candidates = receipt["candidates"]
    resolved = sum(candidate["state"] == "resolved" for candidate in candidates)
    missing = sum(candidate["state"] in ("missing_root", "missing_file") for candidate in candidates)
    receipt["counts"] = {
        "explicit_candidates": len(candidates),
        "resolved_candidates": resolved,
        "missing_candidates": missing,
        "rejected_candidates": len(candidates) - resolved - missing,
        "unique_canonical_paths": unique_paths,
        "canonical_aliases": max(0, resolved - unique_paths),
    }
    receipt["resolved_source_classes"] = [
        candidate["source_class"] for candidate in candidates if candidate["state"] == "resolved"
    ]


def resolve_mapped_file(
    input_root: str | os.PathLike[str],
    owner: str,
    slug: str,
    relative_filename: str,
    expected_size: int,
    expected_sha256: str,
) -> ResolvedMappedFile:
    """Return a canonical path and receipt only after exact scoped byte checks.

    Missing candidates may be ignored if the other accepted layout resolves.
    Any malformed, inaccessible, escaping, or ambiguous candidate is fatal.
    A root-level alias may target another location inside ``input_root``; a
    file-level alias must stay inside that resolved dataset root. This permits
    legacy/namespaced mount aliases without accepting a cross-dataset file.
    """
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "resolver": "SCOPED_MOUNT_RESOLVER_V5",
        "status": "CHECKING",
        "candidates": [],
        "counts": {
            "explicit_candidates": 0,
            "resolved_candidates": 0,
            "missing_candidates": 0,
            "rejected_candidates": 0,
            "unique_canonical_paths": 0,
            "canonical_aliases": 0,
        },
        "resolved_source_classes": [],
    }
    if not (
        _safe_component(owner)
        and _safe_component(slug)
        and _safe_relative_file(relative_filename)
        and type(expected_size) is int
        and expected_size >= 0
        and isinstance(expected_sha256, str)
        and bool(_SHA256.fullmatch(expected_sha256))
        and isinstance(input_root, (str, os.PathLike))
    ):
        _fail(receipt, "INPUT_CONTRACT_INVALID")
    receipt["request"] = {
        "owner": owner,
        "slug": slug,
        "relative_filename": relative_filename,
        "expected_size": expected_size,
        "expected_sha256": expected_sha256,
    }
    try:
        lexical_root = Path(input_root)
        canonical_root = lexical_root.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        _fail(receipt, "INPUT_ROOT_UNRESOLVABLE")
    if not canonical_root.is_dir():
        _fail(receipt, "INPUT_ROOT_NOT_DIRECTORY")

    layouts = (
        ("explicit_owner_slug", Path("datasets") / owner / slug),
        ("legacy_slug", Path(slug)),
    )
    canonical_candidates: dict[Path, list[dict[str, Any]]] = {}
    for source_class, scoped_root in layouts:
        candidate = {
            "source_class": source_class,
            "scoped_relative_path": (scoped_root / relative_filename).as_posix(),
            "state": "checking",
        }
        receipt["candidates"].append(candidate)
        declared_root = lexical_root / scoped_root
        try:
            declared_root.lstat()
        except FileNotFoundError:
            candidate["state"] = "missing_root"
            continue
        except OSError:
            candidate["state"] = "root_inaccessible"
            continue
        try:
            resolved_dataset_root = declared_root.resolve(strict=True)
            if not _within(resolved_dataset_root, canonical_root):
                candidate["state"] = "root_escapes_input"
                continue
            if not resolved_dataset_root.is_dir():
                candidate["state"] = "root_not_directory"
                continue
        except (OSError, RuntimeError):
            candidate["state"] = "root_unresolvable"
            continue
        declared_file = declared_root / relative_filename
        try:
            declared_file.lstat()
        except FileNotFoundError:
            candidate["state"] = "missing_file"
            continue
        except OSError:
            candidate["state"] = "file_inaccessible"
            continue
        try:
            canonical_file = declared_file.resolve(strict=True)
            if not _within(canonical_file, resolved_dataset_root):
                candidate["state"] = "file_escapes_dataset"
                continue
            if not canonical_file.is_file():
                candidate["state"] = "file_not_regular"
                continue
        except (OSError, RuntimeError):
            candidate["state"] = "file_unresolvable"
            continue
        candidate["state"] = "resolved"
        candidate["canonical_source_index"] = list(canonical_candidates).index(canonical_file) if canonical_file in canonical_candidates else len(canonical_candidates)
        canonical_candidates.setdefault(canonical_file, []).append(candidate)

    _refresh_counts(receipt, len(canonical_candidates))
    if receipt["counts"]["rejected_candidates"]:
        _fail(receipt, "SCOPED_CANDIDATE_REJECTED")
    if not canonical_candidates:
        _fail(receipt, "MAPPED_FILE_MISSING")
    if len(canonical_candidates) != 1:
        _fail(receipt, "DISTINCT_CANONICAL_SOURCES")
    canonical_file = next(iter(canonical_candidates))
    receipt["selected_scoped_relative_paths"] = [candidate["scoped_relative_path"] for candidate in canonical_candidates[canonical_file]]

    # Open the already canonical path without following a replacement symlink.
    # Mounted inputs are stable, but fstat before/after catches file drift while
    # hashing; private device/inode/time values never enter the receipt.
    descriptor: int | None = None
    try:
        descriptor = os.open(canonical_file, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None  # The file object owns and closes the descriptor.
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                _fail(receipt, "SELECTED_SOURCE_NOT_REGULAR")
            receipt["observed_size"] = before.st_size
            if before.st_size != expected_size:
                _fail(receipt, "SIZE_MISMATCH")
            digest = hashlib.sha256()
            bytes_read = 0
            while chunk := stream.read(_CHUNK_BYTES):
                bytes_read += len(chunk)
                if bytes_read > expected_size:
                    _fail(receipt, "SOURCE_CHANGED_DURING_HASH")
                digest.update(chunk)
            after = os.fstat(stream.fileno())
            fingerprint = lambda info: (
                info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns
            )
            if bytes_read != expected_size or fingerprint(before) != fingerprint(after):
                _fail(receipt, "SOURCE_CHANGED_DURING_HASH")
            observed_sha256 = digest.hexdigest()
            receipt["observed_sha256"] = observed_sha256
            if observed_sha256 != expected_sha256:
                _fail(receipt, "SHA256_MISMATCH")
    except OSError:
        _fail(receipt, "SELECTED_SOURCE_UNREADABLE")
    finally:
        if descriptor is not None:
            os.close(descriptor)

    receipt["status"] = "PASS"
    receipt["reason"] = "ONE_CANONICAL_SCOPED_SOURCE_MATCHES_EXACT_BYTES"
    return ResolvedMappedFile(canonical_file, receipt)
