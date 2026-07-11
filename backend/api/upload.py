"""附件上传:multipart → 摄取 → attachment_id。"""
from fastapi import APIRouter, File, UploadFile

from context.ingest import ingest
from context.store import put

router = APIRouter()


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    a = await ingest(content, file.filename, file.content_type or "text/plain")
    put(a)
    return {
        "attachment_id": a.id,
        "filename": a.filename,
        "kind": a.kind,
        "mime": a.mime,
    }
