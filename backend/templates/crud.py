"""通用 CRUD 模板(asyncpg / Postgres),可直接复用或按需改。

依赖 core.database 的连接池(DATABASE_URL 配置后生效;未配置则抛错)。
占位符用 asyncpg 的 $1, $2 ... 风格(参数化,防注入)。
注意:表名/列名不能参数化,本模板直接拼接 —— 生产环境应做白名单校验。

示例:
    row = await crud.insert("records", {"name": "x", "amount": 10})
    rows = await crud.list_all("records", limit=20)
    await crud.update_row("records", row_id, {"amount": 20})
    await crud.delete_row("records", row_id)
"""
from typing import Any, Mapping

from core.database import get_pool


async def execute(sql: str, *args: Any) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(sql, *args)


async def fetchrow(sql: str, *args: Any) -> Mapping | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(sql, *args)


async def fetch(sql: str, *args: Any) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(sql, *args)


async def insert(table: str, data: dict) -> Mapping | None:
    """插入并返回新行(RETURNING *)。"""
    cols = list(data.keys())
    placeholders = ", ".join(f"${i + 1}" for i in range(len(cols)))
    cols_sql = ", ".join(cols)
    sql = f'INSERT INTO "{table}" ({cols_sql}) VALUES ({placeholders}) RETURNING *'
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(sql, *data.values())


async def get_by_id(table: str, row_id: Any, pk: str = "id") -> Mapping | None:
    return await fetchrow(f'SELECT * FROM "{table}" WHERE {pk} = $1', row_id)


async def list_all(table: str, limit: int = 100, order: str = "created_at DESC") -> list:
    return await fetch(f'SELECT * FROM "{table}" ORDER BY {order} LIMIT $1', limit)


async def update_row(table: str, row_id: Any, data: dict, pk: str = "id") -> Mapping | None:
    cols = list(data.keys())
    set_sql = ", ".join(f"{c} = ${i + 1}" for i, c in enumerate(cols))
    sql = f'UPDATE "{table}" SET {set_sql} WHERE {pk} = ${len(cols) + 1} RETURNING *'
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(sql, *data.values(), row_id)


async def delete_row(table: str, row_id: Any, pk: str = "id") -> str:
    return await execute(f'DELETE FROM "{table}" WHERE {pk} = $1', row_id)
