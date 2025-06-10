#!/bin/bash

# エラーが発生した場合、直ちにスクリプトを終了する
set -e

echo "--- Running setup.sh for Streamlit Lab Setup ---"
echo "Current working directory: $(pwd)"

# uvがインストールされているか確認
if ! command -v uv &> /dev/null
then
    echo "Error: uv command not found. Codespace setup failed."
    exit 1
fi

echo "Creating virtual environment using uv at: ./.venv"
# uv venv が失敗した場合、エラーメッセージを出して終了
uv venv || { echo "Error: uv venv failed to create virtual environment. Aborting setup."; exit 1; }

echo "Installing dependencies from .devcontainer/requirements.txt into ./.venv"
# uv pip install が失敗した場合、エラーメッセージを出して終了
./.venv/bin/uv pip install -r ./.devcontainer/requirements.txt || { echo "Error: uv pip install failed. Aborting setup."; exit 1; }

echo "Verifying .venv/bin contents after installation:"
ls -lF ./.venv/bin || echo "Warning: ./.venv/bin not found after install."

echo "Attempting to verify streamlit installation:"
./.venv/bin/streamlit --version || { echo "Error: Streamlit not found in ./.venv/bin after installation. This is critical."; exit 1; }

echo "--- setup.sh finished ---"