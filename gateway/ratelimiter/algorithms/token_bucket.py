import os
import time
import redis
from django.conf import settings

LUA_SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'lua_scripts', 'token_bucket.lua'
)


class TokenBucketLimiter:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )
        with open(LUA_SCRIPT_PATH) as f:
            script_source = f.read()
        # register_script compiles once, caches the SHA, and calls it via
        # EVALSHA on every subsequent invocation — this is what makes the
        # check atomic and cheap, not re-uploading Lua source every request
        self._script = self._redis.register_script(script_source)

    def check(self, api_key: str, cost: int = 1) -> tuple[bool, float, int]:
        """Returns (allowed, tokens_remaining, retry_after_seconds)."""
        key = f'ratelimit:token_bucket:{api_key}'
        now = time.time()

        allowed, tokens, retry_after = self._script(
            keys=[key],
            args=[self.capacity, self.refill_rate, now, cost],
        )
        return bool(int(allowed)), float(tokens), int(retry_after)