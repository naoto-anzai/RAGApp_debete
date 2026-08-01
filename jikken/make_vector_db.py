import shutil
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from torch.nn.functional import embedding

PDF_FILE = "stream.pdf"
DB_DIR = "./chroma_db"
COLLECTION_NAME = "stream_pdf"

def main():
    if Path(DB_DIR).exists():
        shutil.rmtree(DB_DIR)

    loader = PyPDFLoader(PDF_FILE)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )

    split_docs = splitter.split_documents(docs)

    for doc in split_docs:
        doc.metadata["file_name"] = PDF_FILE

        page = doc.metadata.get("page")
        if page is not None:
            doc.metadata["page_label"] = page + 1

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/"
                   "paraphrase-multilingual-MiniLM-L12-v2",
    )

    Chroma.from_documents(
        documents=split_docs,
        embedding=embeddings,
        persist_directory=DB_DIR,
        collection_name=COLLECTION_NAME
    )

    print("ベクトルDBを作成しました。")

if __name__ == "__main__":
    main()