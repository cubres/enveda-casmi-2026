# SPDX-License-Identifier: MIT
"""Original charged-ion adapter; explicit hypotheses, not a chemistry oracle.

Pure stdlib. No models, filesystem writes, chemistry library, or data loading.
A precursor adduct is never automatically copied to a fragment ion.
"""
from __future__ import annotations
import math
from collections import defaultdict

H = 1.00782503207
ELECTRON = 0.00054857990
PROTON = H-ELECTRON
NA = 22.9897692809
K = 38.96370668
N = 14.0030740048
O = 15.9949146196
CL = 34.96885268
WATER = 2*H+O
AMMONIUM = N+4*H-ELECTRON

# Exact supported precursor labels: multiplicity, absolute charge, mass shift, polarity.
# Operational constants match the pinned current own precursor-index implementation.
ADDUCTS = {
    "[M+H]+": (1,1,PROTON,"positive"),
    "[M-H]-": (1,1,-PROTON,"negative"),
    "[M+Na]+": (1,1,NA-ELECTRON,"positive"),
    "[M+K]+": (1,1,K-ELECTRON,"positive"),
    "[M+NH4]+": (1,1,AMMONIUM,"positive"),
    "[M+2H]2+": (1,2,2*PROTON,"positive"),
    "[M-2H]2-": (1,2,-2*PROTON,"negative"),
    "[M]+": (1,1,-ELECTRON,"positive"),
    "[M]-": (1,1,ELECTRON,"negative"),
    "[M+Cl]-": (1,1,CL+ELECTRON,"negative"),
    "[M-H2O+H]+": (1,1,PROTON-WATER,"positive"),
    "[M+H-H2O]+": (1,1,PROTON-WATER,"positive"),
    "[M-H2O-H]-": (1,1,-PROTON-WATER,"negative"),
    "[2M+H]+": (2,1,PROTON,"positive"),
    "[2M-H]-": (2,1,-PROTON,"negative"),
    "[2M+Na]+": (2,1,NA-ELECTRON,"positive"),
    "[2M+K]+": (2,1,K-ELECTRON,"positive"),
    "[2M+NH4]+": (2,1,AMMONIUM,"positive"),
    "[3M+H]+": (3,1,PROTON,"positive"),
    "[3M-H]-": (3,1,-PROTON,"negative"),
}
FAMILIES = {
    "protonated": ("positive",PROTON),
    "deprotonated": ("negative",-PROTON),
    "sodium_retained": ("positive",NA-ELECTRON),
    "potassium_retained": ("positive",K-ELECTRON),
    "radical_cation": ("positive",-ELECTRON),
    "radical_anion": ("negative",ELECTRON),
    "chloride_retained": ("negative",CL+ELECTRON),
}
MAX_RAW_PEAKS = 100_000
MAX_KEPT_PEAKS = 256
MAX_NEUTRAL_FRAGMENTS = 2048
MAX_IONS = 2048
FLOOR = .002


class AdapterHold(ValueError):
    pass


def _finite(x, field, positive=False):
    if type(x) not in (int,float):
        raise AdapterHold(field+" must be a finite real number")
    try:
        x=float(x)
    except OverflowError:
        raise AdapterHold(field+" is outside supported float range")
    if not math.isfinite(x) or (positive and x<=0):
        raise AdapterHold(field+" must be finite"+(" and positive" if positive else ""))
    return x


def precursor_metadata(adduct, mode, precursor_mz):
    if not isinstance(adduct,str):
        raise AdapterHold("precursor adduct must be an explicit string")
    if adduct == "[M-2H]-":
        raise AdapterHold("ambiguous [M-2H]- charge label; require corrected explicit annotation")
    if adduct not in ADDUCTS:
        raise AdapterHold("unsupported precursor adduct")
    if mode not in ("positive","negative"):
        raise AdapterHold("unknown ionization mode")
    n,z,delta,expected = ADDUCTS[adduct]
    if mode != expected:
        raise AdapterHold("adduct/polarity disagreement")
    mz = _finite(precursor_mz,"precursor_mz",True)
    neutral = (z*mz-delta)/n
    if neutral <=0 or not math.isfinite(neutral):
        raise AdapterHold("nonpositive or nonfinite inferred neutral mass")
    return {"adduct":adduct,"mode":mode,"multiplicity":n,"precursor_abs_charge":z,
            "precursor_mz":mz,"neutral_mass":neutral}


