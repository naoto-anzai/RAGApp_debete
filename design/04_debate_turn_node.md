# debate_turn_node — 発言ターンノード(草案③④)

## 役割

「相手の直前発言に反論する資料を検索し、反論を生成する」1ターン分の処理。
草案の③発言者RAGと④相手方RAGは処理が完全に対称なので、
このノード1本で両方を担い、`current_speaker` で立場を切り替える。

内部は4ステップに分かれる:

| ステップ | 処理 | 使うもの |
|---|---|---|
| (a) 反論対象の特定 | 相手の直前発言から反論すべき主張を取り出す | State操作のみ |
| (b) 反証クエリ生成 | 「その主張に反する証拠」を探すクエリを作る | LLM |
| (c) 検索+フィルタ | 検索 → 使用済み除外 → 立場適合チェック | vectorstore + LLM |
| (d) 反論生成 | 採用した論拠だけを根拠に反論文を作る | LLM |

さらにターン終了時に、弾切れ管理(`dry_streak`)・話者交代・終了判定を行う。

## State との入出力

| 方向 | キー | 内容 |
|---|---|---|
| 入力 | `current_speaker` | いま発言する側 |
| 入力 | `turns` | 発言履歴(最後の要素=相手の直前発言) |
| 入力 | `used_doc_ids` | 使用済みチャンクID |
| 入力 | `dry_streak` | 新規論拠なしの連続回数 |
| 入力 | `turn_count`, `max_turns` | ターン数と上限 |
| 入力 | `stance_pro`, `stance_con` | 自陣営の立場文(プロンプトに使う) |
| 戻り値 | `turns` | 今回の発言を追加したリスト |
| 戻り値 | `used_doc_ids` | 今回使ったチャンクIDを追加したdict |
| 戻り値 | `dry_streak` | 更新後の値 |
| 戻り値 | `current_speaker` | 次に発言する側(交代後) |
| 戻り値 | `turn_count` | +1した値 |
| 戻り値 | `end_reason` | 終了なら `"both_exhausted"` か `"max_turns"`、続行なら `""` |

## ファイル

`debate_agent/nodes/debate_turn_node.py`

## コード骨子

