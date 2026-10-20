"""Deterministic reference-only negative selection. SPDX-License-Identifier: Apache-2.0

No file/network/model calls. Similarity is target similarity, not MS evidence.
"""
import hashlib
from collections import Counter, defaultdict
from fractions import Fraction

SEED = "casmi-reference-hard-negatives/20261020/v1"
STAGES = ("separated", "intermediate", "confusable")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(values):
    return hashlib.sha256("\n".join(sorted(values)).encode("ascii")).hexdigest()


def choose_canary(rows, pairs, count=64):
    """Metadata-only selection; the producer must prove classes from real bits.

    Seeds are the smallest source-row collision anchor, smallest nonempty
    anchor with no stored collision, and smallest empty anchor. Fill with the
    smallest remaining source rows, then process sorted source-row order.
    """
    require(type(count) is int and 3 <= count <= len(rows), "canary size")
    by_query = defaultdict(list)
    for pair in pairs:
        by_query[int(pair["query_row"])].append(pair)
    collisions = sorted({int(p["query_row"]) for p in pairs
                         if int(p["intersection_on_bits"]) == int(p["union_on_bits"])})
    collision_set = set(collisions)
    noncollisions = [i for i in range(len(rows)) if by_query[i] and i not in collision_set]
    empty = [i for i in range(len(rows)) if not by_query[i]]
    require(collisions and noncollisions and empty, "three real source metadata classes required")
    seeds = {"collision_anchor": collisions[0], "nonempty_noncollision_anchor": noncollisions[0],
             "empty_anchor": empty[0]}
    selected = set(seeds.values())
    require(len(selected) == 3, "distinct canary seed classes")
    for index in range(len(rows)):
        if len(selected) == count:
            break
        selected.add(index)
    chosen = sorted(selected)
    require(len(chosen) == count and len(set(chosen)) == count, "distinct canary anchors")
    return chosen, {"selection_scope": "Frozen metadata only, not numerical coverage qualification",
                    "tie_rule": "Minimum source row per disjoint class; ascending remaining source-row fill; sorted execution",
                    "seeds": seeds, "chosen_anchor_rows": chosen}


class UnionFind:
    def __init__(self, size):
        self.parent = list(range(size))

    def find(self, row):
        while self.parent[row] != row:
            self.parent[row] = self.parent[self.parent[row]]
            row = self.parent[row]
        return row

    def union(self, left, right):
        left, right = self.find(left), self.find(right)
        if left != right:
            self.parent[max(left, right)] = min(left, right)


def partition(rows, fp_hashes, pairs):
    """Keep connectivity, canonical groups, exact FP targets AND pair edges in one fold.

    The first-block InChIKeys come from the qualified source export; this does
    not calculate chemistry or certify a new external spectrum mapping.
    """
    size = len(rows)
    identities = UnionFind(size)
    for values in ([r["inchikey14"] for r in rows],
                   [r["canonical_group"] for r in rows], fp_hashes):
        first = {}
        for index, value in enumerate(values):
            if value in first:
                identities.union(index, first[value])
            else:
                first[value] = index
    aliases = defaultdict(list)
    for index in range(size):
        aliases[identities.find(index)].append(index)
    alias_id = {}
    for members in aliases.values():
        value = digest([rows[i]["inchikey14"] + ":" + rows[i]["canonical_group"] + ":" + fp_hashes[i]
                        for i in members])
        for index in members:
            alias_id[index] = value
    components = UnionFind(size)
    for members in aliases.values():
        for index in members[1:]:
            components.union(members[0], index)
    for pair in pairs:
        components.union(int(pair["query_row"]), int(pair["candidate_row"]))
    members_by_component = defaultdict(list)
    for index in range(size):
        members_by_component[components.find(index)].append(index)
    component_id, split = {}, {}
    for members in members_by_component.values():
        value = digest([rows[i]["inchikey14"] for i in members])
        bucket = int(hashlib.sha256((SEED + ":" + value).encode("ascii")).hexdigest()[:16], 16) % 10
        fold = "validation" if bucket == 0 else "test" if bucket == 1 else "train"
        for index in members:
            component_id[index], split[index] = value, fold
    evidence = {"component_count": len(members_by_component),
                "component_size_histogram": dict(sorted(Counter(map(len, members_by_component.values())).items())),
                "largest_component_rows": max(map(len, members_by_component.values())),
                "identity_alias_classes": len(aliases),
                "identity_alias_size_histogram": dict(sorted(Counter(map(len, aliases.values())).items())),
                "fold_row_counts": dict(Counter(split.values())),
                "nominal_hash_buckets": {"train": 8, "validation": 1, "test": 1},
                "exact_80_10_10_row_balance_claim": False,
                "split_seed": SEED}
    for name, values in (("provided_connectivity", [r["inchikey14"] for r in rows]),
                         ("canonical_group", [r["canonical_group"] for r in rows]),
                         ("exact_fingerprint", fp_hashes),
                         ("identity_alias", [alias_id[i] for i in range(size)])):
        seen = defaultdict(set)
        for index, value in enumerate(values):
            seen[value].add(split[index])
        overlap = sum(len(folds) > 1 for folds in seen.values())
        require(overlap == 0, name + " crosses folds")
        evidence[name + "_cross_fold_values"] = overlap
    evidence["source_pair_cross_fold_endpoints"] = sum(
        split[int(p["query_row"])] != split[int(p["candidate_row"])] for p in pairs)
    require(evidence["source_pair_cross_fold_endpoints"] == 0, "pair crosses folds")
    return alias_id, component_id, split, evidence


