import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from dotenv import load_dotenv
load_dotenv()

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = PineconeVectorStore(
    index_name="docuquery",
    embedding=embeddings,
    pinecone_api_key=os.getenv("PINECONE_API_KEY")
)


def ingest_text(content: str, user_id: int, source_name: str) -> int:
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_text(content)

    docs = [
        Document(page_content=chunk, metadata={"user_id": user_id, "source": source_name})
        for chunk in chunks
    ]

    vector_store.add_documents(docs)
    return len(chunks)


if __name__ == "__main__":
    FILE_NAME = "data/test.txt"
    USER_ID = 1

    try:
        with open(FILE_NAME, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"File not found: {FILE_NAME}")
        exit()

    num_chunks = ingest_text(content, USER_ID, FILE_NAME)
    print(f"Ingested {num_chunks} chunks into Pinecone for user_id={USER_ID}.")