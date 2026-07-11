"""连接器基类(MCP 兼容接口)。"""
from typing import Any


class Connector:
    id: str = ""
    schema: dict = {}  # JSON-schema / MCP 工具定义

    async def call(self, **args: Any) -> str:
        raise NotImplementedError
