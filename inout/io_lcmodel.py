import json
import numpy as np
import nibabel as nib
from interface import utils

# adapted from suspect.io.lcmodel.save_raw because it gets SEQ errors
def save_raw(filepath, data, seq="PRESS"):
    with open(filepath, 'w') as fout:
        fout.write(" $SEQPAR\n")
        fout.write(" ECHOT = {}\n".format(data.te))
        fout.write(" HZPPPM = {}\n".format(data.f0))
        fout.write(f" SEQ = {seq}\n")
        fout.write(" $END\n")
        fout.write(" $NMID\n")
        fout.write(" FMTDAT = '(2E15.6)'\n")
        if data.transform is not None: fout.write(" VOLUME = {}\n".format(data.voxel_volume() * 1e-3))
        # else: print("Saving LCModel data without a transform, using default voxel volume of 1ml")
        fout.write(" $END\n")
        for point in np.nditer(data, order='C'):
            fout.write("  {0: 4.6e}  {1: 4.6e}\n".format(float(point.real), float(point.imag)))

def read_control(filepath):
    output = {}
    try:
        with open(filepath, "r") as file:
            lines = file.readlines()
    except Exception as e:
        utils.log_error(f"Failed to open CONTROL file {filepath}: {e}")
        return output  # Return empty dict on failure

    for line in lines:
        line = line.strip()
        if not line or line.startswith("$"):
            continue  # Skip empty lines and comments

        if '=' not in line:
            utils.log_warning(f"Malformed line in CONTROL file: {line}")
            continue  # Skip malformed lines

        key, value = line.split("=", 1)
        key = key.strip().upper()  # Ensure keys are uppercase
        value = value.strip()

        # Handle boolean values
        if value == "T":
            output[key] = True
        elif value == "F":
            output[key] = False
        # Handle quoted strings
        elif value.startswith("'") and value.endswith("'"):
            output[key] = value.strip("'")
        else:
            # Attempt to parse numerical values
            try:
                if ',' in value:
                    # Assume it's a tuple of floats
                    tuple_vals = tuple(map(float, value.split(",")))
                    output[key] = tuple_vals
                else:
                    # Try to convert to int
                    output[key] = int(value)
            except ValueError:
                try:
                    # Try to convert to float (handles scientific notation)
                    output[key] = float(value)
                except ValueError:
                    # Leave as string if all conversions fail
                    output[key] = value

    return output

# adapted from suspect.io.lcmodel.write_all_files because it unnecessarily overwrites entries
def save_control(filepath, params):
    with open(filepath, 'wt') as fout:
        fout.write(" $LCMODL\n")
        #fout.write(" KEY = 123456789\n")
        for key, value in params.items():
            if isinstance(value, str):
                value = f"'{value}'"
            elif isinstance(value, bool):
                value = 'T' if value else 'F'
            elif isinstance(value, tuple):
                value = str(value).strip("()'")
            fout.write(f" {key} = {value}\n")
        fout.write(" $END\n")

# find nifti spec at https://github.com/NIFTI-Imaging/nifti_clib/blob/master/niftilib/nifti1.h
def save_nifti(filepath, data, seq="unknown_seq"):
    if isinstance(data, list):
        if len(data) == 0: return utils.log_error(f"Data list is empty, cannot save {filepath}.")
        if not isinstance(data[0], np.ndarray):
            return utils.log_error(f"Data is a list but not a numpy array, cannot save {filepath}.")
    elif isinstance(data, np.ndarray): data = [data]
    else: return utils.log_error(f"Data is not a list or numpy array, cannot save {filepath}.")
    # handle possible placeholders in data
    for i, d in enumerate(data):
        if d is not None:
            refi = i; break
    for i, d in enumerate(data):
        if d is None: data[i] = np.zeros_like(data[refi])
    affine = data[0].transform if hasattr(data[0], 'transform') and data[0].transform is not None else np.eye(4)
    img = nib.nifti1.Nifti1Image(np.array(data).swapaxes(0, 1).reshape((1, 1, 1, len(data[0]), len(data))), affine=affine, dtype=np.complex128)
    img.header['pixdim'][4] = data[0].dt * 1e3 # ms
    img.header['xyzt_units'] = 16 + 2 # 16: ms, 2: mm
    img.header['datatype'] = 1792 # DT_COMPLEX128
    img.header['intent_name'] = "mrs_v0_9"
    img.header['descrip'] = (seq + "_" + str(data[0].te) + "ms_" + str(round(data[0].f0, 1)) + "Hz_" + str(len(data[0])) + "pts").encode('utf-8')
    if img.header['descrip'].nbytes > 80: img.header['descrip'] = img.header['descrip'][:80]
    metadata = {
        "SpectrometerFrequency": [data[0].f0], # MHz
        "EchoTime": data[0].te, # ms
        "RepetitionTime": getattr(data[0], 'tr', None), # ms
        "ResonantNucleus": [getattr(data[0], 'nucleus', "unknown")],
        "Sequence": seq,
        "dim_5": "DIM_MEAS"
    }
    img.header.extensions.append(nib.nifti1.Nifti1Extension('mrs', json.dumps(metadata).encode('utf-8')))
    nib.save(img, filepath)