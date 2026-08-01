import json
from textwrap import dedent

from debate_agent.debate_state import DebateState

MIN_HITS = 3


def create_setup_topic_node(vectorstores: dict, llm):

    def setup_topic_node(state: DebateState) -> dict:
        topic = state["topic"]

        print("\n[setup_topic_node]")

        prompt = dedent(f"""
            次の論題を、Yes/Noで立場が分かれる命題文に書き換え、
            肯定側・否定側の立場文を1文ずつ作ってください。

            【論題】
            {topic}

            【出力形式】
            次のJSON形式のみで出力してください。
            {{"proposition": "...", "pro": "...", "con": "..."}}
            """).strip()

        response = llm.invoke(prompt)
        raw = response.content.strip()

        raw = raw.replace("```json", "").replace("```", "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        parsed = json.loads(raw[start:end + 1])

        proposition = parsed["proposition"]
        stance_pro = parsed["pro"]
        stance_con = parsed["con"]

        retriever_pro = vectorstores["pro"].as_retriever(
            search_kwargs={"k": MIN_HITS}
        )
        retriever_con = vectorstores["con"].as_retriever(
            search_kwargs={"k": MIN_HITS}
        )

        hits_pro = retriever_pro.invoke(stance_pro)
        hits_con = retriever_con.invoke(stance_con)

        print(f"命題: {proposition}")
        print(f"肯定側: {stance_pro}")
        print(f"否定側: {stance_con}")
        print(f"肯定側の資料: {len(hits_pro)}件 / 否定側の資料: {len(hits_con)}件")

        if len(hits_pro) < MIN_HITS or len(hits_con) < MIN_HITS:
            print("警告: 片方の立場の資料が不足しています。")

        return {
            "topic": proposition,
            "stance_pro": stance_pro,
            "stance_con": stance_con,
        }

    return setup_topic_node
