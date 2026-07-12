"""审批续跑:{session_id, answers?} → SSE。answers 用于回答 Mike 的澄清提问。"""
import json
import logging
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.db import save_project
from core.orchestrator import run
from core.memory import ProjectMemory
from core.session import get_session
from core.sse import sse

router = APIRouter()
log = logging.getLogger("atoms.approve")


@router.post("/approve")
async def approve(body: dict):
    session = get_session(body.get("session_id", ""))
    answers = body.get("answers")
    if session and answers:
        answer_text = json.dumps(answers, ensure_ascii=False) if isinstance(answers, (dict, list)) else str(answers)
        session.clarify_answers = (session.clarify_answers or "") + "\n用户回答:" + answer_text
        session.conversation.append({
            "id": f"msg_{len(session.conversation) + 1}", "role": "user", "agent": "",
            "content": answer_text, "text": answer_text, "format": "structured_answers",
            "created_at": time.time(),
        })
        ProjectMemory(session.project_id).remember_message("user", answer_text)
    log.info(f"审批/续跑 session={body.get('session_id', '')[:8]} "
             f"found={bool(session)} has_answers={bool(answers)}")

    async def stream():
        if not session:
            yield sse({"type": "error", "message": "session not found"})
            return
        async for evt in run(session, save_project):
            yield evt

    return StreamingResponse(stream(), media_type="text/event-stream")
