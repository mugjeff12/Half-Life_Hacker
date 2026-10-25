#!/usr/bin/env bash
# macOS / Linux:  ./build.sh   (add --onefile on Linux for a single binary)
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
python build.py --test "$@"
echo; echo 'Your app is in the "dist" folder.'
