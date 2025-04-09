"""import wx
import os
import glob
import inspect
import importlib.util
import threading
import pickle
import shutil

from interface import utils
from interface.pipeline_frame import PipelineFrame
from interface.fitting_frame import FittingFrame
from interface.main_layout import LayoutFrame
from interface.plot_helpers import plot_coord, get_coord_info
from processing.processing_pipeline import processPipeline, autorun_pipeline_exe
from inout.read_coord import ReadlcmCoord"""

import wx
import os
import glob
import inspect
import importlib.util
import threading
import pickle
import shutil


import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import nibabel as nib
from scipy.ndimage import rotate, zoom
#import cv2
#from skimage import measure

from interface.metabolite_map_frame import MetaboliteMapParameterDialog
from processing.get_mapping import create_brain_mask


from interface import utils
from interface.pipeline_frame import PipelineFrame
from interface.fitting_frame import FittingFrame
from interface.main_layout import LayoutFrame
from interface.plot_helpers import plot_coord, get_coord_info#, plot_ext
from processing.processing_pipeline import processPipeline, autorun_pipeline_exe
from inout.read_coord import ReadlcmCoord
from inout.group_files_by_header import group_files_by_header, group_water_files_by_header

class MainFrame(LayoutFrame):

    def __init__(self, *args, **kwds):
        LayoutFrame.__init__(self, *args, **kwds)

        utils.init_logging(self.info_text)
        utils.set_debug(False)
        self.debug_button.SetValue(False)

        self.current_step = 0
        self.basis_file = None
        self.basis_file_user = None
        self.control_file_user = None
        self.wm_file_user = None
        self.gm_file_user = None
        self.csf_file_user = None

        self.skip_manual_adjustment = False

        self.batch_mode = False      # Will be True when "Run in Batch Mode" is toggled.
        self.batch_folder = None     # Will store the path to the batch system folder.
        self.batch_participants = [] # A list of participant folder paths.
        
        #self.background_image = self.load_background_image() #check what it does

        self.param = {
            "vmin": None,
            "vmax": None,
        }

        self.brain_image = {
            "selected_img_path": None,
            "selected_img": None,
            "selected_img_view": None,
            "slice_index": None,
            "selected_img_rotation": None,
        }


        self.data_to_plot = {
            "dir": None,
            "metab_list": None,
            "metab_to_plot": None,
            "metab_ref": None,
            "dim": None,
            "slice": None,
            "coord": None,
            "sz": None,
            "use_ref": None,
            "crlb_threshold": None,
            "scaling": None,
            "conc_map_to_plot": None,
        }

        self.external_nodes_library = os.path.join(os.getcwd(), "customer_nodes")
        try:
            if not os.path.exists(self.external_nodes_library): os.mkdir(self.external_nodes_library)
        except:
            self.on_open_external_nodes(wx.PyEvent())
        self.copy_customer_processing_scripts()


        self.outputpath_base = os.path.join(os.getcwd(), "output")
        try:
            if not os.path.exists(self.outputpath_base): os.mkdir(self.outputpath_base)
        except:
            self.on_change_output(wx.PyEvent())
        self.outputpath = self.outputpath_base
        self.load_lastfiles()

        self.retrieve_steps() # dictionary of processing steps definitions
        self.pipeline_frame = PipelineFrame(parent=self) # /!\ put this after retrieve_steps
        self.pipeline_frame.Hide()
        self.fitting_frame = FittingFrame(parent=self)
        self.fitting_frame.Hide()
        self.retrieve_pipeline()

        self.metabolite_map_frame = MetaboliteMapParameterDialog(parent=self) # /!\ put this after retrieve_steps
        self.metabolite_map_frame.Hide()

        self.load_brain_image()
        self.update_map()

        self.CreateStatusBar(1)
        self.update_statusbar()

        pipeline_filepath = os.path.join(os.getcwd(), "lastpipeline.pipe")
        if os.path.exists(pipeline_filepath):
            self.pipeline_frame.on_load_pipeline(event=None, filepath=pipeline_filepath)

        self.Bind(wx.EVT_CLOSE, self.on_close) # save last files on close
        self.Bind(wx.EVT_BUTTON, self.on_reset, self.button_terminate_processing)
        self.Bind(wx.EVT_BUTTON, self.on_autorun_processing, self.button_auto_processing)
        self.Bind(wx.EVT_BUTTON, self.on_open_output_folder, self.folder_button)
        self.Bind(wx.EVT_BUTTON, self.on_open_pipeline, self.pipeline_button)
        self.Bind(wx.EVT_BUTTON, self.on_open_external_nodes, self.extenal_nodes)
        self.Bind(wx.EVT_BUTTON, self.on_change_output, self.change_output_button)
        self.Bind(wx.EVT_BUTTON, self.on_open_fitting, self.fitting_button)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_show_debug, self.show_debug_button)
        self.Bind(wx.EVT_CHECKBOX, self.on_toggle_debug, self.debug_button)
        self.Bind(wx.EVT_BUTTON, self.on_reload, self.reload_button)
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.Bind(wx.EVT_BUTTON, self.on_button_step_processing, self.button_step_processing)
        self.Bind(wx.EVT_COMBOBOX, self.on_plot_box_selection)
        self.Bind(wx.EVT_BUTTON, self.on_open_metabolite_map_plot, self.button_nplot)

        self.Bind(wx.EVT_BUTTON, self.on_create_batch, self.create_batch_button)
        self.Bind(wx.EVT_BUTTON, self.on_load_batch, self.load_batch_button)
        self.Bind(wx.EVT_CHECKBOX, self.on_toggle_batch, self.run_batch_toggle)

        self.on_show_debug(None)
        self.reset()

    def on_reset(self, event=None):
        self.processing = False
        self.fast_processing = False
        self.button_terminate_processing.Disable()
        self.button_step_processing.Enable()
        self.button_auto_processing.Enable()
        if self.current_step >= len(self.steps):
            self.button_step_processing.SetBitmap(self.run_bmp)
        self.button_auto_processing.SetBitmap(self.autorun_bmp)
        if self.current_step > 0:
            utils.log_info("Reset processing steps.")
        self.current_step = 0

        # Clear previous run's data so that loadInput is forced to reload the input files.
        self.originalData = None
        self.originalWref = None
        self.dataSteps = []
        self.wrefSteps = []
        
        # (Optionally, you might want to also clear the filepaths if you wish to force re-drop of data)
        # self.MRSfiles.filepaths = []
        # self.Waterfiles.filepaths = []
        
        self.plot_box.Clear()
        self.plot_box.Append("")  # Start with an empty selection
        self.plot_box.SetSelection(0)
        self.matplotlib_canvas.clear()  
        self.matplotlib_canvas.draw()
        self.Layout()
        if event is not None:
            event.Skip()

    def reset(self, event=None):
        self.processing = False
        self.fast_processing = False
        self.button_terminate_processing.Disable()
        self.button_step_processing.Enable()
        self.button_auto_processing.Enable()
        self.button_nplot.Enable()
        if self.current_step >= len(self.steps):
            self.button_step_processing.SetBitmap(self.run_bmp)
        self.button_auto_processing.SetBitmap(self.autorun_bmp)
        self.current_step = 0
        # Clear previous run's data so that loadInput is forced to reload the input files.
        self.originalData = None
        self.originalWref = None
        self.dataSteps = []
        self.wrefSteps = []
        self.Layout()
        if event is not None: event.Skip()
    
   
    




    def copy_customer_processing_scripts(self):
        self.programpath = os.path.dirname(os.path.dirname(__file__))
        source_folders = self.external_nodes_library #os.path.join(self.programpath, "customer_nodes")
        backup_folder = os.path.join(self.programpath, "customer_nodes/backup")
        destination_folder = os.path.join(self.programpath, "nodes")
        try:
            # Ensure the destination folder exists; create it if it doesn't
            os.makedirs(destination_folder, exist_ok=True)


            # Loop through each source folder
            #for source_folder in source_folders:
            # Find all Python (.py) files in the current source folder
            python_files = glob.glob(os.path.join(source_folders, '*.py'))
               
            # Copy each file to the destination folder
            for file_path in python_files:
                file_name = os.path.basename(file_path)
                destination_path = os.path.join(destination_folder, file_name)


                # # Check if a file with the same name already exists
                # if os.path.exists(destination_path):
                #     base_name, extension = os.path.splitext(file_name)
                #     counter = 1


                #     # Find a unique filename by appending a counter
                #     while os.path.exists(destination_path):
                #         new_file_name = f"{base_name}_{counter}{extension}"
                #         destination_path = os.path.join(destination_folder, new_file_name)
                #         counter += 1


                # Check if a file with the same name already exists
                if os.path.exists(destination_path):
                    # Send a reminder
                    print(f"Reminder: The file '{file_name}' already exists in '{destination_folder}'.")
                   
                    # Prepare to back up the old file
                    os.makedirs(backup_folder, exist_ok=True)
                    backup_path = os.path.join(backup_folder, file_name)


                    # Create a unique backup filename if necessary
                    if os.path.exists(backup_path):
                        base_name, extension = os.path.splitext(file_name)
                        counter = 1
                       
                        # Find a unique backup filename by appending a counter
                        while os.path.exists(backup_path):
                            backup_path = os.path.join(backup_folder, f"{base_name}_{counter}{extension}")
                            counter += 1
                   
                    # Move the existing file to the backup folder
                    shutil.move(destination_path, backup_path)
                    print(f"Backup of the existing file has been created: '{backup_path}'")


                # Copy the new file to the destination folder
                shutil.copy(file_path, destination_path)
                print(f"'{file_path}' has been copied to '{destination_path}'.")


                # # Copy the file to the unique destination path
                # shutil.copy(file_path, destination_path)
                # print(f"Copied '{file_path}' to '{destination_path}'")


            print("All Customer Processing scripts have been copied successfully.")


        except FileNotFoundError:
            print(f"One of the source folders not found.")
        except PermissionError:
            print("Permission denied. Please check your folder permissions.")
        except Exception as e:
            print(f"An error occurred: {e}")


    def retrieve_steps(self):
        self.programpath = os.path.dirname(os.path.dirname(__file__))
        processing_files = glob.glob(os.path.join(self.programpath, "nodes", "*.py"))
        self.processing_steps = {}
        for file in processing_files:
            module_name = os.path.basename(file)[:-3]
            if module_name.startswith("_"): continue
            spec = importlib.util.spec_from_file_location(module_name, file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and obj.__module__ == module_name:
                    obj = getattr(module, name)
                    self.processing_steps[name] = obj

    def update_statusbar(self):
        self.SetStatusText("Current pipeline: " + " → ".join(step.__class__.__name__ for step in self.steps))

    def on_button_step_processing(self, event):
        if self.current_step > len(self.steps):
            self.on_reset()
        self.button_step_processing.Disable()
        self.button_auto_processing.Disable()
        if self.current_step > 0:
            self.button_terminate_processing.Disable()
        thread_processing = threading.Thread(target=processPipeline, args=[self])
        thread_processing.start()
        event.Skip()
        
    def on_autorun_processing(self, event):
        if self.batch_mode:
            # If in batch mode, disable individual step processing
            self.button_step_processing.Disable()
            # Start batch processing in a new thread
            thread_batch = threading.Thread(target=self.run_batch_processing)
            thread_batch.start()
        else:
            if self.current_step > len(self.steps):
                self.on_reset()
            self.fast_processing = not self.fast_processing
            if not self.fast_processing:
                self.button_auto_processing.SetBitmap(self.autorun_bmp)
            else:
                self.button_auto_processing.SetBitmap(self.pause_bmp)
                self.button_step_processing.Disable()
                if self.current_step > 0:
                    self.button_terminate_processing.Disable()

                thread_processing = threading.Thread(target=autorun_pipeline_exe, args=[self])
                thread_processing.start()
            event.Skip()

    def load_brain_image(self):
        """Load a 3D NIfTI image and return the data."""
        # Check if self.img_file_user has a valid path
        if self.brain_image["selected_img_path"] is not None:
            # Use the stored path from self.img_file_user
            img = nib.load(self.brain_image["selected_img_path"])  # Load the image from the file path stored in self.img_file_user
            return img.get_fdata()  # Get the data from the NIfTI file
        else:
            utils.log_info(f"Image file is not set.")

    def on_open_output_folder(self, event):
        if os.path.exists(self.outputpath):
            os.startfile(self.outputpath)
        event.Skip()

    def on_open_pipeline(self, event):
        self.pipeline_frame.Show()
        event.Skip()

    def on_open_metabolite_map_plot(self,event):
        self.metabolite_map_frame.Show()
        event.Skip()
    
    def update_map(self):

        fig = self.matplotlib_canvas.figure
        fig.clf()  # Clear figure
        self.matplotlib_canvas.draw()  # Refresh the canvas
        utils.log_info("Start update main canvas")

        # if (self.brain_image["selected_img"] is None or self.brain_image["selected_img"].size == 0) and \
        if (self.brain_image["selected_img_path"] is None or self.brain_image["selected_img"] is None) and \
        (self.data_to_plot["coord"] is None):
            utils.log_info("Nothing to plot")
            return  # Nothing to plot

        ax = fig.add_subplot(111)

        # Handle background image
        if self.brain_image["selected_img_path"]: 
            if self.brain_image["selected_img"] is not None:
                if self.brain_image["selected_img"].size > 0:
                    views = {
                        0: self.brain_image["selected_img"][self.brain_image['slice_index'], :, :],
                        1: self.brain_image["selected_img"][:, self.brain_image['slice_index'], :],
                        2: self.brain_image["selected_img"][:, :, self.brain_image['slice_index']]
                    }
                    background_slice = views.get(self.brain_image["selected_img_view"])

                if background_slice is None:
                    utils.log_error("Selected image view is incorrect!")
                    return

                background_slice = rotate(
                    background_slice, self.brain_image["selected_img_rotation"], reshape=False, mode='nearest'
                )
                ax.imshow(background_slice, cmap='gray', interpolation='nearest')

        # Handle metabolite concentration map
        if self.data_to_plot["conc_map_to_plot"] is not None and self.data_to_plot["conc_map_to_plot"].size > 0:
            utils.log_info(f"Plot slice {self.data_to_plot['slice']} of {self.data_to_plot['metab_to_plot']}")
            conc_map = self.data_to_plot["conc_map_to_plot"]
            vmin, vmax = np.nanmin(np.abs(conc_map)), np.nanmax(np.abs(conc_map))
            concentration_masked = conc_map

            # If background exists, interpolate concentration map to match its size
            if self.brain_image["selected_img"] is not None and self.brain_image["selected_img"].size > 0:
                background_height, background_width = background_slice.shape
                concentration_masked = zoom(conc_map, (background_height / conc_map.shape[0], background_width / conc_map.shape[1]), order=1)
                mask = create_brain_mask(background_slice)  # Assuming mask function exists
                concentration_masked = np.where(mask == 1, concentration_masked, np.nan)

            cax = ax.imshow(concentration_masked, cmap='coolwarm', interpolation='nearest', alpha=1, vmin=self.param["vmin"], vmax=self.param["vmax"])
            fig.colorbar(cax, ax=ax, orientation='vertical', label='Concentration')
            ax.set_title(f"Slice {self.data_to_plot['slice']} (min={vmin:.2g}, max={vmax:.2g})")
            ax.axis('off')

        self.matplotlib_canvas.draw_idle()

    def on_open_external_nodes(self, event):
            dirDialog = wx.DirDialog(self.Parent, "Select a folder for the customer nodes library", style=wx.DD_DIR_MUST_EXIST)
            if dirDialog.ShowModal() == wx.ID_CANCEL: return
            temp = os.path.join(dirDialog.GetPath())
            if not os.path.exists(temp):
                try: os.mkdir(temp)
                except:
                    utils.log_error(f"Could not create folder {temp}")
                    return
            self.external_nodes_library = temp
            self.copy_customer_processing_scripts()
            self.retrieve_steps()
            self.retrieve_pipeline()
            self.update_statusbar()


    def on_change_output(self, event):
        dirDialog = wx.DirDialog(self.Parent, "Choose a new output folder", style=wx.DD_DIR_MUST_EXIST)
        if dirDialog.ShowModal() == wx.ID_CANCEL: return
        temp = os.path.join(dirDialog.GetPath(), "output")
        if not os.path.exists(temp):
            try: os.mkdir(temp)
            except:
                utils.log_error(f"Could not create folder {temp}")
                return
        self.outputpath_base = temp

    def on_open_fitting(self, event):
        self.fitting_frame.Show()
        event.Skip()
    
    def on_show_debug(self, event):
        if self.show_debug_button.GetValue():
            self.debug_button.Show()
            self.reload_button.Show()
            self.show_debug_button.SetLabel("Hide debug options")
        else:
            self.debug_button.Hide()
            self.reload_button.Hide()
            self.show_debug_button.SetLabel("Show debug options")
        self.Layout()
        if event is not None: event.Skip()

    def on_toggle_debug(self, event):
        utils.set_debug(self.debug_button.GetValue())
        if event is not None: event.Skip()
    
    def on_reload(self, event):
        self.copy_customer_processing_scripts()
        self.retrieve_steps()
        self.retrieve_pipeline()
        self.update_statusbar()
        if event is not None: event.Skip()

    def on_plot_box_selection(self, event):
        selected_item = self.plot_box.GetValue()
        if selected_item == "":
            self.matplotlib_canvas.clear()
        elif selected_item == "lcmodel":
            if os.path.exists(self.last_coord):
                self.matplotlib_canvas.clear()
                f = ReadlcmCoord(self.last_coord)
                plot_coord(f, self.matplotlib_canvas.figure, title=self.last_coord)
                self.matplotlib_canvas.draw()
                self.file_text.SetValue(f"File: {self.last_coord}\n{get_coord_info(f)}")
            else:
                utils.log_warning("LCModel output not found")
        else:
            index = self.plot_box.GetSelection()
            for step in self.steps:
                if step.__class__.__name__ in selected_item:
                    dataDict = {
                        "input": self.dataSteps[index-1],
                        "wref": self.wrefSteps[index-1],
                        "output": self.dataSteps[index],
                        "wref_output": self.wrefSteps[index]
                    }
                    self.matplotlib_canvas.clear()
                    step.plot(self.matplotlib_canvas.figure, dataDict)
                    self.matplotlib_canvas.draw()
                    event.Skip()
                    return
            utils.log_warning("Step not found")

    def retrieve_pipeline(self):
        current_node = self.pipeline_frame.nodegraph.GetInputNode()
        self.pipeline = []
        self.steps = []
        while current_node is not None:
            for socket in current_node.GetSockets():
                if socket.direction == 1:
                    if len(socket.GetWires()) == 0:
                        current_node = None
                        continue
                    if len(socket.GetWires()) > 1:
                        utils.log_error("Only serial pipelines are allowed for now")
                        self.pipeline = []
                        self.steps = []
                        return
                    current_node = socket.GetWires()[0].dstsocket.node
                    self.pipeline.append(current_node.GetLabel())
                    self.steps.append(current_node)

    def on_create_batch(self, event):
        # Prompt for study name and number of participants
        dlg = wx.TextEntryDialog(self, "Enter Study Name:", "Create Batch Folder System")
        if dlg.ShowModal() == wx.ID_OK:
            study_name = dlg.GetValue().strip()
        else:
            dlg.Destroy()
            return
        dlg.Destroy()

        num_dlg = wx.NumberEntryDialog(self, "Enter Number of Participants", "Number of Participants:", "Create Batch Folder System", 1, 1, 100)
        if num_dlg.ShowModal() == wx.ID_OK:
            num_participants = num_dlg.GetValue()
        else:
            num_dlg.Destroy()
            return
        num_dlg.Destroy()

        # Prompt for a parent folder where the batch system will be created
        dirDialog = wx.DirDialog(self, "Choose a folder to create the Batch System", style=wx.DD_DIR_MUST_EXIST)
        if dirDialog.ShowModal() == wx.ID_CANCEL:
            return
        parent_folder = dirDialog.GetPath()
        dirDialog.Destroy()

        # Create the study folder
        study_folder = os.path.join(parent_folder, study_name)
        try:
            os.makedirs(study_folder, exist_ok=True)
            # Create subfolders for each participant and the required subfolders
            self.batch_participants = []  # Clear any previous list
            for i in range(1, num_participants + 1):
                participant_folder = os.path.join(study_folder, f"Participant{i}")
                os.makedirs(participant_folder, exist_ok=True)
                for sub in ["water_reference", "tissue_segmentation_files", "metabolite_files"]:
                    os.makedirs(os.path.join(participant_folder, sub), exist_ok=True)
                self.batch_participants.append(participant_folder)

            custom_basis = os.path.join(study_folder, "custom.BASIS")
            custom_control = os.path.join(study_folder, "custom.CONTROL")
            open(custom_basis, "w").close()
            open(custom_control, "w").close()

            wx.MessageBox(f"Batch folder system created under:\n{study_folder}", "Success", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.MessageBox(f"Error creating batch folders:\n{e}", "Error", wx.OK | wx.ICON_ERROR)
    
    def on_load_batch(self, event):
        dirDialog = wx.DirDialog(self, "Select the Batch System Folder (Study Folder)", style=wx.DD_DIR_MUST_EXIST)
        if dirDialog.ShowModal() == wx.ID_CANCEL:
            return
        self.batch_folder = dirDialog.GetPath()
        dirDialog.Destroy()

        try:
            # Only load subfolders that begin with "Participant" (case-insensitive).
            self.batch_participants = [
                os.path.join(self.batch_folder, d)
                for d in os.listdir(self.batch_folder)
                if os.path.isdir(os.path.join(self.batch_folder, d))
                and d.lower().startswith("participant")
            ]

            count = len(self.batch_participants)
            wx.MessageBox(f"Loaded {count} participant folder{'s' if count != 1 else ''}.",
                        "Batch Loaded", wx.OK | wx.ICON_INFORMATION)

        except Exception as e:
            wx.MessageBox(f"Error loading batch folder:\n{e}", "Error", wx.OK | wx.ICON_ERROR)

    def on_toggle_batch(self, event):
        self.batch_mode = self.run_batch_toggle.GetValue()
        if self.batch_mode:
            self.button_step_processing.Disable()
        else:
            self.button_step_processing.Enable()
        event.Skip()

    def run_batch_processing(self):
        if not self.batch_participants:
            wx.MessageBox("No batch system loaded or created. Please load or create one.", "Batch Mode", wx.OK | wx.ICON_WARNING)
            return
        # For each participant folder, update the file panels and run the pipeline
        try:
            self.MRSfiles.clear()
        except:
            pass
        try:
            self.Waterfiles.clear()
        except:
            pass

        import datetime

        prefix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_output"
        self.batch_study_folder = os.path.join(self.batch_folder, prefix)
        os.mkdir(self.batch_study_folder)


        basis_candidates = []
        control_candidates = []

        # We do a simple iteration over the batch folder
        for fname in os.listdir(self.batch_folder):
            fullpath = os.path.join(self.batch_folder, fname)
            # Must be an actual file
            if not os.path.isfile(fullpath):
                continue
            # Check extension
            fname_lower = fname.lower()
            if fname_lower.endswith(".basis"):
                basis_candidates.append(fullpath)
            elif fname_lower.endswith(".control"):
                control_candidates.append(fullpath)

        # If we found any .BASIS file with size > 0, pick the first
        self.basis_file_user = None
        if basis_candidates:
            # Sort them or just pick the first
            basis_candidates.sort()
            first_basis = basis_candidates[0]
            if os.path.getsize(first_basis) > 0:
                self.basis_file_user = first_basis
                utils.log_info(f"Using custom BASIS file for all participants: {first_basis}")

        # If we found any .CONTROL file with size > 0, pick the first
        self.control_file_user = None
        if control_candidates:
            control_candidates.sort()
            first_control = control_candidates[0]
            if os.path.getsize(first_control) > 0:
                self.control_file_user = first_control
                utils.log_info(f"Using custom CONTROL file for all participants: {first_control}")

        for part_folder in self.batch_participants:
            try:
                self.participant_name = os.path.basename(part_folder)

                wx.CallAfter(self.reset)

                import time

                # For example, assume that metabolite files are in the "metabolite_files" subfolder
                met_folder = os.path.join(part_folder, "metabolite_files")
                water_folder = os.path.join(part_folder, "water_reference")
                # Update file lists:
                if os.path.exists(met_folder):
                    met_files = [os.path.join(met_folder, f) for f in os.listdir(met_folder)
                                if f.lower().endswith(tuple(utils.supported_files))]
                    wx.CallAfter(self.MRSfiles.on_drop_files, met_files)
                    time.sleep(0.5)
                else:
                    self.MRSfiles.on_drop_files([])
                if os.path.exists(water_folder):
                    water_files = [os.path.join(water_folder, f) for f in os.listdir(water_folder)
                                if f.lower().endswith(tuple(utils.supported_files))]
                    wx.CallAfter(self.Waterfiles.on_drop_files, water_files)
                    time.sleep(0.5)
                else:
                    self.Waterfiles.on_drop_files([])

                seg_folder = os.path.join(part_folder, "tissue_segmentation_files")
                self.wm_file_user = None
                self.gm_file_user = None
                self.csf_file_user = None
                if os.path.exists(seg_folder):
                    seg_files = [
                        os.path.join(seg_folder, f)
                        for f in os.listdir(seg_folder)
                        # You can refine this if you want only .nii or .nii.gz
                    ]
                    # For example, pick a file with 'wm' in its name
                    for f in seg_files:
                        fname_lower = os.path.basename(f).lower()
                        if "wm" in fname_lower:
                            self.wm_file_user = f
                        elif "gm" in fname_lower:
                            self.gm_file_user = f
                        elif "csf" in fname_lower:
                            self.csf_file_user = f

                if len(self.MRSfiles.filepaths) == 0 and len(self.Waterfiles.filepaths) == 0:
                    utils.log_warning("No input files found for participant " + self.participant_name + "; skipping.")
                    continue

                # Reset processing state for the new participant
                
                # You can choose auto-run mode for each participant
                self.fast_processing = True
                autorun_pipeline_exe(self)
                
                self.MRSfiles.clear()
                self.Waterfiles.clear()
                # Optionally wait for the current run to complete (or add a delay)
                # You might want to update a progress indicator, etc.
            except Exception as e:
                utils.log_error(f"Processing failed for {part_folder}: {e}")
        wx.MessageBox("Batch processing complete.", "Batch Mode", wx.OK | wx.ICON_INFORMATION)
    
    def save_lastfiles(self):
        tosave = [self.MRSfiles.filepaths, self.Waterfiles.filepaths, self.basis_file_user, self.control_file_user, self.wm_file_user, self.gm_file_user, self.csf_file_user]
        filepath = os.path.join(os.getcwd(), "lastfiles.pickle")
        with open(filepath, 'wb') as f:
            pickle.dump(tosave, f)
        pipeline_filepath = os.path.join(os.getcwd(), "lastpipeline.pipe")
        self.pipeline_frame.on_save_pipeline(event=None, filepath=pipeline_filepath)

    def load_lastfiles(self):
        filepath = os.path.join(os.getcwd(), "lastfiles.pickle")
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                filepaths, filepaths_wref, self.basis_file_user, self.control_file_user, self.wm_file_user, self.gm_file_user, self.csf_file_user = pickle.load(f)
            self.MRSfiles.on_drop_files(filepaths)
            self.Waterfiles.on_drop_files(filepaths_wref)
        

    def on_close(self, event):
        try: self.save_lastfiles()
        except: pass
        self.Destroy()
        
    def on_resize(self, event):
        self.Layout()
        self.Refresh()

class MainApp(wx.App):
    def OnInit(self):
        self.frame = MainFrame(None, wx.ID_ANY, "")
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True

if __name__ == "__main__":
    app = MainApp(0)
    app.MainLoop()