#!/usr/bin/env bash
# Compatible con macOS, Linux y Windows (Git Bash / WSL)

set -e

VENV_DIR=".venv"

# ── 1. Localizar el ejecutable de Python 3.13 ────────────────────────────────
if command -v python3.13 &>/dev/null; then
    PYTHON=python3.13
elif [ -x "/opt/homebrew/bin/python3.13" ]; then
    PYTHON=/opt/homebrew/bin/python3.13
elif [ -x "/usr/local/bin/python3.13" ]; then
    PYTHON=/usr/local/bin/python3.13
else
    echo "ERROR: python3.13 not found. Install it with: brew install python@3.13" >&2
    exit 1
fi

echo "Using $($PYTHON --version)"

# ── 2. Crear el entorno virtual si no existe ──────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in '$VENV_DIR'..."
    $PYTHON -m venv "$VENV_DIR"
fi

# ── 3. Activar el entorno virtual ─────────────────────────────────────────────
# Windows (Git Bash) usa Scripts/activate; macOS/Linux usan bin/activate
if [ -f "$VENV_DIR/Scripts/activate" ]; then
    source "$VENV_DIR/Scripts/activate"
elif [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "ERROR: virtual environment activation script not found." >&2
    exit 1
fi

# ── 4. Actualizar pip e instalar dependencias ────────────────────────────────
PIP="$VENV_DIR/bin/pip"
if [ -f "$VENV_DIR/Scripts/pip" ]; then
    PIP="$VENV_DIR/Scripts/pip"
fi

"$PIP" install --upgrade pip --quiet

if ! "$PIP" show bstelegramserver &>/dev/null; then
    echo "Upgrading pip..."
    "$PIP" install --upgrade pip
    echo "Installing dependencies from pyproject.toml..."
    "$PIP" install -e .
fi

# ── 5. Arrancar la aplicación ─────────────────────────────────────────────────
echo "Starting bstelegramserver..."
"$VENV_DIR/bin/python" app.py

