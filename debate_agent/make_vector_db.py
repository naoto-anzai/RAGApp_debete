import shutil
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

PROJECT_DIR = Path(__file__).resolve().parent
DOCS_DIR = PROJECT_DIR.parent / "docs_src"
DB_DIR = PROJECT_DIR / "chroma_db"

# 陣営ごとに別コレクションを作る(資料の取り違えを構造的に防ぐ)
#   (陣営キー, PDFフォルダ, コレクション名)
CAMPS = [
    ("pro", DOCS_DIR / "pro", "debate_pro"),
    ("con", DOCS_DIR / "con", "debate_con"),
]


def load_chunks(camp_dir):
    docs = []

    for pdf in sorted(camp_dir.glob("*.pdf")):
        loader = PyPDFLoader(str(pdf))
        loaded = loader.load()

        for doc in loaded:
            doc.metadata["file_name"] = pdf.name

            page = doc.metadata.get("page")
            if page is not None:
                doc.metadata["page_label"] = page + 1

        docs.extend(loaded)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )

    return splitter.split_documents(docs)


def main():
    if DB_DIR.exists():
        shutil.rmtree(DB_DIR)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/"
                   "paraphrase-multilingual-MiniLM-L12-v2",
    )

    for camp, camp_dir, collection_name in CAMPS:
        chunks = load_chunks(camp_dir)

        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=str(DB_DIR),
            collection_name=collection_name,
        )

        print(f"[{camp}] コレクション '{collection_name}' を作成しました。チャンク数: {len(chunks)}")


if __name__ == "__main__":
    main()
