# SPDX-License-Identifier: MIT
"""Render aggregate measured results; no data loading, model fitting or network.

Accept only the public aggregate schema, complete local execution and independently
verified result evidence. Individual query identities and predictions are neither
needed nor accepted. Fresh outputs preserve every existing chart and notebook.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_summary(path):
    if path.stat().st_size > 1_000_000:
        raise ValueError('aggregate summary is unexpectedly large')
    result = json.loads(path.read_text())
    if result['schema'] != 'CASMI_PUBLIC_TIE_NEUTRAL_HISTORICAL_BENCHMARK_V1':
        raise ValueError('unexpected summary schema')
    if result['execution']['exit_code'] != 0 or result['execution']['fit_calls'] != 4:
        raise ValueError('only completed four-fit benchmark results are supported')
    if result['independent_result_recomputation']['status'] != 'PASS':
        raise ValueError('independent aggregate recomputation must pass first')
    if result['official_score'] is not None or result['promotion_qualified'] is not False:
        raise ValueError('this renderer accepts historical development results only')
    if [s['simulation'] for s in result['summaries']] != [0, 1]:
        raise ValueError('two complete matched simulations are required')
    posthoc = result['posthoc_prediction_tie_sensitivity']
    if posthoc['independent_evidence_status'] != 'PASS' or [s['simulation'] for s in posthoc['summaries']] != [0, 1]:
        raise ValueError('separate reviewed post hoc tie sensitivity is required')
    for s in result['summaries']:
        if s['anonymous_observed_queries'] != 2965:
            raise ValueError('historical observed denominator must remain explicit')
        if s['wins'] + s['losses'] + s['ties'] != 2965:
            raise ValueError('incomplete paired query accounting')
        a, b = (s['arms'][n] for n in ('original', 'tie_neutral'))
        if abs((b['conditional_MRR25'] - a['conditional_MRR25']) - s['paired_delta_conditional_MRR25']) > 1e-14:
            raise ValueError('arm and paired metrics disagree')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--summary', type=Path, required=True)
    ap.add_argument('--png', type=Path, required=True)
    ap.add_argument('--svg', type=Path, required=True)
    args = ap.parse_args()
    if args.png.exists() or args.svg.exists() or args.png.resolve() == args.svg.resolve():
        raise FileExistsError('choose two new artifact paths')
    result = read_summary(args.summary)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    original, treatment, sensitivity = '#6A7C90', '#197F78', '#B16E3A'
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.spines.left': False,
                         'axes.labelcolor': '#26384A', 'text.color': '#26384A',
                         'xtick.color': '#526375', 'ytick.color': '#526375'})
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.8), gridspec_kw={'width_ratios': [1.12, 1]})
    fig.patch.set_facecolor('#FCFCF8')
    labels = ['Class 1 · secondary', 'Class 2 · primary']
    for i, s in enumerate(result['summaries']):
        a, b = (s['arms'][n] for n in ('original', 'tie_neutral'))
        y = 1 - i
        axes[0].plot([a['conditional_MRR25'], b['conditional_MRR25']], [y, y], color='#B4C9C4', lw=4)
        axes[0].scatter(a['conditional_MRR25'], y, color=original, s=105, zorder=3, label='Original ranks' if i == 0 else None)
        axes[0].scatter(b['conditional_MRR25'], y, color=treatment, s=105, zorder=4, label='Tie-neutral ranks' if i == 0 else None)
        axes[0].annotate(f"{a['conditional_MRR25']:.5f} → {b['conditional_MRR25']:.5f}",
                         (b['conditional_MRR25'], y), xytext=(0, 19), textcoords='offset points', ha='center', fontsize=10)
        axes[0].annotate(f"Top 1: {a['top1_count']:,} → {b['top1_count']:,} of 2,965",
                         (b['conditional_MRR25'], y), xytext=(0, -27), textcoords='offset points', ha='center', fontsize=10)
        delta = s['paired_delta_conditional_MRR25']
        low, high = s['query_CI95']
        axes[1].errorbar(delta, y + .08, xerr=[[delta - low], [high - delta]], fmt='o', color=treatment,
                         capsize=5, ms=7, elinewidth=2, label='Registered stable order' if i == 0 else None)
        p = result['posthoc_prediction_tie_sensitivity']['summaries'][i]
        pd = p['paired_delta_expected_MRR25']; pl, ph = p['paired5000query_bootstrap_CI95']
        axes[1].errorbar(pd, y - .08, xerr=[[pd - pl], [ph - pd]], fmt='s', color=sensitivity,
                         capsize=5, ms=6, elinewidth=2, label='Post hoc tie averaging' if i == 0 else None)
        axes[1].annotate(f"Δ {delta:+.5f} / {pd:+.5f}", (delta, y + .08), xytext=(0, 17), textcoords='offset points', ha='center', fontsize=10)
        axes[1].annotate(f"{s['wins']} wins · {s['losses']} losses · {s['ties']:,} ties",
                         (delta, y), xytext=(0, -27), textcoords='offset points', ha='center', fontsize=10)
    for ax in axes:
        ax.set_facecolor('#FCFCF8'); ax.set_ylim(-.55, 1.55)
        ax.set_yticks([1, 0], labels); ax.tick_params(axis='y', length=0)
        ax.grid(axis='x', alpha=.17); ax.set_axisbelow(True)
    axes[0].set_xlim(.78, .98); axes[0].set_xlabel('Observed-query MRR@25')
    axes[0].xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    axes[0].set_title('Matched two-fold OOF predictions', fontsize=12, pad=12)
    axes[0].legend(loc='upper left', frameon=False, fontsize=9)
    axes[1].set_xlim(-.002, .0085); axes[1].axvline(0, ls='--', color='#9DAAB5', lw=1)
    axes[1].set_xlabel('Paired MRR@25 change · query bootstrap 95% CI')
    axes[1].set_title('Check prediction ties, too', fontsize=12, pad=12)
    axes[1].legend(loc='upper left', frameon=False, fontsize=8)
    fig.suptitle('Equal evidence should receive equal rank features', x=.07, ha='left', fontsize=19, weight='bold')
    fig.text(.07, .9, 'CASMI historical development benchmark · 736,788 candidate rows · 4 new CPU fits', fontsize=11)
    fig.text(.07, .06, 'Both post hoc tie-averaged intervals include zero; the secondary registered interval is borderline.\n'
             'Historical development evidence; prior checkpoint sampling and native candidate deduplication remain unqualified. No competition score.', fontsize=9, color='#526375')
    fig.subplots_adjust(left=.14, right=.97, bottom=.24, top=.8, wspace=.48)
    with args.png.open('xb') as stream:
        fig.savefig(stream, format='png', dpi=180, facecolor=fig.get_facecolor())
    with args.svg.open('xb') as stream:
        fig.savefig(stream, format='svg', facecolor=fig.get_facecolor(), metadata={'Date': None})
    plt.close(fig)


if __name__ == '__main__':
    main()
