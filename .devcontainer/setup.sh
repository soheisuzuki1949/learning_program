#!/bin/bash

# コマンドが非ゼロのステータスで終了した場合、直ちに終了する。
set -e

echo "--- カスタムセットアップスクリプトを開始します ---"

echo "1. pipをアップグレードしています..."
pip install --no-cache-dir --upgrade pip

echo "2. uvをグローバルにインストールしています..."
# 正しいPythonのpipであることを確認するため、python3 -m pip install を使用します
python3 -m pip install --no-cache-dir uv

echo "3. ~/.bashrc に ~/.local/bin をPATHに追加しています（存在しない場合のみ）..."
grep -qxF 'export PATH="$HOME/.local/bin:$PATH"' "$HOME/.bashrc" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"

echo "4. このセッションのPATHを更新するため、~/.bashrc をソースしています..."
source "$HOME/.bashrc"

echo "5. uvのインストールを確認しています（パスが表示されるはずです）..."
which uv || { echo "エラー: インストールとPATH設定後もuvコマンドが見つかりません。中止します。"; exit 1; }

echo "6. uvを使用して仮想環境を作成しています..."
# uvが見つからなかった場合に備え、uvへのフルパスを使用します（より堅牢にするため）
UV_PATH=$(which uv)
if [ -z "$UV_PATH" ]; then
    echo "エラー: uvのパスが見つかりません。フォールバックを試みます。"
    # which uvが失敗したが、uvが標準のユーザーbinにインストールされている場合のフォールバック
    if [ -x "$HOME/.local/bin/uv" ]; then
        UV_PATH="$HOME/.local/bin/uv"
    else
        echo "致命的なエラー: uv実行ファイルが見つかりません。仮想環境を作成できません。"
        exit 1
    fi
fi

"$UV_PATH" venv || { echo "エラー: uv venv が失敗しました。詳細についてはログを確認してください。中止します。"; exit 1; }

echo "7. ./.devcontainer/requirements.txt から仮想環境に依存関係をインストールしています..."
# 仮想環境内のuvへのフルパスを使用します
"./.venv/bin/uv" pip install -r ./.devcontainer/requirements.txt || { echo "エラー: uv pip install が失敗しました。中止します。"; exit 1; }

echo "8. インストール後の.venv/binの内容をリストしています:"
ls -lF ./.venv/bin || echo "エラー: venv作成とインストール後も./.venv/binディレクトリが見つかりません。"

echo "9. 最終チェックのためにvenv内でstreamlitを直接探しています:"
"./.venv/bin/streamlit" --version || echo "インストール後にvenvでStreamlitが見つかりません。これは予期せぬ事態です。"

echo "--- カスタムセットアップスクリプトが完了しました ---"