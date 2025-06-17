import processing.api as api
import copy
import numpy as np
from scipy.optimize import differential_evolution, minimize, dual_annealing, leastsq
import interface.utils as utils

class PhaseAlignment31P(api.ProcessingNode):
    def __init__(self, nodegraph, id):
        self.meta_info = {
            "label": "Phase Alignment (31P)",
            "author": "CIBM",
            "description": (
                "Performs frequency and phase alignment for 31P spectra "
            )
        }

        self.parameters = [
            # Zero-padding factor
            api.IntegerProp(
                idname="zp_factor",
                default=2,
                min_val=0,
                max_val=10,
                fpb_label="Zero-padding factor"
            ),
            # Line-broadening factor (Lorentzian)
            api.IntegerProp(
                idname="lb_factor",
                default=5,
                min_val=0,
                max_val=50,
                fpb_label="Line-broadening factor (e^(-f*pi))"
            ),
            # Reference range for alignment (ppm)
            api.VectorProp(
                idname="freqRange",
                default=(-0.6, 0.6, 0),
                labels=("Lower Bound (ppm)", "Higher Bound (ppm)"),
                min_vals=(-10, -10, 0),
                max_vals=(10, 10, 0),
                fpb_label="Reference peak range (ppm)"
            ),
            # Determine how the target spectrum is selected
            api.ChoiceProp(
                idname="median",
                default="True",
                choices=["True", "False"],
                fpb_label="Set target to median of input data"
            ),
            api.StringProp(
                idname="target",
                default="0",
                fpb_label="Set target to index of input data (if not median; starts at 0)"
            )
        ]
        
        super().__init__(nodegraph, id)

    def process(self, data):
        """
        1. Check toggles (freq, phase, 1st-order).
        2. Zero-padding.
        3. Line broadening.
        4. If align1stOrderPhase=True, apply first-order phase fix to target & each dataset.
        5. For the target: do peak-max zero-order phasing.
        6. Frequency & zero-order phase alignment via least-squares.
        7. Output the result.
        """
        _data = data["input"]

        utils.log_info("Running auto phase frequency correction (may take about 10 minutes)")

        def peak_max_phase_correction(data_obj,lower_bound, upper_bound):
            candidate_phases = np.arange(-180, 181, 2) #-180 181
            candidate_1p = np.arange(0, 0.004, 0.0000005)
            best_phase = 0
            best_1p = 0
            best_peak_amp = -np.inf
            freq_ppm = data_obj.frequency_axis_ppm()
            region_indices = np.where((freq_ppm >= lower_bound) & (freq_ppm <= upper_bound))[0]
            if len(region_indices) == 0:
                region_indices = np.arange(len(freq_ppm))
            i = 0
            p = 0
            for phase_deg in candidate_phases:
                if i >= 36:
                    p += 10
                    utils.log_info(f"{p}% done")
                    i = 0
                i += 2
                #print(phase_deg)
                for phase_1p in candidate_1p:
                    candidate = data_obj.adjust_phase(-np.deg2rad(phase_deg), first_phase = -phase_1p)
                    spec = np.real(candidate.spectrum())
                    current_peak = np.max(spec[region_indices])
                    if current_peak > best_peak_amp:
                        best_peak_amp = current_peak
                        best_phase = phase_deg
                        best_1p = phase_1p                            
                        #print("0: ", best_phase, "1: ", best_1p)
            #print(current_peak)
            return best_phase, best_1p
        
        

        def phase_correction_entropy(data_obj, c=1.0, m=1, num_de_runs=10):
            """
            Perform automatic phase correction using an entropy-minimization approach.
            First, a global search via differential evolution is performed, and then
            the best solution is refined using the Nelder–Mead simplex method.
            
            Parameters:
            data_obj : Object with a spectrum() method returning a complex spectrum,
                        and an adjust_phase() method that applies phase correction.
            c        : Penalty factor for negative absorption.
            m        : Order of derivative to use (typically 1 works well).
            
            Returns:
            best_params : [phc0, phc1] that minimize the objective.
                        phc0 is in degrees; phc1 is in the original units.
            """
            
            def entropy_objective(params, data_obj, m=1, c=1.0):
                """
                Entropy-based objective function for phase correction.
                Applies phase correction using:
                S_corr = S.adjust_phase(-np.deg2rad(phc0), first_phase=-phc1)
                then computes the Shannon-type entropy of the normalized derivative of
                the real part and adds a penalty for negative absorption.
                """
                phc0, phc1 = params
                S = data_obj.spectrum()  # complex spectrum array
                n = len(S)
                
                # Apply phase correction: convert phc0 from degrees to radians; use phc1 as-is.
                S_corr = data_obj.adjust_phase(-np.deg2rad(phc0), first_phase=-phc1)
                R = np.real(S_corr)
                
                # Compute derivative of order m (default is 1)
                if m == 1:
                    dR = np.gradient(R)
                else:
                    dR = R.copy()
                    for _ in range(m):
                        dR = np.gradient(dR)
                        
                abs_dR = np.abs(dR)
                total = np.sum(abs_dR)
                if total == 0:
                    return np.inf
                h = abs_dR / total  # normalized derivative
                
                epsilon = 1e-12
                entropy_val = np.sum(h * np.log(h + epsilon))
                
                # Penalty: fraction of points with negative absorption.
                penalty = np.sum(R < 0) / n
                
                return entropy_val + c * penalty

            # Define broad search bounds.
            bounds = [(-180, 180), (-0.1, 0.1)]
            
            solutions = []
            for seed in range(num_de_runs):
                # Global search with DE for each seed.
                result_de = differential_evolution(
                    entropy_objective, bounds,
                    args=(data_obj, m, c),
                    maxiter=10000,
                    disp=False,
                    seed=seed
                )
                de_solution = result_de.x
                
                # Local refinement using Nelder-Mead, starting from the DE solution.
                result_nm = minimize(
                    entropy_objective, de_solution,
                    args=(data_obj, m, c),
                    method='Nelder-Mead',
                    options={'maxiter': 10000, 'disp': False}
                )
                refined_solution = result_nm.x
                obj_value = entropy_objective(refined_solution, data_obj, m, c)
                solutions.append((refined_solution, obj_value))
                utils.log_debug(f"Run {seed}: phc0={refined_solution[0]:.4f}, phc1={refined_solution[1]:.4f}, obj={obj_value:.6f}")
            
            theoretical_candidate = (-82,0.0021991148575128553)

            result_theo = minimize(
                entropy_objective, theoretical_candidate,
                args=(data_obj, m, c),
                method='Nelder-Mead',
                options={'maxiter': 10000, 'disp': False}
            )
            refined_theo = result_theo.x
            obj_theo = entropy_objective(refined_theo, data_obj, m, c)
            solutions.append((refined_theo, obj_theo))
            utils.log_debug(f"Theoretical candidate refined: phc0 = {refined_theo[0]:.4f}, phc1 = {refined_theo[1]:.10f}, obj = {obj_theo:.6f}")

            # Select the best candidate among all runs.
            best_solution, best_obj = min(solutions, key=lambda x: x[1])
            utils.log_debug("Best overall solution:")
            utils.log_debug("  0th order phase: {:.4f} degrees".format(best_solution[0]))
            utils.log_debug("  1st order phase: {:.4f}".format(best_solution[1]))
            return best_solution
        
        def phase_correction_automics(data_obj, threshold=0.001, min_interval=15, max_interval_fraction=0.05, amp_frac=0.1):
            """
            Perform automatic phase correction using a tuned Automics algorithm with additional
            filtering based on amplitude.
            
            This method:
            1. Unwraps the phase and subtracts the phase at the dominant PCr peak.
            2. Restricts the "tail" intervals (beginning and end) to indices where the amplitude is below
                a fraction (amp_frac) of the maximum amplitude.
            3. Uses the median of the phase (and indices) in each tail to robustly estimate the local phase.
            4. Solves the linear model:
                    φ(k) = φ₀ + (k/N)·φ₁
                to obtain φ₀ (zero-order phase, returned in degrees and wrapped to [–180, 180]) and φ₁ (first-order phase).
            
            Parameters:
            data_obj           : Object with spectrum() and adjust_phase() methods.
            threshold          : Maximum allowed slope (radians/index) in the tail intervals.
            min_interval       : Minimum number of points to include in the tail interval.
            max_interval_fraction : Maximum fraction of total points to consider.
            amp_frac           : Fraction of the maximum amplitude used as a threshold for selecting low-signal points.
            
            Returns:
            (phc0, phc1)       : Zero-order phase (degrees, wrapped) and first-order phase.
            """
            # Obtain the complex spectrum, its length, and magnitude.
            S = data_obj.spectrum()
            N = len(S)
            mag = np.abs(S)
            
            # Unwrap phase and subtract the phase at the dominant (PCr) peak.
            full_phase = np.unwrap(np.angle(S))
            peak_index = np.argmax(mag)
            ref_phase = full_phase[peak_index]
            phase = full_phase - ref_phase

            # Define an amplitude threshold (e.g. 10% of maximum).
            amp_threshold = amp_frac * np.max(mag)
            
            # Determine maximum allowed interval length.
            max_interval = int(max_interval_fraction * N)
            if max_interval < min_interval:
                max_interval = min_interval

            # --- Beginning Tail ---
            # Start with the first min_interval points and then restrict to those with amplitude below amp_threshold.
            indices_begin = np.arange(min_interval)
            # While increasing interval length (up to max_interval) if the slope is within threshold.
            L1 = min_interval
            while L1 < max_interval:
                idx_range = np.arange(L1)
                # Only consider points with low amplitude.
                low_amp_idx = idx_range[mag[idx_range] < amp_threshold]
                if len(low_amp_idx) < min_interval:
                    # If not enough low-amplitude points, try a larger window.
                    L1 += 1
                    continue
                # Compute slope for these selected indices.
                p = np.polyfit(low_amp_idx, phase[low_amp_idx], 1)
                if abs(p[0]) > threshold:
                    break
                L1 += 1
            if L1 > min_interval:
                L1 = L1 - 1
            idx_begin = np.arange(L1)
            low_amp_begin = idx_begin[mag[idx_begin] < amp_threshold]
            if len(low_amp_begin) == 0:
                low_amp_begin = idx_begin  # fallback if none qualify
            ph1 = np.median(phase[low_amp_begin])
            k1 = np.median(low_amp_begin)
            
            # --- Ending Tail ---
            L2 = min_interval
            while L2 < max_interval:
                idx_range = np.arange(N - L2, N)
                low_amp_idx = idx_range[mag[idx_range] < amp_threshold]
                if len(low_amp_idx) < min_interval:
                    L2 += 1
                    continue
                p = np.polyfit(low_amp_idx, phase[low_amp_idx], 1)
                if abs(p[0]) > threshold:
                    break
                L2 += 1
            if L2 > min_interval:
                L2 = L2 - 1
            idx_end = np.arange(N - L2, N)
            low_amp_end = idx_end[mag[idx_end] < amp_threshold]
            if len(low_amp_end) == 0:
                low_amp_end = idx_end  # fallback if none qualify
            ph2 = np.median(phase[low_amp_end])
            k2 = np.median(low_amp_end)
            
            # Check that k2 is different from k1
            if k2 == k1:
                k2 = k1 + 1

            # Solve for φ₁: phi1 = N * (ph2 - ph1) / (k2 - k1)
            phi1 = N * (ph2 - ph1) / (k2 - k1)
            # Solve for φ₀: phi0 = ph1 - (k1/N)*phi1
            phi0 = ph1 - (k1 / N) * phi1
            
            # Convert φ₀ to degrees and wrap to [-180, 180].
            phi0_deg = np.rad2deg(phi0)
            phi0_wrapped = ((phi0_deg + 180) % 360) - 180
            
            utils.log_debug("Automics (filtered):")
            utils.log_debug("  L1 =", L1, "L2 =", L2, "k1 =", k1, "k2 =", k2)
            utils.log_debug("  ph1 =", ph1, "ph2 =", ph2)
            utils.log_debug("  phi0 (rad) =", phi0, "phi0 (deg) =", phi0_deg, "wrapped =", phi0_wrapped)
            utils.log_debug("  phi1 =", phi1)
            
            return phi0_wrapped, phi1


