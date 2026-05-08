#!/usr/bin/env bash
# Compatible con macOS, Linux y Windows (Git Bash / WSL)

set -e

VENV_DIR=".venv"

# ── 1. Instalar uv si no está disponible ──────────────────────────────────────
if ! command -v uv &>/dev/null; then
    echo "uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Using $(uv --version)"

# ── 2. Crear el entorno virtual si no existe ──────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in '$VENV_DIR'..."
    uv venv "$VENV_DIR"
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

# ── 4. Instalar/actualizar dependencias ──────────────────────────────────────
echo "Installing/updating dependencies from pyproject.toml..."
uv pip install --upgrade -e .

# ── 5. Arrancar la aplicación ─────────────────────────────────────────────────
echo "Starting bs-telegram-server..."
python app.py

