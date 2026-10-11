"""Invented public chemistry controls for the original candidate supplement."""
import json,math,time,hashlib,pathlib,unittest
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors
from analogue_edits import generate

def mass(s):
    return rdMolDescriptors.CalcExactMolWt(Chem.MolFromSmiles(s))

class Tests(unittest.TestCase):
    def test_methanol_homologation(self):
        r=generate(["CO"],mass("CCO"))
        self.assertIn("CCO",[c.smiles for c in r.additions])
    def test_benzoate_hydroxylation(self):
        r=generate(["O=C(O)c1ccccc1"],mass("O=C(O)c1ccccc1O"))
        self.assertIn(Chem.MolToSmiles(Chem.MolFromSmiles("O=C(O)c1ccccc1O")),[c.smiles for c in r.additions])
    def test_oxidation(self):
        r=generate(["CCO"],mass("CC=O"))
        self.assertIn("CC=O",[c.smiles for c in r.additions])
    def test_deoxygenation(self):
        r=generate(["CCO"],mass("CC"))
        self.assertIn("CC",[c.smiles for c in r.additions])
    def test_incumbent_order_kept_and_not_reemitted(self):
        original=["CCO","CO"]
        r=generate(["CO"],mass("CCO"),incumbent=original)
        self.assertEqual(tuple(original),r.incumbent)
        self.assertNotIn("CCO",[c.smiles for c in r.additions])
        self.assertEqual(original,["CCO","CO"])
    def test_unreachable_structure_stays_unreached(self):
        # One edit from methanol cannot manufacture an aromatic ring.
        r=generate(["CO"],mass("c1ccccc1"))
        self.assertEqual((),r.additions)
    def test_no_candidates_for_wrong_mass(self):
        self.assertEqual((),generate(["CO"],1000).additions)
    def test_all_candidates_neutral_connected_within_window(self):
        for s in ("CO","CCO","CC(=O)O","O=C(O)c1ccccc1"):
            r=generate([s],mass(s)+15.9949146196,ppm=20)
            for c in r.additions:
                m=Chem.MolFromSmiles(c.smiles)
                self.assertEqual(1,len(Chem.GetMolFrags(m)))
                self.assertTrue(all(a.GetFormalCharge()==0 for a in m.GetAtoms()))
                self.assertLessEqual(abs(c.residual_ppm),20)
                self.assertAlmostEqual(mass(c.smiles),c.exact_mass,places=8)
    def test_exact_attempt_bound_is_reported(self):
        r=generate(["CCO","CCCCCC"],mass("CC=O"),max_attempts=1)
        self.assertEqual(1,r.attempted);self.assertTrue(r.capped_attempts)
    def test_deterministic_no_duplicate_votes(self):
        a=generate(["CO"],mass("CCO"))
        b=generate(["CO","OC","CO"],mass("CCO"))
        self.assertEqual(a.additions,b.additions)
        self.assertEqual(a.attempted,b.attempted)
        self.assertEqual(len(set(c.smiles for c in b.additions)),len(b.additions))
    def test_invalid_seed_and_deep_seed_no_fill(self):
        r=generate(["bad","CO"],mass("CCO"),max_seeds=1)
        self.assertEqual(1,r.invalid_seeds);self.assertEqual((),r.additions)
    def test_salts_radicals_isotopes_and_charges_rejected(self):
        for s in ("C.C","[CH3]","[13CH4]","[NH4+]"):
            r=generate([s],mass("CCO"))
            self.assertEqual(1,r.invalid_seeds)
    def test_input_validation(self):
        for k,v in (("max_seeds",True),("max_attempts",0),("max_atoms",-1),("max_additions",1.5),("ppm",0),("ppm",math.nan)):
            with self.assertRaises(ValueError):generate(["CO"],mass("CCO"),**{k:v})
        for v in (True,-1,0,math.inf,math.nan):
            with self.assertRaises(ValueError):generate(["CO"],v)
    def test_strings_not_collections(self):
        with self.assertRaises(ValueError):generate("CO",mass("CCO"))
        with self.assertRaises(ValueError):generate(["CO"],mass("CCO"),incumbent="CO")
    def test_max_atoms(self):
        r=generate(["CCCC"],mass("CCO"),max_atoms=3)
        self.assertEqual(1,r.invalid_seeds)
    def test_stereo_dedup_without_official_identity_claim(self):
        r=generate(["CC(O)C"],mass("CC(=O)C"))
        self.assertEqual(len(r.additions),len(set(c.smiles for c in r.additions)))
    def test_model_never_imported(self):
        import sys
        self.assertNotIn("torch",sys.modules)
        self.assertNotIn("pickle",sys.modules)
    def test_overlong_incumbent_rejected_without_silent_truncation(self):
        with self.assertRaises(ValueError):generate(["CO"],mass("CCO"),incumbent=["CO"]*26)
    def test_seed_iterable_consumed_only_to_bound(self):
        def seeds():
            yield "CO"
            raise RuntimeError("deep seed was consumed")
        self.assertIn("CCO",[c.smiles for c in generate(seeds(),mass("CCO"),max_seeds=1).additions])
    def test_alternate_seed_atom_order_has_identical_provenance(self):
        a=generate(["CCO"],mass("CC=O"),max_attempts=15)
        b=generate(["OCC"],mass("CC=O"),max_attempts=15)
        self.assertEqual(a,b)

if __name__=="__main__":
    unittest.main()

