# setup_topic_node — 論題設定ノード(草案①)

## 役割

ユーザーが入力した論題の生文字列を、ディベートできる形に整える。

1. 論題を「Yes/Noで立場が分かれる命題文」に正規化する(LLM)
2. 肯定側・否定側の立場文を作る(LLM)
3. 両方の立場に資料があるかチェックする(ベクトル検索)
   → 草案の懸念「対立する意見をソースに含まないといけない」への対策

## State との入出力

| 方向 | キー | 内容 |
|---|---|---|
| 入力 | `topic` | ユーザーが入力した生の論題文字列 |
| 戻り値 | `topic` | 命題文に正規化した論題 |
| 戻り値 | `stance_pro` | 肯定側の立場文(1文) |
| 戻り値 | `stance_con` | 否定側の立場文(1文) |

## ファイル

`debate_agent/nodes/setup_topic_node.py`

## コード骨子

```python
import json

from langchain_chroma import Chroma
from debate_agent.debate_state import DebateState

# 両立場に最低何件の資料ヒットが必要か(ディベート可能性チェックの基準)
MIN_HITS = 3


def create_setup_topic_node(llm, vectorstore: Chroma):

    def setup_topic_node(state: DebateState) -> dict:
        # DebateStateから、入力パラメータ"topic"を取り出す
        topic = state["topic"]

        # setup_topic_nodeが呼び出されたことを確認するために表示しておく
        print("\n[setup_topic_node]")

        # ==========================================
        # (1) 命題化と立場文の生成(LLM・1回呼び出し)
        # ==========================================
        # JSONで {"proposition": 命題文, "pro": 肯定立場文, "con": 否定立場文}
        # を返させる
        prompt = f"""次の論題を、Yes/Noで立場が分かれる命題文に書き換え、
肯定側・否定側の立場文を1文ずつ作ってください。
論題: {topic}
以下のJSON形式のみで答えてください。
{{"proposition": "...", "pro": "...", "con": "..."}}"""
        response = llm.invoke(prompt)
        parsed = json.loads(response.content)

        proposition = parsed["proposition"]
        stance_pro = parsed["pro"]
        stance_con = parsed["con"]

        # ==========================================
        # (2) ディベート可能性チェック(ベクトル検索)
        # ==========================================
        # 立場文ごとに検索して、双方にMIN_HITS件以上ヒットするか確認する
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": MIN_HITS}
        )
        hits_pro = retriever.invoke(stance_pro)
        hits_con = retriever.invoke(stance_con)

        # 動作確認用にヒット数を表示しておく
        print(f"肯定側の資料: {len(hits_pro)}件 / 否定側の資料: {len(hits_con)}件")

        # 片側に資料が足りなければ警告する
        # (ver1では警告のみで続行。ver2で論題の再入力に分岐させる)
        if len(hits_pro) < MIN_HITS or len(hits_con) < MIN_HITS:
            print("警告: 片方の立場の資料が不足しています。議論がすぐ終わる可能性があります。")

        # DebateStateに格納する戻り値をreturnする
        return {
            "topic": proposition,
            "stance_pro": stance_pro,
            "stance_con": stance_con,
        }

    return setup_topic_node
```

## 処理の説明

| ブロック | 説明 |
|---|---|
| `llm.invoke(prompt)` | 命題化・立場文生成を1回のLLM呼び出しにまとめる(JSON出力を指定) |
| `json.loads(...)` | LLMの返答をdictに変換。パース失敗時は ver1では例外のままでよい |
| `retriever.invoke(stance_pro)` | 立場文そのものをクエリにして試し検索。似た資料が拾えるかだけ確認する |
| 警告print | ver1は続行。ver2でここを条件分岐エッジにして「論題再入力」へ戻す拡張ができる |

## 動作確認

単体で確認する場合は、ファイル末尾に以下を書いて実行する。

```python
if __name__ == "__main__":
    # embeddings, vectorstore, llm を debate_main.py と同じ手順で生成してから
    node = create_setup_topic_node(llm, vectorstore)
    result = node({"topic": "地球温暖化って進んでるの?"})
    print(result)
```

期待する表示:

```
[setup_topic_node]
肯定側の資料: 3件 / 否定側の資料: 3件
{'topic': '地球温暖化は進行している', 'stance_pro': '...', 'stance_con': '...'}
```
