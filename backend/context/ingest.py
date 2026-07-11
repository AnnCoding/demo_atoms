"""附件摄取:分类 + 文本抽取 + 存储。"""
import uuid
from io import BytesIO

from .models import Attachment


def classify(mime: str) -> str:
    mime = (mime or "").lower()
    if mime.startswith("image/"):
        return "image"
    if mime == "application/pdf":
        return "pdf"
    if any(x in mime for x in ("javascript", "python", "css", "xml", "json", "typescript")):
        return "code"
    return "text"


def extract_text(content: bytes, kind: str) -> str:
    if kind == "pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(content))
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as e:
            return f"[pdf 提取失败: {e}]"
    if kind in ("text", "code"):
        return content.decode("utf-8", errors="ignore")
    return ""  # image → 无文本


async def ingest(content: bytes, filename: str, mime: str) -> Attachment:
    from core.storage import upload as storage_upload
    kind = classify(mime)
    text = extract_text(content, kind)
    storage_url = await storage_upload(content, filename)
    return Attachment(
        id=str(uuid.uuid4()),
        filename=filename, mime=mime, kind=kind,
        text=text if kind != "image" else None,
        image_url=storage_url if kind == "image" else None,
        storage_url=storage_url,
    )
