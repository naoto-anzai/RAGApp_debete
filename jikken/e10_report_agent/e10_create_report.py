# オフラインで行う
# import os
# os.environ["HF_HUB_OFFLINE"] = "1"
# os.environ["TRANSFORMERS_OFFLINE"] = "1"

from pathlib import Path
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from e10_report_agent.report_graph import create_report_graph
from e10_report_agent.report_state import ReportState

load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parent
DB_DIR = PROJECT_DIR / "chroma_db"
COLLECTION_NAME = "stream_pdf"

def main():

    embeddings = HuggingFaceEmbeddings(
        model_name=(
            "sentence-transformers/"
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
    )

    vectorstore = Chroma(
        persist_directory=str(DB_DIR),
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME
    )

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        max_tokens=700
    )

    graph = create_report_graph(
        vectorstore=vectorstore,
        llm=llm,
    )

    title="JavaのStreamについて1000字以内でレポートを作成してください"

    initial_state : ReportState = {
        "title": title,
        "context": "",
        "outline": "",
        "human_select": "0",
        "report": ""
    }

    graph.invoke(initial_state)

    print("処理が完了しました。")

if __name__ == "__main__":
    main()
