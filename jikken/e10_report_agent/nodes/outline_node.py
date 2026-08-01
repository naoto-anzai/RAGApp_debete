from textwrap import dedent
from langchain_groq import ChatGroq

from e10_report_agent.report_state import ReportState

def create_outline_node(llm: ChatGroq):

    def search_node(state: ReportState) -> dict:
        title=state["title"]
        context=state["context"]

        prompt = dedent(f"""
            あなたは大学生向けレポートの構成を考える編集者です。
            次の依頼と参考資料をもとに、
            レポートの構成案だけを作成してください。
            
            【レポート作成依頼】
            {title}
            
            【参考資料】
            {context}
            
            【条件】
            - 省は4章から６章程度にして下さい。
            - 「はじめに」と「まとめ」を含めてください。
            - 各章に、何を書くかを１文で説明してください。
            - 本文はまだ書かないでください。
            - 日本語で出力してください。
            """).strip()

        response = llm.invoke(prompt)
        outline = response.content.strip()

        print("\n[outline_node]")
        
        return {
            "outline": outline
        }
    
    return search_node