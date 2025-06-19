import os

if os.name == 'posix': # avoid X11 errors on Linux
    import ctypes
    ctypes.cdll.LoadLibrary('libX11.so').XInitThreads()

from interface.main_frame import MainApp

if __name__ == "__main__":
    app = MainApp(0)
    app.MainLoop()