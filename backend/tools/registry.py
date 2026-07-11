"""统一工具注册表 = 连接器(MCP 外部工具)+ 文件工具。"""
from connectors.registry import CONNECTORS
from .file_tools import FileEditTool, FileReadTool, FileWriteTool

TOOLS = dict(CONNECTORS)  # web_search 等
TOOLS.update({
    "file_read": FileReadTool(),
    "file_write": FileWriteTool(),
    "file_edit": FileEditTool(),
})

# 预留:后续接 MCP server 时,把 MCP client 也合并进 TOOLS
