from debate_agent.debate_state import DebateState


def create_collect_bet_node():

    def collect_bet_node(state: DebateState) -> dict:
        topic = state["topic"]
        stance_pro = state["stance_pro"]
        stance_con = state["stance_con"]

        print("\n[collect_bet_node]")

        print(f"論題: {topic}")
        print(f"  AI-1(肯定側): {stance_pro}")
        print(f"  AI-2(否定側): {stance_con}")

        print("\nどちらが勝つと思いますか?")
        print("1: 肯定側")
        print("2: 否定側")

        while True:
            select = input("選択: ").strip()
            if select in ("1", "2"):
                break
            print("1 か 2 を入力してください。")

        user_bet = "pro" if select == "1" else "con"

        return {
            "user_bet": user_bet
        }

    return collect_bet_node
