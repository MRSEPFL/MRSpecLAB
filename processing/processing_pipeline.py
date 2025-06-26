import wx, os, sys, shutil, zipfile, time, subprocess
import numpy as np
import matplotlib
# import ants
import datetime
import traceback
import threading

from interface import utils
from inout.read_mrs import load_file
from inout.read_coord import ReadlcmCoord
from inout.read_header import Table
from inout.io_lcmodel import save_raw, read_control, save_control, save_nifti
from interface.plot_helpers import plot_mrs, plot_coord, read_file

def run_blocking(func, *args, **kwargs):
    event = threading.Event()
    result_container = {}
    def wrapper():
        result_container['result'] = func(*args, **kwargs)
        event.set()
    wx.CallAfter(wrapper)
    event.wait()
    return result_container['result']

def loadInput(self):
    self.save_lastfiles()
    self.filepaths = []
    for f in self.MRSfiles.filepaths:
        if not f.lower().endswith(".coord"): self.filepaths.append(f)
    if len(self.filepaths) == 0:
        utils.log_error("No files found")
        return False

    self.originalData = []
    self.header = None
    self.issvs = True
    vendor = None
    dtype = None

    for filepath in self.filepaths:
        try: data, header, dtype, vendor = load_file(filepath)
        except: utils.log_warning("Error loading file: " + filepath + "\n\t" + str(sys.exc_info()[0]))
        else:
            if data is None:
                utils.log_warning("Couldn't load file: " + filepath); continue
            if isinstance(data, list):
                self.originalData += data
            elif len(data.shape) > 1:
                for d in data: self.originalData.append(data.inherit(d))
            else: self.originalData.append(data)
            if header is None: utils.log_warning("Header not found in file: " + filepath)
            else:
                # check multi-voxel for rda data
                if dtype == "rda":
                    self.issvs = header["CSIMatrix_Size[0]"] == 1 and header["CSIMatrix_Size[1]"] == 1 and header["CSIMatrix_Size[2]"] == 1
                    if self.issvs: utils.log_debug(f"SVS data detected for {filepath}")
                    else: utils.log_debug(f"CSI data detected for {filepath}")
                if self.header is None: self.header = header
            utils.log_debug("Loaded file: " + filepath)
    
    if len(self.originalData) == 0:
        utils.log_error("No files loaded"); return False
    if self.header is None:
        utils.log_error("No header found"); return False
    
    nucleus = self.originalData[0].nucleus
    if nucleus in (None, 'unknown'):
        utils.log_error("Nucleus not found in data.")
        return False

    if nucleus == "31P" and self.issvs:
        has_phase_alignment = any("PhaseAlignment31P" in step.__class__.__name__ for step in self.steps) or any("TEBasedPhaseCorrecton31P" in step.__class__.__name__ for step in self.steps)
        if not has_phase_alignment:
            def dialog_func():
                dlg = wx.MessageDialog(self,
                    "31P data detected, but the current pipeline does not include the 'PhaseAlignment31P' step.\n"
                    "Would you like to load the standard 31P pipeline?",
                    "Pipeline Mismatch", wx.YES_NO | wx.ICON_QUESTION
                )
                response = dlg.ShowModal(); dlg.Destroy(); return response
            response = run_blocking(dialog_func)
            if response == wx.ID_YES:
                standard_pipeline_path = os.path.join(os.getcwd(), "31P_standard_pipeline.pipe")
                self.pipeline_frame.on_load_pipeline(event=None, filepath=standard_pipeline_path)

        if len(self.filepaths) > 1 and dtype not in ("dcm", "ima", "raw"):
            utils.log_warning("Multiple files given despite not in DICOM, IMA, or RAW format")

    self.originalWref = None
    wrefpath = None
    if len(self.Waterfiles.filepaths) > 1: utils.log_warning("Only one water reference is supported; choosing first one")
    if len(self.Waterfiles.filepaths) == 0: utils.log_warning("No water reference given")
    else: wrefpath = self.Waterfiles.filepaths[0]
    if wrefpath is not None:
        try: self.originalWref, _, _, _ = load_file(wrefpath)
        except: utils.log_warning("Error loading water reference: " + wrefpath + "\n\t" + str(sys.exc_info()[0]))
        else:
            if self.originalWref is None: utils.log_warning("Couldn't load water reference: " + wrefpath)
            else: utils.log_debug("Loaded water reference: " + filepath)

    utils.log_info(len(self.originalData), " MRS files and ", "no" if self.originalWref is None else "1", " water reference file loaded")

    # check coil combination
    if dtype != "rda": # "rda" is coil combined 
        if len(self.originalData[0].shape) > 1: #check if its voxel or coil dimension better
            if len(self.steps) == 0 or self.steps[0].GetCategory() != "COIL_COMBINATION":
                utils.log_warning("Coil combination needed for multi-coil data; performing adaptive coil combination")
                from nodes._CoilCombinationAdaptive import coil_combination_adaptive
                datadict = {"input": self.originalData, "output": [], "wref": self.originalWref, "wref_output": None}
                coil_combination_adaptive(datadict)
                self.originalData = datadict["output"]
                self.originalWref = datadict["wref_output"]
    
    self.dataSteps = [self.originalData]
    self.wrefSteps = [self.originalWref]
    self.headerSteps = [self.header] # added for transmit header, for reading MRSI data dimension in processing nodes
    self.last_wref = None

    # get sequence for proper raw file saving
    seqstr = None
    for key in ["SequenceString", "Sequence"]:
        if key in self.header.keys():
            seqstr = self.header[key]; break
    self.sequence = None
    if seqstr is None: utils.log_warning("Sequence not found in header")
    else:
        for k, v in utils.supported_sequences.items():
            for seq in v:
                if seq in seqstr:
                    self.sequence = k; break
        if self.sequence is not None:
            utils.log_info("Sequence detected: ", seqstr + " → " + self.sequence)

    # create output and work folders
    allfiles = [os.path.basename(f) for f in self.filepaths]
    if self.originalWref is not None:
        allfiles.append(os.path.basename(self.Waterfiles.filepaths[0]))
    if hasattr(self, 'batch_mode') and self.batch_mode and hasattr(self, 'participant_name') and self.participant_name:
        prefix = self.participant_name
        base = os.path.join(self.batch_study_folder, prefix)
    else:
        prefix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + self.filepaths[0].split(os.path.sep)[-1][:-len(dtype)-1]
        if not os.path.exists(self.outputpath_base): os.mkdir(self.outputpath_base)
        base = os.path.join(self.outputpath_base, prefix)
    i = 1
    self.outputpath = base
    while os.path.exists(self.outputpath):
        self.outputpath = base + f"({i})"
        i += 1
    os.mkdir(self.outputpath)

    # save header.csv
    if vendor is not None:
        table = Table()
        self.header = table.table_clean(vendor, dtype, self.header)
        table.populate(vendor, dtype, self.header)
        csvcols = ['Header', 'SubHeader', 'MRSinMRS', 'Values']
        table.MRSinMRS_Table[csvcols].to_csv(os.path.join(self.outputpath, "MRSinMRS_table.csv"))
    return True

