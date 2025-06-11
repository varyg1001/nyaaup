#!/usr/bin/env python3

import os
import platform
import shutil
import subprocess
from pathlib import Path


if not shutil.which("uv"):
    subprocess.run(["pip", "install", "uv"])

print("\n[*] Installing dependencies")
subprocess.run(["uv", "sync", "--frozen", "--link-mode=copy"], check=True)

if platform.system() != "Windows":
    d = Path("~/.local/bin").expanduser()
    d.mkdir(parents=True, exist_ok=True)

    print("\n[*] Installing launcher script")
    (d / "nyaaup").unlink(missing_ok=True)
    (d / "nyaaup").symlink_to(Path(".venv/bin/nyaaup").resolve())

    if not any(
        Path(x).resolve() == d.resolve() for x in os.environ["PATH"].split(os.pathsep)
    ):
        print(f"[!] WARNING: {d} is not in PATH.")
