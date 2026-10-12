"""MIT-licensed numerical example; the source ions are theoretical, not observed."""
from pathlib import Path
import json
import sys

from ion_index import BY_LABEL, open_release, query


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parent
    maps = open_release(root)
    neutral = maps[1]
    # A real numerical source row, chosen for an exact known round-trip demonstration.
    # This is not a competition spectrum, molecule ID or positive ranking example.
    example_row = 123456
    channel = BY_LABEL["[M+2H]2+"]
    mz = float(channel.precursor_mz(neutral[example_row]))
    answer = query(maps, mz, channel.label, ppm=10.0,
                   tolerance_basis="precursor_mz", polarity="positive")
    assert answer["source_row_start"] <= example_row < answer["source_row_stop_exclusive"]
    answer["example_source_row_included"] = True
    answer["first_source_rows"] = list(range(answer["source_row_start"],
                                           min(answer["source_row_stop_exclusive"],
                                               answer["source_row_start"] + 10)))
    print(json.dumps(answer, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
