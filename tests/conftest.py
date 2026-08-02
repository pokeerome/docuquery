import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["DB_FILE"] = "data/test_users.db"
os.environ.setdefault("OPENAI_API_KEY", "test-dummy-key")
os.environ.setdefault("SECRET_KEY", "test-dummy-secret")
os.environ.setdefault("PINECONE_API_KEY", "test-dummy-key")

from unittest.mock import MagicMock

import langchain_pinecone

langchain_pinecone.PineconeVectorStore = MagicMock(return_value=MagicMock())

import pytest

from app.database import DB_FILE, init_db


class FakeDocument:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata


class FakeVectorStore:
    def __init__(self):
        self.storage = []

    def add_documents(self, docs):
        self.storage.extend(docs)

    def similarity_search(self, query, k=5, filter=None):
        results = self.storage
        if filter:
            for key, value in filter.items():
                results = [doc for doc in results if doc.metadata.get(key) == value]
        return results[:k]

@pytest.fixture(autouse=True)
def clean_test_db():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db()
    yield
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

@pytest.fixture
def fake_rag_backend(monkeypatch):
    fake_store = FakeVectorStore()

    monkeypatch.setattr("app.ingest.vector_store", fake_store)
    monkeypatch.setattr("app.query.vector_store", fake_store)

    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = "This is a fake grounded answer."
    monkeypatch.setattr("app.query.llm", fake_llm)

    return fake_store