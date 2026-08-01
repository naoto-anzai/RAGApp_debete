# report_node — 答え合わせ・レポートノード(草案⑦)

## 役割

ユーザーの賭けと勝敗を照合し、試合全体のレポート(Markdown)を作って表示する。

1. 答え合わせ(的中/外れ)
2. 試合サマリ(LLM。草案の「5. 論点整理」に相当)
3. 全論拠の出典一覧(ユーザーが原典を確認できるように)
4. バランス注記 — 草案の懸念「過信/自信喪失」への対策

## State との入出力

| 方向 | キー | 内容 |
|---|---|---|
| 入力 | `topic`, `user_bet`, `winner`, `scores`, `turns`, `end_reason` | ほぼ全部 |
| 戻り値 | `report` | レポート全文(Markdown文字列) |

## ファイル

`debate_agent/nodes/report_node.py`

## コード骨子

```python
from debate_agent.debate_state import DebateState

SIDE_NAME = {"pro": "肯定側", "con": "否定側", "draw": "引き分け"}


def create_report_node(llm):

    def report_node(state: DebateState) -> dict:
        # DebateStateから、必要な情報を取り出す
        topic = state["topic"]
        user_bet = state["user_bet"]
        winner = state["winner"]
        scores = state["scores"]
        turns = state["turns"]

        # report_nodeが呼び出されたことを確認するために表示しておく
        print("\n[report_node]")

        # ==========================================
        # (1) 答え合わせ
        # ==========================================
        if winner == "draw":
            bet_result = "引き分けのためノーカウント"
        elif user_bet == winner:
            bet_result = "的中!🎉"
        else:
            bet_result = "外れ…"

        # ==========================================
        # (2) 試合サマリ(LLM)— 論点整理
        # ==========================================
        # 発言履歴を時系列テキストにする(turn_no=0のダミー発言は除く)
        history_text = "\n".join(
            f'ターン{t["turn_no"]} [{SIDE_NAME[t["speaker"]]}] {t["claim"]}'
            for t in turns if t["turn_no"] > 0
        )
        summary_prompt = f"""以下はディベートの発言履歴です。
論題: {topic}
{history_text}
両陣営の主要な論点をそれぞれ3点以内で整理してください。
勝敗の評価はせず、論点の整理だけを行ってください。"""
        summary = llm.invoke(summary_prompt).content.strip()

        # ==========================================
        # (3) 全論拠の出典一覧
        # ==========================================
        evidence_lines = []
        for t in turns:
            for ev in t["evidences"]:
                evidence_lines.append(
                    f'- ターン{t["turn_no"]} [{SIDE_NAME[t["speaker"]]}] '
                    f'{ev["source"]} p.{ev["page"]}: {ev["quote"][:80]}…'
                )
        evidence_list = "\n".join(evidence_lines)

        # ==========================================
        # (4) 敗者側のベスト論拠 + バランス注記
        # ==========================================
        # 「一方的な決着ではない」ことを見せるため、負けた側の論拠を1つ拾う
        loser = "con" if winner == "pro" else "pro"
        loser_best = ""
        if winner != "draw":
            for t in reversed(turns):
                if t["speaker"] == loser and len(t["evidences"]) > 0:
                    loser_best = (
                        f'なお、{SIDE_NAME[loser]}にも '
                        f'「{t["claim"][:100]}…」という有力な論拠がありました。'
                    )
                    break

        # ==========================================
        # (5) レポートを組み立てる
        # ==========================================
        report = f"""# ディベート結果レポート

## 論題
{topic}

## 結果
- 勝者: **{SIDE_NAME[winner]}**(終了理由: {state["end_reason"]})
- 論拠数 — 肯定側: {scores["pro"]["evidences"]}件 / 否定側: {scores["con"]["evidences"]}件
- あなたの予想: {SIDE_NAME[user_bet]} → **{bet_result}**

## 論点整理
{summary}

## 論拠一覧(出典)
{evidence_list}

## 注意
{loser_best}
この結果は与えられた資料の範囲内でのディベートであり、
現実の結論を示すものではありません。原典にあたって確認してください。
"""

        # DebateStateに格納する戻り値"report"をreturnする
        return {"report": report}

    return report_node
```

## 処理の説明

| ブロック | 説明 |
|---|---|
| (2) サマリのLLM | 「勝敗の評価はしない」と明示する。評価まで任せるとジャッジAI問題が再発する |
| (3) 出典一覧 | ディベート教材としての本体。ユーザーが原典を確認する導線 |
| (4) 敗者側のベスト論拠 | 草案の懸念「反対意見がなくなるとユーザーが過信する」対策。勝敗がついても両論あることを見せる |
| (4) 定型注記 | 「資料の範囲内の結果であって現実の結論ではない」を必ず入れる(過信・自信喪失の両対策) |

## 動作確認

メイン(`debate_main.py`)が `final_state["report"]` を表示するので、
最後にMarkdownのレポートが出力されて正常終了すればOK。

```
[report_node]
処理が完了しました
# ディベート結果レポート
...
```

## ver2への拡張ポイント

- レポートを `.md` ファイルに保存する(実習①の save_word_node の要領で、
  `save_report_node` を後ろに足すだけ)
- Streamlit化して、発言をチャット風に逐次表示する
