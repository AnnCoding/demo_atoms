"""短期记忆:会话状态(pipeline 进度、最近 artifact、澄清问答)。

REDIS_URL 配置时用 Redis(跨进程/重启不丢),否则内存 dict(默认,重启丢)。
预留 Redis:装 `redis` 包 + 配 REDIS_URL 即生效,无需改其它代码。
"""
import json
import os


class ShortTermMemory:
    def __init__(self):
        self._redis = None
        url = os.getenv("REDIS_URL")
        if url:
            try:
                import redis  # 预留:需 pip install redis
                self._redis = redis.Redis.from_url(url, decode_responses=True)
                self._redis.ping()
            except Exception as e:  # 装饰降级:未装 redis / 连不上 → 内存
                print(f"[shortterm] Redis 不可用,降级内存: {e}")
                self._redis = None
        self._mem: dict = {}

    def get(self, key: str):
        if self._redis:
            v = self._redis.get(key)
            return json.loads(v) if v else None
        return self._mem.get(key)

    def set(self, key: str, val, ttl: int = 86400):
        if self._redis:
            self._redis.setex(key, ttl, json.dumps(val, ensure_ascii=False))
        else:
            self._mem[key] = val

    def delete(self, key: str):
        if self._redis:
            self._redis.delete(key)
        else:
            self._mem.pop(key, None)
