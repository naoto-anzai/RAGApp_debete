from debate_agent.debate_state import DebateState


def create_aggregate_node():

    def aggregate_node(state: DebateState) -> dict:
        turns = state["turns"]

        print("\n[aggregate_node]")

        scores = {
            "pro": {"evidences": 0, "passes": 0, "turns": 0},
            "con": {"evidences": 0, "passes": 0, "turns": 0},
        }

        for turn in turns:
            if turn["turn_no"] == 0:
                continue

            side = turn["speaker"]
            scores[side]["turns"] += 1

            if len(turn["evidences"]) > 0:
                scores[side]["evidences"] += len(turn["evidences"])
            else:
                scores[side]["passes"] += 1

        pro = scores["pro"]
        con = scores["con"]

        if pro["evidences"] != con["evidences"]:
            winner = "pro" if pro["evidences"] > con["evidences"] else "con"
        elif pro["passes"] != con["passes"]:
            winner = "pro" if pro["passes"] < con["passes"] else "con"
        else:
            winner = "draw"

        print(f'肯定側: 論拠{pro["evidences"]}件 / パス{pro["passes"]}回')
        print(f'否定側: 論拠{con["evidences"]}件 / パス{con["passes"]}回')
        print(f"勝者: {winner}")

        return {
            "scores": scores,
            "winner": winner,
        }

    return aggregate_node
