"""Invented mass/bit arrays only: no molecules, model, spectra or real labels."""
import argparse
import json
import numpy as np

from packed_window_lab import PackingContract, aligned_window, pack_declared_bits, row_order_digest, score_window, topk_with_ties


def make_synthetic_demo(bitorder="big"):
    query = 100.0
    delta = query * (10.0 / 1e6)
    lower, upper = query - delta, query + delta
    masses = np.array([
        50.0, np.nextafter(lower, -np.inf), lower, lower,
        np.nextafter(lower, np.inf), query, np.nextafter(upper, -np.inf),
        upper, upper, np.nextafter(upper, np.inf), 150.0, 200.0,
    ], dtype=np.float64)
    tokens = tuple(f"SYN_{i:03d}" for i in range(len(masses)))
    bits = np.zeros((len(masses), 2216), dtype=np.uint8)
    for i in range(len(masses)):
        bits[i, i] = 1
        bits[i, 2049 + i] = 1
    contract = PackingContract("SYNTHETIC_ONLY", "invented-demo-v1", bitorder)
    packed = pack_declared_bits(bits, contract)
    logits = np.zeros(2216, dtype=np.float64)
    logits[5], logits[2049 + 5] = 4.0, 1.0
    logits[2048], logits[2215] = 999.0, -999.0
    return masses, tokens, bits, packed, logits, contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bitorder", choices=["big", "little"], default="big")
    parser.add_argument("--ppm", type=float, default=10.0)
    parser.add_argument("--mass", type=float, default=100.0)
    parser.add_argument("--mode", choices=["likelihood_order", "balanced_prospective"], default="likelihood_order")
    args = parser.parse_args()
    masses, tokens, _, packed, logits, contract = make_synthetic_demo(args.bitorder)
    interval, window_tokens, window_bits = aligned_window(
        masses, tokens, packed, contract, args.mass,
        expected_row_order_sha256=row_order_digest(tokens), ppm=args.ppm,
    )
    scores = score_window(window_bits, logits, contract, mode=args.mode)
    print(json.dumps({
        "scope": "CLEARLY_SYNTHETIC_MECHANICS_ONLY",
        "chemical_structures_spectra_or_trained_models": False,
        "external_producer_eligibility": "UNKNOWN",
        "interval": list(interval), "candidate_count": len(window_tokens),
        "mode": args.mode, "topk": topk_with_ties(scores, window_tokens, k=5),
        "scientific_or_competition_score": None,
    }, indent=2))


if __name__ == "__main__":
    main()
