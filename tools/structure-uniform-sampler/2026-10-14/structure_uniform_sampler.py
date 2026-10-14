"""Original structure-uniform treatment over the owned trainer's eligible rows.

Source candidate only. No data, model, notebook identity or experiment result is
embedded. Selection uses the existing training RNG; construction consumes none.
"""
from __future__ import annotations

import hashlib

import numpy as np


class StructureUniformSampler:
    def __init__(self, eligible_spectra, structure_by_spectrum, roles, positive_by_structure):
        eligible_spectra = np.asarray(eligible_spectra)
        structure_by_spectrum = np.asarray(structure_by_spectrum)
        roles = np.asarray(roles)
        positive_by_structure = np.asarray(positive_by_structure)
        assert eligible_spectra.ndim == structure_by_spectrum.ndim == 1
        assert roles.ndim == positive_by_structure.ndim == 1
        assert len(roles) == len(positive_by_structure)
        assert np.issubdtype(eligible_spectra.dtype, np.integer)
        assert np.issubdtype(structure_by_spectrum.dtype, np.integer)
        assert len(eligible_spectra) > 0 and len(structure_by_spectrum) > 0
        assert np.all((structure_by_spectrum >= 0) & (structure_by_spectrum < len(roles)))
        expected = np.flatnonzero(
            (roles[structure_by_spectrum] == 0)
            & (positive_by_structure[structure_by_spectrum] >= 0)
        )
        assert np.array_equal(eligible_spectra, expected), 'Eligible rows drifted from valid role-0 rows'
        order = np.argsort(structure_by_spectrum[eligible_spectra], kind='stable')
        self.spectrum_ids = eligible_spectra[order]
        self.structures, self.starts, self.counts = np.unique(
            structure_by_spectrum[self.spectrum_ids], return_index=True, return_counts=True
        )
        self.structure_by_spectrum = structure_by_spectrum
        assert np.all(roles[self.structures] == 0)
        assert np.all(positive_by_structure[self.structures] >= 0)
        assert np.all(self.counts > 0) and int(self.counts.sum()) == len(expected)

    def sample(self, rng, batch_size):
        """Distinct structures, then one uniform eligible spectrum from each.

        Each structure has batch inclusion probability B/S, and every ordered
        batch slot has structure probability 1/S. A spectrum of a structure with
        n eligible spectra has per-slot probability 1/(S*n). Across steps,
        structures are drawn afresh. Singleton spectrum groups select their only
        row. No fallback permits duplicate structures when B exceeds S.
        """
        assert 0 < batch_size <= len(self.structures), 'Batch exceeds eligible optimizer structures'
        selected = rng.choice(len(self.structures), size=batch_size, replace=False)
        offsets = rng.integers(0, self.counts[selected])
        ids = self.spectrum_ids[self.starts[selected] + offsets]
        assert np.array_equal(self.structure_by_spectrum[ids], self.structures[selected])
        return ids

    def receipt(self):
        multiplicity, structures_at_multiplicity = np.unique(self.counts, return_counts=True)
        count = len(self.structures)
        return dict(
            treatment='uniform role-0 structures without replacement; one uniform eligible spectrum each',
            optimizer_structures=count,
            eligible_optimizer_spectra=len(self.spectrum_ids),
            singleton_spectrum_structures=int(np.count_nonzero(self.counts == 1)),
            minimum_eligible_spectra_per_structure=int(self.counts.min()),
            maximum_eligible_spectra_per_structure=int(self.counts.max()),
            eligible_spectra_multiplicity_histogram={
                str(int(n)): int(k) for n, k in zip(multiplicity, structures_at_multiplicity)
            },
            per_slot_structure_probability=1.0 / count,
            per_slot_spectrum_probability_minimum=1.0 / (count * int(self.counts.max())),
            per_slot_spectrum_probability_maximum=1.0 / (count * int(self.counts.min())),
            index_binding_sha256={
                name: hashlib.sha256(np.asarray(value, dtype='<i8').tobytes()).hexdigest()
                for name, value in (
                    ('structure_indices', self.structures),
                    ('eligible_spectrum_counts', self.counts),
                    ('grouped_spectrum_indices', self.spectrum_ids),
                )
            },
            index_binding_encoding='contiguous little-endian int64 array bytes',
            randomness='existing seeded training Generator; no RNG consumption at construction',
        )
