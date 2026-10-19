"""Display saved summary values only; no bootstrap/model/alpha execution.
SPDX-License-Identifier: Apache-2.0
"""
import json
from pathlib import Path


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    plt.rcParams['svg.fonttype']='none'
    plt.rcParams['svg.hashsalt']='casmi-v9-fixed90-10-local-effect-20261020'
    root = Path(__file__).absolute().parent
    result = json.loads((root/'PUBLIC_RESULT.json').read_text())
    delta = result['canonical_group_delta']
    low, high = result['bootstrap_group_delta_95pct']
    if not low < 0 < delta < high or result['official_score'] is not None:
        raise ValueError('This display is bound to the reported uncertain local result')
    fig = plt.figure(figsize=(10,6.4),facecolor='white',layout='constrained')
    grid = fig.add_gridspec(3,1,height_ratios=[2.3,1.2,.6])
    ax = fig.add_subplot(grid[0])
    ax.axvline(0,color='#263238',linewidth=1.4,linestyle='--',label='Zero difference')
    ax.errorbar([delta],[0],xerr=[[delta-low],[high-delta]],fmt='o',markersize=10,
                color='#176D9C',ecolor='#176D9C',elinewidth=3,capsize=9,capthick=2)
    ax.set_xlim(low-.00025,high+.00025)
    ax.set_ylim(-.55,.55)
    ax.set_yticks([0],['Fixed 90/10\nminus cached V6'])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value,_:f'{value:+.4f}'))
    ax.set_xlabel('Absolute change in canonical-group MRR@25',fontsize=12)
    ax.set_title('Fixed 90/10 blend: uncertain local estimate',fontsize=18,weight='bold',pad=20)
    ax.grid(axis='x',color='#DDE3E7',linewidth=.8)
    ax.set_axisbelow(True)
    for side in ('top','right','left'):
        ax.spines[side].set_visible(False)
    ax.text(.5,.96,f'Δ {delta:+.12f}   |   95% CI [{low:+.12f}, {high:+.12f}]',
            ha='center',va='top',transform=ax.transAxes,fontsize=10.5,color='#263238')
    table_ax = fig.add_subplot(grid[1]);table_ax.axis('off')
    values = [[f'{value:.16f}' for value in result[key]]
              for key in ('unconditional_query_MRR25','canonical_group_MRR25')]
    table = table_ax.table(cellText=values,rowLabels=['Query mean','Group mean'],
        colLabels=['Cached V6','Fixed 90/10'],cellLoc='center',rowLoc='center',
        colWidths=[.34,.34],loc='center')
    table.auto_set_font_size(False);table.set_fontsize(11);table.scale(1,1.8)
    for (row,col),cell in table.get_celld().items():
        cell.set_edgecolor('#DDE3E7')
        if row==0:
            cell.set_facecolor('#EAF2F7');cell.set_text_props(weight='bold')
    foot = fig.add_subplot(grid[2]);foot.axis('off')
    foot.text(.5,.7,'2,653 queries · 2,650 groups · predeclared fixed weights',ha='center',fontsize=11)
    foot.text(.5,.2,'Interval includes zero. Local result, not a Kaggle leaderboard score.\n'
              'CPU FP32 V9 versus cached CUDA FP16 V6; no isolated training-effect claim.',
              ha='center',va='center',fontsize=10,color='#46545D')
    target=root/'figures';target.mkdir(exist_ok=True)
    description=('Uncertain local fixed 90/10 group MRR difference. The 95% paired-group '
                 'interval includes zero. No official Kaggle score or native-serving qualification.')
    fig.savefig(target/'local_effect_size.svg',metadata={'Title':'Uncertain local fixed90/10 effect',
                'Description':description,'Creator':'cubres / prvsiyan; Matplotlib','Date':'2026-10-20'})
    fig.savefig(target/'local_effect_size.png',dpi=180,metadata={'Description':description})
    plt.close(fig)


if __name__=='__main__':
    main()
