import wx
import os
from . import utils
from .plot_frame import PlotFrame
from .plot_helpers import read_file
from .colours import XISLAND4, BLACK_WX

class FileDrop(wx.FileDropTarget):
    def __init__(self, parent):
        wx.FileDropTarget.__init__(self)
        self.Parent = parent

    def OnDropFiles(self, x, y, filenames):
        self.Parent.on_drop_files(filenames)
        return True

class FilePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.drop_target = FileDrop(self)
        self.SetDropTarget(self.drop_target)
        self.filepaths = []
        self.root = ""
        self.is_viewer = False

        self.label = wx.StaticText(self, wx.ID_ANY, "Import MRS files here", style=wx.ALIGN_CENTRE_VERTICAL)
        self.label.SetForegroundColour(wx.Colour(BLACK_WX))

        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.plus_button = wx.Button(self, wx.ID_ANY, "+")
        self.plus_button.SetMaxSize(wx.Size(40, -1))
        self.minus_button = wx.Button(self, wx.ID_ANY, "-")
        self.minus_button.SetMaxSize(wx.Size(40, -1))
        self.clear_button = wx.Button(self, wx.ID_ANY, "Clear")

        self.button_sizer.Add(self.plus_button, 0, wx.ALL | wx.EXPAND, 5)
        self.button_sizer.Add(self.minus_button, 0, wx.ALL | wx.EXPAND, 5)
        self.button_sizer.Add(self.clear_button, 0, wx.ALL | wx.EXPAND, 5)
        
        self.list = wx.ListBox(self, wx.ID_ANY, choices=[], style=wx.LB_SINGLE | wx.LB_NEEDED_SB | wx.HSCROLL | wx.LB_OWNERDRAW)
        self.list.SetBackgroundColour(wx.Colour(XISLAND4)) 
        
        self.number_label = wx.StaticText(self, wx.ID_ANY, "0 files", style=wx.ALIGN_TOP|wx.ALIGN_RIGHT)
        self.number_label.SetForegroundColour(wx.Colour(BLACK_WX))

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.label, 0, wx.EXPAND, 0)
        self.sizer.Add(self.button_sizer, 0, wx.EXPAND, 0)
        self.sizer.Add(self.list, 1, wx.EXPAND, 0)
        self.sizer.Add(self.number_label, 0, wx.EXPAND, 0)
        self.SetSizer(self.sizer)
        self.Layout()
        
        self.Bind(wx.EVT_BUTTON, self.on_clear, self.clear_button)
        self.Bind(wx.EVT_BUTTON, self.on_plus, self.plus_button)
        self.Bind(wx.EVT_BUTTON, self.on_minus, self.minus_button)
        self.Bind(wx.EVT_LISTBOX, self.on_click, self.list)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_dclick, self.list)

    def on_clear(self, event):
        self.filepaths = []
        self.list.Set([])
        self.clear_button.Disable()
        self.minus_button.Disable()
        self.number_label.SetLabel("0 files")
        self.Layout()
        utils.log_info("Filepaths cleared")
        event.Skip()

    def clear(self):
        self.filepaths = []
        self.list.Set([])
        self.clear_button.Disable()
        self.minus_button.Disable()
        self.number_label.SetLabel("0 files")
        self.Layout()
        
    def on_plus(self, event):
        wildcard = "MRS files ("
        for ext in utils.supported_files:
            wildcard += f"*.{ext}, "
        wildcard = wildcard[:-2] + ")|"
        for ext in utils.supported_files:
            wildcard += f"*.{ext};"
        wildcard = wildcard[:-1]
        defaultDir = utils.last_directory
        if defaultDir is None or not os.path.exists(defaultDir):
            defaultDir = os.getcwd()
        fileDialog = wx.FileDialog(self.Parent, "Choose a file", wildcard=wildcard, defaultDir=defaultDir, style=wx.FD_OPEN | wx.FD_MULTIPLE)
        if fileDialog.ShowModal() == wx.ID_CANCEL:
            return
        filepaths = fileDialog.GetPaths()
        utils.last_directory = fileDialog.GetDirectory()
        files = []
        for filepath in filepaths:
            if filepath == "" or not os.path.exists(filepath):
                utils.log_warning(f"File not found:\n\t{filepath}")
            else:
                files.append(filepath)
        ext = filepaths[0].rsplit(os.path.sep, 1)[1].rsplit(".", 1)[1]
        if not all([f.endswith(ext) for f in filepaths]):
            utils.log_error("Inconsistent file types")
            return False
        ex = None
        for e in utils.supported_files:
            if filepath.lower().endswith(e):
                ex = e
                break
        if ex is None:
            utils.log_error(f"Invalid file type: {ex}.")
            return False
        self.on_drop_files(files)
        event.Skip()

    def on_minus(self, event):
        deleted_item = self.list.GetSelection()
        if deleted_item != wx.NOT_FOUND:
            new_paths = self.filepaths
            new_paths.pop(deleted_item)
            self.filepaths = []
            self.list.Set([])
            self.on_drop_files(new_paths)
        event.Skip()

    def on_click(self, event):
        event.Skip()

    def on_dclick(self, event):
        filepath = self.filepaths[self.list.GetSelection()]
        if filepath is None or filepath == "" or not os.path.exists(filepath):
            return utils.log_error("File not found")
        if not any([filepath.lower().endswith(ext) for ext in utils.supported_files]):
            return utils.log_error("Invalid file type")
        child = PlotFrame(filepath, is_viewer=self.is_viewer)
        read_file(filepath, child.canvas, child.text, self.is_viewer)
        event.Skip()
    
    def on_drop_files(self, filenames):
        if len(filenames) == 0:
            if len(self.filepaths) == 0:
                self.on_clear(wx.CommandEvent())
            return False
        self.filepaths.extend(filenames)
        self.list.Set([])
        if len(self.filepaths) > 1:  # find common root folder
            root = ""
            if all([f[0] == self.filepaths[0][0] for f in self.filepaths]):
                root = os.path.commonpath(self.filepaths)
            if root != "":
                self.list.Append([f.replace(root, "") for f in self.filepaths])
            else:
                self.list.Append([f for f in self.filepaths])
        else:
            self.list.Append([f for f in self.filepaths])
        _sorted = sorted(enumerate(self.filepaths), key=lambda x: x[1])
        self.filepaths = [f[1] for f in _sorted]
        order = [f[0] for f in _sorted]
        temp = self.list.GetStrings()
        self.list.Set([temp[i] for i in order])
        self.number_label.SetLabel(str(len(self.filepaths)) + " files")
        self.Layout()
        self.clear_button.Enable()
        self.minus_button.Enable()
        return True