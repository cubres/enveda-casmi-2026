"""Original, NumPy-only candidate contracts; no chemistry data or model execution."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PROTON_MASS_DA = 1.0072764665789  # 2022 CODATA; see SOURCES.md.


class ContractError(ValueError):
    """A supplied array or declared convention does not match this contract."""


def _number(value, name, *, positive=False, nonnegative=False):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.number)):
        raise ContractError(name + " must be a real number")
    if np.iscomplexobj(value):
        raise ContractError(name + " must be real")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0) or (nonnegative and result < 0):
        raise ContractError(name + " is out of range")
    return result


@dataclass(frozen=True)
class IonSpec:
    """m/z = (molecule_count * neutral_mass + signed_shift_da) / abs(charge).

    Only proton addition/removal is predefined. Other adducts need an explicit,
    independently checked signed mass shift: no ion label is guessed.
    """

    charge: int
    signed_shift_da: float
    molecule_count: int = 1

    def __post_init__(self):
        if type(self.charge) is not int or self.charge == 0:
            raise ContractError("charge must be a nonzero Python integer")
        if type(self.molecule_count) is not int or self.molecule_count <= 0:
            raise ContractError("molecule_count must be a positive Python integer")
        _number(self.signed_shift_da, "signed_shift_da")


def protonated_ion(charge):
    """Positive charge adds protons; negative charge removes protons."""
    if type(charge) is not int or charge == 0:
        raise ContractError("charge must be a nonzero Python integer")
    return IonSpec(charge, charge * PROTON_MASS_DA)


def neutral_from_mz(mz, ion):
    if not isinstance(ion, IonSpec):
        raise ContractError("supply an explicit IonSpec")
    result = (_number(mz, "mz", positive=True) * abs(ion.charge) - ion.signed_shift_da) / ion.molecule_count
    return _number(result, "converted neutral mass", positive=True)


def mz_from_neutral(neutral_mass_da, ion):
    if not isinstance(ion, IonSpec):
        raise ContractError("supply an explicit IonSpec")
    result = (_number(neutral_mass_da, "neutral_mass_da", positive=True) * ion.molecule_count + ion.signed_shift_da) / abs(ion.charge)
    return _number(result, "converted mz", positive=True)


def validate_masses(masses):
    """Validate once before repeated O(log n) windows. Positive float64, ascending."""
    if not isinstance(masses, np.ndarray) or masses.ndim != 1 or masses.dtype != np.dtype("float64"):
        raise ContractError("masses must be a one-dimensional float64 ndarray")
    if not np.all(np.isfinite(masses)) or np.any(masses <= 0) or np.any(masses[1:] < masses[:-1]):
        raise ContractError("masses must be finite, positive and sorted ascending")
    return masses


def mass_window(masses, neutral_mass_da, ppm, *, validated=False):
    """Inclusive query-denominator interval [q-q*ppm/1e6, q+q*ppm/1e6].

    validated=True skips the O(n) scan; use only after validate_masses and keep
    the array unchanged. No guessed m/z/adduct conversion and no auto-sort.
    """
    q = _number(neutral_mass_da, "neutral_mass_da", positive=True)
    tolerance = _number(ppm, "ppm", nonnegative=True)
    if tolerance >= 1e6:
        raise ContractError("ppm must be smaller than one million")
    if not validated:
        validate_masses(masses)
    width = q * (tolerance / 1e6)
    return (int(np.searchsorted(masses, q - width, side="left")),
            int(np.searchsorted(masses, q + width, side="right")))


def precursor_window(masses, precursor_mz, precursor_ppm, ion, *, validated=False):
    """Propagate a measured m/z tolerance through the specified ion equation.

    This is deliberately separate from neutral-mass ppm. The mass tolerance
    scales by abs(charge)/molecule_count and does not subtract an adduct from
    the error itself. A lower bound <= 0 is allowed: bank masses are positive.
    """
    center = neutral_from_mz(precursor_mz, ion)
    tolerance = _number(precursor_ppm, "precursor_ppm", nonnegative=True)
    if tolerance >= 1e6:
        raise ContractError("precursor_ppm must be smaller than one million")
    width = float(precursor_mz) * (tolerance / 1e6) * abs(ion.charge) / ion.molecule_count
    if not validated:
        validate_masses(masses)
    return (int(np.searchsorted(masses, center - width, side="left")),
            int(np.searchsorted(masses, center + width, side="right")))


def require_matching_feature_contracts(candidate_contract, model_contract):
    """Reject unknown semantics or a declared mismatch, without inferring either.

    This checks declarations only. A trusted source/version/manifest is still
    needed to establish that the declarations describe the real tensors.
    """
    required = {"family", "bit_count", "generator", "generator_version", "parameters", "preprocessing", "bit_names"}
    for contract in (candidate_contract, model_contract):
        if not isinstance(contract, dict) or set(contract) != required:
            raise ContractError("incomplete or unknown feature contract fields")
        _positive_int(contract["bit_count"], "bit_count")
        for field in ("family", "generator", "generator_version", "preprocessing", "bit_names"):
            if not isinstance(contract[field], str) or not contract[field].strip() or contract[field].lower() in {"unknown", "unspecified"}:
                raise ContractError("feature semantics must be explicit")
        parameters = contract["parameters"]
        if not isinstance(parameters, dict):
            raise ContractError("parameters must be a JSON object")
        if contract["family"] == "Morgan":
            morgan_fields = {"radius", "use_chirality", "use_bond_types", "invariant_kind", "count_simulation", "include_ring_membership", "include_redundant_environments", "only_nonzero_invariants"}
            if set(parameters) != morgan_fields:
                raise ContractError("Morgan parameters must describe the complete selected convention")
            if type(parameters["radius"]) is not int or parameters["radius"] < 0:
                raise ContractError("Morgan radius must be nonnegative")
            if not isinstance(parameters["invariant_kind"], str) or not parameters["invariant_kind"].strip():
                raise ContractError("Morgan invariant_kind must be explicit")
            for name in morgan_fields - {"radius", "invariant_kind"}:
                if type(parameters[name]) is not bool:
                    raise ContractError("Morgan convention switches must be booleans")
            if parameters["count_simulation"]:
                raise ContractError("count simulation is unsupported until explicit count bounds are implemented")
        # Reject non-JSON floating specials, objects, and unstable representations.
        try:
            json.dumps(contract, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ContractError("feature contract is not finite JSON") from exc
    if candidate_contract != model_contract:
        raise ContractError("candidate and model feature contracts differ")
    return True


def _positive_int(value, name):
    if type(value) is not int or value <= 0:
        raise ContractError(name + " must be a positive Python integer")
    return value


def validate_binary(bits, bit_count):
    _positive_int(bit_count, "bit_count")
    if not isinstance(bits, np.ndarray) or bits.ndim != 2 or bits.shape[1] != bit_count:
        raise ContractError("fingerprints must be a rows-by-bit_count matrix")
    if bits.dtype not in (np.dtype("bool"), np.dtype("uint8")):
        raise ContractError("fingerprints require bool or uint8, without coercion")
    if np.any((bits != 0) & (bits != 1)):
        raise ContractError("unpacked fingerprints contain a nonbinary value")
    return bits


def unpack_fingerprints(packed, *, bit_count, bitorder):
    """Require declared byte packing and zero padding; never infer bit order."""
    _positive_int(bit_count, "bit_count")
    if bitorder not in ("big", "little"):
        raise ContractError("bitorder must be explicitly big or little")
    if not isinstance(packed, np.ndarray) or packed.ndim != 2 or packed.dtype != np.dtype("uint8"):
        raise ContractError("packed fingerprints require a two-dimensional uint8 ndarray")
    if packed.shape[1] != (bit_count + 7) // 8:
        raise ContractError("packed byte width does not match bit_count")
    bits = np.unpackbits(packed, axis=1, bitorder=bitorder)
    if np.any(bits[:, bit_count:] != 0):
        raise ContractError("nonzero unused padding bits")
    return bits[:, :bit_count]


def maccs_keys_1_to_166(full_rdkit_bits):
    """Explicit 167-to-166 operation, allowed only when unused bit zero is zero."""
    bits = validate_binary(full_rdkit_bits, 167)
    if np.any(bits[:, 0] != 0):
        raise ContractError("RDKit MACCS unused bit zero is nonzero")
    return bits[:, 1:167]


def binary_tanimoto(query_bits, candidate_bits):
    """Intersection / union; two empty fingerprints deliberately score 0."""
    if not isinstance(query_bits, np.ndarray) or query_bits.ndim != 1:
        raise ContractError("query must be a one-dimensional binary ndarray")
    validate_binary(query_bits.reshape(1, -1), query_bits.shape[0])
    validate_binary(candidate_bits, query_bits.shape[0])
    q = query_bits.astype(bool, copy=False)
    c = candidate_bits.astype(bool, copy=False)
    intersection = np.sum(c & q, axis=1, dtype=np.int64)
    union = np.sum(c | q, axis=1, dtype=np.int64)
    return np.divide(intersection, union, out=np.zeros(len(c), dtype=np.float64), where=union != 0)


def expected_overlap_score(query_probabilities, candidate_bits):
    """dot(p,b)/(sum(p)+sum(b)-dot(p,b)); heuristic, NOT E[Jaccard].

    It differs from squared-norm algebraic Tanimoto and from a calibrated
    likelihood. No thresholding/clipping is performed. All-zero pairs score 0.
    """
    p = query_probabilities
    if not isinstance(p, np.ndarray) or p.ndim != 1 or p.dtype.kind != "f":
        raise ContractError("probabilities must be a one-dimensional floating ndarray")
    if not np.all(np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise ContractError("probabilities must be finite and within [0, 1]")
    validate_binary(candidate_bits, p.shape[0])
    p64 = p.astype(np.float64, copy=False)
    intersection = candidate_bits @ p64
    union = p64.sum(dtype=np.float64) + candidate_bits.sum(axis=1, dtype=np.int64) - intersection
    return np.divide(intersection, union, out=np.zeros(len(candidate_bits), dtype=np.float64), where=union != 0)


def stable_ranking(keys, scores):
    """Descending score, then Unicode key ascending; no chemical deduplication."""
    if not isinstance(keys, np.ndarray) or keys.ndim != 1 or keys.dtype.kind != "U":
        raise ContractError("keys must be a one-dimensional Unicode ndarray")
    if not isinstance(scores, np.ndarray) or scores.ndim != 1 or scores.dtype.kind != "f":
        raise ContractError("scores must be a one-dimensional floating ndarray")
    if len(keys) != len(scores) or not np.all(np.isfinite(scores)) or len(np.unique(keys)) != len(keys):
        raise ContractError("ranking keys/scores have an invalid alignment or duplicate key")
    return np.lexsort((keys, -scores))


def load_numeric_npy(path):
    """Read .npy without pickle. No claim of safety for hostile giant files."""
    if Path(path).suffix != ".npy":
        raise ContractError("only standalone .npy arrays are supported")
    array = np.load(path, allow_pickle=False, mmap_mode="r", max_header_size=10000)
    if not isinstance(array, np.ndarray) or array.dtype.hasobject or array.dtype.fields is not None:
        raise ContractError("object and structured arrays are not supported")
    return array


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_fixture_bundle(directory, *, manifest_sha256):
    """Read the four fixed invented arrays only after an external manifest pin.

    This is the KIT fixture contract, not an unverified third-party loader.
    An externally trusted hash verifies bytes; it cannot prove chemical semantics.
    """
    root = Path(directory)
    if not isinstance(manifest_sha256, str) or len(manifest_sha256) != 64 or any(c not in "0123456789abcdef" for c in manifest_sha256):
        raise ContractError("supply the exact external manifest SHA256")
    manifest_path = root / "MANIFEST.json"
    if sha256_file(manifest_path) != manifest_sha256:
        raise ContractError("manifest bytes differ from the external pin")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = ("masses.npy", "keys.npy", "morgan_sized.npy", "maccs_sized.npy")
    if manifest.get("schema") != "casmi-interop-invented-fixtures-v1" or set(manifest.get("files", {})) != set(files):
        raise ContractError("unexpected fixture manifest schema or filename set")
    arrays = {}
    for filename in files:
        spec = manifest["files"][filename]
        path = root / filename
        if path.stat().st_size != spec["bytes"] or sha256_file(path) != spec["sha256"]:
            raise ContractError("fixture file bytes differ from the manifest")
        arrays[filename] = load_numeric_npy(path)
    masses, keys = arrays["masses.npy"], arrays["keys.npy"]
    validate_masses(masses)
    if keys.ndim != 1 or keys.dtype.kind != "U" or len(keys) != len(masses) or len(np.unique(keys)) != len(keys) or np.any(keys == ""):
        raise ContractError("fixture keys are not unique and row aligned")
    for name, width in (("morgan_sized.npy", 2048), ("maccs_sized.npy", 166)):
        bits = validate_binary(arrays[name], width)
        if len(bits) != len(masses):
            raise ContractError("fixture fingerprint rows do not align")
    return arrays, manifest
