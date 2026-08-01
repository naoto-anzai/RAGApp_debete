from textwrap import dedent

from e10_report_agent.report_state import ReportState

def create_report_node(llm):

    def report_node(state: ReportState) -> dict:
        prompt = dedent(f"""
            あなたはレポート執筆者です。
            以下のアウトラインに従ってレポートの本文を1000文字以内で作成してください。
            以下の参考資料だけを根拠にして質問に答えてください。
            
            参考資料:
            {state["context"]}
            
            アウトライン:
            {state["outline"]}
            
            質問:
            {state["title"]}
            
            回答ルール:
            - 日本語で答えてください。
            - 初心者にもわかるように説明してください。
            - 参考資料に書かれている内容を優先してください。
            - 参考資料にない内容を推測しないでください。
            """).strip()

        response = llm.invoke(prompt)
        report = response.content.strip()

        print("\n[report_node]")
        print(report)

        return {
            "report": report
        }

    return report_node