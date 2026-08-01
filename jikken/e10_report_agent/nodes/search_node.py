from langchain_chroma import Chroma
from e10_report_agent.report_state import ReportState

def create_search_node(vectorstore: Chroma):

    def search_node(state: ReportState) -> dict:
        title=state["title"]

        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 3}
        )

        docs = retriever.invoke(title);

        context_parts = []

        for index, doc in enumerate(docs, start=1):
            page = doc.metadata.get("page_label", "不明")

            context_parts.append(
                f" [資料{index}] \n"
                f"ページ: {page} \n"
                f"{doc.page_content[:800]}"
            )

        print("\n[search_node]")
        print(f"{len(docs)}件の資料を検索しました。")

        return {
            "context": "\n\n---\n\n".join(context_parts),
        }

    return search_node