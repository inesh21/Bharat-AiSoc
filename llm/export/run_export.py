"""Helper script to run ExecuTorch export_llm on Windows with proper DLL path resolution."""

import os
import sys
import shutil
import torch

# Ensure ExecuTorch shared libraries are discoverable by Windows DLL loader
venv_root = os.path.dirname(os.path.dirname(sys.executable))
site_packages = os.path.join(venv_root, "Lib", "site-packages")
et_lib = os.path.join(site_packages, "executorch", "lib")
scripts_dir = os.path.join(venv_root, "Scripts")
flatc_bin_dir = os.path.join(site_packages, "executorch", "data", "bin")

# Add to PATH so subprocess.run(["flatc", ...]) resolves on Windows
os.environ["PATH"] = scripts_dir + os.pathsep + flatc_bin_dir + os.pathsep + et_lib + os.pathsep + os.environ.get("PATH", "")

if hasattr(os, "add_dll_directory"):
    if os.path.exists(et_lib):
        os.add_dll_directory(et_lib)
    if os.path.exists(scripts_dir):
        os.add_dll_directory(scripts_dir)

# Ensure flatc is resolvable
import executorch.exir._serialize._flatbuffer as fb
original_get_flatc_path = fb._get_flatc_path

def get_flatc_path_fixed():
    flatc_exe = os.path.join(flatc_bin_dir, "flatc.exe")
    if os.path.exists(flatc_exe):
        return flatc_exe
    scripts_flatc = os.path.join(scripts_dir, "flatc.exe")
    if os.path.exists(scripts_flatc):
        return scripts_flatc
    which_flatc = shutil.which("flatc")
    if which_flatc:
        return which_flatc
    return original_get_flatc_path()

fb._get_flatc_path = get_flatc_path_fixed

# Pre-load custom_ops_aot_lib so torch.ops.llama is populated
custom_ops_dll = os.path.join(
    site_packages, "executorch", "extension", "llm", "custom_ops", "custom_ops_aot_lib.dll"
)
if os.path.exists(custom_ops_dll):
    torch.ops.load_library(custom_ops_dll)

from executorch.extension.llm.export.export_llm import main

if __name__ == "__main__":
    main()
