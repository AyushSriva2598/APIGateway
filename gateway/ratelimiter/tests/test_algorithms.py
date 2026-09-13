import time
import uuid
import pytest

from ratelimiter.algorithms.token_bucket import TokenBucketLimiter
from ratelimiter.algorithms.fixed_window import FixedWindowLimiter


@pytest.fixture
def api_key():
    return f'test-{uuid.uuid4()}'


class TestTokenBucketLimiter:
    def test_allows_up_to_capacity(self, api_key):
        limiter = TokenBucketLimiter(capacity=3, refill_rate=1 / 60)
        for _ in range(3):
            allowed, _, _ = limiter.check(api_key)
            assert allowed is True

    def test_rejects_once_capacity_exhausted(self, api_key):
        limiter = TokenBucketLimiter(capacity=3, refill_rate=1 / 60)
        for _ in range(3):
            limiter.check(api_key)
        allowed, tokens, retry_after = limiter.check(api_key)
        assert allowed is False
        assert tokens < 1
        assert retry_after > 0

    def test_refills_over_time(self, api_key):
        limiter = TokenBucketLimiter(capacity=2, refill_rate=1.0)  # 1 token/sec
        limiter.check(api_key)
        limiter.check(api_key)
        allowed, _, _ = limiter.check(api_key)
        assert allowed is False

        time.sleep(1.1)

        allowed, _, _ = limiter.check(api_key)
        assert allowed is True

    def test_different_keys_are_independent(self):
        limiter = TokenBucketLimiter(capacity=1, refill_rate=1 / 60)
        key_a, key_b = f'a-{uuid.uuid4()}', f'b-{uuid.uuid4()}'
        allowed_a, _, _ = limiter.check(key_a)
        allowed_b, _, _ = limiter.check(key_b)
        assert allowed_a is True
        assert allowed_b is True


class TestFixedWindowLimiter:
    def test_allows_up_to_limit(self, api_key):
        limiter = FixedWindowLimiter(limit=3, window_seconds=60)
        for _ in range(3):
            allowed, _, _ = limiter.check(api_key)
            assert allowed is True

    def test_rejects_once_limit_exceeded(self, api_key):
        limiter = FixedWindowLimiter(limit=3, window_seconds=60)
        for _ in range(3):
            limiter.check(api_key)
        allowed, count, ttl = limiter.check(api_key)
        assert allowed is False
        assert count == 4
        assert 0 < ttl <= 60

    def test_window_resets_after_expiry(self, api_key):
        limiter = FixedWindowLimiter(limit=2, window_seconds=1)
        limiter.check(api_key)
        limiter.check(api_key)
        allowed, _, _ = limiter.check(api_key)
        assert allowed is False

        time.sleep(1.2)

        allowed, count, _ = limiter.check(api_key)
        assert allowed is True
        assert count == 1  # confirms an actual reset, not a continued increment