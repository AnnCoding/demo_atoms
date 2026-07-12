"""Personal knowledge base and explicitly published knowledge square APIs."""
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from knowledge import store


router = APIRouter()


@router.get("/knowledge")
def mine(owner_id: str = Query("local-user")):
    return {"items": store.list_owned(owner_id)}


@router.get("/knowledge/square")
def square(q: str = Query("")):
    return {"items": store.list_square(q)}


@router.post("/knowledge/upload")
async def upload(
    file: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form(""),
    tags: str = Form(""),
    owner_id: str = Form("local-user"),
    remember: bool = Form(True),
    publish: bool = Form(False),
):
    try:
        item = await store.create(
            await file.read(), file.filename or "knowledge.txt", file.content_type or "text/plain",
            title=title, description=description, tags=tags, owner_id=owner_id,
            remember=remember, publish=publish,
        )
        return {"ok": True, "item": item}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/knowledge/{knowledge_id}")
def update(knowledge_id: str, body: dict, owner_id: str = Query("local-user")):
    try:
        return {"ok": True, "item": store.update(knowledge_id, body, owner_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/knowledge/{knowledge_id}")
def remove(knowledge_id: str, owner_id: str = Query("local-user")):
    try:
        store.remove(knowledge_id, owner_id)
        return {"ok": True}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/knowledge/{knowledge_id}/use")
def use(knowledge_id: str, owner_id: str = Query("local-user")):
    try:
        attachment = store.as_attachment(knowledge_id, owner_id)
        return {
            "ok": True, "attachment_id": attachment.id,
            "filename": attachment.filename, "kind": attachment.kind,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
