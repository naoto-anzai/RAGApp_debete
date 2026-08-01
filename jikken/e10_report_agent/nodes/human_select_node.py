from e10_report_agent.report_state import ReportState

def create_human_select_node():

    def human_select_node(state: ReportState) -> dict:
        outline = state["outline"]

        print("\n生成された構成案")
        print(outline)

        print("\n次の操作を選んでください。")
        print("1: この構成で本文を作成")
        print("2: 構成案を作り直す")
        print("3: 終了")

        choice = input("選択: ").strip()

        print("\n[human_select_node]")

        return {
            "human_select": choice
        }

    return human_select_node