import time
import threading
from django.http import JsonResponse

# In-process only — lives in this worker's memory, gone on restart,
# invisible to the other 2 gateway replicas. That gap is the whole point
# of Day 1: prove this breaks under multi-instance before Redis fixes it.
_counters = {}
_lock = threading.Lock()

WINDOW_SECONDS = 60
MAX_REQUESTS = 5


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/healthz':
            return self.get_response(request)

        api_key = getattr(request, 'api_key', None)
        if not api_key:
            # auth middleware already rejects missing keys — this is a
            # safety fallback, not the primary check
            return self.get_response(request)

        now = time.time()

        with _lock:
            window_start, count = _counters.get(api_key, (now, 0))

            if now - window_start > WINDOW_SECONDS:
                # window expired, reset
                window_start, count = now, 0

            count += 1
            _counters[api_key] = (window_start, count)

        if count > MAX_REQUESTS:
            retry_after = int(WINDOW_SECONDS - (now - window_start))
            return JsonResponse(
                {'detail': 'rate limit exceeded'},
                status=429,
                headers={'Retry-After': str(max(retry_after, 1))},
            )

        return self.get_response(request)