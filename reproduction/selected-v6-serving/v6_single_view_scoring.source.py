"""Pinned V6 single-view FPNet primitives; no driver, discovery, blend or fallback.

Importing this module performs no file or model access. Root must qualify raw
test preprocessing, candidate bits, native fp32 numerics, rights and mounts
before any caller can use these primitives in an inference notebook.
"""
import hashlib
import json
import os
from pathlib import Path

WEIGHT_SHA = '9c46ca4fcf19002fecbcded0d0808e8a81e3a25a143e684e259f265c44a5be31'
WEIGHT_BYTES = 197739081
FPMODEL_SHA = '69f2656778a08233e22235bf4853f0b3d2420b431390a32d6c8ed453cde85c76'
FULL_MASK_SHA = 'f771cb6aa87a418b06d9abfbdac0c1759040afb955b9dfa59e8932105a65bdc6'
CLEAN_MASK_SHA = 'a61e372fc41091bf5c7467e08134081266262665077cb9e2c56d73e4887f3013'
ROLE_SHA = '4d7b366293225a1ae67dfc0306480129b9ac1351a6d8581f0be40a269bdaff86'
MAPPING_RECEIPT_SHA = '488a04b9d148e83c1bc5c9dcf49acfb97479bc436d1c72912b047f4dcfb1e8f7'
MAPPING_SHA = '2fb6a121c4272622d3558c49180ff45dd9e7cc13705e1a7e29f25929323c0d91'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def file_sha(path):
    path = Path(path)
    need(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), 'EXPLICIT_REGULAR_FILE_REQUIRED')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def prepare_raw_spectrum(raw, owned_fpmodel):
    """Exact owned build_dataset metadata/peak transform for one admitted row.

    Root must join an independent cached prepared reference by original source
    row before the canary; passing this helper twice is not that qualification.
    """
    import numpy as np
    need(file_sha(owned_fpmodel.__file__) == FPMODEL_SHA, 'OWNED_PREPROCESSOR_SOURCE_DRIFT')
    precursor = float(raw['precursor_mz'])
    # Match the library cache's float32 rounding before unchanged prep_peaks.
    # speclib.py: 27e149dd8f705389a969f1b9232b7b2451c7f3189f5586f5a42160864ff403eb
    # build_dataset.py: ec90d3d9ef3ec9b1e45d2dc9e2e766439ef7431cce8f8388ccb96b0be96a517b
    # nb_common.py corroboration: eb40629c379b5a529f1cf462814b22c98fafbc52ed82a568c45702bdcd68785d
    mz, intensity = owned_fpmodel.prep_peaks(
        np.asarray(raw['ms2_mzs'], dtype=np.float32),
        np.asarray(raw['ms2_normalized_intensities'], dtype=np.float32), precursor)
    energies = raw['collision_energy_ev']
    ce = np.float32(float(np.mean(energies)) if energies is not None and len(energies) > 0 else -1.)
    return dict(mz=mz[:128], intensity=intensity[:128], precursor=np.float32(precursor),
                adduct_index=owned_fpmodel.ADDUCT_IX.get(raw['adduct'], owned_fpmodel.ADDUCT_IX['<unk>']),
                instrument_index=owned_fpmodel.instr_family(raw['instrument_type']),
                collision_energy=np.float32(25. if ce < 0 else ce),
                ion_mode=np.float32(1. if str(raw['ionization_mode']) == 'positive' else -1.))


def qualify_prepared_reference(prepared, independent_cached_reference):
    """Compare one source-row-bound cached Data.batch input, with no file access."""
    import numpy as np
    fields = {'mz', 'intensity', 'precursor', 'adduct_index', 'instrument_index', 'collision_energy', 'ion_mode'}
    need(type(prepared) is dict and type(independent_cached_reference) is dict
         and set(prepared) == set(independent_cached_reference) == fields, 'PREPARED_REFERENCE_SCHEMA')
    for name in fields:
        actual, expected = np.asarray(prepared[name]), np.asarray(independent_cached_reference[name])
        vector = name in ('mz', 'intensity')
        need(actual.ndim == expected.ndim == (1 if vector else 0), 'PREPARED_REFERENCE_DIMENSION:'+name)
        shape = (len(actual),) if name in ('mz', 'intensity') and actual.ndim == 1 else ()
        dtype = np.dtype('int64') if name in ('adduct_index', 'instrument_index') else np.dtype('float32')
        need(actual.shape == expected.shape == shape and actual.dtype == expected.dtype == dtype
             and np.isfinite(actual).all() and np.isfinite(expected).all()
             and actual.tobytes(order='C') == expected.tobytes(order='C'),
             'EXACT_TRAINING_PREPROCESSING_REFERENCE_DRIFT:'+name)
    return True


