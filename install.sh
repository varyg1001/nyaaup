#!/bin/sh

destdir="$HOME/.local/bin"

if [ -z "$VIRTUAL_ENV" ]; then
    echo "[+] Creating virtual environment"
    if [ -x "$(command -v virtualenv)" ]; then
        virtualenv -p python3 .venv
    else
        python3 -m venv .venv
    fi
    # shellcheck disable=SC1091
    . .venv/bin/activate
    echo "[+] Upgrading base packages"
    pip install --upgrade pip setuptools wheel
    echo "[+] Installing Poetry"
    pip install --upgrade poetry
fi

echo "[+] Updating Poetry"
pip install --upgrade poetry

echo "[+] Installing dependencies"
git submodule update --init
poetry install "$@"

echo "[+] Creating launcher script"
ln -sf "$(realpath .venv/bin/vt)" ~/.local/bin/vt

echo "[*] Successfully installed to $destdir/vt"
case "$PATH" in
    *"$destdir"*)
        ;;
    *)
        echo "[!] Warning: $destdir is not in PATH. You will not be able to run 'nyaaup' from outside the tool's directory."
esac
