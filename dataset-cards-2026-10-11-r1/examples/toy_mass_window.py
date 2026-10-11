# SPDX-License-Identifier: MIT
"""Invented numeric control for an inclusive mass window; no dataset input."""
import json
import numpy as np

def run():
    centre=300.0
    tolerance=centre*10e-6
    mass=np.array([centre-tolerance,centre,centre+tolerance,centre+2*tolerance],dtype=np.float64)
    lower=np.searchsorted(mass,centre-tolerance,side='left')
    old_upper=np.searchsorted(mass,centre+tolerance)  # default left excludes exact upper endpoint
    inclusive_upper=np.searchsorted(mass,centre+tolerance,side='right')
    if (int(lower),int(old_upper),int(inclusive_upper))!=(0,2,3):
        raise ValueError('INVENTED_BOUNDARY_EXPECTATION_FAILED')
    # Empty and repeated exact-boundary cases are explicit parts of the contract.
    repeated=np.array([centre-tolerance,centre-tolerance,centre+tolerance,centre+tolerance],dtype=np.float64)
    repeated_lo=np.searchsorted(repeated,centre-tolerance,side='left')
    repeated_hi=np.searchsorted(repeated,centre+tolerance,side='right')
    empty=np.array([],dtype=np.float64)
    empty_count=np.searchsorted(empty,centre+tolerance,side='right')-np.searchsorted(empty,centre-tolerance,side='left')
    if int(repeated_hi-repeated_lo)!=4 or int(empty_count)!=0:
        raise ValueError('INVENTED_BOUNDARY_EXPECTATION_FAILED')
    return {'status':'INVENTED_MASS_BOUNDARIES_ONLY','numpy_version':np.__version__,
            'old_default_upper_selected_rows':int(old_upper-lower),
            'inclusive_upper_selected_rows':int(inclusive_upper-lower),
            'repeated_exact_endpoint_rows':int(repeated_hi-repeated_lo),
            'empty_selected_rows':int(empty_count),
            'real_query_molecule_or_spectrum':False,'native_or_competition_score':None}

if __name__=='__main__':print(json.dumps(run(),indent=2,allow_nan=False))
