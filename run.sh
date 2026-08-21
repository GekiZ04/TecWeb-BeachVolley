#!/usr/bin/env bash
# Avvia il server di sviluppo Django. Uso: ./run.sh (da Git Bash / WSL)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v pipenv >/dev/null 2>&1; then
    python -m pip install --user pipenv
fi

python -m pipenv install
python -m pipenv run python manage.py migrate
python -m pipenv run python manage.py runserver 127.0.0.1:8000
