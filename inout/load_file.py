def load_file(filepath):
    ext = os.path.splitext(filepath)[-1].lower()

    # Already NIfTI — no conversion needed
    if ext in [".nii", ".gz"]:
        data, header = load_nifti(filepath)
        final_ext = "nii"

    else:
        # Convert all supported formats to NIfTI first
        nifti_path = convert_to_nifti_with_spec2nii(filepath)

        if nifti_path is None:
            utils.log_error(f"Could not convert {filepath} to NIfTI.")
            return None, None, None, None

        data, header = load_nifti(nifti_path)
        final_ext = "nii"

    # Guess vendor from Sequence or file extension
    vendor = None
    if final_ext == "nii":
        if header and "Sequence" in header and header["Sequence"]:
            seq = header["Sequence"].lower()
            if "philips" in seq:
                vendor = "philips"
            elif "ge" in seq:
                vendor = "ge"
            elif "press" in seq or "svs" in seq or "siemens" in seq:
                vendor = "siemens"
        elif ext in [".sdat"]:
            vendor = "philips"
        elif ext in [".7"]:
            vendor = "ge"
        elif ext in [".dat", ".ima", ".dcm", ".rda"]:
            vendor = "siemens"

    # Ensure data is a list for consistent downstream processing
    if not isinstance(data, list):
        data = [data]

    return data, header, final_ext, vendor
