# 実装計画(Codex 用)— 反証探索ディベートRAG

このファイルは **コード生成エージェント(Codex / GPT-5 high)に渡す実装指示書**。
Codex が推測で埋める余地をなくし、書けば動く状態にすることが目的。

- 各ノードの中身は `design/00〜07` を「仕様」として参照する(このファイルは手順と規約)。
- LLM は **Groq**(`langchain_groq.ChatGroq`)。埋め込みは実習どおり HuggingFace ローカル。
- 実装は下の「実装順序」で **1ファイルずつ作り、都度チェックポイントを実行**して進める。
  まとめて全部書いてから実行すると原因切り分けができず必ず詰まる。

---

## 0. 絶対に守るルール(Codexへの厳命)

1. **勝手にライブラリを変えない。** 下の「確定スタック」以外の import を足さない。
   特に LLM は `langchain_groq.ChatGroq` 固定。`ChatOpenAI` / `openai` を書かない。
2. **ノードの型を統一する。** 全ノードは
   `create_xxx_node(...)` が内側関数 `xxx_node(state: DebateState) -> dict` を返す形。
   戻り値は **更新するStateキーだけ** を入れた dict(全Stateを返さない)。
3. **各ノード先頭で `print("\n[xxx_node]")`** を必ず出す(実習と同じ動作確認方式)。
4. **LLMの出力を信用しない。** JSON要求は `_extract_json()` 経由で必ずパースし、
   Yes/No判定は `_is_yes()` で緩く判定する(§4のヘルパを使う)。素の `json.loads` を直接使わない。
5. **1ステップ書いたら必ずそのステップのチェックポイントを実行**し、
   期待出力が出てから次へ進む。エラーが出たらそのステップ内で直す。
6. パスは `pathlib.Path` を使い、OSは **Windows** 前提(区切りに注意、ただしPathで吸収)。
7. 日本語コメントはそのまま残す。既存 `design/` の関数名・Stateキー名を1文字も変えない。

---

## 1. 確定スタック(これ以外を使わない)

| 項目 | 確定値 |
|---|---|
| Python | 3.11(実習環境に合わせる) |
| LLM | Groq / `ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)` |
| LLM(軽量・判定用) | Groq / `ChatGroq(model="llama-3.1-8b-instant", temperature=0)` |
| 埋め込み | `HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")` |
| ベクトルストア | Chroma(`langchain_chroma.Chroma`)、永続化ディレクトリ `debate_agent/chroma_db` |
| コレクション名 | `"debate_docs"`(生成側と読込側で完全一致させる) |
| グラフ | `langgraph`(`StateGraph, START, END`) |
| 環境変数 | `.env` の `GROQ_API_KEY`(`python-dotenv` の `load_dotenv()` で読む) |

### requirements.txt(そのまま作成)

```
langgraph
langchain-core
langchain-groq
langchain-huggingface
langchain-chroma
langchain-community
sentence-transformers
chromadb
pypdf
python-dotenv
```

> 実習の `.venv` が使えるなら、不足分(`langchain-groq`)だけ `pip install langchain-groq` でよい。

---

## 2. 完成後のディレクトリ構成(ゴール)

```
RAGApp/                              ← いまのプロジェクト直下でよい
├─ .env                             … GROQ_API_KEY=xxxx
├─ requirements.txt
├─ docs_src/                        … 賛否両論を含む元PDFを置く(自分で用意)
│   ├─ pro_xxx.pdf
│   └─ con_yyy.pdf
└─ debate_agent/
    ├─ __init__.py
    ├─ chroma_db/                   … make_vector_db.py が生成(手で作らない)
    ├─ nodes/
    │   ├─ __init__.py
    │   ├─ setup_topic_node.py      … 仕様: design/01
    │   ├─ collect_bet_node.py      … 仕様: design/02
    │   ├─ assign_camps_node.py     … 仕様: design/03
    │   ├─ debate_turn_node.py      … 仕様: design/04
    │   ├─ aggregate_node.py        … 仕様: design/06
    │   └─ report_node.py           … 仕様: design/07
    ├─ common.py                    … §4 の共通ヘルパ(_extract_json / _is_yes / call_llm)
    ├─ make_vector_db.py            … §5
    ├─ debate_state.py              … 仕様: design/00 §3
    ├─ debate_graph.py              … 仕様: design/00 §5(judge_continue含む, design/05)
    └─ debate_main.py               … 仕様: design/00 §6(LLMはChatGroqに差し替え)
```

---

## 3. 実装順序(この順番で、1ファイルずつ)

