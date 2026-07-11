"""多轮对话迭代:{session_id, message} → SSE。

基于已生成应用做修改:取回 session,轮次+1,记录最新指令,run() 会走迭代分支。
与 /api/approve(澄清/审批续跑)共存:approve 在 pipeline 中间断点续跑;
chat 仅在 pipeline 完成后触发迭代(idx >= len(steps))。
"""
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.db import save_project
from core.orchestrator import run
from core.session import get_session, save_session
from core.sse import sse

router = APIRouter()
log = logging.getLogger("atoms.chat")


@router.post("/chat")
async def chat(body: dict):
    message = (body.get("message") or "").strip()
    session_id = body.get("session_id", "")
    slug = body.get("slug", "")

    # 1) 优先用内存 session(主页刚生成完,session 还在)
    session = get_session(session_id) if session_id else None
    # 2) session 不在 → 从作品(slug)重建,支持随时/旧作品继续对话
    if not session and slug:
        from core.db import get_project
        from core.session import session_from_project
        row = get_project(slug)
        if row:
            session = session_from_project(row)

    async def stream():
        if not session:
            yield sse({"type": "error", "message": "会话/作品不存在"})
            return
        if not message:
            yield sse({"type": "error", "message": "消息不能为空"})
            return
        # 设置迭代状态:轮次 +1,记录最新修改指令
        session.iteration += 1
        session.last_user_msg = message
        save_session(session)
        log.info(f"迭代请求 session={session.id[:8]} slug={slug or '-'} "
                 f"iteration={session.iteration} msg={message[:40]!r}")
        async for evt in run(session, save_project):
            yield evt

    return StreamingResponse(stream(), media_type="text/event-stream")