class V6SingleView:
    def __init__(self, owned_fpmodel, checkpoint, device, serving_admission, canary_only=False):
        # The caller imports only the exact owned module from an admitted path.
        # Neither a mount glob nor torch/pickle fallback exists in this module.
        import numpy as np
        import torch
        need(file_sha(owned_fpmodel.__file__) == FPMODEL_SHA and owned_fpmodel.MAX_PEAKS == 128,
             'OWNED_ARCHITECTURE_OR_FEATURIZER_DRIFT')
        need(type(canary_only) is bool, 'EXPLICIT_DISPATCH_SCOPE')
        need(serving_admission['checkpoint_sha256'] == WEIGHT_SHA
             and serving_admission['owned_fpmodel_sha256'] == FPMODEL_SHA
             and serving_admission['raw_test_preprocessing_matches_training'] is True
             and serving_admission['candidate_raw_10407_recipe_and_full_mask_qualified'] is True
             and serving_admission['competition_use_and_private_artifact_mount_rights_qualified'] is True
             and serving_admission['merged_view_or_autocast_or_new_blend_authorized'] is False,
             'ROOT_SERVING_QUALIFICATION_MISSING')
        if canary_only:
            need(serving_admission['status'] == 'ADMITTED_ONE_NATIVE_V6_SINGLE_SPECTRUM_CANARY_ONLY'
                 and type(serving_admission['maximum_spectrum_forward_calls']) is int
                 and serving_admission['maximum_spectrum_forward_calls'] == 1
                 and serving_admission['competition_submission_authorized'] is False,
                 'ONE_CANARY_SCOPE_REQUIRED')
        else:
            need(serving_admission['status'] == 'ADMITTED_EXACT_V6_SINGLE_VIEW_SERVING_PRIMITIVES'
                 and serving_admission['actual_native_fp32_canary_qualified'] is True,
                 'ACTUAL_NATIVE_CANARY_REQUIRED_BEFORE_SERVING')
        need(device in ('mps', 'cuda:0') and serving_admission['actual_device'] == device,
             'EXPLICIT_BACKEND_REQUIRED')
        if device == 'mps':
            need(torch.backends.mps.is_available()
                 and os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK', '0') == '0', 'MPS_UNAVAILABLE_OR_FALLBACK')
        else:
            need(torch.cuda.is_available(), 'CUDA_UNAVAILABLE')
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
        checkpoint = Path(checkpoint)
        need(checkpoint.stat().st_size == WEIGHT_BYTES and file_sha(checkpoint) == WEIGHT_SHA,
             'EXACT_V6_CHECKPOINT_BYTES_REQUIRED')
        ck = torch.load(checkpoint, map_location='cpu', weights_only=True)
        need(type(ck) is dict and (ck['nbits'], ck['layers'], ck['d'], ck['step'], ck['seed']) ==
             (10395, 8, 512, 28000, 20261003)
             and ck['split']['role_table_sha256'] == ROLE_SHA, 'V6_CHECKPOINT_SEMANTICS_DRIFT')
        self.net = owned_fpmodel.FPNet(10395, d=512, layers=8)
        self.net.load_state_dict(ck['model'], strict=True)
        need(sum(p.numel() for p in self.net.parameters()) == 49424027
             and all(torch.isfinite(value).all().item() for value in self.net.state_dict().values()),
             'V6_ARCHITECTURE_OR_FINITE_STATE_DRIFT')
        self.net.eval().to(device=device, dtype=torch.float32)
        self.device, self.np, self.torch = device, np, torch
        self.canary_only, self.canary_forward_remaining = canary_only, 1 if canary_only else None

    def prepared_spectrum_logits(self, mz, intensity, precursor, adduct_index,
                                instrument_index, collision_energy, ion_mode):
        """One already training-qualified spectrum -> exactly 10395 raw logits.

        Inputs are the training-equivalent prepared sequence, NOT arbitrary raw
        peaks. Use the first128 prepared peaks just as Data.batch(aug=False,
        merge_p=0) does. The caller must separately qualify that preparation.
        No averaging across spectra or merged view happens here.
        """
        np, torch = self.np, self.torch
        mz, intensity = np.asarray(mz), np.asarray(intensity)
        need(mz.ndim == intensity.ndim == 1 and mz.shape == intensity.shape
             and mz.dtype == intensity.dtype == np.float32
             and 0 < len(mz) and np.isfinite(mz).all() and np.isfinite(intensity).all(),
             'PREPARED_PEAK_SCHEMA')
        need(type(adduct_index) is int and 0 <= adduct_index < 26
             and type(instrument_index) is int and 0 <= instrument_index < 5
             and np.isfinite(precursor) and precursor > 0
             and np.isfinite(collision_energy) and ion_mode in (-1., 1.), 'PREPARED_METADATA_SCHEMA')
        mz = mz[:128].reshape(1, -1)
        intensity = intensity[:128].reshape(1, -1)
        pad = np.zeros(mz.shape, bool)
        ce = 25. if collision_energy < 0 else collision_energy
        tensor = lambda values: torch.as_tensor(values, device=self.device)
        inputs = (tensor(mz), tensor(intensity), tensor(pad),
                  tensor(np.asarray([precursor], np.float32)),
                  tensor(np.asarray([adduct_index], np.int64)),
                  tensor(np.asarray([instrument_index], np.int64)),
                  tensor(np.asarray([ce], np.float32)), tensor(np.asarray([ion_mode], np.float32)))
        if self.canary_only:
            need(self.canary_forward_remaining == 1, 'SINGLE_CANARY_FORWARD_CONSUMED')
            self.canary_forward_remaining = 0
        with torch.inference_mode(), torch.autocast(device_type=self.device.split(':')[0], enabled=False):
            values = self.net(*inputs).float().cpu().numpy()
        need(values.shape == (1, 10395) and np.isfinite(values).all(), 'FINITE_FULL_LOGITS_REQUIRED')
        return values[0]


def exact_full_candidate_scores(candidate_bits, raw_logits):
    """Full10395 dot score; does not reconstruct absent bits from clean6930."""
    import numpy as np
    bits, logits = np.asarray(candidate_bits), np.asarray(raw_logits)
    need(bits.ndim == 2 and bits.shape[1] == 10395 and bits.shape[0] <= 4096
         and bits.dtype == np.uint8 and np.all((bits == 0) | (bits == 1)), 'FULL_CANDIDATE_BITS_REQUIRED')
    need(logits.shape == (10395,) and logits.dtype == np.float32 and np.isfinite(logits).all(),
         'FULL_RAW_LOGITS_REQUIRED')
    scores = bits.astype(np.float32) @ logits
    need(np.isfinite(scores).all(), 'FINITE_CANDIDATE_SCORES_REQUIRED')
    return scores


def gather_clean_coordinates(raw_logits, mapping_file, mapping_file_sha256):
    """A qualified coordinate gather only; no blend or ranker compatibility claim."""
    import numpy as np
    need(mapping_file_sha256 == MAPPING_RECEIPT_SHA and file_sha(mapping_file) == mapping_file_sha256,
         'ACTUAL_MAPPING_RECEIPT_PIN_REQUIRED')
    with Path(mapping_file).open('rb') as stream:
        body = stream.read(131073)
    need(len(body) <= 131072, 'MAPPING_RECEIPT_CAP')
    receipt = json.loads(body)
    need(receipt['status'] == 'PASS_EXACT_INTEGER_SUBSET_ORDER_ONLY'
         and receipt['raw_coordinates'] == 10407 and receipt['full_count'] == 10395
         and receipt['clean_count'] == 6930 and receipt['missing_raw_coordinates'] == 0
         and receipt['input_sha256'] == {'full': FULL_MASK_SHA, 'clean': CLEAN_MASK_SHA}
         and receipt['private_only'] is True and receipt['inference_performed'] is False
         and receipt['blend_or_score_equivalence_established'] is False,
         'MAPPING_QUALIFICATION_SCOPE')
    mapping = receipt['clean_to_full_output_positions']
    need(type(mapping) is list and len(mapping) == 6930
         and all(type(value) is int and 0 <= value < 10395 for value in mapping)
         and all(left < right for left, right in zip(mapping, mapping[1:])), 'EXACT_GATHER_SCHEMA')
    encoded = json.dumps(mapping, separators=(',', ':')).encode('ascii')
    need(hashlib.sha256(encoded).hexdigest() == receipt['mapping_sha256'] == MAPPING_SHA, 'EXACT_GATHER_DIGEST')
    logits = np.asarray(raw_logits)
    need(logits.shape == (10395,) and logits.dtype == np.float32 and np.isfinite(logits).all(), 'FULL_RAW_LOGITS_REQUIRED')
    return logits[np.asarray(mapping, np.int64)].copy()
