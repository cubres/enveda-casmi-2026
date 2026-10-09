# PubChem compound popularity counts

Look up how often a molecular connectivity appears in PubChem substance records and PubMed links, without calling a web API for each candidate. The dataset provides **105,880,815 InChIKey first blocks** with two integer counts per block, plus counts aligned to the existing [PubChem mass index](https://www.kaggle.com/datasets/prvsiyan/pubchem-npformula-massindex).

This is useful as a documentation prior among chemically plausible candidates, for inspecting database coverage, or for studying how unevenly compounds are represented in the literature. It contains identifiers and derived counts, with no spectra or competition labels.

```text
14-letter InChIKey block -> sorted-key lookup -> distinct SID / PMID counts
                                                  |
                                      optional log1p(SID) + log1p(PMID)
                                                  |
                                    combine with independent chemical evidence
```

## Two ways to use the arrays

**For arbitrary candidate lists:** use the `ap2pop_ik14*` arrays and look up the InChIKey first block. A matching block and a missing block can both have a popularity value of zero; keep the `matched` flag if that distinction matters.

**For the companion mass-index rows:** use `ap2pop_store_*`. Those arrays follow that dataset's `off.npy` / `len.npy` order **before sorting by mass**. If you sort masses or create a shortlist, apply the same row indices to the count arrays. Length equality alone does not establish row alignment.

## File dictionary — data version 1

| File | Shape and dtype | Meaning |
|---|---|---|
| `ap2pop_ik14.npy` | `(105880815,)`, `S14` | Sorted, unique 14-byte InChIKey first blocks |
| `ap2pop_ik14_sid.npy` | `(105880815,)`, `uint32` | Distinct PubChem substance identifiers linked to the block |
| `ap2pop_ik14_pmid.npy` | `(105880815,)`, `uint32` | Distinct PubMed identifiers linked to the block |
| `ap2pop_store_sid.npy` | `(71370470,)`, `uint32` | Substance counts in the companion mass-index row order |
| `ap2pop_store_pmid.npy` | `(71370470,)`, `uint32` | PubMed counts in the same row order |
| `ap2pop_manifest.json` | JSON | Count definitions, row totals and 16 companion alignment checks |
| `PROVENANCE.json` | JSON | Input URLs, source dates, published/local checksums and output hashes |
| `build_popularity.py` | Python | The original build procedure |
| `README.md` | Markdown | Additional definitions and source notes |

The five arrays occupy approximately **2.90 GB on disk**, including headers. Memory mapping avoids loading that entire collection into RAM; binary searches and small result arrays still use memory and trigger disk reads.

## Quick start: bounded lookup, including unknown keys

This CPU example uses NumPy only. Change `root` to an extracted local folder for experiments outside Kaggle. Pass the 14-letter first block, rather than silently truncating a full InChIKey.

```python
from pathlib import Path
import re
import numpy as np

root = Path('/kaggle/input/pubchem-popularity-counts')
keys = np.load(root / 'ap2pop_ik14.npy', mmap_mode='r', allow_pickle=False)
sid = np.load(root / 'ap2pop_ik14_sid.npy', mmap_mode='r', allow_pickle=False)
pmid = np.load(root / 'ap2pop_ik14_pmid.npy', mmap_mode='r', allow_pickle=False)
assert keys.dtype == np.dtype('S14') and keys.ndim == 1
assert sid.dtype == pmid.dtype == np.dtype('uint32')
assert keys.shape == sid.shape == pmid.shape == (105880815,)

blocks = ['RYYVLZVUVIJVGH']  # caffeine's connectivity block; example only
if any(re.fullmatch(r'[A-Z]{14}', b) is None for b in blocks):
    raise ValueError('Use uppercase 14-letter InChIKey first blocks')
q = np.asarray(blocks, dtype='S14')
i = np.searchsorted(keys, q, side='left')
matched = i < len(keys)
inside = np.flatnonzero(matched)
matched[inside] = keys[i[inside]] == q[inside]
hit = np.flatnonzero(matched)
substances = np.zeros(len(q), dtype=np.uint32)
articles = np.zeros(len(q), dtype=np.uint32)
substances[hit] = sid[i[hit]]
articles[hit] = pmid[i[hit]]
pop = np.log1p(substances.astype('float64')) + np.log1p(articles.astype('float64'))
print({'matched': matched.tolist(), 'substances': substances.tolist(),
       'pubmed': articles.tolist(), 'pop': pop.tolist()})
```

Only in-bounds matching indices reach the count arrays. An unknown block that sorts after the final key therefore returns zero rather than raising `IndexError`. The numerical lookup was checked on invented fixtures covering missing keys, empty inputs, duplicate requests and genuine zero-count matches; the full multi-gigabyte table was not reloaded or exhaustively checked during that example audit.

## What the counts mean

`substances` counts distinct `(InChIKey first block, SID)` pairs from `CID-SID` link types 1 and 2. `pubmed` counts distinct `(block, PMID)` pairs from all four `CID-PMID` link types. Several CIDs sharing a block pool their links, and one linked article counts once for that block. A PubMed link is not a count of independent experiments, and a SID is not a biological abundance measurement.

The optional prior is `log1p(substances) + log1p(pubmed)`. Keep the raw integers separate from logs: these files are **not** the float16 log-count arrays used by some other CASMI resources. Do not reuse another dataset's row indices or scoring weights without checking its semantics.

The prior favours well-documented chemistry. Evaluate it separately on rare compounds and on complete query denominators, and compare it with spectral evidence before letting it reorder candidates. Lookup correctness is not a leaderboard result.

## Alignment and reproducibility

Pin this data version and the companion mass-index version together. `ap2pop_manifest.json` records 16 row positions and SHA-1 checks of the raw SMILES bytes at those companion rows. These spot checks help detect an incorrect mount or row order; they do not certify every aligned row.

The build manifest reports 71,370,466 companion rows with a known block out of 71,370,470. Preserve unmatched rows rather than dropping them and shifting all later indices.

Fresh full reads of two small files on October 9, 2026 gave:

- `ap2pop_manifest.json`: `48d2378ab45a352749422af755b5ee4c7bd1db14e4c90b51d8d32cc4af616e4a`
- `PROVENANCE.json`: `5b615fc8299b5625e4c382be37595d2e300f1041dd6984b1a061ab9057d092d8`

The large-array hashes in `PROVENANCE.json` are publisher-provided build records. This card's October 9 audit verified the small manifest/provenance files and file inventory, rather than independently rehashing all large arrays.

## Sources, attribution and terms

The build used [NCBI PubChem Compound Extras](https://ftp.ncbi.nlm.nih.gov/pubchem/Compound/Extras/) files `CID-InChI-Key.gz`, `CID-SID.gz` and `CID-PMID.gz`, downloaded on October 2, 2026. `PROVENANCE.json` records the actual server dates and MD5 checks; the PMID source's server date is older than the other two inputs.

Please acknowledge PubChem and cite Kim et al., *PubChem 2025 update*, *Nucleic Acids Research* 53(D1):D1516–D1525. The existing dataset license is **CC0 1.0**. NCBI's [molecular-data policy](https://www.ncbi.nlm.nih.gov/home/about/policies/#data) states its reuse policy and explains that depositor rights can still apply to original contributed materials. This dataset distributes derived identifiers/counts rather than deposited descriptions or articles; it does not relicense external records.

The [Analog Propagation CASMI notebook](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) shows one use in candidate ranking. Reproduction notes and measured experiments belong in the [Enveda project repository](https://github.com/cubres/enveda-casmi-2026); use its pinned experiment receipts for score claims.
