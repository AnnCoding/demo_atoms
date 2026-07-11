"""web_search 连接器(v1:Tavily)。"""
import os

from .base import Connector


class WebSearchConnector(Connector):
    id = "web_search"
    schema = {
        "name": "web_search",
        "description": "搜索网页,返回相关结果摘要与链接。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["query"],
        },
    }

    async def call(self, query: str) -> str:
        key = os.getenv("TAVILY_API_KEY")
        if not key:
            return f"[web_search 未配置 TAVILY_API_KEY] 模拟:关于「{query}」的若干结果。"
        try:
            from tavily import TavilyClient
            res = TavilyClient(api_key=key).search(query, max_results=5)
            lines = []
            for r in res.get("results", []):
                lines.append(f"- {r.get('title')}: {r.get('url')}\n  {(r.get('content') or '')[:200]}")
            return "\n".join(lines) or "[无结果]"
        except Exception as e:
            return f"[web_search 错误: {e}]"
