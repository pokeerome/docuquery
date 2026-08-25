# DocuQuery — Multi-Tenant RAG API

A production-oriented Retrieval-Augmented Generation (RAG) API built with FastAPI, LangChain, and Pinecone. Users authenticate, upload their own documents through an authenticated endpoint, and query them through natural language — with strict per-user data isolation enforced at the retrieval layer, automated LLM-judged quality evaluation, and a full CI/CD pipeline deploying to AWS.

> **Status:** Complete (Milestones 1–5). Live demo available — see [Live Demo](#live-demo) below.

## Live Demo

The API is deployed on AWS ECS Fargate. Try it yourself:

## Live Demo

The API is deployed on AWS ECS Fargate. Try it yourself:

```cmd
# 1. Register

curl.exe -X POST "http://docuquery-alb-1962360824.us-east-1.elb.amazonaws.com/auth/register" -H "Content-Type: application/json" -d "{\"email\":\"you@example.com\",\"password\":\"yourpassword\"}"

# 2. Log in

curl.exe -X POST "http://docuquery-alb-1962360824.us-east-1.elb.amazonaws.com/auth/login" -H "Content-Type: application/json" -d "{\"email\":\"you@example.com\",\"password\":\"yourpassword\"}"

# 3. Upload a document (use the access_token from step 2)

curl.exe -X POST "http://docuquery-alb-1962360824.us-east-1.elb.amazonaws.com/documents/upload" -H "Authorization: Bearer <your_token>" -F "file=@yourfile.txt"

# 4. Ask a question about it

curl.exe -X POST "http://docuquery-alb-1962360824.us-east-1.elb.amazonaws.com/query" -H "Content-Type: application/json" -H "Authorization: Bearer <your_token>" -d "{\"question\":\"your question here\"}"

> **Note:** this URL is served through an Application Load Balancer, so it stays stable even if the underlying ECS task restarts.

## Why This Project Exists

Most RAG demos are single-user, single-session toys — call an LLM API, retrieve some chunks, done. This project goes further: it answers the question *"can multiple users safely share one RAG service, self-serve their own documents, run it as a real deployed system, and have automated proof the answers are actually good — not just a script on my laptop?"* — a set of constraints any production RAG system actually has to solve.

## Features

- **Retrieval-Augmented Generation** — documents are chunked, embedded, and stored in Pinecone; questions are answered using only retrieved, grounded context (no hallucinated answers outside the source material)
- **JWT-based authentication** — secure registration and login, with bcrypt password hashing and signed, expiring access tokens
- **Self-serve document upload** — authenticated users upload their own `.txt` documents via `POST /documents/upload`; validated for type, size, and encoding before processing
- **Multi-tenant data isolation** — every document chunk is tagged with the owning user's ID at ingestion time, and every query is filtered by that same ID at retrieval time. Verified with two-account isolation testing, in both directions, on both ChromaDB (initial) and Pinecone (current)
- **Automated LLM-judged evaluation** — a golden set of test questions (including deliberately unanswerable ones) is run through the live pipeline and scored on faithfulness, relevancy, and correct-refusal accuracy, with results logged for tracking over time
- **Structured query logging** — every question, its retrieved context, and its answer are logged to a JSONL file
- **Protected API endpoints** — routes require a valid bearer token; invalid, missing, or expired tokens are rejected before any business logic runs
- **Containerized and cloud-deployed** — packaged with Docker, deployed on AWS ECS Fargate with Secrets Manager-backed configuration and CloudWatch logging
- **Per-user rate limiting** — `/query` and `/documents/upload` are limited to 10 requests per minute per authenticated user (via `slowapi`, keyed by JWT identity rather than IP), protecting against cost-abuse and accidental client-side retry loops
- **Prompt injection defense (two-layer)** — the system prompt explicitly instructs the model to treat retrieved document context as untrusted data, never as instructions to follow, and retrieved chunks are additionally scanned against a list of common injection patterns before reaching the LLM, with any matches logged as a warning
- **Automated test suite** — a pytest suite covering authentication flows, token enforcement on protected endpoints, upload validation, and — most importantly — multi-tenant data isolation, fully mocked against external APIs (OpenAI, Pinecone) so it runs in seconds with no real API cost, wired into GitHub Actions CI
- **Automated CI checks** — GitHub Actions verifies dependency installation, runs the full test suite, and confirms Docker build success on every push

## Tech Stack

- **Backend:** FastAPI
- **AI/LLM:** OpenAI API (`gpt-4o-mini` for generation and evaluation judging, `text-embedding-3-small` for embeddings), LangChain
- **Vector Store:** Pinecone (managed, cloud-hosted, namespaced by user via metadata filtering)
- **Auth:** JWT (PyJWT), Passlib + bcrypt for password hashing
- **Database:** SQLite (user records)
- **Evaluation:** Custom LLM-as-judge harness (see [Evaluation](#evaluation) below)
- **Testing:** pytest, with FastAPI's `TestClient` and mocked external dependencies (OpenAI, Pinecone)
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
   └── reachable via Application Load Balancer (stable DNS name) → task's private IP (VPC + Security Group, port 8000 open only to the ALB)
```

## How Data Isolation Is Enforced

Every chunk stored in Pinecone carries a `user_id` field in its metadata, set at ingestion time. Every retrieval call passes a `filter={"user_id": current_user_id}` argument to Pinecone's similarity search — meaning a user's query vector is only ever compared against chunks they own. This was verified with two independent test accounts on both the original ChromaDB implementation and again after migrating to Pinecone: each user correctly answered questions about their own uploaded document, and correctly received "I don't know" when asked about the other user's document — in both directions, on both backends.

## Evaluation

Rather than relying on manual spot-checks, answer quality is measured automatically against a golden set of test questions (`app/eval/golden_set.py`), including deliberately unanswerable questions to test for hallucination resistance.

Two evaluation runners exist:

- **`app/eval/run_eval.py`** — a fast, simple keyword-based check: does the answer contain the expected key terms?
- **`app/eval/run_llm_eval.py`** — a custom LLM-as-judge harness. For each question, a second LLM call scores the generated answer on:
  - **Faithfulness** — is the answer fully supported by the retrieved context, with nothing invented?
  - **Relevancy** — does the answer actually address the question? (measured only on genuinely answerable questions — see note below)
  - **Refusal accuracy** — on deliberately unanswerable questions, did the system correctly decline to answer rather than hallucinate?

**A note on metric design:** an early version of this harness averaged relevancy across *all* questions, including the deliberately unanswerable ones — which produced a misleadingly low score, since a correct "I don't know" is *not* a relevant answer to an out-of-scope question by definition, even though it's the *correct* response. The metric was redesigned to segment relevancy by whether a question should be answerable, and to measure unanswerable questions separately via refusal accuracy instead. This is the same "don't just report a number, understand why it is what it is" instinct behind the thesis-level error analysis this project's author has applied elsewhere — a naive average would have made a correctly-behaving system look worse than it is.

Both runners log results to JSONL files (`data/eval_log.jsonl`, `data/llm_eval_log.jsonl`) for tracking quality over time.

Run either with:
```bash
uv run python -m app.eval.run_eval
uv run python -m app.eval.run_llm_eval
```

## Testing

A pytest suite (`tests/`) covers:
- **Authentication** — registration, correct/incorrect login, rejection of nonexistent users
- **Token enforcement** — protected endpoints (`/query`, `/documents/upload`) correctly reject missing or invalid tokens
- **Multi-tenant isolation** — the highest-stakes correctness property in the system, now automated: two users are registered, each uploads distinct content, and the test confirms neither can ever retrieve the other's data
- **Upload validation** — file type, size, and empty-content checks on `/documents/upload`

External dependencies (OpenAI, Pinecone) are fully mocked, using a small in-memory fake vector store that genuinely applies the same `user_id` metadata filtering the real Pinecone integration does — so the isolation test proves the actual filtering logic works, not just that a mock returns pre-scripted data. This means the whole suite runs in seconds, costs nothing, and has no external dependency on real API availability.

Run the suite:
```bash
uv run pytest tests/ -v
```

The suite runs automatically in CI on every push, before the Docker build step.

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
- [x] **Milestone 4** — Automated evaluation harness: golden set (including unanswerable questions), custom LLM-as-judge scoring for faithfulness/relevancy/refusal accuracy
- [x] **Milestone 5** — Dockerized, added CI/CD (GitHub Actions), deployed to AWS ECS Fargate; added authenticated self-serve document upload endpoint

**Future improvements (not currently planned as milestones, but identified gaps):**
- [ ] Support PDF/DOCX uploads, not just `.txt`
- [ ] Add a document deletion endpoint
- [ ] Wire evaluation runs into CI, so quality regressions are caught automatically on every push

## Known Limitations

- **Text files only** — `/documents/upload` currently accepts `.txt` files only; no PDF/DOCX support yet.
- **No document deletion** — uploaded documents accumulate in Pinecone; there's currently no endpoint to remove a previously uploaded document.
- **Evaluation is manually triggered** — the evaluation harness exists and works but isn't yet wired into CI to run automatically on every push.
- **Prompt injection defense is keyword-based, not exhaustive** — the system prompt explicitly instructs the model to treat retrieved context as data, not instructions, and retrieved chunks are scanned against a list of common injection patterns before reaching the LLM, with matches logged as warnings. This catches obvious attempts but not sophisticated rephrasing, and detection currently only logs a warning rather than blocking the request outright.

## What I'd Do Differently at Scale

At higher scale, I'd move from filtering a shared Pinecone index by `user_id` metadata to fully namespaced storage per tenant (Pinecone supports this natively), move rate limiting from in-process (`slowapi`, which won't coordinate correctly across multiple horizontally-scaled ECS tasks) to a shared, distributed store like Redis, move query logging from a flat JSONL file to a proper time-series-queryable store for real monitoring, migrate off SQLite to unblock running more than one ECS task behind the load balancer already in place (currently `desiredCount: 1`, so the ALB provides a stable URL but not yet horizontal scaling), upgrade prompt injection detection beyond keyword matching toward a more robust classifier-based approach, and wire the evaluation harness into CI with a defined regression threshold (e.g., fail the build if faithfulness drops below 0.9) rather than running it manually.

