import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from dotenv import load_dotenv
load_dotenv()

FILE_NAME = "data/test2.txt"
USER_ID = 2

try:
    with open(FILE_NAME, "r") as f:
        content = f.read()
except FileNotFoundError:
    print(f"File not found: {FILE_NAME}")
    exit()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = text_splitter.split_text(content)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = PineconeVectorStore(
    index_name="docuquery",
    embedding=embeddings,
    pinecone_api_key=os.getenv("PINECONE_API_KEY")
)

docs = [
    Document(page_content=chunk, metadata={"user_id": USER_ID, "source": FILE_NAME})
    for chunk in chunks
]

vector_store.add_documents(docs)

print(f"Ingested {len(chunks)} chunks into Pinecone for user_id={USER_ID}.")