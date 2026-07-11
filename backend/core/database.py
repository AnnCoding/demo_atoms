"""通用关系型数据库连接(预留)。与 core/db.py(本地 JSON stub)区分开。

- 本文件:给 templates/ 的建表 + CRUD 用的「真数据库」连接(Postgres / asyncpg)。
- 配置方式:环境变量 DATABASE_URL(由使用者自行提供,代码里不硬编码)。
- 未配置或未装 asyncpg 时,所有操作会抛清晰错误,不影响主流程启动(惰性)。
"""
import os
from typing import Optional

_pool = None


def database_url() -> Optional[str]:
    return os.getenv("DATABASE_URL") or None


def is_configured() -> bool:
    return bool(database_url())


async def get_pool():
    """惰性创建 asyncpg 连接池。"""
    global _pool
    if _pool is not None:
        return _pool
    url = database_url()
    if not url:
        raise RuntimeError("DATABASE_URL 未配置(预留项:由使用者提供数据库连接串)")
    import asyncpg  # 预留:需 pip install asyncpg
    _pool = await asyncpg.create_pool(url, min_size=1, max_size=10)
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
