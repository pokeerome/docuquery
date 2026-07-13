import json
from datetime import datetime, timezone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from dotenv import load_dotenv
load_dotenv()



embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = Chroma(
    collection_name="docuquery_test",
    embedding_function=embeddings,
    persist_directory="data/chroma_persist"
)

llm = ChatOpenAI(model="gpt-4o-mini")

LOG_FILE = "data/query_log.jsonl"


def log_query(question: str, chunks: list[str], answer: str):
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "retrieved_chunks": chunks,
        "answer": answer,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def answer_question(question: str, user_id: int):
    results = vector_store.similarity_search(question, k=5, filter={"user_id": user_id})
    chunk_texts = [doc.page_content for doc in results]
    context = "\n\n".join(chunk_texts)

    prompt = f"""Answer the question using ONLY the context below. If the answer isn't in the context, say you don't know.

    Context:
    {context}

    Question: {question}

    Answer:"""

    response = llm.invoke(prompt)
    answer = response.content

    log_query(question, chunk_texts, answer)

    return answer


if __name__ == "__main__":
    test_question = "What did Jack ignore?"
    answer = answer_question(test_question, user_id=1)
    print(f"Q: {test_question}")
    print(f"A: {answer}")