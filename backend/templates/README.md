# 后端数据库模板(建表 + CRUD)

需要「真数据库」持久化时(生成的应用要后端存储 / 平台自身扩展),直接复用这里的模板。
**连接配置由使用者提供**(环境变量 `DATABASE_URL`),代码里不硬编码。

## 文件

| 文件                  | 作用                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------ |
| `schema.sql`          | 建表模板:通用记录表(uuid+jsonb+时间戳+软删除)、用户表、关联表、`updated_at` 触发器         |
| `crud.py`             | 通用 asyncpg CRUD:`insert / get_by_id / list_all / update_row / delete_row`(参数化,防注入) |
| `example_route.py`    | 一整个 FastAPI CRUD 路由模板,复制改名即用                                                  |
| `../core/database.py` | 连接池(预留):读 `DATABASE_URL`,惰性创建 asyncpg pool                                       |

## 用法

1. 装驱动(已写入 requirements.txt):
   ```bash
   pip install asyncpg
   ```
2. 在 `.env` 填连接串(使用者自行配置):
   ```
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   ```
3. 建表:在 Supabase SQL Editor / psql 执行 `schema.sql`(按需改表名/字段)。
4. 挂路由(在 `main.py`):
   ```python
   from templates import example_route
   app.include_router(example_route.router, prefix="/api")
   ```
5. 直接调用 CRUD:
   ```python
   from templates import crud
   row = await crud.insert("records", {"name": "x", "amount": 10})
   ```

## 与本地 stub 的关系

- `core/db.py`:**本地 JSON**(平台 projects 的默认 stub,开箱即用,无需 DB)。
- `core/database.py` + `templates/`:**真 Postgres**(可选,需要时启用)。
- 两者独立,不冲突。要持久化升级时,把 `db.py` 的几个函数改成调 `templates.crud` 即可。