```python
import json

from langchain_chroma import Chroma
from debate_agent.debate_state import DebateState

SEARCH_K = 5        # 1回の検索で取り出す候補チャンク数
MAX_EVIDENCES = 2   # 1ターンで採用する論拠の上限
DRY_LIMIT = 2       # 何回連続「新規論拠なし」で弾切れとみなすか


def create_debate_turn_node(llm, vectorstore: Chroma):

    def debate_turn_node(state: DebateState) -> dict:
        # DebateStateから、必要な情報を取り出す
        speaker = state["current_speaker"]
        turns = state["turns"]
        used_doc_ids = state["used_doc_ids"]
        dry_streak = state["dry_streak"]
        turn_count = state["turn_count"] + 1      # このターンの番号

        # 自陣営の立場文を選ぶ
        my_stance = state["stance_pro"] if speaker == "pro" else state["stance_con"]

        # debate_turn_nodeが呼び出されたことを確認するために表示しておく
        print(f"\n[debate_turn_node] ターン{turn_count}: {speaker}の番")

        # ==========================================
        # (a) 反論対象の特定
        # ==========================================
        # 相手の直前発言(turnsの最後の要素)のclaimを反論対象にする
        target_claim = turns[-1]["claim"]

        # ==========================================
        # (b) 反証クエリ生成(LLM)
        # ==========================================
        # 既出論拠と同じものを引かないよう、自陣営が使った論拠の要約を
        # プロンプトに入れて「異なる角度」を明示的に要求する
        my_past_quotes = [
            ev["quote"][:100]
            for t in turns if t["speaker"] == speaker
            for ev in t["evidences"]
        ]
        query_prompt = f"""あなたはディベートで「{my_stance}」の立場です。
相手の主張: {target_claim}
この主張に反する証拠を文書から探すための検索クエリを1つ作ってください。
ただし、以下の既出の論拠とは異なる角度
(統計データ/因果関係/具体事例/方法論への批判など)を狙ってください。
既出の論拠: {my_past_quotes}
検索クエリの文字列のみを出力してください。"""
        query = llm.invoke(query_prompt).content.strip()

        # ==========================================
        # (c) 検索 + フィルタ
        # ==========================================
        # ベクトルストアから候補チャンクを取り出すretrieverを生成
        retriever = vectorstore.as_retriever(search_kwargs={"k": SEARCH_K})
        docs = retriever.invoke(query)

        evidences = []
        for doc in docs:
            # チャンクIDをつくる(source + page で代用できる)
            doc_id = f'{doc.metadata.get("source", "?")}_p{doc.metadata.get("page_label", "?")}_{hash(doc.page_content) % 100000}'

            # (c-1) 使用済みチャンクは除外する(同じ弾は二度撃てない)
            if doc_id in used_doc_ids[speaker]:
                continue

            # (c-2) 立場適合チェック(LLM)
            # コーパスは賛否両論混在なので、ヒット=味方の証拠ではない。
            # このチャンクが本当に自陣営を支持するかをYes/Noで判定する
            check_prompt = f"""次の資料は「{my_stance}」という立場を
支持する内容ですか? YesかNoのみで答えてください。
資料: {doc.page_content[:500]}"""
            answer = llm.invoke(check_prompt).content.strip()
            if not answer.lower().startswith("yes"):
                continue

            # 採用。出典情報をつけてevidencesに追加する
            evidences.append({
                "doc_id": doc_id,
                "source": doc.metadata.get("source", "不明"),
                "page": doc.metadata.get("page_label", "不明"),
                "quote": doc.page_content[:300],
            })
            if len(evidences) >= MAX_EVIDENCES:
                break

        # 動作確認用に採用数を表示しておく
        print(f"検索{len(docs)}件 → 採用{len(evidences)}件")

        # ==========================================
        # (d) 反論生成(LLM)/ 論拠ゼロなら「パス」
        # ==========================================
        if len(evidences) > 0:
            evidence_text = "\n".join(
                f'[{ev["source"]} p.{ev["page"]}] {ev["quote"]}'
                for ev in evidences
            )
            claim_prompt = f"""あなたはディベートで「{my_stance}」の立場です。
相手の主張: {target_claim}
以下の資料だけを根拠に、150〜250字で反論してください。
資料にない主張はしないこと。根拠には[出典 ページ]を付けること。
資料:
{evidence_text}"""
            claim = llm.invoke(claim_prompt).content.strip()
            dry_streak[speaker] = 0               # 新規論拠あり→連続記録リセット
        else:
            claim = "(有効な新規論拠が見つからず、パス)"
            dry_streak[speaker] += 1              # 新規論拠なし→連続記録+1

        # 発言を表示する(ディベート観戦の本体)
        print(f"--- {speaker}の発言 ---")
        print(claim)

        # ==========================================
        # ターンの記録とState更新
        # ==========================================
        new_turn = {
            "turn_no": turn_count,
            "speaker": speaker,
            "target_claim": target_claim,
            "query": query,
            "claim": claim,
            "evidences": evidences,
        }
        used_doc_ids[speaker] += [ev["doc_id"] for ev in evidences]

        # 終了判定(草案⑤の判定材料をここで確定する)
        exhausted_pro = dry_streak["pro"] >= DRY_LIMIT
        exhausted_con = dry_streak["con"] >= DRY_LIMIT
        if exhausted_pro and exhausted_con:
            end_reason = "both_exhausted"         # 両陣営とも弾切れ
        elif turn_count >= state["max_turns"]:
            end_reason = "max_turns"              # 安全上限に到達
        else:
            end_reason = ""                       # 続行

        # 話者交代(ただし相手が弾切れなら自分が続けて発言する)
        opponent = "con" if speaker == "pro" else "pro"
        opponent_exhausted = dry_streak[opponent] >= DRY_LIMIT
        next_speaker = speaker if opponent_exhausted else opponent

        # DebateStateに格納する戻り値をreturnする
        return {
            "turns": turns + [new_turn],
            "used_doc_ids": used_doc_ids,
            "dry_streak": dry_streak,
            "current_speaker": next_speaker,
            "turn_count": turn_count,
            "end_reason": end_reason,
        }

    return debate_turn_node
```

## 処理の説明

| ブロック | 説明 |
|---|---|
| (a) `turns[-1]["claim"]` | 反論対象は「相手の直前発言」。1ターン目は assign_camps_node が仕込んだ立場文(turn_no=0)が対象になる |
| (b) 既出論拠をプロンプトに入れる | 草案の懸念「何度検索しても同じ反証しか出ないのでは」への対策。**角度を変えたクエリ**をLLMに作らせることで、意見のベクトルを少しずつずらす |
| (c-1) 使用済み除外 | `used_doc_ids` にあるチャンクはスキップ。「リソースがなくなるまで議論する」仕組みの土台 |
| (c-2) 立場適合チェック | ベクトル検索は「関連する文書」を返すだけで「味方の文書」を返すわけではないので、LLMでYes/No判定する |
| (d) パス処理 | 採用0件なら反論を生成せず `dry_streak` を+1。これが2回続くとその陣営は弾切れ(草案⑤) |
| 話者交代 | 片方だけ弾切れの場合、もう片方は続けて発言できる(論拠数の差が⑥のスコア差になる) |

## 動作確認

```
[debate_turn_node] ターン1: proの番
検索5件 → 採用2件
--- proの発言 ---
(引用つきの反論文)
```

パスの場合:

```
[debate_turn_node] ターン7: conの番
検索5件 → 採用0件
--- conの発言 ---
(有効な新規論拠が見つからず、パス)
```

## ver2への拡張ポイント

- (c) に**新規性スコア**を追加: 候補チャンクと既出論拠の埋め込みコサイン類似度を
  計算し、類似度が高すぎる(≒同じ内容の言い換え)チャンクも除外する
- (b) のクエリを2〜3本生成して検索結果をマージする
