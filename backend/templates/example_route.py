"""示例:一个完整 CRUD 路由模板(基于 templates.crud)。复制 / 改表名即用。

挂载方式(在 main.py):
    from templates import example_route
    app.include_router(example_route.router, prefix="/api")
然后:
    GET    /api/items            列表
    POST   /api/items            新建
    GET    /api/items/{id}       详情
    PUT    /api/items/{id}       更新
    DELETE /api/items/{id}       删除

前提:已配 DATABASE_URL 且执行过 templates/schema.sql 里的建表。
"""
from fastapi import APIRouter, HTTPException

from templates import crud

router = APIRouter(prefix="/items")

TABLE = "records"  # 改成你的表名


@router.get("")
async def list_items(limit: int = 100):
    return {"items": await crud.list_all(TABLE, limit=limit)}


@router.post("")
async def create_item(body: dict):
    return {"item": await crud.insert(TABLE, body)}


@router.get("/{item_id}")
async def get_item(item_id: str):
    row = await crud.get_by_id(TABLE, item_id)
    if not row:
        raise HTTPException(404, "not found")
    return {"item": row}


@router.put("/{item_id}")
async def update_item(item_id: str, body: dict):
    row = await crud.update_row(TABLE, item_id, body)
    if not row:
        raise HTTPException(404, "not found")
    return {"item": row}


@router.delete("/{item_id}")
async def delete_item(item_id: str):
    await crud.delete_row(TABLE, item_id)
    return {"ok": True}
