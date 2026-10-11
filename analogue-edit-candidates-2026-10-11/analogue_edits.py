"""Original bounded one-edit candidate generator; development prototype, not a scorer.

Only caller-supplied analogues and measured neutral mass are used. The incumbent
list is returned separately and never reordered or removed. No models, datasets,
downloaders, truth formulae, labels or notebook code are imported.
"""
from dataclasses import dataclass
import math
from typing import Iterable
from rdkit import Chem, rdBase
from rdkit.Chem import rdMolDescriptors

@dataclass(frozen=True)
class Candidate:
    smiles: str
    exact_mass: float
    residual_ppm: float
    seed_smiles: str
    edit: str

@dataclass(frozen=True)
class Result:
    incumbent: tuple[str, ...]
    additions: tuple[Candidate, ...]
    attempted: int
    sanitized: int
    mass_compatible: int
    capped_attempts: bool
    capped_candidates: bool
    invalid_seeds: int
    rdkit_version: str

def _positive_int(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(name + " must be a positive int")

def _neutral_connected(molecule):
    if molecule is None or len(Chem.GetMolFrags(molecule)) != 1:
        return False
    return all(a.GetFormalCharge() == 0 and a.GetNumRadicalElectrons() == 0
               and a.GetIsotope() == 0 for a in molecule.GetAtoms())

def _canonical(molecule):
    copy = Chem.Mol(molecule)
    Chem.RemoveStereochemistry(copy)
    return Chem.MolToSmiles(copy, canonical=True, isomericSmiles=False)

def _edits(seed):
    # Independent, deliberately small chemistry: terminal C/O addition/removal,
    # heteroatom substitution and acyclic bond oxidation/reduction. Aromatic bond
    # edits, ring surgery, learned templates and multisite edits are excluded.
    n = seed.GetNumAtoms()
    for site in range(n):
        atom = seed.GetAtomWithIdx(site)
        if atom.GetTotalNumHs() > 0:
            for symbol in ("C", "O"):
                rw = Chem.RWMol(seed)
                added = rw.AddAtom(Chem.Atom(symbol))
                rw.AddBond(site, added, Chem.BondType.SINGLE)
                yield rw.GetMol(), "add_" + symbol + "@" + str(site)
        if atom.GetDegree() == 1 and not atom.GetIsAromatic() and atom.GetSymbol() in ("C", "O") and n > 1:
            rw = Chem.RWMol(seed)
            rw.RemoveAtom(site)
            yield rw.GetMol(), "remove_" + atom.GetSymbol() + "@" + str(site)
        if not atom.GetIsAromatic() and atom.GetSymbol() in ("C", "N", "O", "S"):
            for symbol in ("C", "N", "O", "S"):
                if symbol != atom.GetSymbol():
                    rw = Chem.RWMol(seed)
                    rw.ReplaceAtom(site, Chem.Atom(symbol), preserveProps=False)
                    yield rw.GetMol(), "replace_" + atom.GetSymbol() + "_" + symbol + "@" + str(site)
    for bond in seed.GetBonds():
        if bond.GetIsAromatic() or bond.IsInRing():
            continue
        current = bond.GetBondType()
        if current not in (Chem.BondType.SINGLE, Chem.BondType.DOUBLE):
            continue
        rw = Chem.RWMol(seed)
        target = Chem.BondType.DOUBLE if current == Chem.BondType.SINGLE else Chem.BondType.SINGLE
        rw.GetBondWithIdx(bond.GetIdx()).SetBondType(target)
        yield rw.GetMol(), "bond_" + str(current) + "_" + str(target) + "@" + str(bond.GetIdx())

def generate(analogues: Iterable[str], neutral_mass: float, *,
             incumbent: Iterable[str] = (), ppm: float = 10.0,
             max_seeds: int = 10, max_attempts: int = 2000,
             max_additions: int = 256, max_atoms: int = 64) -> Result:
    """Generate a separate candidate supplement without touching incumbent order.

    Input neutral mass must come from measured precursor/adduct metadata.
    This prototype uses canonical non-stereo SMILES, NOT the official tautomer
    quotient. Full official identity normalization is an unresolved integration
    gate, and the supplement must be rescored in the common candidate universe.
    """
    for value, name in ((max_seeds,"max_seeds"), (max_attempts,"max_attempts"),
                        (max_additions,"max_additions"), (max_atoms,"max_atoms")):
        _positive_int(value,name)
    if isinstance(neutral_mass,bool) or not isinstance(neutral_mass,(int,float)) or not math.isfinite(neutral_mass) or neutral_mass <= 0:
        raise ValueError("neutral_mass must be finite and positive")
    if isinstance(ppm,bool) or not isinstance(ppm,(int,float)) or not math.isfinite(ppm) or not 0 < ppm <= 1000:
        raise ValueError("ppm must be finite in (0, 1000]")
    if isinstance(analogues,(str,bytes)) or isinstance(incumbent,(str,bytes)):
        raise ValueError("analogue and incumbent collections must be iterables of SMILES")
    # Inputs themselves are bounded before parsing. Preserve analogue ranking
    # supplied by the spectral stage; never use truth structure to select seeds.
    seeds, seen_seeds, invalid = [], set(), 0
    from itertools import islice
    original = tuple(islice(iter(incumbent), 26))
    if len(original) > 25:
        raise ValueError("incumbent has more than 25 entries")
    known = set()
    with rdBase.BlockLogs():
        for s in original:
            if not isinstance(s,str) or not 0 < len(s) <= 1024:
                raise ValueError("invalid incumbent SMILES string")
            m = Chem.MolFromSmiles(s)
            if m is None:
                raise ValueError("incumbent cannot be parsed")
            known.add(_canonical(m))
        # Consume at most max_seeds entries. A caller must provide the frozen top
        # seeds; invalid or duplicate entries do not silently pull deeper ones.
        for s in islice(iter(analogues), max_seeds):
            if not isinstance(s,str) or not 0 < len(s) <= 1024:
                invalid += 1
                continue
            m = Chem.MolFromSmiles(s)
            if not _neutral_connected(m) or m.GetNumAtoms() > max_atoms:
                invalid += 1
                continue
            canonical = _canonical(m)
            if canonical not in seen_seeds:
                # Use the reported canonical seed's own atom order so that edit
                # indices can be reproduced from the provenance string.
                seeds.append((canonical,Chem.MolFromSmiles(canonical)))
                seen_seeds.add(canonical)
    attempted = sanitized = compatible = 0
    additions = {}
    capped = False
    with rdBase.BlockLogs():
        for seed_s, seed in seeds:
            for candidate, edit in _edits(seed):
                if attempted >= max_attempts:
                    capped = True
                    break
                attempted += 1
                try:
                    Chem.SanitizeMol(candidate)
                except (ValueError,RuntimeError):
                    continue
                if not _neutral_connected(candidate) or candidate.GetNumAtoms() > max_atoms:
                    continue
                sanitized += 1
                mass = float(rdMolDescriptors.CalcExactMolWt(candidate))
                residual = (mass - neutral_mass) / neutral_mass * 1e6
                if abs(residual) > ppm:
                    continue
                compatible += 1
                canonical = _canonical(candidate)
                if canonical in known or canonical in seen_seeds:
                    continue
                value = Candidate(canonical,mass,residual,seed_s,edit)
                previous = additions.get(canonical)
                if previous is None or (value.seed_smiles,value.edit) < (previous.seed_smiles,previous.edit):
                    additions[canonical] = value
            if capped:
                break
    ordered = sorted(additions.values(),key=lambda c:(abs(c.residual_ppm),c.smiles))
    return Result(original,tuple(ordered[:max_additions]),attempted,sanitized,compatible,
                  capped,len(ordered)>max_additions,invalid,rdBase.rdkitVersion)

