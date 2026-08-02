import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_new_user():
    response = client.post(
        "/auth/register",
        json={"email": "testuser@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "User registration endpoint"

def test_login_with_correct_credentials():
    client.post(
        "/auth/register",
        json={"email": "logintest@example.com", "password": "correctpass"}
    )
    response = client.post(
        "/auth/login",
        json={"email": "logintest@example.com", "password": "correctpass"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password():
    client.post(
        "/auth/register",
        json={"email": "wrongpasstest@example.com", "password": "correctpass"}
    )
    response = client.post(
        "/auth/login",
        json={"email": "wrongpasstest@example.com", "password": "wrongpass"}
    )
    assert response.status_code == 401


def test_login_with_nonexistent_user():
    response = client.post(
        "/auth/login",
        json={"email": "doesnotexist@example.com", "password": "anything"}
    )
    assert response.status_code == 401

def test_query_without_token_is_rejected():
    response = client.post("/query", json={"question": "anything"})
    assert response.status_code == 401


def test_query_with_invalid_token_is_rejected():
    response = client.post(
        "/query",
        json={"question": "anything"},
        headers={"Authorization": "Bearer this_is_not_a_real_token"}
    )
    assert response.status_code == 401


def test_documents_upload_without_token_is_rejected():
    import io
    files = {"file": ("test.txt", io.BytesIO(b"some content"), "text/plain")}
    response = client.post("/documents/upload", files=files)
    assert response.status_code == 401