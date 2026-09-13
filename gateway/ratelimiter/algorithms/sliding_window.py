import os
import time
import uuid
import redis
from django.conf import settings

LUA_SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'lua_scripts', 'sliding_window_log.lua'
)


class SlidingWindowLimiter:
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

    def check(self, api_key: str) -> tuple[bool, int, int]:
        key = f'ratelimit:sliding_log:{api_key}'
        now_ms = int(time.time() * 1000)
        # unique per call — two requests in the same millisecond must not
        # collide as the same sorted-set member
        member = f'{now_ms}-{uuid.uuid4().hex[:8]}'
        allowed, count, retry_after = self._script(
            keys=[key], args=[self.limit, self.window_seconds, now_ms, member]
        )
        return bool(int(allowed)), int(count), int(retry_after)