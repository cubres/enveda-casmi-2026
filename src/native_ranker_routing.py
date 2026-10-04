# MIT License
#
# Copyright (c) 2026 cubres
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Mechanics for one query's gated, two-head native ranker; stdlib only.

This module verifies caller-pinned native bytes and routes callbacks. It neither
loads nor executes a model, finds files, changes candidates, sorts predictions,
nor measures quality. Callers must construct each native predictor from its
corresponding verified bytes. A callback cannot itself prove model provenance.
Feature-pipeline hashes are caller-attested identifiers: generic Column_i names
and equal dimensions alone do not prove that feature meanings match.
"""

from dataclasses import dataclass
import hashlib
import math
from numbers import Real
import re
from typing import Any, Callable, Sequence


def _sha(value: str) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


@dataclass(frozen=True)
class BundleContract:
    """Caller-frozen identity; feature order, hashes and runtime are exact."""

    feature_names: tuple[str, ...]
    feature_pipeline_sha256: str
    head_sha256: tuple[str, str]
    runtime_version: str
    trees_per_head: int
    library_max_column: int
    gate: float

    def __post_init__(self) -> None:
        if (not isinstance(self.feature_names, tuple) or not self.feature_names
                or any(not isinstance(n, str) or not n or any(c.isspace() for c in n)
                       for n in self.feature_names)
                or len(set(self.feature_names)) != len(self.feature_names)):
            raise ValueError("feature names must be unique, ordered, nonempty tokens")
        if not _sha(self.feature_pipeline_sha256):
            raise ValueError("feature pipeline requires a lowercase SHA256")
        if (not isinstance(self.head_sha256, tuple) or len(self.head_sha256) != 2
                or any(not _sha(h) for h in self.head_sha256)):
            raise ValueError("exactly two ordered head SHA256 pins are required")
        if not isinstance(self.runtime_version, str) or not self.runtime_version:
            raise ValueError("an exact runtime version is required")
        if (isinstance(self.trees_per_head, bool)
                or not isinstance(self.trees_per_head, int) or self.trees_per_head <= 0):
            raise ValueError("tree count must be a positive integer")
        if (isinstance(self.library_max_column, bool)
                or not isinstance(self.library_max_column, int)
                or not 0 <= self.library_max_column < len(self.feature_names)):
            raise ValueError("library maximum column must be pinned within the schema")
        if type(self.gate) is not float or not math.isfinite(self.gate) or not 0.0 <= self.gate <= 1.0:
            raise ValueError("gate must be a pinned finite Python float in [0, 1]")


@dataclass(frozen=True)
class VerifiedBundle:
    """Result of native byte/header checks; no model construction is implied."""

    contract: BundleContract


def verify_native_bundle(
    blobs: Sequence[bytes], contract: BundleContract, *, runtime_version: str
) -> VerifiedBundle:
    """Check both complete native text files before any model construction.

    Requires LightGBM native format v4, scalar LambdaRank, exact feature order,
    contiguous tree indices, caller-pinned bytes and exact runtime version.
    Hashes establish identity, not licensing, safety or prediction equivalence.
    """
    if runtime_version != contract.runtime_version:
        raise ValueError("runtime version drift")
    if len(blobs) != 2:
        raise ValueError("exactly two native blobs are required")
    for index, (blob, expected_sha) in enumerate(zip(blobs, contract.head_sha256)):
        if not isinstance(blob, bytes) or hashlib.sha256(blob).hexdigest() != expected_sha:
            raise ValueError(f"native head {index} byte hash drift")
        try:
            lines = blob.decode("utf-8", errors="strict").splitlines()
        except UnicodeError as exc:
            raise ValueError("native model must be UTF-8 text") from exc
        if not lines or lines[0] != "tree":
            raise ValueError("unsupported native file header")
        fields: dict[str, str] = {}
        for line in lines[1:]:
            if line.startswith("Tree="):
                break
            if "=" in line:
                key, value = line.split("=", 1)
                if key in fields:
                    raise ValueError("duplicate native header field")
                fields[key] = value
        expected_fields = {
            "version": "v4", "num_class": "1", "num_tree_per_iteration": "1",
            "objective": "lambdarank", "max_feature_idx": str(len(contract.feature_names) - 1),
            "feature_names": " ".join(contract.feature_names),
        }
        if any(fields.get(k) != v for k, v in expected_fields.items()):
            raise ValueError("native objective, format or feature schema drift")
        trees = [line for line in lines if line.startswith("Tree=")]
        if trees != [f"Tree={i}" for i in range(contract.trees_per_head)]:
            raise ValueError("native tree count or order drift")
    return VerifiedBundle(contract)


def _number(value: Any, message: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(message)
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(message) from exc
    if not math.isfinite(result):
        raise ValueError(message)
    return result


def _score_vector(values: Any, count: int, *, probability: bool = False) -> tuple[float, ...]:
    try:
        if len(values) != count:
            raise ValueError("prediction length differs from candidate count")
        scores = tuple(_number(v, "predictions must be finite scalar numbers") for v in values)
    except TypeError as exc:
        raise ValueError("predictions must be a one-dimensional vector") from exc
    if probability and any(v < 0.0 or v > 1.0 for v in scores):
        raise ValueError("baseline must return probabilities in [0, 1]")
    return scores


@dataclass(frozen=True)
class RoutedScores:
    """Scores remain in input candidate order; no calibrated weak probability."""

    scores: Any
    source: str
    gate_open: bool
    library_max: float


def route_query(
    features: Sequence[Sequence[Real]],
    baseline_predict: Callable[[Any], Any],
    native_predictors: Sequence[Callable[..., Any]],
    *,
    bundle: VerifiedBundle,
    feature_names: Sequence[str],
    feature_pipeline_sha256: str,
    runtime_version: str,
    library_max_column: int,
    gate: float,
) -> RoutedScores:
    """Use two raw heads below the literal gate; preserve baseline otherwise.

    One nonempty candidate list only. All rows must have the exact declared
    width and the same finite library maximum; inputs are never rounded, sliced
    or mutated. For a closed gate, only baseline_predict runs and its exact
    returned score object is retained, allowing the existing downstream sort
    and tie behavior. For an open gate, only two native callbacks run, each
    called with raw_score=True. Return their arithmetic mean in candidate order.

    The supplied pipeline identity must bind actual feature producers and
    dependencies upstream. This function cannot verify that caller attestation.
    Downstream transformations of score spacings require separate validation.
    """
    if not isinstance(bundle, VerifiedBundle):
        raise ValueError("a verified native bundle is required")
    contract = bundle.contract
    if (tuple(feature_names) != contract.feature_names
            or feature_pipeline_sha256 != contract.feature_pipeline_sha256):
        raise ValueError("feature pipeline or order drift")
    if runtime_version != contract.runtime_version:
        raise ValueError("runtime version drift")
    width = len(contract.feature_names)
    if (isinstance(library_max_column, bool) or not isinstance(library_max_column, int)
            or not 0 <= library_max_column < width):
        raise ValueError("library maximum column is outside the schema")
    threshold = _number(gate, "gate must be finite")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("gate must be in [0, 1]")
    if library_max_column != contract.library_max_column or threshold != contract.gate:
        raise ValueError("routing policy drift")
    try:
        count = len(features)
        if count == 0:
            raise ValueError("empty query must be handled by the caller")
        maximum = None
        for row in features:
            if len(row) != width:
                raise ValueError("feature width drift; truncation is forbidden")
            scalars = tuple(_number(v, "features must be finite scalar numbers") for v in row)
            observed = scalars[library_max_column]
            if maximum is None:
                maximum = observed
            elif observed != maximum:
                raise ValueError("rows do not share one exact query library maximum")
    except TypeError as exc:
        raise ValueError("features must be a rectangular scalar matrix") from exc
    if len(native_predictors) != 2 or any(not callable(f) for f in native_predictors):
        raise ValueError("exactly two ordered native predictors are required")
    if not callable(baseline_predict):
        raise ValueError("baseline predictor must be callable")
    assert maximum is not None
    if maximum >= threshold:
        unchanged = baseline_predict(features)
        _score_vector(unchanged, count, probability=True)
        return RoutedScores(unchanged, "baseline_probability", False, maximum)
    heads = [_score_vector(predict(features, raw_score=True), count)
             for predict in native_predictors]
    mean = tuple((a + b) / 2.0 for a, b in zip(*heads))
    _score_vector(mean, count)
    return RoutedScores(mean, "native_raw_mean", True, maximum)
