from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from app.query import answer_question
from app.models import QueryRequest, QueryResponse
from app.auth import get_current_user
from app.routers.auth import router as auth_router
from app.routers.documents import router as documents_router
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(documents_router)


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    answer = answer_question(request.question, user_id=current_user["id"])
    return QueryResponse(question=request.question, answer=answer)