import os
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)
import PyInstaller.__main__

options = [
    'MRSpecLAB.py',
    '--noconfirm',
    '--onefile',
    # own files
    '--hidden-import', 'processing.processing_node',
    '--add-data', 'inout:inout',
    '--add-data', 'lcmodel:lcmodel',
    '--add-data', 'nodes:nodes',
    # external libraries
    '--hidden-import', 'pydicom.encoders.gdcm',
    '--hidden-import', 'pydicom.encoders.pylibjpeg',
    '--hidden-import', 'pydicom.encoders.native',
    '--collect-submodules', 'ometa._generated',
    '--collect-submodules', 'terml._generated',
    '--hidden-import', 'wx',
    '--hidden-import', 'wx._xml',
    '--hidden-import', 'wx.core',
    '--hidden-import', 'matplotlib.backends.backend_pdf',
    '--hidden-import', 'matplotlib.backends.backend_svg',
    # exclude
    '--exclude-module', 'cv2',
    '--exclude-module', 'babel',
    '--exclude-module', 'PyQt5',
]

if os.name == 'posix':
	options += [
	    '--add-binary', '/usr/lib/x86_64-linux-gnu/libtiff.so.5:.'
	]

PyInstaller.__main__.run(options)