## Debugging Journal (Selected Issues Encountered)

Documenting real issues hit during development, since debugging production systems — and knowing when to work around a broken dependency rather than keep fighting it — is as much a part of building them as writing the initial code:

- **SQLite silently creates empty databases.** `sqlite3.connect()` doesn't error if the target directory is missing in the way you'd expect — instead the app crashed with `unable to open database file` inside a fresh Docker container, because the `data/` directory didn't exist in the image. Fixed by explicitly creating the directory in the Dockerfile and calling `init_db()` on app startup via a lifespan handler.
- **Local port conflicts caused a false-positive test result.** An old local `uvicorn` process left running on port 8000 caused test requests to silently hit the wrong server while debugging a seemingly-passing Docker container — the container was actually crashing the whole time. Resolved by explicitly checking `docker logs` for request activity rather than trusting curl output alone.
- **IAM permissions for CloudWatch log group creation.** The default `AmazonECSTaskExecutionRolePolicy` doesn't include `logs:CreateLogGroup`, causing ECS tasks to fail on startup when using `awslogs-create-group: true`. Fixed by attaching `CloudWatchLogsFullAccess` to the task execution role.
- **ECR authentication tokens expire.** `docker push` began failing with a `403 Forbidden` after a period of inactivity between sessions — ECR login tokens are short-lived and need to be refreshed via `aws ecr get-login-password` before pushing again.
- **`ragas` had genuine, cascading upstream bugs.** While building the evaluation harness, the `ragas` library failed to import at all (`ModuleNotFoundError` for a `ChatVertexAI` path that had been removed from `langchain_community` in current versions — a confirmed bug in `ragas` itself, not a local misconfiguration). After patching the import and pinning dependency versions, a second, deeper bug surfaced inside `ragas`'s internal LLM-wrapper handling (`AttributeError: 'InstructorLLM' object has no attribute 'agenerate_prompt'`), which would have required debugging the library's own internals rather than application code. Rather than continuing to chase bugs inside a third-party dependency, the evaluation harness was rebuilt as a small, custom LLM-as-judge implementation — achieving the same faithfulness/relevancy scoring goal directly, with full understanding and control over the resulting code, and no dependency on an unstable library.
- **The same "assumes a directory exists" bug resurfaced twice more, in new environments.** After fixing it once for Docker (see above), the pytest suite hit an identical root cause in GitHub Actions CI: a fresh checkout has no `data/` directory at all (it's gitignored), so `init_db()` failed with the same `unable to open database file` error, even though the exact same test suite passed locally every time. Fixed the same way — explicitly creating the directory before use, this time in `conftest.py`. The pattern across three separate incidents (local vs. Docker vs. CI) reinforced the same lesson: any assumption about pre-existing filesystem state has to be verified in *every* environment that runs the code, not just the one you happen to be developing in.
- **External client libraries can make real network calls, or reject missing credentials, at import time — before any test or mock gets a chance to run.** Wiring the pytest suite into CI surfaced two distinct issues here. First, OpenAI's client raises immediately if `OPENAI_API_KEY` is completely unset (not just empty) — GitHub Actions' clean environment has no environment variables at all unless explicitly provided, unlike a local shell where a variable can exist but be empty. Second, and less obvious: Pinecone's client actually performs a real authenticated network call the moment `PineconeVectorStore(...)` is constructed, to look up the index — meaning a fake/dummy API key wasn't enough, since it's rejected over the network regardless of the string's value. Both `app/query.py` and `app/ingest.py` construct these clients at module import time, before any test fixture can intervene. The fix was patching `langchain_pinecone.PineconeVectorStore` at the very top of `conftest.py`, before any application module gets imported — ensuring the fake replaces the real class before it's ever used, rather than trying to mock it after the fact.
- **Windows PowerShell's `curl` alias and quoting behavior caused several false leads during manual testing.** PowerShell aliases `curl` to `Invoke-WebRequest` (different flag syntax entirely — fixed by always using `curl.exe` explicitly) and inconsistently handles single-quoted JSON bodies containing embedded double quotes, at one point causing a `422 JSON decode error` that looked like an application bug but was actually a request malformed before it ever left the terminal. The most reliable fix was writing the JSON body to a file (`body.json`) and sending it with `curl.exe --data-binary "@body.json"`, sidestepping shell quoting entirely.