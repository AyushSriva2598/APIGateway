def build_rate_limit_headers(limit: int, remaining: float, retry_after: int | None = None) -> dict:
    headers = {
        'X-RateLimit-Limit': str(limit),
        'X-RateLimit-Remaining': str(max(int(remaining), 0)),
    }
    if retry_after is not None:
        headers['Retry-After'] = str(max(retry_after, 1))
    return headers