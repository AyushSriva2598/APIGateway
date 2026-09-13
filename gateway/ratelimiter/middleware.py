import time
import logging
from django.http import JsonResponse
from ratelimiter.config import resolve_algorithm_config
from ratelimiter.algorithms.factory import get_limiter
from ratelimiter.headers import build_rate_limit_headers
from observability.metrics import rate_limit_decisions_total, rate_limit_check_duration_seconds

logger = logging.getLogger('ratelimiter')


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in ('/healthz', '/metrics') or request.path.startswith('/admin'):
            return self.get_response(request)

        api_key = getattr(request, 'api_key', None)
        if not api_key:
            return self.get_response(request)

        config = resolve_algorithm_config(request.path, api_key)
        limiter = get_limiter(config)

        start = time.time()
        allowed, remaining_or_count, retry_after = limiter.check(api_key)
        rate_limit_check_duration_seconds.labels(algorithm=config['algorithm']).observe(time.time() - start)

        limit_value = config.get('capacity') or config.get('limit')
        log_fields = {
            'api_key_prefix': api_key[:8], 'path': request.path,
            'algorithm': config['algorithm'], 'allowed': allowed, 'limit': limit_value,
        }

        if not allowed:
            rate_limit_decisions_total.labels(algorithm=config['algorithm'], decision='rejected').inc()
            logger.warning('rate_limit_rejected', extra={**log_fields, 'retry_after': retry_after})
            headers = build_rate_limit_headers(limit_value, 0, retry_after)
            return JsonResponse({'detail': 'rate limit exceeded'}, status=429, headers=headers)

        rate_limit_decisions_total.labels(algorithm=config['algorithm'], decision='allowed').inc()
        logger.info('rate_limit_allowed', extra=log_fields)

        response = self.get_response(request)
        headers = build_rate_limit_headers(limit_value, limit_value - remaining_or_count if config['algorithm'] != 'token_bucket' else remaining_or_count)
        for key, value in headers.items():
            response[key] = value
        return response