from pathlib import Path
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from debate_agent.debate_graph import create_debate_graph
from debate_agent.debate_state import DebateState

load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parent
DB_DIR = PROJECT_DIR / "chroma_db"


def main():

    embeddings = HuggingFaceEmbeddings(
        model_name=(
            "sentence-transformers/"
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
    )

    vectorstores = {
        "pro": Chroma(
            persist_directory=str(DB_DIR),
            embedding_function=embeddings,
            collection_name="debate_pro",
        ),
        "con": Chroma(
            persist_directory=str(DB_DIR),
            embedding_function=embeddings,
            collection_name="debate_con",
        ),
    }

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
    )

    graph = create_debate_graph(
        vectorstores=vectorstores,
        llm=llm,
    )

    topic = input("論題を入力してください(例: 地球温暖化は進んでいる?): ")

    initial_state: DebateState = {
        "topic": topic,
        "stance_pro": "",
        "stance_con": "",
        "user_bet": "",
        "current_speaker": "",
        "turns": [],
        "used_doc_ids": {},
        "dry_streak": {},
        "turn_count": 0,
        "max_turns": 12,
        "end_reason": "",
        "scores": {},
        "winner": "",
        "report": "",
    }

    graph.invoke(
        initial_state,
        {"recursion_limit": 50},
    )

    print("\n処理が完了しました。")


if __name__ == "__main__":
    main()
