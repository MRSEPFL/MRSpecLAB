# import os
import os, sys
sys.setrecursionlimit(sys.getrecursionlimit() * 5)
import PyInstaller.__main__
import PyInstaller.utils.hooks

PyInstaller.__main__.run([
    'inout/read_ants_image.py',
    '--noconfirm',
    '--onefile',
    '--console',
    '--clean',
    '--exclude-module', 'wxPython'
])

options = [
    'MRSpecLAB.py',
    '--noconfirm',
    '--onefile',
	'--console',
    '--clean',
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
	'--hidden-import', 'nifti_mrs.standard',
    # exclude
    '--exclude-module', 'antspyx'
]

nifti_mrs_data = PyInstaller.utils.hooks.collect_data_files('nifti_mrs')
for src, dest in nifti_mrs_data:
    options += ['--add-data', f'{src}:{dest}']

helper_exe_path = os.path.join('dist', 'read_ants_image' + ('.exe' if os.name == 'nt' else ''))
if os.path.exists(helper_exe_path):
    options += ['--add-data', f'{helper_exe_path}:.']

# if os.name == 'posix' and "24.04" in platform.version():
# 	options += [
# 	    '--add-binary', '/usr/lib/x86_64-linux-gnu/libtiff.so.5:.'
# 	]

PyInstaller.__main__.run(options)