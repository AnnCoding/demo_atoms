"""作品库 / 分享 / 应用静态文件 / 项目数据库(database.md)读写。"""
import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

from core.db import APPS_DIR, DATA_DIR, get_project, list_projects

router = APIRouter()


@router.get("/projects")
def list_all():
    return {"projects": list_projects()}


@router.get("/projects/{slug}")
def get_one(slug: str):
    return {"project": get_project(slug)}


@router.get("/apps/{slug}.html")
def serve_app(slug: str):
    """暴露 apps/{slug}.html,供作品库缩略图 iframe 渲染。"""
    path = os.path.join(APPS_DIR, f"{slug}.html")
    if not os.path.exists(path):
        return {"error": "not found"}
    return FileResponse(path, media_type="text/html")


def _db_path(project_id: str) -> str:
    """项目 workspace/database.md 路径(生成应用持久化数据的真文件)。"""
    return os.path.join(DATA_DIR, "projects", project_id, "workspace", "database.md")


@router.get("/projects/{slug}/db")
def get_db(slug: str):
    """读取项目 workspace/database.md(不存在则初始化为空库)。供生成应用读持久数据。"""
    row = get_project(slug)
    if not row:
        return {"error": "not found"}
    path = _db_path(row["id"])
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Database\n")
    with open(path, encoding="utf-8") as f:
        return {"content": f.read()}


@router.put("/projects/{slug}/db")
async def put_db(slug: str, body: dict):
    """写入项目 workspace/database.md。供生成应用持久化数据。"""
    row = get_project(slug)
    if not row:
        return {"error": "not found"}
    path = _db_path(row["id"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body.get("content", ""))
    return {"ok": True}
