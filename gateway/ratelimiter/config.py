# Per-route defaults. Checked by path prefix, same matching style as
# BACKEND_ROUTES in proxy config — longest/first match wins.
ROUTE_ALGORITHM_CONFIG = {
    '/api/orders': {'algorithm': 'sliding_window', 'limit': 10, 'window_seconds': 60},
    '/api/users': {'algorithm': 'token_bucket', 'capacity': 5, 'refill_rate': 5 / 60},
}

# Per-key overrides — a stand-in for the real tier system coming Day 4
# (Postgres-backed APIKey/Tier models). Hardcoded here on purpose so
# algorithm selection can be built and tested before that model exists.
KEY_ALGORITHM_OVERRIDES = {
    'headertest': {'algorithm': 'fixed_window', 'limit': 5, 'window_seconds': 60},
}

DEFAULT_ALGORITHM_CONFIG = {'algorithm': 'fixed_window', 'limit': 5, 'window_seconds': 60}


def resolve_algorithm_config(path: str, api_key: str) -> dict:
    if api_key in KEY_ALGORITHM_OVERRIDES:
        return KEY_ALGORITHM_OVERRIDES[api_key]
    for prefix, config in ROUTE_ALGORITHM_CONFIG.items():
        if path.startswith(prefix):
            return config
    return DEFAULT_ALGORITHM_CONFIG