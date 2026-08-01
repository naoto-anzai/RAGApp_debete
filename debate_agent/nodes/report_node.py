from textwrap import dedent

from debate_agent.debate_state import DebateState

SIDE_NAME = {"pro": "肯定側", "con": "否定側", "draw": "引き分け"}


def create_report_node(llm):

    def report_node(state: DebateState) -> dict:
        topic = state["topic"]
        user_bet = state["user_bet"]
        winner = state["winner"]
        scores = state["scores"]
        turns = state["turns"]
        end_reason = state["end_reason"]

        print("\n[report_node]")

        # (1) 答え合わせ
        if winner == "draw":
            bet_result = "引き分けのためノーカウント"
        elif user_bet == winner:
            bet_result = "的中!"
        else:
            bet_result = "外れ…"

        # (2) 論点整理(LLM)
        history_text = "\n".join(
            f'ターン{turn["turn_no"]} [{SIDE_NAME[turn["speaker"]]}] {turn["claim"]}'
            for turn in turns if turn["turn_no"] > 0
        )

        summary_prompt = dedent(f"""
            以下はディベートの発言履歴です。
            両陣営の主要な論点をそれぞれ3点以内で整理してください。
            勝敗の評価はせず、論点の整理だけを行ってください。

            【論題】
            {topic}

            【発言履歴】
            {history_text}
            """).strip()

        response = llm.invoke(summary_prompt)
        summary = response.content.strip()

        # (3) 全論拠の出典一覧
        evidence_lines = []
        for turn in turns:
            for ev in turn["evidences"]:
                evidence_lines.append(
                    f'- ターン{turn["turn_no"]} [{SIDE_NAME[turn["speaker"]]}] '
                    f'{ev["file_name"]} p.{ev["page_label"]}: {ev["quote"][:80]}…'
                )
        evidence_list = "\n".join(evidence_lines)

        # (4) 敗者側のベスト論拠
        loser_best = ""
        if winner != "draw":
            loser = "con" if winner == "pro" else "pro"
            for turn in reversed(turns):
                if turn["speaker"] == loser and len(turn["evidences"]) > 0:
                    loser_best = (
                        f'なお、{SIDE_NAME[loser]}にも '
                        f'「{turn["claim"][:100]}…」という論拠がありました。'
                    )
                    break

        # (5) レポートを組み立てる
        report = f"""# ディベート結果レポート

## 論題
{topic}

## 結果
- 勝者: {SIDE_NAME[winner]}(終了理由: {end_reason})
- 論拠数 — 肯定側: {scores["pro"]["evidences"]}件 / 否定側: {scores["con"]["evidences"]}件
- あなたの予想: {SIDE_NAME[user_bet]} → {bet_result}

## 論点整理
{summary}

## 論拠一覧(出典)
{evidence_list}

## 注意
{loser_best}
この結果は与えられた資料の範囲内でのディベートであり、
現実の結論を示すものではありません。原典にあたって確認してください。
"""

        print(report)

        return {
            "report": report
        }

    return report_node