# dataDict = {}
labels = []

def processStep(self, step, nstep):
    with self.data_lock:
        dataDict = {}
        dataDict["input"] = self.dataSteps[-1]
        dataDict["wref"] = self.wrefSteps[-1]
        dataDict["output"] = []
        dataDict["wref_output"] = []
        dataDict["header"] = self.headerSteps[-1] # added for transmit header

    wx.CallAfter(self.button_step_processing.Disable)
    if not self.fast_processing:
        wx.CallAfter(self.button_auto_processing.Disable)

    utils.log_debug("Running ", step.__class__.__name__)
    start_time = time.time()
    step.process(dataDict)
    utils.log_info("Time to process " + step.__class__.__name__ + ": {:.3f}".format(time.time() - start_time))
    with self.data_lock:
        self.dataSteps.append(dataDict["output"])
        if len(dataDict["wref_output"]) != 0:
            self.wrefSteps.append(dataDict["wref_output"])
        else: self.wrefSteps.append(dataDict["wref"])
        if "labels" in dataDict.keys() and dataDict["labels"] is not None:
            global labels; labels = dataDict["labels"]

    utils.log_debug("Plotting ", step.__class__.__name__)
    start_time = time.time()
    if self.save_plots_button.GetValue():
        steppath = os.path.join(self.outputpath, str(nstep) + step.__class__.__name__)
        if not os.path.exists(steppath): os.mkdir(steppath)
        figure = matplotlib.figure.Figure(figsize=(12, 9))
        # step plot
        step.plot(figure, dataDict)
        figure.suptitle(step.__class__.__name__)
        filepath = os.path.join(steppath, step.__class__.__name__ + ".pdf")
        figure.savefig(filepath, dpi=600, format = 'pdf')
        utils.log_debug("Saved "+ str(step.__class__.__name__) + " to " + filepath)
        # data plot
        figure.clear()
        if self.issvs:
            plot_mrs(dataDict["output"], figure)
            figure.suptitle("Result of " + step.__class__.__name__)
            filepath = os.path.join(steppath, "result.pdf")
            figure.savefig(filepath, dpi=600, format = 'pdf')
            utils.log_debug("Saved result of " + step.__class__.__name__ + " to " + filepath)
    # raw
    if self.save_raw_button.GetValue():
        steppath = os.path.join(self.outputpath, str(nstep) + step.__class__.__name__)
        if not os.path.exists(steppath): os.mkdir(steppath)
        filepath = os.path.join(steppath, "data")
        if not os.path.exists(filepath): os.mkdir(filepath)
        with self.data_lock:
            for i, d in enumerate(dataDict["output"]):
                if d is not None: save_raw(os.path.join(filepath, "metab_" + str(i+1) + ".RAW"), d, seq=self.sequence)
                else: utils.log_warning(f"Data for index {i} is None, skipping save.")
            for i, d in enumerate(dataDict["wref_output"]):
                if d is not None: save_raw(os.path.join(filepath, "water_" + str(i+1) + ".RAW"), d, seq=self.sequence)
                else: utils.log_warning(f"Water reference data for index {i} is None, skipping save.")
            save_nifti(os.path.join(filepath, "metab.nii"), dataDict['output'], seq=self.sequence)
            if dataDict["wref_output"] is not None and len(dataDict["wref_output"]) > 0:
                save_nifti(os.path.join(filepath, "water.nii"), dataDict["wref_output"], seq=self.sequence)

    # canvas plot
    if not self.fast_processing:
        wx.CallAfter(self.matplotlib_canvas.clear)
        wx.CallAfter(step.plot, self.matplotlib_canvas.figure, dataDict)
        wx.CallAfter(self.matplotlib_canvas.draw)
    utils.log_info("Time to plot " + step.__class__.__name__ + ": {:.3f}".format(time.time() - start_time))
    
