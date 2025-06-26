import wx
from .plot_helpers import read_file
from .plot_canvas import MatplotlibCanvas
from interface.colours import XISLAND1
import interface.images as images

class PlotFrame(wx.Frame):
    def __init__(self, filepath, title=None, is_viewer=False):
        super().__init__(None)
        self.filepath = filepath
        if title is None: title = filepath
        self.is_viewer = is_viewer # for the standalone file viewer
        self.SetTitle(title)
        #self.SetIcon(images.icon_img_32.GetIcon())
        self.SetBackgroundColour(wx.Colour(XISLAND1)) 
        self.SetSize((1200, 800))
        self.Show(True)

        self.splitter = wx.SplitterWindow(self, wx.ID_ANY, style=wx.SP_3D | wx.SP_LIVE_UPDATE)
        self.leftPanel = wx.Panel(self.splitter, wx.ID_ANY)
        self.canvas = MatplotlibCanvas(self.leftPanel, wx.ID_ANY)

        self.rightPanel = wx.Panel(self.splitter, wx.ID_ANY)
        self.ccombine_checkbox = wx.CheckBox(self.rightPanel, wx.ID_ANY, "Combine coils")
        self.ccombine_checkbox.SetValue(self.is_viewer)
        self.gaussian_checkbox = wx.CheckBox(self.rightPanel, wx.ID_ANY, "Fit gaussian")
        self.gaussian_checkbox.SetValue(False)
        self.text = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", style=wx.TE_READONLY | wx.TE_MULTILINE)
        self.text.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.NORMAL,wx.FONTWEIGHT_NORMAL, False))
        self.text.Bind(wx.EVT_SET_FOCUS, lambda event: self.SetFocus()) # remove blinking cursor

        self.leftSizer = wx.BoxSizer(wx.VERTICAL)
        self.leftSizer.Add(self.canvas, 1, wx.EXPAND, 0)
        self.leftSizer.Add(self.canvas.toolbar, 0, wx.EXPAND, 0)
        self.leftPanel.SetSizer(self.leftSizer)
        
        self.rightSizer = wx.BoxSizer(wx.VERTICAL)
        self.rightSizer.Add(self.ccombine_checkbox, 0, wx.EXPAND, 0)
        self.rightSizer.Add(self.gaussian_checkbox, 0, wx.EXPAND, 0)
        self.rightSizer.Add(self.text, 1, wx.EXPAND, 0)
        self.rightPanel.SetSizer(self.rightSizer)
        
        self.splitter.SetMinimumPaneSize(200)
        self.splitter.SplitVertically(self.leftPanel, self.rightPanel, -150)
        self.splitter.SetSashGravity(1.)
        self.ccombine_checkbox.Bind(wx.EVT_CHECKBOX, self.on_checkbox)
        self.gaussian_checkbox.Bind(wx.EVT_CHECKBOX, self.on_checkbox)

        self.on_checkbox()
        self.Layout()
    
    def on_checkbox(self, event=None):
        multi_coil = read_file(self.filepath, self.canvas, self.text, self.ccombine_checkbox.GetValue(), self.gaussian_checkbox.GetValue())
        self.ccombine_checkbox.Enable(multi_coil)
        self.gaussian_checkbox.Enable(self.filepath.lower().endswith(".coord"))
        if event is not None: event.Skip()