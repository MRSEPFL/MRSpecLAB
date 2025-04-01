import wx
from datetime import datetime
from .colours import INFO_COLOR, WARNING_COLOR, ERROR_COLOR, DEBUG_COLOR

text_dst = None
last_directory = None
supported_files = ["ima", "IMA", "dcm", "dat", "sdat", "rda", "coord", "nii", "nii.gz"]
supported_sequences = {
    "PRESS": ["PRESS", "press"],
    "STEAM": ["STEAM", "steam"],
    "sSPECIAL": ["sSPECIAL", "sspecial", "sS"],
    "MEGA": ["MEGA", "mega"]
}

myEVT_LOG = wx.NewEventType()
EVT_LOG = wx.PyEventBinder(myEVT_LOG, 1)
class LogEvent(wx.PyCommandEvent):
    def __init__(self, evtType, id, text=None, colour=None):
        wx.PyCommandEvent.__init__(self, evtType, id)
        self.text = text
        self.colour = colour

    def GetText(self): return self.text
    def GetColour(self): return self.colour

def init_logging(text, _debug=False):
    global text_dst, debug
    text_dst = text
    debug = _debug
    text_dst.Bind(EVT_LOG, on_log)

def set_debug(_debug):
    global debug
    debug = _debug

def log_text( colour, *args):
        if not text_dst: return
        text = ""
        for arg in args: text += str(arg)
        evt = LogEvent(myEVT_LOG, -1, text=text, colour=colour)
        wx.PostEvent(text_dst, evt)

def on_log(event):
    text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + event.GetText()
    text_dst.BeginTextColour(event.GetColour())
    text_dst.WriteText(text)
    text_dst.EndTextColour()
    text_dst.Newline()
    text_dst.SetScrollPos(wx.VERTICAL, text_dst.GetScrollRange(wx.VERTICAL))
    text_dst.ShowPosition(text_dst.GetLastPosition())
    event.Skip()

def log_info(*args):
    log_text(INFO_COLOR, *args)

def log_error(*args):
    log_text(ERROR_COLOR, *args)

def log_warning(*args):
    log_text(WARNING_COLOR, *args)

def log_debug(*args):
    global debug
    if debug: log_text(DEBUG_COLOR, *args)