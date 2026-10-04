# Native ranker routing

[The standalone module](../src/native_ranker_routing.py) verifies two caller-pinned native model files and routes one query's existing candidates. Below a frozen library-similarity gate it returns the arithmetic mean of two raw LambdaRank outputs. At or above the gate it returns the **exact score object** produced by the existing baseline callback. It does not sort scores, alter candidates, load a model, or evaluate ranking quality. The module and its 30 synthetic contract tests use only the Python standard library.

From the repository root, make `src` importable for the current shell and run the tests:

```sh
export PYTHONPATH=src
python -m unittest discover -s tests -p 'test_native_ranker_routing.py'
```

Use Python 3.12, as in the contracts workflow. The following example runs in that shell's Python session. Its native headers and callbacks are **synthetic fixtures**, not complete loadable LightGBM models; it requires no model files, data or LightGBM installation.

```python
import hashlib
from native_ranker_routing import BundleContract, route_query, verify_native_bundle

names = ("Column_0", "Column_1", "Column_2")
header = (
    "tree\nversion=v4\nnum_class=1\nnum_tree_per_iteration=1\n"
    "max_feature_idx=2\nobjective=lambdarank\n"
    "feature_names=Column_0 Column_1 Column_2\n\nTree=0\n"
).encode()
blobs = (header + b"synthetic-head-a\n", header + b"synthetic-head-b\n")
pipeline_id = hashlib.sha256(b"synthetic three-column pipeline").hexdigest()
version = "synthetic-runtime"
contract = BundleContract(
    feature_names=names,
    feature_pipeline_sha256=pipeline_id,
    head_sha256=tuple(hashlib.sha256(b).hexdigest() for b in blobs),
    runtime_version=version,
    trees_per_head=1,
    library_max_column=2,
    gate=0.90,  # Preserve this Python float; do not cast the threshold to float32.
)
bundle = verify_native_bundle(blobs, contract, runtime_version=version)
baseline_scores = [0.8, 0.8, 0.1]

def baseline_predict(features):
    return baseline_scores

def head_a(features, *, raw_score):
    assert raw_score is True
    return [-5.0, 9.0, 3.0]

def head_b(features, *, raw_score):
    assert raw_score is True
    return [1.0, 3.0, 1.0]

def score_query(library_max):
    features = [[0.0, 0.0, library_max] for _ in range(3)]
    return route_query(
        features, baseline_predict, (head_a, head_b), bundle=bundle,
        feature_names=names, feature_pipeline_sha256=pipeline_id,
        runtime_version=version, library_max_column=2, gate=0.90,
    )

weak = score_query(0.2)
assert weak.source == "native_raw_mean" and weak.scores == (-2.0, 6.0, 2.0)
strong = score_query(0.95)
assert not strong.gate_open and strong.scores is baseline_scores
```

For real use, freeze the expected contract **independently of the incoming files**, before prediction. Computing expected hashes from whatever files arrive, as the synthetic example does, checks mechanics but provides no independent drift detection. Keep models, datasets and private run manifests outside this repository.

`verify_native_bundle` checks both complete byte hashes, exact caller-reported runtime version, UTF-8 headers, native format `v4`, scalar `lambdarank`, ordered feature names and contiguous tree indices. It does not parse every tree parameter or establish licensing, model safety, loadability or numerical equivalence. Construct each real predictor from its corresponding verified bytes in the same head order; for LightGBM, its bound `Booster.predict` method accepts the router's `raw_score=True` keyword. Supply the actual installed LightGBM version to both verifier and router. The existing baseline callback must return one finite probability in `[0, 1]` per input candidate.

The feature-pipeline SHA256 is a **caller-attested frozen identity**, not an inspection of the matrix. Bind ordered feature meanings, producer functions and constants, descriptor selection, upstream model assets and relevant dependency versions in a reproducible manifest. Generic `Column_i` names and matching dimensions cannot establish those meanings. If hashing Python AST dumps, pin the Python version and canonicalization method too. The integration must derive the observed identity from the actual producers and bind callbacks to the verified assets; merely repeating the expected strings cannot prove either fact.

`route_query` requires one nonempty rectangular feature matrix with the exact frozen width, finite scalar values and an exactly repeated library maximum in the declared column. Empty queries remain the caller's responsibility. Extra columns are rejected rather than sliced away. Gate and column changes are rejected. The router preserves the supplied matrix object when calling predictors; callbacks must preserve it themselves. Native failures propagate instead of silently changing the scoring policy.

The comparison uses the observed maximum and the literal Python gate without rounding. Float32 `0.90` represents approximately `0.8999999761581421`, so it is **below** the Python `0.90` gate and opens that gate. The adjacent float32 value above the threshold closes it. Finite similarity overshoots slightly above `1.0` are not clipped or rejected. Preserve the application's existing numeric representation and comparison policy.

Closed queries invoke only the baseline callback and retain its score object, allowing the caller to preserve existing sorting and tie behavior. Open queries invoke only the two native callbacks and return a tuple of raw means in candidate order, with no sigmoid, percentile conversion, sorting or implicit cap. To preserve a production ordering, keep its downstream sort and tie policy unchanged.

Passing these tests establishes routing mechanics, not model quality or deployment readiness. Weak-library Class-1 behavior needs separate evaluation. A production candidate cap changes both the available candidates and candidate-dependent features; an uncapped scorer comparison does not validate that pipeline. Popularity and forward-fusion stages can use score spacings, so replacing probabilities with raw ranking scores can change their results even when their code and weights stay fixed. Validate the complete intended pipeline and serving environment before making any score claim.
