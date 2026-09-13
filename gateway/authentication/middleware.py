class APIKeyAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # /healthz stays open — no key needed to check if the gateway is alive
        if request.path == '/healthz':
            return self.get_response(request)

        api_key = request.headers.get('X-API-Key')

        if not api_key:
            from django.http import JsonResponse
            return JsonResponse({'detail': 'X-API-Key header required'}, status=401)

        # No DB/Redis lookup yet — that's Day 2/4. For now, just attach it
        # to the request so downstream code (rate limiter, proxy) can see it.
        request.api_key = api_key

        return self.get_response(request)