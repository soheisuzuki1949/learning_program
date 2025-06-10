#!/bin/bash

# エラーが発生した場合、直ちにスクリプトを終了する
set -e

echo "--- Running setup.sh for Streamlit Lab Setup ---"
echo "Current working directory: $(pwd)"
echo "Checking if uv is available: $(which uv)"

UV_BIN=$(which uv)
if [ -z "$UV_BIN" ]; then
  echo "Error: uv command not found in PATH. Attempting fallback for manual install."
  python3 -m pip install --no-cache-dir uv || { echo "Error: Manual uv installation failed. Aborting."; exit 1; }
  UV_BIN=$(which uv)
  if [ -z "$UV_BIN" ]; then
    echo "Critical Error: uv could not be found or installed. Cannot create virtual environment. Aborting Codespace creation."; exit 1;
  fi
  # .bashrcへのPATH追加とsourceは、Codespaceが完全に起動した後のセッションに影響するため、ここでは行わない
  # featuresとremoteEnvでPATHが設定されることを期待する
  echo "uv path after manual install: $(which uv)"
fi

echo "Creating virtual environment using uv at: ./.venv"
# uv venv が失敗した場合に備え、より詳細なエラーメッセージを出す
"$UV_BIN" venv || { echo "Error: uv venv failed to create virtual environment. Aborting Codespace creation."; exit 1; }

echo "Installing dependencies from .devcontainer/requirements.txt into ./.venv"
# uv pip install が失敗した場合に備え、より詳細なエラーメッセージを出す
"./.venv/bin/uv" pip install -r ./.devcontainer/requirements.txt || { echo "Error: uv pip install failed. Aborting Codespace creation."; exit 1; }

echo "Verifying .venv/bin contents after installation:"
ls -lF ./.venv/bin || echo "Warning: ./.venv/bin not found after install."

echo "Attempting to verify streamlit installation:"
"./.venv/bin/streamlit" --version || echo "Error: Streamlit not found in ./.venv/bin after installation. This is critical."

echo "--- setup.sh finished ---"