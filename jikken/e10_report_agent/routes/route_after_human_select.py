from e10_report_agent.report_state import ReportState

def route_after_human_select(state: ReportState) -> str:
    human_select = state["human_select"]

    if human_select == "1":
        print("1")
        return "report"

    if human_select == "2":
        print("2")
        return "outline"

    print(human_select)
    return "end"