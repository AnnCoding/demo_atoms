"""LLM 客户端。OpenAI 兼容协议(GLM / DeepSeek)。流式 + function-calling。

环境变量在函数内惰性读取(避免 import 早于 load_dotenv 导致读到空值)。

429 处理:指数退避重试 + 全局速率限制(避免触发智谱AI 的 RPM/TPM 限制)。
"""
import json
import os
import asyncio
import logging

import httpx
from langsmith import traceable

log = logging.getLogger("atoms.llm")

# 429 重试配置
MAX_RETRIES = 4              # 最大重试次数
INITIAL_BACKOFF = 1.0        # 初始退避秒数
MAX_BACKOFF = 30.0           # 最大退避秒数
RATE_LIMIT_INTERVAL = 0.5    # 全局最小请求间隔(秒),控制 RPM

# 全局速率限制锁(进程内串行化请求,避免突发并发触发 429)
_rate_lock = asyncio.Lock()
_last_request_time = 0.0


async def _respect_rate_limit():
    """确保请求间隔不小于 RATE_LIMIT_INTERVAL,平滑请求速率。"""
    global _last_request_time
    async with _rate_lock:
        now = asyncio.get_event_loop().time()
        elapsed = now - _last_request_time
        if elapsed < RATE_LIMIT_INTERVAL:
            await asyncio.sleep(RATE_LIMIT_INTERVAL - elapsed)
        _last_request_time = asyncio.get_event_loop().time()


# 永久性错误(重试无意义,直接抛出友好提示)
# key: 业务错误码, value: 友好提示
_FATAL_ERROR_HINTS = {
    "1113": "智谱AI 账户余额不足或资源包已用完,请登录 open.bigmodel.cn 充值。",
    "1301": "智谱AI API Key 无效,请检查 .env 中的 LLM_API_KEY。",
    "1112": "智谱AI 模型不存在或无权访问,请检查 LLM_MODEL 配置。",
}


class LLMFatalError(RuntimeError):
    """LLM 永久性错误(余额不足/Key 失效等),不应重试。"""

    def __init__(self, message: str, code: str = ""):
        super().__init__(message)
        self.code = code


def _check_fatal(resp: httpx.Response, op_name: str):
    """检查响应是否为永久性错误(余额不足等),是则抛 LLMFatalError。

    智谱AI 对余额不足也返回 429,需要解析 body 区分。
    """
    if resp.status_code != 429 and resp.status_code != 401:
        return
    try:
        body = resp.json()
        err = body.get("error", {}) if isinstance(body, dict) else {}
        code = str(err.get("code", ""))
        msg = err.get("message", "")
    except Exception:
        return

    if code in _FATAL_ERROR_HINTS:
        hint = _FATAL_ERROR_HINTS[code]
        log.error(f"[{op_name}] 永久性错误 code={code}: {msg} → {hint}")
        raise LLMFatalError(hint, code)


async def _retry_on_429(coro_factory, op_name: str = "llm"):
    """对协程工厂执行指数退避重试(针对 429 限流/5xx/网络抖动)。

    注意:余额不足(1113)、Key 失效(1301)等永久性错误不会重试,
    直接抛出 LLMFatalError。

    Args:
        coro_factory: 返回协程的可调用对象
        op_name: 操作名称(日志用)

    Returns:
        协程结果

    Raises:
        LLMFatalError: 永久性错误(余额不足等)
        HTTPStatusError: 重试耗尽后的瞬时错误
    """
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            await _respect_rate_limit()
            return await coro_factory()
        except LLMFatalError:
            # 永久性错误:不重试,直接向上抛(让 orchestrator 给前端清晰提示)
            raise
        except httpx.HTTPStatusError as e:
            last_exc = e
            status = e.response.status_code
            # 仅对 429(限流) 和 5xx 重试
            if status == 429 or 500 <= status < 600:
                # 优先用服务端建议的 Retry-After
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = float(retry_after)
                    except ValueError:
                        wait = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)
                else:
                    wait = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)

                if attempt < MAX_RETRIES:
                    log.warning(
                        f"[{op_name}] HTTP {status},第 {attempt + 1}/{MAX_RETRIES} 次重试,"
                        f"等待 {wait:.1f}s..."
                    )
                    await asyncio.sleep(wait)
                    continue
            # 非 429/5xx 或重试耗尽,直接抛出
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                wait = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)
                log.warning(
                    f"[{op_name}] 网络异常 {type(e).__name__},"
                    f"第 {attempt + 1}/{MAX_RETRIES} 次重试,等待 {wait:.1f}s..."
                )
                await asyncio.sleep(wait)
                continue
            raise

    raise last_exc


