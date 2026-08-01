from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

from debate_agent.nodes.setup_topic_node import create_setup_topic_node
from debate_agent.nodes.collect_bet_node import create_collect_bet_node
from debate_agent.nodes.assign_camps_node import create_assign_camps_node
from debate_agent.nodes.debate_turn_node import create_debate_turn_node
from debate_agent.routes.route_after_debate_turn import route_after_debate_turn
from debate_agent.nodes.aggregate_node import create_aggregate_node
from debate_agent.nodes.report_node import create_report_node
from debate_agent.debate_state import DebateState


def create_debate_graph(vectorstores: dict, llm: ChatGroq):

    builder = StateGraph(DebateState)

    builder.add_node(
        "setup_topic",
        create_setup_topic_node(vectorstores, llm),
    )

    builder.add_node(
        "collect_bet",
        create_collect_bet_node(),
    )

    builder.add_node(
        "assign_camps",
        create_assign_camps_node(),
    )

    builder.add_node(
        "debate_turn",
        create_debate_turn_node(vectorstores, llm),
    )

    builder.add_node(
        "aggregate",
        create_aggregate_node(),
    )

    builder.add_node(
        "report",
        create_report_node(llm),
    )

    builder.add_conditional_edges(
        "debate_turn",
        route_after_debate_turn,
        {
            "continue": "debate_turn",
            "finish": "aggregate",
        },
    )

    builder.add_edge(START, "setup_topic")
    builder.add_edge("setup_topic", "collect_bet")
    builder.add_edge("collect_bet", "assign_camps")
    builder.add_edge("assign_camps", "debate_turn")
    builder.add_edge("aggregate", "report")
    builder.add_edge("report", END)

    return builder.compile()
