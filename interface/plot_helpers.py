import os
import numpy as np
from suspect import MRSData
from scipy.optimize import curve_fit
from inout.read_mrs import load_file
from inout.read_coord import ReadlcmCoord
from interface import utils

def plot_mrs(data, figure, title=None, fit_gaussian=False):
    if isinstance(data, MRSData): data = [data]
    if not isinstance(data, list): return
    data = [d for d in data if d is not None]
    if len(data[0].shape) > 1: # separate coils
        data2 = []
        for d in data:
            data2 = data2 + [d.inherit(d[i]) for i in range(d.shape[0])]
        data = data2
    if title is None: title = "Result"
    
    ax = figure.add_subplot(2, 1, 1)
    for d in data:
        ax.plot(d.time_axis(), np.real(d))
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Signal Intensity')
    ax = figure.add_subplot(2, 1, 2)
    for d in data:
        ax.plot(d.frequency_axis_ppm(), np.real(d.spectrum()))
    if fit_gaussian:
        avg = data[0].inherit(np.mean(data, axis=0))
        gaussparams, fwhm, fwhmhz = gaussian_fit(avg)
        gauss = gaussian(data[0].frequency_axis_ppm(), *gaussparams)
        ax.plot(data[0].frequency_axis_ppm(), gauss, ":r", label="gaussian fit")
        ax.text(gaussparams[1], gaussparams[0] / 2, f"FWHM = {fwhm:.2f} ppm\n= {fwhmhz:.2f} Hz", ha="center", va="center")
    ax.set_xlabel('Chemical shift (ppm)')
    ax.set_ylabel('Amplitude')
    ax.set_xlim((np.max(d.frequency_axis_ppm()), np.min(d.frequency_axis_ppm())))
    figure.suptitle(title)
    figure.tight_layout()

def get_mrs_info(data):
    f = data[0]
    info = ""
    if len(data[0].shape) == 1: # if coils are combined
        if len(data) == 1: info += f"\n\tSNR: {str(estimate_snr(data[0]))}"
        else: info += f"Mean SNR: {str(np.mean(np.array([estimate_snr(d) for d in data])))}"
    info += "\n"
    if hasattr(f, "np"): info += f"\n\tNumber of points: {f.np}"
    info += f"\n\tNumber of coils: {data[0].shape[0] if len(data[0].shape) > 1 else 1}"
    if "ave_per_rep" in f.metadata:
        info += f"\n\tNumber of shots per average: {f.metadata['ave_per_rep']}"
    info += f"\n\tNumber of averages: {len(data)}"
    if "ave_per_rep" in f.metadata:
        info += "→ {len(data) / f.metadata['ave_per_rep']}"
    info += "\n"
    if hasattr(f, "f0"): info += f"\n\tScanner frequency (MHz): {f.f0}"
    if hasattr(f, "dt"): info += f"\n\tDwell time (s): {f.dt}"
    if hasattr(f, "df"): info += f"\n\tFrequency delta (Hz): {f.df}"
    if hasattr(f, "sw"): info += f"\n\tSpectral Width (Hz): {f.sw}"
    if hasattr(f, "te"): info += f"\n\tEcho time (ms): {f.te}"
    if hasattr(f, "tr"): info += f"\n\tRepetition time (ms): {f.tr}"
    info += f"\n\tPPM range: {[f.hertz_to_ppm(-f.sw / 2.0), f.hertz_to_ppm(f.sw / 2.0)]}"
    info += "\n"
    if f.transform is not None:
        info += f"\n\tTransform:\n{f.transform}"
        info += f"\n\tCentre: {f.centre}"
    if hasattr(f, "metadata") and hasattr(f.metadata, "items"): info += "\n\tMetadata: " + "\n\t\t".join([f"{k}: {v}" for k, v in f.metadata.items()])
    return info

def estimate_snr(data: MRSData):
    ppms = data.frequency_axis_ppm()
    spec = data.spectrum()
    naapeak = np.max(np.real(spec[np.where(np.logical_and(ppms > 1.8, ppms < 2.2))]))
    return naapeak / estimate_noise_std(data)

def estimate_water_snr(data: MRSData):
    ppms = data.frequency_axis_ppm()
    spec = data.spectrum()
    water = np.real(spec[np.where(np.logical_and(ppms > 4.2, ppms < 5.2))])
    return np.max(water) / estimate_noise_std(data)

def estimate_noise_std(data: MRSData):
    ppms = data.frequency_axis_ppm()
    spec = data.spectrum()
    noise = np.real(spec[np.where(np.logical_and(ppms > 0, ppms < 0.5))])
    noise[np.isnan(noise)] = 0
    poly = np.polynomial.polynomial.Polynomial.fit(range(len(noise)), noise, 5)
    noise -= poly(range(len(noise)))
    return np.std(noise)

def gaussian(x, a, x0, sigma):
    return a * np.exp(-(x - x0)**2 / (2 * sigma**2))

def gaussian_fit(data: MRSData):
    spec = np.real(data.spectrum())
    gaussparams, _ = curve_fit(gaussian, data.frequency_axis_ppm(), spec, p0=[np.max(spec), 4.7, 0.01])
    fwhm = np.abs(2 * np.sqrt(2 * np.log(2)) * gaussparams[2])
    fwhmhz = fwhm * data.f0
    return gaussparams, fwhm, fwhmhz

