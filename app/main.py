from fastapi import FastAPI, Depends
from app.query import answer_question
from app.models import QueryRequest, QueryResponse
from app.auth import get_current_user
from app.routers.auth import router as auth_router

app = FastAPI()
app.include_router(auth_router)

@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    answer = answer_question(request.question, user_id=current_user["id"])
    return QueryResponse(question=request.question, answer=answer)