def exact_pair(left, right):
    intersection, union = (left & right).bit_count(), (left | right).bit_count()
    return intersection, union, left.bit_count(), right.bit_count()


def select_anchor(query, source_pairs, rows, fingerprints, aliases, splits):
    """Every source edge receives one disposition; alias candidates get one representative.

    Integer arithmetic defines identity, bins, ranking and Hamming separation.
    Float strings in the atlas are not threshold tests.
    """
    kept, excluded, target_aliases = [], [], set()
    for pair in sorted(source_pairs, key=lambda p: int(p["candidate_row"])):
        candidate = int(pair["candidate_row"])
        inter, union, qa, ca = exact_pair(fingerprints[query], fingerprints[candidate])
        for name, value in (("intersection_on_bits", inter), ("union_on_bits", union),
                            ("query_on_bits", qa), ("candidate_on_bits", ca)):
            require(int(pair[name]) == value, "atlas integer mismatch " + name)
        require(splits[query] == splits[candidate], "negative crosses folds")
        reason = None
        if rows[query]["inchikey14"] == rows[candidate]["inchikey14"]:
            reason = "same_provided_connectivity"
        elif rows[query]["canonical_group"] == rows[candidate]["canonical_group"]:
            reason = "same_canonical_group"
        elif fingerprints[query] == fingerprints[candidate]:
            reason = "identical_fingerprint_target"
        elif aliases[query] == aliases[candidate]:
            reason = "transitively_equivalent_target_identity"
        elif aliases[candidate] in target_aliases:
            reason = "redundant_negative_target_alias"
        if reason:
            excluded.append({"query_row": query, "candidate_row": candidate, "reason": reason})
            continue
        require(union > inter and union > 0, "negative needs distinct nonempty target union")
        target_aliases.add(aliases[candidate])
        hardness = 0 if 4 * inter < union else 1 if 2 * inter < union else 2
        kept.append({"query_row": query, "candidate_row": candidate, "split": splits[query],
                     "hardness_bin": STAGES[hardness], "minimum_stage": hardness,
                     "intersection_on_bits": inter, "union_on_bits": union,
                     "query_on_bits": qa, "candidate_on_bits": ca,
                     "jaccard": format(inter / union, ".17g"),
                     "binary_cosine": format(inter / ((qa * ca) ** 0.5), ".17g") if qa and ca else "",
                     "target_hamming_bits": qa + ca - 2 * inter,
                     "signed_reference_ppm": pair["signed_ppm"], "selected_reference_ppm": pair["selected_ppm"],
                     "candidate_identity_alias": aliases[candidate]})
    kept.sort(key=lambda p: (-Fraction(p["intersection_on_bits"], p["union_on_bits"]), p["candidate_row"]))
    return kept, excluded


def sample_negative(negative_rows, anchor, stage, epoch, fold="train"):
    """One target-alias-uniform candidate; call only for a separately licensed positive.

    Empty means no eligible negative, never a synthetic label. Validation/test
    cannot be sampled as optimizer training by this helper.
    """
    require(type(anchor) is int and type(stage) is int and type(epoch) is int and
            anchor >= 0 and 0 <= stage < len(STAGES) and epoch >= 0, "sampler arguments")
    require(fold == "train", "optimizer sampler is train-only")
    candidates = sorted([p for p in negative_rows if int(p["query_row"]) == anchor and
                         p["split"] == "train" and int(p["minimum_stage"]) <= stage],
                        key=lambda p: int(p["candidate_row"]))
    if not candidates:
        return None
    token = f"{SEED}:{anchor}:{stage}:{epoch}".encode("ascii")
    index = int.from_bytes(hashlib.sha256(token).digest(), "big") % len(candidates)
    return candidates[index]
