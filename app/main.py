from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.auth import get_current_user
from app.database import init_db
from app.limiter import limiter
from app.models import QueryRequest, QueryResponse
from app.query import answer_question
from app.routers.auth import router as auth_router
from app.routers.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(auth_router)
app.include_router(documents_router)


@app.post("/query", response_model=QueryResponse)
@limiter.limit("10/minute")
def query(request: Request, query_request: QueryRequest, current_user: dict = Depends(get_current_user)):
    answer = answer_question(query_request.question, user_id=current_user["id"])
    return QueryResponse(question=query_request.question, answer=answer)