import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def get_token():
    client.post("/auth/register", json={"email": "uploadtest@example.com", "password": "pass123"})
    response = client.post("/auth/login", json={"email": "uploadtest@example.com", "password": "pass123"})
    return response.json()["access_token"]


def test_upload_rejects_non_txt_file(fake_rag_backend):
    token = get_token()
    files = {"file": ("document.pdf", io.BytesIO(b"fake pdf content"), "application/pdf")}
    response = client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )
    assert response.status_code == 400
    assert "Only .txt files" in response.json()["detail"]


def test_upload_rejects_oversized_file(fake_rag_backend):
    token = get_token()
    large_content = b"x" * (1_000_001)  # 1 byte over your MAX_FILE_SIZE
    files = {"file": ("big.txt", io.BytesIO(large_content), "text/plain")}
    response = client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )
    assert response.status_code == 400
    assert "too large" in response.json()["detail"]


def test_upload_rejects_empty_file(fake_rag_backend):
    token = get_token()
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    response = client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_upload_accepts_valid_txt_file(fake_rag_backend):
    token = get_token()
    files = {"file": ("valid.txt", io.BytesIO(b"This is valid content"), "text/plain")}
    response = client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )
    assert response.status_code == 200
    assert "Ingested" in response.json()["message"]