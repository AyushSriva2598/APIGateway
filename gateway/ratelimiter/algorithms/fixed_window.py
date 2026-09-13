import os
import redis
from django.conf import settings

LUA_SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'lua_scripts', 'fixed_window.lua'
)


class FixedWindowLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )
        with open(LUA_SCRIPT_PATH) as f:
            self._script = self._redis.register_script(f.read())

    def check(self, api_key: str, cost: int = 1) -> tuple[bool, int, int]:
        """Returns (allowed, current_count, ttl_seconds)."""
        key = f'ratelimit:fixed_window:{api_key}'
        allowed, count, ttl = self._script(keys=[key], args=[self.limit, self.window_seconds, cost])
        return bool(int(allowed)), int(count), int(ttl)