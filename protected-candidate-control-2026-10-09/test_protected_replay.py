"""Synthetic changed-arm and exact-control contracts; no competition data."""
from types import SimpleNamespace
import json

from protected_replay import ProtectedReplay


def scenario(changed_arm=True, buggy_closed=False):
    cfg = SimpleNamespace(USE_SECOND_LIST=True, LIB_GATE=.90)
    diag = []

    def final_list(*args):
        lib_max = args[6]
        diag.append({"gate_open": lib_max < cfg.LIB_GATE})
        if cfg.USE_SECOND_LIST and (lib_max < cfg.LIB_GATE or buggy_closed):
            return ["CCC", "CC", "C"]
        return ["C", "CC", "CCC"]

    return ProtectedReplay(final_list, cfg, diag, changed_arm=changed_arm), cfg, diag


def call(replay, gate):
    return replay(None, None, None, None, None, None, gate, None, None, None)


def run():
    replay, cfg, diag = scenario()
    if call(replay, 1.0) != ["C", "CC", "CCC"]:
        raise RuntimeError("Protected row altered")
    if call(replay, .20) != ["CCC", "CC", "C"]:
        raise RuntimeError("Declared changed-candidate arm was rejected")
    if len(diag) != 2 or not cfg.USE_SECOND_LIST:
        raise RuntimeError("Control polluted diagnostics or failed flag restore")
    if replay.receipt(2)["status"] != "PASS":
        raise RuntimeError("Valid synthetic changed arm failed")
    if replay.receipt(3)["status"] != "HOLD":
        raise RuntimeError("Missing rows did not fail closed")
    bad, _, _ = scenario(buggy_closed=True)
    try:
        call(bad, 1.0)
    except RuntimeError:
        pass
    else:
        raise RuntimeError("A changed protected candidate order was accepted")
    exact, _, _ = scenario(changed_arm=False)
    try:
        call(exact, .20)
    except RuntimeError:
        pass
    else:
        raise RuntimeError("Exact-control mode accepted a changed open row")
    # A crash in the scientific control cannot leave the global flag disabled.
    cfg = SimpleNamespace(USE_SECOND_LIST=True, LIB_GATE=.90)
    def fail(*args):
        raise ValueError("synthetic original function failure")
    replay = ProtectedReplay(fail, cfg, [])
    try:
        call(replay, 1.0)
    except ValueError:
        pass
    else:
        raise RuntimeError("Scientific failure was swallowed")
    if not cfg.USE_SECOND_LIST:
        raise RuntimeError("Control failure changed the experiment flag")
    replay = ProtectedReplay(fail, cfg, [])
    try:
        call(replay, .20)
    except ValueError:
        pass
    if replay.receipt(1)["status"] != "HOLD":
        raise RuntimeError("Open scientific exception could qualify a receipt")
    for appended in (0, 2):
        cfg = SimpleNamespace(USE_SECOND_LIST=True, LIB_GATE=.90)
        diag = []
        def wrong_count(*args):
            n = 1 if args[6] >= cfg.LIB_GATE else appended
            diag.extend([{} for _ in range(n)])
            return ["C", "CC", "CCC"]
        replay = ProtectedReplay(wrong_count, cfg, diag)
        call(replay, 1.0)
        try:
            call(replay, .20)
        except RuntimeError:
            pass
        else:
            raise RuntimeError("Wrong open-row diagnostic count passed")
        if replay.receipt(2)["status"] != "HOLD":
            raise RuntimeError("Wrong open-row diagnostic count qualified")
    cfg = SimpleNamespace(USE_SECOND_LIST=True, LIB_GATE=.90)
    diag, shared = [], []
    def aliasing(*args):
        diag.append({})
        shared[:] = ["CCC", "CC", "C"] if cfg.USE_SECOND_LIST else ["C", "CC", "CCC"]
        return shared
    replay = ProtectedReplay(aliasing, cfg, diag)
    try:
        call(replay, 1.0)
    except RuntimeError:
        pass
    else:
        raise RuntimeError("Aliased mutable result hid a protected mismatch")
    print(json.dumps({"status": "PASS", "synthetic_only": True,
                      "checks": ["changed open candidate arm passes",
                                 "closed complete ordering preserved",
                                 "one diagnostic per real row",
                                 "flag restored after success and error",
                                 "missing coverage holds",
                                 "closed mutation holds",
                                 "exact-control open mutation holds",
                                 "scientific exception propagates",
                                 "open diagnostic count enforced",
                                 "mutable control snapshot preserved"]}, indent=2))


if __name__ == "__main__":
    run()
