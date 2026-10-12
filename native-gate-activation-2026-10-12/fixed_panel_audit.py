# SPDX-License-Identifier: MIT
"""Original read-only audit of a frozen panel and slot-preserving rank pairs.

No model, chemistry, labels or numerical scorer is executed. Actual experiment
inputs and outputs are private. Public examples must contain invented records.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


class AuditHold(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise AuditHold(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def hash_text(value):
    need(type(value) is str and len(value) == 64
         and all(c in "0123456789abcdef" for c in value), "HASH_FORMAT")
    return value


def permutation(value, n, code):
    need(type(value) is list and len(value) == n
         and all(type(x) is int for x in value)
         and sorted(value) == list(range(n)), code)
    return value


def pair_audit(record, expected_source, context=None, response=None):
    """Return aggregate structural counts; raw query identities never escape.

    Context binds a main-branch pair to its complete captured candidate list and
    fitted probabilities. Scalar response, when available, binds each incoming
    head position to the actual service result. Auxiliary pairs lacking captured
    candidate context remain explicitly unbound; they do not count as main pairs.
    """
    need(type(record) is dict and record.get("schema") ==
         "PRIVATE_F1_COMPLETE_GROUP_ICE_FALLBACK_V1", "PAIR_SCHEMA")
    need(record.get("source_sha256") == hash_text(expected_source), "PAIR_SOURCE")
    branch = record.get("query_branch")
    need(type(branch) is str and bool(branch), "PAIR_BRANCH")
    for name in ("candidate_order_sha256", "candidate_head_sha256",
                 "frozen_scores_sha256", "signals_sha256"):
        hash_text(record.get(name))
    need(record.get("features31_changed") is False and record.get("ranker_refit") is False
         and record.get("candidate_pool_changed") is False
         and record.get("official_score") is None, "PAIR_RECIPE_DRIFT")
    control, treatment = record.get("control_order"), record.get("treatment_order")
    need(type(control) is list and 1 <= len(control) <= 100_000, "PAIR_UNIVERSE")
    n = len(control)
    permutation(control, n, "CONTROL_PERMUTATION")
    permutation(treatment, n, "TREATMENT_PERMUTATION")
    top = record.get("top")
    need(type(top) is int and 1 <= top <= 100_000, "HEAD_BOUND")
    head = min(top, n)
    need(treatment[head:] == control[head:], "TAIL_CHANGED")
    groups = record.get("groups")
    need(type(groups) is list and 1 <= len(groups) <= head, "GROUP_COVERAGE")
    incoming = [None] * head
    used_members, formula_keys, allowed_slots = set(), set(), set()
    counts = dict(groups=0, declared_fallback_groups=0, changed_groups=0,
                  constant_noop_groups=0, control_preserved_groups=0,
                  changed_slots=0, head_rank_l1_distance=0, top1_changed=0,
                  scalar_bound_groups=0)
    for group in groups:
        need(type(group) is dict, "GROUP_SCHEMA")
        key, slots, members = group.get("formula"), group.get("slots"), group.get("members")
        need(key is None or type(key) is str, "GROUP_FORMULA")
        need(key not in formula_keys, "GROUP_SPLIT")
        formula_keys.add(key)
        need(type(slots) is list and bool(slots) and all(type(x) is int for x in slots)
             and slots == sorted(set(slots)) and all(0 <= x < head for x in slots), "GROUP_SLOTS")
        need(type(members) is list and len(members) == len(slots)
             and all(type(x) is int and 0 <= x < n for x in members)
             and len(set(members)) == len(members), "GROUP_MEMBERS")
        need(not used_members.intersection(members), "GROUP_MEMBER_REUSE")
        used_members.update(members)
        for slot, member in zip(slots, members):
            need(incoming[slot] is None, "GROUP_SLOT_REUSE")
            incoming[slot] = member
        old = [control[s] for s in slots]
        new = [treatment[s] for s in slots]
        need(sorted(old) == sorted(members), "CONTROL_GROUP_UNIVERSE")
        need(sorted(new) == sorted(members), "TREATMENT_GROUP_UNIVERSE")
        gl, ice = group.get("gl_finite"), group.get("ice_finite")
        need(type(gl) is int and type(ice) is int
             and 0 <= gl <= len(slots) and 0 <= ice <= len(slots), "EVIDENCE_COUNTS")
        complete_absent_gl = key is not None and len(slots) >= 2 and gl == 0 and ice == len(slots)
        status = group.get("status")
        need(status in ("CONTROL_PRESERVED", "ICE_CONSTANT_NOOP", "ICE_FALLBACK"), "GROUP_STATUS")
        changed = new != old
        need(type(group.get("changed")) is bool and group["changed"] == changed, "GROUP_CHANGED_FLAG")
        if status == "CONTROL_PRESERVED":
            need(not complete_absent_gl and not changed, "PRESERVED_GROUP_CHANGED")
            counts["control_preserved_groups"] += 1
        else:
            need(complete_absent_gl and old == members, "ABSENT_GL_CONTROL_PARITY")
            if status == "ICE_CONSTANT_NOOP":
                need(not changed, "NO_INFORMATION_CHANGED")
                counts["constant_noop_groups"] += 1
            else:
                revised = group.get("revised_members")
                need(type(revised) is list and all(type(x) is int for x in revised)
                     and revised == new, "REVISED_ORDER_DRIFT")
                allowed_slots.update(slots)
                counts["declared_fallback_groups"] += 1
                counts["changed_groups"] += int(changed)
        counts["groups"] += 1
    need(all(x is not None for x in incoming), "INCOMING_HEAD_INCOMPLETE")
    changed_slots = {i for i, (a, b) in enumerate(zip(control, treatment)) if a != b}
    need(changed_slots <= allowed_slots, "PROTECTED_SLOT_CHANGED")
    need(type(record.get("changed")) is bool and record["changed"] == bool(changed_slots), "PAIR_CHANGED_FLAG")
    counts["changed_slots"] = len(changed_slots)
    old_positions = {candidate: i for i, candidate in enumerate(control)}
    counts["head_rank_l1_distance"] = sum(abs(i - old_positions[c]) for i, c in enumerate(treatment[:head]))
    counts["top1_changed"] = int(control[0] != treatment[0])
    if context is not None:
        need(context.get("query_id") == branch, "CONTEXT_BRANCH")
        rank = context.get("rank_capture")
        need(type(rank) is dict, "CONTEXT_RANK_MISSING")
        candidates = rank.get("candidates")
        need(type(candidates) is list and len(candidates) == n, "CONTEXT_UNIVERSE")
        smiles, formulas = [], []
        for i, candidate in enumerate(candidates):
            need(type(candidate) is dict and type(candidate.get("ordinal")) is int
                 and candidate["ordinal"] == i
                 and type(candidate.get("smiles")) is str and bool(candidate["smiles"]), "CONTEXT_ORDER")
            smiles.append(candidate["smiles"])
            formulas.append(candidate.get("formula"))
        probabilities = rank.get("fitted_control_probabilities")
        need(type(probabilities) is list and len(probabilities) == n
             and all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1
                     for x in probabilities), "CONTEXT_PROBABILITIES")
        need(digest(smiles) == record["candidate_order_sha256"]
             and digest([smiles[i] for i in incoming]) == record["candidate_head_sha256"], "CONTEXT_CANDIDATE_HASH")
        need(digest([float(x) for x in probabilities]) == record["frozen_scores_sha256"], "CONTEXT_BASE_HASH")
        for group in groups:
            need(all(formulas[i] == group["formula"] for i in group["members"]), "CONTEXT_FORMULA")
    if response is not None:
        need(context is not None and response.get("id") == branch and "error" not in response,
             "RESPONSE_BRANCH")
        arrays = {}
        for name in ("iceberg", "glacier"):
            values = response.get(name)
            need(type(values) is list and len(values) == head, "RESPONSE_HEAD_SIZE")
            need(all(v is None or type(v) in (int, float) and math.isfinite(v) for v in values),
                 "RESPONSE_NONFINITE_OR_NONNUMERIC")
            full = [None] * n
            for member, value in zip(incoming, values):
                full[member] = None if value is None else float(value)
            arrays[name] = full
        need(digest(arrays) == record["signals_sha256"], "RESPONSE_SIGNAL_HASH")
        for group in groups:
            members = group["members"]
            gl = sum(arrays["glacier"][i] is not None for i in members)
            ice = [arrays["iceberg"][i] for i in members]
            need(gl == group["gl_finite"] and sum(v is not None for v in ice) == group["ice_finite"],
                 "RESPONSE_GROUP_COUNTS")
            if group["status"] in ("ICE_CONSTANT_NOOP", "ICE_FALLBACK"):
                # This reader validates evidence gates, not the floating-point scorer.
                # Exact constants can be decided without reproducing NumPy variance.
                constant = len(set(ice)) == 1
                if constant:
                    need(group["status"] == "ICE_CONSTANT_NOOP", "CONSTANT_ICE_FALLBACK")
                elif group["status"] == "ICE_CONSTANT_NOOP":
                    mean = math.fsum(ice) / len(ice)
                    spread = math.sqrt(math.fsum((v - mean) ** 2 for v in ice) / len(ice))
                    need(spread <= 1e-12, "INFORMATIVE_ICE_NOOP")
            counts["scalar_bound_groups"] += 1
    counts["context_bound"] = int(context is not None)
    counts["scalar_bound"] = int(response is not None)
    return counts


def panel_audit(panel, completion, query_records, pair_records, expected_source,
                expected_count=16, scalar_responses=None):
    """Audit the entire preselected panel; missing pairs remain explicit absences."""
    need(type(expected_count) is int and 1 <= expected_count <= 32, "PANEL_COUNT")
    need(panel.get("schema") == "ENVEDA_PRIVATE_NATIVE_PANEL_V1"
         and completion.get("schema") == "ENVEDA_PRIVATE_NATIVE_CAPTURE_COMPLETE_V1", "PANEL_SCHEMA")
    all_ids, selected = panel.get("all_query_order"), panel.get("selected_capture_order")
    need(type(all_ids) is list and all(type(x) is str and x for x in all_ids)
         and len(set(all_ids)) == len(all_ids), "PANEL_ROSTER")
    need(type(selected) is list and len(selected) == expected_count
         and selected == all_ids[:expected_count], "PANEL_SELECTION_CHANGED")
    roster = panel.get("all_query_roster")
    need(type(roster) is list and len(roster) == len(all_ids)
         and all(type(r) is dict and r.get("query_id") == identity
                 and type(r.get("spectrum_order")) is list
                 and all(type(s) is str and s for s in r["spectrum_order"])
                 and type(r.get("spectrum_count")) is int
                 and r["spectrum_count"] == len(r["spectrum_order"])
                 for r, identity in zip(roster, all_ids)), "PANEL_SPECTRUM_ROSTER")
    need(completion.get("panel_sha256") == digest(panel), "PANEL_HASH")
    need(completion.get("query_truth_labels_loaded") is False
         and completion.get("original_training_reference_labels_used") is True
         and completion.get("official_score") is None, "PANEL_SCOPE")
    need(all(completion.get(k) is False for k in ("candidate_generation_changed", "features_changed",
             "ranker_refitted_for_intervention")), "PANEL_RECIPE_DRIFT")
    records = completion.get("query_records")
    need(type(records) is list and [r.get("query_id") for r in records] == selected
         and len(query_records) == expected_count, "PANEL_COMPLETION_COHORT")
    lookup = {}
    for index, (meta, query) in enumerate(zip(records, query_records)):
        need(meta.get("path") == "PRIVATE_QUERY_%03d.json" % index
             and meta.get("sha256") == digest(query)
             and query.get("query_id") == selected[index]
             and query.get("panel_sha256") == digest(panel)
             and query.get("capture_status") == meta.get("status")
             and meta.get("status") in ("COMPLETE", "NO_NATIVE_CANDIDATE_SCORES"), "QUERY_BINDING")
        need((query.get("rank_capture") is not None) == (meta["status"] == "COMPLETE"), "QUERY_STATUS")
        spectra = query.get("spectra")
        need(type(spectra) is list and len(spectra) == roster[index]["spectrum_count"]
             and all(type(s) is dict and s.get("spectrum_id") == identity
                     and type(s.get("view_ordinal")) is int and s["view_ordinal"] == ordinal
                     for ordinal, (s, identity) in enumerate(zip(spectra, roster[index]["spectrum_order"]))),
             "QUERY_SPECTRUM_ORDER")
        lookup[selected[index]] = query
    need(scalar_responses is None or type(scalar_responses) is dict
         and set(scalar_responses) <= set(selected), "RESPONSE_COHORT")
    need(type(pair_records) is list and len(pair_records) <= 4096, "PAIR_COUNT_LIMIT")
    totals = dict(fixed_panel_size=expected_count, queries_with_rank_records=0,
                  main_pairs=0, auxiliary_pairs=0, unselected_pairs=0,
                  no_main_pair_queries=0, groups=0, declared_fallback_groups=0,
                  changed_groups=0, constant_noop_groups=0, control_preserved_groups=0,
                  changed_slots=0, head_rank_l1_distance=0, top1_changed=0,
                  scalar_bound_groups=0, scalar_bound_main_pairs=0)
    totals["queries_with_rank_records"] = sum(q["rank_capture"] is not None for q in query_records)
    seen = set()
    for record in pair_records:
        branch = record.get("query_branch")
        need(type(branch) is str and branch not in seen, "PAIR_BRANCH_DUPLICATE")
        seen.add(branch)
        if branch in lookup:
            response = (scalar_responses or {}).get(branch)
            counts = pair_audit(record, expected_source, lookup[branch], response)
            totals["main_pairs"] += 1
            totals["scalar_bound_main_pairs"] += counts["scalar_bound"]
            for key in ("groups", "declared_fallback_groups", "changed_groups", "constant_noop_groups",
                        "control_preserved_groups", "changed_slots", "head_rank_l1_distance", "top1_changed",
                        "scalar_bound_groups"):
                totals[key] += counts[key]
        elif branch.endswith(":tier") and branch[:-5] in lookup:
            pair_audit(record, expected_source)
            totals["auxiliary_pairs"] += 1
        else:
            need(branch in all_ids or branch.endswith(":tier") and branch[:-5] in all_ids,
                 "PAIR_UNKNOWN_QUERY")
            pair_audit(record, expected_source)
            totals["unselected_pairs"] += 1
    totals["no_main_pair_queries"] = expected_count - totals["main_pairs"]
    need(not scalar_responses or set(scalar_responses) <= seen, "RESPONSE_WITHOUT_PAIR")
    return {"qualification": "PASS_FIXED_PANEL_STRUCTURAL_AUDIT_ONLY", "counts": totals,
            "scope": "Source-bound same-call fusion pairs before final-list processing; no final-control rerun, correctness, OOF or score.",
            "scalar_evidence": "ALL_MAIN_PAIRS_BOUND" if totals["main_pairs"] and
            totals["scalar_bound_main_pairs"] == totals["main_pairs"] else "PARTIAL_OR_UNMEASURED",
            "auxiliary_context": "STRUCTURAL_ONLY_NO_CAPTURED_TIER_CANDIDATE_CONTEXT",
            "missing_main_pairs": "ABSENCE_OF_CAPTURED_FUSION_NOT_PROOF_OF_NO_ELIGIBLE_EVIDENCE",
            "real_results_publication": False, "official_score": None}


def read_spec(base, spec, cap):
    need(type(spec) is dict and type(spec.get("name")) is str
         and Path(spec["name"]).name == spec["name"], "FILE_NAME")
    path = base / spec["name"]
    need(path.is_file() and not path.is_symlink() and type(spec.get("bytes")) is int
         and 0 < spec["bytes"] <= cap and path.stat().st_size == spec["bytes"], "FILE_SIZE_OR_LINK")
    raw = path.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == hash_text(spec.get("sha256")), "FILE_HASH")
    def bad_constant(_):
        raise AuditHold("NONSTANDARD_JSON_NUMBER")
    def unique_keys(items):
        result = {}
        for k, value in items:
            need(k not in result, "JSON_DUPLICATE_KEY")
            result[k] = value
        return result
    return json.loads(raw, parse_constant=bad_constant, object_pairs_hook=unique_keys)


def manifest_audit(manifest, base):
    need(manifest.get("schema") == "FIXED_PANEL_CAPTURE_FILE_MANIFEST_V1", "MANIFEST_SCHEMA")
    need(type(manifest.get("expected_count")) is int and 1 <= manifest["expected_count"] <= 32,
         "MANIFEST_PANEL_COUNT")
    need(type(manifest.get("queries")) is list and type(manifest.get("pairs")) is list,
         "MANIFEST_FILE_LISTS")
    specs = [manifest["panel"], manifest["completion"]] + manifest["queries"] + manifest["pairs"]
    responses_spec = manifest.get("scalar_responses")
    if responses_spec is not None:
        specs.append(responses_spec)
    need(all(type(s) is dict and type(s.get("bytes")) is int and s["bytes"] > 0 for s in specs),
         "MANIFEST_FILE_TYPES")
    need(len(specs) <= 4131 and sum(s["bytes"] for s in specs) <= 640 * 1024 * 1024,
         "MANIFEST_TOTAL_LIMIT")
    need(len({s["name"] for s in specs}) == len(specs), "MANIFEST_FILE_REUSE")
    need(manifest["panel"]["name"] == "PRIVATE_PANEL_REGISTRATION.json"
         and manifest["completion"]["name"] == "PRIVATE_PANEL_COMPLETION.json"
         and [s["name"] for s in manifest["queries"]] ==
         ["PRIVATE_QUERY_%03d.json" % i for i in range(manifest["expected_count"])], "MANIFEST_PANEL_FILES")
    need([s["name"] for s in manifest["pairs"]] ==
         ["PRIVATE_PAIR_%05d.json" % i for i in range(len(manifest["pairs"]))], "MANIFEST_PAIR_SEQUENCE")
    panel = read_spec(base, manifest["panel"], 5 * 1024 * 1024)
    completion = read_spec(base, manifest["completion"], 5 * 1024 * 1024)
    queries = [read_spec(base, s, 64 * 1024 * 1024) for s in manifest["queries"]]
    pairs = [read_spec(base, s, 4 * 1024 * 1024) for s in manifest["pairs"]]
    responses = None if responses_spec is None else read_spec(base, responses_spec, 64 * 1024 * 1024)
    result = panel_audit(panel, completion, queries, pairs,
                         hash_text(manifest["expected_pair_source_sha256"]), manifest["expected_count"], responses)
    result["file_bytes_sha256_verified"] = True
    result["producer_chronology_or_full_pair_directory_independently_authenticated"] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    need(args.input_dir.is_dir() and not args.input_dir.is_symlink(), "INPUT_DIRECTORY")
    need(args.output.name.startswith("PRIVATE_") and args.output.suffix == ".json", "PRIVATE_OUTPUT_NAME")
    need(args.manifest.is_file() and not args.manifest.is_symlink()
         and args.manifest.stat().st_size <= 1_000_000, "MANIFEST_FILE")
    manifest = json.loads(args.manifest.read_bytes())
    result = manifest_audit(manifest, args.input_dir)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(result["qualification"])


if __name__ == "__main__":
    main()
