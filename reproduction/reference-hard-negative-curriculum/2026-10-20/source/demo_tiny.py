"""Invented mechanics example, no real data/model. SPDX-License-Identifier: Apache-2.0"""
import json
from curriculum_core import choose_canary, partition, select_anchor, sample_negative
from qualification import checked_headers


def main():
    # The fixture uses explicit invented identifier tokens; it makes no chemical claim.
    rows = [{"inchikey14": "SYNTHETIC_" + str(i), "canonical_group": "group_" + str(i)} for i in range(6)]
    rows[5]["inchikey14"] = rows[0]["inchikey14"]
    fingerprints = [0b1111, 0b1111, 0b1110, 0b110000, 0b10000000, 0b1011]
    pairs = []
    for candidate in (1, 2, 3, 5):
        a, b = fingerprints[0], fingerprints[candidate]
        pairs.append({"query_row": 0, "candidate_row": candidate, "signed_ppm": "0", "selected_ppm": "10",
                      "intersection_on_bits": (a & b).bit_count(), "union_on_bits": (a | b).bit_count(),
                      "query_on_bits": a.bit_count(), "candidate_on_bits": b.bit_count()})
    aliases, components, folds, evidence = partition(rows, [str(x) for x in fingerprints], pairs)
    kept, excluded = select_anchor(0, pairs, rows, fingerprints, aliases, folds)
    assert len(excluded) == 2 and {p["reason"] for p in excluded} == {
        "identical_fingerprint_target", "same_provided_connectivity"}
    assert len(kept) == 2 and {p["target_hamming_bits"] for p in kept} == {1, 6}
    assert evidence["source_pair_cross_fold_endpoints"] == 0
    assert evidence["exact_fingerprint_cross_fold_values"] == 0
    assert len(components) == 6  # Empty anchor4 is retained, rather than becoming a negative.
    # Sampler mechanics use an explicit invented training fold, not a real split override.
    invented_train = [dict(p, split="train") for p in kept]
    assert sample_negative(invented_train, 4, 2, 0) is None
    assert sample_negative(invented_train, 0, 0, 0)["candidate_row"] == 3
    assert sample_negative(invented_train, 0, 2, 7) == sample_negative(invented_train, 0, 2, 7)
    try:
        sample_negative(invented_train, 0, 2, 0, fold="validation")
    except ValueError:
        pass
    else:
        raise AssertionError("held-fold optimizer sampling must reject")
    # Metadata selection must include all treatment classes instead of merely
    # taking the first source rows. Real coverage remains a producer bit check.
    canary_metadata = pairs + [{"query_row": 2, "candidate_row": 3,
                               "intersection_on_bits": 0, "union_on_bits": 5}]
    chosen, selection = choose_canary(rows, canary_metadata, count=3)
    assert chosen == [0, 1, 2]
    assert selection["seeds"] == {"collision_anchor": 0, "nonempty_noncollision_anchor": 2, "empty_anchor": 1}
    # Failed/partial owning receipts reject before child/table contents can be
    # interpreted. No real completed-tree or wrapper PASS is fabricated here.
    for result in ({}, {"schema": "casmi-reference-curriculum-owned-result/2", "status": "FAILED_CONSUMED_UNQUALIFIED"}):
        try:
            checked_headers(result, {}, {}, "unused", "unused")
        except ValueError:
            pass
        else:
            raise AssertionError("unqualified retained tree must reject")
    print(json.dumps({"status": "PASS_INVENTED_MECHANICS_ONLY", "kept": kept, "excluded": excluded,
                      "split_evidence": evidence}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
