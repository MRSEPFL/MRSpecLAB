def convert_to_nifti_with_spec2nii(filepath, out_dir="/tmp/mrs_nifti", output_basename="converted"):
    os.makedirs(out_dir, exist_ok=True)
    ext = os.path.splitext(filepath)[-1].lower()
    cmd = []
    
    try:
        if ext == ".dat":
            # Siemens Twix
            cmd = ["spec2nii", "twix", "-e", "image", "-j", "-f", output_basename, "-o", out_dir, filepath]

        elif ext in [".ima", ".dcm"]:
            # Siemens or UIH DICOM
            cmd = ["spec2nii", "dicom", "-j", "-f", output_basename, "-o", out_dir, filepath]

        elif ext == ".sdat":
            # Philips SDAT/SPAR
            spar = filepath.lower().replace(".sdat", ".spar")
            if not os.path.exists(spar):
                utils.log_error(f"Missing SPAR file: {spar}")
                return None
            cmd = ["spec2nii", "philips", "-j", "-f", output_basename, "-o", out_dir, filepath, spar]

        elif ext == ".7":
            # GE P-file
            cmd = ["spec2nii", "ge", "-j", "-f", output_basename, "-o", out_dir, filepath]

        elif ext == ".rda":
            # Siemens RDA
            cmd = ["spec2nii", "siemens", "--rda", "-j", "-f", output_basename, "-o", out_dir, filepath]

        elif ext == ".raw":
            # LCModel .RAW
            cmd = ["spec2nii", "raw", "-j", "-f", output_basename, "-o", out_dir, filepath]

        elif ext in [".txt", ".mrui"]:
            # jMRUI or text
            cmd = ["spec2nii", "jmrui", "-j", "-f", output_basename, "-o", out_dir, filepath]

        else:
            utils.log_warning(f"Unsupported extension: {ext}")
            return None

        subprocess.run(cmd, check=True)

    except subprocess.CalledProcessError as e:
        utils.log_error(f"spec2nii failed for {filepath}: {e}")
        return None

    # Find the resulting .nii/.nii.gz file
    for f in os.listdir(out_dir):
        if f.startswith(output_basename) and (f.endswith(".nii") or f.endswith(".nii.gz")):
            return os.path.join(out_dir, f)

    utils.log_error(f"No NIfTI file found after spec2nii conversion for {filepath}")
    return None
