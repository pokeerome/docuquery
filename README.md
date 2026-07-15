# DocuQuery — Multi-Tenant RAG API

A production-oriented Retrieval-Augmented Generation (RAG) API built with FastAPI, LangChain, and Pinecone. Users authenticate, upload their own documents through an authenticated endpoint, and query them through natural language — with strict per-user data isolation enforced at the retrieval layer. Deployed on AWS ECS Fargate behind a CI/CD pipeline.

> **Status:** Core build complete (Milestones 1–3 and 5). Live demo available — see [Live Demo](#live-demo) below. Automated evaluation harness (Milestone 4) is a planned next step — see [Roadmap](#roadmap).

## Live Demo

The API is deployed on AWS ECS Fargate. Try it yourself:

```bash
# 1. Register
curl -X POST http://100.25.197.136:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'

# 2. Log in
curl -X POST http://100.25.197.136:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'

# 3. Upload a document (use the access_token from step 2)
curl -X POST http://100.25.197.136:8000/documents/upload \
  -H "Authorization: Bearer <your_token>" \
  -F "file=@yourfile.txt"

# 4. Ask a question about it
curl -X POST http://100.25.197.136:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{"question": "your question here"}'
```

> **Note:** the demo IP is tied to a single ECS task without a load balancer, so it can change if the task restarts. See [Known Limitations](#known-limitations).

## Why This Project Exists

Most RAG demos are single-user, single-session toys — call an LLM API, retrieve some chunks, done. This project goes further: it answers the question *"can multiple users safely share one RAG service, self-serve their own documents, and run it as a real deployed system — not just a script on my laptop?"* — a set of constraints any production RAG system actually has to solve.

## Features

- **Retrieval-Augmented Generation** — documents are chunked, embedded, and stored in Pinecone; questions are answered using only retrieved, grounded context (no hallucinated answers outside the source material)
- **JWT-based authentication** — secure registration and login, with bcrypt password hashing and signed, expiring access tokens
- **Self-serve document upload** — authenticated users upload their own `.txt` documents via `POST /documents/upload`; validated for type, size, and encoding before processing
- **Multi-tenant data isolation** — every document chunk is tagged with the owning user's ID at ingestion time, and every query is filtered by that same ID at retrieval time. Verified with two-account isolation testing, in both directions, on both ChromaDB (initial) and Pinecone (current)
- **Structured query logging** — every question, its retrieved context, and its answer are logged to a JSONL file, forming the foundation for future automated evaluation
- **Protected API endpoints** — routes require a valid bearer token; invalid, missing, or expired tokens are rejected before any business logic runs
- **Containerized and cloud-deployed** — packaged with Docker, deployed on AWS ECS Fargate with Secrets Manager-backed configuration and CloudWatch logging
- **Automated CI checks** — GitHub Actions verifies dependency installation and Docker build success on every push

## Tech Stack

- **Backend:** FastAPI
- **AI/LLM:** OpenAI API (`gpt-4o-mini` for generation, `text-embedding-3-small` for embeddings), LangChain
- **Vector Store:** Pinecone (managed, cloud-hosted, namespaced by user via metadata filtering)
- **Auth:** JWT (PyJWT), Passlib + bcrypt for password hashing
- **Database:** SQLite (user records)
- **Package management:** uv
- **Containerization:** Docker
- **CI/CD:** GitHub Actions
- **Cloud infrastructure:** AWS ECS Fargate, ECR, Secrets Manager, IAM, CloudWatch Logs, VPC/Security Groups

## Architecture

```
Client
  │
  ├── POST /auth/register       → hash password → store user in SQLite
  ├── POST /auth/login          → verify password → issue signed JWT
  ├── GET  /auth/me             → validate token → return current user
  ├── POST /documents/upload    → validate file → chunk → embed → store in Pinecone (tagged with user_id)
  │
  └── POST /query  (requires valid bearer token)
         │
         ├── decode + validate JWT → resolve current_user
         ├── embed question
         ├── similarity search in Pinecone, filtered by user_id
         ├── build grounded prompt from retrieved chunks
         ├── call LLM for answer
         ├── log {question, chunks, answer} to JSONL
         └── return answer
```

**Deployment architecture:**

```
GitHub push → GitHub Actions (build + dependency check)
                    │
Local: docker build → docker push → Amazon ECR
                    │
AWS ECS Fargate service (pulls from ECR)
   ├── reads secrets from AWS Secrets Manager (OpenAI, Pinecone, JWT keys)
   ├── logs to CloudWatch
   └── publicly reachable via assigned public IP (VPC + Security Group, port 8000 open)
```

## How Data Isolation Is Enforced

Every chunk stored in Pinecone carries a `user_id` field in its metadata, set at ingestion time. Every retrieval call passes a `filter={"user_id": current_user_id}` argument to Pinecone's similarity search — meaning a user's query vector is only ever compared against chunks they own. This was verified with two independent test accounts on both the original ChromaDB implementation and again after migrating to Pinecone: each user correctly answered questions about their own uploaded document, and correctly received "I don't know" when asked about the other user's document — in both directions, on both backends.

## Setup (Local Development)

```bash
git clone <this-repo>
cd docuquery
uv sync
```

Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_openai_key_here
SECRET_KEY=your_random_secret_here
PINECONE_API_KEY=your_pinecone_key_here
```

Generate a secure `SECRET_KEY`:
```bash
uv run python -c "import secrets; print(secrets.token_hex(32))"
```

Create your Pinecone index (one-time):
```bash
uv run python -m app.setup_pinecone
```

Run the server:
```bash
uv run uvicorn app.main:app --reload
```

Interactive API docs available at `http://127.0.0.1:8000/docs`. The SQLite user database initializes automatically on startup.

## Running with Docker

```bash
docker build -t docuquery .
docker run -p 8000:8000 --env-file .env docuquery
```

## Deploying to AWS (Summary)

1. Build and push the image to Amazon ECR
2. Store secrets (`OPENAI_API_KEY`, `SECRET_KEY`, `PINECONE_API_KEY`) in AWS Secrets Manager
3. Register an ECS task definition (see `task-definition.example.json` for the structure — replace placeholders with your own AWS account details)
4. Create an ECS Fargate service with a public IP-enabled network configuration
5. Open the relevant port on the associated security group

## Roadmap

- [x] **Milestone 1** — Core RAG pipeline: ingestion, embedding, retrieval, generation, FastAPI endpoint, query logging
- [x] **Milestone 2** — Authentication (JWT, bcrypt) and multi-tenant data isolation, verified with two-user testing
- [x] **Milestone 3** — Migrated from local ChromaDB to Pinecone; isolation re-verified on the new backend
- [x] **Milestone 5** — Dockerized, added CI/CD (GitHub Actions), deployed to AWS ECS Fargate; added authenticated self-serve document upload endpoint
- [ ] **Milestone 4** — Automated evaluation harness (faithfulness, relevance, regression detection via Ragas or similar)
- [ ] Add a Load Balancer for a stable, non-changing public URL
- [ ] Add automated test suite (pytest)

## Known Limitations

- **Unstable public IP** — the current deployment uses a single Fargate task without a load balancer; the public IP changes if the task restarts. A load balancer with a fixed DNS name would resolve this.
- **No automated test suite yet** — all verification so far has been manual (curl-based end-to-end testing), though thorough (including two-account isolation testing on both vector store backends).
- **No formal evaluation metrics yet** — query quality has been verified manually rather than via automated scoring (planned).
- **Text files only** — `/documents/upload` currently accepts `.txt` files only; no PDF/DOCX support yet.
- **No document deletion** — uploaded documents accumulate in Pinecone; there's currently no endpoint to remove a previously uploaded document.

## What I'd Do Differently at Scale

At higher scale, I'd move from filtering a shared Pinecone index by `user_id` metadata to fully namespaced storage per tenant (Pinecone supports this natively), add rate limiting per user to control LLM API cost exposure, move query logging from a flat JSONL file to a proper time-series-queryable store for real monitoring, and put the ECS service behind an Application Load Balancer for both a stable URL and the ability to scale beyond a single task.

## Debugging Journal (Selected Issues Encountered)

Documenting real issues hit during development, since debugging production systems is as much a part of building them as writing the initial code:

- **SQLite silently creates empty databases.** `sqlite3.connect()` doesn't error if the target directory is missing in the way you'd expect — instead the app crashed with `unable to open database file` inside a fresh Docker container, because the `data/` directory didn't exist in the image. Fixed by explicitly creating the directory in the Dockerfile and calling `init_db()` on app startup via a lifespan handler.
- **Local port conflicts caused a false-positive test result.** An old local `uvicorn` process left running on port 8000 caused test requests to silently hit the wrong server while debugging a seemingly-passing Docker container — the container was actually crashing the whole time. Resolved by explicitly checking `docker logs` for request activity rather than trusting curl output alone.
- **IAM permissions for CloudWatch log group creation.** The default `AmazonECSTaskExecutionRolePolicy` doesn't include `logs:CreateLogGroup`, causing ECS tasks to fail on startup when using `awslogs-create-group: true`. Fixed by attaching `CloudWatchLogsFullAccess` to the task execution role.
- **ECR authentication tokens expire.** `docker push` began failing with a `403 Forbidden` after a period of inactivity between sessions — ECR login tokens are short-lived and need to be refreshed via `aws ecr get-login-password` before pushing again.