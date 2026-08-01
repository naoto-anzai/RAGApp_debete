#!/usr/bin/env bash
# Debate RAG セットアップスクリプト (Linux / macOS)
# 使い方: プロジェクト直下(RAGApp)で  bash setup.sh  を実行
set -euo pipefail
cd "$(dirname "$0")"

echo "== Debate RAG セットアップ =="

# 1) Python 確認(3.11 推奨)
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 が見つかりません。Python 3.11 をインストールしてください。" >&2
  exit 1
fi
python3 --version

# 2) venv 作成
if [ ! -d ".venv" ]; then
  echo "[1/4] .venv を作成します..."
  python3 -m venv .venv
else
  echo "[1/4] 既存の .venv を使用します"
fi
VENV_PY="./.venv/bin/python"

# 3) 依存インストール(torch等で数GB・十数分かかる場合あり)
echo "[2/4] 依存パッケージをインストールします(数GB・時間がかかります)..."
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r requirements.txt

# 4) .env 準備
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "[3/4] .env を作成しました。エディタで開いて GROQ_API_KEY を設定してください!"
else
  echo "[3/4] .env は既に存在します(GROQ_API_KEY が設定済みか確認してください)"
fi

# 5) ベクトルDB構築
echo "[4/4] ベクトルDB(debate_pro / debate_con)を構築します..."
export PYTHONUTF8=1
"$VENV_PY" -m debate_agent.make_vector_db

echo ""
echo "セットアップ完了! 次のコマンドでデモを実行できます:"
echo "  export PYTHONUTF8=1"
echo "  ./.venv/bin/python -m debate_agent.debate_main"
