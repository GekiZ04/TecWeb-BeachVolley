#!/usr/bin/env bash
# Avvia il server di sviluppo Django. Uso: ./run.sh (da Git Bash su Windows, oppure dal
# Terminale su Mac/Linux).
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# su macOS/Linux di solito c'è solo "python3", non "python" — controllo quale dei due esiste
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
else
    PYTHON=python
fi

if ! command -v pipenv >/dev/null 2>&1; then
    "$PYTHON" -m pip install --user pipenv
fi

"$PYTHON" -m pipenv install
"$PYTHON" -m pipenv run python manage.py migrate
"$PYTHON" -m pipenv run python manage.py runserver 127.0.0.1:8000
