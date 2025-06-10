import numpy as np
import nibabel as nib
import json
import numpy as np
import os
import sys
import shutil
import glob
from interface import utils
import subprocess
# from spec2nii.other_formats import lcm_raw

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

def save_nifti(filepath, data, seq="PRESS"):
    while len(data.shape) > 1: data = data[0] # yeah
    img = nib.nifti1.Nifti1Image(np.array([[[data]]]), affine=np.eye(4), dtype=np.complex128)
    header = img.header
    header['descrip'] = (seq + "_" + str(data.te) + "ms_" + str(data.f0) + "Hz_" + str(len(data)) + "pts").encode('utf-8')
    if header['descrip'].nbytes > 80: 
        utils.log_warning("Description exceeds 80 bytes, truncating to fit NIfTI header limit.")
        header['descrip'] = header['descrip'][:80]
    metadata = {
        "SpectrometerFrequency": [data.f0],
        "EchoTime": data.te,
        "RepetitionTime": getattr(data, 'tr', None),
        "ResonantNucleus": [getattr(data, 'nucleus', "unknown")],
        "Sequence": seq,
    }
    json_metadata = json.dumps(metadata).encode('utf-8')
    ext = nib.nifti1.Nifti1Extension('mrs', json_metadata)
    img.header.extensions.append(ext)
    nib.save(img, filepath)