#!/bin/sh

if ! [ -x "$(command -v poetry)" ]; then
  echo "ERROR: poetry is not installed. Please install it and try again." >&2
  echo "Installing Poetry"
  pip install poetry
fi

poetry install

venv=${VIRTUAL_ENV:-$(poetry env info --path)}
if [ -z "$venv" ]; then
  echo "ERROR: Unable to find virtualenv." >&2
fi

executable="$venv/bin/nyaaup"
if ! [ -f "$executable" ]; then
  echo "ERROR: $executable doesn't exist." >&2
  exit 1
fi
mkdir -p ~/.local/bin
ln -sf "$executable" ~/.local/bin/