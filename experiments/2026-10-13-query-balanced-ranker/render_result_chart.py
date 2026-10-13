# SPDX-License-Identifier: MIT
"""Render measured aggregate CASMI results without private rows or model fits."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def read_summary(path):
    if path.stat().st_size > 100_000:
        raise ValueError('expected a small public aggregate summary')
    result = json.loads(path.read_text())
    if result['schema'] != 'CASMI_PUBLIC_QUERY_BALANCED_HISTORICAL_SCREEN_V1':
        raise ValueError('unexpected summary schema')
    if result['execution']['exit_code'] != 0 or result['execution']['fit_calls'] != 4:
        raise ValueError('requires a completed four-fit screen')
    if result['independent_recomputation']['status'] != 'PASS':
        raise ValueError('requires genuine independent numeric recomputation')
    if result['official_score'] is not None or result['promotion_qualified'] is not False:
        raise ValueError('historical development evidence only')
    if [row['simulation'] for row in result['summaries']] != [0, 1]:
        raise ValueError('requires both complete simulations')
    for row in result['summaries']:
        if row['anonymous_queries'] != 2965 or row['wins'] + row['losses'] + row['ties'] != 2965:
            raise ValueError('paired query accounting is incomplete')
        a, b = (row['arms'][name]['conditional_expected_MRR25']
                for name in ('original', 'query_balanced'))
        delta = row['paired_delta_conditional_expected_MRR25']
        lo, hi = row['query_CI95']
        if abs((b - a) - delta) > 1e-14 or not lo <= delta <= hi:
            raise ValueError('inconsistent measured metrics')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--png', type=Path, required=True)
    parser.add_argument('--svg', type=Path, required=True)
    args = parser.parse_args()
    if args.png.exists() or args.svg.exists() or args.png.resolve() == args.svg.resolve():
        raise FileExistsError('choose two fresh output files')
    result = read_summary(args.summary)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator, FuncFormatter

    ink, muted, primary, secondary = '#26364A', '#657387', '#B94A49', '#8D7290'
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 11,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.spines.left': False, 'axes.labelcolor': ink, 'text.color': ink,
        'xtick.color': muted, 'ytick.color': muted,
        'svg.hashsalt': 'casmi-query-balanced-failure-v1',
    })
    fig, ax = plt.subplots(figsize=(10.6, 5.8))
    background = '#FCFCF8'
    fig.patch.set_facecolor(background)
    ax.set_facecolor(background)
    ax.axvspan(-15, 0, color=primary, alpha=.035)
    ax.axvline(0, color='#8392A3', linestyle='--', linewidth=1.1)
    for y, simulation, color in ((1, 1, primary), (0, 0, secondary)):
        row = result['summaries'][simulation]
        delta = row['paired_delta_conditional_expected_MRR25'] * 1000
        lo, hi = [value * 1000 for value in row['query_CI95']]
        ax.errorbar(delta, y, xerr=[[delta-lo], [hi-delta]], fmt='o', color=color,
                    capsize=6, markersize=10, elinewidth=2.7, zorder=3)
        ax.annotate(f'Δ {delta:+.2f}   95% CI [{lo:+.2f}, {hi:+.2f}]',
                    (delta, y), xytext=(0, 23), textcoords='offset points',
                    ha='center', fontsize=11, weight='bold', color=color)
        a, b = [row['arms'][name]['conditional_expected_MRR25']
                for name in ('original', 'query_balanced')]
        ax.annotate(f'MRR@25 {a:.5f} → {b:.5f}   ·   {row["wins"]} wins / {row["losses"]} losses',
                    (delta, y), xytext=(0, -31), textcoords='offset points',
                    ha='center', fontsize=10, color=muted)
    ax.set_xlim(-15, 4)
    ax.set_ylim(-.57, 1.55)
    ax.set_yticks([1, 0], ['Class 2\nprimary', 'Class 1\nsecondary'])
    ax.tick_params(axis='y', length=0, pad=13)
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f'{value:+.0f}' if value else '0'))
    ax.grid(axis='x', alpha=.16)
    ax.set_axisbelow(True)
    ax.set_xlabel('Paired change in expected MRR@25  × 10⁻³', labelpad=12)
    fig.suptitle('Giving each query equal weight did not help',
                 x=.065, y=.96, ha='left', fontsize=21, weight='bold')
    fig.text(.065, .875, 'Same features, folds and candidate pools · 4 new CPU fits · 2,965 historical queries', fontsize=11)
    fig.text(.065, .06,
             'Intervals use 5,000 paired query bootstrap samples; exact score ties are averaged uniformly.\n'
             'Reused development data; checkpoint-selection exposure is unknown. No official score or model promotion.',
             fontsize=9, color=muted)
    fig.subplots_adjust(left=.18, right=.96, top=.79, bottom=.23)
    with args.png.open('xb') as stream:
        fig.savefig(stream, format='png', dpi=180, facecolor=background)
    with args.svg.open('xb') as stream:
        fig.savefig(stream, format='svg', facecolor=background, metadata={'Date': None})
    plt.close(fig)


if __name__ == '__main__':
    main()