> 依存の下流から作る。各ステップに「作るもの」と「チェックポイント(CP)」がある。
> CPが通ってから次へ。

### STEP 0 — 環境
- `requirements.txt` を作り `pip install -r requirements.txt`。
- `.env` に `GROQ_API_KEY=...` を書く。
- **CP0:** 次を実行して疎通確認(Groqが喋れば全体の土台OK)。
  ```python
  from dotenv import load_dotenv; load_dotenv()
  from langchain_groq import ChatGroq
  print(ChatGroq(model="llama-3.3-70b-versatile").invoke("ping").content)
  ```
  → 何か返答が表示されればOK。認証エラーなら `.env` を直す。

### STEP 1 — パッケージ土台
- `debate_agent/__init__.py`、`debate_agent/nodes/__init__.py`(中身は空でよい)。
- **CP1:** `python -c "import debate_agent"` がエラーなく通る。

### STEP 2 — 共通ヘルパ `common.py`(§4をそのまま実装)
- **CP2:** §4末尾の自己テストを実行し、JSON抽出とYes判定が期待どおり。

### STEP 3 — ベクトルストア `make_vector_db.py`(§5)
- `docs_src/` に **賛成寄り・反対寄りの資料を両方** 置く(最低でも各1PDF)。
- 実行して `debate_agent/chroma_db` を生成。
- **CP3:** 実行ログに「ベクトルDBを作成しました」等が出て `chroma_db/` ができる。
  さらに検索が効くか単発確認:
  ```python
  # 論題キーワードで数件ヒットすればOK(source/page_label が入っているかも確認)
  ```

### STEP 4 — State `debate_state.py`(design/00 §3 をそのまま)
- **CP4:** `python -c "from debate_agent.debate_state import DebateState"` が通る。

### STEP 5 — ノードを1個ずつ(順に setup→collect→assign→debate→aggregate→report)
各ノードは対応する design/0x を仕様に実装。**ただしLLM呼び出しは `common.call_llm` 経由**、
**JSON/Yesは `_extract_json`/`_is_yes` 経由**に置き換える(design のコード骨子の該当箇所を差し替え)。

- STEP 5a `setup_topic_node.py`(design/01)
  - **CP5a:** §6の単体テストで、命題文・pro/con立場文・ヒット数が表示される。
- STEP 5b `collect_bet_node.py`(design/02)
  - **CP5b:** 対戦カードが表示され、`1`/`2`入力で `{"user_bet": ...}` が返る。
- STEP 5c `assign_camps_node.py`(design/03)
  - **CP5c:** `turns` に turn_no=0 の初期発言1件、`current_speaker="pro"`。
- STEP 5d `debate_turn_node.py`(design/04)
  - **CP5d:** ダミーStateを1回通し、検索件数と採用件数、反論文 or パスが表示される。
- STEP 5e `aggregate_node.py`(design/06)
  - **CP5e:** 作り物の `turns` を渡すと論拠数・勝者が表示される。
- STEP 5f `report_node.py`(design/07)
  - **CP5f:** 作り物のStateからMarkdownレポートが返る。

### STEP 6 — グラフ `debate_graph.py`(design/00 §5 + judge_continue design/05)
- **CP6:** `python -c "from debate_agent.debate_graph import create_debate_graph"` が通る。

### STEP 7 — メイン `debate_main.py`(design/00 §6、LLMは §1 の ChatGroq)
- **CP7(最終):** `python -m debate_agent.debate_main` を実行 →
  論題入力 → 賭け入力 → ターンが数回進む → `both_exhausted` か `max_turns` で終了 →
  レポートが表示され「処理が完了しました」。**正常終了(終了コード0)。**

---

## 4. 共通ヘルパ `debate_agent/common.py`(全文・これをそのまま作る)

Groq(Llama系)は JSON や Yes/No を厳密に返さないことがある。ここで吸収する。

```python
import json
import re
import time


def call_llm(llm, prompt: str, retries: int = 3) -> str:
    """LLM呼び出し。Groqのレート制限・一時エラーを数回リトライして文字列を返す。"""
    last_err = None
    for i in range(retries):
        try:
            return llm.invoke(prompt).content.strip()
        except Exception as e:          # レート制限や瞬断
            last_err = e
            time.sleep(2 * (i + 1))     # 2s, 4s, 6s と待つ
    raise last_err


def _extract_json(text: str) -> dict:
    """LLM出力から最初のJSONオブジェクトを取り出してdictにする。
    ```json ... ``` で囲まれていても、前後に文が付いていても拾う。"""
    # コードフェンスを除去
    text = re.sub(r"```(?:json)?", "", text).strip()
    # 最初の { から対応する } までを素朴に抽出
    start = text.find("{")
    if start == -1:
        raise ValueError(f"JSONが見つかりません: {text[:200]}")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError(f"JSONが閉じていません: {text[:200]}")


