import wx
import wx.richtext
from . import images
from .plot_canvas import MatplotlibCanvas
from .file_panel import FilePanel
from .colours import(BLACK_WX,XISLAND1,XISLAND2)

class ButtonNoBorder(wx.Button):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnHover)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnUnHover)
        self.SetWindowStyleFlag(wx.BORDER_NONE)

    def OnHover(self, event):
        self.SetWindowStyleFlag(wx.BORDER_SUNKEN)
        event.Skip()
        
    def OnUnHover(self, event):
        self.SetWindowStyleFlag(wx.BORDER_NONE)
        event.Skip()

class ToggleButtonNoBorder(wx.ToggleButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnHover)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnUnHover)
        self.SetWindowStyleFlag(wx.BORDER_NONE)

    def OnHover(self, event):
        self.SetWindowStyleFlag(wx.BORDER_SUNKEN)
        event.Skip()
        
    def OnUnHover(self, event):
        self.SetWindowStyleFlag(wx.BORDER_NONE)
        event.Skip()

class BtmButtonNoBorder(wx.BitmapButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnHover)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnUnHover)
        self.SetWindowStyleFlag(wx.NO_BORDER)

    def OnHover(self, event):
        self.SetWindowStyleFlag(wx.BORDER_SUNKEN)
        event.Skip()
        
    def OnUnHover(self, event):
        self.SetWindowStyleFlag(wx.NO_BORDER)
        event.Skip()

class LayoutFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((1200, 800))
        self.SetTitle("MRSpecLAB")
        #self.SetIcon(images.icon_img_32.GetIcon())
        font1 = wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.NORMAL,wx.FONTWEIGHT_NORMAL, False)

        main_splitter = wx.SplitterWindow(self, wx.ID_ANY, style=wx.SP_3D | wx.SP_LIVE_UPDATE)
        right_splitter = wx.SplitterWindow(main_splitter, wx.ID_ANY, style=wx.SP_3D | wx.SP_LIVE_UPDATE)
        text_splitter = wx.SplitterWindow(right_splitter, wx.ID_ANY, style=wx.SP_3D | wx.SP_LIVE_UPDATE)

        main_splitter.SetMinimumPaneSize(100)
        right_splitter.SetMinimumPaneSize(100)

        self.left_panel = wx.Panel(main_splitter, wx.ID_ANY)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.left_panel.SetSizer(left_sizer)
        self.right_panel = wx.Panel(right_splitter, wx.ID_ANY)
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        self.right_panel.SetSizer(right_sizer)

        self.MRSfiles = FilePanel(self.left_panel)
        self.MRSfiles.SetFont(font1)
        self.MRSfiles.label.SetLabel("Metabolite files")
        self.MRSfiles.Layout()

        self.Waterfiles = FilePanel(self.left_panel)
        self.Waterfiles.SetFont(font1)
        self.Waterfiles.label.SetLabel("Water file (optional)")
        self.Waterfiles.list.SetMaxSize((-1, 50))
        self.Waterfiles.Layout()

        cibm_bmp = wx.StaticBitmap(self.left_panel, wx.ID_ANY, images.cibm_logo_img.GetBitmap())
        left_sizer.Add(self.MRSfiles, 3, wx.ALL | wx.EXPAND, 5)
        left_sizer.AddSpacer(20)
        left_sizer.Add(self.Waterfiles, 0, wx.ALL | wx.EXPAND, 5)
        left_sizer.AddStretchSpacer(2)
        left_sizer.Add(cibm_bmp, 0, wx.ALL | wx.ALIGN_LEFT, 0)
        self.left_panel.SetMinSize((cibm_bmp.GetSize().x, -1))
        
        ### WINDOW BUTTONS ###
        folder_bmp = images.folder_img.GetBitmap().ConvertToImage().Rescale(50, 50).ConvertToBitmap()
        self.folder_button = BtmButtonNoBorder(self.right_panel, wx.ID_ANY, folder_bmp)
        self.folder_button.SetBackgroundColour(wx.Colour(XISLAND1))
        self.folder_button.SetMinSize((50, 50))
        self.folder_button.SetToolTip("Open output folder")

        pipeline_bmp = images.pipeline_img.GetBitmap().ConvertToImage().Rescale(50, 50).ConvertToBitmap()
        self.pipeline_button = BtmButtonNoBorder(self.right_panel, wx.ID_ANY, pipeline_bmp)
        self.pipeline_button.SetBackgroundColour(wx.Colour(XISLAND1))
        self.pipeline_button.SetMinSize((50, 50))
        self.pipeline_button.SetToolTip("Open pipeline editor")
        
        bmp_sizer = wx.BoxSizer(wx.VERTICAL)
        bmp_sizer.Add(self.folder_button, 0, wx.ALL | wx.EXPAND, 2)
        bmp_sizer.Add(self.pipeline_button, 0, wx.ALL | wx.EXPAND, 2)

        ### PLOT BUTTONS ###
        self.save_plots_button = wx.CheckBox(self.right_panel, wx.ID_ANY, "Save plots", style=wx.BORDER_NONE | wx.BU_LEFT)
        self.save_plots_button.SetValue(True)
        self.save_plots_button.SetMinSize((-1, 25))
        self.save_plots_button.SetToolTip("Toggle saving plots in the output folder")

        self.save_raw_button = wx.CheckBox(self.right_panel, wx.ID_ANY, "Save intermediate data files", style=wx.BORDER_NONE | wx.BU_LEFT)
        self.save_raw_button.SetValue(False)
        self.save_raw_button.SetMinSize((-1, 25))
        self.save_raw_button.SetToolTip("Toggle saving raw data in the output folder")
        
        plot_label = wx.StaticText(self.right_panel, wx.ID_ANY, "Show plot of node:", style=wx.ALIGN_CENTRE_VERTICAL)
        plot_label.SetForegroundColour(wx.Colour(BLACK_WX))
        plot_label.SetMinSize((-1, 25))

        self.plot_box = wx.ComboBox(self.right_panel, value="", choices=[""], style=wx.CB_READONLY)
        self.plot_box.SetMinSize((150, 25))

        plot_sizer = wx.BoxSizer(wx.VERTICAL)
        plot_sizer.Add(self.save_plots_button, 0, wx.ALL | wx.ALIGN_CENTER, 0)
        plot_sizer.Add(self.save_raw_button, 0, wx.ALL | wx.ALIGN_CENTER, 0)
        plot_sizer.AddSpacer(5)
        plot_sizer.Add(plot_label, 0, wx.ALL | wx.ALIGN_CENTER, 0)
        plot_sizer.Add(self.plot_box, 0, wx.ALL | wx.ALIGN_CENTER, 0)

        ### DEBUG BUTTONS ###
        self.extenal_nodes = ButtonNoBorder(self.right_panel, wx.ID_ANY, "Customer nodes library", style=wx.BORDER_NONE | wx.BU_LEFT)
        self.extenal_nodes.SetBackgroundColour(wx.Colour(XISLAND1))
        self.extenal_nodes.SetMinSize((-1, 25))
        self.extenal_nodes.SetToolTip("Select a folder for the customer nodes library")

        self.change_output_button = ButtonNoBorder(self.right_panel, wx.ID_ANY, "Change output folder", style=wx.BORDER_NONE | wx.BU_LEFT)
        self.change_output_button.SetBackgroundColour(wx.Colour(XISLAND1))
        self.change_output_button.SetMinSize((-1, 25))
        self.change_output_button.SetToolTip("Select a folder for the output files")

        self.fitting_button = ButtonNoBorder(self.right_panel, wx.ID_ANY, "Show fitting options", style=wx.BORDER_NONE | wx.BU_LEFT)
        self.fitting_button.SetBackgroundColour(wx.Colour(XISLAND1))
        self.fitting_button.SetMinSize((-1, 25))
        self.fitting_button.SetToolTip("Show fitting options for LCModel")

        self.show_debug_button = ToggleButtonNoBorder(self.right_panel, wx.ID_ANY, "Show debug options", style=wx.BORDER_NONE | wx.BU_LEFT)
        self.show_debug_button.SetBackgroundColour(wx.Colour(XISLAND1))
        self.show_debug_button.SetValue(False)
        self.show_debug_button.SetMinSize((-1, 25))
        self.show_debug_button.SetToolTip("Show debug options")

        self.debug_button = wx.CheckBox(self.right_panel, wx.ID_ANY, "Log debug messages", style=wx.BORDER_NONE | wx.BU_LEFT)
        self.debug_button.SetBackgroundColour(wx.Colour(XISLAND2))
        self.debug_button.SetMinSize((-1, 25))
        self.debug_button.SetToolTip("Write debug information in the log window")

        self.reload_button = ButtonNoBorder(self.right_panel, wx.ID_ANY, "Rescan node folder", style=wx.BORDER_NONE | wx.BU_LEFT)
        self.reload_button.SetBackgroundColour(wx.Colour(XISLAND2))
        self.reload_button.SetMinSize((-1, 25))
        self.reload_button.SetToolTip("Reload all nodes from the node folder; only useful when running the Python source code")

        debug_sizer = wx.BoxSizer(wx.VERTICAL)
        debug_sizer.Add(self.extenal_nodes, 0, wx.ALL | wx.EXPAND, 0)
        debug_sizer.Add(self.change_output_button, 0, wx.ALL | wx.EXPAND, 0)
        debug_sizer.Add(self.fitting_button, 0, wx.ALL | wx.EXPAND, 0)
        debug_sizer.Add(self.show_debug_button, 0, wx.ALL | wx.EXPAND, 0)
        debug_sizer.Add(self.debug_button, 0, wx.ALL | wx.EXPAND, 0)
        debug_sizer.Add(self.reload_button, 0, wx.ALL | wx.EXPAND, 0)

        # --- BATCH PROCESSING BUTTONS (NEW) ---
        self.create_batch_button = ButtonNoBorder(self.right_panel, wx.ID_ANY, "Create batch folder system", style=wx.BORDER_NONE)
        self.create_batch_button.SetBackgroundColour(wx.Colour(XISLAND1))
        self.create_batch_button.SetMinSize((-1, 25))
        self.create_batch_button.SetToolTip("Create folder structure for a new study")

        self.load_batch_button = ButtonNoBorder(self.right_panel, wx.ID_ANY, "Load batch system folder", style=wx.BORDER_NONE)
        self.load_batch_button.SetBackgroundColour(wx.Colour(XISLAND1))
        self.load_batch_button.SetMinSize((-1, 25))
        self.load_batch_button.SetToolTip("Load an existing batch system folder")

        self.run_batch_toggle = wx.CheckBox(self.right_panel, wx.ID_ANY, "Run in batch mode", style=wx.BORDER_NONE | wx.BU_LEFT)
        self.run_batch_toggle.SetBackgroundColour(wx.Colour(XISLAND1))
        self.run_batch_toggle.SetMinSize((-1, 25))
        self.run_batch_toggle.SetToolTip("Toggle batch mode processing")

        # Create a sizer for these new buttons.
        batch_sizer = wx.BoxSizer(wx.VERTICAL)
        batch_sizer.Add(self.create_batch_button, 0, wx.ALL | wx.EXPAND, 2)
        batch_sizer.Add(self.load_batch_button, 0, wx.ALL | wx.EXPAND, 2)
        batch_sizer.Add(self.run_batch_toggle, 0, wx.ALL | wx.EXPAND, 2)

        

        ### PLAYER BUTTONS ###
        self.player_panel = wx.Panel(self.right_panel, wx.ID_ANY)
        self.player_panel.SetBackgroundColour(wx.Colour(XISLAND2)) 
        player_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.player_panel.SetSizer(player_sizer)
        
        self.run_bmp = images.run_img.GetBitmap()
        self.button_step_processing = BtmButtonNoBorder(self.player_panel, wx.ID_ANY, self.run_bmp)
        self.button_step_processing.SetBackgroundColour(wx.Colour(XISLAND2))
        self.button_step_processing.SetMinSize((-1, 100))
        self.button_step_processing.SetToolTip("Run stepwise")
        
        self.autorun_bmp = images.autorun_img.GetBitmap()
        self.pause_bmp = images.pause_img.GetBitmap()
        self.button_auto_processing = BtmButtonNoBorder(self.player_panel, wx.ID_ANY, self.autorun_bmp)
        self.button_auto_processing.SetBackgroundColour(wx.Colour(XISLAND2))
        self.button_auto_processing.SetMinSize((-1, 100))
        self.button_auto_processing.SetToolTip("Run") 

        self.nplot_bmp = images.nplot_img.GetBitmap()
        self.button_nplot = BtmButtonNoBorder(self.player_panel, wx.ID_ANY, self.nplot_bmp)
        self.button_nplot.SetBackgroundColour(wx.Colour(XISLAND2))
        self.button_nplot.SetMinSize((-1, 100))
        self.button_nplot.SetToolTip("Show plots")
        self.button_nplot.Disable()

        self.terminate_bmp = images.terminate_img.GetBitmap()
        self.button_terminate_processing = BtmButtonNoBorder(self.player_panel, wx.ID_ANY, self.terminate_bmp)
        self.button_terminate_processing.SetBackgroundColour(wx.Colour(XISLAND2))
        self.button_terminate_processing.SetMinSize((-1, 100))
        self.button_terminate_processing.SetToolTip("Reset processing of the current pipeline")
        self.button_terminate_processing.Disable()

        player_sizer.Add(self.button_step_processing, 0, wx.ALL | wx.EXPAND, 5)
        player_sizer.Add(self.button_auto_processing, 0, wx.ALL | wx.EXPAND, 5)
        player_sizer.Add(self.button_terminate_processing, 0, wx.ALL | wx.EXPAND, 5)
        player_sizer.Add(self.button_nplot, 0, wx.ALL | wx.EXPAND, 5)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(bmp_sizer, 0, wx.ALL | wx.EXPAND, 0)
        button_sizer.Add(wx.StaticLine(self.right_panel, wx.ID_ANY, style=wx.LI_VERTICAL), 0, wx.ALL | wx.EXPAND, 5)
        button_sizer.Add(plot_sizer, 0, wx.ALL | wx.EXPAND, 0)
        button_sizer.Add(wx.StaticLine(self.right_panel, wx.ID_ANY, style=wx.LI_VERTICAL), 0, wx.ALL | wx.EXPAND, 5)
        button_sizer.Add(debug_sizer, 0, wx.ALL | wx.EXPAND, 0)
        button_sizer.Add(batch_sizer, 0, wx.ALL | wx.EXPAND, 0)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(self.player_panel, 0, wx.ALL | wx.EXPAND, 0)
        right_sizer.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 0)

        self.matplotlib_canvas = MatplotlibCanvas(self.right_panel, wx.ID_ANY)
        self.info_text = wx.richtext.RichTextCtrl(text_splitter, wx.ID_ANY, "", style=wx.TE_READONLY | wx.TE_MULTILINE)
        self.file_text = wx.TextCtrl(text_splitter, wx.ID_ANY, "", style=wx.TE_READONLY | wx.TE_MULTILINE)
        font_fixed_width = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.file_text.SetFont(font_fixed_width)
        self.info_text.Bind(wx.EVT_SET_FOCUS, lambda event: self.SetFocus()) # remove blinking cursor
        self.file_text.Bind(wx.EVT_SET_FOCUS, lambda event: self.SetFocus())

        right_sizer.Add(self.matplotlib_canvas, 1, wx.ALL | wx.EXPAND, 0)
        right_sizer.Add(self.matplotlib_canvas.toolbar, 0, wx.EXPAND, 0)
        right_splitter.SplitHorizontally(self.right_panel, text_splitter, -150)
        right_splitter.SetSashGravity(1.)
        text_splitter.SplitVertically(self.info_text, self.file_text, 0)
        text_splitter.SetSashGravity(.5)
        main_splitter.SplitVertically(self.left_panel, right_splitter, 300)
        self.SetBackgroundColour(wx.Colour(XISLAND1))

        self.Layout()
        self.Refresh()