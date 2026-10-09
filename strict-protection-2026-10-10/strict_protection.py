"""Original fail-closed candidate-order audit contract. SPDX-License-Identifier: MIT.

This validates evidence supplied by a trusted source-bound integration. It does
not authenticate a remote run, execute a neutral core, read files, or authorize
publication/submission. No identifiers, candidates, paths or labels are emitted.
"""
from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence

_HEX = re.compile(r"[0-9a-f]{64}\Z")
_SCOPES = {"terminal_hook", "neutral_full_core"}


def _sha(value):
    return isinstance(value, str) and bool(_HEX.fullmatch(value))


def _finite_number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _sequence(value):
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _row(value, max_guesses):
    return (_sequence(value) and 1 <= len(value) <= max_guesses and
            all(isinstance(x, str) and x.strip() for x in value) and
            len(set(value)) == len(value))


def _bindings(value):
    return (isinstance(value, Mapping) and bool(value) and
            all(isinstance(k, str) and k and _sha(v) for k, v in value.items()))


def validate_protection(ids, submitted_rows, audit, *, expected_source_sha256,
                        lib_gate, required_scope="neutral_full_core",
                        historical_rows=None, require_historical_match=True,
                        expected_control_source_sha256=None,
                        expected_input_bindings=None, exact_control=False,
                        max_guesses=25):
    """Return a scalar receipt; every missing/malformed requirement holds.

    ``audit`` has schema_version=1, source_sha256, scope, ordered ids, rows mapping,
    molecules, gate_open, fired, not_fired, counterfactual_checked and errors=0.
    Each row record has finite lib_max, boolean gate_open/fired, complete output
    and counterfactual lists. Protection follows the library gate, never firing.

    Full-core scope also requires exact control-source and complete expected
    input/derived-state maps, matched to BOTH arm_input_bindings and
    control_input_bindings. The integration must prove those traces were produced
    by the pinned programs at actual loader/stage sites. Declarations alone do
    not establish execution. Terminal-only PASS cannot qualify the full core.
    Historical full protected ordering is required by default on every device.
    """
    problems = []
    counts = dict(rows=0, protected_rows=0, gate_open_rows=0, fired_rows=0,
                  protected_order_mismatches=0, historical_order_mismatches=0)

    def problem(code):
        if code not in problems:
            problems.append(code)

    scope = audit.get("scope") if isinstance(audit, Mapping) else None
    if not isinstance(exact_control, bool) or not isinstance(require_historical_match, bool):
        problem("control_flags_invalid")
    if (scope == "neutral_full_core" or required_scope == "neutral_full_core") and not require_historical_match:
        problem("full_core_historical_reference_required")
    if (not isinstance(required_scope, str) or required_scope not in _SCOPES or
            not isinstance(scope, str) or scope not in _SCOPES or scope != required_scope):
        problem("counterfactual_scope")
    if not _sha(expected_source_sha256):
        problem("expected_source_invalid")
    if not isinstance(audit, Mapping):
        problem("audit_schema")
        audit = {}
    if audit.get("source_sha256") != expected_source_sha256:
        problem("source_binding")
    if not _integer(audit.get("schema_version")) or audit.get("schema_version") != 1:
        problem("audit_schema")
    if not _integer(audit.get("errors")) or audit.get("errors") != 0:
        problem("scientific_errors")
    valid_gate = _finite_number(lib_gate)
    if not valid_gate:
        problem("library_gate_invalid")
    if not _integer(max_guesses) or max_guesses < 1:
        problem("max_guesses_invalid")
        max_guesses = 25
    valid_ids = (_sequence(ids) and bool(ids) and
                 all(isinstance(x, str) and x for x in ids) and len(set(ids)) == len(ids))
    if not valid_ids:
        problem("submission_identity")
        ids = []
    valid_submission = (_sequence(submitted_rows) and len(submitted_rows) == len(ids) and
                        all(_row(r, max_guesses) for r in submitted_rows))
    if not valid_submission:
        problem("submission_rows")
    count = len(ids)
    counts["rows"] = count
    if not _sequence(audit.get("ids")) or list(audit.get("ids", [])) != list(ids):
        problem("audit_identity_order")
    records = audit.get("rows")
    if not isinstance(records, Mapping):
        problem("audit_rows_schema")
        records = {}
    if set(records) != set(ids) or len(records) != count or count == 0:
        problem("audit_exact_coverage")
    for name in ("molecules", "counterfactual_checked"):
        if not _integer(audit.get(name)) or audit.get(name) != count:
            problem(name + "_coverage")
    valid_history = (_sequence(historical_rows) and len(historical_rows) == count and
                     all(_row(r, max_guesses) for r in historical_rows))
    if require_historical_match and not valid_history:
        problem("historical_reference_missing_or_malformed")
    for index, identifier in enumerate(ids):
        record = records.get(identifier)
        if not isinstance(record, Mapping):
            problem("row_record_missing_or_malformed")
            continue
        value = record.get("lib_max")
        if not _finite_number(value):
            problem("finite_library_gate_evidence")
            continue
        if not valid_gate:
            continue
        gate_open = value < lib_gate
        counts["gate_open_rows"] += int(gate_open)
        if not isinstance(record.get("gate_open"), bool) or record["gate_open"] != gate_open:
            problem("recorded_gate_disagrees")
        fired = record.get("fired")
        if not isinstance(fired, bool):
            problem("fired_schema")
            fired = False
        counts["fired_rows"] += int(fired)
        if fired and not gate_open:
            problem("fired_outside_open_gate")
        output, control = record.get("output"), record.get("counterfactual")
        if not _row(output, max_guesses) or not _row(control, max_guesses):
            problem("complete_output_or_counterfactual_missing")
            continue
        # Snapshot logical lists; no prefix/truncated hash or top-1 comparison.
        output, control = tuple(output), tuple(control)
        if not valid_submission or output != tuple(submitted_rows[index]):
            problem("audit_output_disagrees_with_submission")
        protected = exact_control or not gate_open
        if protected:
            counts["protected_rows"] += 1
            if output != control:
                counts["protected_order_mismatches"] += 1
                problem("protected_complete_order_changed")
            if valid_history and output != tuple(historical_rows[index]):
                counts["historical_order_mismatches"] += 1
                problem("protected_historical_complete_order_changed")
    if not counts["protected_rows"]:
        problem("no_protected_coverage")
    expected_counts = {"gate_open": counts["gate_open_rows"], "fired": counts["fired_rows"],
                       "not_fired": count - counts["fired_rows"]}
    for name, expected in expected_counts.items():
        if not _integer(audit.get(name)) or audit.get(name) != expected:
            problem(name + "_count_inconsistent")
    full_core_contract = False
    if scope == "neutral_full_core":
        if (not _sha(expected_control_source_sha256) or
                audit.get("control_source_sha256") != expected_control_source_sha256):
            problem("neutral_core_source_binding")
        if not _bindings(expected_input_bindings):
            problem("complete_expected_input_manifest_missing")
        else:
            for field in ("arm_input_bindings", "control_input_bindings"):
                if not _bindings(audit.get(field)) or dict(audit[field]) != dict(expected_input_bindings):
                    problem(field + "_incomplete_or_changed")
        full_core_contract = not problems
    status = "HOLD" if problems else ("PASS_NEUTRAL_CORE_CONTRACT" if full_core_contract
                                      else "PASS_TERMINAL_HOOK_ONLY")
    return dict(protocol="strict-protected-complete-order-v1", status=status,
                counterfactual_scope=scope if isinstance(scope, str) and scope in _SCOPES else "invalid_or_missing",
                required_scope=required_scope if isinstance(required_scope, str) and required_scope in _SCOPES else "invalid",
                matched_full_core_contract=full_core_contract,
                historical_reference_required=bool(require_historical_match),
                exact_control=bool(exact_control), source_sha256=expected_source_sha256 if _sha(expected_source_sha256) else None,
                counts=counts, failures=problems, private_records_exported=False,
                remote_execution_authenticated=False, submission_authorized=False)
