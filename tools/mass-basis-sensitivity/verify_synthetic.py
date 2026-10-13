"""Original invented numerical controls; no dataset/reference records are read."""
import argparse
import copy
import csv
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

from mass_basis_sensitivity import BASIS_NAMES, CHANNELS, MassIndex, PROTON_MASS_DA, audit_basis, interpretation_window, load_mass_csv

checks = 0


def require(value, name):
    global checks
    if not value:
        raise RuntimeError(name)
    checks += 1


def refuses(call, name):
    try:
        call()
    except (ValueError, TypeError, OverflowError):
        require(True, name)
    else:
        raise RuntimeError("expected refusal: " + name)


def main():
    if sys.flags.optimize:
        raise RuntimeError("optimized verification is explicitly refused")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Fresh result directory; existing outputs are preserved")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir()
    began = time.process_time()
    oracle_windows = 0
    for label, (n, h, z) in CHANNELS.items():
        for value in (2.0, 100.0, 201.0072764665789, 801.0):
            for ppm in (0.0, 3.0, 10.0, 20.0):
                for basis in BASIS_NAMES:
                    row = interpretation_window(value, label, ppm, basis)
                    with localcontext() as context:
                        context.prec = 50
                        s, p, fraction = Decimal(str(value)), Decimal(str(PROTON_MASS_DA)), Decimal(str(ppm)) / Decimal(1_000_000)
                        scale = n if basis == "neutral_monomer_mass" else (1 if basis == "ion_total_mass" else abs(z))
                        shift = Decimal(0) if basis == "neutral_monomer_mass" else h * p
                        expected = [(scale * s * (Decimal(1) + sign * fraction) - shift) / n for sign in (-1, 0, 1)]
                    for name, target in zip(("lower_da", "center_da", "upper_da"), expected):
                        require(math.isclose(row[name], float(target), rel_tol=1e-14, abs_tol=3e-14), "independent high-precision affine oracle")
                    if row["status"] != "CONDITIONAL_NUMERICAL_WINDOW":
                        require(row["center_da"] <= 0, "held conversion must have nonpositive center")
                        continue
                    lower, upper = row["lower_da"], row["upper_da"]
                    fixture = sorted(x for x in [math.nextafter(lower, -math.inf), lower, lower, row["center_da"], upper, upper, math.nextafter(upper, math.inf)] if x > 0)
                    report = audit_basis(MassIndex(fixture), value, label, ppm)
                    actual = next(r for r in report["hypotheses"] if r["basis"] == basis)
                    direct = [i for i, x in enumerate(fixture) if lower <= x <= upper]
                    require(list(range(actual["source_row_start"], actual["source_row_stop_exclusive"])) == direct, "inclusive independent direct scan with duplicates/ULP neighbors")
                    require(report["mass_basis_qualification"] == "UNQUALIFIED" and not report["chemical_identity_or_basis_inferred"], "no basis qualification")
                    oracle_windows += 1
    # All pairwise source-position overlap calculations are checked by sets,
    # independently of the interval arithmetic used by the implementation.
    for label in CHANNELS:
        report = audit_basis(MassIndex([1., 99., 100., 100., 101., 199., 200., 201., 400., 800.]), 201., label, 5000.)
        by = {r["basis"]: r for r in report["hypotheses"]}
        for pair in report["pairwise_sensitivity"]:
            a, b = by[pair["lhs"]], by[pair["rhs"]]
            aset = set(range(a["source_row_start"], a["source_row_stop_exclusive"]))
            bset = set(range(b["source_row_start"], b["source_row_stop_exclusive"]))
            require(pair["intersection_row_count"] == len(aset & bset), "intersection oracle")
            require(pair["union_row_count"] == len(aset | bset), "union oracle")
            for field, expected in (("lhs_only_ranges", aset - bset), ("rhs_only_ranges", bset - aset)):
                unfolded = {i for lo, hi in pair[field] for i in range(lo, hi)}
                require(unfolded == expected, "difference-range oracle")
            require(pair["row_jaccard"] == (len(aset & bset) / len(aset | bset) if aset | bset else None), "Jaccard oracle")
    empty = audit_basis(MassIndex([]), 100., "[M+H]+", 10.)
    require(all(r["row_jaccard"] is None for r in empty["pairwise_sensitivity"]), "empty-union Jaccard unavailable")
    singly = audit_basis(MassIndex([98.,99.,100.,101.]), 100., "[M+H]+", 10.)
    require(singly["hypotheses"][1]["center_da"] == singly["hypotheses"][2]["center_da"] and singly["mass_basis_qualification"] == "UNQUALIFIED", "unit charge coincidence does not qualify basis")
    dimer = audit_basis(MassIndex([100.,200.]), 200., "[2M+H]+", 10.)
    require(dimer["hypotheses"][0]["center_da"] == 200. and dimer["hypotheses"][1]["center_da"] < 100., "neutral monomer versus dimer aggregate")
    lower_negative = interpretation_window(1.0072764665789 + 1e-6, "[M+H]+", 20., "ion_total_mass")
    require(lower_negative["center_da"] > 0 and lower_negative["lower_da"] < 0, "positive center can have negative lower bound")
    held = audit_basis(MassIndex([1.,2.,3.]), 1., "[M+3H]3+", 10.)
    require(held["hypotheses"][1]["status"].startswith("HOLD") and held["pairwise_sensitivity"][0]["row_jaccard"] is None, "held hypothesis has unavailable pairwise metric")
    original = [100.,100.,200.]
    before = copy.deepcopy(original)
    index = MassIndex(original)
    original[0] = 99.
    require(index.masses == tuple(before), "index detaches caller ownership")
    report = audit_basis(index, 100., "[M-H]-", 10., polarity="negative")
    require(report["channel"]["signed_charge"] == -1, "negative channel support")
    for value in (True, "100", None, -1., 0., float("nan"), float("inf")):
        refuses(lambda value=value: audit_basis(index, value, "[M+H]+", 10.), "invalid supplied scalar")
    for ppm in (True, "10", -1., 1_000_000., float("nan"), float("inf")):
        refuses(lambda ppm=ppm: audit_basis(index, 100., "[M+H]+", ppm), "invalid ppm")
    for masses in ([True], [float("nan")], [0.], [-1.], [200.,100.]):
        refuses(lambda masses=masses: MassIndex(masses), "invalid mass index")
    class MustNotConsume:
        def __iter__(self):
            raise RuntimeError("unbounded iterable was consumed")
    refuses(lambda: MassIndex(MustNotConsume()), "lazy iterable refused before consumption")
    refuses(lambda: MassIndex([1.] * 1_000_001), "row cap")
    refuses(lambda: audit_basis(index, 100., "[M+Na]+", 10.), "unsupported adduct")
    refuses(lambda: audit_basis(index, 100., "[M+H]+", 10., polarity="negative"), "polarity mismatch")
    class EqualToEveryBasis:
        def __eq__(self, other):
            return True
    refuses(lambda: interpretation_window(100., "[M+H]+", 10., EqualToEveryBasis()), "adversarial equality object is not a declared basis")
    refuses(lambda: interpretation_window(100., "[M+H]+", 10., None), "basis must be a declared string")
    refuses(lambda: interpretation_window(1.7e308, "[M+3H]3+", 20., "precursor_mz"), "overflow conversion")
    # Original tiny mass-only CSV; no real identifiers or source rows are used.
    csv_path = out / "invented-masses.csv"
    with csv_path.open("x", newline="") as stream:
        writer = csv.writer(stream);writer.writerow(["source_row_id", "neutral_mass_da"])
        writer.writerows(enumerate([98.,100.,100.,199.,200.,201.,400.]))
    loaded = load_mass_csv(csv_path)
    require(len(loaded.masses) == 7 and loaded.masses[1] == loaded.masses[2], "CSV preserves equal-mass rows")
    cli_report, cli_csv = out / "cli-report.json", out / "cli-windows.csv"
    command = [sys.executable,"-B",str(Path(__file__).with_name("mass_basis_sensitivity.py")),"--masses-csv",str(csv_path),"--value","201.0072764665789","--channel","[M+2H]2+","--ppm","10","--polarity","positive","--report",str(cli_report),"--windows-csv",str(cli_csv)]
    run = subprocess.run(command,capture_output=True,text=True,timeout=5)
    require(run.returncode == 0, "CLI numerical report and CSV")
    require(json.loads(cli_report.read_text())["mass_basis_qualification"] == "UNQUALIFIED", "CLI keeps unqualified basis")
    pin = hashlib.sha256(cli_report.read_bytes()).hexdigest()
    repeat = subprocess.run(command,capture_output=True,text=True,timeout=5)
    require(repeat.returncode != 0 and hashlib.sha256(cli_report.read_bytes()).hexdigest() == pin, "CLI exclusive output preserves existing report")
    result = {"status":"PASS_ORIGINAL_SYNTHETIC_CONTROLS_ONLY", "checks":checks, "high_precision_window_oracles":384,
              "positive_closed_window_direct_scan_oracles":oracle_windows,"source_row_set_pair_oracles":24,
              "python":sys.version.split()[0],"process_cpu_seconds":time.process_time()-began,
              "core_sha256":hashlib.sha256(Path(__file__).with_name("mass_basis_sensitivity.py").read_bytes()).hexdigest(),
              "real_candidate_table_or_reference_record_read":False,"basis_qualification":"UNQUALIFIED","model_or_official_score":None}
    with (out/"CONTROL_RECEIPT.json").open("x") as stream:json.dump(result,stream,indent=2,sort_keys=True);stream.write("\n")
    print(json.dumps(result,sort_keys=True))


if __name__ == "__main__":
    main()
