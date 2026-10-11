# SPDX-License-Identifier: MIT
"""Only invented numeric spectra. Prints a bounded benchmark and counterexamples."""
import json
import random
import time
from fragment_consensus import candidate_features


def run():
    duplicated = [{"mz":[100,100.005,150,200], "intensity":[100,81,100,100], "window":[40,300]}]
    sparse = candidate_features([100,150,200], duplicated)
    dense_ions = [40+i*.02 for i in range(1001)]
    dense_spectra = [{"mz":[42,47,53,58],"intensity":[1,1,1,1],"window":[40,60]}]
    dense = candidate_features(dense_ions, dense_spectra, abs_tol=.011, ppm=0)
    accidental = candidate_features(
        [100,150],
        [{"mz":[a,b],"intensity":[1,1],"window":[40,300]} for a,b in [(100,150),(110,160),(120,170)]]
    )
    rng = random.Random(20261011)
    spectra = [
        {"mz":sorted(rng.uniform(40,300) for _ in range(64)),
         "intensity":[rng.uniform(1,100) for _ in range(64)],"window":[40,300]}
        for _ in range(4)
    ]
    bank = [[rng.uniform(40,300) for _ in range(96)] for _ in range(32)]
    start_cpu, start_wall = time.process_time(), time.perf_counter()
    total_cells = 0
    for ions in bank:
        total_cells += candidate_features(ions,spectra)["work_cells"]
    seconds_cpu = time.process_time()-start_cpu
    seconds_wall = time.perf_counter()-start_wall
    return {
        "status":"INVENTED_CONTROLS_ONLY_NO_COMPETITION_EVALUATION",
        "duplicate_centroids":sparse,
        "dense_hypotheses":dense,
        "single_accidental_view":accidental,
        "benchmark":{
            "candidates":32,"views_per_candidate":4,"peaks_per_view":64,
            "ion_hypotheses_per_candidate":96,"total_dp_cells":total_cells,
            "cpu_seconds":seconds_cpu,"wall_seconds":seconds_wall,
            "maxrss_not_measured":True,
            "native_compatibility_and_runtime":"UNVERIFIED",
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, allow_nan=False))

