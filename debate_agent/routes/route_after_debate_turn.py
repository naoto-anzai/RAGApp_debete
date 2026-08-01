from debate_agent.debate_state import DebateState


def route_after_debate_turn(state: DebateState) -> str:
    end_reason = state["end_reason"]

    if end_reason != "":
        print(f"\n試合終了: {end_reason}")
        return "finish"

    return "continue"
