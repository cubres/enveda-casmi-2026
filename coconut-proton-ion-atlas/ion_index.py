"""Original, NumPy-only precursor lookup for a version-pinned COCONUT pool.

Code copyright 2026 prvsiyan; MIT. Data retain their separate source license.
No chemical parsing, pickle, network, training data, or fingerprint loading.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

import numpy as np

PROTON_MASS_U = 1.0072764665789
SOURCE_ROWS = 436389
SOURCE_BYTES = 3491240
SOURCE_SHA256 = "2b2af92c3185fa8cd52a4a3e3e7fd7eda4d94e8b9402662a3a4c55ffb13c6e5c"


@dataclass(frozen=True)
class IonChannel:
    label: str
    channel_index: int
    signed_charge: int
    molecule_multiplier: int
    signed_protons: int

    @property
    def polarity(self) -> str:
        return "positive" if self.signed_charge > 0 else "negative"

    def precursor_mz(self, neutral_mass_da):
        return (self.molecule_multiplier * neutral_mass_da
                + self.signed_protons * PROTON_MASS_U) / abs(self.signed_charge)

    def neutral_mass(self, precursor_mz):
        return (abs(self.signed_charge) * precursor_mz
                - self.signed_protons * PROTON_MASS_U) / self.molecule_multiplier


CHANNELS = (
    IonChannel("[M+H]+", 0, 1, 1, 1),
    IonChannel("[M-H]-", 1, -1, 1, -1),
    IonChannel("[M+2H]2+", 2, 2, 1, 2),
    IonChannel("[M-2H]2-", 3, -2, 1, -2),
    IonChannel("[M+3H]3+", 4, 3, 1, 3),
    IonChannel("[M-3H]3-", 5, -3, 1, -3),
    IonChannel("[2M+H]+", 6, 1, 2, 1),
    IonChannel("[2M-H]-", 7, -1, 2, -1),
)
BY_LABEL = {c.label: c for c in CHANNELS}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def finite_positive(value: float, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a finite positive number")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return value


def ppm_width(center: float, ppm: float) -> float:
    center = finite_positive(center, "center")
    if isinstance(ppm, (bool, np.bool_)):
        raise ValueError("ppm must be a finite nonnegative number")
    ppm = float(ppm)
    if not math.isfinite(ppm) or ppm < 0:
        raise ValueError("ppm must be a finite nonnegative number")
    width = center * (ppm / 1e6)
    if not math.isfinite(width):
        raise ValueError("ppm interval must be finite")
    return width


def inclusive_window(sorted_mass, center: float, ppm: float) -> tuple[int, int]:
    """Return [lo, hi) row positions; both numerical ppm endpoints are included."""
    width = ppm_width(center, ppm)
    lower, upper = center - width, center + width
    if not math.isfinite(lower) or not math.isfinite(upper):
        raise ValueError("ppm interval endpoints must be finite")
    lo = int(np.searchsorted(sorted_mass, lower, side="left"))
    hi = int(np.searchsorted(sorted_mass, upper, side="right"))
    return lo, hi


def _validate_vector(a, *, expected_rows: int | None = None):
    if a.ndim != 1 or a.dtype.str != "<f8":
        raise ValueError("expected a one-dimensional little-endian float64 array")
    if expected_rows is not None and len(a) != expected_rows:
        raise ValueError("row count mismatch")
    if not np.isfinite(a).all() or (a <= 0).any():
        raise ValueError("all masses must be finite and positive")
    if np.any(a[1:] < a[:-1]):
        raise ValueError("mass order must be nondecreasing")


def open_release(root: str | Path) -> tuple[dict, np.memmap, dict[str, np.memmap]]:
    """Check the complete frozen numerical payload once, then keep read-only maps.

    The manifest is a consistency record, not a signature. Trust the release
    obtained through its attributed source; an adversary can replace a manifest.
    """
    root = Path(root)
    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "coconut-proton-ion-index-v1":
        raise ValueError("unknown manifest schema")
    source = manifest.get("source", {})
    if (source.get("sha256") != SOURCE_SHA256
            or source.get("rows") != SOURCE_ROWS
            or source.get("dataset_version") != 2
            or source.get("dataset_ref") != "prvsiyan/coconut-casmi26-candidates"):
        raise ValueError("source pin mismatch")
    rows = manifest.get("channels")
    expected = [dict(label=c.label, channel_index=c.channel_index, signed_charge=c.signed_charge,
                     molecule_multiplier=c.molecule_multiplier,
                     signed_protons=c.signed_protons) for c in CHANNELS]
    if rows != expected or manifest.get("proton_mass_u") != PROTON_MASS_U:
        raise ValueError("ion convention mismatch")
    pins = manifest.get("files", {})
    filenames = ["neutral_mass_da.npy", "ion_mz.npy"]
    if set(pins) != set(filenames):
        raise ValueError("numeric payload allowlist mismatch")
    for name in filenames:
        p = root / name
        pin = pins[name]
        if p.is_symlink() or not p.is_file():
            raise ValueError("numeric payload must be a regular file")
        if p.stat().st_size != pin["bytes"] or sha256_file(p) != pin["sha256"]:
            raise ValueError(f"payload integrity mismatch: {name}")
    neutral = np.load(root / "neutral_mass_da.npy", mmap_mode="r", allow_pickle=False)
    _validate_vector(neutral, expected_rows=SOURCE_ROWS)
    if sha256_file(root / "neutral_mass_da.npy") != SOURCE_SHA256:
        raise ValueError("neutral source bytes changed")
    all_ions = np.load(root / "ion_mz.npy", mmap_mode="r", allow_pickle=False)
    if all_ions.shape != (len(CHANNELS), SOURCE_ROWS) or all_ions.dtype.str != "<f8":
        raise ValueError("ion matrix must be channel-major little-endian float64")
    channels = {}
    for c in CHANNELS:
        a = all_ions[c.channel_index]
        _validate_vector(a, expected_rows=SOURCE_ROWS)
        # Full row-by-row checks preserve the source positional join.
        for start in range(0, SOURCE_ROWS, 32768):
            stop = min(start + 32768, SOURCE_ROWS)
            if not np.array_equal(a[start:stop], c.precursor_mz(neutral[start:stop])):
                raise ValueError("ion array is not aligned with its neutral source")
        channels[c.label] = a
    return manifest, neutral, channels


def query(root_maps, precursor_mz: float, adduct: str, ppm: float = 10.0,
          *, tolerance_basis: str = "precursor_mz", polarity: str | None = None) -> dict:
    """Query a release already opened once; no candidate cap or ranking is applied."""
    _, neutral, arrays = root_maps
    if adduct not in BY_LABEL:
        raise ValueError("choose an explicitly supported adduct")
    c = BY_LABEL[adduct]
    if polarity is not None and polarity != c.polarity:
        raise ValueError("adduct polarity does not match the supplied polarity")
    mz = finite_positive(precursor_mz, "precursor_mz")
    target = finite_positive(c.neutral_mass(mz), "converted neutral mass")
    if tolerance_basis == "precursor_mz":
        lo, hi = inclusive_window(arrays[adduct], mz, ppm)
        width = ppm_width(mz, ppm) * abs(c.signed_charge) / c.molecule_multiplier
    elif tolerance_basis == "neutral_mass":
        lo, hi = inclusive_window(neutral, target, ppm)
        width = ppm_width(target, ppm)
    else:
        raise ValueError("tolerance_basis must be precursor_mz or neutral_mass")
    return dict(adduct=adduct, polarity=c.polarity, signed_charge=c.signed_charge,
                tolerance_basis=tolerance_basis, ppm=float(ppm),
                precursor_mz=mz, neutral_mass_center_da=target,
                neutral_mass_half_width_da=width,
                source_row_start=lo, source_row_stop_exclusive=hi,
                candidate_count=hi - lo)