def saveDataPlot(self):
    if getattr(self, 'skip_manual_adjustment', False):
        if self.issvs:
            filepath = os.path.join(self.outputpath, "Result.pdf")
            figure = matplotlib.figure.Figure(figsize=(12, 9))
            plot_mrs(self.dataSteps[-1], figure)
            figure.suptitle("Result")
            figure.savefig(filepath, dpi=600, format='pdf')
            utils.log_debug("Saved result to " + filepath)
        return

    if self.issvs:
        def man_adj_dialog():
            dlg = wx.MessageDialog(None, "Do you want to manually adjust frequency and phase shifts of the result?", "", wx.YES_NO | wx.ICON_INFORMATION)
            button_clicked = dlg.ShowModal(); dlg.Destroy(); return button_clicked
        button_clicked = run_blocking(man_adj_dialog)
        if button_clicked == wx.ID_YES:
            wx.CallAfter(self.matplotlib_canvas.clear)
            from processing.manual_adjustment import ManualAdjustment
            manual_adjustment = ManualAdjustment(self.dataSteps[-1], self.matplotlib_canvas, self.manual_adjustment_params)
            data, *self.manual_adjustment_params = manual_adjustment.run()
            self.dataSteps.append(data)
        elif getattr(self, 'batch_mode', False): self.skip_manual_adjustment = True
        filepath = os.path.join(self.outputpath, "Result.pdf")
        figure = matplotlib.figure.Figure(figsize=(12, 9))
        plot_mrs(self.dataSteps[-1], figure)
        figure.suptitle("Result")
        figure.savefig(filepath, dpi=600, format='pdf')
        utils.log_debug("Saved result to " + filepath)