def _is_yes(text: str) -> bool:
    """LLMのYes/No回答を緩く判定。先頭付近に yes/はい/支持 があればTrue。"""
    head = text.strip().lower()[:20]
    return any(w in head for w in ("yes", "はい", "支持", "true", "肯定"))


if __name__ == "__main__":   # CP2 の自己テスト
    assert _extract_json('前置き ```json\n{"a": 1}\n``` 後書き') == {"a": 1}
    assert _extract_json('{"proposition":"x","pro":"y","con":"z"}')["pro"] == "y"
    assert _is_yes("Yes, これは支持します") is True
    assert _is_yes("No、支持しません") is False
    print("common.py OK")
```

### design のコード骨子との差し替え規約(重要)

Codex は design/01,04 の骨子にある以下を機械的に置換する:

| design骨子の書き方 | 実装での書き方 |
|---|---|
| `response = llm.invoke(prompt)` + `json.loads(response.content)` | `raw = call_llm(llm, prompt)` + `_extract_json(raw)` |
| `answer = llm.invoke(check_prompt).content.strip()` + `answer.lower().startswith("yes")` | `answer = call_llm(check_llm, check_prompt)` + `_is_yes(answer)` |
| `query = llm.invoke(query_prompt).content.strip()` | `query = call_llm(llm, query_prompt)` |
| `claim = llm.invoke(claim_prompt).content.strip()` | `claim = call_llm(llm, claim_prompt)` |
| `summary = llm.invoke(summary_prompt).content.strip()` | `summary = call_llm(llm, summary_prompt)` |

---

## 5. `make_vector_db.py`(実習流用+今回向け修正)

実習①の `make_vector_db.py` を土台に、以下を必ず反映する。

- 入力PDFを **複数**読む(`docs_src/` 内の全PDF)。賛成寄り・反対寄りを両方入れる。
- `COLLECTION_NAME = "debate_docs"`(§1と一致)。
- 永続化先 `DB_DIR = Path(__file__).resolve().parent / "chroma_db"`。
- チャンクの `metadata` に `source`(ファイル名)と `page_label` が残ること。
  `PyPDFLoader` は `source`・`page` を付ける。debate_turn は `page_label` を見るので、
  **無ければ `page` を `page_label` にコピーする**か、debate_turn 側の `.get("page_label", ...)` を
  `.get("page_label") or doc.metadata.get("page", "不明")` に変更する(どちらかに統一)。
- 埋め込みは §1 のモデルで固定。

骨子:

```python
import shutil
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

PROJECT_DIR = Path(__file__).resolve().parent
DOCS_DIR = PROJECT_DIR.parent / "docs_src"
DB_DIR = PROJECT_DIR / "chroma_db"
COLLECTION_NAME = "debate_docs"


def main():
    if DB_DIR.exists():
        shutil.rmtree(DB_DIR)

    # docs_src 内の全PDFを読み込む
    docs = []
    for pdf in sorted(DOCS_DIR.glob("*.pdf")):
        loaded = PyPDFLoader(str(pdf)).load()
        for d in loaded:
            d.metadata["source"] = pdf.name
            d.metadata["page_label"] = d.metadata.get("page", "不明")
        docs.extend(loaded)

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    Chroma.from_documents(
        chunks,
        embedding=embeddings,
        persist_directory=str(DB_DIR),
        collection_name=COLLECTION_NAME,
    )
    print(f"ベクトルDBを作成しました。チャンク数: {len(chunks)}")


if __name__ == "__main__":
    main()
```

---

## 6. 各ノードの単体テスト雛形(CP5x で使う)

各ノードファイル末尾に付ける確認コード。実習と同じ「単体で叩いて表示を見る」方式。

```python
# --- setup_topic_node.py 末尾(CP5a) ---
if __name__ == "__main__":
    from dotenv import load_dotenv; load_dotenv()
    from langchain_groq import ChatGroq
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    from pathlib import Path

    emb = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    vs = Chroma(
        persist_directory=str(Path(__file__).resolve().parents[1] / "chroma_db"),
        embedding_function=emb, collection_name="debate_docs")
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
    node = create_setup_topic_node(llm, vs)
    print(node({"topic": "地球温暖化って進んでるの?"}))
