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
    session = new_session(
        mode=body.get("mode", "engineer"),
        idea=body.get("prompt", ""),
        attachment_ids=body.get("attachment_ids", []),
        skill_id=body.get("skill_id"),
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
