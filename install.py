#!/usr/bin/env python3

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

if not shutil.which("uv"):
    print("[*] Installing 'uv' via pip...")
    subprocess.run([sys.executable, "-m", "pip", "install", "uv"], check=True)

print("\n[*] Syncing dependencies...")
subprocess.run(["uv", "sync", "--frozen", "--link-mode=copy"], check=True)

print("\n[*] Installing launcher script")
binary_path = Path(
    ".venv/Scripts/nyaaup.exe" if platform.system() == "Windows" else ".venv/bin/nyaaup"
).resolve()

if platform.system() != "Windows":
    bin_dir = Path("~/.local/bin").expanduser()
    bin_dir.mkdir(parents=True, exist_ok=True)
    launcher = bin_dir / "nyaaup"
    launcher.unlink(missing_ok=True)
    if binary_path.exists():
        launcher.symlink_to(binary_path)
        print(f"[+] Launcher created: {launcher}")

    if not any(
        Path(x).resolve() == bin_dir.resolve()
        for x in os.environ.get("PATH", "").split(os.pathsep)
    ):
        print(f"[!] WARNING: {bin_dir} is not in your PATH.")
else:
    appdata_bin = Path(os.environ.get("LOCALAPPDATA", "C:/")).joinpath(
        "Microsoft/WindowsApps"
    )
    if appdata_bin.exists():
        launcher = appdata_bin / "nyaaup.bat"
        with launcher.open("w") as f:
            f.write(f'@echo off\n"{binary_path}" %*')
        print(f"[+] Windows launcher created: {launcher}")

shell = os.environ.get("SHELL", "").split("/")[-1]
print("\n[*] Shell Autocompletion")
if "zsh" in shell:
    print('    Add to ~/.zshrc: eval "$(_NYAAUP_COMPLETE=zsh_source nyaaup)"')
elif "bash" in shell:
    print('    Add to ~/.bashrc: eval "$(_NYAAUP_COMPLETE=bash_source nyaaup)"')
elif "fish" in shell:
    print(
        "    Run: _NYAAUP_COMPLETE=fish_source nyaaup > ~/.config/fish/completions/nyaaup.fish"
    )
else:
    print("    Refer to 'click' documentation for your shell.")

print("\n[!] Restart your terminal to apply changes.")
