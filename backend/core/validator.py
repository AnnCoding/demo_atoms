"""生成代码的运行时校验:node + jsdom 跑一遍,捕获 init/运行时报错。

node/jsdom 不可用时静默跳过(返回 skipped=True),不阻塞生成流程。
"""
import asyncio
import json
import os
import re

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


def html_complete(code: str) -> tuple[bool, str]:
    """纯字符串完整性检查(不走 node),入库前快速拦截被 max_tokens 截断的半成品。

    与 validate_html 互补:validate_html 依赖 jsdom,会对半截 HTML 自动补全 DOM
    而误判 ok;本函数只做原始标签配对检查,用于入库前的硬性拦截与截断续写门控。
    """
    if not code:
        return False, "代码为空"
    low = code.lower()
    start = low.find("<html")
    end = low.rfind("</html>")
    if start < 0:
        return False, "缺少 <html> 根标签"
    if end < start:
        return False, "缺少 </html> 闭合标签(输出可能被 max_tokens 截断)"
    for tag in ("script", "style", "body"):
        opens = len(re.findall(rf"<{tag}[\s>]", low))
        closes = low.count(f"</{tag}>")
        if opens != closes:
            return False, f"<{tag}> 标签未配对(开 {opens} 闭 {closes}),可能被截断"
    return True, ""
