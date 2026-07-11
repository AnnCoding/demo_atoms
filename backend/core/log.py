"""统一日志配置。支持 pretty（彩色终端）和 json（结构化）两种格式，通过 LOG_FORMAT 环境变量切换。"""
import json
import logging
import os
import sys
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """JSON 结构化日志格式（生产环境 / 日志聚合工具用）。"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # 附加结构化字段（通过 extra={...} 传入）
        for key in ("session_id", "agent", "step", "duration_ms", "tool", "iteration", "agent_id"):
            val = getattr(record, key, None)
            if val is not None:
                log_data[key] = val
        return json.dumps(log_data, ensure_ascii=False)


class PrettyFormatter(logging.Formatter):
    """人类可读的彩色终端日志格式（开发环境用）。"""

    COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[1;31m",  # bold red
    }
    RESET = "\033[0m"
    DIM = "\033[90m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]

        parts: list[str] = [
            f"{color}{record.levelname:5s}{self.RESET}",
            f"{self.DIM}{time_str}{self.RESET}",
        ]

        # session_id 前 8 位
        session_id = getattr(record, "session_id", None)
        if session_id:
            parts.append(f"{self.MAGENTA}[{session_id[:8]}]{self.RESET}")

        # agent name
        agent = getattr(record, "agent", None)
        if agent:
            parts.append(f"{self.BLUE}{agent}{self.RESET}")

        # 消息体
        parts.append(record.getMessage())

        # 耗时
        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            parts.append(f"{self.DIM}({duration_ms:.0f}ms){self.RESET}")

        return " | ".join(parts)


def setup(level: str = "INFO"):
    """初始化日志。通过环境变量 LOG_FORMAT=pretty|json 切换格式，默认 pretty。"""
    fmt_type = os.getenv("LOG_FORMAT", "pretty").lower()

    handler = logging.StreamHandler(sys.stdout)
    if fmt_type == "json":
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(PrettyFormatter())

    logging.basicConfig(level=level, handlers=[handler], force=True)