def fragment_ions(neutral_masses, metadata, *, family, h_shifts=(-2,-1,0,1,2), mass_kind="neutral"):
    """Explicit singly-charged fragment family, separate from precursor charge.

    H shifts are model hypotheses. They are not claims of valence/atom balance.
    No automatic protonated/retained family selection is performed.
    """
    if mass_kind != "neutral":
        raise AdapterHold("input fragment mass_kind must be declared neutral")
    if family not in FAMILIES:
        raise AdapterHold("declare a supported explicit fragment family")
    mode,delta=FAMILIES[family]
    if metadata.get("mode") != mode:
        raise AdapterHold("fragment family/polarity disagreement")
    if family=="sodium_retained" and metadata.get("adduct") not in ("[M+Na]+","[2M+Na]+"):
        raise AdapterHold("sodium retention requires a sodium precursor")
    if family=="potassium_retained" and metadata.get("adduct") not in ("[M+K]+","[2M+K]+"):
        raise AdapterHold("potassium retention requires a potassium precursor")
    if family=="chloride_retained" and metadata.get("adduct")!="[M+Cl]-":
        raise AdapterHold("chloride retention requires a chloride precursor")
    if not isinstance(h_shifts,(list,tuple)) or not 1<=len(h_shifts)<=5:
        raise AdapterHold("supply 1..5 explicit H-shift hypotheses")
    if any(type(x) is not int or x < -2 or x > 2 for x in h_shifts):
        raise AdapterHold("H shifts must be distinct integers in -2..2")
    if len(set(h_shifts))!=len(h_shifts):
        raise AdapterHold("duplicate H shift")
    if not isinstance(neutral_masses,(list,tuple)) or not 1<=len(neutral_masses)<=MAX_NEUTRAL_FRAGMENTS:
        raise AdapterHold("neutral fragment vector size outside prototype bounds")
    values=[_finite(x,"neutral fragment",True) for x in neutral_masses]
    ions=sorted({m+h*H+delta for m in values for h in h_shifts})
    if len(ions)>MAX_IONS:
        raise AdapterHold("charged-ion hypothesis budget exceeded; no truncation")
    if any(x<=0 or not math.isfinite(x) for x in ions):
        raise AdapterHold("nonpositive or nonfinite charged fragment hypothesis")
    return {"ion_mz":ions,"fragment_family":family,"fragment_abs_charge":1,
            "h_shifts":list(h_shifts),"chemical_identity_verified":False}


def clean_peaks(mz,intensity):
    """Frozen native-style floor/top-k/normalization; stable tie rule declared."""
    if not isinstance(mz,(list,tuple)) or not isinstance(intensity,(list,tuple)):
        raise AdapterHold("explicit aligned peak vectors required")
    if not 1<=len(mz)<=MAX_RAW_PEAKS or len(mz)!=len(intensity):
        raise AdapterHold("raw peak count outside bounds or unaligned vectors")
    pairs=[]
    for i,(m,w) in enumerate(zip(mz,intensity)):
        m=_finite(m,"peak m/z",True);w=_finite(w,"intensity")
        if w<0:raise AdapterHold("negative intensity")
        pairs.append((m,w,i))
    maximum=max(w for _,w,_ in pairs)
    if maximum<=0:raise AdapterHold("no positive intensity")
    keep=[r for r in pairs if r[1]>=FLOOR*maximum]
    if len(keep)>MAX_KEPT_PEAKS:
        keep=sorted(keep,key=lambda r:(-r[1],r[2]))[:MAX_KEPT_PEAKS]
    keep.sort(key=lambda r:(r[0],r[2]))
    total=sum(w for _,w,_ in keep)
    if not math.isfinite(total):
        raise AdapterHold("intensity total overflow")
    return {"mz":[m for m,_,_ in keep],"intensity":[w/total for _,w,_ in keep],
            "raw_peak_count":len(pairs),"kept_peak_count":len(keep),
            "cleaning_policy":"floor0.002_top256_linear_then_sqrt_assignment_stable_ties",
            "native_bitwise_parity":"UNVERIFIED"}


