"""生成入口:{mode, prompt, attachment_ids, skill_id?} → SSE,跑到首个审批门或完成。"""
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.db import save_project
from core.orchestrator import run
from core.session import new_session
from core.sse import sse

router = APIRouter()
log = logging.getLogger("atoms.generate")


@router.post("/generate")
async def generate(body: dict):
    attachment_ids = list(body.get("attachment_ids", []))
    knowledge_ids = list(body.get("knowledge_ids", []))
    owner_id = body.get("owner_id") or "local-user"
    if knowledge_ids:
        from knowledge.store import as_attachment
        for knowledge_id in knowledge_ids:
            try:
                attachment_ids.append(as_attachment(knowledge_id, owner_id).id)
            except KeyError:
                # Inaccessible knowledge is ignored here; API never leaks its content.
                log.warning("知识条目不可访问: %s", knowledge_id)
    session = new_session(
        mode=body.get("mode", "engineer"),
        idea=body.get("prompt", ""),
        attachment_ids=attachment_ids,
        skill_id=body.get("skill_id"),
        owner_id=owner_id,
        knowledge_ids=knowledge_ids,
    )
    log.info(f"生成请求 mode={session.mode} skill={body.get('skill_id')} "
             f"idea={session.idea[:40]!r} session={session.id[:8]}")

    async def stream():
        if not session.idea:
            yield sse({"type": "error", "message": "prompt 不能为空"})
            return
        async for evt in run(session, save_project):
            yield evt

    return StreamingResponse(stream(), media_type="text/event-stream")
