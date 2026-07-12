"""Versioned event envelope shared by SSE, the UI and LangSmith traces."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid


SCHEMA_VERSION = "2.0"


def event(event_type: str, *, session=None, **payload: Any) -> dict:
    if session is not None:
        session.event_seq = int(getattr(session, "event_seq", 0)) + 1
        seq = session.event_seq
        session_id = session.id
        run_id = getattr(session, "run_id", "")
    else:
        seq = payload.pop("sequence", 0)
        session_id = payload.get("session_id", "")
        run_id = payload.get("run_id", "")
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sequence": seq,
        "session_id": session_id,
        "run_id": run_id,
        "type": event_type,
        **payload,
    }


def normalize_questions(raw: list | None) -> list[dict]:
    """Keep choices machine-readable; never flatten them into display text."""
    questions: list[dict] = []
    for index, item in enumerate(raw or []):
        if isinstance(item, str):
            item = {"question": item, "options": []}
        if not isinstance(item, dict):
            continue
        label = str(item.get("question") or item.get("q") or item.get("text") or "").strip()
        if not label:
            continue
        options = []
        for option_index, option in enumerate(item.get("options") or []):
            if isinstance(option, str):
                option = {"label": option}
            if not isinstance(option, dict):
                continue
            option_label = str(option.get("label") or option.get("value") or "").strip()
            if option_label:
                options.append({
                    "id": str(option.get("id") or f"q{index + 1}_o{option_index + 1}"),
                    "label": option_label,
                    "description": str(option.get("description") or ""),
                    "recommended": bool(option.get("recommended", False)),
                })
        questions.append({
            "id": str(item.get("id") or f"q{index + 1}"),
            "question": label,
            "type": item.get("type") if item.get("type") in {"single_select", "multi_select", "text"} else ("single_select" if options else "text"),
            "required": bool(item.get("required", True)),
            "options": options,
            "allow_custom": bool(item.get("allow_custom", True)),
        })
    return questions
