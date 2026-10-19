"""SOURCE ONLY. CPU inputs adapted from cubres' Apache-2.0 CASMI trainer.

Credit: original train_fp4.py Data.batch input prefix (SHA1daa2532...) and
train_full_fingerprint.py FullData casts (SHAdf609595...). No peaks are prepared
again. No original module, Data constructor, truth fingerprint or model runs.
NumPy and Torch are passed by the separately admitted caller, never imported.
SPDX-License-Identifier: Apache-2.0
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

INPUT_NAMES = ("off", "mz", "it", "prec", "ad", "ins", "ce", "mode")
HEADER_SHA = "4c8db4e46b0bceef8bcf80310d09e371988501ea5d35c1f208dd2ccc3db5a8d4"
SPEC_SHA = "99dbf966d2607e2da8085a6550206a71fc912d2c90b9555a725a2569e4af4500"
SOURCE_PINS = {
    "fpmodel": "69f2656778a08233e22235bf4853f0b3d2420b431390a32d6c8ed453cde85c76",
    "train_fp4": "1daa2532ef186600c21fc96fa6a16e1729084b4e7257524a0dc33fc2adc7abb0",
    "train_full_fingerprint": "df609595b23b37fa475b480057275dcc22b753ae4159726bc7ddff5442980a0e",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def metadata_header_guard(np, spec, header_receipt_path):
    """Check loaded inputs against the exact public-V1 header-only receipt."""
    body = Path(header_receipt_path).read_bytes()
    require(hashlib.sha256(body).hexdigest() == HEADER_SHA, "Pinned header receipt drift")
    receipt = json.loads(body)
    require(receipt["sha256"] == SPEC_SHA and receipt["file_bytes"] == 920788910, "Public V1 spec binding")
    require(set(spec) == set(INPUT_NAMES), "Inputs-only eight-member mapping required")
    for name in INPUT_NAMES:
        value, header = spec[name], receipt["member_headers"][name]
        require(isinstance(value, np.ndarray) and not value.dtype.hasobject, "Numeric prepared input only")
        require(value.shape == tuple(header["shape"]) and value.dtype == np.dtype(header["descr"]), "Exact prepared header: " + name)
        require(not header["fortran_order"] and value.flags.c_contiguous, "C-order prepared input: " + name)
    return {"header_receipt_sha256": HEADER_SHA, "spec_sha256_contract": SPEC_SHA, "input_members": list(INPUT_NAMES)}


def cpu_inputs(np, torch, spec, ids):
    """Independent implementation of the fixed single-view input contract."""
    require(set(spec) == set(INPUT_NAMES), "No labels or fingerprints in input mapping")
    ids = np.asarray(ids)
    require(ids.ndim == 1 and ids.dtype.kind in "iu" and 0 < len(ids) <= 64, "Integer batch of one to64 rows")
    require(np.all((ids >= 0) & (ids < len(spec["prec"]))), "Spectrum IDs in public input range")
    ids = ids.astype(np.int64, copy=False)
    starts, ends = spec["off"][ids], spec["off"][ids + 1]
    require(np.all((starts >= 0) & (ends >= starts) & (ends <= len(spec["mz"]))) and len(spec["mz"]) == len(spec["it"]), "Prepared peak offsets")
    lengths = np.minimum(ends - starts, 128)
    width = max(int(lengths.max()), 1)
    mz, intensity = np.zeros((len(ids), width), np.float32), np.zeros((len(ids), width), np.float32)
    pad = np.ones((len(ids), width), bool)
    for row, (start, length) in enumerate(zip(starts, lengths)):
        mz[row, :length] = spec["mz"][start:start + length]
        intensity[row, :length] = spec["it"][start:start + length]
        pad[row, :length] = False
    ce = np.where(spec["ce"][ids] < 0, 25.0, spec["ce"][ids]).astype(np.float32)
    values = (mz, intensity, pad, spec["prec"][ids], spec["ad"][ids].astype(np.int64),
              spec["ins"][ids].astype(np.int64), ce, spec["mode"][ids])
    require(all(np.isfinite(value).all() for value in values), "Finite prepared inputs; never repair nonfinite values")
    return tuple(torch.as_tensor(value, device="cpu") for value in values)


def original_input_prefix(np, torch, spec, ids, source_paths):
    """Project the exact pinned prefix under aug=False, merge_p=0, no targets."""
    require(set(source_paths) == set(SOURCE_PINS), "All three original source bindings required")
    bodies = {name: Path(source_paths[name]).read_bytes() for name in SOURCE_PINS}
    require(all(hashlib.sha256(bodies[name]).hexdigest() == pin for name, pin in SOURCE_PINS.items()), "Original source drift")
    data = next(node for node in ast.parse(bodies["train_fp4"]).body if isinstance(node, ast.ClassDef) and node.name == "Data")
    method = copy.deepcopy(next(node for node in data.body if isinstance(node, ast.FunctionDef) and node.name == "batch"))
    prefix, removed, stopped = [], set(), False
    for statement in method.body:
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pos" for t in statement.targets):
            stopped = True
            break
        if isinstance(statement, ast.If):
            condition = ast.unparse(statement.test)
            require(condition in {"merge_p > 0 and rng is not None", "aug and rng is not None"}, "Only fixed-disabled branches may be removed")
            removed.add(condition)
            continue
        prefix.append(statement)
    require(stopped and len(removed) == 2, "Exact target boundary and two inactive branches")
    require(not any(isinstance(n, ast.Attribute) and n.attr in {"s2p", "six", "PFP", "peers", "_merged"} for node in prefix for n in ast.walk(node)), "Reference cannot access targets or merge peers")
    method.body = prefix + [ast.Return(value=ast.Name(id="inp", ctx=ast.Load()))]
    namespace = {"np": np, "torch": torch, "fpmodel": SimpleNamespace(MAX_PEAKS=128)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), "<pinned-input-prefix-only>", "exec"), namespace)
    holder = SimpleNamespace(**{name: spec[name] for name in INPUT_NAMES}, device="cpu")
    holder.ad, holder.ins = holder.ad.astype(np.int64), holder.ins.astype(np.int64)
    return namespace["batch"](holder, np.asarray(ids, dtype=np.int64), K=0, rng=None, aug=False, merge_p=0.0)


def assert_prefix_parity(np, torch, spec, ids, source_paths):
    actual = cpu_inputs(np, torch, spec, ids)
    reference = original_input_prefix(np, torch, spec, ids, source_paths)
    require(all(a.device.type == b.device.type == "cpu" and a.dtype == b.dtype and a.shape == b.shape and torch.equal(a, b)
                for a, b in zip(actual, reference)) and len(actual) == len(reference) == 8, "Exact eight-input original-prefix parity")
    return actual
