"""SSE 事件编码。"""
import json


def sse(obj: dict) -> str:
    """把 dict 编码成一条 SSE 事件(data: ...\\n\\n)。"""
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"