# Example usage:
# best_phase, best_first_order = phase_correction_entropy(data_obj, c=1.0, m=1)
        
        def peak_max_phase_correction_two_peaks(data_obj, pcr_bounds, atp_bounds, 
                                          weight_pcr=0.5, weight_atp=0.5,
                                          num_de_runs=5):
            """
            Optimize phase correction to maximize a combined metric of the PCr peak 
            (near 0 ppm) and the a-ATP peak (in the specified bounds) using multiple 
            differential evolution runs.
            
            Parameters:
            data_obj    : Object with methods adjust_phase(), spectrum(), and frequency_axis_ppm().
            pcr_bounds  : Tuple (pcr_lower_bound, pcr_upper_bound) for the PCr peak region.
            atp_bounds  : Tuple (atp_lower_bound, atp_upper_bound) for the a-ATP peak region.
            weight_pcr  : Weight for the PCr peak amplitude.
            weight_atp  : Weight for the a-ATP peak amplitude.
            num_de_runs : Number of independent DE runs.
            
            Returns:
            best_phase : Optimized 0th order phase (in degrees).
            best_1p    : Optimized 1st order phase.
            """
            
            def objective(params, data_obj, region_indices_pcr, region_indices_atp, weight_pcr, weight_atp, epsilon=1e-6):
                """
                Objective function that rewards a high ratio of the real peak amplitude to the 
                overall imaginary content in each region. This measure is scale invariant.
                """
                phase_deg, phase_1p = params
                candidate = data_obj.adjust_phase(-np.deg2rad(phase_deg), first_phase=-phase_1p)
                spec = candidate.spectrum()
                spec_re = np.real(spec)
                spec_im = np.imag(spec)
                
                # For the PCr region:
                ratio_pcr = np.max(spec_re[region_indices_pcr]) / (np.sum(np.abs(spec_im[region_indices_pcr])) + epsilon)
                # For the a-ATP region:
                ratio_atp = np.max(spec_re[region_indices_atp]) / (np.sum(np.abs(spec_im[region_indices_atp])) + epsilon)
                
                # We want to maximize the sum of the ratios, so we return the negative.
                return - (ratio_pcr + ratio_atp)
                        
            # Define search bounds.
            bounds = [(-180, 180), (0, 0.04)]
            
            # Get frequency axis and indices for the PCr and a-ATP regions.
            freq_ppm = data_obj.frequency_axis_ppm()
            region_indices_pcr = np.where((freq_ppm >= pcr_bounds[0]) & (freq_ppm <= pcr_bounds[1]))[0]
            region_indices_atp = np.where((freq_ppm >= atp_bounds[0]) & (freq_ppm <= atp_bounds[1]))[0]
            if len(region_indices_pcr) == 0:
                region_indices_pcr = np.arange(len(freq_ppm))
            if len(region_indices_atp) == 0:
                region_indices_atp = np.arange(len(freq_ppm))
            
            # Run multiple differential evolution searches.
            best_de_obj = np.inf
            best_de_params = None
            
            for seed in range(num_de_runs):
                result_de = differential_evolution(
                    objective, bounds,
                    args=(data_obj, region_indices_pcr, region_indices_atp, weight_pcr, weight_atp),
                    maxiter=2000, popsize=100, mutation=(0.5, 1.5), recombination=0.8,
                    tol=1e-7, polish=False, seed=seed, disp=False
                )
                if result_de.fun < best_de_obj:
                    best_de_obj = result_de.fun
                    best_de_params = result_de.x

            # Optionally include a theoretical candidate based on known TE, if available.
            if hasattr(data_obj, "te"):
                p1_theoretical = 2 * np.pi * data_obj.te * 1e-3  # Theoretical 1st order phase
                best_val_theo = np.inf
                best_phase_theo = None
                for phase_deg in np.linspace(-180, 180, 181):
                    params = [phase_deg, p1_theoretical]
                    val = objective(params, data_obj, region_indices_pcr, region_indices_atp, weight_pcr, weight_atp)
                    if val < best_val_theo:
                        best_val_theo = val
                        best_phase_theo = phase_deg
                theoretical_candidate = np.array([best_phase_theo, p1_theoretical])
                # If the theoretical candidate beats DE, adopt it.
                if objective(theoretical_candidate, data_obj, region_indices_pcr, region_indices_atp, weight_pcr, weight_atp) < best_de_obj:
                    best_de_params = theoretical_candidate
                    best_de_obj = objective(theoretical_candidate, data_obj, region_indices_pcr, region_indices_atp, weight_pcr, weight_atp)
                    utils.log_debug("Theoretical candidate adopted:", theoretical_candidate)
            
            utils.log_debug("Best DE result before local refinement:")
            utils.log_debug("  0th order phase: {:.4f}".format(best_de_params[0]))
            utils.log_debug("  1st order phase: {:.8f}".format(best_de_params[1]))
            
            # Refine the best DE result using a local optimizer.
            result_local = minimize(
                objective, best_de_params,
                args=(data_obj, region_indices_pcr, region_indices_atp, weight_pcr, weight_atp),
                bounds=bounds, method='L-BFGS-B'
            )
            
            best_params = result_local.x
            utils.log_debug("Optimized parameters after local refinement:")
            utils.log_debug("  0th order phase: {:.4f}".format(best_params[0]))
            utils.log_debug("  1st order phase: {:.8f}".format(best_params[1]))
            
            return best_params[0], best_params[1]

        try: 
            header = data["header"]
            xdim = header["CSIMatrix_Size[0]"]
            self.issvs = False
        except:
            self.issvs = True

        if self.issvs:
            # 2. Zero-padding
            zp_factor = self.get_parameter("zp_factor")
            if zp_factor != 0:
                zp_data = []
                for d in _data:
                    pad_len = int(np.floor(len(d) * zp_factor))
                    padding = np.zeros(pad_len, dtype=d.dtype)
                    out_d = d.inherit(np.concatenate((d, padding), axis=None))
                    zp_data.append(out_d)
                _data = zp_data

            # 3. Line broadening
            lb_factor = self.get_parameter("lb_factor")
            if lb_factor != 0:
                time_axis = _data[0].time_axis()
                exp_weight = np.exp(-time_axis * np.pi * lb_factor)
                lb_data = []
                for d in _data:
                    out_d = d.inherit(d * exp_weight)
                    lb_data.append(out_d)
                _data = lb_data

            self.freq_in = _data

            # 4. Build target
            if self.get_parameter("median") == "True":
                self.target = _data[0].inherit(np.median(_data, axis=0))
            else:
                idx = int(self.get_parameter("target"))
                if idx in range(len(_data)):
                    self.target = _data[idx]
                else:
                    self.target = _data[0]

            ppm_bounds = self.get_parameter("freqRange")[:-1]  # e.g. (lower, upper)
            lower_bound_ppm, upper_bound_ppm = ppm_bounds
            
            entropy_c = 0#self.get_parameter("entrop_c")
            entropy_m = 0#self.get_parameter("entropy_m")

            best_phase_deg, best_1p = peak_max_phase_correction(self.target,lower_bound_ppm, upper_bound_ppm) #phase_correction_automics(self.target) #-80, 0.0029579999999999997 #peak_max_phase_correction(self.target,lower_bound_ppm, upper_bound_ppm)#peak_max_phase_correction_two_peaks(self.target,(lower_bound_ppm, upper_bound_ppm), (6,9),1,1)
            
            self.target = self.target.adjust_phase(-np.deg2rad(best_phase_deg), first_phase = -best_1p)

            spec = np.real(self.target.spectrum())
            freq_axis = self.target.frequency_axis_ppm()
            max_index = np.argmax(spec)
            peak_ppm = freq_axis[max_index]
            freq_shift_Hz = -peak_ppm * self.target.f0
            self.target = self.target.adjust_frequency(-freq_shift_Hz)

            def residual(params, this_data, spectral_weights):
                """
                param structure:
                - if do_freq & do_phase:    params = (freqShift, zeroPhase)
                - if do_freq & not do_phase: params = (freqShift,)
                - if not do_freq & do_phase: params = (zeroPhase,)
                - if neither => no residual optimization anyway
                """
                idx_par = 0
                # 1) freq shift

                fs = params[idx_par]
                idx_par += 1
                this_data = this_data.adjust_frequency(-fs)


                # 2) zero-order phase
                zp = params[idx_par]
                idx_par += 1

                # apply them
                this_data = this_data.adjust_phase(-zp)

                diff_data = this_data - self.target
                spec_diff = diff_data.spectrum()

                # Weight by freqRange
                weighted_spectrum = spec_diff * spectral_weights
                weighted_spectrum = weighted_spectrum[weighted_spectrum != 0]

                # inverse FFT => time-domain residual
                resid_td = np.fft.ifft(np.fft.ifftshift(weighted_spectrum))

                # real & imaginary stacked
                out_vec = np.zeros(len(resid_td)*2)
                out_vec[:len(resid_td)] = resid_td.real
                out_vec[len(resid_td):] = resid_td.imag
                return out_vec

            freq_array = _data[0].frequency_axis()
            freqRange_Hz = [_data[0].ppm_to_hertz(ppm) for ppm in ppm_bounds]
            freqRange_Hz.sort()
            spectral_weights_global = np.logical_and(
                freqRange_Hz[0] < freq_array,
                freqRange_Hz[1] > freq_array
            )

            output = []
            #aligned_data = data["input"]

            for i, d in enumerate(_data):
                # Build param guesses
                # We only guess freqShift & zeroPhase if toggles are on:

                aligned_data = d.adjust_phase(0,first_phase = -best_1p)

                guess = (freq_shift_Hz, 0)
                # Fit
                out = leastsq(
                    residual,
                    x0=guess,
                    args=(d, spectral_weights_global),
                    maxfev=500
                )
                pars = out[0]
                # parse solution
                idx_par = 0
                final_freqShift = pars[idx_par]
                idx_par += 1

                final_zeroPhase = pars[idx_par]
                idx_par += 1

                # Apply final freq & zero-phase on top of what we already did
                aligned_data = aligned_data.adjust_frequency(-final_freqShift)
                aligned_data = aligned_data.adjust_phase(-final_zeroPhase)
                output.append(aligned_data)

            data["output"] = output

        else:
            _data = copy.deepcopy(data["input"])  # e.g. shape = (16, 16, 8, 1024)
            
            ppm_bounds = self.get_parameter("freqRange")[:-1]  # e.g. (lower, upper)
            lower_bound_ppm, upper_bound_ppm = ppm_bounds
            # print("PPM bounds: ", ppm_bounds)
            
            header = data["header"]
            xdim = header["CSIMatrix_Size[0]"]
            ydim = header["CSIMatrix_Size[1]"]
            zdim = header["CSIMatrix_Size[2]"]
            
            # Ensure _data has the expected dimensions
            np_data = np.array(_data)
            if np_data.ndim > 3:
                _data = _data[0]
                np_data = np.array(_data)
            
            # --- Determine the target voxel based on highest spectral area ---
            highest_spec_area_id = (0, 0, 0)
            target_voxel = _data[0][0][0]
            highest_spec_area = np.sum(np.real(target_voxel.spectrum()))
            for ix in range(xdim):
                for iy in range(ydim):
                    for iz in range(zdim):
                        d = _data[ix][iy][iz]
                        spec = np.real(d.spectrum())
                        spec_area = np.sum(spec)
                        if spec_area > highest_spec_area:
                            highest_spec_area_id = (ix, iy, iz)
                            highest_spec_area = spec_area
                            target_voxel = d
                            # print("spec area:", highest_spec_area)
            
            # --- Get best phase parameters from the target voxel ---
            best_phase_deg, best_1p = peak_max_phase_correction(
                target_voxel, lower_bound_ppm, upper_bound_ppm
            )
            # Apply the initial correction to the target to generate the reference spectrum.
            target = target_voxel.adjust_phase(-np.deg2rad(best_phase_deg), first_phase=-best_1p)
            
            # Compute spectral weights using the target's frequency axis and ppm bounds.
            freq_array = target.frequency_axis()
            freqRange_Hz = [target.ppm_to_hertz(ppm) for ppm in ppm_bounds]
            freqRange_Hz.sort()
            spectral_weights = np.logical_and(freq_array > freqRange_Hz[0],
                                              freq_array < freqRange_Hz[1])
            
            # --- Define a residual function for least squares refinement ---
            # Here params = (delta0, delta1) which are additional corrections
            def residual(params, data_obj, target, spectral_weights):
                delta0, delta1 = params
                # Apply additional phase corrections on top of the initial correction.
                corrected = data_obj.adjust_phase(-np.deg2rad(delta0), first_phase=-delta1)
                diff = corrected - target
                spec_diff = diff.spectrum()
                weighted_spec = spec_diff * spectral_weights
                # Remove any zeros (to avoid division issues)
                weighted_spec = weighted_spec[weighted_spec != 0]
                resid_td = np.fft.ifft(np.fft.ifftshift(weighted_spec))
                return np.concatenate([resid_td.real, resid_td.imag])
            
            # --- Loop over all voxels and perform LS optimization ---
            output = copy.deepcopy(data["input"])
            for ix in range(xdim):
                for iy in range(ydim):
                    for iz in range(zdim):
                        voxel = _data[ix][iy][iz]
                        # Start by applying the initial (target-derived) phase corrections.
                        initial = voxel.adjust_phase(-np.deg2rad(best_phase_deg), first_phase=-best_1p)
                        # For the target voxel itself, we keep the initial correction.
                        if (ix, iy, iz) == highest_spec_area_id:
                            final_corrected = initial
                        else:
                            # Use LS optimization to determine additional phase adjustments.
                            guess = (0.0, 0.0)
                            result = leastsq(residual, x0=guess, args=(initial, target, spectral_weights), maxfev=500)
                            delta0, delta1 = result[0]
                            final_corrected = initial.adjust_phase(-np.deg2rad(delta0), first_phase=-delta1)
                        # Save the final corrected voxel.
                        output[0][ix][iy][iz] = final_corrected
            data["output"] = output

        """else:
            #CSI
            _data = copy.deepcopy(data["input"])  # shape = (16, 16, 8, 1024) for example
            

            ppm_bounds = self.get_parameter("freqRange")[:-1]  # e.g. (lower, upper)
            lower_bound_ppm, upper_bound_ppm = ppm_bounds
            print("PPM bounds: ", ppm_bounds)

            header = data["header"]
            xdim = header["CSIMatrix_Size[0]"]
            ydim = header["CSIMatrix_Size[1]"]
            zdim = header["CSIMatrix_Size[2]"]

            np_data = np.array(_data)
            dim1 = np_data.shape[0]
            if dim1 != header["CSIMatrix_Size[0]"]:
                _data = _data[0]
                np_data = np_data[0]
            

            output = copy.deepcopy(data["input"])

            highest_spec_area_id = (0,0,0)
            highest_spec_area = np.sum(np.real(_data[highest_spec_area_id[0]][highest_spec_area_id[1]][highest_spec_area_id[2]].spectrum()))
            for ix in range(xdim):
                for iy in range(ydim):
                    for iz in range(zdim):

                        d = _data[ix][iy][iz]

                        spec = np.real(d.spectrum())
                        spec_area = np.sum(spec)
                        if spec_area > highest_spec_area:
                            highest_spec_area_id = (ix,iy,iz)
                            highest_spec_area = spec_area
                            print("spec area:", highest_spec_area)



            best_phase_deg, best_1p = peak_max_phase_correction(_data[highest_spec_area_id[0]][highest_spec_area_id[1]][highest_spec_area_id[2]],lower_bound_ppm, upper_bound_ppm)


            for ix in range(xdim):
                for iy in range(ydim):
                    for iz in range(zdim):
                        out_d = output[0][ix][iy][iz]

                        out_d = out_d.adjust_phase(-np.deg2rad(best_phase_deg),first_phase=-best_1p)

                        output[0][ix][iy][iz] = out_d

            data["output"] = output"""
        

            


    def plot(self, figure, data):
        """
        Custom plot code.
        """
        figure.suptitle(self.__class__.__name__)
        
        if self.issvs:
            xlim = (
                np.max(self.freq_in[0].frequency_axis_ppm()),
                np.min(self.freq_in[0].frequency_axis_ppm())
            )

            #  -- ROW 1 --
            # Panel 1: Input
            ax = figure.add_subplot(3, 6, (1,3))
            for d in data["input"]:
                ax.plot(d.frequency_axis_ppm(), np.real(d.spectrum()))
            ax.set_xlim(xlim)
            ax.set_xlabel("Chemical shift (ppm)")
            ax.set_ylabel("Amplitude")
            ax.set_title("Input")

            # Panel 2: Output
            ax = figure.add_subplot(3, 6, (4,6))
            for d in data["output"]:
                ax.plot(d.frequency_axis_ppm(), np.real(d.spectrum()))
            ax.set_xlim(xlim)
            ax.set_xlabel("Chemical shift (ppm)")
            ax.set_ylabel("Amplitude")
            ax.set_title("Aligned Output")
            """
            #  -- ROW 2 --
            # Panel 3: freq_in after final shifts
            ax = figure.add_subplot(3, 6, (7,9))
            for i, d in enumerate(self.freq_in):
                # Show the "final" alignment (if you want to replicate exactly how it ended up)
                #fs = self.freqShifts[i]
                #zp = self.zeroOrderPhases[i]
                fp = 2 * np.pi * d.te * 1e-3
                temp_d = d.adjust_phase(0., first_phase=-fp)  # if do_first_order
                #temp_d = temp_d.adjust_frequency(-fs)
                temp_d = temp_d.adjust_phase(-zp)
                ax.plot(temp_d.frequency_axis_ppm(), np.real(temp_d.spectrum()))
            ax.set_xlim(xlim)
            ax.set_xlabel("Chemical shift (ppm)")
            ax.set_ylabel("Amplitude")
            ax.set_title("ZP+LB data after final shifts")"""

            """
            # Panel 4: Frequency shifts
            ax = figure.add_subplot(3, 6, 10)
            ax.plot(self.freqShifts, marker="o")
            ax.set_xlabel("Index")
            ax.set_ylabel("Frequency shift (Hz)")
            if self.get_parameter("alignFreq") == "False":
                ax.set_title("Freq shifts (not used)")
            else:
                ax.set_title("Frequency shifts")"""
            """
            # Panel 5: Zero-order phase
            ax = figure.add_subplot(3, 6, 11)
            ax.plot(self.zeroOrderPhases, marker="o")
            ax.set_xlabel("Index")
            ax.set_ylabel("Zero-Order (rad)")
            if self.get_parameter("alignPhase") == "False":
                ax.set_title("0th Phase (not used)")
            else:
                ax.set_title("0th Phase")"""

            #  -- ROW 3 --
            # Panel 7: The target spectrum
            ax = figure.add_subplot(3, 6, (13,18))
            ax.plot(self.target.frequency_axis_ppm(), np.real(self.target.spectrum()), 'r')
            ax.set_xlim(xlim)
            ax.set_xlabel("Chemical shift (ppm)")
            ax.set_ylabel("Amplitude")
            ax.set_title("Reference Target Spectrum")

            figure.tight_layout()
        else:
            header = data["header"]
            CSIMatrix_Size = [header["CSIMatrix_Size[0]"],
                            header["CSIMatrix_Size[1]"],
                            header["CSIMatrix_Size[2]"]]


            ax = figure.add_subplot(1, 2, 1)


            d = data["input"][0]


            d_np = np.array(d)
            utils.log_info(f"Shape of the input data: {d_np.shape}")


            ax.plot(d.frequency_axis_ppm(), np.real(d[int(CSIMatrix_Size[0]/2)][int(CSIMatrix_Size[1]/2)][int(CSIMatrix_Size[2]/2)].spectrum()))
            ax.set_xlabel('ppm')
            ax.set_ylabel('Intensity')
            ax.set_title("Input central voxel spectrum")
            figure.tight_layout()


            ax = figure.add_subplot(1, 2, 2)


            d = data["output"][0]


            d_np = np.array(d)
            utils.log_info(f"Shape of the output data: {d_np.shape}")


            ax.plot(d.frequency_axis_ppm(), np.real(d[int(CSIMatrix_Size[0]/2)][int(CSIMatrix_Size[1]/2)][int(CSIMatrix_Size[2]/2)].spectrum()))
            ax.set_xlabel('ppm')
            ax.set_ylabel('Intensity')
            ax.set_title("Output central voxel spectrum")
            figure.tight_layout()

api.RegisterNode(PhaseAlignment31P, "PhaseAlignment31P")