def analyseResults(self):
    results = self.dataSteps[-1]
    self.basis_file = None
    nucleus = self.originalData[0].nucleus
    if nucleus is None or nucleus == 'unknown':
        utils.log_error("Nucleus not found in data."); return False
    if nucleus not in utils.larmor_frequencies:
        utils.log_error(f"Nucleus '{nucleus}' not supported. Supported nuclei: {list(utils.larmor_frequencies.keys())}"); return False
    larmor = utils.larmor_frequencies[nucleus]
    utils.log_debug(f"Determined nucleus {nucleus} from string {self.originalData[0].nucleus}.")

    wresult = None
    if nucleus == "1H":
        if len(self.wrefSteps) == 0: utils.log_warning("No water reference available for analysis.")
        elif self.wrefSteps[-1] is None or len(self.wrefSteps[-1]) == 0:
            utils.log_warning("wrefSteps is empty or improperly formatted. Water reference will be ignored.")
        else: wresult = self.wrefSteps[-1][0].inherit(np.mean(np.array(self.wrefSteps[-1]), axis=0))

    # Handle user-specified basis file
    self.basis_file = None
    if self.basis_file_user is not None:
        if os.path.exists(self.basis_file_user): self.basis_file = self.basis_file_user
        else: utils.log_warning(f"User-specififed basis set not found: {self.basis_file_user}.")
    
    # Basis file generation
    if self.basis_file is None:
        tesla = round(results[0].f0 / larmor, 0)
        basis_file_gen = None
        if self.sequence is not None:
            strte = str(results[0].te)
            if strte.endswith(".0"): strte = strte[:-2]
            if nucleus == "31P": basis_file_gen = f"{int(tesla)}T_{self.sequence}_31P_TE{strte}ms.BASIS"
            else: basis_file_gen = f"{int(tesla)}T_{self.sequence}_TE{strte}ms.BASIS"
            basis_file_gen = os.path.join(self.programpath, "lcmodel", "basis", basis_file_gen)
            utils.log_debug(f"Generated basis file name {basis_file_gen}.")
        else: utils.log_warning("Sequence not found, basis file not generated.")
        if basis_file_gen is not None and os.path.exists(basis_file_gen):
            def basis_dialog():
                dlg = wx.MessageDialog(None, basis_file_gen, "Basis set found, is it the right one?\n" + basis_file_gen, wx.YES_NO | wx.CANCEL | wx.ICON_INFORMATION)
                button_clicked = dlg.ShowModal(); dlg.Destroy(); return button_clicked
            button_clicked = run_blocking(basis_dialog)
            if button_clicked == wx.ID_YES: self.basis_file = basis_file_gen
            elif button_clicked == wx.ID_CANCEL: return False
    
    if self.basis_file is None:
        utils.log_warning(f"Generated basis set not found: {basis_file_gen}")
        run_blocking(self.fitting_frame.Show)
        wx.CallAfter(self.fitting_frame.SetFocus)
        while self.fitting_frame.IsShown(): time.sleep(0.1)
        self.basis_file = self.basis_file_user

    if self.basis_file is None:
        utils.log_error("No basis file specified"); return False
    utils.log_debug(f"Using basis set {self.basis_file}.")

    # Control file handling
    params = None
    if self.control_file_user is not None and os.path.exists(self.control_file_user):
        try: params = read_control(self.control_file_user)
        except Exception as e:
            utils.log_warning(f"Error reading user control file, attempting to use default control file.\n{e}")
            params = None
    else:
        self.control_file_user = os.path.join(self.programpath, "lcmodel", ("" if nucleus == "1H" else nucleus + "_") + "default.CONTROL")
        try:
            params = read_control(self.control_file_user)
            params.update({"DOECC": nucleus == "1H" and wresult is not None and "EddyCurrentCorrection" not in self.pipeline})
        except Exception as e:
            utils.log_warning(f"Error reading default control file: {e}.")
            params = None
    if params is None:
        utils.log_error("Control file not found or could not be read: ", self.control_file_user); return False
    utils.log_debug(f"Using control file {self.control_file_user}.")

    # Handle labels
    global labels
    if labels is None or len(labels) == 0:
        if self.issvs == True: labels = [str(i) for i in range(len(results))]
        else: labels = [str(i) for i in range(len(results[0]))]
    utils.log_debug(f"Using labels {labels}.")

    # Setup workpath
    workpath = os.path.join(os.path.dirname(self.outputpath_base), "temp")
    if os.path.exists(workpath): shutil.rmtree(workpath)
    os.mkdir(workpath)
    utils.log_debug(f"LCModel/ANTs work folder: {workpath}")

    # Segmentation and water concentration (only for 1H)
    wconc = None
    seg_files = [self.wm_file_user, self.gm_file_user, self.csf_file_user]
    if all(seg_files):
        if not all(os.path.exists(f) for f in seg_files):
            utils.log_error(f"Could not find segmentation files."); return False
        if not hasattr(results[0], "centre"):
            utils.log_error(f"Could not retrieve voxel location from input data."); return False
        centre = results[0].centre
        # ANTs and WX use conflicting C++ backends and crash when run in the same process..
        import pickle
        pkl_arg_path = os.path.join(workpath, "tmp.pkl")
        pkl_result_path = os.path.join(workpath, "tmp2.pkl")
        with open(pkl_arg_path, "wb") as f:
            pickle.dump([seg_files, centre, results[0].transform, pkl_result_path], f)
        if hasattr(sys, '_MEIPASS'): # running from pyinstaller executable
            helper_exe = os.path.join(sys._MEIPASS, "read_ants_image" + (".exe" if utils.iswindows() else ""))
            utils.log_debug(f"Calling ANTs subprocess with {helper_exe}.")
            result = subprocess.run([helper_exe, pkl_arg_path], capture_output=True, text=True)
        else: # running from source code
            utils.log_debug(f"Calling ANTs subprocess with {sys.executable}.")
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "./inout/read_ants_image.py")
            result = subprocess.run([sys.executable, script_path, pkl_arg_path], capture_output=True, text=True)
        if result.returncode != 0:
            utils.log_error(f"Analysing the segmentation images failed:\n{result.stdout}\n{result.stderr}"); return False
        with open(pkl_result_path, "rb") as f:
            wm_gm_csf_sums = pickle.load(f)
        wm_sum, gm_sum, csf_sum = tuple(wm_gm_csf_sums)
        seg_sum = wm_sum + gm_sum + csf_sum
        if seg_sum == 0:
            utils.log_warning("Segmentation sums to zero. Skipping water concentration calculation.")
            wconc = None
        else:
            f_wm = wm_sum / seg_sum
            f_gm = gm_sum / seg_sum
            f_csf = csf_sum / seg_sum
            wconc = (43300 * f_gm + 35880 * f_wm + 55556 * f_csf) / (1 - f_csf)
            utils.log_info("Calculated WM = ", f_wm, ", GM = ", f_gm, ", CSF = ", f_csf, " → Water conc. = ", wconc, ".")
    else:
        if nucleus != "1H": utils.log_info("Segmentation and water concentration calculation skipped for nucleus ", nucleus, ".")
        utils.log_warning("Segmentation files not provided, water concentration will be ignored.")

    # Create work folder and copy LCModel executable
    lcmodelfile = os.path.join(self.programpath, "lcmodel", "lcmodel")  # Linux exe
    if utils.iswindows(): lcmodelfile += ".exe"  # Windows exe

    utils.log_debug("Looking for executable here: ", lcmodelfile)
    if not os.path.exists(lcmodelfile):
        zippath = os.path.join(self.programpath, "lcmodel", "lcmodel.zip")
        if not os.path.exists(zippath):
            utils.log_error("lcmodel executable or zip not found")
            return False
        utils.log_info("lcmodel executable not found, extracting from zip")
        utils.log_debug("Looking for zip here: ", zippath)
        try:
            with zipfile.ZipFile(zippath, "r") as zip_ref:
                zip_ref.extractall(os.path.join(self.programpath, "lcmodel"))
            utils.log_info("lcmodel executable extracted from zip.")
        except Exception as e:
            utils.log_error(f"Failed to extract lcmodel from zip: {e}")
            return False

    # Ensure executable permissions on Linux
    if utils.islinux(): os.chmod(lcmodelfile, 0b111000000)

    # Copy LCModel executable to workpath
    if utils.iswindows(): command = f"""copy "{lcmodelfile}" "{workpath}" """
    else: command = f"""cp "{lcmodelfile}" "{workpath}" """
    result_copy = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
    utils.log_debug(f"Copy command output: {result_copy.stdout}")
    if result_copy.stderr:
        utils.log_warning(f"Copy command errors: {result_copy.stderr}")

    # Setup LCModel save path
    lcmodelsavepath = os.path.join(self.outputpath, "lcmodel")
    if os.path.exists(lcmodelsavepath):
        shutil.rmtree(lcmodelsavepath)
    os.mkdir(lcmodelsavepath)
    utils.log_debug(f"LCModel output folder: {lcmodelsavepath}")
    
    if self.issvs == True: temp_results = results
    else: temp_results = results[0]


    def processVoxel(result, label):
        """Process a single voxel for LCModel fitting."""
        label = "lcm" if label == "0" else label
        rparams = {
            "KEY": 123456789,
            "FILRAW": f"./{label}.RAW",
            "FILBAS": self.basis_file,
            "FILPRI": f"./{label}.print",
            "FILTAB": f"./{label}.table",
            "FILPS": f"./{label}.ps",
            "FILCOO": f"./{label}.coord",
            "FILCOR": f"./{label}.coraw",
            "FILCSV": f"./{label}.csv",
            "NUNFIL": result.np,
            "DELTAT": result.dt,
            "ECHOT": result.te,
            "HZPPPM": result.f0,
            "LCOORD": 9,
            "LCSV": 11,
            "LTABLE": 7
        }

        if params:
            params_upper = {k.upper(): v for k, v in params.items()}
            excluded_keys = [
                "FILRAW", "FILBAS", "FILPRI", "FILTAB",
                "FILPS", "FILCOO", "FILCOR", "FILCSV", "FILH2O",
                "NUNFIL", "DELTAT", "ECHOT", "HZPPPM"
            ]
            params_filtered = {
                k: v for k, v in params_upper.items()
                if k not in excluded_keys
            }
            rparams.update(params_filtered)
        if self.originalWref is not None and nucleus == "1H" and wresult is not None:
            rparams.update({
                "FILH2O": f"./{label}.H2O",
                "DOWS": "EddyCurrentCorrection" not in self.pipeline
            })
            if wconc is not None:
                rparams.update({"WCONC": wconc})
        else:
            rparams.update({"DOWS": False})
            rparams.update({"DOECC": False})
            rparams.pop("FILH2O", None)
            rparams.pop("WCONC", None)

        # Write CONTROL and RAW files
        try:
            base_path = os.path.join(workpath, label)
            save_control(base_path + ".CONTROL", rparams)
            save_raw(base_path + ".RAW", result, seq=self.sequence)
            save_nifti(base_path + ".nii", result, seq=self.sequence)
            if nucleus == "1H" and wresult is not None:
                save_raw(base_path + ".H2O", wresult, seq=self.sequence)
                save_nifti(base_path + ".water.nii", wresult, seq=self.sequence)
        except Exception as e:
            return utils.log_error(f"Error writing CONTROL or RAW files for {label}: {e}")

        # Run LCModel
        if utils.iswindows(): command = f"""cd "{workpath}" & lcmodel.exe < {label}.CONTROL"""
        else: command = f"""cd "{workpath}" && ./lcmodel < {label}.CONTROL"""
        utils.log_info(f"Running LCModel for {label}...")
        utils.log_debug(f"LCModel command: {command}")

        try:
            result_lcmodel = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            utils.log_info(f"LCModel Output for {label}: {os.linesep.join([l for l in result_lcmodel.stdout.splitlines() if l])}")
            expected_files = [f"{label}.table", f"{label}.ps", f"{label}.coord", f"{label}.csv"]
            missing_files = [f for f in expected_files if not os.path.exists(os.path.join(workpath, f))]
            if missing_files: utils.log_error(f"Missing LCModel output files for {label}: {missing_files}")
        except Exception as e: return utils.log_error(f"LCModel execution failed for {label}: {e}")

        if result_lcmodel.returncode != 0:
            return utils.log_error(f"LCModel failed for {label} with return code {result_lcmodel.returncode}")

        # Move output files to savepath
        savepath = os.path.join(lcmodelsavepath, label)
        try: os.mkdir(savepath)
        except Exception as e: return utils.log_error(f"Failed to create savepath for {label}: {e}")

        command_move = ""
        for f in os.listdir(workpath):
            if "lcmodel" in f.lower(): continue
            if utils.iswindows(): command_move += f""" & move "{os.path.join(workpath, f)}" "{savepath}" """
            else: command_move += f""" && mv "{os.path.join(workpath, f)}" "{savepath}" """

        if command_move:
            command_move = command_move[3:]  # Remove initial ' & ' or ' && '
            utils.log_debug("Moving files...\n\t" + command_move)
            try: subprocess.run(command_move, shell=True, check=True)
            except Exception as e:
                utils.log_warning(f"Failed to move files for {label}: {e}")
                utils.log_warning(f"Files remain in the temporary work folder: {workpath}")

        # Handle coord files
        filepath = os.path.join(savepath, f"{label}.coord")
        if os.path.exists(filepath):
            self.last_coord = filepath
            try:
                fcoord = ReadlcmCoord(filepath, nucleus)
                if nucleus == "31P":
                    from processing.add_calculated_metabolites import add_calculated_metabolites
                    add_calculated_metabolites(fcoord)
                figure = matplotlib.figure.Figure(figsize=(10, 10), dpi=600)
                plot_coord(fcoord, figure, title=filepath)
                read_file(filepath, self.matplotlib_canvas, self.file_text)
                filepath_pdf = os.path.join(savepath, "lcmodel.pdf")
                figure.savefig(filepath_pdf, dpi=600, format='pdf')
            except Exception as e: utils.log_warning(f"Failed to process coord file for {label}: {e}")
        else: utils.log_warning(f"LCModel output not found for {label}")

    if self.issvs:
        for result, label in zip(temp_results, labels):
            processVoxel(result, label)
    else:
        xdim, ydim, zdim, _ = np.array(temp_results).shape
        for i in range(xdim):
            for j in range(ydim):
                for k in range(zdim):
                    result_data = temp_results[i][j][k]
                    label = "_".join([str(i+1),str(j+1),str(k+1)])
                    processVoxel(result_data, label)

    shutil.rmtree(workpath) # Clean up workpath
    utils.log_info("LCModel processing complete")
    return True

