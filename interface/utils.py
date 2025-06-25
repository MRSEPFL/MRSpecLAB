import wx, os
import threading
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

larmor_frequencies = {
    "1H": 42.577,
    "31P": 17.235,
    "23Na": 11.262,
    "2H": 6.536,
    "13C": 10.7084,
    "19F": 40.078
}

def iswindows(): return os.name == 'nt'
def islinux(): return os.name == 'posix'

myEVT_LOG = wx.NewEventType()
EVT_LOG = wx.PyEventBinder(myEVT_LOG, 1)
class LogEvent(wx.PyCommandEvent):
    def __init__(self, evtType, id, text=None, colour=None):
        wx.PyCommandEvent.__init__(self, evtType, id)
        self.text = text
        self.colour = colour

    def GetText(self): return self.text
    def GetColour(self): return self.colour

text_dst: wx.TextCtrl
def init_logging(text, _debug=False):
    global text_dst, debug
    text_dst = text
    debug = _debug
    text_dst.Bind(EVT_LOG, on_log)

def set_debug(_debug):
    global debug
    debug = _debug

text_dst_lock = threading.Lock()
def log_text(colour, *args):
    if not text_dst: return
    text = ""
    for arg in args: text += str(arg)
    evt = LogEvent(myEVT_LOG, -1, text=text, colour=colour)
    wx.PostEvent(text_dst, evt)

def on_log(event):
    def do_log():
        text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + event.GetText()
        with text_dst_lock:
            text_dst.BeginTextColour(event.GetColour())
            text_dst.WriteText(text)
            text_dst.EndTextColour()
            text_dst.Newline()
            # text_dst.SetScrollPos(wx.VERTICAL, text_dst.GetScrollRange(wx.VERTICAL))
            text_dst.ShowPosition(text_dst.GetLastPosition())
    # if wx.IsMainThread(): do_log()
    # else: wx.CallAfter(do_log)
    do_log()
    event.Skip()

def log_info(*args):
    log_text(INFO_COLOR, *args)

def log_error(*args):
    log_text(ERROR_COLOR, *args)
    print("ERROR:", *args)

def log_warning(*args):
    log_text(WARNING_COLOR, *args)

def log_debug(*args):
    global debug
    if debug: log_text(DEBUG_COLOR, *args)