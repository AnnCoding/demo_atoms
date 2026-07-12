"""SSE event encoding with a versioned envelope and per-run sequencing."""
from contextvars import ContextVar
import json

from core.events import event


_session_context: ContextVar[object | None] = ContextVar("event_session", default=None)


def bind_session(session):
    """Bind once at orchestrator entry; child asyncio tasks inherit the context."""
    _session_context.set(session)


def sse(obj: dict) -> str:
    """把 dict 编码成一条 SSE 事件(data: ...\\n\\n)。"""
    if "schema_version" not in obj:
        payload = dict(obj)
        event_type = payload.pop("type", "message")
        obj = event(event_type, session=_session_context.get(), **payload)
    return f"data: {json.dumps(obj, ensure_ascii=False, default=str)}\n\n"
