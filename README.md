# DocuQuery — Multi-Tenant RAG API

A production-oriented Retrieval-Augmented Generation (RAG) API built with FastAPI, LangChain, and ChromaDB. Users authenticate, upload documents, and query them through natural language — with strict per-user data isolation enforced at the retrieval layer.

> **Status:** Actively in development. Milestones 1–2 complete (core RAG pipeline, authentication, and multi-tenancy). See [Roadmap](#roadmap) below for what's next.

## Why This Project Exists

Most RAG demos are single-user, single-session toys — call an LLM API, retrieve some chunks, done. This project goes further: it's built to answer the question *"can multiple users safely share one RAG service without seeing each other's data?"* — a real constraint any production RAG system has to solve.

## Features (Current)

- **Retrieval-Augmented Generation** — documents are chunked, embedded, and stored in ChromaDB; questions are answered using only retrieved, grounded context (no hallucinated answers outside the source material)
- **JWT-based authentication** — secure registration and login, with bcrypt password hashing and signed, expiring access tokens
- **Multi-tenant data isolation** — every document chunk is tagged with the owning user's ID at ingestion time, and every query is filtered by that same ID at retrieval time. Verified with automated two-user isolation testing (see below)
- **Structured query logging** — every question, its retrieved context, and its answer are logged to a JSONL file, forming the foundation for future automated evaluation
- **Protected API endpoints** — routes require a valid bearer token; invalid, missing, or expired tokens are rejected before any business logic runs

## Tech Stack

- **Backend:** FastAPI
- **AI/LLM:** OpenAI API (`gpt-4o-mini` for generation, `text-embedding-3-small` for embeddings), LangChain
- **Vector Store:** ChromaDB (local persistence; migration to Pinecone planned — see Roadmap)
- **Auth:** JWT (PyJWT), Passlib + bcrypt for password hashing
- **Database:** SQLite (user records)
- **Package management:** uv

## Architecture

```
Client
  │
  ├── POST /auth/register  → hash password → store user in SQLite
  ├── POST /auth/login     → verify password → issue signed JWT
  ├── GET  /auth/me         → validate token → return current user
  │
  └── POST /query  (requires valid bearer token)
         │
         ├── decode + validate JWT → resolve current_user
         ├── embed question
         ├── similarity search in ChromaDB, filtered by user_id
         ├── build grounded prompt from retrieved chunks
         ├── call LLM for answer
         ├── log {question, chunks, answer} to JSONL
         └── return answer
```

## How Data Isolation Is Enforced

Every chunk stored in ChromaDB carries a `user_id` field in its metadata, set at ingestion time. Every retrieval call passes a `filter={"user_id": current_user_id}` argument to ChromaDB's similarity search — meaning a user's query vector is only ever compared against chunks they own. This was verified manually with two independent test accounts: each user was able to correctly answer questions about their own uploaded document, and correctly received "I don't know" when asked about the other user's document, in both directions.

## Setup

```bash
git clone <this-repo>
cd docuquery
uv sync
```

Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_openai_key_here
SECRET_KEY=your_random_secret_here
```

Generate a secure `SECRET_KEY`:
```bash
uv run python -c "import secrets; print(secrets.token_hex(32))"
```

Initialize the database:
```bash
uv run python -c "from app.database import init_db; init_db()"
```

Run the server:
```bash
uv run uvicorn app.main:app --reload
```

Interactive API docs available at `http://127.0.0.1:8000/docs`.

## Usage

**1. Register:**
```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'
```

**2. Log in:**
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'
```
Copy the returned `access_token`.

**3. Query (requires the token from step 2):**
```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{"question": "your question here"}'
```

## Roadmap

This project follows a milestone-based build plan. Progress so far:

- [x] **Milestone 1** — Core RAG pipeline: ingestion, embedding, retrieval, generation, FastAPI endpoint, query logging
- [x] **Milestone 2** — Authentication (JWT, bcrypt) and multi-tenant data isolation, verified with two-user testing
- [ ] **Milestone 3** — Migrate from local ChromaDB to a managed vector database (Pinecone)
- [ ] **Milestone 4** — Automated evaluation harness (faithfulness, relevance, regression detection)
- [ ] **Milestone 5** — Dockerize, add CI/CD, and deploy to cloud infrastructure (AWS)

## Known Limitations

- Currently runs locally only — no cloud deployment yet (planned for Milestone 5)
- Vector storage is local ChromaDB, not yet a production-grade managed vector database (planned for Milestone 3)
- No automated test suite yet (pytest coverage planned)
- No formal evaluation metrics beyond manual verification (planned for Milestone 4)
- Document ingestion is currently a manual script, not yet exposed as an authenticated API endpoint

## What I'd Do Differently at Scale

At higher scale, I'd move from filtering a shared ChromaDB collection by `user_id` metadata to fully namespaced storage per tenant (Pinecone supports this natively), add rate limiting per user to control LLM API cost exposure, and move query logging from a flat JSONL file to a proper time-series-queryable store for real monitoring.