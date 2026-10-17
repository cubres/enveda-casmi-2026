"""Build a tiny, embeddable per-structure role table for a clean (optimizer-only) fingerprint-model training run.

Source of truth (read-only): enveda_glacier_references_20260930T172626Z/spectrum_role_codes.npy, aligned with the
`six` (structure index) array of the spectrum archive up_train/spec.npz that the private trainer mounts as
prvsiyan/casmi26-spec-fp. Role codes: 0 optimizer, 1 checkpoint_selection, 2 fusion_selection, 3 final_test.
Structure indices without any spectrum get code 3 here (never sampled: they have no spectra).

Outputs (new files next to this script):
  roles_by_structure.b64      zlib+base64 of the 2-bit packed table (one line, ~55 kB)
  roles_by_structure.sha256   sha256 of the UNPACKED uint8 table (n_structures bytes)
  trainer_patch.txt           the two-line change for train_fp3.py / train_fp4.py and the decode snippet
  receipt.json                counts and hashes
Nothing is pushed anywhere; a coordinator decides whether to use it.
"""
import base64, hashlib, json, zlib
import numpy as np

R = "/Users/cubres/Documents/Neurogolf/research/enveda_glacier_references_20260930T172626Z/spectrum_role_codes.npy"
S = "/Users/cubres/Documents/Clauding/casmi_work/up_train/spec.npz"
role = np.load(R); z = np.load(S); six = z["six"]; is_val = z["is_val"]
assert len(role) == len(six)
n = int(six.max()) + 1
tab = np.full(n, 3, np.uint8); tab[six] = role
assert (tab[six] == role).all(), "role is not constant per structure index"
bits = np.unpackbits(tab[:, None], axis=1)[:, 6:].reshape(-1)          # 2 bits per structure, MSB first
packed = np.packbits(bits)
b64 = base64.b64encode(zlib.compress(packed.tobytes(), 9)).decode()
open("roles_by_structure.b64", "w").write(b64)
sha = hashlib.sha256(tab.tobytes()).hexdigest()
open("roles_by_structure.sha256", "w").write(sha + "\n")

# decode exactly as the trainer would, and verify
def decode(b64s, n):
    raw = np.frombuffer(zlib.decompress(base64.b64decode(b64s)), np.uint8)
    b = np.unpackbits(raw)[: 2 * n].reshape(n, 2)
    return (b[:, 0] * 2 + b[:, 1]).astype(np.uint8)
t2 = decode(b64, n)
assert (t2 == tab).all() and hashlib.sha256(t2.tobytes()).hexdigest() == sha
r = t2[six]
tr = np.where(r == 0)[0]
va = np.where((r == 1) & (six % 2 == 0))[0]
rk = np.where((r == 1) & (six % 2 == 1))[0]
rec = dict(n_structures=n, n_spectra=int(len(six)), table_sha256=sha, b64_chars=len(b64),
           spectrum_role_codes_sha256=hashlib.sha256(open(R, "rb").read()).hexdigest(),
           train_spectra_optimizer=int(len(tr)), train_structures=int(len(np.unique(six[tr]))),
           val_spectra_checkpoint_even=int(len(va)), val_structures=int(len(np.unique(six[va]))),
           reserved_for_ranker_rows_checkpoint_odd_spectra=int(len(rk)), reserved_structures=int(len(np.unique(six[rk]))),
           held_out_fusion_selection_spectra=int((r == 2).sum()), held_out_final_test_spectra=int((r == 3).sum()),
           old_split_train_spectra=int((~is_val).sum()), old_split_val_spectra=int(is_val.sum()),
           old_train_spectra_now_held_out=int(((~is_val) & (r != 0)).sum()))
json.dump(rec, open("receipt.json", "w"), indent=1)
open("trainer_patch.txt", "w").write(f'''Clean-split change for train_fp3.py (per-spectrum model) and train_fp4.py (merged-spectrum model).
Both files contain the same two lines in Data.__init__ (train_fp3.py line 29, train_fp4.py line 36):

    self.tr=np.where(~self.is_val)[0]; self.va=np.where(self.is_val)[0]

Replace them with (ROLES_B64 = the single line stored in roles_by_structure.b64, {len(b64)} characters):

    import base64, zlib, hashlib
    _n = int(self.six.max()) + 1
    _b = np.unpackbits(np.frombuffer(zlib.decompress(base64.b64decode(ROLES_B64)), np.uint8))[: 2 * _n].reshape(_n, 2)
    _role = (_b[:, 0] * 2 + _b[:, 1]).astype(np.uint8)
    assert hashlib.sha256(_role.tobytes()).hexdigest() == "{sha}"
    _r = _role[self.six]                                   # 0 optimizer, 1 checkpoint_selection, 2 fusion_selection, 3 final_test
    self.tr = np.where(_r == 0)[0]                         # weights: optimizer spectra only
    self.va = np.where((_r == 1) & (self.six % 2 == 0))[0] # checkpoint choice: even-index checkpoint_selection structures
                                                           # (odd-index ones stay untouched for ranker-row generation)

Expected first log line after the change: train={rec["train_spectra_optimizer"]} (before the s2p>=0 filter) val={rec["val_spectra_checkpoint_even"]}
(the old split printed train=2222324 val=109985 after the filter).
Nothing else changes: same architecture, loss, augmentation, hard-negative sampling from the full blind pool.
''')
print(json.dumps(rec, indent=1))
