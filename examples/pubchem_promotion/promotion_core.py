"""Original conservative post-fusion promotion mechanics; no calibrated policy.

Chemistry identities and masses must be produced by the caller from the same
SMILES with the declared scoring canonicalizer. This module validates their
contracts, not chemical equivalence. A policy must be independently calibrated
and explicitly approved before a real candidate can move. The preflight has no
such policy and never reconstructs a production final list.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


# The unchanged baseline's neutral-ion constants, pinned in the preflight.
H = 1.00782503207
ELECTRON = 0.00054857990
PROTON = H - ELECTRON
WATER = 2 * H + 15.9949146196
AMMONIUM = 14.0030740048 + 4 * H - ELECTRON
FORMATE = 12.0 + 2 * H + 2 * 15.9949146196
ACETATE = 24.0 + 4 * H + 2 * 15.9949146196
SODIUM = 22.9897692809 - ELECTRON
POTASSIUM = 38.96370668 - ELECTRON
ADDUCTS = {
    "[M+H]+": (1, 1, PROTON), "[M+NH4]+": (1, 1, AMMONIUM),
    "[M+Na]+": (1, 1, SODIUM), "[M+K]+": (1, 1, POTASSIUM),
    "[M-H2O+H]+": (1, 1, PROTON - WATER),
    "[M-2H2O+H]+": (1, 1, PROTON - 2 * WATER),
    "[M+2H]2+": (1, 2, 2 * PROTON), "[M]+": (1, 1, -ELECTRON),
    "[M-H2O]+": (1, 1, -ELECTRON - WATER),
    "[M+CH3OH+H]+": (1, 1, PROTON + 12.0 + 4 * H + 15.9949146196),
    "[M+CH3CN+H]+": (1, 1, PROTON + 24.0 + 3 * H + 14.0030740048),
    "[M-H]-": (1, 1, -PROTON), "[M-H2O-H]-": (1, 1, -PROTON - WATER),
    "[M+CH2O2-H]-": (1, 1, FORMATE - PROTON),
    "[M+C2H4O2-H]-": (1, 1, ACETATE - PROTON),
    "[M+Cl]-": (1, 1, 34.96885268 + ELECTRON), "[M]-": (1, 1, ELECTRON),
    "[M-2H]-": (1, 2, -2 * PROTON),
    # Preserve the actual baseline constant, rather than silently revising it.
    "[M+Na-2H]-": (1, 1, 22.9897692809 - 2 * PROTON),
    "[2M+H]+": (2, 1, PROTON), "[2M+Na]+": (2, 1, SODIUM),
    "[2M+NH4]+": (2, 1, AMMONIUM), "[2M+K]+": (2, 1, POTASSIUM),
    "[2M-H]-": (2, 1, -PROTON),
    "[2M+CH2O2-H]-": (2, 1, FORMATE - PROTON),
    "[2M+C2H4O2-H]-": (2, 1, ACETATE - PROTON),
    "[2M+Na-2H]-": (2, 1, 22.9897692809 - 2 * PROTON),
    "[3M+H]+": (3, 1, PROTON), "[3M-H]-": (3, 1, -PROTON),
}


@dataclass(frozen=True)
class Observation:
    precursor_mz: float | None
    adduct: str | None
    mode: str | None


@dataclass(frozen=True)
class RankedCandidate:
    smiles: str
    # (sorted heavy-atom composition, tautomer-canonical InChIKey14)
    identity: tuple


@dataclass(frozen=True)
class TierEvidence:
    candidate: RankedCandidate
    exact_mass: float
    raw_fz: float
    standardized_fz: float
    popularity: float
    combined_score: float
    survivor_count: int
    survivor_mean: float
    survivor_std: float
    store_row: int


@dataclass(frozen=True)
class PromotionResult:
    # The same input sequence object is returned on every abstention.
    ranked: Sequence[RankedCandidate]
    promoted: bool
    reason: str
    matching_observations: tuple[int, ...] = ()


def finite_number(value: object) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def neutral_observation(observation: Observation) -> float | None:
    """Undo a declared supported adduct; reject missing or conflicting polarity."""
    if not finite_number(observation.precursor_mz) or observation.precursor_mz <= 0:
        return None
    spec = ADDUCTS.get(observation.adduct)
    if spec is None or observation.mode not in ("positive", "negative"):
        return None
    if observation.adduct.endswith("+") != (observation.mode == "positive"):
        return None
    multiplicity, charge, shift = spec
    mass = (observation.precursor_mz * charge - shift) / multiplicity
    return mass if math.isfinite(mass) and mass > 0 else None


def matching_observations(exact_mass: float, observations: Sequence[Observation]) -> tuple[int, ...]:
    """Candidate-specific inclusive 10 ppm checks, relative to the candidate mass.

    This is an eligibility check on an already selected median-window tier
    candidate. It does not expand that tier window or repair an unknown adduct.
    """
    if not finite_number(exact_mass) or exact_mass <= 0:
        return ()
    tolerance = exact_mass * 10.0 / 1_000_000.0
    return tuple(i for i, observation in enumerate(observations)
                 if (mass := neutral_observation(observation)) is not None
                 and abs(mass - exact_mass) <= tolerance)


def valid_identity(identity: object) -> bool:
    if not isinstance(identity, tuple) or len(identity) != 2:
        return False
    composition, key = identity
    if not isinstance(composition, tuple) or not composition:
        return False
    if not isinstance(key, str) or len(key) != 14 or not key.isascii() or not key.isalpha() or not key.isupper():
        return False
    if any(not isinstance(item, tuple) or len(item) != 2 or
           not isinstance(item[0], str) or not item[0] or item[0] == "H" or
           not isinstance(item[1], int) or isinstance(item[1], bool) or item[1] <= 0
           for item in composition):
        return False
    return composition == tuple(sorted(composition)) and len({e for e, _ in composition}) == len(composition)


def valid_evidence(evidence: TierEvidence) -> bool:
    """Require finite, nondegenerate statistics and identity-bound values."""
    c = evidence.candidate
    if not isinstance(c, RankedCandidate) or not c.smiles.strip() or not valid_identity(c.identity):
        return False
    values = (evidence.exact_mass, evidence.raw_fz, evidence.standardized_fz,
              evidence.popularity, evidence.combined_score, evidence.survivor_mean,
              evidence.survivor_std)
    if not all(finite_number(v) for v in values):
        return False
    if evidence.exact_mass <= 0 or evidence.popularity < 0 or evidence.survivor_std <= 1e-9:
        return False
    if not isinstance(evidence.survivor_count, int) or isinstance(evidence.survivor_count, bool) or evidence.survivor_count < 2:
        return False
    if not isinstance(evidence.store_row, int) or isinstance(evidence.store_row, bool) or evidence.store_row < 0:
        return False
    z = (evidence.raw_fz - evidence.survivor_mean) / evidence.survivor_std
    combined = z + 0.25 * evidence.popularity
    return math.isclose(z, evidence.standardized_fz, rel_tol=1e-9, abs_tol=1e-9) and math.isclose(
        combined, evidence.combined_score, rel_tol=1e-9, abs_tol=1e-9)


def promote_leading(
    final_ranked: Sequence[RankedCandidate],
    leading: TierEvidence | None,
    observations: Sequence[Observation],
    *,
    policy_approved: bool = False,
    full_pipeline_available: bool = False,
    ap2_invoked: bool = False,
    library_max: float | None = None,
) -> PromotionResult:
    """Promote at most the leading eligible tier candidate after final dedup.

    No confidence threshold or optimum is supplied here. Approval is an
    explicit caller attestation, never inferred from a strong-looking score.
    Failure/empty/unavailable cases abstain. On success aliases of the promoted
    identity are removed, all other candidates keep their relative order, and
    only the tail may be displaced from the 25-entry output.
    """
    abstain = lambda reason: PromotionResult(final_ranked, False, reason)
    if not full_pipeline_available:
        return abstain("full_pipeline_unavailable")
    if not ap2_invoked:
        return abstain("ap2_uninvoked")
    if not policy_approved:
        return abstain("policy_unapproved")
    if not finite_number(library_max):
        return abstain("library_evidence_missing")
    if float(library_max) >= 0.90:
        return abstain("strong_library_match")
    if not final_ranked or len(final_ranked) > 25:
        return abstain("final_list_invalid")
    if any(not isinstance(c, RankedCandidate) or not c.smiles.strip() or not valid_identity(c.identity)
           for c in final_ranked):
        return abstain("final_list_invalid")
    if len({c.identity for c in final_ranked}) != len(final_ranked):
        return abstain("final_list_not_deduplicated")
    if leading is None or not valid_evidence(leading):
        return abstain("tier_metadata_invalid")
    matches = matching_observations(leading.exact_mass, observations)
    if not matches:
        return abstain("candidate_mass_ineligible")
    ranked = [leading.candidate] + [c for c in final_ranked if c.identity != leading.candidate.identity]
    return PromotionResult(ranked[:25], True, "promoted", matches)
