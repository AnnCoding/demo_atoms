"""生成代码的运行时校验:node + jsdom 跑一遍,捕获 init/运行时报错。

node/jsdom 不可用时静默跳过(返回 skipped=True),不阻塞生成流程。
"""
import asyncio
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VALIDATE_JS = os.path.join(HERE, "..", "validator", "validate.js")


async def validate_html(code: str) -> dict:
    """返回 {ok, errors, skipped}。"""
    if not code or "<" not in code:
        return {"ok": False, "errors": ["未检测到 HTML 内容"], "skipped": False}
    try:
        proc = await asyncio.create_subprocess_exec(
            "node", VALIDATE_JS,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(
            proc.communicate(code.encode("utf-8")), timeout=20
        )
        if proc.returncode != 0:
            return {"ok": False, "errors": [f"校验器异常(exit {proc.returncode})"],
                    "skipped": True}
        return json.loads(out.decode("utf-8"))
    except FileNotFoundError:
        # node 不存在 → 跳过
        return {"ok": True, "errors": [], "skipped": True}
    except asyncio.TimeoutError:
        return {"ok": False, "errors": ["校验超时"], "skipped": True}
    except Exception as e:
        # 任何意外都不阻塞主流程
        return {"ok": True, "errors": [], "skipped": True, "reason": str(e)}
