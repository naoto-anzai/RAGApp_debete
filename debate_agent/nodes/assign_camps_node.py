from debate_agent.debate_state import DebateState


def create_assign_camps_node():

    def assign_camps_node(state: DebateState) -> dict:
        stance_con = state["stance_con"]

        print("\n[assign_camps_node]")
        print("先攻: 肯定側(pro) / 後攻: 否定側(con)")

        initial_turn = {
            "turn_no": 0,
            "speaker": "con",
            "target_claim": "",
            "query": "",
            "claim": stance_con,
            "evidences": [],
        }

        return {
            "current_speaker": "pro",
            "turns": [initial_turn],
            "used_doc_ids": {"pro": [], "con": []},
            "dry_streak": {"pro": 0, "con": 0},
            "turn_count": 0,
            "end_reason": "",
        }

    return assign_camps_node
