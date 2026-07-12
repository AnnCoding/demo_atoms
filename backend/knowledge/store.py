"""Local-first personal knowledge base with an explicit public square."""
from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time
import uuid

from context.ingest import ingest
from context.models import Attachment
from context.store import put


DATA_DIR = Path(__file__).parent.parent.parent / "data" / "knowledge"
ITEMS_PATH = DATA_DIR / "items.json"
MEMORY_DIR = DATA_DIR / "memory"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
_lock = threading.RLock()
MAX_KNOWLEDGE_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 120_000


def _load() -> list[dict]:
    with _lock:
        try:
            with open(ITEMS_PATH, encoding="utf-8") as file:
                value = json.load(file)
                return value if isinstance(value, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            return []


def _save(items: list[dict]) -> None:
    with _lock:
        tmp = ITEMS_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as file:
            json.dump(items, file, ensure_ascii=False, indent=2)
        os.replace(tmp, ITEMS_PATH)


def _parse_tags(tags) -> list[str]:
    if isinstance(tags, list):
        values = tags
    else:
        raw = str(tags or "").strip()
        try:
            value = json.loads(raw)
            values = value if isinstance(value, list) else [raw]
        except json.JSONDecodeError:
            values = raw.replace("，", ",").split(",")
    return list(dict.fromkeys(str(tag).strip()[:30] for tag in values if str(tag).strip()))[:10]


def _remember(owner_id: str, knowledge_id: str) -> None:
    safe_owner = "".join(char for char in owner_id if char.isalnum() or char in "_-") or "local-user"
    path = MEMORY_DIR / f"{safe_owner}.json"
    try:
        with open(path, encoding="utf-8") as file:
            ids = json.load(file)
            ids = ids if isinstance(ids, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        ids = []
    ids = [item for item in ids if item != knowledge_id] + [knowledge_id]
    with open(path, "w", encoding="utf-8") as file:
        json.dump(ids[-100:], file, ensure_ascii=False, indent=2)


async def create(
    content: bytes,
    filename: str,
    mime: str,
    *,
    title: str = "",
    description: str = "",
    tags=None,
    owner_id: str = "local-user",
    remember: bool = True,
    publish: bool = False,
) -> dict:
    if not content or len(content) > MAX_KNOWLEDGE_BYTES:
        raise ValueError(f"知识文件大小必须在 1-{MAX_KNOWLEDGE_BYTES} bytes")
    attachment = await ingest(content, filename, mime)
    now = int(time.time())
    item = {
        "id": uuid.uuid4().hex,
        "owner_id": owner_id or "local-user",
        "title": (title or filename).strip()[:120],
        "description": description.strip()[:500],
        "tags": _parse_tags(tags),
        "filename": filename,
        "mime": mime,
        "kind": attachment.kind,
        "text": (attachment.text or "")[:MAX_TEXT_CHARS],
        "storage_url": attachment.storage_url,
        "remembered": bool(remember),
        "published": bool(publish),
        "created_at": now,
        "updated_at": now,
    }
    items = _load()
    items.append(item)
    _save(items)
    if remember:
        _remember(item["owner_id"], item["id"])
    return public_view(item, include_text=True)


def public_view(item: dict, *, include_text: bool = False) -> dict:
    result = {key: value for key, value in item.items() if key != "text"}
    text = item.get("text") or ""
    result["excerpt"] = text[:300]
    if include_text:
        result["text"] = text
    return result


def list_owned(owner_id: str = "local-user") -> list[dict]:
    items = [public_view(item) for item in _load() if item.get("owner_id") == owner_id]
    return sorted(items, key=lambda item: item.get("updated_at", 0), reverse=True)


def list_square(query: str = "") -> list[dict]:
    needle = query.strip().lower()
    items = []
    for item in _load():
        if not item.get("published"):
            continue
        haystack = " ".join([
            item.get("title", ""), item.get("description", ""),
            " ".join(item.get("tags") or []), item.get("text", "")[:1000],
        ]).lower()
        if needle and needle not in haystack:
            continue
        view = public_view(item)
        view["owner_id"] = item.get("owner_id", "")
        items.append(view)
    return sorted(items, key=lambda item: item.get("updated_at", 0), reverse=True)[:100]


def get_item(knowledge_id: str) -> dict | None:
    return next((item for item in _load() if item.get("id") == knowledge_id), None)


def update(knowledge_id: str, body: dict, owner_id: str = "local-user") -> dict:
    items = _load()
    item = next((entry for entry in items if entry.get("id") == knowledge_id), None)
    if not item or item.get("owner_id") != owner_id:
        raise KeyError("Knowledge item not found")
    for key, limit in (("title", 120), ("description", 500)):
        if key in body:
            item[key] = str(body[key]).strip()[:limit]
    if "tags" in body:
        item["tags"] = _parse_tags(body["tags"])
    if "published" in body:
        item["published"] = bool(body["published"])
    if "remembered" in body:
        item["remembered"] = bool(body["remembered"])
        if item["remembered"]:
            _remember(owner_id, knowledge_id)
    item["updated_at"] = int(time.time())
    _save(items)
    return public_view(item, include_text=True)


def remove(knowledge_id: str, owner_id: str = "local-user") -> None:
    items = _load()
    item = next((entry for entry in items if entry.get("id") == knowledge_id), None)
    if not item or item.get("owner_id") != owner_id:
        raise KeyError("Knowledge item not found")
    _save([entry for entry in items if entry.get("id") != knowledge_id])


def as_attachment(knowledge_id: str, requester_id: str = "local-user") -> Attachment:
    item = get_item(knowledge_id)
    if not item or (item.get("owner_id") != requester_id and not item.get("published")):
        raise KeyError("Knowledge item not found or not accessible")
    attachment = Attachment(
        id=f"knowledge:{item['id']}",
        filename=item.get("filename") or item.get("title") or "knowledge.txt",
        mime=item.get("mime") or "text/plain",
        kind=item.get("kind") or "text",
        text=item.get("text") or "",
        storage_url=item.get("storage_url") or "",
    )
    put(attachment)
    return attachment


def memory_context(owner_id: str = "local-user", limit: int = 8) -> list[dict]:
    safe_owner = "".join(char for char in owner_id if char.isalnum() or char in "_-") or "local-user"
    path = MEMORY_DIR / f"{safe_owner}.json"
    try:
        with open(path, encoding="utf-8") as file:
            ids = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    lookup = {item.get("id"): item for item in _load()}
    result = []
    for knowledge_id in reversed(ids[-limit:]):
        item = lookup.get(knowledge_id)
        if item and item.get("remembered"):
            result.append({
                "id": item["id"], "title": item.get("title", ""),
                "tags": item.get("tags", []), "excerpt": (item.get("text") or "")[:1200],
            })
    return result
