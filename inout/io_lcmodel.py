import json
import numpy as np
import nibabel as nib
from interface import utils

# adapted from suspect.io.lcmodel.save_raw because it gets SEQ errors
def save_raw(filepath, data, seq="sSPECIAL"):
    """
    Write LCModel .RAW that LCModel accepts:
      $SEQPAR: ECHOT (ms), HZPPPM (MHz), SEQ
      $NMID:   FMTDAT only (+ optional VOLUME in mL)
      then real/imag pairs per FID point.
    """
    import numpy as np

    # --- coerce to complex and flatten ---
    a = np.asarray(data)
    if a.dtype.kind in "iu":     # ints -> float -> complex
        a = a.astype(np.float64)
    if a.dtype.kind == "f":      # real -> complex
        a = a + 0j
    elif a.dtype.kind != "c":
        raise TypeError(f"save_raw: unsupported dtype {a.dtype}")
    fid = a.ravel(order="C")

    # clean NaN/Inf safely (avoid complex kwarg quirk)
    r = np.nan_to_num(fid.real, nan=0.0, posinf=0.0, neginf=0.0)
    i = np.nan_to_num(fid.imag, nan=0.0, posinf=0.0, neginf=0.0)

    # --- pull metadata from object if available ---
    te_ms = getattr(data, "te", None)              # ms
    f0 = getattr(data, "f0", None)                 # Hz or MHz
    if f0 is not None and float(f0) > 1e5:         # if Hz, convert to MHz
        hzpppm_mhz = float(f0) / 1e6
    else:
        hzpppm_mhz = float(f0) if f0 is not None else None

    volume_ml = None
    if hasattr(data, "voxel_volume") and callable(getattr(data, "voxel_volume")):
        vol_mm3 = data.voxel_volume()
        if vol_mm3 is not None:
            volume_ml = float(vol_mm3) * 1e-3      # mm^3 -> mL

    # --- write text file (ASCII, no BOM) ---
    with open(filepath, "w", newline="\n") as f:
        # $SEQPAR block (exactly as LCModel expects)
        f.write("$SEQPAR\n")
        if te_ms is None:
            raise ValueError("save_raw: missing TE (ms) on data.te")
        if hzpppm_mhz is None:
            raise ValueError("save_raw: missing spectrometer frequency on data.f0 (Hz or MHz)")
        f.write(f" ECHOT = {te_ms:.6g}\n")
        f.write(f" HZPPPM = {hzpppm_mhz:.9f}\n")   # print enough precision
        f.write(f" SEQ = {seq}\n")
        f.write(" $END\n")

        # $NMID block: only FMTDAT (+ optional VOLUME)
        f.write("$NMID\n")
        f.write(" FMTDAT = '(2E15.6)'\n")
        if volume_ml is not None:
            f.write(f" VOLUME = {volume_ml:.6g}\n")
        f.write(" $END\n")

        # data: real imag per line
        for rr, ii in zip(r, i):
            f.write(f"  {rr: 4.6e}  {ii: 4.6e}\n")
            
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
    """
    Save complex MRS data to NIfTI with shape (1, 1, 1, n_pts, n_meas).
    - Keeps your existing units/metadata:
        * pixdim[4] in ms, xyzt_units = ms + mm
        * metadata keys identical to your current function
    - Auto-detects spectral axis; flattens everything else into the measurement axis.
    - Uses NIfTI-1 unless a dim > 32767, then auto-switches to NIfTI-2.
    - Accepts: np.ndarray or list[np.ndarray]; complex or real.
    """
    import json
    import numpy as np
    import nibabel as nib
    from interface import utils

    # ---- Normalize input to list of arrays ----
    if isinstance(data, np.ndarray):
        data_list = [data]
    elif isinstance(data, list) and len(data) > 0:
        data_list = data
    else:
        return utils.log_error(f"Data is not a list or numpy array, cannot save {filepath}.")

    # Replace None with zeros (like your original behavior)
    refi = next((i for i, d in enumerate(data_list) if d is not None), None)
    if refi is None:
        return utils.log_error(f"Data list is empty or all None, cannot save {filepath}.")
    for i, d in enumerate(data_list):
        if d is None:
            data_list[i] = np.zeros_like(data_list[refi])

    # Helper: convert to complex ndarray and clean NaN/Inf
    def _to_complex(a):
        a = np.asarray(a)
        if a.ndim == 0:
            return None
        if a.dtype.kind in "iu":  # integers/unsigned
            a = a.astype(np.float64, copy=False)
        if a.dtype.kind in "f":   # real floats
            a = a + 0j
        elif a.dtype.kind != "c":  # not complex/real/int
            return None
        # Clean NaN/Inf on real/imag separately
        r = np.nan_to_num(a.real, nan=0.0, posinf=0.0, neginf=0.0)
        i = np.nan_to_num(a.imag, nan=0.0, posinf=0.0, neginf=0.0)
        return r + 1j * i

    # Heuristic to choose spectral axis (prefer common point counts; else largest axis)
    COMMON_PTS = (8192, 4096, 2048, 1024, 512, 256)

    def _spec_axis(arr):
        if arr.ndim == 1:
            return 0
        # prefer axis whose size is in COMMON_PTS; if multiple, take the largest
        sizes = list(arr.shape)
        candidates = [ax for ax, sz in enumerate(sizes) if sz in COMMON_PTS]
        if candidates:
            # choose the one with largest size among candidates
            mx = max(candidates, key=lambda ax: sizes[ax])
            return int(mx)
        # fallback: largest axis
        return int(np.argmax(sizes))

    # ---- Build (n_meas, n_pts) matrix ----
    blocks = []
    n_pts_ref = None
    for idx, d in enumerate(data_list):
        a = _to_complex(d)
        if a is None:
            return utils.log_error(f"Unsupported dtype/shape for entry {idx}: {type(d)} {getattr(d, 'dtype', None)}")

        ax = _spec_axis(a)
        n_pts = int(a.shape[ax])
        # move spectral axis last, then collapse others into 'measurement'
        b = np.moveaxis(a, ax, -1).reshape(-1, n_pts)  # (n_meas_local, n_pts)

        if n_pts_ref is None:
            n_pts_ref = n_pts
        elif n_pts != n_pts_ref:
            return utils.log_error(f"Inconsistent spectral lengths across entries: {n_pts_ref} vs {n_pts} (entry {idx}).")

        blocks.append(b)

    meas = np.concatenate(blocks, axis=0)  # (n_meas, n_pts)
    n_meas, n_pts = meas.shape

    # ---- Target 5D layout: (1,1,1,n_pts,n_meas) ----
    arr5d = meas.T[np.newaxis, np.newaxis, np.newaxis, :, :]  # complex128

    # ---- Choose NIfTI-1 vs NIfTI-2 ----
    use_nifti2 = (n_pts > 32767) or (n_meas > 32767)
    img_cls = nib.Nifti2Image if use_nifti2 else nib.Nifti1Image

    # ---- Affine & metadata source ----
    meta_src = data_list[0]
    affine = getattr(meta_src, 'transform', None)
    if affine is None:
        affine = np.eye(4)

    img = img_cls(arr5d.astype(np.complex128, copy=False), affine)

    # ---- Header: keep your units and fields ----
    hdr = img.header
    # time step in **ms** to match your pipeline (pixdim[4] and xyzt_units)
    dt = getattr(meta_src, 'dt', None)
    if dt is not None:
        try:
            hdr['pixdim'][4] = float(dt) * 1e3  # ms
        except Exception:
            hdr['pixdim'][4] = 0.0
    hdr['xyzt_units'] = np.uint8(16 + 2)  # 16: ms, 2: mm
    hdr['datatype'] = np.uint16(1792)     # DT_COMPLEX128
    hdr['intent_name'] = "mrs_v0_9"

    te = getattr(meta_src, 'te', None)
    f0 = getattr(meta_src, 'f0', None)
    desc = f"{seq}_{te}ms_{f0}Hz_{n_pts}pts"
    hdr['descrip'] = str(desc)[:79].encode('utf-8')

    # ---- Embedded JSON extension (keys unchanged) ----
    metadata = {
        "SpectrometerFrequency": [getattr(meta_src, 'f0', None)],  # assumed MHz in your pipeline
        "FieldStrength": getattr(meta_src, 'fieldstrength', 3.0),  # Tesla
        "EchoTime": getattr(meta_src, 'te', None),                 # ms (keep as you had)
        "RepetitionTime": getattr(meta_src, 'tr', None),           # ms (keep as you had)
        "ResonantNucleus": [getattr(meta_src, 'Nucleus', "1H")],
        "Sequence": seq,
        "dim_5": "DIM_MEAS"
    }
    # drop None for clean JSON
    metadata = {k: v for k, v in metadata.items() if v is not None}

    img.header.extensions.append(
        nib.nifti1.Nifti1Extension(44, json.dumps(metadata).encode('utf-8'))
    )

    # ---- Save NIfTI ----
    nib.save(img, filepath)

    # ---- Sidecar JSON next to .nii/.nii.gz ----
    if filepath.endswith(".nii.gz"):
        json_path = filepath[:-7] + ".json"
    elif filepath.endswith(".nii"):
        json_path = filepath[:-4] + ".json"
    else:
        json_path = filepath + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
