"""文件存储。v1 本地落盘到 data/uploads;配置 Supabase 后切换 Storage。"""
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "..", "data")
LOCAL_DIR = os.getenv("STORAGE_DIR", os.path.join(DATA_DIR, "uploads"))
os.makedirs(LOCAL_DIR, exist_ok=True)


async def upload(content: bytes, filename: str) -> str:
    """返回可访问 URL。v1 用 local:// 占位;TODO: Supabase Storage。"""
    ext = os.path.splitext(filename)[1]
    key = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(LOCAL_DIR, key), "wb") as f:
        f.write(content)
    return f"local://{key}"
