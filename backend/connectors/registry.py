"""连接器注册表。"""
from .base import Connector
from .web_search import WebSearchConnector

CONNECTORS = {
    "web_search": WebSearchConnector(),
    # 预留:github / mcp__notion / ...(均为 MCP server)
}


def list_connectors() -> list:
    return [{"id": c.id, "schema": c.schema} for c in CONNECTORS.values()]