def plot_coord(lcmdata, figure, title=None):
    if isinstance(lcmdata, str):
        filepath = lcmdata
        if filepath == "" or not os.path.exists(filepath):
            utils.log_error("Invalid filepath provided: " + filepath)
            return
        lcmdata = ReadlcmCoord(filepath)
        if title is None:
            title = filepath
    elif not isinstance(lcmdata, dict):
        utils.log_error("Invalid lcmdata format.")
        return
    if title is None:
        title = ".coord file"
    
    ax = figure.add_subplot(1, 1, 1)
    
    def getOffset(data, prevdata):
        return max(data) - min(prevdata) if prevdata else 0
    
    x_left = np.max(lcmdata['ppm'])
    margin = 0.05 * (np.max(lcmdata['ppm']) - np.min(lcmdata['ppm']))

    # Plot Residue
    if 'ppm' in lcmdata and 'residue' in lcmdata and lcmdata['ppm'] and lcmdata['residue']:
        ax.plot(lcmdata['ppm'], lcmdata['residue'], 'b-', label='Residue')
        residue_mean = np.mean(lcmdata["residue"]) if lcmdata["residue"] else 0
        ax.text(x_left+0.2, residue_mean, "Residue", rotation=0, va='center', ha='left', color='b') #4.25
    
    # Plot Spectrum and Fit
    if 'spec' in lcmdata and 'fit' in lcmdata and lcmdata['spec'] and lcmdata['fit']:
        padding = (max(lcmdata['fit']) - min(lcmdata['fit'])) * 0.1 if lcmdata['fit'] else 0
        offset = getOffset(lcmdata['fit'], lcmdata['residue']) + padding
        ax.plot(lcmdata['ppm'], [x - offset for x in lcmdata['spec']], 'k-', label="Spectrum")
        ax.plot(lcmdata['ppm'], [x - offset for x in lcmdata['fit']], 'r-', label="Fit")
        fit_mean = np.mean(lcmdata["fit"]) - offset if lcmdata["fit"] else 0
        ax.text(x_left+0.2, fit_mean, "Fit", rotation=0, va='center', ha='left', color='r')
    
    # Plot Baseline
    if 'baseline' in lcmdata and lcmdata['baseline']:
        padding = (max(lcmdata['baseline']) - min(lcmdata['baseline'])) * 0.1 if lcmdata['baseline'] else 0
        offset += getOffset(lcmdata['baseline'], lcmdata['fit']) + padding
        ax.plot(lcmdata['ppm'], [x - offset for x in lcmdata['baseline']], 'g-', label="Baseline")
        baseline_mean = np.mean(lcmdata["baseline"]) - offset if lcmdata["baseline"] else 0
        ax.text(x_left+0.2, baseline_mean, "Baseline", rotation=0, va='center', ha='left', color='g')
    
    # Plot Subspectra
    if 'subspec' in lcmdata and 'metab' in lcmdata and lcmdata['subspec'] and lcmdata['metab']:
        for metab, subspec in zip(lcmdata['metab'], lcmdata['subspec']):
            if len(subspec) != len(lcmdata['ppm']):
                utils.log_warning(f"Subspectra length mismatch for metabolite '{metab}'. Skipping.")
                continue
            padding = (max(subspec) - min(subspec)) * 0.1 if subspec else 0
            offset += getOffset(subspec, lcmdata['baseline']) + padding
            ax.plot(lcmdata['ppm'], [x - offset for x in subspec], label=metab)
            ax.text(x_left+0.2, -offset, metab, rotation=0, va='center', ha='left', color='k')
    
    ax.set_xlabel('ppm')
    ax.set_xlim(ax.get_xlim()[::-1])
    ax.get_yaxis().set_visible(False)
    figure.suptitle(title)
    figure.tight_layout()
    
    handles, labels = ax.get_legend_handles_labels()
    #if handles:
        #ax.legend()


def get_coord_info(lcmdata):
    dtab = '\n\t\t'
    info = (
        f"\n\tNumber of points: {len(lcmdata['ppm'])}\n\tNumber of metabolites: {len(lcmdata['conc'])} ({lcmdata['nfit']} fitted)\n\t0th-order phase: {lcmdata['ph0']}"
        f"\n\t1st-order phase: {lcmdata['ph1']}\n\tFWHM: {lcmdata['linewidth']}\n\tSNR: {lcmdata['SNR']}\n\tData shift: {lcmdata['datashift']}\n"
        f"""\tMetabolites:\n\t\t{dtab.join([f"{c['name']}: {str(c['c'])} (±{str(c['SD'])}%, {lcmdata['crnaa']}: {str(c['c_cr'])})" for c in lcmdata['conc']])}\n"""
    )
    return info

def read_file(filepath, canvas, text, coil_combine=False, fit_gaussian=False):
    canvas.clear()
    if filepath.lower().endswith(".coord"):
        f = ReadlcmCoord(filepath)
        if f is None: return
        text.SetValue(f"File: {filepath}\n{get_coord_info(f)}")
        plot_coord(f, canvas.figure, title=filepath)
    else:
        f, _, _, _= load_file(filepath)
        text.SetValue(f"File: {filepath}\n{get_mrs_info(f)}")
        if coil_combine: 
            if len(f[0].shape) > 1:
                from nodes._CoilCombinationAdaptive import coil_combination_adaptive
                d = {"input": f, "output": []}
                coil_combination_adaptive(d)
                f = d["output"]
        title = filepath.rsplit(os.path.sep, 1)[1]
        plot_mrs(f, canvas.figure, title=title, fit_gaussian=fit_gaussian)
    canvas.draw()