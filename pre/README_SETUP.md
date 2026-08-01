# Debate RAG デモ セットアップ手順(別環境向け)

AI同士が資料に基づいて討論する RAG デモ(`debate_agent/`)を、新しいマシンで動かすための手順です。

---

## 1. 事前準備(必須)

| 項目 | 内容 |
|------|------|
| **Python** | 3.11 系(動作確認は 3.11.4)。`python --version` で確認。 |
| **インターネット接続** | 初回のみ Hugging Face から埋め込みモデル(約120MB)を自動DL。 |
| **Groq APIキー** | https://console.groq.com/keys で発行(無料枠あり)。 |
| **資料PDF** | `docs_src/pro/*.pdf`(肯定側)と `docs_src/con/*.pdf`(否定側)が存在すること。リポジトリに含まれていなければ配布物からコピーする。 |

> ⚠️ ディスク: `torch` などで **数GB** を使います。インストールに十数分かかることがあります。

---

## 2. かんたんセットアップ(スクリプト)

プロジェクト直下(`RAGApp/`)で実行します。venv作成 → 依存インストール → `.env`作成 → ベクトルDB構築までを自動で行います。

### Windows (PowerShell)
```powershell
.\setup.ps1
```
> 実行がブロックされる場合は一度だけ:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### Linux / macOS
```bash
bash setup.sh
```

スクリプトが `.env` を新規作成したら、**エディタで開いて `GROQ_API_KEY` を実際のキーに書き換えてください**(この手順を忘れると実行時に認証エラーになります)。

---

## 3. 手動セットアップ(スクリプトを使わない場合)

```bash
# 1) venv 作成
python -m venv .venv

# 2) 有効化
#   Windows PowerShell:
.\.venv\Scripts\Activate.ps1
#   Linux / macOS:
source .venv/bin/activate

# 3) 依存インストール
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4) .env を用意して GROQ_API_KEY を設定
#   Windows:  Copy-Item .env.example .env
#   Linux/mac: cp .env.example .env
#   → .env を編集して GROQ_API_KEY=... を記入

# 5) ベクトルDB(debate_pro / debate_con)を構築
python -m debate_agent.make_vector_db
```

---

## 4. デモの実行

```bash
#   Windows PowerShell:
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m debate_agent.debate_main

#   Linux / macOS:
export PYTHONUTF8=1
./.venv/bin/python -m debate_agent.debate_main
```

実行すると論題(例: `地球温暖化は進んでいる?`)を聞かれ、続いてどちらが勝つかの予想(`1`=肯定側 / `2`=否定側)を入力します。あとは AI 同士が資料に基づいて討論し、最後に結果レポートが表示されます。

---

## 5. トラブルシューティング

- **`UnicodeEncodeError: ... surrogates not allowed`**
  日本語入出力の文字コード問題です。実行前に **`PYTHONUTF8=1`**(上記コマンド)を必ず設定してください。標準入力にパイプで日本語を渡す場合は特に必須です。

- **`GROQ_API_KEY` 関連の認証エラー / 401**
  `.env` に有効なキーが設定されているか確認。`.env` はプロジェクト直下(`debate_main.py` は `load_dotenv()` でカレントの `.env` を読みます)。

- **Groq のレート制限(429)**
  無料枠の制限です。少し時間を置いて再実行してください。`common.py` にリトライは入っています。

- **`torch` のインストールに失敗 / GPUを使いたい**
  `requirements.txt` の `torch==2.13.0` は CPU 前提の固定です。GPU(CUDA)環境では、いったんこの行を外して https://pytorch.org の案内に従い環境に合ったビルドを入れてから、残りを `pip install -r requirements.txt` してください。

- **資料が少なくてすぐ討論が終わる**
  各陣営の資料が少ないと早く「弾切れ」になります。`docs_src/pro/` `docs_src/con/` に資料PDFを追加し、`python -m debate_agent.make_vector_db` でDBを作り直してください。

- **資料を入れ替えたのに反映されない**
  `make_vector_db` を再実行するとDB(`debate_agent/chroma_db/`)を丸ごと作り直します。実行を忘れていないか確認してください。
