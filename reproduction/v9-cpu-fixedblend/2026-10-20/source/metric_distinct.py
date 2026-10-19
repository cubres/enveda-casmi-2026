"""Original stable candidate compaction matching the published CASMI26 metric.

Specification: https://www.kaggle.com/code/metric/casmi-mean-reciprocal-rank
No trained parameters, reference answers, or third-party notebook code are used.
"""
from functools import lru_cache

import rdkit
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize

EXPECTED_RDKIT = "2026.03.3"
if rdkit.__version__ != EXPECTED_RDKIT:
    raise RuntimeError(f"Metric requires RDKit {EXPECTED_RDKIT}; found {rdkit.__version__}")
_enumerator = rdMolStandardize.TautomerEnumerator()


@lru_cache(maxsize=100_000)
def equivalence_key(smiles):
    """Return the metric's composition gate plus tautomer-canonical InChIKey14.

    Including the composition gate preserves the complete matching predicate,
    even in the hypothetical case of an InChIKey hash collision.
    """
    if not isinstance(smiles, str) or not smiles.strip():
        return None
    try:
        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            return None
        counts = {}
        for atom in molecule.GetAtoms():
            symbol = atom.GetSymbol()
            if symbol != "H":
                counts[symbol] = counts.get(symbol, 0) + 1
        canonical = _enumerator.Canonicalize(molecule)
        key = Chem.MolToInchiKey(canonical)[:14]
        if len(key) != 14 or not counts:
            return None
        return tuple(sorted(counts.items())), key
    except (ValueError, RuntimeError, TypeError):
        return None


def distinct_guesses(ranked_smiles, maximum=25):
    """Keep each metric class's first representative in an already ranked list.

    Consume the full ranked list until 25 distinct valid classes are collected.
    Every retained class moves earlier or stays in place; reciprocal rank cannot
    fall for any possible answer under the pinned MRR@25 metric. The supplied
    order, including ties, must match the base ranking; this function never
    sorts. Model scores must not be recomputed or pooled during this operation.
    """
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum != 25:
        raise ValueError("maximum must be exactly 25, the official metric cutoff")
    seen, guesses = set(), []
    for raw in ranked_smiles:
        if not isinstance(raw, str):
            raise TypeError("Candidate SMILES must be strings")
        smiles = raw.strip()
        key = equivalence_key(smiles)
        if key is None or key in seen:
            continue
        seen.add(key)
        guesses.append(smiles)
        if len(guesses) == maximum:
            break
    if not guesses:
        raise ValueError("No valid candidate remains; no constant fallback is permitted")
    return guesses
