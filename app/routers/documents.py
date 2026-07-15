from fastapi import APIRouter, Depends, UploadFile, HTTPException
from app.auth import get_current_user
from app.ingest import ingest_text

router = APIRouter()

MAX_FILE_SIZE = 1_000_000


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    current_user: dict = Depends(get_current_user)
):
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")

    raw_bytes = await file.read()

    if len(raw_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 1MB)")

    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")

    if not content.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    num_chunks = ingest_text(content, user_id=current_user["id"], source_name=file.filename)

    return {"message": f"Ingested {num_chunks} chunks", "filename": file.filename}