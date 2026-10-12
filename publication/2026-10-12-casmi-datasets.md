# Three public CASMI tools, 12 October 2026

Three complementary datasets are now public under **prvsiyan**. Their recorded version-1 releases were checked after creation: exact owner, title, version, processing readiness, downloadable file names and sizes. Public visibility was confirmed through the selected **Public** setting for each canonical dataset.

| Dataset | Useful for | Exact published release |
|---|---|---|
| [CASMI Candidate Interop Kit: Mass + Fingerprints](https://www.kaggle.com/datasets/prvsiyan/casmi-candidate-interop-kit) | Catching mass-window, ion, bit-order, padding, MACCS and alignment-contract mistakes with original invented NumPy fixtures | ID 12541448 · V1 · 20 files · 352,243 bytes |
| [COCONUT Proton Ion Atlas: 436k Mass Index](https://www.kaggle.com/datasets/prvsiyan/coconut-proton-ion-mass-index) | Querying eight explicit theoretical proton/charge/dimer channels across 436,389 real source mass rows, with source-row alignment and mass-ambiguity diagnostics | ID 12541801 · V1 · 20 files · 33,288,188 bytes |
| [MassBank x COCONUT: Reference Evidence Atlas](https://www.kaggle.com/datasets/prvsiyan/casmi-reference-mass-ambiguity) | Inspecting 6,951 literal-CC0 reference occurrences, 616 full keys and 5,814 raw condition groups, then comparing numerical candidate counts at ±3/10/20 ppm | ID 12542565 · V1 · 19 files · 6,711,902 bytes |

The kit is a numerical interoperability exercise: its 12 invented rows are not chemical fingerprints or molecular benchmarks. The ion atlas preserves source row positions and defines theoretical channels; it does not assign an observed ion or certify chemical query coverage. The reference atlas preserves complete original attribution and exact supplied keys. Its supplied reference mass has no independently established neutral-mass basis, so the windows remain explicitly numerical. None of these publications measures descriptor alignment, model accuracy or a competition score gain.

The reference atlas includes runnable standard-library readers and a separately reviewed portable rebuild. Its measured original build and the unexecuted-on-real-inputs public rebuild variant remain distinct. Source and original diagrams are available in the [immutable reference-atlas source directory](https://github.com/cubres/enveda-casmi-2026/tree/4fd38d860e639d4f2764dc74531deac93e1c13b5/reference-evidence-atlas).

The existing [COCONUT 2.0 candidates + fingerprints (CASMI26)](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates) also now has saved **Sources** and **Collection Methodology** text, confirmed in the dataset UI at 18:58:42 UTC. The source link is the [COCONUT resource](https://coconut.naturalproducts.net/). This was a description/provenance edit: it uploaded no data, created no dataset version and left its version-2 data unchanged. Credit belongs to the COCONUT team and the original candidate producer; the reference atlas additionally credits Samar Talwar's compilation and each MassBank contributor.

The kit's original code and invented data are MIT licensed, described under Kaggle's native “Other” licence selection. The real-source ion and reference data retain **CC BY-NC-SA 4.0** and full attribution; their original code, prose and schematic have a separate MIT scope. A raw record's CC0 label does not relicense the MassBank compilation or its COCONUT derivative.

**Verification limit:** these readbacks did not download the remote payloads or verify their content hashes. Local source/release SHA-256 pins remain local byte evidence. The raw privacy field was missing, so SDK defaults were not treated as proof of visibility; explicit Public UI observations supplied that evidence. The compact [publication proof](2026-10-12-casmi-datasets.json) records the exact IDs, counts, timestamps and captured-receipt hashes without distributing private paths or authenticated responses.

Existing notebook artwork stays preserved. This release record adds useful data tools and documentation; it claims no new leaderboard result.