def processPipeline(self):
    try:
        if self.current_step == 0:
            wx.CallAfter(self.plot_box.Clear)
            wx.CallAfter(self.plot_box.AppendItems, "")
            if not loadInput(self):
                utils.log_error("Error loading input")
                wx.CallAfter(self.reset)
                return
            
        if 0 <= self.current_step and self.current_step <= len(self.steps) - 1:
            # self.retrieve_pipeline() # bad way to update any changed parameters
            processStep(self, self.steps[self.current_step], self.current_step + 1)
            wx.CallAfter(self.plot_box.AppendItems, str(self.current_step + 1) + self.steps[self.current_step].__class__.__name__)
            if not self.fast_processing:
                wx.CallAfter(self.button_step_processing.Enable)
                wx.CallAfter(self.button_auto_processing.Enable)

        elif self.current_step == len(self.steps):
            saveDataPlot(self)
            if analyseResults(self):
                wx.CallAfter(self.plot_box.AppendItems, "lcmodel")
                self.pipeline_frame.on_save_pipeline(None, os.path.join(self.outputpath, "pipeline.pipe"), self.manual_adjustment_params)
                if self.manual_adjustment_params is not None:
                    with open(os.path.join(self.outputpath, "manual_adjustment.txt"), "w") as f:
                        f.write("Manual adjustment parameters; these values can also be loaded with the .pipe file:\n")
                        f.write("Frequency shift: " + str(self.manual_adjustment_params[0]) + " PPM\n" \
                                "0th order phase shift: " + str(self.manual_adjustment_params[1]) + "°\n" \
                                "1st order phase shift: " + str(self.manual_adjustment_params[2]) + "°/PPM\n")
            else:
                utils.log_error("Error analysing results")
                wx.CallAfter(self.reset)
                return

        self.current_step += 1
        wx.CallAfter(self.plot_box.SetSelection, self.current_step)
        if self.current_step > len(self.steps):
            wx.CallAfter(self.reset)
            return
        if not self.fast_processing:
            wx.CallAfter(self.button_terminate_processing.Enable)
    
    except Exception as e:
        tb_str = traceback.format_exc()
        utils.log_error(f"Pipeline error:\n{tb_str}")
        wx.CallAfter(self.button_terminate_processing.Enable)

def autorun_pipeline_exe(self):
    while self.fast_processing and self.current_step <= len(self.steps):
        processPipeline(self)