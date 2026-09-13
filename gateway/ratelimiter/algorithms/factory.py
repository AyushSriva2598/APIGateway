from functools import lru_cache
from ratelimiter.algorithms.token_bucket import TokenBucketLimiter
from ratelimiter.algorithms.fixed_window import FixedWindowLimiter
from ratelimiter.algorithms.sliding_window import SlidingWindowLimiter

_BUILDERS = {
    'token_bucket': lambda c: TokenBucketLimiter(capacity=c['capacity'], refill_rate=c['refill_rate']),
    'fixed_window': lambda c: FixedWindowLimiter(limit=c['limit'], window_seconds=c['window_seconds']),
    'sliding_window': lambda c: SlidingWindowLimiter(limit=c['limit'], window_seconds=c['window_seconds']),
}


@lru_cache(maxsize=32)
def _cached_limiter(algorithm: str, params: tuple):
    config = dict(params)
    return _BUILDERS[algorithm](config)


def get_limiter(config: dict):
    # lru_cache needs hashable args — dicts aren't, so convert to a
    # sorted tuple of items. This also means each distinct config only
    # builds one limiter instance (and registers its Lua script once),
    # not a fresh one per request.
    params = tuple(sorted((k, v) for k, v in config.items() if k != 'algorithm'))
    return _cached_limiter(config['algorithm'], params)