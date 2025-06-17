import math
import numpy as np
from interface import utils

def add_calculated_metabolites(lcmdata):
    """
    For 31P-MRS data, calculates additional metabolites (PH, MGmm, PiEX_conc)
    from the LCModel concentration table and adds synthetic subspectra to lcmdata.
    """

    def find_metabolite_value(target_name):
        # Look for a metabolite whose name contains target_name (case-insensitive)
        for entry in lcmdata.get('conc', []):
            if target_name.lower() in entry.get('name', '').lower():
                try:
                    return float(entry['c'])
                except (ValueError, TypeError):
                    return None
        return None

    # Extract required metabolite values (assumed to be the fitted shift values)
    PCr = find_metabolite_value("PCr")
    Pi   = find_metabolite_value("Pi")
    aATP = find_metabolite_value("a-ATP")
    bATP = find_metabolite_value("b-ATP")
    gATP = find_metabolite_value("g-ATP")
    PiEX = find_metabolite_value("Pi_ex")

    # Ensure all required metabolites were found
    if None in (PCr, Pi, aATP, bATP, gATP, PiEX):
        # If any of the required values is missing, skip calculation
        utils.log_warning("Not all required metabolites were found for additional 31P calculations.")
        return

    # Define basis (offset) values as in the MATLAB code
    PCr_basis = 0.0
    Pi_basis  = 4.84
    aATP_basis = -7.56
    bATP_basis = -16.18
    gATP_basis = -2.53
    PiEX_basis = 5.24

    # Calculate corrected chemical shift values (CS values)
    CS_PCr  = PCr_basis  + PCr  / 1000.0
    CS_Pi   = Pi_basis   + Pi   / 1000.0
    CS_aATP = aATP_basis + aATP / 1000.0
    CS_bATP = bATP_basis + bATP / 1000.0
    CS_gATP = gATP_basis + gATP / 1000.0
    CS_PiEX = PiEX_basis + PiEX / 1000.0

    # Define constants for the calculations
    pKA     = 6.73
    delta_a = 3.275
    delta_b = 5.685

    # Calculate PH (pH) using the corrected chemical shift of Pi.
    try:
        PH = pKA + math.log10((CS_Pi - delta_a) / (delta_b - CS_Pi))
    except Exception as e:
        utils.log_warning("Error computing PH:", e)
        PH = None

    # Calculate MGmm (Mg concentration in mM) using CS_bATP and CS_PCr.
    try:
        diff = CS_bATP - CS_PCr
        numerator   = math.pow(diff + 18.58, 0.42)
        denominator = math.pow(-15.74 - diff, 0.84)
        inner = (4.24 - math.log10(numerator / denominator))
        MGmm = math.pow(10, -inner) * 1000
    except Exception as e:
        utils.log_warning("Error computing MGmm:", e)
        MGmm = None

    # Calculate PiEX_conc using the corrected chemical shift of PiEX.
    try:
        PiEX_conc = pKA + math.log10((CS_PiEX - delta_a) / (delta_b - CS_PiEX))
    except Exception as e:
        utils.log_warning("Error computing PiEX_conc:", e)
        PiEX_conc = None

    # Append the calculated values to the LCModel concentration list
    if PH is not None:
        lcmdata['conc'].append({
            'name': 'PH',
            'c': PH,
            'SD': '',
            'c_cr': 0.0,
            'c_ref': 0.0
        })
    if MGmm is not None:
        lcmdata['conc'].append({
            'name': 'MGmm',
            'c': MGmm,
            'SD': '',
            'c_cr': 0.0,
            'c_ref': 0.0
        })
    if PiEX_conc is not None:
        lcmdata['conc'].append({
            'name': 'PiEX_conc',
            'c': PiEX_conc,
            'SD': '',
            'c_cr': 0.0,
            'c_ref': 0.0
        })

    # --- Generate synthetic subspectra (Gaussian curves) for plotting ---
    # The idea is to create a curve along the ppm axis for each calculated metabolite,
    # so that plot_coord will display them like the measured subspectra.

    # Use the ppm axis from lcmdata
    ppm = np.array(lcmdata.get('ppm', []))
    if ppm.size == 0:
        utils.log_error("No ppm data available to generate synthetic subspectra.")
        return

    # Use the measured spectrum to set a base amplitude
    spec = np.array(lcmdata.get('spec', []))
    base_amp = spec.max() if spec.size > 0 else 1.0
    amplitude = base_amp * 0.1  # set amplitude to 10% of maximum intensity
    sigma = 0.05  # arbitrary peak width

    # Choose centers for the synthetic peaks:
    # For these examples, we use the underlying CS values that were used in the calculations.
    center_PH   = CS_Pi    # For PH, we use the chemical shift from Pi
    center_MGmm = CS_bATP  # For MGmm, we use the bATP corrected shift
    center_PiEX = CS_PiEX  # For PiEX_conc, use the PiEX corrected shift

    def gaussian(x, center, amp, sigma):
        return amp * np.exp(-((x - center) ** 2) / (2 * sigma ** 2))

    # Generate the synthetic curves
    curve_PH   = gaussian(ppm, center_PH, amplitude, sigma)
    curve_MGmm = gaussian(ppm, center_MGmm, amplitude, sigma)
    curve_PiEX = gaussian(ppm, center_PiEX, amplitude, sigma)

    # Append these synthetic curves to the subspectra list so they get plotted.
    lcmdata.setdefault('subspec', []).append(curve_PH.tolist())
    lcmdata.setdefault('metab', []).append('PH')
    lcmdata['nfit'] = lcmdata.get('nfit', 0) + 1

    lcmdata.setdefault('subspec', []).append(curve_MGmm.tolist())
    lcmdata.setdefault('metab', []).append('MGmm')
    lcmdata['nfit'] += 1

    lcmdata.setdefault('subspec', []).append(curve_PiEX.tolist())
    lcmdata.setdefault('metab', []).append('PiEX_conc')
    lcmdata['nfit'] += 1

    # utils.log_debug("Calculated metabolites added: PH, MGmm, PiEX_conc")