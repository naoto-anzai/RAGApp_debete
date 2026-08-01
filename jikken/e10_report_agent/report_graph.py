from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

from e10_report_agent.nodes.search_node import create_search_node
from e10_report_agent.nodes.outline_node import create_outline_node
from e10_report_agent.nodes.human_select_node import create_human_select_node
from e10_report_agent.routes.route_after_human_select import route_after_human_select
from e10_report_agent.nodes.create_report_node import create_report_node
from e10_report_agent.nodes.save_word_node import create_save_word_node
from e10_report_agent.report_state import ReportState

def create_report_graph(
        vectorstore: Chroma,
        llm: ChatGroq
):

    builder = StateGraph(ReportState)

    builder.add_node(
        "search",
        create_search_node(vectorstore),
    )

    builder.add_node(
        "outline",
        create_outline_node(llm)
    )

    builder.add_node(
        "human_select",
        create_human_select_node()
    )

    builder.add_node(
        "report",
        create_report_node(llm)
    )

    builder.add_node(
        "save_word",
        create_save_word_node()
    )

    builder.add_conditional_edges(
        "human_select",
        route_after_human_select,
        {
            "outline": "outline",
            "report": "report",
            "end": END
        }
    )

    builder.add_edge(START, "search")
    builder.add_edge("search", "outline")
    builder.add_edge("outline", "human_select")
    builder.add_edge("report", "save_word")
    builder.add_edge("save_word", END)

    return builder.compile()