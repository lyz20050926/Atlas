#!/usr/bin/env sh
set -eu
atlas_root=$(CDPATH= cd "$(dirname "$0")" && pwd)
cd "$atlas_root"
if [ -x "$atlas_root/.venv/bin/python" ]; then
    exec "$atlas_root/.venv/bin/python" "$atlas_root/launch.py" "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 "$atlas_root/launch.py" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "$atlas_root/launch.py" "$@"
else
    echo 'Python 3.11+ is required. Install Python, create .venv, then install requirements.txt.' >&2
    exit 2
fi
