import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
include_files = ['html\\', 'custom.css', 'templates\\']
build_exe_options = {"packages": ["os", 'sys', 'cal_maker', 'bottle', 'idna'], "excludes": ["tkinter"], "include_files": include_files}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(  name = "GTCC Cal",
        version = "0.1",
        description = "GTCC Calendar Tool",
        options = {"build_exe": build_exe_options},#, 'include_files': include_files},
        executables = [Executable("gtcc_cal.py", base=base)])
