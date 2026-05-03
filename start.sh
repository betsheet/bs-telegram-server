#!/usr/bin/env bash
# Compatible con macOS, Linux y Windows (Git Bash / WSL)

set -e

VENV_DIR=".venv"

# ── 1. Localizar el ejecutable de Python ─────────────────────────────────────
if command -v python &>/dev/null; then
    PYTHON=python
elif command -v python3 &>/dev/null; then
    PYTHON=python3
else
    echo "ERROR: python not found in system" >&2
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

# ── 4. Instalar dependencias si el paquete no está instalado ──────────────────
if ! pip show bstelegramserver &>/dev/null; then
    echo "Installing dependencies from pyproject.toml..."
    pip install -e .
fi

# ── 5. Arrancar la aplicación ─────────────────────────────────────────────────
echo "Starting bstelegramserver..."
python app.py