```

他ノードも同様に、必要な入力キーだけ入れた dict を渡して叩く
(design/0x の「動作確認」節の期待出力と一致すればCP通過)。

---

## 7. Groq固有の注意(ここを外すと動かない/落ちる)

1. **モデル名は実在するものを使う。** 生成: `llama-3.3-70b-versatile`、
   判定(軽量): `llama-3.1-8b-instant`。名前が違うと 400 エラー。
   実行時に落ちたら `ChatGroq` のエラーメッセージにある現行モデル名へ合わせる。
2. **呼び出し回数が多い。** 1ディベートで数十〜百回LLMを呼ぶ(ターン×検索候補の適合判定)。
   無料枠のレート制限に当たりやすい → **適合判定は軽量モデル(8b-instant)**、
   `call_llm` のリトライ+待機で吸収。それでも厳しければ:
   - `SEARCH_K` を 5→3 に、`MAX_EVIDENCES` を 2→1 に、`max_turns` を 12→6 に下げる。
3. **JSON崩れ対策は §4 の `_extract_json` で必須。** Llamaは前置き文を付けがち。
4. `temperature` は生成 0.3、判定 0(判定のブレを消す)。

---

## 8. LangGraph / LangChain の落とし穴

| 症状 | 原因 | 対策 |
|---|---|---|
| `GraphRecursionError` | ループが再帰上限(既定25)超過 | `graph.invoke(state, {"recursion_limit": 50})`(design/00 §6 済) |
| 検索が0件 | コレクション名不一致 | 生成側/読込側の `COLLECTION_NAME` を `"debate_docs"` に統一 |
| `page_label` が None | PyPDFLoaderは `page` を付ける | make_vector_db で `page_label` にコピー(§5) |
| import エラー | 実行方法 | ルートから `python -m debate_agent.debate_main` で実行(相対import解決) |
| 立場適合が全部False | 判定プロンプトが厳しすぎ/Yes判定が硬い | `_is_yes` で緩く判定(§4)。それでも0なら判定を一時スキップして検索通過で採用 |
| 無限にpassしない | dry_streakが増えない | debate_turn の採用0件時に `dry_streak[speaker] += 1` が通っているか確認 |

---

## 9. 最終受け入れ条件(Definition of Done)

- [ ] `python -m debate_agent.debate_main` が例外なく最後まで走り、終了コード0。
- [ ] 論題入力→賭け入力→複数ターンの発言(引用付き)がコンソールに流れる。
- [ ] 終了理由が `both_exhausted` または `max_turns` で表示される。
- [ ] 最後に Markdown レポート(結果・答え合わせ・論点整理・出典一覧・注記)が出る。
- [ ] 同じ資料・同じ論題で2回流しても勝敗集計がクラッシュしない(数勘定は再現的)。

---

## 10. Codex に渡す指示文(このままコピペ)

```
あなたは Python 実装エージェントです。以下の設計に厳密に従い、反証探索ディベートRAGアプリを実装してください。

【最重要】
- 参照設計は同フォルダの design/00〜08 です。design/08_実装計画_Codex.md を主手順書とし、
  各ノードの中身は design/00〜07 を仕様として使ってください。
- LLM は Groq(langchain_groq.ChatGroq)固定。ChatOpenAI や openai は絶対に使わないこと。
- 埋め込みは HuggingFace ローカル(paraphrase-multilingual-MiniLM-L12-v2)固定。
- 全ノードは create_xxx_node(...) が xxx_node(state)->dict を返す形。戻り値は更新キーだけの dict。
- LLM呼び出しは common.call_llm 経由、JSON は _extract_json、Yes/No は _is_yes 経由(design/08 §4)。
- design/08 §3 の STEP 順で 1ファイルずつ実装し、各 STEP のチェックポイント(CP)を実行して
  期待出力を確認してから次へ進むこと。まとめ書きして最後に実行するのは禁止。

【スタック】design/08 §1 の確定スタックと requirements.txt をそのまま使う。勝手に足さない。
【構成】design/08 §2 のディレクトリ構成をゴールにする。
【完了条件】design/08 §9 のチェックリストを全て満たすこと。

まず STEP 0(環境・.env・CP0の疎通確認)から始め、各ステップの実行結果を報告しながら進めてください。
```
```

---

## 付録: このリポジトリ側で先にやっておくと事故らないこと

- `docs_src/` に **賛成寄り・反対寄りの資料を必ず両方** 入れる(片側だけだと即弾切れ=議論にならない)。
- `.env` に Groq のキーを入れておく(`GROQ_API_KEY=...`)。
- 実習の `.venv` を使うなら `pip install langchain-groq` だけ先に通しておく。
