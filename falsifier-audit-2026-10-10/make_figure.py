"""Plot the published scalar table only. SPDX-License-Identifier: MIT."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser=argparse.ArgumentParser()
parser.add_argument('--output',default='falsifier-evidence.svg')
args=parser.parse_args()
source=Path(__file__).parent/'PUBLIC_RESULTS.json'
rows=json.loads(source.read_text())['falsifier']['c2']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none','svg.hashsalt':'enveda-falsifier-oct10'})
fig,ax=plt.subplots(figsize=(11.3,4.2),layout='constrained')
fig.patch.set_facecolor('#101827');ax.set_facecolor('#101827')
colors=['#6bd4c6','#efbb6e','#8ea9df']
for i,(row,color) in enumerate(zip(rows,colors)):
 y=2-i;lo,hi=row['percentile_interval'];value=row['mean_delta']
 ax.plot([lo,hi],[y,y],color=color,linewidth=4,solid_capstyle='round')
 ax.scatter([value],[y],s=92,color=color,edgecolor='#101827',linewidth=1.5,zorder=3)
 ax.text(.061,y,f"n={row['n']} · W/L {row['wins']}/{row['losses']}",color='#d5e0f1',va='center',fontsize=10)
ax.axvline(0,color='#cc7680',linewidth=1.1,linestyle='--',alpha=.9)
ax.set_yticks([2,1,0],[row['label'] for row in rows],color='#d5e0f1')
ax.set_xlim(-.012,.085);ax.set_ylim(-.65,2.7)
ax.set_xlabel('Paired mean change in MRR@25 · 90% bootstrap interval',color='#d5e0f1',labelpad=12)
ax.set_xticks([-.01,0,.01,.02,.03,.04,.05,.06]);ax.tick_params(colors='#d5e0f1',length=0,pad=8)
for spine in ax.spines.values():spine.set_visible(False)
ax.grid(axis='x',color='#324359',linewidth=.5,alpha=.5);ax.set_axisbelow(True)
ax.set_title('A fixed development-panel falsifier',loc='left',color='#f1f5ff',fontweight='bold',fontsize=16,pad=18)
fig.text(.01,-.045,'Previously used fusion-selection queries. Positive S1 evidence is local; it does not establish hidden-domain transport or a score gain.',color='#b3c3d9',fontsize=10)
format_=Path(args.output).suffix.lower().lstrip('.')
if format_ not in ('svg','png'):
 raise ValueError('Use a new .svg or .png output filename')
metadata={'Date':None,'Creator':'cubres paired-slice audit'} if format_=='svg' else {'Software':'cubres paired-slice audit'}
with Path(args.output).open('xb') as stream:
 fig.savefig(stream,format=format_,dpi=150,bbox_inches='tight',metadata=metadata)
plt.close(fig)
