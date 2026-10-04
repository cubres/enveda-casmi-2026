# MIT License
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

"""Union exact ppm windows for multiple measured neutral-mass estimates.

This retrieval utility preserves an existing candidate set, such as the set
from a median precursor window and its empty-window fallback. It adds each
valid measured mass's own window. It does not rank or cap candidates.

Run the boundary checks with: python precursor_window_union.py --self-test
"""
from __future__ import annotations

import argparse
import bisect
import math
import numbers
from collections.abc import Iterable, Sequence


def union_precursor_windows(
    sorted_masses: Sequence[float],
    baseline_indices: Iterable[int],
    neutral_mass_estimates: Iterable[float],
    ppm: float = 10.0,
    *,
    check_mass_index: bool = False,
) -> tuple[int, ...]:
    """Return sorted, unique pool indices from baseline plus inclusive windows.

    ``sorted_masses`` must be finite, positive and sorted in ascending order.
    Validate a newly constructed index once with ``check_mass_index=True``;
    repeated queries can use the trusted index without a full linear scan.
    Baseline indices must address this same index. Nonfinite or nonpositive
    estimates are ignored. Ppm is a nonnegative finite tolerance.

    Supply actual neutral-mass estimates after an explicit adduct/charge
    conversion. This function does not interpret precursor m/z or ion labels.
    A subsequent candidate cap can change retention and needs its own audit.
    """
    ppm = float(ppm)
    if not math.isfinite(ppm) or ppm < 0:
        raise ValueError('ppm must be finite and nonnegative')
    size = len(sorted_masses)
    if check_mass_index:
        previous = -math.inf
        for value in sorted_masses:
            value = float(value)
            if not math.isfinite(value) or value <= 0 or value < previous:
                raise ValueError('mass index must be finite, positive and sorted')
            previous = value
    selected: set[int] = set()
    for index in baseline_indices:
        if isinstance(index, bool) or not isinstance(index, numbers.Integral):
            raise TypeError('baseline indices must be integers')
        if not 0 <= index < size:
            raise IndexError('baseline index is outside the mass index')
        selected.add(int(index))
    for center in neutral_mass_estimates:
        center = float(center)
        if not math.isfinite(center) or center <= 0:
            continue
        radius = center * ppm / 1_000_000.0
        left = bisect.bisect_left(sorted_masses, center - radius)
        right = bisect.bisect_right(sorted_masses, center + radius)
        selected.update(range(left, right))
    return tuple(sorted(selected))


def self_test() -> int:
    """Exercise inclusive boundaries, fallback retention and malformed inputs."""
    count = 0

    def equal(actual, expected):
        nonlocal count
        assert actual == expected, (actual, expected)
        count += 1

    def raises(kind, call):
        nonlocal count
        try:
            call()
        except kind:
            count += 1
        else:
            raise AssertionError(f'Expected {kind.__name__}')

    center = 400.0
    radius = center * 10.0 / 1_000_000.0
    index = [399.0, center-radius, center, center+radius, 401.0]
    equal(union_precursor_windows(index, [], [center], check_mass_index=True), (1, 2, 3))
    equal(union_precursor_windows(index, [0], [center]), (0, 1, 2, 3))
    equal(union_precursor_windows(index, [4, 4], [center, center]), (1, 2, 3, 4))
    equal(union_precursor_windows(index, [0], [math.nan, math.inf, -math.inf, 0, -1]), (0,))
    equal(union_precursor_windows(index, [], [400.0], ppm=0), (2,))
    equal(union_precursor_windows([400.0, 400.0], [], [400.0], ppm=0), (0, 1))
    equal(union_precursor_windows([], [], [400.0]), ())
    equal(union_precursor_windows([100.0, 200.0], [0], [200.0]), (0, 1))
    raises(ValueError, lambda: union_precursor_windows(index, [], [], ppm=-1))
    raises(ValueError, lambda: union_precursor_windows(index, [], [], ppm=math.nan))
    raises(IndexError, lambda: union_precursor_windows(index, [-1], []))
    raises(IndexError, lambda: union_precursor_windows(index, [len(index)], []))
    raises(TypeError, lambda: union_precursor_windows(index, [True], []))
    raises(TypeError, lambda: union_precursor_windows(index, [1.0], []))
    raises(ValueError, lambda: union_precursor_windows([200.0, 100.0], [], [], check_mass_index=True))
    raises(ValueError, lambda: union_precursor_windows([math.nan], [], [], check_mass_index=True))
    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        print(f'PASS: {self_test()} boundary and input checks')
    else:
        parser.print_help()
