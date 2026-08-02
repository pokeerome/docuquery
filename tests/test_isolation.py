import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register_and_login(email, password):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def test_users_cannot_see_each_others_documents(fake_rag_backend, monkeypatch):
    token_a = register_and_login("usera@example.com", "passa123")
    token_b = register_and_login("userb@example.com", "passb123")

    # Simulate User A's document being ingested with their real user_id
    import io
    files_a = {"file": ("a.txt", io.BytesIO(b"Secret content only User A should see"), "text/plain")}
    client.post("/documents/upload", headers={"Authorization": f"Bearer {token_a}"}, files=files_a)

    files_b = {"file": ("b.txt", io.BytesIO(b"Different content only User B should see"), "text/plain")}
    client.post("/documents/upload", headers={"Authorization": f"Bearer {token_b}"}, files=files_b)

    # Confirm isolation: each user's chunks in the fake store have distinct user_ids
    user_ids_stored = {doc.metadata["user_id"] for doc in fake_rag_backend.storage}
    assert len(user_ids_stored) == 2

    a_docs = [doc for doc in fake_rag_backend.storage if doc.metadata["user_id"] == next(iter(user_ids_stored))]
    b_docs = [doc for doc in fake_rag_backend.storage if doc.metadata["user_id"] == list(user_ids_stored)[1]]

    a_content = " ".join(doc.page_content for doc in a_docs)
    b_content = " ".join(doc.page_content for doc in b_docs)

    assert "Secret content" in a_content
    assert "Secret content" not in b_content
    assert "Different content" in b_content
    assert "Different content" not in a_content