def _cfg():
    return (
        os.getenv("LLM_BASE_URL", ""),
        os.getenv("LLM_API_KEY", ""),
        os.getenv("LLM_MODEL", "glm-4.5"),
    )


def _configured() -> bool:
    base, key, _ = _cfg()
    return bool(base and key)


@traceable(name="llm_stream", run_type="llm")
async def stream(system: str, user: str):
    """流式生成,逐 token yield str。

    流式请求的重试策略:仅在建立连接时(首 chunk 前)失败才重试,
    一旦开始吐 token 则不重试(避免重复输出)。
    """
    base, key, model = _cfg()
    if not (base and key):
        yield _mock(system, user)
        return
    payload = {
        "model": model,
        "stream": True,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    async def _open_stream():
        client = httpx.AsyncClient(timeout=None)
        resp = await client.send(
            client.build_request("POST", f"{base}/chat/completions",
                                 headers=headers, json=payload),
            stream=True,
        )
        # 流式请求:429/401 时 body 还没读,先预读一点检查永久性错误
        if resp.status_code in (401, 429):
            await resp.aread()
            _check_fatal(resp, "stream")
        resp.raise_for_status()
        return client, resp

    # 建立连接时重试(429 在此处抛出)
    client, resp = await _retry_on_429(_open_stream, "stream")
    try:
        async for line in resp.aiter_lines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                return
            try:
                delta = json.loads(data)["choices"][0]["delta"].get("content")
            except Exception:
                delta = None
            if delta:
                yield delta
    finally:
        await resp.aclose()
        await client.aclose()


@traceable(name="llm_complete", run_type="llm")
async def complete(messages: list, tools: list = None):
    """非流式 + function-calling,返回 {content, tool_calls}。用于 ReAct 循环。

    自动对 429/5xx/网络错误做指数退避重试。
    """
    base, key, model = _cfg()
    if not (base and key):
        return {"content": _mock(messages[0]["content"], messages[-1]["content"]),
                "tool_calls": []}
    payload = {"model": model, "stream": False, "messages": messages}
    if tools:
        payload["tools"] = [{"type": "function", "function": _schema(t)} for t in tools]
        payload["tool_choice"] = "auto"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    async def _do():
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{base}/chat/completions",
                                  headers=headers, json=payload)
            _check_fatal(r, "complete")  # 余额不足等永久性错误优先识别
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
            return {
                "content": msg.get("content") or "",
                "tool_calls": _parse(msg.get("tool_calls")),
            }

    return await _retry_on_429(_do, "complete")


def _mock(system: str, user: str) -> str:
    return (f"[LLM 未配置,模拟输出]\nsystem: {system[:60]}...\n"
            f"user: {user[:80]}...\n(填 LLM_BASE_URL / LLM_API_KEY 后为真实输出)")


def _schema(tool_name: str) -> dict:
    from tools.registry import TOOLS
    return TOOLS[tool_name].schema


def _parse(raw):
    out = []
    if not raw:
        return out
    for tc in raw:
        fn = tc.get("function", {})
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except Exception:
            args = {}
        out.append({"name": fn.get("name"), "args": args})
    return out