def _energy(record):
    values=record.get("collision_energy_ev")
    if not isinstance(values,(list,tuple)) or not values:
        return None,"HOLD_CE_COMPARABILITY"
    try:
        ev=tuple(sorted(_finite(x,"collision energy") for x in values))
    except AdapterHold:
        return None,"HOLD_CE_COMPARABILITY"
    if any(x<0 for x in ev):
        return None,"HOLD_CE_COMPARABILITY"
    # The explicitly named *_ev column supplies eV. Preserve the original units
    # separately, rather than silently converting a percent/NCE value ourselves.
    units=record.get("collision_energy_orig_units")
    return (ev,units if isinstance(units,str) else None),"DECLARED_EV_COLUMN_ONLY"


def acquisition_window(record,cleaned,*,window_source=None):
    lo=record.get("acquisition_mz_min");hi=record.get("acquisition_mz_max")
    if lo is None or hi is None or not isinstance(window_source,str) or not window_source.strip():
        return None,"HOLD_NO_ACQUISITION_WINDOW"
    lo=_finite(lo,"acquisition_mz_min",True);hi=_finite(hi,"acquisition_mz_max",True)
    if hi<=lo or any(not lo<=x<=hi for x in cleaned["mz"]):
        raise AdapterHold("invalid acquisition bounds or retained peak outside bounds")
    return [lo,hi],"DECLARED_ACQUISITION_WINDOW"


def adapt_spectrum(record,*,window_source=None,query_binding=None):
    if not isinstance(record,dict):
        raise AdapterHold("spectrum must be a metadata/peak record")
    if query_binding is not None and (not isinstance(query_binding,str) or not query_binding):
        raise AdapterHold("query_binding must be a caller-bound nonempty token")
    meta=precursor_metadata(record.get("adduct"),record.get("ionization_mode"),record.get("precursor_mz"))
    cleaned=clean_peaks(record.get("ms2_mzs"),record.get("ms2_normalized_intensities"))
    window,wstatus=acquisition_window(record,cleaned,window_source=window_source)
    energy,estatus=_energy(record)
    instrument=record.get("instrument_type")
    if not isinstance(instrument,str) or not instrument:
        instrument=None
    key=(meta["adduct"],meta["mode"],meta["precursor_abs_charge"],meta["multiplicity"],
         instrument,energy,tuple(window) if window else None,window_source)
    return {"status":"READY_ASSIGNMENT_ONLY" if window is None else "READY_DECLARED_WINDOW",
            "query_binding":query_binding,
            "metadata":meta,"cleaned":cleaned,"window":window,"window_status":wstatus,
            "energy":energy,"energy_status":estatus,"instrument":instrument,
            "compatible_group_key":key,"group_comparability":"HOLD" if energy is None or instrument is None else "DECLARED_METADATA_ONLY"}


def compatible_groups(adapted,*,same_query_binding):
    """Partition already-bound views of ONE query; metadata is not analyte identity.

    Caller binding must precede this function. A shared token is an assertion,
    not independent proof that spectra belong to the same physical analyte.
    Unknown energy/instrument is isolated, never silently pooled.
    """
    if not isinstance(same_query_binding,str) or not same_query_binding:
        raise AdapterHold("a previously established same-query binding is required")
    if any(view.get("query_binding")!=same_query_binding for view in adapted):
        raise AdapterHold("missing or mismatched same-query binding")
    groups=defaultdict(list)
    for i,view in enumerate(adapted):
        key=view["compatible_group_key"]
        if view["group_comparability"]=="HOLD":
            key=key+("isolated_unknown_view",i)
        groups[key].append(i)
    return list(groups.values())


def potential_reuse_intervals(cleaned,*,abs_tol=.01,ppm=0.0):
    """Geometry only: adjacent centroids' admissible ion intervals overlap.

    Without a predicted ion bank this is *not* a measured reused-ion score gap.
    """
    a=_finite(abs_tol,"abs_tol",True);p=_finite(ppm,"ppm")*1e-6
    if a>.1 or p<0 or p>.001:raise AdapterHold("prototype tolerance bound exceeded")
    mz=cleaned["mz"]
    overlap=0
    for left,right in zip(mz,mz[1:]):
        if left+max(a,p*left)>=right-max(a,p*right):
            overlap+=1
    return {"adjacent_pairs":max(0,len(mz)-1),"overlapping_pairs":overlap,
            "actual_predicted_ion_reuse":"UNMEASURED"}

